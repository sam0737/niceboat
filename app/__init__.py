from flask import Flask, session, redirect, url_for, render_template, request, abort, send_file
import os
import random
import time
import string
import io
from captcha.image import ImageCaptcha
from config import Config
from .supervisor_config_manager import SupervisorConfigManager
from .auth_file import authenticate, get_user_profile, update_user_profile
from . import timed_signature
import logging
import logging.handlers
from .mailer import sendmail

handler = logging.handlers.RotatingFileHandler('run/app.log', maxBytes=1024*1024*5, backupCount=5, encoding='utf-8')
handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s [%(funcName)s:%(lineno)d] %(message)s'))
handler.setLevel(logging.DEBUG)

app = Flask(__name__, static_folder='static', static_url_path='')
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SECRET_KEY'] = Config.secret
app.logger.addHandler(handler)
app.logger.setLevel(logging.DEBUG)

scm = SupervisorConfigManager( os.path.dirname(os.path.dirname(os.path.realpath(__file__))) + '/supervisord_config' )

class UnauthorizedException(Exception):
    pass

@app.before_request
def csrf_protect():
    if request.method == "POST":
        token = session.get('_csrf_token')
        if not token or token != request.form.get('_csrf_token'):
            abort(403, 'CSRF Token 错误，请返回主页重新登录')

def generate_csrf_token():
    if '_csrf_token' not in session:
        pool = string.ascii_letters + string.digits
        session['_csrf_token'] = ''.join(random.choice(pool) for i in range(16))
    return session['_csrf_token']

app.jinja_env.globals['csrf_token'] = generate_csrf_token

def assert_valid_session():
    if 'username' not in session:
        raise UnauthorizedException
    if 'time' not in session:
        raise UnauthorizedException
    if time.time() - int(session['time']) > 60 * 5:
        raise UnauthorizedException
    session['time'] = time.time()

@app.errorhandler(UnauthorizedException)
def handle_unauthorized_exception(ex):
    return redirect(url_for('index'))

@app.after_request
def add_header(r):
    """
    Add headers to both force latest IE rendering engine or Chrome Frame,
    and also to cache the rendered page for 10 minutes.
    """
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    r.headers['Cache-Control'] = 'public, max-age=0'
    return r

@app.template_filter('strftime')
def _jinja2_filter_datetime(value, fmt='%Y-%m-%d %H:%M:%S'):
    return time.strftime(fmt, time.localtime(value))

@app.route('/', methods=['GET', 'POST'])
def index():
    auth_failed = False
    if request.method == "POST":
        if authenticate(request.form['username'], request.form['password']):
            session.clear()
            session['username'] = request.form['username']
            session['time'] = time.time()
            return redirect(url_for('main'))
        auth_failed = True

    session.pop('username', None)
    m = dict()
    return render_template('login.html', auth_failed=auth_failed, m=m)

@app.route('/welcome')
def main():
    assert_valid_session()
    ss_links = scm.create(session['username'])
    return render_template('main.html', ss_links=ss_links)

@app.route('/restart', methods=['POST'])
def restart():
    assert_valid_session()
    scm.restart(session['username'])
    return render_template('status.html', title="重启", message="穿越隧道已成功重启")

@app.route('/recreate', methods=['POST'])
def recreate():
    assert_valid_session()
    scm.remove(session['username'])
    scm.create(session['username'])
    return render_template('status.html', title="重建", message="穿越隧道已重建，请返回上一页获取参数。")

@app.route('/password/reset', methods=['GET', 'POST'])
def password_reset():
    username = request.args.get('username', '')
    reset_key = request.args.get('reset_key', '')
    user_profile = get_user_profile({'username': username})
    check = False
    password_complexity_failed = False
    if user_profile:
        if timed_signature.validate(
            (user_profile['username'] + ':' + (user_profile['crypt'] or '')).encode('utf-8'),
            reset_key,
            size = 600):
            check = True
    if not check:
        return render_template('password_forget.html', reset_key_failed=True)
    if request.method == "POST":
        password = request.form['password']
        kinds = 0
        if len(password) < 8:
            password_complexity_failed = True
        if any(x in password for x in string.ascii_uppercase):
            kinds = kinds + 1
        if any(x in password for x in string.ascii_lowercase):
            kinds = kinds + 1
        if any(x in password for x in string.punctuation):
            kinds = kinds + 1
        if any(x in password for x in string.digits):
            kinds = kinds + 1
        if kinds < 2:
            password_complexity_failed = True

        if not password_complexity_failed:
            update_user_profile(username, {'password': password})
            return render_template('status.html', title="重置密码", message="重置密码完成，现在可以返回首页并登录。")

    return render_template('password_reset.html', user_profile=user_profile, Config=Config, password_complexity_failed=password_complexity_failed)

@app.route('/password/forget', methods=['GET', 'POST'])
def password_forget():
    captcha_failed = False
    user_profile = None
    if request.method == "POST":
        captcha_input = request.form['captcha'].upper().encode('utf-8')
        captcha_sig = session.pop('captcha_pf', '')
        if timed_signature.validate(captcha_input, captcha_sig):
            user_profile = get_user_profile({'email': request.form['email'].strip()})
            if user_profile:
                app.logger.info('password forget request: <%s> ok' % request.form['email'].strip())
                reset_key = timed_signature.sign(
                    (user_profile['username'] + ':' + (user_profile['crypt'] or '')).encode('utf-8')
                )
                sendmail([user_profile['email']], 'Niceboat: 密码重置', render_template('password_reset_letter.txt', Config=Config, user_profile=user_profile, reset_key=reset_key))
            else:
                app.logger.info('password forget request: <%s> not found' % (request.form['email'].strip())[0:80])
            return render_template('status.html', title='重置密码', message='如果你是有穿越权，系统已将重置密码的连结发到你的电子邮箱，请注意查收。')
        else:
            captcha_failed = True

    return render_template('password_forget.html', captcha_failed=captcha_failed)

@app.route('/captcha/<id>')
def captcha(id):
    if id is None: abort(500, 'id is not defined')
    if len(id) < 1 or len(id) > 8: abort(500, 'id too long')

    pool = 'ABCEFGHJKLMNPQRTWXYZ234689'
    captcha = ''.join(random.choice(pool) for i in range(4))
    session['captcha_%s' % id] = timed_signature.sign(captcha.encode('utf-8'))
    img = ImageCaptcha().generate(captcha)
    return send_file(img, mimetype='image/png')

import hashlib
import time
import string
import random
import re
import hmac
from config import Config

def _sign(msg, salt, time):
    h = hmac.new(Config.secret, msg=msg, digestmod=hashlib.sha512)
    h.update(('__' + str(time)).encode('utf8'))
    h.update(('__' + salt).encode('utf8'))
    return salt + '/' + h.hexdigest()

def sign(msg, interval=60):
    pool = string.ascii_letters + string.digits
    salt = ''.join(random.choice(pool) for i in range(8))
    return _sign(msg, salt, int(time.time() / interval))

def validate(msg, signature, interval=60, size=5):
    m = re.search("^([^/]+?)/(.+)$", signature)
    if m is None:
        return False
    
    for i in range(size):
        target = _sign(msg, m.group(1), int(time.time() / interval) - i)
        if hmac.compare_digest(signature, target):
            return True
    return False

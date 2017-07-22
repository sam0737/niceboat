import hashlib
import re
import os
import subprocess
import time
import random
import string
import base64
import socket
from config import Config

class SupervisorConfigManager(object):
    def __init__(self, config_path):
        self.config_path = config_path
        pass
                
    @staticmethod
    def _random_string(length):
        pool = string.ascii_letters + string.digits
        return ''.join(random.choice(pool) for i in range(length))


    @staticmethod
    def _hash_username(username):
        return '%s_%s' % (
            re.sub('[^A-Za-z0-9_-]','@',username), 
            hashlib.sha256(username.encode('utf-8')).hexdigest()
        )

    @staticmethod
    def _extract_spec(filename):
        m = re.search(r'^([^\.]+)\.([^\.]+)\.([0-9]{1,8})\.([0-9]+)\.conf$', filename)
        if m is None:
            return None
        passphrase = m.group(2)
        encryption = 'aes-256-cfb'
        if passphrase.startswith("2_"):
            passphrase = passphrase[2::1]
            encryption = 'aes-256-gcm'
        return {
            'safe_username': m.group(1), 
            'encryption': encryption,
            'passphrase': passphrase, 
            'port': int(m.group(3)), 
            'time': int(m.group(4))
        }
    
    def _add_link(self, spec):
        host = Config.host
        # [(s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]
        spec['host'] = host
        spec['url'] = 'ss://' + base64.b64encode(('%s:%s@%s:%s' % (spec['encryption'], spec['passphrase'], host, spec['port'])).encode('utf-8')).decode('utf-8')
        return spec

    def _find_exists(self, username):
        safe_username = self._hash_username(username)
        for filename in os.listdir(self.config_path):
            if filename.startswith(safe_username + '.'):
                yield filename

    def create(self, username):
        links = {'aes_256_cfb': None, 'aes_256_gcm': None}
        for filename in self._find_exists(username):
            spec = self._extract_spec(filename)
            links[spec['encryption'].replace("-","_")] = self._add_link(spec)

        if None in links.values():
            for e in links:
                if links[e] is not None:
                    continue
                if e == 'aes_256_cfb':
                    links[e] = self._create(username, '')
                if e == 'aes_256_gcm':
                    links[e] = self._create(username, '2_')
            self._update()

        return links

    def _create(self, username, prefix=''):
        safe_username = self._hash_username(username)
        used_ports = set()
        for filename in os.listdir(self.config_path):
            s = self._extract_spec(filename)
            if s is None:
                continue
            used_ports |= set([s['port']])

        if len(used_ports) > (Config.port_end - Config.port_start)/2:
            raise RuntimeError('Too many ports are in use')
        while True:
            port = random.randrange(Config.port_start, Config.port_end)
            if port not in used_ports:
                break

        passphrase = self._random_string(8)
        filename = '%s.%s%s.%s.%s.conf' % (safe_username, prefix, passphrase, port, int(time.time()))
        spec = self._extract_spec(filename)
        fullpath = self.config_path + '/' + filename
        with open(fullpath, 'w') as f:
            f.write('''[program:%s_%s]
command=/usr/bin/ss-server -p %s -k %s -m %s
autorestart=true
            ''' % (prefix, spec['safe_username'], spec['port'], spec['passphrase'], spec['encryption']))

        os.chmod(fullpath, 0o600)
        return self._add_link(spec)
        
    def restart(self, username):
        subprocess.check_call(['supervisorctl', 'reread'])
        subprocess.check_call(['supervisorctl', 'restart', self._hash_username(username)])

    def remove(self, username):
        removed = False
        for filename in self._find_exists(username):
            os.remove(self.config_path + '/' + filename)
            removed = True
        if removed: 
            self._update()

    def expire(self):
        update = False
        for filename in os.listdir(self.config_path):
            s = self._extract_spec(filename)
            if s is None:
                continue
            if time.time() - int(s['time']) > Config.exp_day * 86400:
                os.remove(self.config_path + '/' + filename)
                update = True
        if update:
            self._update()

    def _update(self):
        subprocess.check_call(['supervisorctl', 'reread'])
        subprocess.check_call(['supervisorctl', 'update', 'all'])



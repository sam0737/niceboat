import hashlib
import re
import os
import subprocess
import time
import random
import string
import base64
import socket
import uuid
from config import Config

class SupervisorConfigManager(object):
    def __init__(self, config_path):
        self.config_path = config_path
        pass

    @staticmethod
    def _default_links():
        return {'aes_256_gcm': None, 'v2ray': None}
        # return {'aes_256_cfb': None, 'aes_256_gcm': None, 'v2ray': None}

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
        if passphrase.startswith("v2ray_"):
            passphrase = passphrase[6::1]
            encryption = 'v2ray'
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
        if not spec['passphrase'].startswith("v2ray_"):
            spec['url'] = 'ss://' + base64.b64encode(('%s:%s@%s:%s' %
                (spec['encryption'], spec['passphrase'], host, spec['port'])
                ).encode('utf-8')).decode('utf-8')
        return spec

    def _find_exists(self, username):
        safe_username = self._hash_username(username)
        for filename in os.listdir(self.config_path):
            if filename.startswith(safe_username + '.'):
                yield filename

    def _free_port(self):
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
        return port


    def create(self, username):
        links = self._default_links()
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
                if e == 'v2ray':
                    links[e] = self._create(username, 'v2ray_')
            self._update()

        return links

    def _create(self, username, prefix=''):
        safe_username = self._hash_username(username)
        port = self._free_port()
        if prefix.startswith("v2ray_"):
            passphrase  = str(uuid.uuid4())
        else:
            passphrase = self._random_string(8)

        filename = '%s.%s%s.%s.%s.conf' % (safe_username, prefix, passphrase, port, int(time.time()))
        spec = self._extract_spec(filename)

        if prefix.startswith("v2ray_"):
            # V2Ray
            fullpath = self.config_path + '/' + filename
            fullpath_v2ray = self.config_path + '/v2ray/' + filename
            with open(fullpath_v2ray, 'w') as f:
                f.write('''{
"inbounds": [{ "port": %s, "protocol": "vmess", "settings": { "clients": [
{ "id": "%s", "level": 1, "alterId": 64 },
{ "id": "%s", "level": 1, "alterId": 64, "streamSettings": { "network": "mkcp" } } 
] } }],
"outbounds": [{ "protocol": "freedom", "settings": {} }, { "protocol": "blackhole", "settings": {}, "tag": "blocked" }],
"routing": { "strategy": "rules", "settings": { 
    "rules": [ 
        { "type": "field", "outboundTag": "blocked", 
          "ip": [
            "0.0.0.0/8", "10.0.0.0/8", "100.64.0.0/10", "127.0.0.0/8", "169.254.0.0/16", "172.16.0.0/12", "192.0.0.0/24", "192.0.2.0/24",
            "192.168.0.0/16", "198.18.0.0/15", "198.51.100.0/24", "203.0.113.0/24", "::1/128", "fc00::/7", "fe80::/10"
          ]
        } 
    ] } },
"transport": { "kcpSettings": { "uplinkCapacity": 2, "downlinkCapacity": 10 } }
}''' % (spec['port'], spec['passphrase']))
            os.chmod(fullpath_v2ray, 0o600)

            with open(fullpath, 'w') as f:
                f.write('''[program:%s_%s]
command=/usr/local/bin/v2ray -config %s
autorestart=true
                ''' % (prefix, spec['safe_username'], fullpath_v2ray))
            os.chmod(fullpath, 0o600)
        else:
            # Shadowsocks
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
        for filename in os.listdir(self.config_path + '/v2ray'):
            s = self._extract_spec(filename)
            if s is None:
                continue
            if time.time() - int(s['time']) > Config.exp_day * 86400:
                os.remove(self.config_path + '/v2ray/' + filename)
        if update:
            self._update()

    def _update(self):
        subprocess.check_call(['supervisorctl', 'reread'])
        subprocess.check_call(['supervisorctl', 'update', 'all'])



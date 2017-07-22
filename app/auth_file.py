import os
import os.path
import re
from passlib.hash import sha512_crypt as crypt
from fcntl import flock, LOCK_EX, LOCK_SH

filename = 'user.list'

def get_user_profile(filters):
    if len(filters) == 0:
        return None
    if not os.path.exists(filename):
        return None

    with open(filename, 'r') as f:
        flock(f, LOCK_SH)
        for line in f:
            m = re.search('^(.+?):([^:]+?)(?::([^:].+?))?(?::|$)', line.strip())
            if m is not None:
                targets = {
                    'username': m.group(1),
                    'email': m.group(2),
                    'crypt': m.group(3),
                }
                all_match = True
                for k in filters:
                    if k in targets and filters[k] == targets[k]:
                        continue
                    all_match = False
                    break
                if all_match:
                    return targets
    return None

def update_user_profile(username, contents):
    if 'password' in contents:
        contents['crypt'] = crypt.hash(contents.pop('password'))
    found = False
    newline = ''
    with open(filename, 'r+') as f:
        flock(f, LOCK_EX)
        for line in f:
            m = re.search('^(.+?):([^:]+?)(?::([^:].+?))?(?::|$)', line.strip())
            if m is not None and m.group(1) == username:
                targets = {
                    'username': m.group(1),
                    'email': m.group(2),
                    'crypt': m.group(3),
                }
                targets.update(contents)
                newline = newline + ("%s:%s:%s\n" % (targets['username'], targets['email'], targets['crypt']))
                found = True
            else:
                newline = newline + line
        f.seek(0)
        f.truncate(0)
        f.write(newline)

    if not found:
        raise ValueError("No record with username %s found" % username)

def authenticate(username, password):
    p = get_user_profile({'username': username})
    if p is None:
        return False
    return crypt.verify(password, p['crypt'] or '')


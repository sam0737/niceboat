# Shadowsocks多用户自助管理系统 

一个方便用户自助管理V2Ray和Shadowsocks tunnel的Python webapp

# V2Ray/Shadowsocks Multiuser Management System

A simple python webapp for user to self-manage their Shadowsocks tunnel

## Installation

执行以下指令

```
# Install system packages
sudo apt install software-properties-common python-software-properties
sudo add-apt-repository universe
sudo add-apt-repository ppa:max-c-lv/shadowsocks-libev
sudo apt-get update
sudo apt-get install git supervisor nginx shadowsocks-libev virtualenv python3-dev build-essential 
curl -Ls https://install.direct/go.sh | sudo bash

# Install and configure niceboat
git clone https://github.com/sam0737/niceboat niceboat
cd niceboat
virtualenv -p python3 pyenv
source pyenv/bin/activate
pip install -r pyenv.txt
sudo loginctl enable-linger `whoami`
mkdir ~/.config
cp -a systemd ~/.config
sed -i "s|/ROOT_DIR/niceboat|`pwd`|g" `find ~/.config -type f` # To replace the path
systemctl --user daemon-reload
systemctl --user enable niceboat-supervisord.service
systemctl --user enable niceboat-web.service
cp config.sample.py config.py # And modify accordingly
cp user.sample.list user.list # And modify accordingly
systemctl --user start niceboat-supervisord.service
systemctl --user start niceboat-web.service
```

## Nginx Configuration

Assume you are using letsencrypt

```
$ sudo add-apt-repository ppa:certbot/certbot
$ sudo apt-get update
$ sudo apt-get install python-certbot-nginx
```

Place an configuration in sites-available and enable it accordingly (Modify niceboat.example.com as needed)

```
server {
    listen 80;
    server_name niceboat.example.com;
    return 301 https://$host;
}
```

Get the certificate

```
# certbot certonly --nginx -d niceboat.example.com
```

Modify and paste the remaining config (Modify niceboat.example.com as needed)
```
server {
    listen 443 ssl;
    server_name niceboat.example.com;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_certificate /etc/letsencrypt/live/niceboat.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/niceboat.example.com/privkey.pem;

    location / {
        uwsgi_pass 127.0.0.1:8001;
        include /etc/nginx/uwsgi_params;
    }

    add_header Strict-Transport-Security "max-age=7776000; includeSubDomains" always;
    # Check the latest HPKP instruction from your letsencrypt if needed
    # add_header Public-Key-Pins '.............; max-age=7776000; includeSubDomains';
    add_header X-Frame-Options 'SAMEORIGIN';
}
```
```
# /etc/init.d/nginx reload   # reload nginx
```


## Usage

Add users into the `user.list`, and ask them to reset the password through password reset mechanism

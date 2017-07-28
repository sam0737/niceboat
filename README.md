# Shadowsocks多用户自助管理系统 

一个方便用户自助管理Shadowsocks tunnel的Python webapp

# Shadowsocks Multiuser Management System

A simple python webapp for user to self-manage their Shadowsocks tunnel

## Installation

```
$ git clone https://github.com/sam0737/niceboat niceboat
$ cd niceboat
$ pip install -r pyenv.txt
$ sudo add-apt-repository universe
$ sudo add-apt-repository ppa:max-c-lv/shadowsocks-libev
$ sudo apt-get update
$ sudo apt-get install supervisor nginx shadowsocks-libev
$ sudo loginctl enable-linger username
$ mkdir ~/.config
$ cp -a systemd ~/.config
$ systemctl --user daemon-reload
$ systemctl --user enable niceboat-supervisord.service
$ systemctl --user enable　niceboat-web.service
$ cp config.sample.py config.py # And modify accordingly
$ cp user.sample.list user.list # And modify accordingly
$ systemctl --user start niceboat-supervisord.service
$ systemctl --user start niceboat-web.service
```

## Nginx Configuration

Assume you are using letsencrypt


```
$ sudo add-apt-repository ppa:certbot/certbot
$ sudo apt-get update
$ sudo apt-get install python-certbot-nginx
```

Place an configuration in sites-available and enable it accordingly

```
server {
    listen 80;
    server_name niceboat.example.com;
    return 301 https://$host;
}

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
    # Check the latest HPKP instruction from your letsencrypt
    # add_header Public-Key-Pins '.............; max-age=7776000; includeSubDomains';
    add_header X-Frame-Options 'SAMEORIGIN';
}
```

Get the certificate

```
# certbot certonly --nginx -d niceboat.example.com
```

## Usage

Add users into the `user.list`, and ask them to reset the password through password reset mechanism

from smtplib import SMTP

class _Config(object):
    # WAN IP (For Shadowsocks link construction)
    host = 'IP_ADDRESS'
    # URL of the installation
    web_url = 'https://niceboat.example.com'
    # How often will the tunnel expire
    exp_day = 15
    # The free port range of the shadowsocks tunnel
    port_start = 12000
    port_end = 20000
    # Secret for signing cookie, reset key
    secret = b'SOME_LONG_TEXT'
    # SMTP Email settings
    smtp_class = SMTP
    smtp_starttls = True
    smtp_host = 'HOST'
    smtp_port = 587
    smtp_user = 'user@example.com'
    smtp_password = 'PASSWORD'
    smtp_from = 'niceboat_admin@example.com'

Config = _Config()

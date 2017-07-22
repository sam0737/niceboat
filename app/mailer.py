from config import Config
from email.mime.text import MIMEText
import smtplib

def sendmail(tos, subject, text):
    message = """From: %s\nTo: %s\nSubject: %s\n\n%s
    """ % (Config.smtp_from, ", ".join(tos), subject, text)

    msg = MIMEText(text)
    msg['Subject'] = subject
    msg['From'] = Config.smtp_from
    msg['To'] = ", ".join(tos)


    with Config.smtp_class(Config.smtp_host, Config.smtp_port) as server:
        if Config.smtp_starttls and server.starttls()[0] != 220:
            raise smtplib.SMTPException("STARTTLS does not give 220 response")
        server.login(Config.smtp_user, Config.smtp_password)
        server.send_message(msg)


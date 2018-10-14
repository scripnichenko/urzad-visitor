import configparser
import smtplib
from email.mime.text import MIMEText

user_config = configparser.ConfigParser()
user_config.read('data/user.ini')

gmail_user = user_config['gmail']['email']
gmail_password = user_config['gmail']['password']


def send_mail(city, date, time, url):
    sent_from = gmail_user
    to = ['***REMOVED***']
    subject = 'Urzad Bot: I was able to lock a slot for you. Hurry up!!!'
    body = f'I\'ve reserved a slot on date {date} at {time} in {city}.\nHere is the URL for you, my master: {url}'

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sent_from
    msg['To'] = ", ".join(to)

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.ehlo()
        server.login(gmail_user, gmail_password)
        server.send_message(msg)
        server.close()

        print('Email sent!')
    except Exception as e:
        print('Something went wrong...' + str(e))

import configparser
import logging
import logging.config
import smtplib
from email.mime.text import MIMEText

logging.config.fileConfig('logging.conf')  # , disable_existing_loggers=False


class UrzadLocation:

    def __init__(self, loc, app_config, page_main):
        app_config_t = app_config['template']
        app_config_n = app_config['branch_' + loc]

        city_loc = app_config_n['city_loc']
        city_name = app_config_n['city_name']
        city_id = app_config_n['city_id']
        city_queue = app_config_n['city_queue']

        self.city_loc = city_loc
        self.city_name = city_name
        self.city_id = city_id
        self.city_queue = city_queue

        self.page_pol = page_main + app_config_t['page_pol'].format(city_id, city_queue)
        self.page_slot = page_main + app_config_t['page_slot'].format(city_id, '{}')  # there is one {} for 'slot'
        self.page_confirm = page_main + app_config_t['page_confirm'].format(city_id, '{}')  # there is one {} for 'slot'


class Urzad:
    logger = logging.getLogger(__name__)

    app_config = configparser.ConfigParser()
    user_config = configparser.ConfigParser()
    dates_config = configparser.ConfigParser()

    def __init__(self):
        self.app_config.read('urzad.conf')
        self.user_config.read('data/user.ini')

        self.page_main = self.app_config['common']['page_main']
        self.page_login = self.page_main + self.app_config['common']['page_login']
        self.page_lock = self.page_main + self.app_config['common']['page_lock']

        locations_list = self.app_config['common']['branches'].split(',')
        self.all_urzad_locations = [
            UrzadLocation(loc, self.app_config, self.page_main)
            for loc in locations_list
        ]

        self.user_email = self.user_config['user']['email']
        self.user_password = self.user_config['user']['password']

    def save_dates_config(self, dates):
        self.dates_config.read_dict(dates)
        with open('data/dates.ini', 'w+') as configfile:
            self.dates_config.write(configfile)

    def read_dates_config(self):
        self.dates_config.read('data/dates.ini')
        return self.dates_config

    def send_mail(self, city, time, url):
        gmail_user = self.user_config['gmail']['email']
        gmail_password = self.user_config['gmail']['password']

        sent_from = gmail_user
        to = [gmail_user]
        subject = 'Urzad Bot: I was able to lock a slot for you. Hurry up!!!'
        body = f'I\'ve reserved a slot {time} in {city}.\nHere is the URL for you, my master: {url}'

        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = sent_from
        msg['To'] = ', '.join(to)

        try:
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            server.ehlo()
            server.login(gmail_user, gmail_password)
            server.send_message(msg)
            server.close()

            self.logger.info('Email sent!')
        except Exception as e:
            self.logger.debug('Something went wrong...' + str(e))

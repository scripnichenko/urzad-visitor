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
    _logger = logging.getLogger(__name__)

    _app_config = configparser.ConfigParser()
    _user_config = configparser.ConfigParser()
    _dates_config = configparser.ConfigParser()

    def __init__(self):
        self._app_config.read('urzad.conf')
        self._user_config.read('data/user.ini')

        self.page_main = self._app_config['common']['page_main']
        self.page_login = self.page_main + self._app_config['common']['page_login']
        self.page_lock = self.page_main + self._app_config['common']['page_lock']

        locations_list = self._app_config['common']['branches'].split(',')
        self.all_urzad_locations = [
            UrzadLocation(loc, self._app_config, self.page_main)
            for loc in locations_list
        ]

        self.user_email = self._user_config['user']['email']
        self.user_password = self._user_config['user']['password']

        self._gmail_user = self._user_config['gmail']['email']
        self._gmail_password = self._user_config['gmail']['password']

    def save_dates_config(self, dates):
        self._dates_config.read_dict(dates)
        with open('data/dates.ini', 'w+') as configfile:
            self._dates_config.write(configfile)

    def read_dates_config(self):
        self._dates_config.read('data/dates.ini')
        return self._dates_config

    def send_mail(self, city, date, time, url):
        sent_from = self._gmail_user
        to = [self._gmail_user]
        subject = 'Urzad Bot: I was able to lock a slot for you. Hurry up!!!'
        body = f'I\'ve reserved a slot on date {date} at {time} in {city}.\nHere is the URL for you, my master: {url}'

        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = sent_from
        msg['To'] = ', '.join(to)

        try:
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            server.ehlo()
            server.login(self._gmail_user, self._gmail_password)
            server.send_message(msg)
            server.close()

            print('Email sent!')
        except Exception as e:
            print('Something went wrong...' + str(e))

import configparser
import logging
import logging.config
import re
import smtplib
from email.mime.text import MIMEText

logging.config.fileConfig('logging.conf')  # , disable_existing_loggers=False


class UrzadVisitor:
    _logger = logging.getLogger(__name__)

    _app_config = configparser.ConfigParser()
    _user_config = configparser.ConfigParser()
    _dates_config = configparser.ConfigParser()

    def __init__(self):
        self._app_config.read('urzad.conf')
        self._user_config.read('data/user.ini')

        page_main = self._app_config['common']['page_main']
        self.page_main = page_main
        self.page_login = page_main + self._app_config['common']['page_login']
        self.page_lock = page_main + self._app_config['common']['page_lock']

        self.page_pol = page_main + self._app_config['template']['page_pol']
        self.page_slot = page_main + self._app_config['template']['page_slot']
        self.page_comfirm = page_main + self._app_config['template']['page_confirm']

        self.all_page_pol = dict(map(lambda n: (str(n), self.__make_page_pol(str(n))), range(2, 6)))

        self.user_email = self._user_config['user']['email']
        self.user_password = self._user_config['user']['password']

        self._gmail_user = self._user_config['gmail']['email']
        self._gmail_password = self._user_config['gmail']['password']

    def __make_page_pol(self, n):
        locn = 'loc_' + n
        return (self._app_config[locn]['city'], self.page_pol.format(self._app_config[locn]['queue'], self._app_config[locn]['city_id']))

    def attempt(self, func, name, times=25):
        for _ in range(times):
            try:
                return func()
            except Exception as err:
                self._logger.error(f"An exception happened during execution function '{name}': {err}")
                pass
        raise err

    def check_is_logged_in(self, response):
        title = re.findall('<title>.*?</title>', response.text)[0]
        self._logger.debug(title)
        if 'Moje rezerwacje' not in title:
            self._logger.error("Something wrong with your login")
            raise RuntimeError("Not logged in")
        else:
            self._logger.info("Successfully logged in. Go ahead...")

    def save_dates_config(self, dates):
        self._dates_config.read_dict(dates)
        with open("data/dates.ini", 'w+') as configfile:
            self._dates_config.write(configfile)

    def read_dates_config(self):
        self._dates_config.read("data/dates.ini")
        return self._dates_config

    def city_id_and_queue(self, loc):
        return (self._app_config['loc_'+loc]['city_id'], self._app_config['loc_'+loc]['queue'])

    def send_mail(self, city, date, time, url):
        sent_from = self._gmail_user
        to = [self._gmail_user]
        subject = 'Urzad Bot: I was able to lock a slot for you. Hurry up!!!'
        body = f'I\'ve reserved a slot on date {date} at {time} in {city}.\nHere is the URL for you, my master: {url}'

        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = sent_from
        msg['To'] = ", ".join(to)

        try:
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            server.ehlo()
            server.login(self._gmail_user, self._gmail_password)
            server.send_message(msg)
            server.close()

            print('Email sent!')
        except Exception as e:
            print('Something went wrong...' + str(e))

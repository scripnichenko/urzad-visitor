import configparser
import json
import logging
import logging.config
import re
import threading

import requests
import urllib3

urllib3.disable_warnings()

logging.config.fileConfig('logging.conf')  # , disable_existing_loggers=False

app_config = configparser.ConfigParser()
app_config.read('urzad.conf')

page_main = app_config['common']['page_main']
page_login = page_main + app_config['common']['page_login']
page_lock = page_main + app_config['common']['page_lock']

page_pol = page_main + app_config['template']['page_pol']
page_slot = page_main + app_config['template']['page_slot']
page_comfirm = page_main + app_config['template']['page_confirm']


def make_page_pol(n):
    locn = 'loc_' + n
    return (app_config[locn]['city'], page_pol.format(app_config[locn]['queue'], app_config[locn]['city_id']))


all_page_pol = dict(map(lambda n: (str(n), make_page_pol(str(n))), range(2, 6)))

user_config = configparser.ConfigParser()
user_config.read('data/user.ini')

dates_config = configparser.ConfigParser()


def attempt(func, name, logger, times=25):  # TODO move logger to <some> parent class when
    for _ in range(times):
        try:
            return func()
        except Exception as err:
            logger.error(f"An exception happened during execution function '{name}': {err}")
            pass
    raise err


def check_is_logged_in(response, logger):  # TODO move logger to <some> parent class when
    title = re.findall('<title>.*?</title>', response.text)[0]
    logger.debug(title)
    if 'Moje rezerwacje' not in title:
        logger.error("Something wrong with your login")
        raise RuntimeError("Not logged in")
    else:
        logger.info("Successfully logged in. Go ahead...")

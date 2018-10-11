import logging
import logging.config
import threading
import re
import json
import configparser

import requests
import urllib3

urllib3.disable_warnings()

logging.config.fileConfig('logging.conf')  # , disable_existing_loggers=False

app_config = configparser.ConfigParser()
app_config.read('urzad.conf')

page_main = app_config['common']['page_main']
page_login = app_config['common']['page_login']
page_lock = app_config['common']['page_lock']
page_form = app_config['common']['page_form']
page_pol = dict(map(
    lambda n: (str(n), (app_config['loc_' + str(n)]['city'], app_config['loc_' + str(n)]['page_pol'])),
    range(2, 6)
))

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
    page_title = re.findall('<title>.*?</title>', response.text)[0]
    logger.debug(page_title)
    if 'Moje rezerwacje' not in page_title:
        logger.error("Something wrong with your login")
        raise RuntimeError("Not logged in")
    else:
        logger.info("Successfully logged in. Go ahead...")

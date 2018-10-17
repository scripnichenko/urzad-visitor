import configparser
import json
import logging
import logging.config
import re
import threading

import requests
import urllib3

from urzad_common import (all_page_pol, attempt, check_is_logged_in,
                          dates_config, page_login, page_main, user_config)

logger = logging.getLogger('urzadDate')


def get_last_date_from_page(response):
    dates_found = re.findall('var dateEvents = \\[{.*?}\\]', response.text)[0][16:]
    dates_json = json.loads(dates_found)
    return dates_json[-1]['date']


with requests.Session() as session:
    session.headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:62.0) Gecko/20100101 Firefox/62.0'}

    # 1. visit main page (to set up cookies in the session ?)
    session.get(page_main, verify=False)

    # 2. visit login page (post data)
    logger.info("Loggging in...")
    data = {'data[User][email]': user_config['user']['email'], 'data[User][password]': user_config['user']['password']}
    login_response = attempt(lambda: session.post(page_login, data=data, verify=False), 'login', logger)

    # 2a. Check if logged in successfully
    check_is_logged_in(login_response, logger)

    # 3. Parse dates and store to Config :)
    print(all_page_pol)
    for loc, (city, page) in all_page_pol.items():
        print("=======", page)
        logger.debug(f"Parsing dates for location {loc}: {city}...")

        last_date = get_last_date_from_page(session.get(page, cookies={'config[currentLoc]': loc, 'AKIS': session.cookies['AKIS']}, verify=False))
        logger.debug(f"The last date for location {loc}: {city} is === {last_date} ===")

        dates_config['loc_'+loc] = {'city': city, 'date': last_date}

    with open("data/dates.ini", 'w+') as configfile:
        dates_config.write(configfile)

    logger.info("Parsing done. Config saved")


logger.info("Session closed")

import logging
import logging.config
import threading
import re
import json
import configparser

import requests
import urllib3

from urzad_common import *

logger = logging.getLogger('urzadDate')

def get_last_date_from_page(response):
    dates_found = re.findall('var dateEvents = \\[{.*?}\\]', response.text)[0][16:]
    dates_json = json.loads(dates_found)
    return dates_json[-1]['date']


# 0. starting session
session = requests.Session()

# 1. visit main page (to set up cookies in the session ?)
session.get(page_main, verify=False)

# 2. visit login page (post data)
logger.info("Loggging in...")
data = {'data[User][email]': user_config['user']['email'], 'data[User][password]': user_config['user']['password']}
login_response = attempt(lambda: session.post(page_login, data=data, verify=False), 'login', logger)

# 2a. Check if logged in successfully
check_is_logged_in(login_response, logger)

# 3. Parse dates and store to Config :)
for loc, (city, page) in page_pol.items():
    logger.debug(f"Parsing dates for location {loc}: {city}...")

    last_date = get_last_date_from_page(session.get(page, cookies={'config[currentLoc]': loc, 'AKIS': session.cookies['AKIS']}, verify=False))
    logger.debug(f"The last date for location {loc}: {city} is === {last_date} ===")

    dates_config['loc_'+loc] = {'city': city, 'date': last_date}

with open("data/dates.ini", 'w+') as configfile:
    dates_config.write(configfile)

logger.info("Parsing done. Config saved")

import logging
import logging.config
import threading
import re
import json
import configparser

import requests
import urllib3
import AdvancedHTMLParser

from urzad_common import *

logger = logging.getLogger('urzadDate')

def get_available_slots(response, date):
    # print(response.text)
    parser = AdvancedHTMLParser.AdvancedHTMLParser()
    parser.parseStr(response.text)
    slots_found = [date + ' ' + a.text + ':00' for a in parser.getElementsByTagName('a') if a.id != "confirmLink"]
    # print(slots_found)
    return slots_found


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

# 2b. Read dates_config
dates_config.read("data/dates.ini")

def lock_slot(session, loc, city, date, time):
    queue = app_config['loc_'+loc]['queue']

    logger.debug(f"Going to lock slot {time} for {loc}: {city}...")
    response = session.post(page_lock, cookies={'config[currentLoc]':loc,'AKIS':session.cookies['AKIS']}, headers={'X-Requested-With':'XMLHttpRequest'}, verify=False, data={'time': time, 'queue': queue})
    logger.debug(f"Lock response for slot {time} for {loc}: {city} is === {response.text} ===")
    logger.info(response.text)

def get_slots(session, loc, city, page):
    date = dates_config['loc_'+loc]['date']

    logger.debug(f"Get available slots for {loc}: {city} and date {date}...")
    slots = get_available_slots(session.get(page + date, cookies={'config[currentLoc]':loc,'AKIS':session.cookies['AKIS']}, headers={'X-Requested-With':'XMLHttpRequest'}, verify=False), date)
    logger.debug(f"Available slots for {loc}: {city} are === {slots} ===")

    for time in slots:
        t = threading.Thread(target=lambda: lock_slot(session, loc, city, date, time), name=f"SearchSlots-{loc}-{time}")
        t.start()
            


# 3. Parse dates and store to Config :)
while True:
    threads = []
    for loc, (city, page) in page_pol.items():
        # logger.debug(f"Get available slots for {loc}: {city} and date {date}...")
        # slots = get_available_slots(session.get(page + date, cookies={'config[currentLoc]':loc,'AKIS':session.cookies['AKIS']}, headers={'X-Requested-With':'XMLHttpRequest'}, verify=False), date)
        # logger.debug(f"Available slots for {loc}: {city} are === {slots} ===")

        t = threading.Thread(target=lambda: get_slots(session, loc, city, page), name=f"SearchSlots-{loc}")
        t.start()
        threads.append(t)

    for t in threads:
        print(f"joining {t}... ")
        t.join()


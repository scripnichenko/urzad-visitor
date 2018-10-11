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
logger = logging.getLogger('urzadDate')

pattern_dates = re.compile('var dateEvents = \\[{.*?}\\]')
pattern_title = re.compile('<title>.*?</title>')

page_main = 'https://rezerwacje.duw.pl/'
page_login = 'https://rezerwacje.duw.pl/reservations/pol/login'
page_pol = {
    '2': ('Jelenia Góra', 'https://rezerwacje.duw.pl/reservations/pol/queues/102/9/'),
    '3': ('Legnica', 'https://rezerwacje.duw.pl/reservations/pol/queues/95/15/'),
    '4': ('Wałbrzych', 'https://rezerwacje.duw.pl/reservations/pol/queues/96/11/'),
    '5': ('Wrocław', 'http://rezerwacje.duw.pl/reservations/pol/queues/17/1/')
}


def attempt(func, name, times=25):
    for _ in range(times):
        try:
            return func()
        except Exception as err:
            logger.error(f"An exception happened during execution function '{name}': {err}")
            pass
    raise err


def check_is_logged_in(response):
    # parser = AdvancedHTMLParser.AdvancedHTMLParser()
    # parser.parseStr(response.text)
    # print(response.text)
    # page_title = parser.getElementsByTagName('title')[0].text
    page_title = pattern_title.findall(response.text)[0]
    logger.debug(page_title)
    if 'Moje rezerwacje' not in page_title:
        logger.error("Something wrong with your login")
        raise RuntimeError("Not logged in")
    else:
        logger.info("Successfully logged in. Go ahead...")


def get_last_date_from_page(response):
    # parser = AdvancedHTMLParser.AdvancedHTMLParser()
    # parser.parseStr(response.text)
    # script_text = parser.getElementsByTagName('script')[-3].text
    # print(script_text)
    dates_found = pattern_dates.findall(response.text)[0][16:]
    dates_json = json.loads(dates_found)
    return dates_json[-1]['date']


# 0. starting session
session = requests.Session()

# 1. visit main page (to set up cookies in the session ?)
session.get(page_main, verify=False)

# 2. get user data from config
user_config = configparser.ConfigParser()
user_config.read('data/user.ini')

# 2a. visit login page (post data)
logger.info("Loggging in...")
data = {'data[User][email]': user_config['user']['email'], 'data[User][password]': user_config['user']['password']}
login_response = attempt(lambda: session.post(page_login, data=data, verify=False), 'login')

# 2a. Check if logged in successfully
check_is_logged_in(login_response)

# 3. Create config file
dates_config = configparser.ConfigParser()

# 3a. Parse dates and store to Config :)
for loc, (city, page) in page_pol.items():
    logger.debug(f"Parsing dates for location {loc}: {city}... (page: {page})")

    last_date = get_last_date_from_page(session.get(page, cookies={'config[currentLoc]': loc, 'AKIS': session.cookies['AKIS']}, verify=False))
    logger.debug(f"The last date for location {loc}: {city} is === {last_date} ===")

    key = 'loc_'+loc
    dates_config[key] = {}
    dates_config[key]['id'] = loc
    dates_config[key]['city'] = city
    dates_config[key]['date'] = last_date

    # no threads here!
    # t = threading.Thread(target=lambda: print("111"), name=f"ParseDateThread-{city}")
    # t.start()

with open("data/dates.ini", 'w+') as configfile:
    dates_config.write(configfile)


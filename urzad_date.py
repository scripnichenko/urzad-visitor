import json
import logging
import re
import threading

import requests
import urllib3

import urzad

urllib3.disable_warnings()

logger = logging.getLogger('urzadDate')


def parse_available_dates():

    def get_last_date_from_page(response):
        dates_found = re.findall('var dateEvents = \\[{.*?}\\]', response.text)[0][16:]
        dates_json = json.loads(dates_found)
        return dates_json[-1]['date']

    with requests.Session() as session:
        uv = urzad.UrzadVisitor()
        session.headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:62.0) Gecko/20100101 Firefox/62.0'}

        # 1. visit main page (to set up cookies in the session ?)
        session.get(uv.page_main, verify=False)

        # 2. visit login page (post data)
        logger.info("Loggging in...")
        data = {'data[User][email]': uv.user_email, 'data[User][password]': uv.user_password}
        login_response = uv.attempt(lambda: session.post(uv.page_login, data=data, verify=False), 'login')

        # 2a. Check if logged in successfully
        uv.check_is_logged_in(login_response)

        # 3. Parse dates and store to config
        dates = {}
        for (loc, ul) in uv.all_urzad_locations.items():
            logger.debug(f"Parsing dates for location {loc}: {ul.city_name}...")

            last_date = get_last_date_from_page(session.get(ul.page_pol, cookies={'config[currentLoc]': loc, 'AKIS': session.cookies['AKIS']}, allow_redirects=True, verify=False))
            logger.debug(f"The last date for location {loc}: {ul.city_name} is === {last_date} ===")

            dates['loc_'+loc] = {'city': ul.city_name, 'date': last_date}

        uv.save_dates_config(dates)
        logger.info("Parsing done. Config saved")

    logger.info("Session closed")


if __name__ == '__main__':
    parse_available_dates()

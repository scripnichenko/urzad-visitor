import json
import logging
import re
import threading

import AdvancedHTMLParser
import requests
import urllib3

import urzad

urllib3.disable_warnings()


def attempt(func, name, logger, times=5):
    for n in range(times):
        try:
            return func()
        except Exception as err:
            logger.error(f'An exception happened during execution function "{name}": {err}')
            logger.debug(f'Another {n} attempt for "{name}"...')
            pass
    raise err


def check_is_logged_in(response, logger):
    title = re.findall('<title>.*?</title>', response.text)[0]
    logger.debug(title)
    if 'Moje rezerwacje' not in title:
        logger.error('Something wrong with your login')
        raise RuntimeError('Not logged in')
    else:
        logger.info('Successfully logged in. Go ahead...')


def parse_available_dates():
    logger = logging.getLogger('urzadDate')

    def get_last_date_from_page(response):
        dates_found = re.findall('var dateEvents = \\[{.*?}\\]', response.text)[0][16:]
        dates_json = json.loads(dates_found)
        return dates_json[-1]['date']

    with requests.Session() as session:
        uv = urzad.Urzad()
        session.headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:62.0) Gecko/20100101 Firefox/62.0'}

        # 1. visit main page (to set up cookies in the session ?)
        session.get(uv.page_main, verify=False)

        # 2. visit login page (post data)
        logger.info('Loggging in...')
        data = {'data[User][email]': uv.user_email, 'data[User][password]': uv.user_password}
        login_response = attempt(lambda: session.post(uv.page_login, data=data, verify=False), 'login', logger)

        # 2a. Check if logged in successfully
        check_is_logged_in(login_response, logger)

        # 3. Parse dates and store to config
        dates = {}
        for ul in uv.all_urzad_locations:
            logger.debug(f'Parsing dates for location {ul.city_loc}: {ul.city_name}...')

            pol_dates_response = session.get(
                ul.page_pol,
                cookies={'config[currentLoc]': ul.city_loc, 'AKIS': session.cookies['AKIS']},
                allow_redirects=True,
                verify=False
            )
            last_date = get_last_date_from_page(pol_dates_response)

            logger.debug(f'The last date for location {ul.city_loc}: {ul.city_name} is === {last_date} ===')

            dates['branch_'+ul.city_loc] = {'city': ul.city_name, 'date': last_date}

        uv.save_dates_config(dates)
        logger.info('Parsing done. Config saved')

    logger.info('Session closed')


def lock_available_slots():
    logger = logging.getLogger('urzadLock')
    locked_slots = []

    def get_available_slots(response, date):
        # print(response.text)
        parser = AdvancedHTMLParser.AdvancedHTMLParser()
        parser.parseStr(response.text)
        slots_found = [date + ' ' + a.text + ':00' for a in parser.getElementsByTagName('a') if a.id != 'confirmLink']
        # for testing purposes:
        # slots_found = [date + ' ' + a + ':00' for a in [
        #     '10:00', '10:20', '10:40',
        #     '11:00', '11:20', '11:40',
        #     '12:00', '12:20', '12:40',
        #     '12:00', '13:20', '13:40']]
        # print(slots_found)
        return slots_found

    def lock_slot(session, ul, time):
        logger.debug(f'Going to lock slot {time} for {ul.city_loc}: {ul.city_name}...')
        response = session.post(
            uv.page_lock,
            cookies={'config[currentLoc]': ul.city_loc, 'AKIS': session.cookies['AKIS']},
            headers={'X-Requested-With': 'XMLHttpRequest'},
            data={'time': time, 'queue': ul.city_queue},
            verify=False
        )
        logger.debug(f'Lock response for slot {time} for {ul.city_loc}: {ul.city_name} is === {response.text} ===')
        if 'OK ' in response.text:
            slot = response.text[3:]
            if slot not in locked_slots:
                logger.info(f'A slot found: {slot} Sending a email with URL...')
                locked_slots.append(slot)
                # TODO automate it! (later)
                uv.send_mail(ul.city_name, time, ul.page_slot.format(slot))
            else:
                logger.info(f'A slot found: {slot} and was already locked by me. Check email!!!')

    def search_slots(session, ul, date):
        while True: # TDOO add condition to exit the endless loop
            logger.debug(f'Search available slots for {ul.city_loc}: {ul.city_name} and date {date}...')
            
            slots_response = session.get(
                    ul.page_pol + date,
                    cookies={'config[currentLoc]': ul.city_loc, 'AKIS': session.cookies['AKIS']},
                    headers={'X-Requested-With': 'XMLHttpRequest'},
                    verify=False
            )
            slots = get_available_slots(slots_response, date)
            
            logger.debug(f'Available slots for {ul.city_loc}: {ul.city_name} are === {slots} ===')

            threads = []
            for time in slots:
                t = threading.Thread(target=lambda: lock_slot(session, ul, time), name=f'TSlot-{ul.city_loc}-{time[11:16]}')
                t.start()
                threads.append(t)
            
            for t in threads:
                logger.debug(f'...joining {t}... ')
                t.join()

    with requests.Session() as session:
        uv = urzad.Urzad()
        session.headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:62.0) Gecko/20100101 Firefox/62.0'}

        # 1. visit main page (to set up cookies in the session ?)
        session.get(uv.page_main, verify=False)

        # 2. visit login page (post data)
        logger.info('Loggging in...')

        data = {'data[User][email]': uv.user_email, 'data[User][password]': uv.user_password}
        login_response = attempt(lambda: session.post(uv.page_login, data=data, verify=False), 'login', logger)

        # 2a. Check if logged in successfully
        check_is_logged_in(login_response, logger)

        # 2b. Read dates_config
        dates_config = uv.read_dates_config()

        # 3. Parse dates and store to Config :)
        threads = []
        for ul in uv.all_urzad_locations:
            date = dates_config['branch_'+ul.city_loc]['date']

            t = threading.Thread(target=lambda: search_slots(session, ul, date), name=f'TSlot-{ul.city_loc}-srch')
            t.start()
            threads.append(t)

        for t in threads:
            logger.debug(f'...joining {t}... ')
            t.join()

        threads.clear()

    logger.info('Session closed')


if __name__ == '__main__':
    import sys
    if len(sys.argv) >= 2:
        arg = sys.argv[1]
        if arg == 'date':
            parse_available_dates()
        elif arg == 'lock':
            lock_available_slots()
    else:
        print('Use extra argument "date" or "lock"')

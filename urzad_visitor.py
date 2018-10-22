import json
import logging
import re
import threading
from time import sleep

import AdvancedHTMLParser
import requests
import urllib3

import urzad

urllib3.disable_warnings()

logging.config.fileConfig('logging.conf')  # , disable_existing_loggers=False

logger = logging.getLogger('urzadVisitor')


def attempt(func, name, times=5):
    for n in range(times):
        try:
            return func()
        except Exception as err:
            logger.error(f'An exception happened during execution function "{name}": {err}')
            logger.debug(f'Another {n} attempt for "{name}"...')
            pass
    raise err


def parse_available_dates(uv, session):
    def get_last_date_from_page(response):
        dates_found = re.findall('var dateEvents = \\[{.*?}\\]', response.text)[0][16:]
        dates_json = json.loads(dates_found)
        return dates_json[-1]['date']

    dates = {}
    for ul in uv.all_urzad_locations:
        logger.debug(f'Parsing dates for location {ul.city_loc}: {ul.city_name}...')

        pol_dates_response = attempt(lambda: session.get(
            ul.page_pol,
            cookies={'config[currentLoc]': ul.city_loc, 'AKIS': session.cookies['AKIS']},
            allow_redirects=True,
            verify=False
        ), 'get_dates')
        last_date = get_last_date_from_page(pol_dates_response)

        logger.debug(f'The last date for location {ul.city_loc}: {ul.city_name} is === {last_date} ===')

        dates['branch_'+ul.city_loc] = {'city': ul.city_name, 'date': last_date}

    uv.save_dates_config(dates)
    logger.info('Parsing done. Config saved')

    return dates


def try_book_available_slots(uv, session, dates=None):
    lock = threading.RLock()
    locked_slots = []

    def get_available_slots(response, date):
        parser = AdvancedHTMLParser.AdvancedHTMLParser()
        parser.parseStr(response.text)
        slots_found = [date + ' ' + a.text + ':00' for a in parser.getElementsByTagName('a') if a.id != 'confirmLink']
        # for testing purposes:
        # slots_found = [date + ' ' + a + ':00' for a in [
        #     '10:00', '10:20', '10:40',
        #     '11:00', '11:20', '11:40',
        #     '12:00', '12:20', '12:40',
        #     '12:00', '13:20', '13:40']]
        return slots_found

    def lock_slot(session, ul, time):
        logger.debug(f'Going to lock slot {time} for {ul.city_loc}: {ul.city_name}...')
        
        # if not locked_slots:

        lock.acquire()
        logger.debug(f'>> lock_slot() locked by thread {threading.currentThread()}')

        if not locked_slots:
            try:
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
            except Exception:
                pass
        else:
            logger.debug(f'Some slot is already locker. Passing by...')
        
        logger.debug(f'>> lock_slot() released by thread {threading.currentThread()}')
        lock.release()


    def search_slots(session, ul, date):
        while not locked_slots:  # TODO add condition to exit the loop if nothing locked
            # sleep(1) # TODO avoid brute force a bit ?
            logger.debug(f'Search available slots for {ul.city_loc}: {ul.city_name} and date {date}...')

            slots_response = attempt(lambda: session.get(
                ul.page_pol + date,
                cookies={'config[currentLoc]': ul.city_loc, 'AKIS': session.cookies['AKIS']},
                headers={'X-Requested-With': 'XMLHttpRequest'},
                verify=False
            ), 'get_slots')
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

    dates_config = dates or uv.read_dates_config()

    threads = []
    for ul in uv.all_urzad_locations:
        date = dates_config['branch_'+ul.city_loc]['date']

        t = threading.Thread(target=lambda: search_slots(session, ul, date), name=f'TSlot-{ul.city_loc}-srch')
        t.start()
        threads.append(t)

    for t in threads:
        logger.debug(f'...joining {t}... ')
        t.join()


def login_and_check(uv, session):
    def check_is_logged_in(response):
        title = re.findall('<title>.*?</title>', response.text)[0]
        logger.debug(title)
        if 'Moje rezerwacje' not in title:
            logger.error('Something wrong with your login')
            raise RuntimeError('Not logged in')
        else:
            logger.info('Successfully logged in. Go ahead...')

    logger.info('Loggging in...')
    data = {'data[User][email]': uv.user_email, 'data[User][password]': uv.user_password}
    attempt(lambda: check_is_logged_in(session.post(uv.page_login, data=data, verify=False)), 'login_and_check')


def main():
    with requests.Session() as session:
        uv = urzad.Urzad()
        session.headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:62.0) Gecko/20100101 Firefox/62.0'}

        # 1. visit main page (to set up cookies in the session)
        session.get(uv.page_main, verify=False)

        # 2. visit login page (post data) and check if logged in successfully
        login_and_check(uv, session)

        # 3. Parse dates and store to config (one time per run)
        dates = parse_available_dates(uv, session)
        # dates = None # for testing purposes

        # 4. Search available slots and book a reservations
        try_book_available_slots(uv, session, dates)

    logger.info('Session closed')


if __name__ == '__main__':
    main()

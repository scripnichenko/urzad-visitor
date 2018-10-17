import logging
import threading

import AdvancedHTMLParser
import requests
import urllib3

import urzad

urllib3.disable_warnings()

logger = logging.getLogger('urzadDate')

global_locked_slots = []


def try_lock_slots():

    def get_available_slots(response, date):
        # print(response.text)
        parser = AdvancedHTMLParser.AdvancedHTMLParser()
        parser.parseStr(response.text)
        slots_found = [date + ' ' + a.text + ':00' for a in parser.getElementsByTagName('a') if a.id != "confirmLink"]
        # for testing purposes:
        # slots_found = [date + ' ' + a + ':00' for a in [
        #     '10:00', '10:20', '10:40',
        #     '11:00', '11:20', '11:40'
        #     '12:00', '12:20', '12:40',
        #     '12:00', '13:20', '13:40']]
        # print(slots_found)
        return slots_found

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

        # 2b. Read dates_config
        dates_config = uv.read_dates_config()

        def lock_slot(session, loc, city, date, time):
            city_id, queue = uv.city_id_and_queue(loc)

            logger.debug(f"Going to lock slot {time} for {loc}: {city}...")
            response = session.post(
                uv.page_lock,
                cookies={'config[currentLoc]': loc, 'AKIS': session.cookies['AKIS']},
                headers={'X-Requested-With': 'XMLHttpRequest'},
                data={'time': time, 'queue': queue},
                verify=False
            )
            logger.debug(f"Lock response for slot {time} for {loc}: {city} is === {response.text} ===")
            if "OK " in response.text:
                slot = response.text[3:]
                if slot not in global_locked_slots:
                    logger.info(f'A slot found: {slot} Sending a email with URL...')
                    global_locked_slots.append(slot)
                    uv.send_mail(city, date, time, uv.page_slot.format(slot, city_id))
                else:
                    logger.info(f'A slot found: {slot} and was already locked by me. Check email!!!')

        def get_slots(session, loc, city, page):
            date = dates_config['loc_'+loc]['date']

            logger.debug(f"Get available slots for {loc}: {city} and date {date}...")
            slots = get_available_slots(
                session.get(
                    page + date,
                    cookies={'config[currentLoc]': loc, 'AKIS': session.cookies['AKIS']},
                    headers={'X-Requested-With': 'XMLHttpRequest'},
                    verify=False),
                date)
            logger.debug(f"Available slots for {loc}: {city} are === {slots} ===")

            for time in slots:
                t = threading.Thread(target=lambda: lock_slot(session, loc, city, date, time), name=f"SearchSlots-{loc}-{time}")
                t.start()

        # 3. Parse dates and store to Config :)
        while True:
            threads = []
            for loc, (city, page) in uv.all_page_pol.items():
                t = threading.Thread(target=lambda: get_slots(session, loc, city, page), name=f"SearchSlots-{loc}")
                t.start()
                threads.append(t)

            for t in threads:
                logger.debug(f"...joining {t}... ")
                t.join()

            threads.clear()

    logger.info("Session closed")


if __name__ == '__main__':
    try_lock_slots()

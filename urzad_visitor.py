import json
import logging
import logging.config
import re
import shutil
import smtplib
import threading
from email.mime.text import MIMEText
from time import sleep, time
from typing import Callable, Dict, List, TypeVar

import AdvancedHTMLParser  # type: ignore
import pytesseract  # type: ignore
import requests
import urllib3  # type: ignore
from PIL import Image  # type: ignore
from requests import Request, Response, Session

from urzad import ApplicationForm, Urzad, UrzadLocation, UserApplication

urllib3.disable_warnings()
# from http.client import HTTPConnection
# HTTPConnection.debuglevel = 1

logging.config.fileConfig('logging.conf')  # , disable_existing_loggers=False

logger = logging.getLogger('urzadVisitor')

# Some global stuff :)
lock: threading.RLock = threading.RLock()
locked_slots: List[str] = []

T = TypeVar('T')

def attempt(func: Callable[[], T], name: str, times: int = 15) -> T:
    for n in range(times):
        try:
            logger.debug(f'{n+1} Attemt for "{name}"...')
            return func()
        except Exception as err:
            logger.error(f'An exception happened during execution function "{name}": {err}')
            pass
    raise RuntimeError(f'Cannot exec function {name} for {times} times. Giving up...')


def login_and_check(uv: Urzad, session: Session):
    def check_is_logged_in(response: Response):
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


def parse_available_dates(urzad: Urzad, session: Session) -> Dict[str, Dict[str, str]]:
    def get_last_date_from_page(response: Response) -> str:
        dates_found = re.findall('var dateEvents = \\[{.*?}\\]', response.text)[0][16:]
        dates_json = json.loads(dates_found)
        return dates_json[-1]['date']

    dates = {}
    for ul in urzad.user_urzad_locations:
        logger.debug(f'Parsing dates for location {ul.city_loc}: {ul.city_name}...')

        pol_dates_response = attempt(lambda: session.get(
            ul.page_terms,
            cookies={'config[currentLoc]': ul.city_loc},
            allow_redirects=True,
            verify=False
        ), 'get_dates')
        last_date = get_last_date_from_page(pol_dates_response)

        logger.debug(f'The last date for location {ul.city_loc}: {ul.city_name} is === {last_date} ===')

        dates['location_'+ul.city_loc] = {'city': ul.city_name, 'date': last_date}

    urzad.save_dates_config(dates)
    logger.info('Parsing done. Config saved')

    return dates


def try_book_available_slots(urzad: Urzad, session: Session, dates: Dict[str, Dict[str, str]] = None):
    start_time = time()

    def time_is_over() -> bool:
        return time() - start_time >= urzad.run_time

    def get_available_slots(response: Response, date: str) -> List[str]:
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

    def lock_slot(session: Session, ul: UrzadLocation, time: str):
        logger.debug(f'Going to lock slot {time} for {ul.city_loc}: {ul.city_name}...')

        lock.acquire()
        logger.debug(f'>> lock_slot() locked by thread {threading.current_thread()}')

        if not locked_slots:
            try:
                response = session.post(
                    urzad.page_lock,
                    cookies={'config[currentLoc]': ul.city_loc},
                    headers={'X-Requested-With': 'XMLHttpRequest'},
                    data={'time': time, 'queue': ul.city_queue},
                    verify=False
                )
                logger.debug(f'Lock response for slot {time} for {ul.city_loc}: {ul.city_name} is === {response.text} ===')
                if 'OK ' in response.text:
                    slot = response.text[3:]
                    if slot not in locked_slots:
                        logger.info(f'A slot found: {slot}. Start filling the form...')
                        locked_slots.append(slot)
                        fill_the_form(urzad, ul, slot, time, session)
                    else:
                        logger.info(f'A slot found: {slot} and was already locked by me. Check email!!!')
            except Exception as err:
                logger.error(f'Something wrong with locking slots: {err}')
                pass
        else:
            logger.debug(f'Some slot is already locker. Passing by...')

        logger.debug(f'>> lock_slot() released by thread {threading.current_thread()}')
        lock.release()

    def search_slots(session: Session, ul: UrzadLocation, date: str):
        while not locked_slots and not time_is_over():
            sleep(1)  # TODO avoid brute force a bit ?
            logger.debug(f'Search available slots for {ul.city_loc}: {ul.city_name} and date {date}...')

            slots_response = attempt(lambda: session.get(
                ul.page_pol_date.format(date),
                cookies={'config[currentLoc]': ul.city_loc},
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

    dates_config = dates or urzad.read_dates_config()

    threads: List[threading.Thread] = []
    for ul in urzad.user_urzad_locations:
        date = dates_config['location_'+ul.city_loc]['date']

        t = threading.Thread(target=lambda: search_slots(session, ul, date), name=f'TSlot-{ul.city_loc}-srch')
        t.start()
        threads.append(t)
        sleep(1)  # small delay before starting next thread

    for t in threads:
        logger.debug(f'...joining {t}... ')
        t.join()


def fill_the_form(urzad: Urzad, ul: UrzadLocation, slot: str, time: str, session: Session):
    def solve_captcha(image_path: str) -> str:
        initial_im = Image.open(image_path).convert('P')
        cleaned_im = Image.new('P', initial_im.size, 255)

        for x in range(initial_im.size[1]):
            for y in range(initial_im.size[0]):
                pix = initial_im.getpixel((y, x))
                if pix >= 2:
                    cleaned_im.putpixel((y, x), 0)

        return pytesseract.image_to_string(image=cleaned_im, config='--psm 7 -c tessedit_char_whitelist=0123456789')

    # 1. Get captcha
    logger.debug(f'Obtaining captcha...')
    captcha_response = attempt(lambda: session.get(
        urzad.page_captcha,
        cookies={'config[currentLoc]': ul.city_loc},
        stream=True,
        verify=False
    ), 'captcha')

    captcha_path = 'data/captcha.png'
    with open(captcha_path, 'wb') as out_file:
        shutil.copyfileobj(captcha_response.raw, out_file)
    captcha_response.close()
    del captcha_response

    logger.debug(f'Obtained! Solving captcha...')
    captcha_text = solve_captcha(captcha_path)
    logger.debug(f'Captcha solved: {captcha_text}. Posting')

    # 2. Verify captcha
    captcha_check_response = attempt(lambda: session.post(
        urzad.page_captcha + '/check',
        cookies={'config[currentLoc]': ul.city_loc},
        headers={'X-Requested-With': 'XMLHttpRequest'},
        data={'code': captcha_text},
        verify=False
    ), 'captcha_check')

    if captcha_check_response.text != 'true':
        logger.info(f'Captcha solved wrong: {captcha_text}... Start again!')
        locked_slots.clear()
        return

    logger.info(f'Captcha solved, posting the user data...')

    # 3. Fill user form
    user_data = prepare_user_data(urzad)
    fill_form_response = attempt(lambda: session.post(
        ul.page_slot.format(slot),
        cookies={'config[currentLoc]': ul.city_loc},
        headers={'X-Requested-With': 'XMLHttpRequest', 'contentType': 'application/json; charset=utf-8'},
        json=user_data,
        verify=False
    ), 'fill_form')

    if fill_form_response.status_code != 200:
        logger.info(f'Could not fill the form, status code: {fill_form_response.status_code}... Start again!')
        locked_slots.clear()
        return

    logger.info(f'Data posted, confirming the link...')

    # 3. Confirm form
    confirm_form_response = attempt(lambda: session.get(
        ul.page_confirm.format(slot),
        cookies={'config[currentLoc]': ul.city_loc},
        allow_redirects=False,
        verify=False
    ), 'fill_form')

    if confirm_form_response.status_code != 302 or slot not in confirm_form_response.headers['Location']:
        logger.info(f'Could not confirm the form, status code: {confirm_form_response.status_code} (location: {confirm_form_response.headers["Location"]})... ')
        logger.info('Start again!')
        locked_slots.clear()
        return

    send_mail(urzad, ul.city_name, time)


def prepare_user_data(urzad: Urzad) -> List[Dict[str, str]]:

    def name_value(name: str, value: str) -> Dict[str, str]:
        return {'name': name, 'value': value}

    def app_additional_text(app_form: ApplicationForm, a: str):
        if a == 'spouse':
            return app_form.additional_spouse_text
        elif a == 'child':
            return app_form.additional_child_text
        elif a == 'children':
            return app_form.additional_children_text
        else:
            pass

    app_form = ApplicationForm()
    user_app = UserApplication()

    if user_app.type == 'temporary':
        type_text = app_form.type_temporary_text
    elif user_app.type == 'permanent':
        type_text = app_form.type_permanent_text
    else:
        raise ValueError(f'Wrong type "{user_app.type}" specified')

    user_data: List[Dict[str, str]] = [
        name_value(app_form.type, type_text),
        name_value(app_form.surname_name, user_app.surname_name),
        name_value(app_form.citizenship, user_app.citizenship),
        name_value(app_form.birth_date, user_app.birth_date),
        name_value(app_form.telephone, user_app.telephone),
        name_value(app_form.passport, user_app.passport),
        name_value(app_form.visa_karta, user_app.visa_karta),
        name_value(app_form.gdpr, app_form.gdpr_text)
    ]

    if not user_app.additional_list:
        additional_data_list = [name_value(app_form.additional, app_form.additional_empty_text)]
    else:
        additional_data_list = [name_value(app_form.additional, app_additional_text(app_form, a)) for a in user_app.additional_list]

    user_data.extend(additional_data_list)

    logger.debug("=============== USER DATA")
    logger.debug(json.dumps(user_data, ensure_ascii=False))
    return user_data


def send_mail(urzad: Urzad, city: str, time: str):
    gmail_user = urzad.user_config['gmail']['email']
    gmail_password = urzad.user_config['gmail']['password']

    sent_from = gmail_user
    to = [gmail_user]
    subject = 'Urzad Visitor has visited a location (successfully?)'
    body = f'I hope I\'ve reserved a slot {time} in {city}.\nCheck on site.\nPrepare you documents in time in successfull case :)'

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sent_from
    msg['To'] = ', '.join(to)

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.ehlo()
        server.login(gmail_user, gmail_password)
        server.send_message(msg)
        server.close()

        logger.info('Email sent!')
    except Exception as e:
        logger.debug('Something went wrong...' + str(e))


def main():
    with requests.Session() as session:
        uv = Urzad()
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

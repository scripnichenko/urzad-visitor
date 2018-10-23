import configparser


class UrzadLocation:

    def __init__(self, loc, app_config, page_main):
        app_config_t = app_config['template']
        app_config_n = app_config['location_' + loc]

        city_loc = app_config_n['city_loc']
        city_name = app_config_n['city_name']
        city_id = app_config_n['city_id']
        city_queue = app_config_n['city_queue']

        self.city_loc = city_loc
        self.city_name = city_name
        self.city_id = city_id
        self.city_queue = city_queue

        self.page_pol = page_main + app_config_t['page_pol'].format(city_id, city_queue)
        self.page_slot = page_main + app_config_t['page_slot'].format(city_id, '{}')  # there is one {} for 'slot'
        self.page_confirm = page_main + app_config_t['page_confirm'].format(city_id, '{}')  # there is one {} for 'slot'

    def __repr__(self):
        return f'{self.city_loc}: {self.city_name} ({self.city_queue}/{self.city_id})'


class Urzad:
    app_config = configparser.ConfigParser()
    user_config = configparser.ConfigParser()
    dates_config = configparser.ConfigParser()

    def __init__(self):
        self.app_config.read('urzad.conf')
        self.user_config.read('data/user.ini')

        app_common = self.app_config['common']
        user_common = self.user_config['user']

        self.page_main = app_common['page_main']
        self.page_login = self.page_main + app_common['page_login']
        self.page_lock = self.page_main + app_common['page_lock']
        self.page_captcha = self.page_main + app_common['page_captcha']

        all_locations_list = app_common['locations'].split(',')
        if 'locations' in user_common.keys():
            user_locations_list = user_common['locations'].split(',')
        else:
            user_locations_list = all_locations_list

        self.all_urzad_locations = [
            UrzadLocation(loc, self.app_config, self.page_main)
            for loc in all_locations_list
        ]
        self.user_urzad_locations = [u for u in self.all_urzad_locations if u.city_loc in user_locations_list]

        self.user_email = user_common['email']
        self.user_password = user_common['password']

    def save_dates_config(self, dates):
        self.dates_config.read_dict(dates)
        with open('data/dates.ini', 'w+') as configfile:
            self.dates_config.write(configfile)

    def read_dates_config(self):
        self.dates_config.read('data/dates.ini')
        return self.dates_config


class ApplicationForm:
    app_config = configparser.ConfigParser()

    def __init__(self):
        self.app_config.read('urzad.conf')
        app_form = self.app_config['application_form']
        app_form_values = self.app_config['application_values']

        self.type = app_form['type']
        self.surname_name = app_form['surname_name']
        self.citizenship = app_form['citizenship']
        self.birth_date = app_form['birth_date']
        self.telephone = app_form['telephone']
        self.passport = app_form['passport']
        self.visa_karta = app_form['visa_karta']
        self.additional = app_form['additional']
        self.gdpr = app_form['gdpr']

        self.type_temporary_text = app_form_values['type_temporary_text']
        self.type_permanent_text = app_form_values['type_permanent_text']
        self.additional_spouse_text = app_form_values['additional_spouse_text']
        self.additional_child_text = app_form_values['additional_child_text']
        self.additional_children_text = app_form_values['additional_children_text']
        self.additional_empty_text = app_form_values['additional_empty_text']
        self.gdpr_text = app_form_values['gdpr_text']


class UserApplication:
    user_config = configparser.ConfigParser()

    def __init__(self):
        self.user_config.read('data/user.ini')
        user_application = self.user_config['application']

        self.type = user_application['type']
        self.surname_name = user_application['surname_name']
        self.citizenship = user_application['citizenship']
        self.birth_date = user_application['birth_date']
        self.telephone = user_application['telephone']
        self.passport = user_application['passport']
        self.visa_karta = user_application['visa_karta']
        self.additional_list = user_application['additional'].split(',')

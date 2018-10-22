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

        self.page_main = self.app_config['common']['page_main']
        self.page_login = self.page_main + self.app_config['common']['page_login']
        self.page_lock = self.page_main + self.app_config['common']['page_lock']
        self.page_captcha = self.page_main + self.app_config['common']['page_captcha']

        all_locations_list = self.app_config['common']['locations'].split(',')
        if 'locations' in self.user_config['user'].keys():
            user_locations_list = self.user_config['user']['locations'].split(',')
        else:
            user_locations_list = all_locations_list

        self.all_urzad_locations = [
            UrzadLocation(loc, self.app_config, self.page_main)
            for loc in all_locations_list
        ]
        self.user_urzad_locations = [u for u in self.all_urzad_locations if u.city_loc in user_locations_list]

        self.user_email = self.user_config['user']['email']
        self.user_password = self.user_config['user']['password']

    def save_dates_config(self, dates):
        self.dates_config.read_dict(dates)
        with open('data/dates.ini', 'w+') as configfile:
            self.dates_config.write(configfile)

    def read_dates_config(self):
        self.dates_config.read('data/dates.ini')
        return self.dates_config

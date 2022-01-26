import json
import os
import re
import threading
import time
import urllib.parse
from sys import platform

import requests
from bs4 import BeautifulSoup as bs
from selenium import webdriver
from selenium.common.exceptions import MoveTargetOutOfBoundsException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.firefox.options import Options


class AppsFinder:
    found_apps = []
    lang = 'ru'

    def __init__(self, keyword, write_result):
        self.keyword = keyword
        self.write_result = write_result
        if len(keyword) > 0:
            options_headless = Options()
            options_headless.add_argument('--headless')
            url = f'https://play.google.com/store/search?q={urllib.parse.quote_plus(keyword)}&c=apps&gl={self.lang}&hl={self.lang}'
            driver = None
            try:
                print('Collecting information about apps...')
                absFilePath = os.path.abspath(__file__)
                path, filename = os.path.split(absFilePath)
                driver_name = ''
                if platform == "linux" or platform == "linux2":
                    driver_name = f"{path}/geckodriver"
                elif platform == "darwin":
                    driver_name = f"{path}/geckodriver.m"
                elif platform == "win32":
                    f"{path}/geckodriver.exe"
                driver = webdriver.Firefox(desired_capabilities=DesiredCapabilities().FIREFOX,
                                           executable_path=driver_name,
                                           options=options_headless)
                driver.implicitly_wait(2)  # seconds
                driver.get(url)
                time.sleep(5)
                footer_el = driver.find_element('class name', 'BDUOnf')
                y_position = 0

                while True:
                    try:
                        ActionChains(driver).move_to_element(footer_el).perform()
                        break
                    except MoveTargetOutOfBoundsException:
                        y_position += 500
                        driver.execute_script(f'window.scrollTo(0, {y_position});')
                        time.sleep(1)

            finally:
                if driver:
                    self.scan(page_source=driver.page_source)
                    driver.quit()

    def scan(self, page_source):
        print('Scanning every found app....')
        soup = bs(page_source, "html.parser")
        soup.decode(True)
        apps = soup.find_all('div', 'Vpfmgd')
        for app in apps:
            app_name = app.find_next('div', 'WsMG1c nnK0zc').text
            app_url = f'https://play.google.com{app.find_next("div", "b8cIId ReQCgd Q9MA7b").find_next("a")["href"]}'
            app_model = GoogleAppModel(app_name=app_name, url=app_url)
            self.found_apps.append(app_model)
            threading.Thread(target=self.find_app_info, args=[app_model]).start()
        while threading.active_count() > 1:
            time.sleep(1)
        if self.write_result:
            with open('result.txt', 'w') as result_file:
                result_file.write(json.dumps(self.found_apps, cls=AppEncoder, ensure_ascii=False))
                result_file.close()
        else:
            print(json.dumps(self.found_apps, cls=AppEncoder, ensure_ascii=False))

    def find_app_info(self, google_app_model):
        url = google_app_model.url
        r = requests.get(url=f'{url}&gl={self.lang}&hl={self.lang}')
        if r.status_code == 200:
            self.get_app_name(html_text=r.text, google_app_model=google_app_model)
            self.get_app_author(html_text=r.text, google_app_model=google_app_model)
            self.get_app_description(html_text=r.text, google_app_model=google_app_model)
            if self.check_keyword(google_app_model=google_app_model):
                self.get_app_last_update(html_text=r.text, google_app_model=google_app_model)
                self.get_app_raiting(html_text=r.text, google_app_model=google_app_model)
                self.get_app_raitings_counter(html_text=r.text, google_app_model=google_app_model)

    def get_app_raitings_counter(self, html_text, google_app_model, attempt=0):
        if attempt < 2:
            soup = bs(html_text, "html.parser")
            raitings_num = soup.find_all('span', 'AYi5wd TBRnV')
            if raitings_num is not None and len(raitings_num) > 0:
                raitings_text = raitings_num[0].find_next('span').text
                google_app_model.raitings_num = ''
                for letter in raitings_text:
                    if letter.isdigit():
                        google_app_model.raitings_num = google_app_model.raitings_num + letter
            if len(google_app_model.raitings_num) <= 0 or google_app_model.raitings_num == 'no':
                attempt += 1
                if self.lang == 'ru':
                    r = requests.get(url=f'{google_app_model.url}&gl=us&hl=us')
                    self.get_app_raitings_counter(html_text=r.text, google_app_model=google_app_model, attempt=attempt)
                elif self.lang == 'us':
                    r = requests.get(url=f'{google_app_model.url}&gl=ru&hl=ru')
                    self.get_app_raitings_counter(html_text=r.text, google_app_model=google_app_model, attempt=attempt)

    def get_app_raiting(self, html_text, google_app_model, attempt=0):
        if attempt < 2:
            soup = bs(html_text, "html.parser")
            raiting_bar = soup.find_all('div', 'jdjqLd')
            if raiting_bar is not None and len(raiting_bar) > 0:
                average_raiting = raiting_bar[0].find_next('div', 'pf5lIe')
                if average_raiting is not None and len(average_raiting) > 0:
                    google_app_model.average_raiting = float(
                        re.findall(r"\d+\.\d+", average_raiting.find_next('div')['aria-label'].replace(',', '.'))[0])
                if google_app_model.average_raiting == -1:
                    attempt += 1
                    if self.lang == 'ru':
                        r = requests.get(url=f'{google_app_model.url}&gl=en&hl=en')
                        self.get_app_raiting(html_text=r.text, google_app_model=google_app_model, attempt=attempt)
                    elif self.lang == 'us':
                        r = requests.get(url=f'{google_app_model.url}&gl=ru&hl=ru')
                        self.get_app_raiting(html_text=r.text, google_app_model=google_app_model, attempt=attempt)

    def get_app_last_update(self, html_text, google_app_model):
        soup = bs(html_text, "html.parser")
        google_app_model.last_update = soup.find_all('div', 'JHTxhe IQ1z0d')[1].find_next('div', 'IQ1z0d').find('span',
                                                                                                                'htlgb').text

    def get_app_category(self, soup_part, google_app_model):
        google_app_model.category = soup_part[1].text

    def get_app_description(self, html_text, google_app_model):
        soup = bs(html_text, "html.parser")
        google_app_model.description = soup.find_all('div', 'DWPxHb')[0].find_next('span').text

    def get_app_author(self, html_text, google_app_model):
        soup = bs(html_text, "html.parser")
        app_info = soup.find_all('a', 'hrTbp R8zArc')
        if app_info is not None and len(app_info) > 1:
            google_app_model.author = soup.find_all('a', 'hrTbp R8zArc')[0].text
            self.get_app_category(soup_part=app_info, google_app_model=google_app_model)

    def get_app_name(self, html_text, google_app_model):
        soup = bs(html_text, "html.parser")
        google_app_model.app_name = soup.find_all('h1', 'AHFaub')[0].find_next('span').text

    def check_keyword(self, google_app_model):
        keywords = self.keyword.split(' ')
        result = False
        for word in keywords:
            word = word.lower()
            if word not in google_app_model.app_name.lower() and word not in google_app_model.description.lower() and word not in google_app_model.app_name.lower():
                self.found_apps.remove(google_app_model)
                result = False
                return result
            else:
                result = True
                return result
        return result


class GoogleAppModel:
    def __init__(self, app_name, url, author='', category='', description='', average_raiting=-1.0, raitings_num='no',
                 last_update=''):
        self.app_name = app_name
        self.url = url
        self.author = author
        self.category = category
        self.description = description
        self.average_raiting = average_raiting
        self.raitings_num = raitings_num
        self.last_update = last_update


class AppEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, GoogleAppModel):
            return obj.__dict__
        return json.JSONEncoder.default(self, obj)

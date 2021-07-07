import re
import time
import json
from configparser import ConfigParser

import pandas as pd
from openpyxl import Workbook, load_workbook
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import telegram_module


class Egrn_Handler():
    def __init__(self):
        self.egrn_driver = None
        self.last_request_time = time.time()
        self.current_auth_key = None

    def init_driver(self, auth_key):
        chrome_options = Options()
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
        self.egrn_driver = webdriver.Chrome(options = chrome_options)
        self.egrn_driver.set_page_load_timeout(30)
        self.egrn_driver.get("https://rosreestr.gov.ru/wps/portal/p/cc_present/ir_egrn")
        DemoKey = WebDriverWait(self.egrn_driver, 10).until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(),'6F9619FF-8B86-D011-B42D-00CF4FC964FF')]")))
        self.egrn_driver.implicitly_wait(30)
        self.auth_key = auth_key

    def request_document(self, text, chat_id, egrp=False):
        try:
            if self.auth_key_dict[chat_id] != self.current_auth_key:
                self.init_driver(self.auth_key_dict[chat_id])
        except:
            telegram_module.send_message(chat_id, "Ключ ФГИС ЕГРН не найден, введите ключ.")

eh = Egrn_Handler()

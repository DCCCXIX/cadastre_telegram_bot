import time

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import data_handler_module


class Egrn_Handler:
    def __init__(self):
        self.egrn_driver = None
        self.last_request_time = time.time()
        self.current_auth_key = None

    def init_driver(self, auth_key):
        # chrome_options = Options()
        # chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
        # self.egrn_driver = webdriver.Chrome(options=chrome_options)
        # self.egrn_driver.set_page_load_timeout(30)
        # self.egrn_driver.get("https://rosreestr.gov.ru/wps/portal/p/cc_present/ir_egrn")
        # DemoKey = WebDriverWait(self.egrn_driver, 10).until(
        #     EC.presence_of_element_located((By.XPATH, "//*[contains(text(),'6F9619FF-8B86-D011-B42D-00CF4FC964FF')]"))
        # )
        # self.egrn_driver.implicitly_wait(30)
        self.auth_key = auth_key

    def check_key(self):
        self.egrn_driver.get("https://rosreestr.gov.ru/wps/portal/p/cc_present/ir_egrn")

    def request_document(self, cad_number, chat_id, egrp=False):
        if self.current_auth_key is None or data_handler_module.dh.auth_key_dict[str(chat_id)] != self.current_auth_key:
            self.init_driver(data_handler_module.dh.auth_key_dict[str(chat_id)])

        # some selenium fuckery here #
        egrn_request_id = "80-0000000"

        return egrn_request_id


def egrn_proccess():
    eh = Egrn_Handler()
    while True:
        time.sleep(10)
        if len(data_handler_module.dh.request_table) > 0:
            for row in data_handler_module.dh.request_table.iterrows():
                row = row[1]
                request_id = row["Request_Id"]
                cad_number = row["Кадастровый номер"]
                excerpt_type = row["Тип выписки"]
                chat_id = row["Chat Id"]

                egrn_request_id = eh.request_document(cad_number, chat_id, excerpt_type)

                if egrn_request_id == None:
                    continue
                elif egrn_request_id == "Not found":
                    data_handler_module.dh.request_table = data_handler_module.dh.request_table[
                        data_handler_module.dh.request_table["Request_Id"] != request_id
                    ]
                else:
                    row["Номер запроса"] = egrn_request_id
                    data_handler_module.dh.completed_request_table = (
                        data_handler_module.dh.completed_request_table.append(row, ignore_index=True)
                    )
                    data_handler_module.dh.request_table = data_handler_module.dh.request_table[
                        data_handler_module.dh.request_table["Request_Id"] != request_id
                    ]
                    data_handler_module.dh.request_table.to_csv(
                        "request_table.xls", index=False, encoding="windows-1251"
                    )

                    data_handler_module.dh.completed_request_table.to_csv(
                        "completed_request_table.xls", index=False, encoding="windows-1251"
                    )
        else:
            pass
            # more selenium fuckery here #

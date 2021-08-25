import base64
import io
import logging
import os
import re
import shutil
import sqlite3 as sql
import sys
import time

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import data_handler_module
import rest_module
import telegram_module

logging.getLogger().setLevel(logging.INFO)


class Egrn_Handler:
    def __init__(self):
        # tracking last request time since only 1 request per 5 minutes is possible
        # should have different timers for different auth keys later
        self.last_request_time = 0
        self.current_auth_key = None
        self.driver_path = "webdriver/chromedriver.exe"
        self.download_dir_path = f"{os.path.dirname(os.path.abspath(sys.argv[0]))}\\completed_requests"
        self.egrn_driver = None

    # init driver for a new account and auth
    def init_driver(self, auth_key):
        if self.current_auth_key == auth_key and self.egrn_driver is not None:
            # if auth key is the same - go back to the initial egrn screen
            logging.info("Proccessing request for the same auth key")
            self.egrn_driver.get("https://rosreestr.gov.ru/wps/portal/p/cc_present/ir_egrn")
            try:
                # sometimes it's needed to reauth despite using the same key
                self.egrn_driver.implicitly_wait(3)
                auth_field = self.egrn_driver.find_element_by_css_selector("#v-Z7_01HA1A42KODT90AR30VLN22003")
                auth_field = auth_field.find_elements_by_xpath(".//input[@type='text']")[0]
                auth_field.send_keys("5c696d08-12f1-4e41-8836-794038d516f2")
            except:
                pass

        else:
            # if it differs - init a new driver with a new key, close the old one and auth
            if self.egrn_driver is not None:
                self.egrn_driver.close()
                self.egrn_driver.quit()

            self.current_auth_key = auth_key

            chrome_options = Options()
            prefs = {"download.default_directory": self.download_dir_path}
            chrome_options.add_experimental_option("prefs", prefs)
            chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

            self.egrn_driver = webdriver.Chrome(executable_path=self.driver_path, options=chrome_options)
            self.egrn_driver.set_page_load_timeout(20)

            try:
                self.egrn_driver.get("https://rosreestr.gov.ru/wps/portal/p/cc_present/ir_egrn")
                self.egrn_driver.implicitly_wait(5)

                auth_field = self.egrn_driver.find_element_by_css_selector("#v-Z7_01HA1A42KODT90AR30VLN22003")
                auth_field = auth_field.find_elements_by_xpath(".//input[@type='text']")[0]

                auth_field.send_keys("5c696d08-12f1-4e41-8836-794038d516f2")

                logging.info("Auth page loaded")
            except:
                logging.info("Failed to load auth page, retrying")
                time.sleep(5)

            enter_button = self.egrn_driver.find_element_by_xpath(
                ".//span[contains(@class,'v-button-caption') and contains(text(),'Войти')]"
            ).click()

            try:
                bad_key = self.egrn_driver.find_element_by_xpath(
                    "//div[@class='gwt-HTML' and text()='Неверный ключ доступа.']"
                )
                if bad_key is not None:
                    logging.info("Failed to auth, bad key")
                    return False
            except:
                logging.info("Auth successful")
                return True

    # check if any egrn requests are completed and download
    def download_excerpt(self, chat_id):
        logging.info("Loading request page")

        with sql.connect("request_data.db") as con:
            cursor = con.cursor()
            query = """SELECT request_id_egrn
                        FROM requests
                        WHERE files_path IS NULL
                        AND chat_id = ?"""
            values = (chat_id,)
            cursor.execute(query, values)
            excerpts_to_check = cursor.fetchall()
            excerpts_to_check = [item[0] for item in excerpts_to_check]

        auth_key = data_handler_module.dh.auth_key_dict[chat_id]
        self.init_driver(auth_key)
        requests_button = self.egrn_driver.find_element_by_xpath(
            ".//span[contains(@class,'v-button-caption') and contains(text(),'Мои заявки')]"
        )
        requests_button.click()
        try:
            dl_image = self.egrn_driver.find_element_by_xpath(".//img[contains(@src, 'btn_first_na.gif')]")
            logging.info("Requests page loaded")
        except:
            logging.info("Failed to load request page")

        table = self.egrn_driver.find_element_by_css_selector("table.v-table-table")
        for tr in table.find_elements_by_css_selector("tr"):
            request_id_egrn = tr.find_elements_by_css_selector("td")[0].get_attribute("innerText")
            request_date = tr.find_elements_by_css_selector("td")[1].get_attribute("innerText")
            # request_date = datetime.strptime(request_date[:10], "%d.%m.%Y")
            request_status = tr.find_elements_by_css_selector("td")[2].get_attribute("innerText")
            download_link = tr.find_elements_by_css_selector("td")[3].find_elements_by_css_selector("a")
            files_path = None

            if request_id_egrn in excerpts_to_check:
                if len(download_link) > 0:
                    download_link[0].click()
                    files_path = f"./completed_requests/Response-{request_id_egrn}.zip"

                    with sql.connect("request_data.db") as con:
                        cursor = con.cursor()
                        query = """UPDATE requests
                                SET request_date = ?,
                                    request_status = ?,
                                    files_path = ?
                                WHERE request_id_egrn = ?"""
                        values = (request_date, request_status, files_path, request_id_egrn)
                        cursor.execute(query, values)
                        try:
                            shutil.move(
                                f"{self.download_dir_path}/Response-{request_id_egrn}.zip",
                                f"./completed_requests/{request_id_egrn}/Response-{request_id_egrn}.zip",
                            )
                        except Exception as e:
                            logging.info(e)
                            continue

    # check for an amount of paid requests left
    def check_accounts(self, chat_id):
        logging.info("Loading accounts page")
        auth_key = data_handler_module.dh.auth_key_dict[chat_id]
        self.init_driver(auth_key)
        accounts_button = self.egrn_driver.find_element_by_xpath(
            ".//span[contains(@class,'v-button-caption') and contains(text(),'Мои счета')]"
        )
        accounts_button.click()
        try:
            paid_requests_left = self.egrn_driver.find_element_by_class_name(
                "v-table-cell-content.v-table-cell-content-objects_num"
            )
            paid_requests_left = int(paid_requests_left.text)
            logging.info("Accounts page loaded")
        except:
            paid_requests_left = None
            logging.info("Failed to load accounts page")

        return paid_requests_left

    def request_excerpt(self, cad_number, chat_id, excerpt_type=0):
        def solve_captcha():
            # finds captcha, recognizes it and inputs into the respective field
            captcha = self.egrn_driver.find_element_by_xpath("//img[@style='width: 180px; height: 50px;']")
            time.sleep(2)
            img_base64 = self.egrn_driver.execute_script(
                """
                    var ele = arguments[0];
                    var cnv = document.createElement('canvas');
                    cnv.width = 180;
                    cnv.height = 50;
                    cnv.getContext('2d').drawImage(ele, 0, 0);
                    return cnv.toDataURL('image/png').substring(22);
                """,
                captcha,
            )

            image = base64.b64decode(img_base64)
            image = io.BytesIO(image)
            solved_captcha = rest_module.mh.predict(image)

            captcha_input_field = self.egrn_driver.find_element_by_xpath(
                "//input[@class='v-textfield v-textfield-srv-field srv-field']"
            )

            captcha_input_field.click()
            captcha_input_field.send_keys(solved_captcha)

        def finish_request():
            # click send request button
            self.egrn_driver.find_element_by_xpath(
                ".//span[contains(@class,'v-button-caption') and contains(text(),'Отправить запрос')]"
            ).click()

            time.sleep(3)

            request_id_egrn = self.egrn_driver.find_element_by_xpath(
                ".//div[contains(@class,'v-label v-label-tipFont tipFont v-label-undef-w')][1]/b[1]"
            ).text

            self.last_request_time = time.time()

            time.sleep(3)
            self.egrn_driver.find_element_by_xpath(".//div[contains(@class,'v-window-closebox')]").click()

            return request_id_egrn

        # requests a document via selenium and returs egrn request id
        auth_key = data_handler_module.dh.auth_key_dict[str(chat_id)]
        if self.current_auth_key is None or auth_key != self.current_auth_key:
            # if driver's current auth key is not present or is different from the user's key
            # reinitialize the driver with user's key

            self.init_driver(auth_key)
        self.egrn_driver.get("https://rosreestr.gov.ru/wps/portal/p/cc_present/ir_egrn")
        search_button = self.egrn_driver.find_element_by_xpath(
            ".//span[contains(@class,'v-button-caption') and contains(text(),'Поиск объектов недвижимости')]"
        )
        search_button.click()

        self.vapp = self.egrn_driver.find_element_by_css_selector("div.v-app")
        cad_input = self.vapp.find_element_by_xpath(".//input[contains(@class,'v-textfield-prompt')]")
        region_input = self.vapp.find_element_by_xpath(".//input[contains(@class,'v-filterselect-input')]")
        search_button = self.vapp.find_element_by_xpath(
            ".//span[contains(@class,'v-button-caption') and contains(text(),'Найти')]"
        )

        cad_input.click()
        cad_input.send_keys(cad_number)
        cad_input.send_keys(Keys.ENTER)
        time.sleep(1)
        # region_input.send_keys(region_dict[cadastral_number[:2]])
        region_input.send_keys("Московская область")
        time.sleep(5)
        region_input.send_keys(Keys.ENTER)
        time.sleep(5)
        region_input.send_keys(Keys.TAB)
        search_button.click()

        t0 = time.time()
        while True:
            table = None
            try:
                table = self.egrn_driver.find_element_by_css_selector("table.v-table-table")
            except:
                pass
            warning = None
            try:
                warning = self.egrn_driver.find_element_by_class_name("v-Notification-warning").get_attribute(
                    "innerText"
                )
                if re.search("Не найдены данные, удовлетворяющие Вашему запросу.", warning) != None:
                    logging.info("Cadastral number not found")
                    break
            except:
                pass
            if table == None and warning == None:
                time.sleep(1)
                if time.monotonic() - t0 > 60:
                    print("За 60 секунд не дождались нужной страницы. Вероятно, ошибка сайта.")
                    # return("SearchKNsError")
            if table is not None:
                break

        try:
            table_row = self.egrn_driver.find_elements_by_xpath("//tr[@class='v-table-row']")
            table_row = [row for row in table_row if cad_number in row.text][0]
            contents = table_row.text.split("\n")
            cad_number = contents[0]
            address = contents[1]
            table_row.click()
        except:
            logging.info("Failed to find cad number")
            return None

        if excerpt_type == 1:
            # click egrp button if flag is set
            self.egrn_driver.find_element_by_xpath("//input[@id='gwt-uid-3']").click()

        time.sleep(2)
        solve_captcha()
        time.sleep(2)

        try:
            # finish request and get request_id_egrn
            request_id_egrn = finish_request()
            return request_id_egrn
        except:
            # if element is not found then either captcha wasn't recognzied properly
            # or egrn webside is being unstable
            # so we try to solve the captcha again
            retry_captcha_button = self.egrn_driver.find_element_by_xpath(
                ".//span[contains(@class,'v-button-caption') and contains(text(),'Другую картинку')]"
            )
            retry_captcha_button.click()
            time.sleep(1)
            solve_captcha()
            request_id_egrn = finish_request()
            return request_id_egrn
        finally:
            # if it fails, most likely egrn is being unstable
            # return to the initial page and try again
            self.init_driver(auth_key)


def egrn_proccess():
    eh = Egrn_Handler()
    while True:
        time.sleep(10)
        # check for unfinished requests every 10 seconds
        with sql.connect("request_data.db") as con:
            unfinished_requests = pd.read_sql("""SELECT * FROM requests WHERE request_id_egrn IS NULL""", con)

        for row in unfinished_requests.iterrows():
            row = row[1]
            request_id = row["request_id"]
            cad_number = row["cadastral_number"]
            excerpt_type = row["excerpt_type"]
            chat_id = row["chat_id"]

            if time.time() - eh.last_request_time > 310:
                pass
                # if 5 minutes has passed since the last request - make another one
                # else continue to other tasks
                # todo: separate timers for different auth_keys
                request_id_egrn = eh.request_excerpt(cad_number, chat_id, excerpt_type)

                if request_id_egrn == None:
                    continue
                    # if getting egrn request failed for some reason - continue with other requests
                else:
                    with sql.connect("request_data.db") as con:
                        cursor = con.cursor()
                        query = """UPDATE requests
                                SET request_id_egrn = ?
                                WHERE request_id = ?"""
                        values = (request_id_egrn, request_id)
                        cursor.execute(query, values)
                        con.commit()

        with sql.connect("request_data.db") as con:
            cursor = con.cursor()
            query = """SELECT chat_id FROM requests WHERE files_path IS NULL GROUP BY chat_id"""
            cursor.execute(query)
            users_to_check = cursor.fetchall()
            logging.info(f"Checking excerpts for users: {users_to_check}")

        for user in users_to_check:
            eh.download_excerpt(user[0])
            paid_requests_left = eh.check_accounts(user[0])
            logging.info(f"Paid requests left for user {user[0]}: {paid_requests_left}")

        with sql.connect("request_data.db") as con:
            cursor = con.cursor()
            query = """SELECT chat_id, files_path, cadastral_number, commentary, extension, request_id_egrn
                FROM requests
                WHERE files_path IS NOT NULL
                AND is_sent IS NULL"""
            cursor.execute(query)
            files_to_send = cursor.fetchall()
            print(f"Printing excerpts {files_to_send}")

            if len(files_to_send) > 0:
                for file in files_to_send:
                    chat_id = file[0]
                    files_path = file[1]
                    cadastral_number = file[2]
                    commentary = file[3]
                    extension = file[4]
                    request_id_egrn = file[5]
                    document_out = data_handler_module.dh.get_files(files_path, extension)
                    telegram_module.bh.send_message(
                        chat_id, document_out, filename=cadastral_number.replace(":", "_") + ".pdf"
                    )
                    with open("whatever_lol.pdf", "wb") as f:
                        f.write(document_out)
                    with sql.connect("request_data.db") as con:
                        cursor = con.cursor()
                        query = """UPDATE requests
                            SET is_sent = ?
                            WHERE request_id_egrn = ?"""
                        values = (1, request_id_egrn)
                        cursor.execute(query, values)


def check_key(auth_key):
    # checks if key is valid
    auth_validation_eh = Egrn_Handler()
    key_valid = auth_validation_eh.init_driver(auth_key)
    auth_validation_eh.egrn_driver.close()
    auth_validation_eh.egrn_driver.quit()
    del auth_validation_eh

    return key_valid

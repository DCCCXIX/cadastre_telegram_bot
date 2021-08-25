#!/usr/bin/env python
# coding: utf-8

import io
import re
import time
from configparser import ConfigParser

import requests

import data_handler_module
import intent_recognition_module


class DialogueManager(object):
    def get_answer(self, chat_id, text):
        if text == "/start" or text == "/help":
            return "Кадастровый бот-ассистент. В данной имплементации позволяет\
                    заказывать выписки из ЕГРН и направлять пользователю в\
                    человекочитаемом формате. Для использования потребуется\
                    ключ ФГИС ЕГРН, который можно получить следуя руководству\
                    по ссылке: https://rosreestr.gov.ru/site/ur/poluchit-svedeniya-iz-egrn/poluchenie-klyucha-dostupa-k-fgis-egrn/\
                    \nТакже, для успешного заказа выписок необходимо оплатить пакет выписок на сайте Росреестра"
        # returns user's intent
        intent = intent_recognition_module.ir.get_intent(str(text))

        if intent == "egrn_auth_key":
            # sets egrn auth key
            auth_key = re.match(r"\w{8}-\w{4}-\w{4}-\w{4}-\w{12}", text)[0]
            auth_key_set = data_handler_module.dh.set_auth_key(chat_id, auth_key)
            if auth_key_set:
                answer = "Ключ принят"
            else:
                answer = "Ключ не принят. Проверьте корректность ключа, либо попробуйте позже."

        elif intent == "egrn" or intent == "egrp":
            # checks if user has an auth key
            auth_key_added = data_handler_module.dh.verify_key(chat_id)
            if not auth_key_added:
                return "Заказ выписок невозможен без предоставления ключа.\
                    Предоставьте ключ ФГИС ЕГРН и повторите запрос."

            else:
                # grabs cadastral numbers from the text
                cad_numbers = re.findall(r"\d{2}:\d{2}:\d{1,7}:\d{1,}", text)
                cad_numbers = set(cad_numbers)
                if len(cad_numbers) > 0:
                    cad_numbers_string = ", ".join(cad_numbers)
                else:
                    return "Не могу заказать выписки без кадастровых номеров"

                # sets the flag for extensions to return excerpts as
                if "pdf" in text or "пдф" in text:
                    extension = ".pdf"
                elif "xml" in text or "хмл" in text:
                    extension = ".xml"
                elif "dxf" in text or "дхф" in text:
                    extension = ".dxf"
                else:
                    extension = ".pdf"

            # calls add_egrn_request with different excerpt types depending on intent
            if intent == "egrn":
                data_handler_module.dh.add_egrn_request(cad_numbers, chat_id, extension, excerpt_type=0)
                answer = "Заказ выписок ЕГРН на " + cad_numbers_string
            elif intent == "egrp":
                data_handler_module.dh.add_egrn_request(cad_numbers, chat_id, extension, excerpt_type=1)
                answer = "Заказ выписок ЕГРП на " + cad_numbers_string
        elif intent == "doc":
            data_handler_module.dh.add_doc_request(text, chat_id)
            answer = "Формирование договора (not implemented)"
        elif intent == "status":
            answer = data_handler_module.dh.get_status(chat_id)
        else:
            answer = "Повторите запрос"

        return answer


class BotHandler:
    # handles basic bot functions
    def __init__(self):
        self.config = ConfigParser()
        self.config.read("config.ini")
        self.token = self.config.get("settings", "token")
        self.api_url = f"https://api.telegram.org/bot{self.token}/"
        self.dialogue_manager = DialogueManager()
        self.offset = 0

    def get_last_update(self):
        get_result = self.get_updates()

        if len(get_result) > 0:
            last_update = get_result[-1]
        else:
            last_update = None
        return last_update

    def get_updates(self, new_offset=None, timeout=5):
        resp = requests.get(self.api_url + "getUpdates", {"timeout": timeout, "offset": new_offset})
        return resp.json()["result"]

    def send_message(self, chat_id, content, filename=None):
        if type(content) is str:
            # sending text
            return requests.post(self.api_url + "sendMessage", {"chat_id": chat_id, "text": content})
        elif type(content) is bytes and filename is not None:
            # sending a document
            # two lines below are needed for the file
            # to be displayed with correct extension for the user
            file_obj = io.BytesIO(content)
            file_obj.name = filename
            return requests.post(self.api_url + "sendDocument", {"chat_id": chat_id}, files={"document": file_obj})
        else:
            # sending a picture
            return requests.post(self.api_url + "sendPhoto", {"chat_id": chat_id}, files={"photo": content})

    def main(self):
        data_handler_module.dh.init_egrn_proccess()
        while True:
            updates = self.get_updates(new_offset=self.offset)
            for update in updates:
                if "message" in update:
                    chat_id = update["message"]["chat"]["id"]
                    if "text" in update["message"]:
                        text = update["message"]["text"]

                        answer = self.dialogue_manager.get_answer(chat_id, text)
                        self.send_message(chat_id, answer)
                self.offset = max(self.offset, update["update_id"] + 1)

            time.sleep(1)


bh = BotHandler()

if __name__ == "__main__":
    try:
        bh.main()
    except KeyboardInterrupt:
        exit()

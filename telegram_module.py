# -*- coding: utf-8 -*-
import logging
import re
import time
from configparser import ConfigParser
from multiprocessing import Process

import data_handler_module
import egrn_module
import intent_recognition_module
import requests
import rest_module


class BotHandler:
    def __init__(self, token, dialogue_manager):
        self.token = token
        self.api_url = f"https://api.telegram.org/bot{self.token}/"
        self.dialogue_manager = dialogue_manager

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

    def send_message(self, chat_id, content):
        # todo: support sending documents
        if type(content) is not str:
            # temporary testing stuff
            return requests.post(self.api_url + "sendPhoto", {"chat_id": chat_id}, files={"photo": content})
        else:
            return requests.post(self.api_url + "sendMessage", {"chat_id": chat_id, "text": content})


class DialogueManager(object):
    def get_answer(self, chat_id, text):
        if text == "/start":
            return "Здравствуйте. Я кадастровый бот-ассистент"
        if text == "/help":
            return "Сам разберешься, хуепутало"

        intent = intent_recognition_module.ir.get_intent(str(text))

        if intent == "egrn_auth_key":
            # todo: validate key on input
            data_handler_module.dh.set_auth_key(chat_id, text)
            answer = "Ключ принят"

        elif intent == "egrn" or intent == "egrp":
            auth_key_added = data_handler_module.dh.verify_key(chat_id)
            if not auth_key_added:
                return (
                    "Заказ выписок невозможен без предоставления ключа. Предоставьте ключ ФГИС ЕГРН и повторите запрос."
                )

            else:
                cad_numbers = re.findall(r"\d{2}:\d{2}:\d{1,7}:\d{1,}", text)
                cad_numbers = set(cad_numbers)
                if len(cad_numbers) > 0:
                    cad_numbers_string = ", ".join(cad_numbers)
                else:
                    return "Не могу заказать выписки без кадастровых номеров"

            if intent == "egrn":
                data_handler_module.dh.add_egrn_request(cad_numbers, chat_id, excerpt_type=0)
                answer = "Заказ выписок ЕГРН на " + cad_numbers_string
            elif intent == "egrp":
                data_handler_module.dh.add_egrn_request(cad_numbers, chat_id, excerpt_type=1)
                answer = "Заказ выписок ЕГРП на " + cad_numbers_string
        elif intent == "doc":
            data_handler_module.dh.add_doc_request(text, chat_id)
            answer = "Формирование договора (not implemented)"
        elif intent == "status":
            answer = data_handler_module.dh.get_status(chat_id)
        else:
            answer = "Повторите запрос"

        return answer


def main():
    config = ConfigParser()
    config.read("config.ini")
    token = config.get("settings", "token")
    dialogue_manager = DialogueManager()
    ca_bot = BotHandler(token, dialogue_manager)
    new_offset = 0

    proc = Process(target=egrn_module.egrn_proccess)
    proc.start()

    while True:
        updates = ca_bot.get_updates(new_offset=new_offset)
        for update in updates:
            if "message" in update:
                chat_id = update["message"]["chat"]["id"]
                if "text" in update["message"]:
                    text = update["message"]["text"]

                    answer = ca_bot.dialogue_manager.get_answer(chat_id, text)
                    ca_bot.send_message(chat_id, answer)
                elif "photo" in update["message"]:
                    file_id = update["message"]["photo"][1]["file_id"]
                    file_id = requests.get(f"https://api.telegram.org/bot{token}/getFile?file_id={file_id}").json()
                    image_path = file_id["result"]["file_path"]
                    image = requests.get(f"https://api.telegram.org/file/bot{token}/{image_path}", stream=True).raw
                    answer = rest_module.mh.predict(image)

                    ca_bot.send_message(chat_id, answer)

            new_offset = max(new_offset, update["update_id"] + 1)
        time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        exit()

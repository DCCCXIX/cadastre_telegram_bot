import io
import json
import os
import re
import time

import dataframe_image as dfi
import pandas as pd
from PIL import Image


class Data_Handler:
    def __init__(self):
        try:
            self.request_table = pd.read_csv("request_table.xls", encoding="windows-1251")
        except:
            self.request_table = pd.DataFrame(
                columns=[
                    "Chat Id",
                    "Дата запроса",
                    "Номер запроса",
                    "Кадастровый номер",
                    "Состояние запроса",
                    "Выдан",
                    "Путь к файлам",
                    "Комментарий",
                    "Тип выписки",
                ]
            )
        try:
            with open("auth_key_dict.json") as f:
                self.auth_key_dict = json.load(f)
        except:
            self.auth_key_dict = {}

    def get_status(self, chat_id):
        # WIP
        status_table = self.request_table[self.request_table["Chat Id"] == chat_id]
        status_table = status_table[
            [
                "Дата запроса",
                "Номер запроса",
                "Тип выписки",
                "Кадастровый номер",
                "Состояние запроса",
                "Выдан",
                "Комментарий",
            ]
        ]
        temp_image_path = f"{chat_id}_status_table.png"
        dfi.export(status_table.tail(20), temp_image_path, table_conversion="matplotlib")
        # with open(temp_image_path, "rb") as f:
        #     outfile = f
        # os.remove(temp_image_path)
        img = Image.open(temp_image_path)
        img_array = io.BytesIO()
        img.save(img_array, format="PNG")
        img_array = img_array.getvalue()

        return img_array

    def verify_key(self, chat_id):
        auth_key_added = True
        try:
            self.auth_key_dict[str(chat_id)]
        except:
            auth_key_added = False

        return auth_key_added

    def set_auth_key(self, chat_id, text):
        # TODO: key testing before setting
        self.auth_key_dict[chat_id] = re.match(r"\w{8}-\w{4}-\w{4}-\w{4}-\w{12}", text)[0]
        with open("auth_key_dict.json", "w") as f:
            json.dump(self.auth_key_dict, f)

    def get_files(self, by="Кадастровый номер", value=None, extension=".xml"):
        # WIP
        request_row = self.request_table.loc[self.request_table[by] == value].tail(1)
        files_path = request_row["Путь к файлам"].values[0]

        return files_path

    def add_egrn_request(self, cad_numbers, chat_id, egrp=False):
        for cad_number in cad_numbers:
            if egrp:
                excerpt_type = "ЕГРП"
            else:
                excerpt_type = "ЕГРН"

            self.request_table.loc[len(self.request_table) + 1] = [
                chat_id,
                None,
                None,
                cad_number,
                None,
                None,
                None,
                None,
                excerpt_type,
            ]
            self.request_table.to_csv("request_table.xls", index=False, encoding="windows-1251")

    def add_doc_request(self, text, chat_id):
        # not implemented
        pass


dh = Data_Handler()

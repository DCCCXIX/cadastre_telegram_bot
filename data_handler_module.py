import io
import json
import logging
import os
import re
import sqlite3 as sql
import time

import dataframe_image as dfi
import pandas as pd
from PIL import Image

import doc_module
import egrn_module


class Data_Handler:
    def __init__(self):

        # opens request tables if present or creates new ones from template
        # egrn requests queued up
        # load a dict of user : auth key
        try:
            with open("auth_key_dict.json") as f:
                self.auth_key_dict = json.load(f)
        except:
            self.auth_key_dict = {}

    def init_db(self):
        with sql.connect("request_data.db") as con:
            self.cursor = con.cursor()
            self.cursor.execute(
                """CREATE TABLE IF NOT EXISTS requests (
                request_id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT,
                request_date TEXT,
                request_id_egrn TEXT,
                cadastral_number TEXT,
                request_status TEXT,
                is_sent INTEGER,
                files_path TEXT,
                commentary TEXT,
                excerpt_type INTEGER
            )"""
            )
            con.commit()

    def get_status(self, chat_id):
        # returns a table with latest egrn requests' statuses
        # todo: fancier table
        with sql.connect("request_data.db") as con:
            self.cursor = con.cursor()

        query = """SELECT (
                request_date,
                request_id_egrn,
                excerpt_type,
                cadastral_number,
                request_status,
                is_sent,
                commentary)
                FROM requests WHERE chat_id = (?)"""
        values = chat_id

        status_table = pd.read_sql(query, values, con)

        temp_image_path = f"{chat_id}_status_table.png"
        dfi.export(status_table.tail(20), temp_image_path, table_conversion="matplotlib")
        img = Image.open(temp_image_path)
        img_array = io.BytesIO()
        img.save(img_array, format="PNG")
        img_array = img_array.getvalue()

        return img_array

    def verify_key(self, chat_id, auth_key=None):
        # checks if user has an auth key in the dict
        auth_key_added = True
        try:
            self.auth_key_dict[str(chat_id)]
        except:
            auth_key_added = False

        return auth_key_added

    def set_auth_key(self, chat_id, auth_key):
        # grabs an auth key from the text and puts user : key pair into the dict
        # todo: key testing before setting
        key_valid = egrn_module.check_key(auth_key)
        if key_valid:
            logging.info(f"Setting auth key {auth_key} for user {chat_id}")
            self.auth_key_dict[chat_id] = auth_key
            with open("auth_key_dict.json", "w") as f:
                json.dump(self.auth_key_dict, f)

            return True
        else:
            return False

    def get_files(self, request_id_egrn, extension=".pdf"):
        # returns files in several formats
        # todo: support returning files by cadastral number and egrn request id
        # WIP
        with sql.connect("request_data.db") as con:
            self.cursor = con.cursor()
            query = """SELECT files_path FROM requests WHERE request_id_egrn IS ?"""
            values = request_id_egrn
            files_path = self.cursor.execute(query, values)[0]

        if extension == ".xml":
            pass
        elif extension == ".pdf":
            pass
        elif extension == ".dxf":
            pass

        return files_path

    def add_egrn_request(self, cad_numbers, chat_id, excerpt_type):
        # adds a new request for egrn module to proccess
        # todo: implement a proper database interaction instead of this shit
        with sql.connect("request_data.db") as con:
            self.cursor = con.cursor()
            query = """INSERT INTO requests (
                chat_id, cadastral_number, excerpt_type
                ) VALUES (?, ?, ?)
                """
            for cad_number in cad_numbers:
                values = (chat_id, cad_number, excerpt_type)
                self.cursor.execute(query, values)
                con.commit()

    def update_request(self, request_id, request_id_egrn):
        with sql.connect("request_data.db") as con:
            self.cursor = con.cursor()
            query = """UPDATE requests
                    SET request_id_egrn = ?
                    WHERE request_id = ?"""
            values = (request_id_egrn, request_id)
            self.cursor.execute(query, values)

    def add_doc_request(self, text, chat_id):
        # adds a new request for doc module to proccess
        # not implemented
        pass


dh = Data_Handler()
dh.init_db()

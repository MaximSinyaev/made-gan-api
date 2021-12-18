import datetime
import os
import random
import re
import sqlite3
from sqlite3 import Error


BOT_PATH = os.path.abspath(os.getcwd())
STATIC_PATH = os.getenv("STATIC_PATH")
STORAGE_PATH = os.path.join(STATIC_PATH, "storage")
STORAGE = os.path.join(STORAGE_PATH, "bot_db.db")
if not os.path.exists(STORAGE_PATH):
    os.mkdir(STORAGE_PATH)


class ImagesDB:
    def __init__(self, storage_path=STORAGE):
        self.storage = storage_path
        if not os.path.exists(storage_path):
            self.init_tables(storage_path)

    def init_tables(self, storage_path):
        conn = self.create_connection(storage_path)
        create_table_users_sql = """
        CREATE TABLE USERS
        (ID INTEGER PRIMARY KEY, REGISTRATION TEXT, TELEGRAM_ID TEXT, NAME TEXT, STATUS INTEGER)
        """
        create_table_logs_sql = """
        CREATE TABLE LOGS
        (ID INTEGER PRIMARY KEY, DATETIME TEXT, UID TEXT, AUTHOR TEXT, MESSAGE TEXT)
        """
        create_table_images_sql = """
        CREATE TABLE IMAGES
        (ID INTEGER PRIMARY KEY, DATETIME TEXT, TEXT TEXT, UID TEXT, TASK_ID TEXT, STATUS INTEGER, QUEUE_POSITION INTEGER)
        """
        cur = conn.cursor()
        cur.execute(create_table_users_sql)
        cur.execute(create_table_logs_sql)
        cur.execute(create_table_images_sql)
        conn.commit()
        conn.close()

    @staticmethod
    def create_connection(db_file):
        """ create a database connection to a SQLite database """
        conn = None
        try:
            conn = sqlite3.connect(db_file)
            print(sqlite3.version)
        except Error as e:
            print(e)
        return conn

    def add_user(self, uid, name):
        conn = self.create_connection(self.storage)
        cur = conn.cursor()
        current_datetime = datetime.datetime.now().isoformat()
        add_user_sql = f"""
        INSERT INTO USERS 
        (REGISTRATION, TELEGRAM_ID, NAME, STATUS)
        VALUES
        ('{current_datetime}', '{uid}', '{name}', 0)
        """
        cur.execute(add_user_sql)
        conn.commit()
        conn.close()

    def add_log(self, author, message, uid):
        conn = self.create_connection(self.storage)
        cur = conn.cursor()
        current_datetime = datetime.datetime.now().isoformat()
        message = re.sub("\W", " ", message)
        add_log_sql = f"""
        INSERT INTO LOGS 
        (DATETIME, UID, AUTHOR, MESSAGE)
        VALUES
        ('{current_datetime}', '{uid}', '{author}', '{message}')
        """
        cur.execute(add_log_sql)
        conn.commit()
        conn.close()

    def add_image(self, uid, text, task_id, queue_position, status=0):
        conn = self.create_connection(self.storage)
        cur = conn.cursor()
        current_datetime = datetime.datetime.now().isoformat()
        add_image_sql = f"""
        INSERT INTO IMAGES 
        (DATETIME, UID, TEXT, TASK_ID, STATUS, QUEUE_POSITION)
        VALUES
        ('{current_datetime}', '{uid}', '{text}', '{task_id}', {status}, {int(queue_position)})
        """
        cur.execute(add_image_sql)
        conn.commit()
        conn.close()

    def update_image_status(self, uid, task_id, status):
        conn = self.create_connection(self.storage)
        cur = conn.cursor()
        update_image_status_sql = f"""
        UPDATE IMAGES 
        SET STATUS = {status}
        WHERE IMAGES.UID = '{uid}'
        AND IMAGES.TASK_ID = '{task_id}'
        """
        cur.execute(update_image_status_sql)
        conn.commit()
        conn.close()

    def update_image_queue_position(self, task_id, queue_position):
        conn = self.create_connection(self.storage)
        cur = conn.cursor()
        update_image_queue_position_sql = f"""
        UPDATE IMAGES 
        SET QUEUE_POSITION = {int(queue_position)}
        WHERE IMAGES.TASK_ID = '{task_id}'
        """
        cur.execute(update_image_queue_position_sql)
        conn.commit()
        conn.close()

    def check_user_queue_position(self, uid):
        queue_position = 0
        res_list = []
        conn = self.create_connection(self.storage)
        cur = conn.cursor()
        check_queue_position_sql = f"""
        SELECT QUEUE_POSITION, DATETIME FROM IMAGES
        WHERE IMAGES.UID = {uid}
        ORDER BY DATETIME DESC
        LIMIT 1
        """
        for res in cur.execute(check_queue_position_sql):
            res_list.append(res[0])
        if len(res_list) > 0:
            queue_position = res_list[0]
        conn.close()
        return queue_position

    def check_user(self, uid):
        flag = False
        conn = self.create_connection(self.storage)
        cur = conn.cursor()
        check_user_sql = f"""
        SELECT count(*) FROM USERS
        WHERE USERS.TELEGRAM_ID = {uid}
        """
        for res in cur.execute(check_user_sql):
            if res[0] > 0:
                flag = True
        conn.close()
        return flag

    def check_user_status(self, uid):
        status = -1
        res_list = []
        conn = self.create_connection(self.storage)
        cur = conn.cursor()
        check_user_sql = f"""
        SELECT STATUS FROM USERS
        WHERE USERS.TELEGRAM_ID = {uid}
        """
        for res in cur.execute(check_user_sql):
            res_list.append(res[0])
        if len(res_list) > 0:
            status = res_list[0]
        conn.close()
        return status

    def update_user_status(self, uid, status):
        conn = self.create_connection(self.storage)
        cur = conn.cursor()
        update_user_status_sql = f"""
        UPDATE USERS 
        SET STATUS = {status}
        WHERE USERS.TELEGRAM_ID = {uid}
        """
        cur.execute(update_user_status_sql)
        conn.commit()
        conn.close()

    def get_time_of_last_task(self, uid):
        last_dt = None
        res_list = []
        conn = self.create_connection(self.storage)
        cur = conn.cursor()
        get_last_dt_sql = f"""
        SELECT MAX(DATETIME) FROM IMAGES
        WHERE IMAGES.UID = {uid}
        """
        for res in cur.execute(get_last_dt_sql):
            res_list.append(res[0])
        if len(res_list) > 0:
            last_dt = res_list[0]
        conn.close()
        return last_dt

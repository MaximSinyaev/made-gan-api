import datetime
import os

import re
import sqlite3
import aiosqlite
from sqlite3 import Error

import asyncio


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

    @staticmethod
    def init_tables(storage_path):
        conn = sqlite3.connect(storage_path)
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
    async def create_connection(db_file):
        """ create a database connection to a SQLite database """
        conn = None
        try:
            conn = await aiosqlite.connect(db_file)
        except Error as e:
            print(e)
        return conn

    async def add_user(self, uid, name):
        conn = await self.create_connection(self.storage)
        current_datetime = datetime.datetime.now().isoformat()
        add_user_sql = f"""
        INSERT INTO USERS 
        (REGISTRATION, TELEGRAM_ID, NAME, STATUS)
        VALUES
        ('{current_datetime}', '{uid}', '{name}', 0)
        """
        await conn.execute(add_user_sql)
        await conn.commit()
        await conn.close()

    async def add_log(self, author, message, uid):
        conn = await self.create_connection(self.storage)
        cur = await conn.cursor()
        current_datetime = datetime.datetime.now().isoformat()
        message = re.sub("\W", " ", message)
        add_log_sql = f"""
        INSERT INTO LOGS 
        (DATETIME, UID, AUTHOR, MESSAGE)
        VALUES
        ('{current_datetime}', '{uid}', '{author}', '{message}')
        """
        await cur.execute(add_log_sql)
        await conn.commit()
        await conn.close()

    async def add_image(self, uid, text, task_id, queue_position, status=0):
        conn = await self.create_connection(self.storage)
        cur = await conn.cursor()
        current_datetime = datetime.datetime.now().isoformat()
        add_image_sql = f"""
        INSERT INTO IMAGES 
        (DATETIME, UID, TEXT, TASK_ID, STATUS, QUEUE_POSITION)
        VALUES
        ('{current_datetime}', '{uid}', '{text}', '{task_id}', {status}, {int(queue_position)})
        """
        await cur.execute(add_image_sql)
        await conn.commit()
        await conn.close()

    async def update_image_status(self, uid, task_id, status):
        conn = await self.create_connection(self.storage)
        cur = await conn.cursor()
        update_image_status_sql = f"""
        UPDATE IMAGES 
        SET STATUS = {status}
        WHERE IMAGES.UID = '{uid}'
        AND IMAGES.TASK_ID = '{task_id}'
        """
        await cur.execute(update_image_status_sql)
        await conn.commit()
        await conn.close()

    async def update_image_queue_position(self, task_id, queue_position):
        conn = await self.create_connection(self.storage)
        cur = await conn.cursor()
        update_image_queue_position_sql = f"""
        UPDATE IMAGES 
        SET QUEUE_POSITION = {int(queue_position)}
        WHERE IMAGES.TASK_ID = '{task_id}'
        """
        await cur.execute(update_image_queue_position_sql)
        await conn.commit()
        await conn.close()

    async def check_user_queue_position(self, uid):
        queue_position = 0
        res_list = []
        conn = await self.create_connection(self.storage)
        cur = await conn.cursor()
        check_queue_position_sql = f"""
        SELECT QUEUE_POSITION, DATETIME FROM IMAGES
        WHERE IMAGES.UID = {uid}
        ORDER BY DATETIME DESC
        LIMIT 1
        """
        async for res in await cur.execute(check_queue_position_sql):
            res_list.append(res[0])
        if len(res_list) > 0:
            queue_position = res_list[0]
        await conn.close()
        return queue_position

    async def check_user(self, uid):
        flag = False
        conn = await self.create_connection(self.storage)
        cur = await conn.cursor()
        check_user_sql = f"""
        SELECT count(*) FROM USERS
        WHERE USERS.TELEGRAM_ID = {uid}
        """
        async for res in await cur.execute(check_user_sql):
            if res[0] > 0:
                flag = True
        await conn.close()
        return flag

    async def check_user_status(self, uid):
        status = -1
        res_list = []
        conn = await self.create_connection(self.storage)
        cur = await conn.cursor()
        check_user_sql = f"""
        SELECT STATUS FROM USERS
        WHERE USERS.TELEGRAM_ID = {uid}
        """
        async for res in await cur.execute(check_user_sql):
            res_list.append(res[0])
        if len(res_list) > 0:
            status = res_list[0]
        await conn.close()
        return status

    async def update_user_status(self, uid, status):
        conn = await self.create_connection(self.storage)
        cur = await conn.cursor()
        update_user_status_sql = f"""
        UPDATE USERS 
        SET STATUS = {status}
        WHERE USERS.TELEGRAM_ID = {uid}
        """
        await cur.execute(update_user_status_sql)
        await conn.commit()
        await conn.close()

    async def get_time_of_last_task(self, uid):
        last_dt = None
        res_list = []
        conn = await self.create_connection(self.storage)
        cur = await conn.cursor()
        get_last_dt_sql = f"""
        SELECT MAX(DATETIME) FROM IMAGES
        WHERE IMAGES.UID = {uid}
        """
        async for res in await cur.execute(get_last_dt_sql):
            res_list.append(res[0])
        if len(res_list) > 0:
            last_dt = res_list[0]
        await conn.close()
        return last_dt

import os

import dbutils
from ramkodb import RamkoDb

tbl_name_map = 'user_map'

def create_user_map_table():
    dbutils.execute(f"DROP TABLE IF EXISTS {tbl_name_map};")
    sql = f"""CREATE TABLE {tbl_name_map} (
     id INTEGER,
     inj_id INTEGER,
     empId INTEGER,
     inj_empId INTEGER,
     username TEXT,
     inj_username TEXT, 
     firstname TEXT, 
     inj_firstname TEXT,
     lastname TEXT, 
     inj_lastname TEXT,
     status TEXT,
     do_merge BOOL
     )
     """
    dbutils.execute(sql)

    db = None
    try:
        db = RamkoDb()
        db.connect()
        sql = f"""SELECT mu.id, mu.empId, mu.username, mu.firstname, mu.lastname
                    FROM ramko.user mu
                    WHERE mu.deleted = 0
                """
        mfg_users = db.select(sql)
        for user in mfg_users:
            sql2 = f"""INSERT INTO {tbl_name_map} (id, inj_id, empId, inj_empId, username, inj_username, firstname, inj_firstname, lastname, inj_lastname, status, do_merge) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
            dbutils.execute(sql2,(user['id'], None, user['empId'], None, user['username'], None, user['firstname'], None, user['lastname'], None, None, False) )

        print(f"Created table: {tbl_name_map}")
    except Exception as e:
        print(f"Error retrieving mfg users into mapping table: {e}")
        raise
    finally:
        if db and db.conn:
            db.disconnect()


def match_existing_users():
    sql = """SELECT iu.id AS inj_id, mu.id AS mfg_id, iu.empId, iu.username, iu.firstname, iu.lastname
            FROM ramkoinj.user iu
            LEFT JOIN ramko.user mu ON iu.firstname = mu.firstname AND iu.lastname = mu.lastname AND iu.username = mu.username
            WHERE iu.deleted = 0 AND mu.id is not NULL
            ORDER BY iu.id;"""

    db = None
    try:
        db = RamkoDb()
        db.connect()
        mfg_users = db.select(sql)
        for user in mfg_users:
            sql2 = f"""UPDATE {tbl_name_map} SET inj_id=?,  inj_empId=?, inj_username=?, inj_firstname=?, inj_lastname=?, status=?, do_merge=? WHERE id = ?;"""
            dbutils.execute(sql2, (user['inj_id'], user['empId'], user['username'], user['firstname'], user['lastname'], 'Existing', False, user['mfg_id']))

    except Exception as e:
        print(f"Error updating user mapping table: {e}")
        raise
    finally:
        if db and db.conn:
            db.disconnect()


def match_usernames():
    sql = """SELECT iu.id AS inj_id, mu.id AS mfg_id, iu.empId, iu.username, iu.firstname, iu.lastname
            FROM ramkoinj.user iu
            LEFT JOIN ramko.user mu ON iu.username = mu.username
            WHERE iu.deleted = 0 AND mu.id is not NULL AND (iu.firstname != mu.firstname OR iu.lastname != mu.lastname)
            ORDER BY iu.id;"""

    db = None
    try:
        db = RamkoDb()
        db.connect()
        mfg_users = db.select(sql)
        for user in mfg_users:
            sql2 = f"""UPDATE {tbl_name_map} SET inj_id=?, inj_empId=?, inj_username=?, inj_firstname=?, inj_lastname=?, status=?, do_merge=? WHERE id = ?;"""
            dbutils.execute(sql2, (user['inj_id'], user['empId'], user['username'], user['firstname'], user['lastname'], 'UserMatch', True, user['mfg_id']))

    except Exception as e:
        print(f"Error updating user mapping table: {e}")
        raise
    finally:
        if db and db.conn:
            db.disconnect()


def match_names():
    sql = """SELECT iu.id AS inj_id, mu.id AS mfg_id, iu.empId, iu.username, iu.firstname, iu.lastname
            FROM ramkoinj.user iu
            LEFT JOIN ramko.user mu ON iu.firstname = mu.firstname AND iu.lastname = mu.lastname
            WHERE iu.deleted = 0 AND mu.id is not NULL AND iu.username != mu.username
            ORDER BY iu.id;"""

    db = None
    try:
        db = RamkoDb()
        db.connect()
        mfg_users = db.select(sql)
        for user in mfg_users:
            sql2 = f"""UPDATE {tbl_name_map} SET inj_id=?, inj_empId=?, inj_username=?, inj_firstname=?, inj_lastname=?, status=?, do_merge=? WHERE id = ?;"""
            dbutils.execute(sql2, (user['inj_id'], user['empId'], user['username'], user['firstname'], user['lastname'], 'NameMatch', True, user['mfg_id']))

    except Exception as e:
        print(f"Error updating user mapping table: {e}")
        raise
    finally:
        if db and db.conn:
            db.disconnect()


def match_missing():
    sql = """SELECT mu.id AS mfg_id, mu.empId, mu.username, mu.firstname, mu.lastname
            FROM ramko.user mu
            LEFT JOIN ramkoinj.user iu1 ON mu.firstname = iu1.firstname AND mu.lastname = iu1.lastname
            LEFT JOIN ramkoinj.user iu2 ON mu.username = iu2.username
            WHERE mu.deleted = 0 AND iu1.id is NULL and iu2.id is NULL
            ORDER BY mu.id;"""

    db = None
    try:
        db = RamkoDb()
        db.connect()
        mfg_users = db.select(sql)
        for user in mfg_users:
            sql2 = f"""UPDATE {tbl_name_map} SET inj_id=?, inj_empId=?, inj_username=?, inj_firstname=?, inj_lastname=?, status=?, do_merge=? WHERE id = ?;"""
            dbutils.execute(sql2, (None, None, None, None, None, 'Missing', True, user['mfg_id']))

    except Exception as e:
        print(f"Error updating user mapping table: {e}")
        raise
    finally:
        if db and db.conn:
            db.disconnect()


def make_user_map_table():
    create_user_map_table()
    match_existing_users()
    match_usernames()
    match_names()
    match_missing()


def merge_users():
    dbmfg = None
    dbinj = None
    try:
        mfg_host = os.environ.get('DB_MFG_HOST')
        mfg_port = os.environ.get('DB_MFG_PORT')
        inj_host = os.environ.get('DB_INJ_HOST')
        inj_port = os.environ.get('DB_INJ_PORT')
        users = dbutils.select(f"SELECT * FROM {tbl_name_map} WHERE do_merge = true;")
        dbmfg = RamkoDb()
        dbmfg.connect(host=mfg_host, port=mfg_port)
        dbinj = RamkoDb()
        dbinj.connect(host=inj_host, port=inj_port)
        for user in users[1]:
            mfg_user = dbmfg.select("SELECT * FROM ramko.user WHERE id = ?", (user['id'],))
            if user['status'] == 'UserMatch':
                username = f"{user['firstname'][0]}{user['lastname']}".lower()
            else:
                username = user['username']

            dbinj.execute(f"INSERT INTO ramkoinj.user (username, password, permflags, firstname, lastname, email, empId, subscriptions, deleted) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (username, mfg_user[0]['password'], mfg_user[0]['permflags'], mfg_user[0]['firstname'], mfg_user[0]['lastname'], mfg_user[0]['email'], None, mfg_user[0]['subscriptions'], mfg_user[0]['deleted']))


    except Exception as e:
        print(f"Error updating user mapping table: {e}")
        raise
    finally:
        if dbmfg and dbmfg.conn:
            dbmfg.disconnect()
        if dbinj and dbinj.conn:
            dbinj.disconnect()



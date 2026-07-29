import os

import dbutils
from ramkodb import RamkoDb

tbl_name_map = 'vendor_map'

def create_vendor_map_table():
    dbutils.execute(f"DROP TABLE IF EXISTS {tbl_name_map};")
    sql = f"""CREATE TABLE {tbl_name_map} (
     id INTEGER,
     inj_id INTEGER,
     name TEXT,
     inj_name TEXT,
     active BOOL,
     inj_active BOOL,
     do_merge BOOL
     )
     """
    dbutils.execute(sql)

    db = None
    try:
        db = RamkoDb()
        db.connect()
        sql = f"""SELECT v.id, v.name, v.active
                    FROM ramko.vendor v
                    WHERE v.id IN (SELECT DISTINCT vendorId FROM ramko.Material_Entry WHERE date > '2021-01-01') AND v.active=1
                    ORDER BY v.id;
                """
        mfg_vendors = db.select(sql)
        for vendor in mfg_vendors:
            sql2 = f"""INSERT INTO {tbl_name_map} (id, inj_id, name, inj_name, active, inj_active, do_merge) VALUES (?, ?, ?, ?, ?, ?, ?)"""
            dbutils.execute(sql2,(vendor['id'], None, vendor['name'], None, vendor['active'], None, True) )

        print(f"Created table: {tbl_name_map}")
    except Exception as e:
        print(f"Error retrieving mfg vendor into mapping table: {e}")
        raise
    finally:
        if db and db.conn:
            db.disconnect()



def match_existing_vendors():
    sql = """SELECT iv.id AS inj_id, mv.id AS mfg_id, iv.name, iv.active
            FROM ramkoinj.vendor iv
            LEFT JOIN ramko.vendor mv ON LOWER(iv.name) = LOWER(mv.name)
            WHERE mv.id is not NULL
            ORDER BY iv.id;"""

    db = None
    try:
        db = RamkoDb()
        db.connect()
        mfg_vendors = db.select(sql)
        for vendor in mfg_vendors:
            sql2 = f"""UPDATE {tbl_name_map} SET inj_id=?,  inj_name=?, inj_active=?, do_merge=? WHERE id = ?;"""
            dbutils.execute(sql2, (vendor['inj_id'], vendor['name'], vendor['active'], False, vendor['mfg_id']))

    except Exception as e:
        print(f"Error updating vendor mapping table: {e}")
        raise
    finally:
        if db and db.conn:
            db.disconnect()


def merge_vendors():
    dbmfg = None
    dbinj = None
    try:
        mfg_host = os.environ.get('DB_MFG_HOST')
        mfg_port = os.environ.get('DB_MFG_PORT')
        inj_host = os.environ.get('DB_INJ_HOST')
        inj_port = os.environ.get('DB_INJ_PORT')
        vendors = dbutils.select(f"SELECT * FROM {tbl_name_map} WHERE do_merge = true;")
        dbmfg = RamkoDb()
        dbmfg.connect(host=mfg_host, port=mfg_port)
        dbinj = RamkoDb()
        dbinj.connect(host=inj_host, port=inj_port)
        for vendor in vendors[1]:
            mfg_vendor = dbmfg.select("SELECT * FROM ramko.vendor WHERE id = ?", (vendor['id'],) )

            dbinj.execute(f"INSERT INTO ramkoinj.vendor (name, active, lastAudit, state, terms, notes, activityLog, contacts, locked, files, lastActivity, oneYearActivity, updated) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (mfg_vendor[0]['name'], mfg_vendor[0]['active'], mfg_vendor[0]['lastAudit'], mfg_vendor[0]['state'], mfg_vendor[0]['terms'], mfg_vendor[0]['notes'], mfg_vendor[0]['activityLog'], mfg_vendor[0]['contacts'], mfg_vendor[0]['locked'], mfg_vendor[0]['files'], mfg_vendor[0]['lastActivity'], mfg_vendor[0]['oneYearActivity'], mfg_vendor[0]['updated']))

    except Exception as e:
        print(f"Error updating vendor mapping table: {e}")
        raise
    finally:
        if dbmfg and dbmfg.conn:
            dbmfg.disconnect()
        if dbinj and dbinj.conn:
            dbinj.disconnect()

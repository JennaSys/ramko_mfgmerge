import os

import dbutils
from ramkodb import RamkoDb

tbl_name_map = 'cust_map'

def create_cust_map_table():
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
        sql = f"""SELECT c.id, c.name, c.active
                    FROM ramko.customer c
                    WHERE c.id IN (SELECT DISTINCT customerId FROM ramko.Jobs WHERE Open_Date > '2021-01-01') AND c.active=1
                    ORDER BY c.id;
                """
        mfg_customers = db.select(sql)
        for cust in mfg_customers:
            sql2 = f"""INSERT INTO {tbl_name_map} (id, inj_id, name, inj_name, active, inj_active, do_merge) VALUES (?, ?, ?, ?, ?, ?, ?)"""
            dbutils.execute(sql2,(cust['id'], None, cust['name'], None, cust['active'], None, True) )

        print(f"Created table: {tbl_name_map}")
    except Exception as e:
        print(f"Error retrieving mfg cust into mapping table: {e}")
        raise
    finally:
        if db and db.conn:
            db.disconnect()


def match_existing_customers():
    sql = """SELECT ic.id AS inj_id, mc.id AS mfg_id, ic.name, ic.active
            FROM ramkoinj.customer ic
            LEFT JOIN ramko.customer mc ON LOWER(ic.name) = LOWER(mc.name)
            WHERE mc.id is not NULL
            ORDER BY ic.id;"""

    db = None
    try:
        db = RamkoDb()
        db.connect()
        mfg_customers = db.select(sql)
        for cust in mfg_customers:
            sql2 = f"""UPDATE {tbl_name_map} SET inj_id=?,  inj_name=?, inj_active=?, do_merge=? WHERE id = ?;"""
            dbutils.execute(sql2, (cust['inj_id'], cust['name'], cust['active'], False, cust['mfg_id']))

    except Exception as e:
        print(f"Error updating cust mapping table: {e}")
        raise
    finally:
        if db and db.conn:
            db.disconnect()


def merge_customers():
    dbmfg = None
    dbinj = None
    try:
        mfg_host = os.environ.get('DB_MFG_HOST')
        mfg_port = os.environ.get('DB_MFG_PORT')
        inj_host = os.environ.get('DB_INJ_HOST')
        inj_port = os.environ.get('DB_INJ_PORT')
        customers = dbutils.select(f"SELECT * FROM {tbl_name_map} WHERE do_merge = true;")
        dbmfg = RamkoDb()
        dbmfg.connect(host=mfg_host, port=mfg_port)
        dbinj = RamkoDb()
        dbinj.connect(host=inj_host, port=inj_port)
        for cust in customers[1]:
            if cust['inj_id'] is None:
                # New customer
                mfg_cust = dbmfg.select("SELECT * FROM ramko.customer WHERE id = ?", (cust['id'],) )

                result = dbinj.execute(f"INSERT INTO ramkoinj.customer (name, active, lastActivity, oneYearActivity, address, rate, updated, notes, files, contacts) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                (mfg_cust[0]['name'], mfg_cust[0]['active'], mfg_cust[0]['lastActivity'], mfg_cust[0]['oneYearActivity'], mfg_cust[0]['address'], mfg_cust[0]['rate'], mfg_cust[0]['updated'], mfg_cust[0]['notes'], mfg_cust[0]['files'], mfg_cust[0]['contacts']))
                cust_id = result[1]['lastrowid']
            else:
                # use existing inj customer
                cust_id = cust['inj_id']

            mfg_items =  dbmfg.select("SELECT * FROM ramko.CustomerItem WHERE customer_id = ?", (cust['id'],) )
            for item in mfg_items:
                dbinj.execute(f"""INSERT INTO ramkoinj.CustomerItem (version, customerPartNumber, description, palletQty, rev, unitOfMeasure, qtyInStock, qtyOnOrder, locked, inv,
                                    customer_id, customerItemFamily_id, rate, date, files, notes, activityLog, autoFifo, ccDateAdded, ccAddedByUser_id, ccApprovalNote, weight,
                                    created, updated, deleted, qtyPerBox, barcode, partCreationVideoObjectKey, machineSetupVideoObjectKey, active, fg) 
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                (item['version'], item['customerPartNumber'], item['description'], item['palletQty'], item['rev'], item['unitOfMeasure'], item['qtyInStock'], item['qtyOnOrder'], item['locked'], item['inv'],
                                 cust_id, item['customerItemFamily_id'], item['rate'], item['date'], item['files'], item['notes'], item['activityLog'], item['autoFifo'], item['ccDateAdded'], item['ccAddedByUser_id'], item['ccApprovalNote'], item['weight'],
                                 item['created'], item['updated'], item['deleted'], item['qtyPerBox'], item['barcode'], item['partCreationVideoObjectKey'], item['machineSetupVideoObjectKey'], item['active'], item['fg']) )


    except Exception as e:
        print(f"Error updating user mapping table: {e}")
        raise
    finally:
        if dbmfg and dbmfg.conn:
            dbmfg.disconnect()
        if dbinj and dbinj.conn:
            dbinj.disconnect()



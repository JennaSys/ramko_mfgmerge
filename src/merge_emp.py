import os

import dbutils
from ramkodb import RamkoDb

tbl_name_map = 'emp_map'

def create_emp_map_table():
    dbutils.execute(f"DROP TABLE IF EXISTS {tbl_name_map};")
    sql = f"""CREATE TABLE {tbl_name_map} (
     id INTEGER,
     inj_id TEXT,
     firstname TEXT, 
     inj_firstname TEXT,
     lastname TEXT, 
     inj_lastname TEXT,
     phone TEXT,
     inj_phone TEXT, 
     inj_active BOOL,
     status TEXT,
     user_id INTEGER,
     do_merge BOOL
     )
     """
    dbutils.execute(sql)

    db = None
    try:
        db = RamkoDb()
        db.connect()
        sql = f"""SELECT me.id, me.firstname, me.lastname, me.phone, me.user_id
                    FROM ramko.emp me
                    WHERE me.active = 1
                """
        mfg_emps = db.select(sql)
        for emp in mfg_emps:
            sql2 = f"""INSERT INTO {tbl_name_map} (id, inj_id, firstname, inj_firstname, lastname, inj_lastname, phone, inj_phone, status, user_id, do_merge) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
            dbutils.execute(sql2,(emp['id'], None, emp['firstname'], None, emp['lastname'], None, emp['phone'], None, None, emp['user_id'], True) )

        print(f"Created table: {tbl_name_map}")
    except Exception as e:
        print(f"Error retrieving mfg emp into mapping table: {e}")
        raise
    finally:
        if db and db.conn:
            db.disconnect()


def match_existing_emps():
    sql = """SELECT ie.id AS inj_id, me.id AS mfg_id, ie.firstname, ie.lastname, ie.phone, ie.active
            FROM ramkoinj.emp ie
            LEFT JOIN ramko.emp me ON ie.firstname = me.firstname AND ie.lastname = me.lastname
            WHERE ie.active = 1 AND me.id is not NULL
            ORDER BY ie.id;"""

    db = None
    try:
        db = RamkoDb()
        db.connect()
        mfg_emps = db.select(sql)
        for emp in mfg_emps:
            sql2 = f"""UPDATE {tbl_name_map} SET inj_id=?, inj_active=?, inj_firstname=?, inj_lastname=?, inj_phone=?, status=?, do_merge=? WHERE id = ?;"""
            dbutils.execute(sql2, (emp['inj_id'], emp['active'], emp['firstname'], emp['lastname'], emp['phone'], 'Existing', False, emp['mfg_id']))

    except Exception as e:
        print(f"Error updating emp mapping table: {e}")
        raise
    finally:
        if db and db.conn:
            db.disconnect()


def match_existing_ids():
    sql = """SELECT ie.id AS inj_id, me.id AS mfg_id, ie.firstname, ie.lastname, ie.phone, ie.active
            FROM ramko.emp me
            LEFT JOIN ramkoinj.emp ie ON me.id = ie.id
            WHERE me.active = 1 AND ie.id is not NULL
            ORDER BY me.id;"""

    db = None
    try:
        db = RamkoDb()
        db.connect()
        mfg_emps = db.select(sql)
        for emp in mfg_emps:
            sql2 = f"""UPDATE {tbl_name_map} SET inj_id=?, inj_active=?, inj_firstname=?, inj_lastname=?, inj_phone=?, status=? WHERE id = ?;"""
            dbutils.execute(sql2, (emp['inj_id'], emp['active'], emp['firstname'], emp['lastname'], emp['phone'], 'Conflict', emp['mfg_id']))

    except Exception as e:
        print(f"Error updating emp mapping table: {e}")
        raise
    finally:
        if db and db.conn:
            db.disconnect()


def match_missing():
    sql = """SELECT mu.id AS mfg_id, mu.username, mu.firstname, mu.lastname
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
            sql2 = f"""UPDATE {tbl_name_map} SET inj_id=?, inj_username=?, inj_firstname=?, inj_lastname=?, status=?, do_merge=? WHERE id = ?;"""
            dbutils.execute(sql2, (None, None, None, None, 'Missing', True, user['mfg_id']))

    except Exception as e:
        print(f"Error updating emp mapping table: {e}")
        raise
    finally:
        if db and db.conn:
            db.disconnect()


def make_emp_map_table():
    create_emp_map_table()
    match_existing_ids()
    match_existing_emps()
    # match_missing()

def find_skipped_ids():
    sql = """SELECT id FROM ramkoinj.emp ORDER BY id;"""
    db = None
    free_ids = []
    current_id = 0
    try:
        db = RamkoDb()
        db.connect()
        emps = db.select(sql)
        return emps
    except Exception as e:
        print(f"Error retrieving mfg emp into mapping table: {e}")
        raise


def create_workCategory_map():
    dbutils.execute(f"DROP TABLE IF EXISTS {'workCategory_map'};")
    sql = f"""CREATE TABLE {'workCategory_map'} (
         id INTEGER,
         inj_id INTEGER,
         category TEXT, 
         shop BOOL
         )
         """
    dbutils.execute(sql)

    db = None
    try:
        db = RamkoDb()
        db.connect()
        sql = f"""SELECT m.id, m.category, m.shop
                    FROM ramko.workCategory m;
                """
        mfg_wcs = db.select(sql)
        for wc in mfg_wcs:
            sql2 = f"""INSERT INTO {'workCategory_map'} (id, category, shop) VALUES (?, ?, ?)"""
            dbutils.execute(sql2,(wc['id'], wc['category'], wc['shop']) )

        print(f"Created table: {'workCategory_map'}")
    except Exception as e:
        print(f"Error retrieving mfg wc into mapping table: {e}")
        raise
    finally:
        if db and db.conn:
            db.disconnect()


def add_workCategories():
    db = None
    try:
        inj_host = os.environ.get('DB_INJ_HOST')
        inj_port = os.environ.get('DB_INJ_PORT')
        db = RamkoDb()
        db.connect(host=inj_host, port=inj_port)
        db.execute("DELETE FROM ramkoinj.workCategory WHERE id > 20;")
        sql = f"""INSERT INTO ramkoinj.workCategory (id, category, shop) 
                  VALUES (21, 'Engineering', 1),
                         (22, 'Moldmaker', 1),
                         (23, 'CNC Milling', 1),
                         (24, 'Electrodes', 1),
                         (25, 'CNC EDM', 1),
                         (26, 'Wire EDM', 1),
                         (27, 'General Machining', 1),
                         (29, 'Polishing', 1)
               """
        db.execute(sql)

    except Exception as e:
        print(f"Error retrieving mfg wc into mapping table: {e}")
        raise
    finally:
        if db and db.conn:
            db.disconnect()



def get_next_inj_empid(db):
    sql = """SELECT MAX(id) AS max_id FROM ramkoinj.emp;"""
    result = db.select(sql)
    if result:
        return result[0]['max_id'] + 1
    else:
        return 1


def reassign_inj_id(db, inj_id):
    newid = get_next_inj_empid(db)
    print(f"INJ emp id {inj_id} conflicts with MFG emp id, moving to {newid}")

    cur = None
    try:
        db.conn.begin()
        cur = db.conn.cursor()
        cur.execute(f"""INSERT INTO ramkoinj.emp (id, lastName, firstName, dateOfBirth, street, city, state, zip, phone, wage, active, pin, allowPerm, allowAllJobs, workCategoryId, temp, __st, __ot, __dt, __stI, __otI, __dtI, supervisorEmpId, created, updated, user_id )
                    SELECT {newid} AS id, lastName, firstName, dateOfBirth, street, city, state, zip, phone, wage, active, pin, allowPerm, allowAllJobs, workCategoryId, temp, __st, __ot, __dt, __stI, __otI, __dtI, supervisorEmpId, created, updated, user_id
                    FROM ramkoinj.emp WHERE id = ?""", (inj_id,) )

        cur.execute("UPDATE ramkoinj.user SET empId=? WHERE empId=?;", (newid, inj_id))
        cur.execute("UPDATE ramkoinj.workEntry SET empId=? WHERE empId=?;", (newid, inj_id))
        cur.execute("UPDATE ramkoinj.InvLocation SET emp_id=? WHERE emp_id=?;", (newid, inj_id))
        cur.execute("UPDATE ramkoinj.CustomerItemTrainedEmp SET emp_id=? WHERE emp_id=?;", (newid, inj_id))
        cur.execute("UPDATE ramkoinj.timeCardError SET empId=? WHERE empId=?;", (newid, inj_id))
        cur.execute("UPDATE ramkoinj.Jobs SET Lead=? WHERE Lead=?;", (newid, inj_id))
        cur.execute("UPDATE ramkoinj.clockIn SET empId=? WHERE empId=?;", (newid, inj_id))
        cur.execute("UPDATE ramkoinj.hsv SET empId=? WHERE empId=?;", (newid, inj_id))
        cur.execute("UPDATE ramkoinj.InvTx SET emp_id=? WHERE emp_id=?;", (newid, inj_id))
        cur.execute("UPDATE ramkoinj.Box SET createdEmp_id=? WHERE createdEmp_id=?;", (newid, inj_id))
        cur.execute("UPDATE ramkoinj.Box SET qcEmp_id=? WHERE qcEmp_id=?;", (newid, inj_id))
        cur.execute("UPDATE ramkoinj.Box SET activatedEmp_id=? WHERE activatedEmp_id=?;", (newid, inj_id))
        cur.execute("UPDATE ramkoinj.Box SET updatedEmp_id=? WHERE updatedEmp_id=?;", (newid, inj_id))
        cur.execute("UPDATE ramkoinj.Box SET scannedInEmp_id=? WHERE scannedInEmp_id=?;", (newid, inj_id))
        cur.execute("UPDATE ramkoinj.Box SET deactivatedEmp_id=? WHERE deactivatedEmp_id=?;", (newid, inj_id))

        cur.execute("DELETE FROM ramkoinj.emp WHERE id=?", (inj_id,) )

        cur.close()
        cur = None
        db.conn.commit()

        return newid

    except Exception as e:
        print(f"Error moving emp: {e}")
        if db.conn:
            db.conn.rollback()
        raise

    finally:
        if cur:
            cur.close()


def merge_emps():
    dbmfg = None
    dbinj = None
    print("\nMerging emps...")
    try:
        add_workCategories()
        wc_map = {}
        workcats = dbutils.select(f"SELECT * FROM {'workCategory_map'};")
        for wc in workcats[1]:
            wc_map[wc['id']] = wc['inj_id']

        mfg_host = os.environ.get('DB_MFG_HOST')
        mfg_port = os.environ.get('DB_MFG_PORT')
        inj_host = os.environ.get('DB_INJ_HOST')
        inj_port = os.environ.get('DB_INJ_PORT')
        emps = dbutils.select(f"SELECT * FROM {tbl_name_map} WHERE do_merge = true;")
        dbmfg = RamkoDb()
        dbmfg.connect(host=mfg_host, port=mfg_port)
        dbinj = RamkoDb()
        dbinj.connect(host=inj_host, port=inj_port)
        for emp in emps[1]:
            mfgemps = dbmfg.select("SELECT * FROM ramko.emp WHERE id = ?", (emp['id'],))
            injemps = dbinj.select("SELECT * FROM ramkoinj.emp WHERE id = ?", (emp['id'],))
            if len(injemps) > 0:
                if injemps[0]['active'] == 0:
                    # move inj emp to new id and insert mfg emp as is
                    new_inj_id = reassign_inj_id(dbinj, injemps[0]['id'])
                    emp_id = emp['id']
                    print(f"{emp['id']}, {emp['id']}, {injemps[0]['id']}, {new_inj_id}")
                else:
                    # insert mfg emp with new id and log it
                    newid = get_next_inj_empid(dbinj)
                    print(f"MFG emp id {emp['id']} is being used in INJ, moving to {newid}")
                    emp_id = newid
                    print(f"{emp['id']}, {newid}, {injemps[0]['id']}, {injemps[0]['id']}")
            else:
                # insert mfg emp as is
                emp_id = emp['id']
                print(f"{emp['id']}, {emp_id}, {' '}, {' '}")

            print(f"Merging MFG emp id {emp['id']}")
            dbinj.execute(f"INSERT INTO ramkoinj.emp (id, lastName, firstName, dateOfBirth, street, city, state, zip, phone, wage, active, pin, allowPerm, allowAllJobs, workCategoryId, temp, __st, __ot, __dt, __stI, __otI, __dtI, supervisorEmpId, created, updated, user_id ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                          (emp_id, mfgemps[0]['lastName'], mfgemps[0]['firstName'], mfgemps[0]['dateOfBirth'], mfgemps[0]['street'], mfgemps[0]['city'], mfgemps[0]['state'], mfgemps[0]['zip'], mfgemps[0]['phone'],
                           mfgemps[0]['wage'], mfgemps[0]['active'], mfgemps[0]['pin'], mfgemps[0]['allowPerm'], mfgemps[0]['allowAllJobs'], wc_map.get(mfgemps[0]['workCategoryId'], None), mfgemps[0]['temp'],
                           mfgemps[0]['__st'], mfgemps[0]['__ot'], mfgemps[0]['__dt'], mfgemps[0]['__stI'], mfgemps[0]['__otI'], mfgemps[0]['__dtI'], None, mfgemps[0]['created'], mfgemps[0]['updated'], mfgemps[0]['user_id'] ))

    except Exception as e:
        print(f"Error updating user mapping table: {e}")
        raise
    finally:
        if dbmfg and dbmfg.conn:
            dbmfg.disconnect()
        if dbinj and dbinj.conn:
            dbinj.disconnect()


def update_user_emp():
    dbinj = None
    try:
        inj_host = os.environ.get('DB_INJ_HOST')
        inj_port = os.environ.get('DB_INJ_PORT')
        users = dbutils.select(f"SELECT * FROM {'user_map'} WHERE do_merge = true and empId is not null;")
        emps = dbutils.select(f"SELECT * FROM {'emp_map'} WHERE do_merge = true;")
        new_emps = [emp['id'] for emp in emps[1]]
        dbinj = RamkoDb()
        dbinj.connect(host=inj_host, port=inj_port)
        for user in users[1]:
            if user['empId'] in new_emps:
                print(f"Updating user {user['firstname']} {user['lastname']} with empId {user['empId']}")
                dbinj.execute(f"UPDATE ramkoinj.user SET empId=? WHERE firstname=? AND lastname=?;", (user['empId'], user['firstname'], user['lastname']) )

    except Exception as e:
        print(f"Error updating user mapping table: {e}")
        raise
    finally:
        if dbinj and dbinj.conn:
            dbinj.disconnect()


def update_emp_super():
    dbmfg = None
    dbinj = None
    try:
        mfg_host = os.environ.get('DB_MFG_HOST')
        mfg_port = os.environ.get('DB_MFG_PORT')
        inj_host = os.environ.get('DB_INJ_HOST')
        inj_port = os.environ.get('DB_INJ_PORT')
        emps = dbutils.select(f"SELECT * FROM {'emp_map'} WHERE do_merge = true;")
        new_emps = [emp['id'] for emp in emps[1]]

        dbmfg = RamkoDb()
        dbmfg.connect(host=mfg_host, port=mfg_port)
        dbinj = RamkoDb()
        dbinj.connect(host=inj_host, port=inj_port)
        for emp in emps[1]:
            mfgemps = dbmfg.select("SELECT * FROM ramko.emp WHERE id = ?", (emp['id'],))
            sup_id = mfgemps[0]['supervisorEmpId']
            if sup_id is not None and sup_id > 0 and sup_id in new_emps:
                print(f"Updating emp {emp['id']} supervisor to ID {sup_id}")
                dbinj.execute(f"UPDATE ramkoinj.emp SET supervisorEmpId=? WHERE id=?;", (sup_id, emp['id']))

    except Exception as e:
        print(f"Error updating user mapping table: {e}")
        raise
    finally:
        if dbmfg and dbmfg.conn:
            dbmfg.disconnect()
        if dbinj and dbinj.conn:
            dbinj.disconnect()


def reassign_emp():
    INJ_EMP = 566

    dbinj = None
    try:
        inj_host = os.environ.get('DB_INJ_HOST')
        inj_port = os.environ.get('DB_INJ_PORT')
        dbinj = RamkoDb()
        dbinj.connect(host=inj_host, port=inj_port)

        new_inj_id = reassign_inj_id(dbinj, INJ_EMP)
        print(f"INJ emp {INJ_EMP} reassigned ID {new_inj_id}")
    except Exception as e:
        print(f"Error reassigning inj emp: {e}")
        raise
    finally:
        if dbinj and dbinj.conn:
            dbinj.disconnect()


if __name__ == '__main__':
    import os
    from decouple import config

    os.environ['DB_INJ_HOST'] = "127.0.0.1"
    os.environ['DB_INJ_PORT'] = "3316"
    os.environ['DB_PWD'] = config('MARIADB_ROOT_PASSWORD')

    # reassign_emp()

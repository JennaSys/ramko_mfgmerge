from datetime import datetime
import os

import dbutils
from ramkodb import RamkoDb


tbl_name_map = 'me_map'


def create_me_map_table():
    print("\nCreating me map table...")
    dbutils.execute(f"DROP TABLE IF EXISTS {tbl_name_map};")
    sql = f"""CREATE TABLE {tbl_name_map} (
     id INTEGER,
     inj_job INTEGER,
     inj_po INTEGER,
     mfg_job INTEGER,
     cust_id INTEGER,
     mfg_labor FLOAT,
     mfg_material FLOAT,
     mfg_labor_calc FLOAT,
     mfg_material_calc FLOAT,
     me_amt FLOAT,
     po_amt FLOAT,
     new_amt FLOAT,
     do_merge BOOL
     )
     """
    dbutils.execute(sql)

    dbinj = None
    try:
        inj_host = os.environ.get('DB_INJ_HOST')
        inj_port = os.environ.get('DB_INJ_PORT')
        dbinj = RamkoDb()
        dbinj.connect(host=inj_host, port=inj_port)
        sql = f"""SELECT *
                    FROM ramkoinj.Material_Entry me
                    WHERE me.id between 453452 and 453629 and me.description like 'T&M Merge from MFG job %'
                    ORDER BY me.id
                """
        mes = dbinj.select(sql)
        for me in mes:
            sql2 = f"""INSERT INTO {tbl_name_map} (id, inj_job, mfg_job, me_amt, do_merge) VALUES (?, ?, ?, ?, ?)"""
            dbutils.execute(sql2,(me['id'], me['jobId'], me['description'].split()[5], float(me['amount']), True) )

        print(f"Created table: {tbl_name_map}")
    except Exception as e:
        print(f"Error retrieving inj mes into mapping table: {e}")
        raise
    finally:
        if dbinj and dbinj.conn:
            dbinj.disconnect()


def get_perm_job_amt():
    db = None
    print("\nUpdating MFG Perm job T&M...")
    try:
        mfg_host = os.environ.get('DB_MFG_HOST')
        mfg_port = os.environ.get('DB_MFG_PORT')
        db = RamkoDb()
        db.connect(host=mfg_host, port=mfg_port)

        sql = """SELECT j.Job_Number, j.customerId, j.labor, j.material, l.labor_calc, m.material_calc
FROM ramko.Jobs j
LEFT JOIN (SELECT wej.jobId,
                  IFNULL(cast((SUM(wej.__st * e.`__st`) + SUM(wej.__ot * e.`__ot`) +
                               SUM(wej.__dt * e.`__dt`)) as decimal(20, 8)), 0) AS labor_calc
           FROM ramko.workEntryJob wej
                    LEFT JOIN ramko.workEntry we ON wej.workEntryId = we.id
                    LEFT JOIN ramko.emp e ON we.empId = e.id
           WHERE wej.jobId between 460100 and 460112
             AND we.__shiftDate >= '2026-07-01'
           GROUP BY wej.jobId) l ON j.Job_Number=l.jobId
LEFT JOIN (SELECT jobId, SUM(amount) AS material_calc FROM ramko.Material_Entry WHERE jobId between 460100 and 460112 AND date >= '2026-07-01' GROUP BY jobId) m ON j.Job_Number=m.jobId
WHERE j.Job_Number between 460100 and 460112;"""

        perm_jobs = db.select(sql)

        sql2 = f"""UPDATE {tbl_name_map} SET inj_job=?, cust_id=?, mfg_labor=?, mfg_material=?, mfg_labor_calc=?, mfg_material_calc=?, new_amt=? WHERE mfg_job=?"""
        for job in perm_jobs:
            print(f"Updating MFG job {job['Job_Number']}")
            labor = float(0 if job['labor_calc'] is None else job['labor_calc'])
            material = float(0 if job['material_calc'] is None else job['material_calc'])
            job_id = job['Job_Number']-200000
            if job_id == 260112:
                job_id = 260111
            dbutils.execute(sql2, (job_id, job['customerId'], float(0 if job['labor'] is None else job['labor']), float(0 if job['material']is None else job['material']), labor, material, labor + material, job['Job_Number']) )

    except Exception as e:
        print(f"Error retrieving mfg job amt: {e}")
        raise
    finally:
        if db and db.conn:
            db.disconnect()


def update_job_amt():
    dbmfg = None
    print("\nUpdating MFG T&M...")
    try:
        mfg_host = os.environ.get('DB_MFG_HOST')
        mfg_port = os.environ.get('DB_MFG_PORT')
        jobs = dbutils.select(f"SELECT * FROM {tbl_name_map} WHERE cust_id IS NULL ORDER BY mfg_job;")
        dbmfg = RamkoDb()
        dbmfg.connect(host=mfg_host, port=mfg_port)
        for job in jobs[1]:
            print(f"Updating MFG job {job['mfg_job']}")
            mfg_job = dbmfg.select("""SELECT j.Job_Number, j.customerId, j.labor, j.material, l.labor_calc, m.material_calc
FROM ramko.Jobs j
LEFT JOIN (SELECT wej.jobId,
                  IFNULL(cast((SUM(wej.__st * e.`__st`) + SUM(wej.__ot * e.`__ot`) +
                               SUM(wej.__dt * e.`__dt`)) as decimal(20, 8)), 0) AS labor_calc
           FROM ramko.workEntryJob wej
                    LEFT JOIN ramko.workEntry we ON wej.workEntryId = we.id
                    LEFT JOIN ramko.emp e ON we.empId = e.id
           GROUP BY wej.jobId) l ON j.Job_Number=l.jobId
LEFT JOIN (SELECT jobId, SUM(amount) AS material_calc FROM ramko.Material_Entry GROUP BY jobId) m ON j.Job_Number=m.jobId
WHERE j.Job_Number = ?;""", (job['mfg_job'],))


            sql2 = f"""UPDATE {tbl_name_map} SET cust_id=?, mfg_labor=?, mfg_material=?, mfg_labor_calc=?, mfg_material_calc=?, new_amt=? WHERE mfg_job=?"""
            labor = float(0 if mfg_job[0]['labor_calc'] is None else mfg_job[0]['labor_calc'])
            material = float(0 if mfg_job[0]['material_calc'] is None else mfg_job[0]['material_calc'])
            dbutils.execute(sql2, (mfg_job[0]['customerId'], float(0 if mfg_job[0]['labor'] is None else mfg_job[0]['labor']), float(0 if mfg_job[0]['material']is None else mfg_job[0]['material']), labor, material, labor + material, mfg_job[0]['Job_Number']) )

    except Exception as e:
        print(f"Error updating vendor mapping table: {e}")
        raise
    finally:
        if dbmfg and dbmfg.conn:
            dbmfg.disconnect()


def fix_inj_jobs():

    ...


def fix_perm_jobs():
    # 460100-460112 -> 260100-260111
    ...


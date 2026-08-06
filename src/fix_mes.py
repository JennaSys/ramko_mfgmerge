from datetime import datetime
import os
import json

import dbutils
from ramkodb import RamkoDb


tbl_name_map = 'me_map'


def create_me_map_table():
    print("\nCreating me map table...")
    dbutils.execute(f"DROP TABLE IF EXISTS {tbl_name_map};")
    sql = f"""CREATE TABLE {tbl_name_map} (
     id INTEGER,
     inj_job INTEGER,
     mfg_po TEXT,
     inj_po INTEGER,
     inj_po_lines JSON,
     me_count INTEGER,
     po_amt FLOAT,
     mfg_job INTEGER,
     cust_id INTEGER,
     mfg_labor FLOAT,
     mfg_material FLOAT,
     mfg_labor_calc FLOAT,
     mfg_material_calc FLOAT,
     me_amt FLOAT,
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
            print(f"Updating map MFG job {job['Job_Number']}")
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


def get_inj_po(po_number):
    data = po_number.strip().split(' ')
    po = data[1] if data[0] == 'PO' else data[0]
    return int(po.split('-')[0])


def get_inj_po_lines(po_number):
    lines=[]
    data = po_number.strip().split(' LN ')
    if len(data) > 1:
        data2 = data[1].split('/ ')[0].strip()
        prev_no = None
        line_range = False
        for c in data2:
            if c == ' ':
                continue

            if c == '&':
                continue

            if c == '-':
                line_range = True

            if c.isdigit():
                if line_range:
                    for line in range(prev_no + 1, int(c) + 1):
                        lines.append(line)
                else:
                    lines.append(int(c))
                    prev_no =int(c)

    return lines


def get_inj_po_amt(job_id, po_id, po_lines):
    dbinj = None
    try:
        inj_host = os.environ.get('DB_INJ_HOST')
        inj_port = os.environ.get('DB_INJ_PORT')
        dbinj = RamkoDb()
        dbinj.connect(host=inj_host, port=inj_port)
        sql = f"""SELECT COUNT(id) as me_count, SUM(amount) as total
FROM ramkoinj.Material_Entry
WHERE jobId=? AND source='PoReceiptItem' AND sourceRef IS NOT NULL AND SUBSTRING_INDEX(sourceRef,'-',1)=?"""
        if len(po_lines) > 0:
            sql = sql + f" AND SUBSTRING_INDEX(sourceRef,'-',-1) IN ({str(po_lines)[1:-1]})"
        sql = sql + ";"
        result = dbinj.select(sql, (job_id, po_id))
        amt = result[0]['total'] if result else 0
        me_count = result[0]['me_count'] if result else 0
        return me_count, amt

    except Exception as e:
        print(f"Error retrieving inj mes into mapping table: {e}")
        raise
    finally:
        if dbinj and dbinj.conn:
            dbinj.disconnect()


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
            print(f"Updating map MFG job {job['mfg_job']}")
            mfg_job = dbmfg.select("""SELECT j.Job_Number, j.customerId, j.PONumber, j.labor, j.material, l.labor_calc, m.material_calc
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


            sql2 = f"""UPDATE {tbl_name_map} SET cust_id=?, mfg_po=?, inj_po=?, inj_po_lines=?, me_count=?, po_amt=?, mfg_labor=?, mfg_material=?, mfg_labor_calc=?, mfg_material_calc=?, new_amt=? WHERE mfg_job=?"""
            labor = float(0 if mfg_job[0]['labor_calc'] is None else mfg_job[0]['labor_calc'])
            material = float(0 if mfg_job[0]['material_calc'] is None else mfg_job[0]['material_calc'])
            po = get_inj_po(mfg_job[0]['PONumber']) if mfg_job[0]['customerId']==216 else None
            lines = get_inj_po_lines(mfg_job[0]['PONumber']) if mfg_job[0]['customerId']==216 else None
            po_amt_data = get_inj_po_amt(job['inj_job'], po, lines) if mfg_job[0]['customerId']==216 else None
            po_me_count = po_amt_data[0] if po_amt_data else None
            po_amt = float(po_amt_data[1]) if po_amt_data and po_amt_data[1] is not None else None
            dbutils.execute(sql2, (mfg_job[0]['customerId'], mfg_job[0]['PONumber'], po, json.dumps(lines), po_me_count, po_amt, float(0 if mfg_job[0]['labor'] is None else mfg_job[0]['labor']), float(0 if mfg_job[0]['material']is None else mfg_job[0]['material']), labor, material, labor + material, mfg_job[0]['Job_Number']) )

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


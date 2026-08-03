from datetime import datetime
import os

import dbutils
from ramkodb import RamkoDb

tbl_name_map = 'job_map'

# all active jobs
# merge non inj jobs
# map inj jobs - extract inj job from po number - PO -> job allocation
# add one T&M ME for each active jobname

def create_job_map_table():
    print("\nCreating jobs map table...")
    dbutils.execute(f"DROP TABLE IF EXISTS {tbl_name_map};")
    sql = f"""CREATE TABLE {tbl_name_map} (
     Job_Number INTEGER,
     inj_job INTEGER,
     inj_po INTEGER,
     customerId INTEGER,
     customerPartNo TEXT,
     inj_pn TEXT,
     PONumber TEXT,
     Active BOOL,
     labor FLOAT,
     material FLOAT,
     do_merge BOOL
     )
     """
    dbutils.execute(sql)

    db = None
    try:
        mfg_host = os.environ.get('DB_MFG_HOST')
        mfg_port = os.environ.get('DB_MFG_PORT')
        db = RamkoDb()
        db.connect(host=mfg_host, port=mfg_port)
        sql = f"""SELECT Job_Number, customerId, customerPartNo, PONumber, Active, labor, material
                    FROM ramko.Jobs j
                    WHERE j.Active=1
                    ORDER BY j.Job_Number
                """
        mfg_jobs = db.select(sql)
        for job in mfg_jobs:
            sql2 = f"""INSERT INTO {tbl_name_map} (Job_Number, inj_job, inj_po, customerId, customerPartNo, inj_pn, PONumber, Active, labor, material, do_merge) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
            dbutils.execute(sql2,(job['Job_Number'], None, None, job['customerId'], job['customerPartNo'], None, job['PONumber'], job['Active'], 0 if job['labor'] is None else float(job['labor']), 0 if job['material'] is None else float(job['material']), True) )

        print(f"Created table: {tbl_name_map}")
    except Exception as e:
        print(f"Error retrieving mfg jobs into mapping table: {e}")
        raise
    finally:
        if db and db.conn:
            db.disconnect()


def get_inj_po(po_number):
    data = po_number.strip().split(' ')
    po = data[1] if data[0] == 'PO' else data[0]
    return int(po.split('-')[0])


def get_inj_job(po_number, pn):
    po_number = 13590 if po_number == 15390 else po_number
    dbinj = None
    try:
        inj_host = os.environ.get('DB_INJ_HOST')
        inj_port = os.environ.get('DB_INJ_PORT')
        dbinj = RamkoDb()
        dbinj.connect(host=inj_host, port=inj_port)
        items = dbinj.select("SELECT job_id, inv, vendorPartId FROM ramkoinj.PoItem WHERE po_id=?", (po_number,))
        result: set =  {item['job_id'] if item['job_id'] is not None else 'Inventory' if item['inv'] else None for item in items}
        return sorted(result, key=str)[-1] if len(result) > 0 else 'Invalid PO'

    except Exception as e:
        print(f"Error retrieving mfg jobs into mapping table: {e}")
        raise
    finally:
        if dbinj and dbinj.conn:
            dbinj.disconnect()


def get_inj_pn(job_id):
    dbinj = None
    try:
        inj_host = os.environ.get('DB_INJ_HOST')
        inj_port = os.environ.get('DB_INJ_PORT')
        dbinj = RamkoDb()
        dbinj.connect(host=inj_host, port=inj_port)
        jobs = dbinj.select("SELECT customerPartNo FROM ramkoinj.Jobs WHERE Job_Number=?", (job_id,))
        return jobs[0]['customerPartNo']

    except Exception as e:
        print(f"Error retrieving mfg jobs into mapping table: {e}")
        raise
    finally:
        if dbinj and dbinj.conn:
            dbinj.disconnect()


def get_inj_cust_id(cust_id):
    try:
        cust = dbutils.select(f"SELECT inj_id FROM {'cust_map'} WHERE id = {cust_id};")
        return cust[1][0]['inj_id']

    except Exception as e:
        print(f"Error retrieving mfg cust mapping table: {e}")
        raise


def map_inj_jobs():
    INJ_CUST_ID = 216
    print("\nMepping jobs...")
    try:
        inj_jobs = dbutils.select(f"SELECT * FROM {tbl_name_map} WHERE customerId = {INJ_CUST_ID};")
        # print(f"MFG Job, INJ PO, INJ Job")
        for job in inj_jobs[1]:
            po = get_inj_po(job['PONumber'])
            inj_job = get_inj_job(po, job['customerPartNo'])

            inj_pn = None
            if inj_job == 'Inventory':
                if job['Job_Number'] in [460170, 460360, 460361, 460365, 460383, 460402, 460442]:
                    inj_job = 260102
                    inj_pn = get_inj_pn(inj_job)
            elif inj_job == 'Invalid PO':
                if job['Job_Number'] in [460412]:
                    inj_job = 262016
                    inj_pn = get_inj_pn(inj_job)
            else:
                inj_pn = get_inj_pn(inj_job)

            # print(f"{job['Job_Number']}, {po}, {inj_job}")

            if inj_pn is not None:
                dbutils.execute(f"UPDATE {tbl_name_map} SET inj_po=?, inj_job=?, inj_pn=? WHERE Job_Number=?;", (po, inj_job, inj_pn, job['Job_Number']))

    except Exception as e:
        print(f"Error updating job mapping table: {e}")
        raise


def merge_jobs():
    MFG_VENDOR_ID = 366
    USER_ID = 1058

    dbmfg = None
    dbinj = None
    try:
        mfg_host = os.environ.get('DB_MFG_HOST')
        mfg_port = os.environ.get('DB_MFG_PORT')
        inj_host = os.environ.get('DB_INJ_HOST')
        inj_port = os.environ.get('DB_INJ_PORT')
        jobs = dbutils.select(f"SELECT * FROM {tbl_name_map} WHERE do_merge = true;")
        dbmfg = RamkoDb()
        dbmfg.connect(host=mfg_host, port=mfg_port)
        dbinj = RamkoDb()
        dbinj.connect(host=inj_host, port=inj_port)
        print("\nMerging jobs...")
        print(f"MFG Job, INJ Job, INJ PO, MFG Cust, INJ Cust")
        for job in jobs[1]:
            mfg_job = dbmfg.select("SELECT * FROM ramko.Jobs WHERE Job_Number = ?", (job['Job_Number'],) )
            if job['inj_job'] is None:
                # Add MFG job to INJ DB
                job_id = job['Job_Number']
                cust_id = get_inj_cust_id(job['customerId'])
                dbinj.execute(f"""INSERT INTO ramkoinj.Jobs (Job_Number, customerId, customerPartNo, quantity, Open_Date, Start_Date, Due_Date, Ship_Date,
                                        Job_Description, Active, Lead, PONumber, QuoteNo, TMValue, tooling, passThru, Terms, POReceived, DepositReceived,
                                        OnHold, audited, invoiced, poAmount, permjob, partsjob, shipToAddress, officeNotes, __FullTextSearch, __IdFixed,
                                        updated, created, labor, laborInclusive, material, samples, files, activityLog, deleted, productionReady) 
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (mfg_job[0]['Job_Number'], cust_id, mfg_job[0]['customerPartNo'], mfg_job[0]['quantity'], mfg_job[0]['Open_Date'], mfg_job[0]['Start_Date'], mfg_job[0]['Due_Date'], mfg_job[0]['Ship_Date'],
                             mfg_job[0]['Job_Description'], mfg_job[0]['Active'], mfg_job[0]['Lead'], mfg_job[0]['PONumber'], mfg_job[0]['QuoteNo'], mfg_job[0]['TMValue'],
                             mfg_job[0]['tooling'], mfg_job[0]['passThru'], mfg_job[0]['Terms'], mfg_job[0]['POReceived'], mfg_job[0]['DepositReceived'],
                             mfg_job[0]['OnHold'], mfg_job[0]['audited'], mfg_job[0]['invoiced'], mfg_job[0]['poAmount'], mfg_job[0]['permjob'], mfg_job[0]['partsjob'],
                             mfg_job[0]['shipToAddress'], mfg_job[0]['officeNotes'], mfg_job[0]['__FullTextSearch'], mfg_job[0]['__IdFixed'],
                             mfg_job[0]['updated'], mfg_job[0]['created'], mfg_job[0]['labor'], mfg_job[0]['laborInclusive'], mfg_job[0]['material'],
                             mfg_job[0]['samples'], mfg_job[0]['files'], mfg_job[0]['activityLog'], mfg_job[0]['deleted'], mfg_job[0]['productionReady'], ))
            else:
                # Use existing INJ Job
                cust_id = ''
                job_id = job['inj_job']

            print(f"{job['Job_Number']}, {job_id}, {'' if job['inj_po'] is None else job['inj_po']}, {job['customerId']}, {cust_id}")

            # Add T&M ME
            curr_date = datetime.now().strftime('%Y-%m-%d')
            amt = job['labor'] + job['material']
            desc = f"T&M Merge from MFG job {job['Job_Number']} (labor: {job['labor']:.2f} / matl: {job['material']:.2f})"
            dbinj.execute(
                f"INSERT INTO ramkoinj.Material_Entry (jobId, vendorId, description, date, amount, dateEntered, source, createdBy_id, scrap) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (job_id, MFG_VENDOR_ID, desc, curr_date, amt, f"{curr_date} 00:00:00", "Manual", USER_ID, False))

    except Exception as e:
        print(f"Error updating vendor mapping table: {e}")
        raise
    finally:
        if dbmfg and dbmfg.conn:
            dbmfg.disconnect()
        if dbinj and dbinj.conn:
            dbinj.disconnect()

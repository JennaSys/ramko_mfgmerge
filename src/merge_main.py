from decouple import config

from merge_user import make_user_map_table, merge_users
from src import merge_user
from src.fix_mes import fix_perm_jobs, create_me_map_table, get_perm_job_amt, update_job_amt, fix_inj_no_me_jobs
from src.merge_cust import create_cust_map_table, match_existing_customers, merge_customers
from src.merge_emp import make_emp_map_table, merge_emps, update_user_emp, update_emp_super
from src.merge_jobs import create_job_map_table, map_inj_jobs, merge_jobs
from src.merge_vendor import create_vendor_map_table, match_existing_vendors, merge_vendors


def main():
    # -make_user_map_table()
    # -merge_users()
    # -make_emp_map_table()

    # merge_emps()
    # update_user_emp()
    # update_emp_super()

    # -create_cust_map_table()
    # -match_existing_customers()
    # merge_customers()

    # -create_vendor_map_table()
    # -match_existing_vendors()
    # merge_vendors()

    # create_job_map_table()
    # map_inj_jobs()
    # merge_jobs()

    # create_me_map_table()
    # get_perm_job_amt()
    # update_job_amt()
    fix_inj_no_me_jobs()
    # fix_perm_jobs()

def setup_dev_env():
    import os

    DB_LOC = '../'
    DB_NAME = 'merge.db'

    os.environ['DB_FILE'] = os.path.join(DB_LOC, DB_NAME)
    os.environ['DB_MFG_HOST'] = "127.0.0.1"
    os.environ['DB_MFG_PORT'] = "3326"
    os.environ['DB_INJ_HOST'] = "127.0.0.1"
    os.environ['DB_INJ_PORT'] = "3316"
    os.environ['DB_PWD'] = config('MARIADB_ROOT_PASSWORD')


if __name__ == '__main__':
    setup_dev_env()
    main()

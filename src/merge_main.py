from decouple import config

from merge_user import make_user_map_table, merge_users
from src import merge_user
from src.merge_emp import make_emp_map_table, merge_emps, update_user_emp, update_emp_super


def main():
    # make_user_map_table()
    # merge_users()
    # make_emp_map_table()

    merge_emps()
    update_user_emp()
    update_emp_super()


def setup_dev_env():
    import os

    DB_LOC = '../'
    DB_NAME = 'merge.db'

    os.environ['DB_FILE'] = os.path.join(DB_LOC, DB_NAME)
    os.environ['DB_MFG_HOST'] = "127.0.0.1"
    os.environ['DB_MFG_PORT'] = "3306"
    os.environ['DB_INJ_HOST'] = "127.0.0.1"
    os.environ['DB_INJ_PORT'] = "3306"
    os.environ['DB_PWD'] = config('MARIADB_ROOT_PASSWORD')


if __name__ == '__main__':
    setup_dev_env()
    main()

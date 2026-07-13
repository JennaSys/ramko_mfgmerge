import sqlite3
import os
import logging


if __name__ == "__main__":
    fmt = "[%(asctime)s]|%(levelname)s|[%(module)s]:%(funcName)s()|%(message)s"
    logging.basicConfig(format=fmt, level=logging.DEBUG)
log = logging.getLogger(__name__)


def connect():
    DB_FILE = os.environ.get("DB_FILE")
    if not os.path.exists(DB_FILE):
        log.warning("Creating new DB")

        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()

            # sqlite foreign key support is off by default
            cur.execute("PRAGMA foreign_keys = ON")
            conn.commit()


def execute(stmt, params=()):
    DB_FILE = os.environ.get("DB_FILE")
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            curs = conn.cursor()
            curs.execute(stmt, params)
            rowcount = curs.rowcount
            curs.close()
            conn.commit()
        return 'success', rowcount
    except Exception as e:
        log.error(e)
        # return 'error', str(e)
        raise


def select(stmt, params=()):
    DB_FILE = os.environ.get("DB_FILE")
    try:
        with sqlite3.connect(DB_FILE) as conn:
            curs = conn.cursor()
            curs.execute(stmt, params)
            desc = curs.description
            cols = [fld[0] for fld in desc]
            rowset = curs.fetchall()
            rows = [dict(zip(cols, row)) for row in rowset]
            curs.close()
        return 'success', rows
    except Exception as e:
        log.error(e)
        # return 'error', str(e)
        raise


def _main():
    DB_FILE = os.environ.get("DB_FILE")
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        sql = "SELECT name FROM sqlite_master WHERE type = ?"
        cur.execute(sql, ('table',))
        data = cur.fetchall()
        print('Tables:', [tbl[0] for tbl in data])


if __name__ == '__main__':
    DB_LOC = '../'
    DB_NAME = 'merge.db'

    os.environ['DB_FILE'] = os.path.join(DB_LOC, DB_NAME)

    connect()
    _main()

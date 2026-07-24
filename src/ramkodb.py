import mariadb  # https://mariadb-corporation.github.io/mariadb-connector-python/
import mariadb.constants.CLIENT as CLIENT
import os
import logging

if __name__ == "__main__":
    fmt = "[%(asctime)s]|%(levelname)s|[%(module)s]:%(funcName)s()|%(message)s"
    logging.basicConfig(format=fmt, level=logging.DEBUG)
log = logging.getLogger(__name__)

DB_UID = "root"

class RamkoDb:
    def __init__(self):
        self.conn = None

    def connect(self, host='127.0.0.1', port='3306', multi=False):
        try:
            conn_params = {
                "user": DB_UID,
                "password": os.environ.get("DB_PWD"),
                "host": host,
                "port": int(port),
                # "database": os.environ.get("DB_DATABASE")
            }

            if multi:
                conn_params['client_flag'] = CLIENT.MULTI_STATEMENTS

            self.conn = mariadb.connect(**conn_params)

        except mariadb.Error as e:
            log.error(e)
        except Exception as e:
            log.exception(e)

    def disconnect(self):
        try:
            self.conn.close()
        except mariadb.Error as e:
            log.error(e)
        except Exception as e:
            log.exception(e)


    def execute(self, sql, params=None):
        cur = None
        try:
            self.conn.begin()
            cur = self.conn.cursor()
            cur.execute(sql, params)
            rowcount = cur.rowcount
            lastrowid = cur.lastrowid
            cur.close()
            cur = None
            self.conn.commit()
            return 'success', {'rowcount': rowcount, 'lastrowid': lastrowid}
        except Exception as e:
            log.error(e)
            if self.conn:
                self.conn.rollback()
            raise
        finally:
            if cur:
                cur.close()


    def select(self, sql, params=None):
        cur = None
        try:
            cur = self.conn.cursor()
            cur.execute(sql, params)
            result = cur.fetchall()
            cols = [fld[0] for fld in cur.description]
            rows = [dict(zip(cols, row)) for row in result]
            return rows
        except Exception as e:
            log.error(e)
            raise
        finally:
            if cur:
                cur.close()


    def get_seq(self, tbl_name: str):
        new_id = None
        try:
            result = self.select(f"SELECT nextId FROM Sequence WHERE sequenceName=?;", (tbl_name,))
            if result:
                new_id = result[0]['nextId']
                self.execute(f"UPDATE Sequence SET nextId=? WHERE sequenceName=?;", (new_id + 1, tbl_name))

            return new_id
        except Exception as e:
            log.error(e)
            raise


def main():
    ramko_db = None
    try:
        ramko_db = RamkoDb()
        ramko_db.connect()
        # cur = conn.cursor()
        # cur.execute("SELECT id, name FROM customer;")
        # row = cur.fetchone()
        # print(*row, sep=' ')
        # cur.close()

        result = ramko_db.select("SELECT id, name FROM ramko.customer;")
        if result:
            print(result[0])
    except Exception as e:
        print(e)
    finally:
        if ramko_db.conn:
            ramko_db.disconnect()


if __name__ == '__main__':
    from decouple import config

    os.environ['DB_PWD'] =  config('MARIADB_ROOT_PASSWORD')
    os.environ['DB_HOST'] = "127.0.0.1"
    # os.environ['DB_DATABASE'] = "ramkoinj"
    main()

import time

from core.settings import Config as cf
from etl import update_vars
from mwstables import Tables
from core.settings import settings


class Sceduler:
    """ """

    def __init__(self, token: str) -> None:
        """ """

        self.token = token
        self.tb = Tables(token)
        self.curr_pos = 0

    def run(self):
        """ """

        print("Start app")

        while True:
            try:
                info = self.tb.get_table_info(cf.IDEAS_TABLE_ID)
                total = info.get("total")

                if total > self.curr_pos:
                    print("Table is update")
                    time.sleep(10)
                    update_vars(self.token)
                    self.curr_pos = total
                print(f"tick - {time.time}")
                time.sleep(10)
            except KeyboardInterrupt:
                break

        print("Stop app")


if __name__ == "__main__":

    sc = Sceduler(settings.mts__token)

    sc.run()

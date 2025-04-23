from requests.exceptions import JSONDecodeError, ConnectionError

from etl import Extractor
from core.settings import settings

class Sceduler:
    """ """

    def __init__(self, token: str) -> None:
        """ """

        self.token = token
        self.ex = Extractor(token)

    def run(self):
        """ """

        print("Start app")

        while True:
            try:
                ideas_set = self.ex.get_ideas_set()
                var_ideas_set = self.ex.check_variants()
                delta: set[str] =  ideas_set.difference(var_ideas_set)

                if delta:
                    print("New ideas have been discovered")
                    ideas_dict = self.ex.get_ideas_dict(list(delta))
                    for idea_name in ideas_dict:
                        print(f"New idea object: {idea_name}")
                    self.ex.update_vars(ideas_dict)
                else:
                    print("No new ideas have been discovered")
                
            except KeyboardInterrupt:
                break
            except IndexError as e:
                print(e)
            except (JSONDecodeError, ConnectionError) as e:
                print(f"API error {e}")
            

        print("Stop app")


if __name__ == "__main__":

    sc = Sceduler(settings.mts__token)

    sc.run()

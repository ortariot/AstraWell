import math

from core.settings import Config as cf
from mwstables import Tables
from utils import filter_list_by_idea, get_extremums


class Extractor:
    """"""
    def __init__(self, token):
        """"""
        self.tb = Tables(token)


    def get_top_3_hotels_by_idea(
        self,
        hotel_recs: list, idea_name: str, idea_id
    ) -> list[dict]:
        """ """

        filtred_hotel_recs = filter_list_by_idea(hotel_recs, idea_name)

        if not filtred_hotel_recs:
            return []

        prices = list(
            map(lambda x: x.get("fields").get("price_per_day"), filtred_hotel_recs)
        )
        stars = list(
            map(lambda x: x.get("fields").get("stars"), filtred_hotel_recs)
        )

        min_price, _, delta_price = get_extremums(prices)
        min_stars, _, delta_stars = get_extremums(stars)

        hotel_rate_recs = []

        for rec in filtred_hotel_recs:
            hotel_id = rec.get("recordId")
            fields = rec.get("fields")
            price_per_day = fields.pop("price_per_day")
            star = fields.pop("stars")
            norm_price = 1 - (price_per_day - min_price) / delta_price
            norm_stars = 1 - (star - min_stars) / delta_stars

            rate = round(norm_price * 4 + norm_stars * 6, 2)

            fields["rate"] = rate
            fields["hotel"] = [hotel_id]
            hotel_name = fields.pop("hotel_name")
            fields.pop("Идея")
            fields["idea"] = [idea_id]
            fields["name"] = f"{idea_name} in {hotel_name}"
            fields.pop("User")

            hotel_rate_recs.append({"fields": fields})

        hotel_rate_recs.sort(
            key=lambda x: x.get("fields", {}).get("rate"), reverse=True
        )

        return hotel_rate_recs[:3]


    def get_top_3_flights_by_idea(
        self,
        flight_recs: list, idea_name: str, idea_id
    ) -> list[dict]:
        """ """

        filtred_flights_recs = filter_list_by_idea(flight_recs, idea_name)

        if not filtred_flights_recs:
            return []

        prices = list(
            map(lambda x: x.get("fields").get("price"), filtred_flights_recs)
        )

        min_price, _, delta_price = get_extremums(prices)

        flight_rate_recs = []

        for rec in filtred_flights_recs:
            flight_id = rec.get("recordId")
            fields = rec.get("fields")
            price = fields.pop("price")
            norm_price = 1 - (price - min_price) / delta_price
            rate = round(norm_price * 10, 2)
            fields["rate"] = rate
            fields["flight"] = flight_id
            fields["idea"] = [idea_id]
            fields.pop("User")
            fields.pop("Идея")

            flight_rate_recs.append(fields)

        flight_rate_recs.sort(key=lambda x: x.get("rate"), reverse=True)

        return list(map(lambda x: x.get("flight"), flight_rate_recs[:3]))


    def fetch_all_recs(
        self,
        info: dict[str, str],
        data_func,
        table_id,
        page_size: int = 1000,
        ) -> list[dict]:
        """"""
        all_recs = []
        
        total = info.get("total", page_size)

        page_count = math.floor(total / page_size)
        
        for page_num in range(1, page_count + 2):
            recs_page = data_func(
                table_id, add_params={"pageSize": page_size, "pageNum": page_num}
            )
            
            all_recs += recs_page
        
        return all_recs


    def update_vars(self, ideas_dict: dict) -> None:
        """ """
    # Получаем записи по гостиницам
    
        hotel_info = self.tb.get_table_info(cf.HOTEL_TABLE_ID)    
        hotel_recs = self.fetch_all_recs(hotel_info, self.tb.get_records, cf.HOTEL_TABLE_ID)
    
    # Получаем записи по рейсам
    
        flight_info = self.tb.get_table_info(cf.FLIGHTS_TABLE_ID)
        flight_recs = self.fetch_all_recs(flight_info, self.tb.get_records, cf.FLIGHTS_TABLE_ID)

    # Рассчитываем варианты

        for idea_name, idea_id in ideas_dict.items():
                # print(idea_name)
            if not idea_name:
                continue
            top_3_f = self.get_top_3_flights_by_idea(
                flight_recs, idea_name, idea_id
            )
            top_3_res = self.get_top_3_hotels_by_idea(
                hotel_recs, idea_name, idea_id
            )

            if not top_3_res:
                print(f"There are no suitable hotels for the idea {idea_name}")
                continue
            
            if not top_3_f:
                print(f"There are no suitable flights for the idea {idea_name}")
                continue
            
            for res in top_3_res:
                res["fields"]["flight"] = [top_3_f[0]]
                
            self.tb.add_records(cf.VARIANT_TABLE_ID, top_3_res)
                
                
    def get_ideas_set(self) -> set[str]:
        """"""
        ideas_recs = self.tb.get_records(
            cf.IDEAS_TABLE_ID,
            add_params={"pageSize": 1000},
            )
        
        return set(map(lambda x: x.get("recordId"), ideas_recs))
    
    
    def get_ideas_dict(self, record_ids: list = []) -> dict[str, str]:
        """"""
        ideas_recs = self.tb.get_records(
            cf.IDEAS_TABLE_ID,
            add_params={
                "pageSize": 1000,
                "recordIds": record_ids,
                },
            )
        
        return dict(
            map(
                lambda x: (x.get("fields").get("name"), x.get("recordId")),
                ideas_recs
                )
            )
        
    def check_variants(self) -> set[str]:
        """"""
        variant_recs = self.tb.get_records(cf.VARIANT_TABLE_ID, add_params={"pageSize": 1000})
        return set(map(lambda x: x.get("fields", {}).get("idea", [])[0], variant_recs))
    

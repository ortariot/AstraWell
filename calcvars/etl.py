from core.settings import Config as cf
from mwstables import Tables
from utils import filter_list_by_idea, get_extremums


def get_top_3_hotels_by_idea(
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


def update_vars(TOKEN: str) -> None:
    """ """

    tb = Tables(TOKEN)

    # Получаем список идей из таблицы

    idea_recs = tb.get_records(
        cf.IDEAS_TABLE_ID, add_params={"pageSize": 1000}
    )
    idea_list = list(
        filter(
            lambda x: x,
            map(
                lambda x: {x.get("fields").get("name"): x.get("recordId")},
                idea_recs,
            ),
        )
    )

    # Получаем записи по гостиницам
    hotel_recs = tb.get_records(
        cf.HOTEL_TABLE_ID, add_params={"pageSize": 1000}
    )

    # Получаем записи по рейсам

    flight_recs = tb.get_records(
        cf.FLIGHTS_TABLE_ID, add_params={"pageSize": 1000}
    )

    # Рассчитываем варианты

    tb.erase_table(cf.VARIANT_TABLE_ID)

    for idea in idea_list:
        for idea_name, idea_id in idea.items():
            top_3_f = get_top_3_flights_by_idea(
                flight_recs, idea_name, idea_id
            )
            top_3_res = get_top_3_hotels_by_idea(
                hotel_recs, idea_name, idea_id
            )

            if not top_3_res:
                continue

            for res in top_3_res:
                res["fields"]["flight"] = [top_3_f[0]]

            tb.add_records(cf.VARIANT_TABLE_ID, top_3_res)


if __name__ == "__main__":

    from pprint import pprint

    TOKEN = "uskcpZ2JD2FZUXTVQ3Hd8WA"

    update_vars(TOKEN)

    # Получаем список идей из таблицы

    # idea_recs = tb.get_records(cf.IDEAS_TABLE_ID, add_params={'pageSize': 1000})
    # idea_list = list(filter(lambda x: x, map(lambda x: {x.get('fields').get('name'): x.get('recordId')}, idea_recs)))

    # # Получаем записи по гостиницам
    # hotel_recs = tb.get_records(cf.HOTEL_TABLE_ID, add_params={'pageSize': 1000})

    # # Получаем записи по рейсам

    # flight_recs = tb.get_records(cf.FLIGHTS_TABLE_ID, add_params={'pageSize': 1000})

    # Рассчитываем рейтинги

    # for idea in idea_list:
    #     for idea_name, idea_id in idea.items():
    #         top_3_f = get_top_3_flights_by_idea(flight_recs, idea_name, idea_id)
    #         top_3_res = get_top_3_hotels_by_idea(hotel_recs, idea_name, idea_id)

    #         if not top_3_res:
    #             continue

    #         for res in top_3_res:
    #             res['fields']['flight'] = [top_3_f[0]]

    #         tb.add_records(cf.VARIANT_TABLE_ID, top_3_res)

    # tb.del_records(RATE_TABLE_ID, ['recTi0czqDK9v', 'rec4AbUGYPQpa'])

    # raw_recs = tb.erase_table(RATE_TABLE_ID)

    # s = set()

    # for rec in recs:
    #     # print(rec['fields'].get('Идея'))
    #     s.update(rec['fields'].get('Идея'))

    # print(s)

    # ideas - 16

    # {'Рок и пиво', 'Тепла охота', 'На картошку', 'В америку', 'Отпуск'}

    # raw_recs = tb.erase_table(cf.VARIANT_TABLE_ID)

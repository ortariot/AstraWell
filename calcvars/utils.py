def get_extremums(vector: list[int | float]) -> tuple[int | float]:
    """ """

    max_val = max(vector)
    min_val = min(vector)
    return min_val, max_val, 1 + max_val - min_val


def filter_list_by_idea(anylist: list[dict], idea: str) -> list[dict]:
    """ """
    return list(
        filter(lambda x: idea in x.get("fields", {}).get("Идея", ""), anylist)
    )

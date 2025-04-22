from itertools import batched
import requests


class BaseApi:
    """
    The base class for interacting with the API
    """

    def __init__(self, token: str) -> None:
        """ """

        self.token: str = token
        self.headers: dict[str, str] = {
            "Authorization": " ".join(["Bearer", self.token]),
            "Content-Type": "application/json",
        }

    def get_request_data(
        self,
        request: requests.api.request,
        add_host: str = "",
        add_headers: dict[str, str] = {},
        add_params: dict[str, str] = {},
        add_data: dict[str, str] = {},
    ) -> dict:
        """
        The method generates requests using
        various methods and returns an API response
        """

        host = "/".join([self.base_host, add_host])

        headers = {
            **self.headers,
            **add_headers,
        }

        r: requests.Response = request(
            host, headers=headers, params=add_params, json=add_data
        )

        if not r.ok:
            code = r.status_code
            message = r.json().get("message")
            raise Exception(f"API error, code: {code}, message: {message}")

        data = r.json()

        if not data.get("success"):
            code = data.get("code")
            msg = data.get("message")
            raise Exception(f"Code: {code}, message: {msg}")

        return r.json().get("data")

    def get_data(
        self,
        add_host: str = "",
        add_headers: dict[str, str] = {},
        add_params: dict[str, str] = {},
    ) -> dict:
        """
        The method generates requests using
        the GET method and returns an API response
        """

        return self.get_request_data(
            requests.get,
            add_host,
            add_headers=add_headers,
            add_params=add_params,
        )

    def add_data(
        self,
        add_host: str = "",
        add_headers: dict[str, str] = {},
        data: dict = {},
    ) -> dict:
        """
        The method generates requests using
        the POST method and returns an API response
        """

        return self.get_request_data(
            requests.post,
            add_host,
            add_headers=add_headers,
            add_data=data,
        )

    def del_data(
        self,
        add_host: str = "",
        add_headers: dict[str, str] = {},
        add_params: dict[str, str] = {},
    ) -> dict:
        """ """
        return self.get_request_data(
            requests.delete,
            add_host,
            add_headers=add_headers,
            add_params=add_params,
        )


class MWSTables(BaseApi):
    """ """

    def __init__(self, token: str) -> None:
        """ """

        super().__init__(token)
        self.base_host: str = "https://true.tabs.sale/api/v1"

    def get_space_tree(self, space_id: str) -> dict:
        """ """

        data = self.get_data("node/tree", {"X-space-id": space_id})

        return data["children"][9]


class Tables(BaseApi):
    """
    A class for interacting with the Tables API
    """

    def __init__(self, token: str) -> None:
        """ """

        super().__init__(token)
        self.base_host: str = "https://tables.mws.ru/fusion/v1/datasheets"

    def get_full_table(
        self,
        table_id: str,
        add_params: dict = {},
    ) -> list[dict[str, str]]:
        """
        The method returns all table data from the specified table
        """
        return self.get_data(
            add_host=f"{table_id}/records",
            add_params=add_params,
        )

    def get_records(
        self,
        table_id: str,
        add_params: dict = {},
    ) -> list[dict[str, str]]:
        """
        The method returns all records from the specified table
        """
        return self.get_full_table(
            table_id,
            add_params=add_params,
        ).get("records")

    def get_table_info(
        self,
        table_id: str,
        add_params: dict = {},
    ) -> list[dict[str, str]]:
        """
        The method returns info from the specified table
        """
        data = self.get_full_table(
            table_id,
            add_params=add_params,
        )

        data.pop("records")

        return data

    def add_records(
        self,
        table_id: str,
        records: list[dict[str, str]],
    ) -> dict:
        """
        The method adds records to the specified table
        """

        return self.add_data(
            add_host=f"{table_id}/records",
            data={"records": records},
        )

    def del_records(
        self,
        table_id: str,
        record_ids: list[str] | str,
    ) -> dict:
        """ """
        return self.del_data(
            add_host=f"{table_id}/records",
            add_params={"recordIds": record_ids},
        )

    def erase_table(self, table_id: str) -> bool:
        """ """
        recs = self.get_records(table_id)
        record_ids = list(map(lambda x: x.get("recordId"), recs))

        for batch in batched(record_ids, 10):
            self.del_records(table_id, batch)

from openai import OpenAI

from core.settings import settings


class DeepSeek:
    deepsek_key = settings.deepsek_key
    base_url = "https://api.deepseek.com"

    def __init__(self):
        self.client = OpenAI(api_key=self.deepsek_key, base_url=self.base_url)

    def get_ai_preferences(self, idea):
        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Лучшие страны удовляетворяющие криетриям"
                        f" {idea} в формате - через запятую"
                        " Приведи ровно три подходящие кода аэропорта, никаких"
                        " названий городв, стран или других коментариев в ответе быть не должно"
                    ),
                },
            ],
            stream=False,
        )
        # print(response.choices[0].message.content)

        text_responce = response.choices[0].message.content

        if "," in text_responce:
            return text_responce.split(", ")
        else:
            return text_responce.split("\n")


if __name__ == "__main__":
    neiro = DeepSeek()
    neiro.get_ai_preferences("Мороз и солнце день чудесный")

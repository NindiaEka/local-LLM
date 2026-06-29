from openai import OpenAI

client = OpenAI(
    api_key="sk_local_cUbDgapakP55YOojts01wM_R4EPFpaKeFDjXZ-0YBoQ",
    base_url="http://localhost:8000/v1"
)

models = client.models.list()

print(models)
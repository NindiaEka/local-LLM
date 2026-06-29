from openai import OpenAI

client = OpenAI(
    api_key="sk_local_cUbDgapakP55YOojts01wM_R4EPFpaKeFDjXZ-0YBoQ",
    base_url="http://localhost:8000/v1"
)

response = client.chat.completions.create(
    model="qwen2.5:7b",
    messages=[
        {
            "role":"user",
            "content":"Hello"
        }
    ]
)

print(response.choices[0].message.content)
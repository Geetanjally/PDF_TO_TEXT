from google import genai
from config import KEY

client = genai.Client(api_key=KEY)

models = client.models.list()
for m in models:
    print(m.name)

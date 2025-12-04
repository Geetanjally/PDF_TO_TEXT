from google import genai
import os
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
# List all available models
models = client.models.list()

print("\n📌 Available Gemini Models:\n")
for m in models:
    print(f"- {m.name}")


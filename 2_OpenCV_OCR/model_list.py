from google import genai

client = genai.Client(api_key="AIzaSyAzHf66I6a1uHUbC1-PnFCK6KyBUZTOJYI")
# List all available models
models = client.models.list()

print("\n📌 Available Gemini Models:\n")
for m in models:
    print(f"- {m.name}")


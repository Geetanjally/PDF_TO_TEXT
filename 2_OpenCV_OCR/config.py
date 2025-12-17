import os

KEY = os.getenv("GEMINI_API_KEY")
if not KEY:
    raise RuntimeError(
        "GEMINI_API_KEY missing.\n"
        "Run:\n"
        "$env:GEMINI_API_KEY='YOUR_KEY'"
    )

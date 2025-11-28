import os
import re
import time
import pytesseract
from google.genai import Client
from google.genai.types import Image,GenerateContentConfig


# ------------------------------
# 1️⃣ BETTER TESSERACT (Printed)
# ------------------------------

def extract_text_tesseract(image, timeout=10, max_retries=2):
    """
    Improved Tesseract OCR for printed/digital text.
    Includes timeout + retries.
    """
    for attempt in range(1, max_retries + 1):
        try:
            start = time.time()

            config = r"--psm 6 --oem 3"
            text = pytesseract.image_to_string(image, config=config)

            if time.time() - start > timeout:
                raise TimeoutError("Tesseract timeout")

            # Clean text
            clean_text = re.sub(r'[^A-Za-z0-9.,!?;:\'\"\-\s]', '', text)

            print("🔍 Tesseract text extraction successful!")
            return clean_text.strip()

        except Exception as e:
            print(f"⚠️ Tesseract attempt {attempt}/{max_retries} failed:", e)
            if attempt < max_retries:
                print("🔁 Retrying Tesseract...")
                time.sleep(1)
            else:
                print("❌ Tesseract OCR failed finally.")
                return ""



# ---------------------------------
# 2️⃣ FIXED GEMINI (Handwritten)
# ---------------------------------

client = Client(api_key="AIzaSyAzHf66I6a1uHUbC1-PnFCK6KyBUZTOJYI")  # replace with your key

def extract_text_gemini(image_path, timeout=20, max_retries=3):
    model_name = "models/gemini-2.0-flash"

    for attempt in range(1, max_retries + 1):
        try:
            print(f"✨ Gemini OCR attempt {attempt}/{max_retries}")

            # Upload image file
            uploaded_file = client.files.upload(file=image_path)

            config = GenerateContentConfig(
                temperature=0,
                max_output_tokens=4096
            )

            # 🔥 MAIN FIX:
            # contents expects a LIST where each item is:
            #   - str
            #   - File   (directly)
            #   - Image
            #   - Part
            response = client.models.generate_content(
                model=model_name,
                config=config,
                contents=[
                    uploaded_file,  # 👈 File object passed directly
                    (
                        "Extract ALL text accurately. "
                        "Preserve formatting, steps, bullet points, equations, "
                        "indentation, tables, and line breaks. "
                        "Do NOT summarize. Return ONLY the raw text."
                    )
                ]
            )

            text = getattr(response, "text", "")
            return text.strip()

        except Exception as e:
            print(f"⚠️ Gemini attempt {attempt}/{max_retries} failed: {e}")
            if attempt < max_retries:
                time.sleep(2)
            else:
                return ""

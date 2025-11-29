import os
import re
import time
import pytesseract
import google.generativeai as genai # Standard SDK
from PIL import Image # For multi-modal input


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
            # NOTE: The original regex was very aggressive. Reverting to basic clean-up for demonstration.
            clean_text = re.sub(r'[^A-Za-z0-9.,!?;:\'\"\\-\s]', '', text)

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


# ------------------------------------
# 2️⃣ GEMINI VISION OCR (Handwritten/Complex)
# ------------------------------------
def extract_text_gemini(image_path, max_retries=3):
    """
    Uses the Gemini API to perform robust OCR on complex or handwritten documents.
    Relies on genai.configure() being called prior to execution (e.g., in ui.py).
    """
    model_name = "gemini-2.5-flash" # Use the latest multi-modal model
    
    # 1. Load image using PIL
    try:
        img = Image.open(image_path)
    except Exception as e:
        print(f"⚠️ Could not load image {image_path} for Gemini OCR: {e}")
        return ""

    # 2. Define the contents and prompt
    prompt_text = (
        "Extract ALL text accurately. "
        "Preserve formatting, steps, bullet points, equations, "
        "indentation, tables, and line breaks. "
        "Do NOT summarize. Return ONLY the raw text."
    )
    # Contents is a list containing the image object and the text prompt
    contents = [img, prompt_text]
    
    # 3. Define generation configuration using a dictionary
    generation_config = {
        "temperature": 0.0,
        "max_output_tokens": 4096,
    }

    # 4. Attempt generation
    for attempt in range(1, max_retries + 1):
        try:
            print(f"✨ Gemini OCR attempt {attempt}/{max_retries}")
            
            # This uses the globally configured client
            model = genai.GenerativeModel(
                model_name,
                generation_config=generation_config
            )

            response = model.generate_content(
                contents=contents
            )

            text = response.text
            return text.strip()

        except Exception as e:
            print(f"⚠️ Gemini attempt {attempt}/{max_retries} failed: {e}")
            if attempt < max_retries:
                time.sleep(2)
            else:
                print("❌ Gemini OCR failed finally.")
                return ""
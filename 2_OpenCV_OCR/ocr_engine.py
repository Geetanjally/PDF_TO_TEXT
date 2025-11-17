import warnings
warnings.filterwarnings("ignore")

import os
import re
import pytesseract
from google.cloud import vision

# ✅ Configure Tesseract path for printed/digital text
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ✅ Initialize Google Vision API client
try:
    vision_client = vision.ImageAnnotatorClient()
    print("✅ Google Vision API client initialized successfully!")
except Exception as e:
    print("⚠️ Google Vision initialization failed:", e)
    vision_client = None


# -------------------------------------------------------------------
# OCR METHODS
# -------------------------------------------------------------------

def extract_text_tesseract(image):
    """
    Extract printed/digital text using Tesseract OCR.
    `image` should be a NumPy array (like cv2.imread result).
    """
    try:
        config = r"--psm 6 --oem 3"
        text = pytesseract.image_to_string(image, config=config)
        clean_text = re.sub(r'[^A-Za-z0-9.,!?;:\'\-\s]', '', text)
        print("🔍 Tesseract text extraction successful!")
        return clean_text.strip()
    except Exception as e:
        print("❌ Tesseract OCR failed:", e)
        return ""


def extract_text_google_vision(image_path):
    """
    Extract text using Google Cloud Vision API.
    `image_path` should be a file path to an image.
    """
    if vision_client is None:
        print("⚠️ Google Vision client not initialized.")
        return ""

    try:
        with open(image_path, "rb") as img_file:
            content = img_file.read()

        image = vision.Image(content=content)
        response = vision_client.text_detection(image=image)

        if response.error.message:
            print("⚠️ Google Vision API Error:", response.error.message)
            return ""

        texts = response.text_annotations
        if not texts:
            print("⚠️ No text detected by Google Vision.")
            return ""

        full_text = texts[0].description.strip()
        clean_text = re.sub(r'[^A-Za-z0-9.,!?;:\'\-\s\n]', '', full_text)
        print("🧠 Google Vision text extraction successful!")
        return clean_text.strip()

    except Exception as e:
        print("❌ Google Vision OCR failed:", e)
        return ""

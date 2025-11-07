import warnings
warnings.filterwarnings("ignore")

import os
import pytesseract
from paddleocr import PaddleOCR
import re

# ✅ Configure Tesseract path for printed/digital text
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ✅ Initialize PaddleOCR (for handwritten text)
print("🔧 Loading PaddleOCR model (for handwritten text)...")
ocr = PaddleOCR(lang='en')
print("✅ PaddleOCR successfully initialized!")

# -------------------------------------------------------------------
# OCR METHODS
# -------------------------------------------------------------------

def extract_text_tesseract(image):
    """
    Extract printed/digital text using Tesseract OCR.
    """
    config = r"--psm 6 --oem 3"
    text = pytesseract.image_to_string(image, config=config)
    text = re.sub(r'[^A-Za-z0-9.,!?;:\'\-\s]', '', text)
    return text.strip()


def extract_text_paddleocr(image):
    """
    Extract handwritten or complex text using PaddleOCR.
    `image` should be a preprocessed RGB image or file path.
    """
    # PaddleOCR accepts both ndarray or path
    result = ocr.ocr(image)

    extracted_text = []
    for line in result[0]:
        line_text = line[1][0]
        clean_text = re.sub(r'[^A-Za-z0-9.,!?;:\'\-\s]', '', line_text)
        extracted_text.append(clean_text.strip())

    full_text = "\n".join(extracted_text)
    print(f"🖋️ Extracted {len(extracted_text)} text lines using PaddleOCR")
    return full_text.strip()

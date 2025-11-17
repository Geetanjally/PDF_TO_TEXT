import cv2
import pytesseract
import numpy as np

def is_image_digital(img):
    """
    Classifies an image as digital (printed) or handwritten based on
    OCR confidence, edge density, and text length.
    Returns:
        True  -> digital/printed image
        False -> handwritten image
    """
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 1️⃣ Quick check: text length
        text = pytesseract.image_to_string(gray)
        if len(text.strip()) < 20:
            print("[ℹ️] Very little recognizable text → likely handwritten.")
            return False

        # 2️⃣ OCR confidence check
        data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)
        confs = [float(conf) for conf in data["conf"] if conf != '-1']

        if not confs:
            print("[⚠️] No OCR confidence values detected → handwritten.")
            return False

        avg_conf = sum(confs) / len(confs)

        # 3️⃣ Edge density check
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size

        print(f"[ℹ️] OCR Confidence: {avg_conf:.2f}, Edge Density: {edge_density:.4f}")

        # Final decision
        return avg_conf > 55 and edge_density < 0.12

    except Exception as e:
        print(f"[❌] Error in is_image_digital: {e}")
        return False

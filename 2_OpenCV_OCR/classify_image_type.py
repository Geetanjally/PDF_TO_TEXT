import cv2
import pytesseract
import numpy as np

def is_image_digital(img):
    """
    Classifies an image as digital (printed) or handwritten based on
    OCR confidence and edge density.
    Returns:
        True  -> digital/printed image
        False -> handwritten image
    """
    try:
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Get OCR data for confidence analysis
        data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)
        confs = [float(conf) for conf in data["conf"] if conf != '-1']

        # Handle empty OCR result
        if not confs:
            print("[⚠️] No OCR confidence values detected, likely handwritten.")
            return False

        avg_conf = sum(confs) / len(confs)

        # Edge density helps distinguish printed vs handwritten
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size

        print(f"[ℹ️] OCR Confidence: {avg_conf:.2f}, Edge Density: {edge_density:.4f}")

        # Adjusted thresholds (empirically better for mixed data)
        return avg_conf > 55 and edge_density < 0.12

    except Exception as e:
        print(f"[❌] Error in is_image_digital: {e}")
        return False

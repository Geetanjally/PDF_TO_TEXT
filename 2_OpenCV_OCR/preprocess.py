import cv2
import numpy as np
def preprocess_for_tesseract(image):
    """
    Preprocessing optimized for printed/digital text.
    - Grayscale
    - Gaussian blur
    - Otsu thresholding
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    return thresh

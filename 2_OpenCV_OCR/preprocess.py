import cv2
import numpy as np

def preprocess_for_paddleocr(image):
    """
    Preprocessing optimized for handwritten text (PaddleOCR).
    - Removes shadows
    - Enhances contrast
    - Denoises and deskews (lightly)
    - Keeps original structure (no segmentation)
    Returns: cleaned image ready for PaddleOCR
    """
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # --- Step 1: Remove shadows and uneven lighting ---
    dilated_img = cv2.dilate(gray, np.ones((15, 15), np.uint8))
    bg_img = cv2.medianBlur(dilated_img, 21)
    diff_img = 255 - cv2.absdiff(gray, bg_img)

    # --- Step 2: Normalize contrast ---
    norm_img = cv2.normalize(diff_img, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)

    # --- Step 3: Denoise slightly (to preserve strokes) ---
    denoised = cv2.fastNlMeansDenoising(norm_img, h=15)

    # --- Step 4: Light binarization (not too aggressive) ---
    binary = cv2.adaptiveThreshold(
        denoised, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        35, 15
    )

    # --- Step 5: Light deskew (PaddleOCR already corrects angles well) ---
    coords = np.column_stack(np.where(binary > 0))
    if coords.size > 0:
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        (h, w) = binary.shape[:2]
        M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
        binary = cv2.warpAffine(binary, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    # Convert back to RGB (PaddleOCR expects color images)
    preprocessed = cv2.cvtColor(binary, cv2.COLOR_GRAY2RGB)

    return preprocessed


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

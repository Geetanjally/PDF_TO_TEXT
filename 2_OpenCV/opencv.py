import cv2
import pytesseract
import os
import shutil
import numpy as np

def is_image_digital(img):
    # Run OCR and check length of extracted text
    text = pytesseract.image_to_string(img)
    return len(text.strip()) > 100  # Adjust threshold based on your data

def preprocess_image(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    denoised = cv2.medianBlur(gray, 3)
    binary = cv2.adaptiveThreshold(
        denoised, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        15, 15
    )
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    return cleaned

def process_folder(input_folder, output_folder):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    image_files = sorted([
        f for f in os.listdir(input_folder)
        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff'))
    ])

    for fname in image_files:
        img_path = os.path.join(input_folder, fname)
        img = cv2.imread(img_path)
        if img is None:
            print(f"Skipping {fname}: cannot read image.")
            continue

        if is_image_digital(img):
            # Copy digital images directly
            shutil.copy2(img_path, os.path.join(output_folder, fname))
            print(f"{fname} detected as digital; copied without preprocessing.")
        else:
            # Preprocess handwritten images and save
            processed = preprocess_image(img)
            out_path = os.path.join(output_folder, fname)
            cv2.imwrite(out_path, processed)
            print(f"{fname} detected as handwritten; preprocessed and saved.")

    print("\n✅ Finished processing all images.")

if __name__ == "__main__":
    input_folder = r"G:\Project\PDF_TO_TEXT\1_pdf_to_image\output_images"
    output_folder = r"G:\Project\PDF_TO_TEXT\3_Preprocessed_Images"
    process_folder(input_folder, output_folder)



# if __name__ == "__main__":
#     input_folder = r"G:\Project\PDF_TO_TEXT\1_pdf_to_image\output_images"
#     main_output_folder = r"G:\Project\PDF_TO_TEXT\3_Preprocessed_Images"
#     process_folder(input_folder, main_output_folder)


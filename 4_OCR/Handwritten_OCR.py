import pytesseract
import cv2
import os

def ocr_images(input_folder, output_folder, lang='eng'):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    for file_name in os.listdir(input_folder):
        if file_name.lower().endswith(('.png', '.jpg', '.jpeg')):
            img_path = os.path.join(input_folder, file_name)
            img = cv2.imread(img_path)
            if img is None:
                continue
            text = pytesseract.image_to_string(img, lang=lang)
            out_txt_path = os.path.join(output_folder, file_name + ".txt")
            with open(out_txt_path, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"OCR done for {file_name} -> {out_txt_path}")

# Example usage:
if __name__ == "__main__":
    input_folder = r"G:\Project\PDF_TO_TEXT\2_OpenCV\processed_images"
    output_folder = r"G:\Project\PDF_TO_TEXT\4_OCR_Results"
    ocr_images(input_folder, output_folder)

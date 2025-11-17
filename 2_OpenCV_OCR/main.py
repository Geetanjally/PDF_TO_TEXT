import os
import cv2
from preprocess import preprocess_for_tesseract
from ocr_engine import extract_text_tesseract, extract_text_google_vision
from combine_texts import combine_texts_in_folder
from classify_image_type import is_image_digital

# ⚙️ LIMIT TRACKER — prevent overuse of Google Vision API
MAX_GOOGLE_VISION_CALLS = 2   # <— change this limit as per your plan
google_calls_used = 0


def process_folder(input_folder, output_folder):
    global google_calls_used  # To keep track across files

    if not os.path.exists(input_folder):
        print(f"❌ Input folder not found: {input_folder}")
        return

    for root, _, files in os.walk(input_folder):
        for fname in files:
            if not fname.lower().endswith(('.png', '.jpg', '.jpeg')):
                continue

            img_path = os.path.join(root, fname)
            img = cv2.imread(img_path)

            if img is None:
                print(f"⚠️ Skipping unreadable file: {img_path}")
                continue

            relative_path = os.path.relpath(root, input_folder)
            sub_output_folder = os.path.join(output_folder, relative_path)
            os.makedirs(sub_output_folder, exist_ok=True)

            try:
                # 🔍 Step 1: Detect image type
                if is_image_digital(img):
                    print(f"\n📘 {fname} detected as DIGITAL.")
                    processed = preprocess_for_tesseract(img)
                    text = extract_text_tesseract(processed)
                else:
                    print(f"\n✍️  {fname} detected as HANDWRITTEN or MIXED.")
                    
                    # ⚙️ Stop if you've hit your safe Vision API limit
                    if google_calls_used >= MAX_GOOGLE_VISION_CALLS:
                        print("⚠️ Vision API daily limit reached. Skipping this image to save credits.")
                        continue

                    text = extract_text_google_vision(img_path)
                    google_calls_used += 1  # count this call

                # 💾 Step 2: Save extracted text
                text_file_path = os.path.join(sub_output_folder, os.path.splitext(fname)[0] + ".txt")
                with open(text_file_path, "w", encoding="utf-8") as f:
                    f.write(text)
                print(f"✅ Extracted text saved to: {text_file_path}")

            except Exception as e:
                print(f"❌ Error processing {fname}: {e}")

    print(f"\n🎯 All images processed successfully! (Google Vision used {google_calls_used}/{MAX_GOOGLE_VISION_CALLS})")


if __name__ == "__main__":
    # input_folder = r"G:\Project\PDF_TO_TEXT\1_pdf_to_image\output_images"
    input_folder = r"G:\Project\PDF_TO_TEXT\2_OpenCV_OCR\test_input"
    # output_folder = r"G:\Project\PDF_TO_TEXT\3_Extracted_Texts"
    output_folder = r"G:\Project\PDF_TO_TEXT\2_OpenCV_OCR\test_output"
    combined_output_folder = r"G:\Project\PDF_TO_TEXT\4_Combined_text"

    process_folder(input_folder, output_folder)

    print("\n📄 Combining extracted text files per folder...")
    combine_texts_in_folder(output_folder)

    print(f"\n✅ Combined text files saved in: {combined_output_folder}")

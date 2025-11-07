import os
import cv2
from classify_image_type import is_image_digital
from preprocess import preprocess_for_paddleocr, preprocess_for_tesseract
from ocr_engine import extract_text_tesseract, extract_text_paddleocr
from combine_texts import combine_texts_in_folder


def process_folder(input_folder, output_folder):
    """
    Process all images in a folder:
    1. Detect if image is handwritten or digital.
    2. Apply appropriate preprocessing.
    3. Perform OCR using PaddleOCR (for handwritten) or Tesseract (for digital).
    4. Save extracted text in a structured output folder.
    """
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

            # Create corresponding output folder structure
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
                    print(f"\n✍️  {fname} detected as HANDWRITTEN.")
                    processed = preprocess_for_paddleocr(img)
                    text = extract_text_paddleocr(processed)

                # 💾 Step 2: Save extracted text
                text_file_path = os.path.join(sub_output_folder, os.path.splitext(fname)[0] + ".txt")
                with open(text_file_path, "w", encoding="utf-8") as f:
                    f.write(text)
                print(f"✅ Extracted text saved to: {text_file_path}")

            except Exception as e:
                print(f"❌ Error processing {fname}: {e}")

    print("\n🎯 All images processed successfully!")


if __name__ == "__main__":
    # 📁 Folder paths (update as needed)
    input_folder = r"G:\Project\PDF_TO_TEXT\1_pdf_to_image\output_images"
    output_folder = r"G:\Project\PDF_TO_TEXT\3_Extracted_Texts"
    combined_output_folder = r"G:\Project\PDF_TO_TEXT\4_Combined_text"

    # 🚀 Step 1: OCR processing (per image)
    process_folder(input_folder, output_folder)

    # 📄 Step 2: Combine all text files into one per folder
    print("\n📄 Combining extracted text files per folder...")
    combine_texts_in_folder(output_folder)

    print(f"\n✅ Combined text files saved in: {combined_output_folder}")

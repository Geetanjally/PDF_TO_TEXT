import os
import cv2
from preprocess import preprocess_for_tesseract
from ocr_engine import extract_text_tesseract, extract_text_gemini
from combine_texts import combine_texts_in_folder
from classify_image_type import is_image_digital


def process_folder(input_folder, output_folder):
    """
    Process a folder containing images:
    - Detect handwritten vs digital
    - Run correct OCR engine
    - Save extracted text in structured output folders
    """

    if not os.path.exists(input_folder):
        print(f"❌ Input folder not found: {input_folder}")
        return

    print(f"\n🚀 Starting OCR processing...")
    print(f"📂 Input: {input_folder}")
    print(f"📂 Output: {output_folder}")

    for root, _, files in os.walk(input_folder):
        for fname in files:

            # Process only images
            if not fname.lower().endswith((".png", ".jpg", ".jpeg")):
                continue

            img_path = os.path.join(root, fname)
            print(f"\n=============================================")
            print(f"🖼️ Processing: {fname}")

            img = cv2.imread(img_path)
            if img is None:
                print(f"⚠️ Skipping unreadable file: {img_path}")
                continue

            # Create output folder mirror structure
            relative_path = os.path.relpath(root, input_folder)
            sub_out_folder = os.path.join(output_folder, relative_path)
            os.makedirs(sub_out_folder, exist_ok=True)

            try:
                # STEP 1 — Detect type of text
                if is_image_digital(img):
                    print(f"📘 {fname} detected as DIGITAL text.")

                    processed_img = preprocess_for_tesseract(img)
                    text = extract_text_tesseract(processed_img)

                else:
                    print(f"✍️ {fname} detected as HANDWRITTEN or MIXED text.")

                    text = extract_text_gemini(img_path)

                # Safety check
                if not text.strip():
                    print("⚠️ OCR returned empty text.")

                # STEP 2 — Save extracted text
                txt_path = os.path.join(
                    sub_out_folder,
                    os.path.splitext(fname)[0] + ".txt"
                )

                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(text)

                print(f"✅ Saved extracted text → {txt_path}")

            except Exception as e:
                print(f"❌ ERROR processing {fname}: {e}")

    print("\n🎯 All images processed successfully!")


# ------------------------------------
# MAIN EXECUTION
# ------------------------------------
if __name__ == "__main__":

    input_folder = r"G:\Project\PDF_TO_TEXT\2_OpenCV_OCR\test_input"
    output_folder = r"G:\Project\PDF_TO_TEXT\2_OpenCV_OCR\test_output"
    combined_output_folder = r"G:\Project\PDF_TO_TEXT\4_Combined_text"

    process_folder(input_folder, output_folder)

    print("\n📄 Combining all extracted text files...")
    combine_texts_in_folder(output_folder)

    print(f"\n✅ Combined text files saved in: {combined_output_folder}")

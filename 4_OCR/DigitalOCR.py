import pdfplumber
import os

def extract_pdf_text(pdf_folder, output_folder):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    for file in os.listdir(pdf_folder):
        if file.lower().endswith('.pdf'):
            pdf_path = os.path.join(pdf_folder, file)
            with pdfplumber.open(pdf_path) as pdf:
                all_text = ''
                for page in pdf.pages:
                    all_text += page.extract_text() or ''
            out_txt_path = os.path.join(output_folder, file + ".txt")
            with open(out_txt_path, "w", encoding="utf-8") as f:
                f.write(all_text)
            print(f"Extracted text from {file}")

# Example usage:
if __name__ == "__main__":
    pdf_folder = r"G:\Project\PDF_TO_TEXT\0_Input_folder"
    output_folder = r"G:\Project\PDF_TO_TEXT\4_OCR_Results"
    extract_pdf_text(pdf_folder, output_folder)

import fitz  # PyMuPDF
import os

def convert_pdf_to_images(pdf_path, output_folder='output_images', dpi=200, image_format='JPEG'):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    try:
        doc = fitz.open(pdf_path)
        print(f"✅ Opened {pdf_path} | Total pages: {len(doc)}")
    except Exception as e:
        print(f"⚠️ Could not open {pdf_path}: {e}")
        return []
    
    saved_images = []
    for i, page in enumerate(doc):
        try:
            pix = page.get_pixmap(dpi=dpi)
            image_path = os.path.join(output_folder, f"page_{i + 1}.{image_format.lower()}")
            pix.save(image_path)
            saved_images.append(image_path)
            print(f"✅ Saved {image_path}")
        except Exception as e:
            print(f"⚠️ Error rendering page {i + 1}: {e}")
    
    doc.close()
    print(f"🎉 Done! {len(saved_images)} pages saved in '{output_folder}'.")
    return saved_images

# Example usage:
if __name__ == "__main__":
    input_folder = r"G:\Project\PDF_TO_TEXT\0_Input_folder"
    output_base = r"G:\Project\PDF_TO_TEXT\1_pdf_to_image\output_images"
    
    if not os.path.exists(output_base):
        os.makedirs(output_base)
    
    pdf_files = [f for f in os.listdir(input_folder) if f.lower().endswith(".pdf")]
    
    if not pdf_files:
        print("⚠️ No PDF files found!")
    else:
        for pdf in pdf_files:
            pdf_path = os.path.join(input_folder, pdf)
            out_folder = os.path.join(output_base, os.path.splitext(pdf)[0])
            print(f"\nConverting {pdf} ...")
            convert_pdf_to_images(pdf_path, out_folder)

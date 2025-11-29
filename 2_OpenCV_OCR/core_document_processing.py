import os
import io
import re
import time
import json
import base64
import numpy as np
import cv2
import fitz # PyMuPDF

from docx import Document
from pptx import Presentation
from pptx.util import Inches, Pt

# Import the necessary Google GenAI libraries
# Note: Using the recommended 'google-genai' library for client-based operations
from google.genai import Client
from google.genai.types import Image, GenerateContentConfig

# --- Configuration Constants (Can be overridden by Streamlit app) ---
MODEL_NAME = "models/gemini-2.5-flash"
OCR_MODEL_NAME = "models/gemini-2.5-flash"

# ----------------------------------------------------------------------
# 1. PDF/Image Extraction (Modified for in-memory processing for Streamlit)
# ----------------------------------------------------------------------

def extract_text_from_pdf(pdf_bytes, dpi=200):
    """
    Extracts text from PDF pages, and renders pages as images for OCR if text is sparse.
    Returns a list of tuples: [(page_number, extracted_text, base64_image)]
    """
    
    # Check for PyMuPDF
    if not hasattr(fitz, 'open'):
        raise ImportError("PyMuPDF (fitz) is not installed. Please install with 'pip install pymupdf'")

    # Convert bytes to a PyMuPDF document
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    results = []
    
    print(f"✅ Opened PDF | Total pages: {len(doc)}")

    for i, page in enumerate(doc):
        page_num = i + 1
        
        # Attempt to extract text directly from the PDF
        raw_pdf_text = page.get_text()
        
        # Render the page to an image (in memory)
        pix = page.get_pixmap(dpi=dpi)
        img_data = pix.tobytes(output="png")
        base64_img = base64.b64encode(img_data).decode('utf-8')
        
        # Decide which text to use, or if OCR is needed
        if raw_pdf_text.strip() and len(raw_pdf_text.strip()) > 50:
            print(f"📄 Page {page_num}: Digital text found, skipping image OCR.")
            results.append((page_num, raw_pdf_text.strip(), None)) # No image needed if text is clean
        else:
            print(f"🖼️ Page {page_num}: Sparse text found. Image saved for OCR.")
            results.append((page_num, None, base64_img)) # Text will be filled by OCR later

    doc.close()
    return results

# ----------------------------------------------------------------------
# 2. OCR Classification
# ----------------------------------------------------------------------

def is_image_digital(img_bytes):
    """
    Classifies an image as digital (printed) or handwritten using basic CV checks.
    For Streamlit, we work with image bytes/base64, not file paths.
    """
    try:
        # Convert bytes to a numpy array for OpenCV
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            print("[⚠️] Could not decode image bytes.")
            return False

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 1️⃣ Quick check: edge density (handwritten often has lower, softer edges)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size

        # Simple thresholding: high edge density (e.g., > 0.01) suggests sharp, printed text
        # Low density suggests fuzzy/handwritten text or a diagram
        is_digital = edge_density > 0.01
        
        print(f"[ℹ️] Edge Density: {edge_density:.4f} -> {'Digital' if is_digital else 'Handwritten/Fuzzy'}")
        
        return is_digital

    except Exception as e:
        print(f"❌ Classification Error: {e}")
        # Default to Gemini for safety if classification fails
        return False 

# ----------------------------------------------------------------------
# 3. OCR Engines (Tesseract & Gemini)
# ----------------------------------------------------------------------

def extract_text_tesseract(img_bytes, timeout=10, max_retries=2):
    """
    Tesseract OCR (for printed/digital text) - Note: requires local tesseract installation.
    Since Streamlit is often deployed without Tesseract, this implementation
    is commented out or replaced with a warning/fallback to Gemini to ensure
    cross-platform stability.
    """
    print("⚠️ Tesseract (local OCR) is generally not supported in cloud environments like Streamlit. Falling back to Gemini.")
    # Fallback: Run the image through Gemini instead
    return extract_text_gemini(img_bytes, is_base64=False, max_retries=max_retries)

def extract_text_gemini(data, api_key, is_base64=True, max_retries=3):
    """
    Gemini OCR for images (especially handwritten or complex layouts).
    Input is either base64 string or raw image bytes (when called from Tesseract fallback).
    """
    client = Client(api_key=api_key)
    
    prompt = (
        "Extract ALL text accurately. Preserve formatting, steps, bullet points, equations, "
        "indentation, tables, and line breaks. Do NOT summarize. Return ONLY the raw text."
    )
    
    img_data = base64.b64decode(data) if is_base64 else data
    
    # Create the Image object from bytes
    img_part = Image.from_bytes(data=img_data, mime_type='image/png')

    config = GenerateContentConfig(
        temperature=0,
        max_output_tokens=8192
    )

    for attempt in range(1, max_retries + 1):
        try:
            print(f"✨ Gemini OCR attempt {attempt}/{max_retries}")
            response = client.models.generate_content(
                model=OCR_MODEL_NAME,
                config=config,
                contents=[
                    img_part,
                    prompt
                ]
            )

            text = getattr(response, "text", "")
            return text.strip()

        except Exception as e:
            print(f"⚠️ Gemini OCR attempt {attempt}/{max_retries} failed: {e}")
            if attempt < max_retries:
                time.sleep(2)
            else:
                print("❌ Gemini OCR failed finally.")
                return ""

# ----------------------------------------------------------------------
# 4. Text Cleaning and Structuring (via Gemini)
# ----------------------------------------------------------------------

def clean_with_gemini(raw_text, api_key):
    """
    Uses Gemini to clean and structure the raw combined text.
    """
    client = Client(api_key=api_key)

    prompt = f"""
You are a professional text cleaner and structure expert.

Clean the following messy OCR extracted text:
- Fix spelling mistakes, OCR artifacts, and fragmented sentences.
- Preserve key information, bullet points, and headings.
- IMPORTANT: Structure the output into clear, presentation-ready slides using Markdown.
- Each major topic should be an H1 heading (# Title).
- Sub-topics or key points should be H2 headings (## Sub-title).
- Detailed information should be bullet points.

OCR Text:
{raw_text}

Return ONLY the cleaned, structured text in Markdown format.
"""

    try:
        print("🤖 Sending combined text to Gemini for cleaning and structuring...")

        gen_config = GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=8192
        )

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[prompt],
            config=gen_config
        )

        return response.text.strip()

    except Exception as e:
        print("❌ Gemini Cleaning Error:", e)
        return f"[ERROR] Gemini cleaning failed: {e}"

# ----------------------------------------------------------------------
# 5. Core Pipeline Function
# ----------------------------------------------------------------------

def process_document_to_cleaned_text(pdf_file_bytes, api_key):
    """
    The main pipeline function: PDF -> OCR (if needed) -> Combine -> Clean/Structure.
    """
    # 1. Extract raw text and images from PDF
    page_data = extract_text_from_pdf(pdf_file_bytes)
    
    combined_raw_text_parts = []
    
    for page_num, raw_text, base64_img in page_data:
        if raw_text:
            # Use digital text directly
            combined_raw_text_parts.append(f"\n\n--- PAGE {page_num} ---\n{raw_text}")
        elif base64_img:
            # Need to run OCR on the image
            img_bytes = base64.b64decode(base64_img)
            
            # 2. Classify and run appropriate OCR (in this case, simplified to Gemini)
            if is_image_digital(img_bytes):
                # We'll use Gemini for digital as Tesseract is unstable in cloud envs
                ocr_text = extract_text_gemini(base64_img, api_key, is_base64=True)
            else:
                # Use Gemini for handwritten/fuzzy text
                ocr_text = extract_text_gemini(base64_img, api_key, is_base64=True)
                
            combined_raw_text_parts.append(f"\n\n--- PAGE {page_num} (OCR) ---\n{ocr_text}")
            
    # 3. Combine all raw text
    raw_combined_text = "\n\n".join(combined_raw_text_parts)
    
    if not raw_combined_text.strip():
        return "[ERROR] Could not extract any text from the document."
        
    # 4. Clean and structure the combined text using Gemini
    cleaned_structured_text = clean_with_gemini(raw_combined_text, api_key)
    
    return cleaned_structured_text

# ----------------------------------------------------------------------
# 6. Final Output Generation (Memory-based for Streamlit)
# ----------------------------------------------------------------------

def create_pptx_from_markdown(markdown_text, template_io=None):
    """
    Generates a PPTX file in memory from structured Markdown text.
    Assumes a basic Title-Content layout (1) and Title-Only layout (5).
    """
    if template_io:
        prs = Presentation(template_io)
    else:
        # Fallback to default presentation if no template is provided
        prs = Presentation() 

    # Split the Markdown text by top-level headings (#) to define slides
    slides_data = re.split(r'(?=\n#+ )', markdown_text)
    
    # Filter out empty strings from splitting
    slides_data = [s.strip() for s in slides_data if s.strip()]

    # First slide is usually the Title Slide
    title_slide_layout = prs.slide_layouts[0] 
    
    # Remove the first slide if it's the default blank one
    if len(prs.slides) == 1 and prs.slides[0].slide_layout.name == title_slide_layout.name:
        prs.slides._sldIdLst.pop() 
    
    # Process slides
    for i, slide_text in enumerate(slides_data):
        lines = slide_text.split('\n')
        title_line = lines[0]
        content_lines = lines[1:]

        # Extract title text, ignoring Markdown formatting
        match = re.match(r'(#+)\s*(.*)', title_line)
        title = match.group(2).strip() if match else title_line.strip()

        # Decide layout: Title Slide for the first slide (if not processed), Title and Content for the rest
        if i == 0:
            slide_layout = prs.slide_layouts[0] # Title Slide (Layout 0)
            slide = prs.slides.add_slide(slide_layout)
            
            # Place title and subtitle
            slide.shapes.title.text = title
            
            # If there's content, use it as a subtitle/deck info
            if content_lines and content_lines[0].strip():
                # Find subtitle placeholder (typically index 1)
                subtitle_placeholder = slide.placeholders[1]
                subtitle_placeholder.text = content_lines[0].strip()
        
        else:
            slide_layout = prs.slide_layouts[1] # Title and Content (Layout 1)
            slide = prs.slides.add_slide(slide_layout)
            
            slide.shapes.title.text = title
            
            body = slide.shapes.placeholders[1].text_frame
            body.clear()
            
            # Add bullets
            for line in content_lines:
                line = line.strip()
                if line:
                    # Check for explicit bullet points
                    if line.startswith(('*', '-', '•')):
                        p = body.add_paragraph()
                        p.text = line.lstrip('*-• ').strip()
                        p.level = 1
                    # Treat other text as first-level content or topic sentences
                    else:
                        p = body.add_paragraph()
                        p.text = line
                        p.level = 0
            
    # Save the presentation to a byte stream
    prs_io = io.BytesIO()
    prs.save(prs_io)
    prs_io.seek(0)
    return prs_io

def create_docx_from_markdown(markdown_text):
    """
    Generates a DOCX file in memory from structured Markdown text.
    """
    doc = Document()
    
    for line in markdown_text.split('\n'):
        line = line.strip()
        if not line:
            continue
            
        if line.startswith('###'):
            doc.add_heading(line.lstrip('#').strip(), level=3)
        elif line.startswith('##'):
            doc.add_heading(line.lstrip('#').strip(), level=2)
        elif line.startswith('#'):
            doc.add_heading(line.lstrip('#').strip(), level=1)
        elif line.startswith(('*', '-', '•')):
            doc.add_paragraph(line.lstrip('*-• ').strip(), style='List Bullet')
        else:
            doc.add_paragraph(line)
            
    # Save the document to a byte stream
    doc_io = io.BytesIO()
    doc.save(doc_io)
    doc_io.seek(0)
    return doc_io
    
def create_markdown_report(markdown_text):
    """
    Returns the final structured Markdown text as a file-like object.
    """
    markdown_io = io.BytesIO(markdown_text.encode('utf-8'))
    markdown_io.seek(0)
    return markdown_io
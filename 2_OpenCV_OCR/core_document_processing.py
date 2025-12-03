import os
import io
import re
import time
import json
import base64
import numpy as np
import cv2
import fitz # PyMuPDF
# The original code imported PIL Image but didn't use it in this version of extract_text_from_pdf.
# Keeping the import here just in case, but using only fitz and base64 for image processing in the PDF function.
# from PIL import Image 

from docx import Document
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE

# Import the necessary Google GenAI libraries
# Note: Using the recommended 'google-genai' library for client-based operations
from google.genai import Client
from google.genai.types import Image, GenerateContentConfig, Part # Added 'Part' import for clarity

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
    
    Ensures iteration over ALL pages and saves images (PNG) for pages with sparse digital text.
    """
    
    # Check for PyMuPDF
    if not hasattr(fitz, 'open'):
        raise ImportError("PyMuPDF (fitz) is not installed. Please install with 'pip install pymupdf'")

    # Convert bytes to a PyMuPDF document
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    results = []
    num_pages = len(doc)
    
    print(f"✅ Opened PDF | Total pages: {num_pages}")

    try:
        # Iterate over all pages detected by PyMuPDF to ensure all pages are processed.
        for i, page in enumerate(doc):
            page_num = i + 1
            
            # 1. Attempt to extract text directly from the PDF
            raw_pdf_text = page.get_text()
            
            # 2. Render the page to an image (in memory)
            # Use matrix=fitz.Matrix(dpi/72, dpi/72) for consistent DPI across platforms
            matrix = fitz.Matrix(dpi/72, dpi/72)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            
            # Convert pixmap to image bytes (PNG is lossless and safe for OCR)
            # We must use 'png' mimeType later if we use this format.
            img_data = pix.tobytes(output="png") 
            base64_img = base64.b64encode(img_data).decode('utf-8')
            
            # 3. Decide which data structure to save
            
            # Threshold Check: If digital text has a decent amount of content, use it directly.
            # Strips whitespace and normalizes it to count meaningful characters.
            meaningful_text_length = len(re.sub(r'\s+', '', raw_pdf_text))

            # Threshold: If meaningful text > 50 characters, assume digital text is sufficient.
            if meaningful_text_length > 250:
                print(f"📄 Page {page_num}: Digital text found, skipping image OCR. Content Length: {meaningful_text_length}")
                # Use raw_pdf_text and set base64_img to None (to avoid unnecessary OCR)
                results.append((page_num, raw_pdf_text.strip(), None)) 
            else:
                print(f"🖼️ Page {page_num}: Sparse text found. Image saved for OCR. Content Length: {meaningful_text_length}")
                # Use None for text and keep base64_img for OCR
                results.append((page_num, None, base64_img)) 

    finally:
        # Crucial: Close the document to release resources
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
    # Guard against missing OpenCV dependency
    if cv2 is None or np is None:
        print("[⚠️] OpenCV/Numpy not available for classification. Assuming handwritten/fuzzy.")
        return False

    try:
        # Convert bytes to a numpy array for OpenCV
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            print("[⚠️] Could not decode image bytes.")
            return False

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 1️⃣ Quick check: edge density 
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size

        # Simple thresholding: high edge density (e.g., > 0.01) suggests sharp, printed text
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
    Since Tesseract is usually not available in cloud environments, this acts as a placeholder
    and returns an empty string, forcing the flow to rely on Gemini Vision.
    """
    print("⚠️ Tesseract (local OCR) is generally not supported in cloud environments like Streamlit. Bypassing and relying on Gemini.")
    return "" 

def extract_text_gemini(data, api_key, is_base64=True, max_retries=3):
    """
    Gemini OCR for images (especially handwritten or complex layouts).
    Input is either base64 string or raw image bytes.
    """
    if not api_key:
        print("❌ API Key missing for Gemini OCR.")
        return ""
        
    client = Client(api_key=api_key)
    
    # Prompt is tailored to extract text ONLY (no summarization)
    prompt = (
        "Extract ALL text accurately. Preserve formatting, steps, bullet points, equations, "
        "indentation, tables, and line breaks. Do NOT summarize. Return ONLY the raw text."
    )
    
    img_data = base64.b64decode(data) if is_base64 else data
    
    # Create the Image object from bytes
    # IMPORTANT: The mimeType must match the actual image type (which is PNG from PyMuPDF in extract_text_from_pdf)
    img_part = Part.from_bytes(data=img_data, mime_type='image/png')

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

def _clean_raw_text(text):
    """Simple cleaning function to reduce noise and optimize token usage."""
    # 1. Replace multiple newlines with at most two newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    # 2. Trim surrounding whitespace
    text = text.strip()
    return text

def clean_with_gemini(raw_text, api_key):
    """
    Uses Gemini to clean and structure the raw combined text.
    """
    if not api_key:
        print("❌ API Key missing for Gemini cleaning.")
        return "[ERROR] API Key is missing for cleaning step."
        
    client = Client(api_key=api_key)

    prompt = f"""
You are a professional text cleaner and structure expert, tasked with creating a comprehensive, organized, and detailed study outline from raw OCR text.

Your primary goal is **COMPLETENESS and ACCURACY ACROSS ALL PAGES**. You MUST process the entire document content. Do not omit or aggressively summarize content. **ABSOLUTELY DO NOT STOP after the first page or the first section.**

Clean the following raw combined text:
- Fix spelling mistakes, OCR artifacts, and fragmented sentences.
- Preserve ALL conceptual information, definitions, and technical details.
- **Structure the output into a clear, detailed report outline using Markdown:**
    - Use H1 headings (#) for major topics.
    - Use H2 headings (##) for main sections/sub-topics.
    - Use H3 headings (###) for detailed sub-sections or specific concepts.
    - Detailed information must be presented using descriptive bullet points.

**CRITICAL INSTRUCTION FOR SOURCE HANDLING:**
The input text is a concatenation of all PDF pages, separated by '---'. Treat the entire input as one continuous source document. Do NOT output the '---' markers.

**CRITICAL INSTRUCTION FOR VISUALS:**
For complex concepts, processes, or systems that would be significantly clearer with a diagram or illustration, strategically insert a diagram request using the exact format: [Image of X]. 'X' must be a concise, contextually relevant, and domain-specific search query (e.g., [Image of the Data Mining Process Flow]). Insert the tag immediately before or after the relevant text. Be economical; only use tags when they add instructional value.

OCR Text:
{raw_text}

Return ONLY the cleaned, structured text in Markdown format.
"""
    max_retries = 3
    delay = 1
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"🤖 Sending combined text to Gemini for cleaning and structuring (Attempt {attempt})...")

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
            print(f"❌ Gemini Cleaning Error (Attempt {attempt}): {e}")
            if attempt < max_retries:
                time.sleep(delay)
                delay *= 2
            else:
                print("❌ Gemini cleaning failed finally.")
                return f"[ERROR] Gemini cleaning failed after {max_retries} attempts: {e}"

# ----------------------------------------------------------------------
# 5. Core Pipeline Function
# ----------------------------------------------------------------------

def process_document_to_cleaned_text(pdf_file_bytes, api_key):
    """
    The main pipeline function: PDF -> OCR (if needed) -> Combine -> Clean/Structure.
    """
    # 1. Extract raw text and images from PDF
    page_data = extract_text_from_pdf(pdf_file_bytes)
    
    raw_text_pages = []
    page_separator = "\n\n---\n\n"
    
    print(f"Total pages retrieved from PDF extraction: {len(page_data)}")
    
    for page_num, raw_text, base64_img in page_data:
        page_content = ""
        
        if raw_text:
            # Case 1: Use digital text directly
            print(f"  -> Page {page_num}: Using digital text ({len(raw_text)} chars)")
            page_content = raw_text.strip()
        elif base64_img:
            # Case 2: Need to run OCR on the image
            if not api_key:
                print("❌ Cannot run OCR: API Key is missing.")
                continue

            img_bytes = base64.b64decode(base64_img)
            
            # 2. Classify and run appropriate OCR (in this case, simplified to Gemini)
            if is_image_digital(img_bytes):
                # Use Gemini for digital text OCR (Tesseract is disabled)
                ocr_text = extract_text_gemini(base64_img, api_key, is_base64=True) 
            else:
                # Use Gemini for handwritten/fuzzy text
                ocr_text = extract_text_gemini(base64_img, api_key, is_base64=True)
            
            print(f"  -> Page {page_num}: Using OCR text ({len(ocr_text)} chars)")
            page_content = ocr_text.strip()
            
        if page_content:
            raw_text_pages.append(page_content)
            
    # 3. Combine all raw text using a separator only BETWEEN pages
    raw_combined_text = page_separator.join(raw_text_pages)
    
    # 4. Clean up the whole document to remove excessive newlines/noise
    raw_combined_text = _clean_raw_text(raw_combined_text)
    
    print(f"Total combined raw text length sent to cleaning: {len(raw_combined_text)} characters.")
    
    if not raw_combined_text.strip():
        # Returning a clear error message instead of an an empty string for the app to handle
        return None, "[ERROR] Could not extract any text from the document. The document may be empty, or OCR failed on all pages."
        
    # 5. Clean and structure the combined text using Gemini
    cleaned_structured_text = clean_with_gemini(raw_combined_text, api_key)
    
    # The calling function expects (text, error) tuple.
    if cleaned_structured_text.startswith("[ERROR]"):
        return None, cleaned_structured_text
        
    return cleaned_structured_text, None

# ----------------------------------------------------------------------
# 6. Final Output Generation (Memory-based for Streamlit)
# ----------------------------------------------------------------------

def create_pptx_from_markdown(markdown_text):
    """
    Generates a PPTX file in memory from structured Markdown text.
    Handles headings (#, ##, ###) as slides and content.
    """
    prs = Presentation() 
    
    # Split by top-level or secondary headings to define slide breaks
    # This regex looks for a newline followed by #, ##, or ###
    slides_data = re.split(r'(?=\n#+\s)', markdown_text)
    
    # Filter out empty strings from splitting and trim whitespace
    slides_data = [s.strip() for s in slides_data if s.strip()]

    # Layouts: 0=Title Slide, 1=Title and Content
    title_slide_layout = prs.slide_layouts[0] 
    content_slide_layout = prs.slide_layouts[1]

    # Remove the default blank slide
    if prs.slides:
        prs.slides._sldIdLst.pop() 
    
    # Process slides
    for i, slide_text in enumerate(slides_data):
        lines = slide_text.split('\n')
        
        # 1. Extract Title
        title_line = lines[0].strip()
        
        # Find the actual title text, ignoring Markdown formatting (e.g., #, ##, ###)
        title_match = re.match(r'(#+)\s*(.*)', title_line)
        title = title_match.group(2).strip() if title_match else title_line
        
        # Remove the title line and process the rest as content
        content_lines = lines[1:]

        # 2. Determine Slide Layout
        if i == 0 and not title.startswith("##"): 
            # Use Title Slide for the first major topic
            slide = prs.slides.add_slide(title_slide_layout)
            slide.shapes.title.text = title
            
            # Use the first content line as the subtitle/deck description
            if content_lines and content_lines[0].strip():
                # Find subtitle placeholder (typically index 1)
                subtitle_placeholder = slide.placeholders[1]
                subtitle_placeholder.text = content_lines[0].strip()
            
            # Skip the first content line for the rest of the body processing
            slide_content = content_lines[1:]
        else:
            # Use Title and Content for all subsequent slides
            slide = prs.slides.add_slide(content_slide_layout)
            slide.shapes.title.text = title
            slide_content = content_lines
            
        # 3. Populate Content
        
        # CRITICAL FIX: Ensure placeholder index 1 (Body) exists before accessing
        # New (Corrected) Code (Replacing the body placeholder Try/Except block)

            # 3. Populate Content
            body = None
            try:
                # Try to access the content placeholder (usually index 1)
                if len(slide.shapes.placeholders) > 1:
                    body = slide.shapes.placeholders[1].text_frame
                
                # If the slide layout is Title/Content, it should have a body.
                if body is None and content_slide_layout.name in slide.slide_layout.name:
                     # Fallback check for placeholder by index
                    for p in slide.shapes.placeholders:
                        if p.placeholder_format.idx == 1: # Common body index
                            body = p.text_frame
                            break
                        
                if body is None:
                    raise ValueError("No suitable body placeholder found.")
                    
                body.clear()
            
            except Exception as e:
                # CRITICAL: Instead of 'continue', create a generic textbox to save the content.
                print(f"Warning: Placeholder failed for slide {i+1}. Falling back to manual textbox. Error: {e}")
                
                # Manual Textbox Fallback
                left, top, width, height = Inches(1), Inches(1.5), Inches(8.5), Inches(5.5)
                txBox = slide.shapes.add_textbox(left, top, width, height)
                body = txBox.text_frame
                body.clear()
                body.vertical_anchor = MSO_ANCHOR.TOP # Ensure text starts from the top

            # Now, proceed with content insertion using the 'body' text_frame 
            # (which is either the placeholder or the new textbox)
            
            current_level = 0
        
            for line in slide_content:
                line = line.strip()
                if not line:
                    continue

                p = body.add_paragraph()
                
                # Check for image tags BEFORE bullet points, as Gemini's output
                # for image tags will not start with * or -.
                img_match = re.match(r'^\$', line, re.IGNORECASE)

                if img_match:
                    # Case 1: Image Placeholder
                    image_topic = img_match.group(1).strip()
                    p.text = f"**[IMAGE PLACEHOLDER: Insert Image of {image_topic}]**"
                    p.level = 0
                
                # Case 2: Check for sub-bullets (**) or (--) and set level 2
                elif re.match(r'^\s*[\*•-]{2,}\s', line):
                    p.text = re.sub(r'^\s*[\*•-]{2,}\s', '', line).strip()
                    p.level = 1 # Sub-bullet level
                
                # Case 3: Check for bullet points (*, -) and set level 1 (Base)
                elif re.match(r'^[\*•-]\s', line):
                    p.text = re.sub(r'^[\*•-]\s', '', line).strip()
                    p.level = 0 # Base bullet level
                
                # Case 4: Treat other text (sub-headings, normal sentences)
                else:
                    # Check for sub-headings (###) and treat as bolded topic line
                    if line.startswith('###'):
                        p.text = f"**{line.lstrip('#').strip()}**"
                    else:
                        p.text = line
                    p.level = 0

                # Ensure font size is manageable
                p.font.size = Pt(16) 

        
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
    # Create an in-memory file for the markdown content
    markdown_io = io.BytesIO(markdown_text.encode('utf-8'))
    markdown_io.seek(0)
    return markdown_io
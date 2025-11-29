import json
import io
import time
import os
import base64
from google import genai
from google.genai import Client
from google.genai.types import Content, Part
from PIL import Image

# --- Conditional Imports for Libraries used in the advanced pipeline ---
# The main app (streamlit_app.py) handles the installation check and displays warnings.
try:
    from pptx import Presentation
except ImportError:
    Presentation = None
    
try:
    from docx import Document
except ImportError:
    Document = None

try:
    import fitz # PyMuPDF for PDF text extraction and image rendering
except ImportError:
    fitz = None

# OCR and Image Classification dependencies
try:
    import pytesseract
except ImportError:
    pytesseract = None

try:
    import cv2
    import numpy as np
    # NOTE: We assume the user has configured Tesseract PATH if using Windows/Linux
except ImportError:
    cv2 = None
    np = None

try:
    from google.genai import Client
    from google.genai.types import GenerateContentConfig
except ImportError:
    Client = None
    GenerateContentConfig = None

# --------------------------------
# CONFIGURATION
# --------------------------------
# Global client for Gemini Vision/Handwritten OCR
GENAI_CLIENT = None
# --------------------------------


# --------------------------------
# HELPER 1: IMAGE CLASSIFICATION (from classify_image_type.py)
# --------------------------------
def is_image_digital(img_array):
    """
    Classifies an image as digital (printed) or handwritten using OpenCV (cv2) 
    and Tesseract confidence/text length. Operates on a numpy array (cv2 image).
    Returns: True (digital/printed) or False (handwritten/low-confidence).
    """
    if cv2 is None or pytesseract is None:
        return True # Default to digital if libraries are missing

    try:
        img = img_array 
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 1️⃣ Quick check: text length
        text = pytesseract.image_to_string(gray)
        if len(text.strip()) < 20:
            print("[ℹ️] Very little recognizable text (OCR FAILED) → likely handwritten.")
            return False

        # 2️⃣ OCR confidence check
        data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)
        confs = [float(conf) for conf in data["conf"] if conf != '-1']

        if not confs:
            return False # No text detected means treat as handwritten/image

        avg_conf = sum(confs) / len(confs)

        # 3️⃣ Edge density check (A robust indicator for printed text)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size

        # Heuristic rules:
        # Digital: High confidence (e.g., > 80) OR good edge density (> 0.005)
        is_digital = (avg_conf > 80.0) or (edge_density > 0.005)
        
        print(f"[ℹ️] Confidence: {avg_conf:.2f}, Edge Density: {edge_density:.4f} -> Digital: {is_digital}")
        return is_digital
    except Exception as e:
        print(f"⚠️ Classification error, defaulting to digital: {e}")
        return True # Default to digital if classification fails

# --------------------------------
# HELPER 2: OCR ENGINES (from ocr_engine.py)
# --------------------------------
def extract_text_tesseract(img_array):
    """Tesseract OCR for printed/digital text, operating on numpy array."""
    if pytesseract is None:
        return "[ERROR] Tesseract library not found for digital OCR."
    
    try:
        config = r"--psm 3 --oem 3" # psn 3: Fully automatic page segmentation
        text = pytesseract.image_to_string(img_array, config=config)
        return text.strip()
    except Exception as e:
        return f"[TESSERACT ERROR] {e}"

GENAI_CLIENT = None

def extract_text_gemini(image_path_or_bytes, api_key):
    """Gemini Vision OCR using NEW Gemini SDK."""
    global GENAI_CLIENT
    
    # Initialize the Gemini client once
    if GENAI_CLIENT is None:
        try:
            GENAI_CLIENT = genai.Client(api_key=api_key)
        except Exception as e:
            return f"[GEMINI CLIENT ERROR] Failed to initialize: {e}"

    # Convert byte input to a temporary PNG file
    temp_file = "temp_ocr_image.png"
    if isinstance(image_path_or_bytes, bytes):
        with open(temp_file, "wb") as f:
            f.write(image_path_or_bytes)
        image_path = temp_file
    else:
        image_path = image_path_or_bytes

    # Read file bytes for the Vision API
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    content = Content(
        parts=[
            Part.from_bytes(image_bytes, mime_type="image/png"),
            Part.from_text("Extract ALL text accurately. Preserve formatting. Do NOT summarize.")
        ]
    )

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            print(f"✨ Gemini OCR attempt {attempt}/{max_retries}")

            response = GENAI_CLIENT.models.generate_content(
                model="gemini-2.5-flash",
                contents=[content],
                config={
                    "temperature": 0,
                    "max_output_tokens": 4096
                }
            )

            # Cleanup temp file
            if os.path.exists(temp_file):
                os.remove(temp_file)

            return response.text.strip()

        except Exception as e:
            print(f"⚠️ Gemini attempt {attempt}/{max_retries} failed: {e}")
            if attempt < max_retries:
                time.sleep(2)
            else:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                return f"[GEMINI OCR ERROR] Failed after retries: {e}"

# --------------------------------
# HELPER 3: PDF EXTRACTION & OCR ORCHESTRATOR
# --------------------------------
def extract_text_from_pdf(uploaded_file):
    """
    Extracts embedded text from PDF first. If successful, returns the text.
    If text is missing or short, it renders pages as images for OCR fallback.
    Returns: tuple (text, error)
    """
    if fitz is None:
        return None, "PyMuPDF library is not installed."
        
    try:
        pdf_bytes = uploaded_file.read()
        uploaded_file.seek(0) # Reset file pointer
        
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        # 1. Try PyMuPDF embedded text extraction
        embedded_text = ""
        for page in doc:
            embedded_text += page.get_text()
        
        doc.close()

        if len(embedded_text.strip()) > 100:
            print("✅ PyMuPDF: Found sufficient embedded text.")
            return embedded_text, None
        
        print("⚠️ PyMuPDF: Embedded text is too short or missing. Switching to OCR pipeline.")

        # 2. If embedded text fails, prepare for OCR (extract images)
        if not cv2 or not pytesseract or not Client:
             return None, "Embedded text is missing, but advanced OCR libraries (cv2, pytesseract, google-genai) are not installed to perform fallback."

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        image_arrays = [] # Store pages as numpy arrays and image bytes for processing
        
        for i, page in enumerate(doc):
            pix = page.get_pixmap(dpi=200) # Render page as image
            
            # Convert PyMuPDF pixmap to PNG bytes
            img_bytes = pix.tobytes(output="png")
            
            # Convert bytes to a numpy array (cv2 format)
            np_arr = np.frombuffer(img_bytes, dtype=np.uint8)
            img_array = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            image_arrays.append((img_array, img_bytes))
            
        doc.close()
        
        if not image_arrays:
            return None, "PDF opened successfully but no pages could be rendered for OCR."
            
        return image_arrays, "OCR_REQUIRED"

    except Exception as e:
        return None, f"Error during PDF processing: {e}. Libraries for OCR (cv2, pytesseract, google.genai) may be missing."


# --------------------------------
# CORE ORCHESTRATOR FOR ADVANCED PIPELINE
# --------------------------------
def process_document_to_cleaned_text(uploaded_file, api_key):
    """
    Master function to process a PDF, perform fallback OCR if needed, 
    and clean the final text using Gemini.
    """
    # 1. Extract/Render PDF
    result, status = extract_text_from_pdf(uploaded_file)
    
    if status is None:
        # Case 1: PyMuPDF found embedded text
        raw_text = result

    elif status == "OCR_REQUIRED":
        # Case 2: OCR is needed
        image_arrays = result
        page_texts = []
        
        for i, (img_array, img_bytes) in enumerate(image_arrays):
            print(f"-> Processing Page {i+1} for OCR...")
            
            is_digital = is_image_digital(img_array)
            
            if is_digital:
                page_text = extract_text_tesseract(img_array)
                print(f"   -> Digital (Tesseract) extracted {len(page_text)} chars.")
            else:
                page_text = extract_text_gemini(img_bytes, api_key)
                print(f"   -> Handwritten (Gemini Vision) extracted {len(page_text)} chars.")
            
            page_texts.append(f"\n\n--- Page {i+1} ---\n\n{page_text}")

        raw_text = "\n".join(page_texts)
        print("-> OCR complete. All pages combined.")

    else:
        # Case 3: Error during extraction
        return None, status

    # -------------------------------------------------------
    # 2. GEMINI CLEANING BLOCK (NEW GEMINI SDK)
    # -------------------------------------------------------
    try:
        client = genai.Client(api_key=api_key)

        prompt_text = (
            "You are a professional text cleaner and content synthesizer. "
            "Take the messy raw text which may contain OCR errors, bad formatting, "
            "line-break issues, duplicates, headers/footers, and noise. "
            "Fix everything but DO NOT summarize or omit content. "
            "Preserve headings, bullet points, and structure.\n\n"
            f"Clean and structure the following raw OCR text:\n\n{raw_text}\n\n"
            "Return ONLY the cleaned text."
        )

        content = {
            "parts": [
                {"text": prompt_text}
            ]
        }

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[content],
            config={
                "temperature": 0,
                "max_output_tokens": 8192
            }
        )

        # ---- Extract text from new Gemini SDK ----
        try:
            cleaned_text = response.candidates[0].content.parts[0].text.strip()
        except Exception as extract_err:
            return None, f"Gemini Cleaning Error (parsing): {extract_err}"

        return cleaned_text, None

    except Exception as e:
        return None, f"Gemini Cleaning Error: {e}"

# --------------------------------
# CORE: GEMINI LOGIC (Modified from other.py)
# --------------------------------

import time
from google import genai

def get_ai_response(prompt, system_instruction, api_key, model_name="gemini-2.5-flash"):
    """Handles Gemini API call using NEW Python SDK."""
    
    if not api_key:
        return None, "API Key is missing."

    # New client initialization
    client = genai.Client(api_key=api_key)

    max_retries = 3

    for attempt in range(max_retries):
        try:
            # Correct API call for new SDK — ONLY this structure works
            response = client.models.generate_content(
                model=model_name,
                contents=[system_instruction, prompt],
                config={
                    "temperature": 0,
                    "max_output_tokens": 8192,
                    "top_p": 1
                }
            )

            # Extract text
            text = response.text.strip()

            # Clean wrapping
            if text.startswith("```json"):
                text = text.replace("```json", "").replace("```", "").strip()
            elif text.startswith("```"):
                text = text.replace("```", "").strip()

            return text, None

        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            return None, f"Error connecting to AI after multiple retries: {e}"

    return None, "Failed to get AI response."

# --------------------------------
# CORE: BLUEPRINT GENERATION (from ppt.py / other.py)
# --------------------------------
def generate_initial_structure(raw_text, system_instruction, api_key):
    prompt = f"""
        You must generate a presentation structure in STRICT JSON ONLY.

        CLEANED_TEXT:
        \"\"\"{raw_text}\"\"\"

        TASK:
        - Convert the cleaned text into a PowerPoint-style structure.
        - Create clear slide titles.
        - Add bullet points.
        - Expand content when needed.
        - NO explanations.
        - NO text outside JSON.
        - JSON must be: 
        [
            {{
            "title": "...",
            "content": ["...", "..."]
            }},
            ...
        ]
            """
    return get_ai_response(prompt, system_instruction, api_key)

def update_structure(current_json, user_instruction, system_instruction, api_key):
    prompt = f"""
        Return ONLY valid JSON.

        CURRENT_JSON:
        \"\"\"{current_json}\"\"\"

        USER_INSTRUCTION:
        \"\"\"{user_instruction}\"\"\"

        TASK:
        - Modify the JSON according to the instruction.
        - Do not add text outside JSON.
            """
    return get_ai_response(prompt, system_instruction, api_key)


# --------------------------------
# OUTPUT EXPORT LOGIC (from final_output_generator.py, ppt.py, and other.py)
# --------------------------------

def create_pptx(slides_data, template_file=None):
    """Converts the JSON structure into a .pptx and returns it as a BytesIO object."""
    if Presentation is None:
        return None, "python-pptx library is not available."
    
    try:
        data = json.loads(slides_data)
    except:
        return None, "Failed to parse blueprint data for PPTX. Check the JSON format."

    # In Streamlit, templates are usually uploaded or configured, not necessarily in os.path.exists
    prs = Presentation(template_file) if template_file and os.path.exists(template_file) else Presentation()

    TITLE_LAYOUT_INDEX = 0
    CONTENT_LAYOUT_INDEX = 1
    
    # 1. Create Title Slide 
    try:
        title_slide_layout = prs.slide_layouts[TITLE_LAYOUT_INDEX] 
        slide = prs.slides.add_slide(title_slide_layout)
        title = slide.shapes.title
        subtitle = slide.placeholders[1]
        
        main_title = data[0]['title'] if data and data[0].get('title') else "Presentation"
        title.text = main_title
        subtitle.text = f"Generated by Gemini"
    except Exception:
        main_title = "Presentation"
        pass 

    # 2. Create Content Slides
    try:
        bullet_slide_layout = prs.slide_layouts[CONTENT_LAYOUT_INDEX] 
    except IndexError:
        # Fallback to the first layout if layout 1 is missing
        bullet_slide_layout = prs.slide_layouts[0] 
    
    for entry in data:
        if entry.get('title') == main_title and entry is data[0]:
            continue 

        slide = prs.slides.add_slide(bullet_slide_layout)
        shapes = slide.shapes
        
        try:
            title_shape = shapes.title
            title_shape.text = entry.get('title', 'Untitled Slide')
        except:
            pass
        
        try:
            body_shape = shapes.placeholders[1]
            tf = body_shape.text_frame
            tf.word_wrap = True
            tf.clear() 

            for point in entry.get('content', []):
                p = tf.add_paragraph()
                p.text = point
                p.level = 0
        except:
            pass

    # Save to a BytesIO buffer
    ppt_stream = io.BytesIO()
    prs.save(ppt_stream)
    ppt_stream.seek(0)
    return ppt_stream, None

def create_docx(slides_data):
    """Converts the JSON structure into a .docx Word document."""
    if Document is None:
        return None, "python-docx library is not available."
        
    try:
        data = json.loads(slides_data)
    except:
        return None, "Failed to parse blueprint data for DOCX. Check the JSON format."
        
    doc = Document()

    for i, entry in enumerate(data):
        title = entry.get('title', f"Slide {i+1}")
        content = entry.get('content', [])

        # Title/Heading
        if i == 0:
            doc.add_heading(title, level=1)
        else:
            doc.add_heading(title, level=2)

        # Content bullets
        for point in content:
            doc.add_paragraph(point, style='List Bullet') 

        if i < len(data) - 1:
            doc.add_page_break()

    # Save to a BytesIO buffer
    doc_stream = io.BytesIO()
    doc.save(doc_stream)
    doc_stream.seek(0)
    return doc_stream, None

def create_markdown_report(slides_data):
    """Generates a detailed Markdown report from the JSON structure."""
    try:
        data = json.loads(slides_data)
    except:
        return None, "Failed to parse blueprint data for Markdown. Check the JSON format."

    markdown = "# Presentation Content Report\n\n"
    
    for i, entry in enumerate(data):
        title = entry.get('title', f"Slide {i+1}")
        content = entry.get('content', [])

        markdown += f"## Slide {i+1}: {title}\n"
        
        if content:
            for point in content:
                markdown += f"* {point}\n"
        else:
            markdown += "*(No detailed content provided for this slide.)*\n"
        markdown += "\n---\n"
        
    return markdown, None
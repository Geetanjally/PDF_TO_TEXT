import json
import io
import time
import os
import base64
from google import genai
from google.genai import Client
from google.genai.types import Content, Part, GenerateContentConfig
from PIL import Image

# --- Conditional Imports for Libraries used in the advanced pipeline ---
try:
    from pptx_designer import create_pptx_with_style as create_pptx
except ImportError:
    create_pptx = None
    
try:
    from docx import Document
except ImportError:
    Document = None

try:
    import fitz # PyMuPDF for PDF text extraction and image rendering
except ImportError:
    fitz = None

try:
    import pytesseract
except ImportError:
    pytesseract = None

try:
    import cv2
    import numpy as np
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
GENAI_CLIENT = None
# --------------------------------

# --------------------------------
# 2. CORE GEMINI API FUNCTIONS
# --------------------------------

def _get_genai_client(api_key):
    """Initializes and returns the global Gemini API client."""
    global GENAI_CLIENT
    if GENAI_CLIENT is None:
        if not api_key:
            raise ValueError("Gemini API Key is required.")
        GENAI_CLIENT = Client(api_key=api_key)
    return GENAI_CLIENT

def _retry_api_call(func, *args, **kwargs):
    """Implements exponential backoff for API calls."""
    max_retries = 5
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt < max_retries - 1:
                delay = 2 ** attempt
                print(f"API Error: {e}. Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                raise

def extract_text_gemini(image_bytes, api_key):
    """
    Uses the Gemini API with vision capabilities to extract text from an image.
    
    Args:
        image_bytes (bytes): Byte content of the image (e.g., PNG).
        api_key (str): The Gemini API key.
        
    Returns:
        str: The extracted text, or None if extraction fails.
    """
    try:
        client = _get_genai_client(api_key)
    except ValueError as e:
        return None, str(e)
        
    parts = [
        # 1. Image part
        Part.from_bytes(data=image_bytes, mime_type="image/png"),
        
        # 2. Text instruction part
        Part.from_text(text="Extract ALL text accurately from this image. Preserve line breaks and formatting. Do NOT summarize or add commentary. Return ONLY the raw text."),
    ]
    
    try:
        response = _retry_api_call(
            client.models.generate_content,
            model="gemini-2.5-flash",
            contents=parts,
            config=GenerateContentConfig(temperature=0.0)
        )
        return response.text, None
        
    except Exception as e:
        return None, f"Gemini API call failed during text extraction: {e}"


def process_document_to_cleaned_text(uploaded_file, api_key):
    """
    Processes an uploaded file (PDF/Image) to extract raw text, 
    then uses Gemini to clean and structure it.
    
    Args:
        uploaded_file: The uploaded file object (e.g., Streamlit UploadedFile).
        api_key (str): The Gemini API key.
    """
    raw_text = None
    
    if uploaded_file.type == "application/pdf":
        pdf_bytes = uploaded_file.getvalue()
        
        # --- Using fitz (PyMuPDF) to convert PDF page to image bytes ---
        if fitz:
            try:
                doc = fitz.open(stream=pdf_bytes)
                page = doc.load_page(0) # Load first page
                pix = page.get_pixmap(dpi=300)
                
                # Convert pixmap to PNG bytes
                img_bytes = pix.tobytes("png")
                doc.close()
                
                # Now pass the image bytes to Gemini Vision for extraction
                raw_text, error = extract_text_gemini(img_bytes, api_key)
                if error:
                    return None, f"Extraction Error (PDF): {error}"
                
            except Exception as e:
                return None, f"PDF Processing Error: {e}"
        else:
            return None, "PyMuPDF (fitz) library is missing, cannot process PDF."
            
    else: # Image file
        img_bytes = uploaded_file.getvalue()
        raw_text, error = extract_text_gemini(img_bytes, api_key)
        if error:
            return None, f"Extraction Error (Image): {error}"

    # Check if raw text was successfully extracted before proceeding to cleaning
    if not raw_text:
        return None, "Raw text extraction failed or returned empty content."

    # Step 2: Use Gemini to clean and structure the extracted raw text
    clean_prompt = (
        "The following text was extracted from a document. "
        "Review the text and generate a structured, clean JSON list suitable for a presentation. "
        "The JSON MUST follow this exact schema: "
        "[{'title': 'Slide Title 1', 'content': ['Point 1', 'Point 2', '...', 'Point N']}, "
        "{'title': 'Slide Title 2', 'content': ['Point 1', 'Point 2', '...']}, ...]. "
        "Infer logical slide breaks from the content (e.g., section headings, major topic changes). "
        "Use simple bullet points in the 'content' lists. Do not use Markdown formatting in the lists."
        f"\n\nRAW TEXT:\n---\n{raw_text}\n---"
    )
    
    try:
        client = _get_genai_client(api_key)
    except ValueError as e:
        return None, str(e)
        
    # --- Structured JSON generation call ---
    try:
        response = _retry_api_call(
            client.models.generate_content,
            model="gemini-2.5-flash",
            contents=clean_prompt,
            config=GenerateContentConfig(
                response_mime_type="application/json",
                response_schema={
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "The title of the presentation slide."},
                            "content": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "A list of bullet points for the slide content."
                            }
                        },
                        "required": ["title", "content"]
                    }
                }
            )
        )
        return response.text, None
        
    except Exception as e:
        return None, f"Gemini API call failed during structuring/cleaning: {e}"


# --------------------------------
# 3. STRUCTURE MANIPULATION FUNCTIONS
# --------------------------------

def generate_initial_structure(input_text, system_instruction, api_key):
    """
    Generates an initial structured JSON for a given topic or existing text.
    """

    # If input_text is very short, assume it's a topic
    if len(input_text.split()) < 10:
        prompt_content = f"on the topic: '{input_text}'. "
    else:
        # Otherwise assume it is full cleaned text
        prompt_content = f"based on the following content:\n\n{input_text}\n\n"

    # Build the prompt
    prompt = (
        f"{system_instruction}\n\n"
        f"Create a structured JSON outline for a presentation {prompt_content}"
        "The JSON must follow this strictly:\n"
        "[\n"
        "  {\n"
        '    "title": "Slide Title",\n'
        '    "content": ["Point 1", "Point 2", "..."]\n'
        "  }\n"
        "]"
    )

    
    try:
        client = _get_genai_client(api_key)
    except ValueError as e:
        return None, str(e)

    try:
        response = _retry_api_call(
            client.models.generate_content,
            model="gemini-2.5-flash",
            contents=prompt,
            config=GenerateContentConfig(
                response_mime_type="application/json",
                response_schema={
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "The title of the presentation slide."},
                            "content": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "A list of bullet points for the slide content."
                            }
                        },
                        "required": ["title", "content"]
                    }
                }
            )
        )
        return response.text, None
    except Exception as e:
        return None, f"Gemini API call failed during structure generation: {e}"

def update_structure(api_key, existing_json, user_prompt):
    """Updates the existing JSON structure based on a user prompt."""
    
    prompt = (
        "You are an editor modifying a presentation structure. "
        "The following is the current structure (JSON) and a user's request. "
        "Modify the structure based on the request and return the new, complete JSON structure. "
        "Strictly adhere to the JSON schema: "
        "[{'title': 'Slide Title 1', 'content': ['Point 1', 'Point 2', '...']}, ...]. "
        f"\n\nCURRENT JSON:\n---\n{existing_json}\n---\n\nUSER REQUEST: {user_prompt}"
    )

    try:
        client = _get_genai_client(api_key)
    except ValueError as e:
        return None, str(e)
        
    try:
        response = _retry_api_call(
            client.models.generate_content,
            model="gemini-2.5-flash",
            contents=prompt,
            config=GenerateContentConfig(
                response_mime_type="application/json",
                response_schema={
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "The title of the presentation slide."},
                            "content": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "A list of bullet points for the slide content."
                            }
                        },
                        "required": ["title", "content"]
                    }
                }
            )
        )
        return response.text, None
    except Exception as e:
        return None, f"Gemini API call failed during structure update: {e}"


# --------------------------------
# 4. OUTPUT GENERATION FUNCTIONS (PPTX, DOCX, MD)
# --------------------------------

# NOTE: create_pptx is aliased to create_pptx_with_style from pptx_designer.py
if create_pptx is None:
    def create_pptx(slides_data, template_data=None):
        """Placeholder for PPTX creation if the required library is missing."""
        return None, "The 'python-pptx' library is not installed or the advanced designer could not be imported."


def create_docx(slides_data):
    """Generates a DOCX file from JSON structure."""
    if Document is None:
        return None, "The 'python-docx' library is not installed."
        
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

        markdown += f"## {title}\n"
        if content:
            for point in content:
                # Use standard markdown bullet points
                markdown += f"- {point}\n"
        markdown += "\n"

    return markdown, None
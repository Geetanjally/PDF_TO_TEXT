import json
import io
import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_AUTO_SIZE
from pptx.enum.shapes import MSO_SHAPE
# Note for python-pptx v1.0.2: MSO_PLACEHOLDER is not available.
# We will use the integer value for the BODY placeholder (which is 2)
# and for the SUBTITLE placeholder (which is 3 or sometimes 1 depending on layout).
# We also need MSO_ANCHOR, which is in pptx.enum.text
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE

# --- Constants for older python-pptx versions ---
# Placeholder IDs based on standard MSO types for compatibility with v1.0.2
# TITLE: 1 (standard)
BODY_PLACEHOLDER_ID = 2
SUBTITLE_PLACEHOLDER_ID = 3 # Often 3 for Subtitle, or 1 if Title is 0

# --- Helper Function for Styling ---
def _apply_bullet_point_style(paragraph, level):
    """Applies consistent styling for bullet points based on level."""
    # Set the font size and color
    font = paragraph.font
    font.size = Pt(18 - (level * 2)) # Smaller size for deeper levels
    font.name = 'Arial'
    
    # Set the line spacing and indentation
    paragraph.space_after = Pt(8)
    # left_indent handles the distance from the left of the text frame
    paragraph.left_indent = Inches(0.5 + (level * 0.5)) 
    # first_line_indent offsets the bullet character
    paragraph.first_line_indent = Inches(-0.25)

# --- Helper Function for finding best-fit layout ---
def _find_layout_by_name_or_type(prs, target_names, fallback_index=1):
    """
    Searches for a slide layout based on common names or types (Title/Content).
    
    Args:
        prs (Presentation): The presentation object.
        target_names (list): A list of case-insensitive layout names to look for (e.g., 'Title Slide', 'Title and Content').
        fallback_index (int): A fallback index if no matching name is found.
    
    Returns:
        SlideLayout: The found layout or a default fallback.
    """
    # 1. Search by Name
    for layout in prs.slide_layouts:
        if any(name.lower() in layout.name.lower() for name in target_names):
            return layout

    # 2. Search by Index (as a final attempt)
    if len(prs.slide_layouts) > fallback_index:
        return prs.slide_layouts[fallback_index]
    
    # 3. Last resort: Return the very first layout
    if prs.slide_layouts:
        return prs.slide_layouts[0]
        
    raise ValueError("Presentation contains no recognizable slide layouts.")


# --- Main Function ---
def create_pptx_with_style(slides_data, template_data=None):
    """
    Generates a PPTX file from JSON structure using an uploaded template or default style.
    
    ... (docstring content remains the same) ...
    """
    try:
        data = json.loads(slides_data)
        if not isinstance(data, list) or not data:
            return None, "Invalid or empty structure data provided. Expected a list of slide objects."
    except json.JSONDecodeError:
        return None, "Failed to parse blueprint data. Check the JSON format."
    except Exception as e:
        return None, f"An unexpected error occurred during data parsing: {e}"

    # Load template or create a blank presentation
    try:
        if template_data:
            # Load from bytes using BytesIO stream
            template_stream = io.BytesIO(template_data)
            prs = Presentation(template_stream)
        else:
            # Create a default presentation
            prs = Presentation() 
    except Exception as e:
        return None, f"Could not load presentation. Ensure your uploaded file is a valid .pptx. Error: {e}"


    # --- Define Slide Layouts using robust search ---
    try:
        # Fallback index 0 for Title Slide
        title_slide_layout = _find_layout_by_name_or_type(
            prs, ['Title Slide', 'Title Page', 'Title Layout'], 0
        )
        # Fallback index 1 for Title and Content
        content_slide_layout = _find_layout_by_name_or_type(
            prs, ['Title and Content', 'Body', 'Content Layout'], 1
        )
    except ValueError as e:
        return None, f"Configuration Error: {e}"
        
    
    for i, entry in enumerate(data):
        title = entry.get('title', f"Untitled Slide {i+1}")
        content_list = entry.get('content', [])
        remaining_content = content_list

        layout = title_slide_layout if i == 0 else content_slide_layout
        slide = prs.slides.add_slide(layout)
        
        # --- Set Title ---
        # The 'title' shape is usually reliably accessible
        title_ph = slide.shapes.title
        if title_ph:
            title_ph.text = title
        
        # --- Find Main Content Placeholder ---
        content_placeholder = None
        
        # Priority 1: Find the 'BODY' placeholder by type (type 2)
        # This is the most reliable way to target the main bullet point box.
        for shape in slide.placeholders:
            # Check for placeholder type ID (2 is generally BODY)
            if hasattr(shape.placeholder_format, 'type') and shape.placeholder_format.type == BODY_PLACEHOLDER_ID:
                content_placeholder = shape
                break
            # Fallback check for older/non-standard layouts where idx 1 is the main body
            elif i > 0 and shape.placeholder_format.idx == 1 and not content_placeholder:
                content_placeholder = shape
        
        # Priority 2: If Title Slide, try to use the Subtitle placeholder for the first bullet
        if i == 0 and not content_placeholder:
            for shape in slide.placeholders:
                 # Check for placeholder type ID (3 is generally SUBTITLE)
                 if hasattr(shape.placeholder_format, 'type') and shape.placeholder_format.type == SUBTITLE_PLACEHOLDER_ID:
                    if remaining_content:
                        # Set the first point as the subtitle
                        shape.text = remaining_content[0]
                        remaining_content = remaining_content[1:]
                        # Continue searching for a body placeholder if content remains
                        for body_shape in slide.placeholders:
                            if hasattr(body_shape.placeholder_format, 'type') and body_shape.placeholder_format.type == BODY_PLACEHOLDER_ID:
                                content_placeholder = body_shape
                                break

        # Priority 3: Fallback to the placeholder with index 1 (common for content)
        if not content_placeholder and len(slide.placeholders) > 1:
            content_placeholder = slide.placeholders[1]
            
        
        # --- Populate Content Placeholder ---
        if content_placeholder and remaining_content:
            try:
                body = content_placeholder.text_frame
                body.clear()  # Clear any default text
                # auto_size might not be available or behave differently in 1.0.2, 
                # but we leave it here for potential forward compatibility/robustness
                body.auto_size = MSO_AUTO_SIZE.SHAPE_TO_FIT_TEXT
                
                for point in remaining_content:
                    level = 0
                    processed_point = point.strip()
                    
                    # Basic Markdown-like level detection (e.g., ** for sub-level)
                    if processed_point.startswith('**'): 
                        level = 1
                        processed_point = processed_point.lstrip('**').strip()
                    elif processed_point.startswith('*'): 
                        level = 0
                        processed_point = processed_point.lstrip('*').strip()

                    # Add paragraph and apply styling
                    p = body.add_paragraph()
                    p.text = processed_point
                    p.level = level
                    _apply_bullet_point_style(p, level)

            except Exception as e:
                print(f"Warning: Could not populate content for slide {i+1} due to text frame issue. Error: {e}")
        elif remaining_content:
            # Fallback: If no standard content placeholder is found, dump the content into a new textbox
            left = top = Inches(1)
            width = Inches(8.5)
            height = Inches(5.5)
            
            # Position the fallback textbox away from the assumed title position
            txBox = slide.shapes.add_textbox(left, top + Inches(1.5), width, height) 
            tf = txBox.text_frame
            tf.clear()
            tf.vertical_anchor = MSO_ANCHOR.TOP
            
            for point in remaining_content:
                p = tf.add_paragraph()
                p.text = point
                _apply_bullet_point_style(p, 0)
                

    # Save to a BytesIO buffer
    pptx_stream = io.BytesIO()
    prs.save(pptx_stream)
    pptx_stream.seek(0)
    return pptx_stream, None
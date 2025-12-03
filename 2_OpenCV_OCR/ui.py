import os
import json
import streamlit as st
import io # Needed for st.download_button

# --- Import ALL logic from the consolidated Canvas file ---
# This file must exist in the same directory as ui.py
from core_document_generator import (
    process_document_to_cleaned_text,
    generate_initial_structure,
    update_structure,
    create_docx,
    create_markdown_report
    # NOTE: refine_document_text_for_tables is excluded if not in core_document_generator.py
)

# --- NEW IMPORT for the advanced PPTX generation ---
from pptx_designer import create_pptx_with_style # <--- NEW: Using the enhanced function

# --------------------------------
# CONFIGURATION
# --------------------------------
# Ensure your API key is set as an environment variable (GEMINI_API_KEY) or enter it below
import os
import json
import streamlit as st
from dotenv import load_dotenv # Import the tool to load .env file
# ... (rest of the imports) ...


# --------------------------------
# CONFIGURATION & SECRET LOADING
# --------------------------------

# 1. Load variables from .env if running locally. 
# This runs silently on Streamlit Cloud (where .env is missing).
load_dotenv() 

# 2. Securely fetch the API key from the environment.
# This works for both local (.env) and cloud (Streamlit Secrets).
# REMOVE THE HARDCODED FALLBACK KEY ("AIzaSy...")
API_KEY = os.getenv("GEMINI_API_KEY") 

MODEL_NAME = "models/gemini-2.5-flash"
# --------------------------------

# --- Add this crucial check to stop the app if the key is missing ---
if API_KEY is None:
    st.error("🔑 **Error:** Gemini API Key not found.")
    st.info("Please set the `GEMINI_API_KEY` environment variable in a local `.env` file or in Streamlit Cloud Secrets.")
    st.stop()

# --- DESIGN SETTINGS ---
TEMPLATE_DIR = "templates"
DYNAMIC_TEMPLATE_OPTIONS = {} # Holds the loaded options

# NEW: Presentation Styles (The three default settings)
PPT_STYLES = ["Professional", "Creative", "Basic"] 

# -------------------------------

# --- SESSION STATE INITIALIZATION ---
# Initialize session state variables if they don't exist
if 'template_file' not in st.session_state:
    st.session_state.template_file = None
if 'raw_text' not in st.session_state:
    st.session_state.raw_text = None
if 'blueprint_json' not in st.session_state:
    st.session_state.blueprint_json = None
if 'api_key' not in st.session_state:
    st.session_state.api_key = API_KEY
if 'system_instruction' not in st.session_state:
    st.session_state.system_instruction = (
        "You are an expert presentation structure designer. "
        "Create a concise, structured outline where each slide is optimized for presentation. "
        "The output MUST be valid JSON: a list of objects with 'title' (string) and 'content' (list of strings)."
    )
if 'uploaded_template_data' not in st.session_state:
    st.session_state.uploaded_template_data = None


# --------------------------------
# HELPER FUNCTION FOR PREVIEW (NEW)
# --------------------------------

def render_slide_preview(json_data, style_name="Professional"):
    """
    Renders a visual preview of the slides in Streamlit, simulating the chosen style's theme.
    This simulates the "different tab" version of the PPT before downloading.
    """
    try:
        data = json.loads(json_data)
        st.info(f"👀 Below is a simplified preview of your slide content, simulating the **{style_name}** theme. The final PPTX will have the correct shapes and formatting.")
        
        # Define simple colors/fonts for the Streamlit preview based on the styles for visual feedback
        preview_styles = {
            "Professional": {"border": "#003366", "bg": "#f0f2f6"}, # Navy/Light Gray
            "Creative": {"border": "#e65100", "bg": "#fff3e0"},      # Orange/Cream
            "Basic": {"border": "#000000", "bg": "#ffffff"},         # Black/White
            "Custom Template (Styles Ignored)": {"border": "#10b981", "bg": "#ecfdf5"}
        }
        theme = preview_styles.get(style_name, preview_styles["Professional"])
        
        # Grid layout for preview
        cols = st.columns([1, 1])
        
        for i, slide in enumerate(data):
            col_index = i % 2
            with cols[col_index]:
                # Use markdown with inline HTML/CSS for a styled card effect
                slide_html = f"""
                <div style="
                    border: 3px solid {theme['border']}; 
                    border-radius: 10px; 
                    padding: 15px; 
                    margin-bottom: 20px;
                    background-color: {theme['bg']};
                    box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
                ">
                    <h5 style="color:{theme['border']}; margin-top: 0px; margin-bottom: 5px;">
                        📄 Slide {i+1}: {slide.get('title', 'Untitled')}
                    </h5>
                    <hr style="border-top: 1px solid #ccc; margin-top: 5px; margin-bottom: 10px;">
                """
                
                content = slide.get('content', [])
                for point in content:
                    point = point.strip()
                    # Simulate bullet levels based on the pptx_designer logic
                    if point.startswith("[CHART:"):
                        slide_html += f'<p style="color: #9c27b0; font-style: italic;">📊 **Chart Placeholder:** {point.splitlines()[0]}...</p>'
                    elif point.startswith("|"):
                        slide_html += f'<p style="color: #00897b; font-style: italic;">🗓️ **Table Data:** {point.splitlines()[0]}...</p>'
                    elif point.startswith('***'):
                        slide_html += f'<p style="margin-left: 40px; font-weight: bold; margin-bottom: 0;">• {point.lstrip("***").strip()}</p>'
                    elif point.startswith('**'):
                         slide_html += f'<p style="margin-left: 20px; font-weight: normal; margin-bottom: 0;">• {point.lstrip("**").strip()}</p>'
                    else:
                        slide_html += f'<p style="margin-left: 0px; font-weight: normal; margin-bottom: 0;">• {point.lstrip("*").strip()}</p>'

                slide_html += "</div>"
                st.markdown(slide_html, unsafe_allow_html=True)
                
    except json.JSONDecodeError:
        st.error("Could not render preview: Blueprint is not valid JSON.")
    except Exception as e:
        st.error(f"Could not render preview: {e}")


# --------------------------------
# CALLBACK FUNCTIONS
# --------------------------------

def run_extraction_and_cleaning(uploaded_file, api_key):
    """Callback to run the PDF extraction and Gemini cleaning pipeline."""
    with st.spinner("Step 1: Extracting text from PDF (including OCR fallback if needed)..."):
        # Assuming process_document_to_cleaned_text handles the file bytes and type correctly
        # file_bytes = uploaded_file.read()
        # NOTE: The provided core_document_generator snippet doesn't show refine_document_text_for_tables
        # We proceed assuming a simplified flow.
        cleaned_text, error = process_document_to_cleaned_text(uploaded_file, api_key)


    if error:
        st.error(f"Extraction/Cleaning Error: {error}")
        st.session_state.raw_text = None
        st.session_state.blueprint_json = None
        return

    st.session_state.raw_text = cleaned_text
    st.success("✅ Text extracted and cleaned successfully!")
    
    # Auto-generate initial blueprint after cleaning
    run_blueprint_generation(cleaned_text, api_key)

def run_blueprint_generation(cleaned_text, api_key):
    """Callback to generate the initial JSON blueprint."""
    if not cleaned_text:
        st.error("Cannot generate blueprint: Cleaned text is missing.")
        return

    with st.spinner("Step 2: Generating initial presentation blueprint using Gemini..."):
        blueprint_json, error = generate_initial_structure(
            cleaned_text, 
            st.session_state.system_instruction, 
            api_key
        )
    
    if error:
        st.error(f"Blueprint Generation Error: {error}")
        st.session_state.blueprint_json = None
        return
    
    st.session_state.blueprint_json = blueprint_json
    st.success("✅ Presentation blueprint generated!")
    st.rerun() # Rerun to display the editor

def run_blueprint_update(user_instruction, api_key):
    """Callback to update the existing JSON blueprint."""
    if not st.session_state.blueprint_json:
        st.error("Cannot update blueprint: No blueprint exists.")
        return

    with st.spinner("Step 3: Updating blueprint based on instruction..."):
        # Corrected call: Pass only 3 arguments in the correct order:
        # 1. api_key
        # 2. existing_json (st.session_state.blueprint_json)
        # 3. user_prompt (user_instruction)
        updated_json, error = update_structure(
            api_key,
            st.session_state.blueprint_json, 
            user_instruction
        )
        
    if error:
        st.error(f"Blueprint Update Error: {error}")
        return

    try:
        # Validate and re-pretty-print the JSON to ensure it's clean
        parsed_json = json.loads(updated_json)
        st.session_state.blueprint_json = json.dumps(parsed_json, indent=2)
        st.success("✅ Blueprint updated successfully!")
    except json.JSONDecodeError:
        st.error("Gemini returned invalid JSON. Please re-run or edit manually.")
        st.session_state.blueprint_json = updated_json # Keep the raw output for debugging
    st.rerun() # Rerun to refresh the editor

# --------------------------------
# MAIN APPLICATION FLOW
# --------------------------------
import streamlit as st
import json
# NOTE: Ensure all necessary constants and functions 
# (PPT_STYLES, MODEL_NAME, run_extraction_and_cleaning, etc.) 
# are correctly imported or defined in your full application file.

# --- 0. Streamlit Session State Initialization (Best Practice) ---
# Initialize session state variables if they don't exist
if 'api_key' not in st.session_state:
    st.session_state.api_key = ''
if 'blueprint_json' not in st.session_state:
    st.session_state.blueprint_json = ''
if 'uploaded_template_data' not in st.session_state:
    st.session_state.uploaded_template_data = None


import streamlit as st
import json
# NOTE: Ensure all necessary constants and functions are correctly imported

# --- 0. Streamlit Session State Initialization (Best Practice) ---
# Initialize session state variables if they don't exist
if 'api_key' not in st.session_state:
    st.session_state.api_key = ''
if 'blueprint_json' not in st.session_state:
    st.session_state.blueprint_json = ''
if 'uploaded_template_data' not in st.session_state:
    st.session_state.uploaded_template_data = None


import streamlit as st
import json
# NOTE: Ensure all necessary constants and functions 
# (PPT_STYLES, MODEL_NAME, run_extraction_and_cleaning, etc.) 
# are correctly imported or defined in your full application file.

# --- 0. Streamlit Session State Initialization (Best Practice) ---
# Initialize session state variables if they don't exist
if 'api_key' not in st.session_state:
    st.session_state.api_key = ''
if 'blueprint_json' not in st.session_state:
    st.session_state.blueprint_json = ''
if 'uploaded_template_data' not in st.session_state:
    st.session_state.uploaded_template_data = None

import streamlit as st
import json
# NOTE: Ensure all necessary constants and functions 
# (PPT_STYLES, MODEL_NAME, run_extraction_and_cleaning, create_pptx_with_style,
# create_docx, create_markdown_report, render_slide_preview, run_blueprint_update) 
# are correctly imported or defined in your full application file.

# --- 0. Streamlit Session State Initialization (Best Practice) ---
# Initialize session state variables if they don't exist
if 'api_key' not in st.session_state:
    st.session_state.api_key = ''
if 'blueprint_json' not in st.session_state:
    st.session_state.blueprint_json = ''
if 'uploaded_template_data' not in st.session_state:
    st.session_state.uploaded_template_data = None


import streamlit as st
import json
# NOTE: Ensure all necessary constants and functions 
# (PPT_STYLES, MODEL_NAME, run_extraction_and_cleaning, create_pptx_with_style,
# create_docx, create_markdown_report, render_slide_preview, run_blueprint_update) 
# are correctly imported or defined in your full application file.

# --- 0. Streamlit Session State Initialization (Best Practice) ---
# Initialize session state variables if they don't exist
if 'api_key' not in st.session_state:
    st.session_state.api_key = ''
if 'blueprint_json' not in st.session_state:
    st.session_state.blueprint_json = ''
if 'uploaded_template_data' not in st.session_state:
    st.session_state.uploaded_template_data = None


def main():
    # Set to wide layout for the custom centered columns trick
    st.set_page_config(page_title="⚙️ NoteScan", layout="wide")
    
    
    # --- 1. HIDDEN CONFIGURATION (SIDEBAR) ---
    # API Key Input (Hidden from the main view)
    api_key_input = st.sidebar.text_input(
        "🔑 Enter Gemini API Key", 
        type="password", 
        value=st.session_state.api_key
    )
    # Update session state
    st.session_state.api_key = api_key_input
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Status")
    api_key = st.session_state.api_key

    if api_key:
        st.sidebar.success("API Key Loaded.")
        st.sidebar.info(f"Model: {MODEL_NAME}")
    else:
        st.sidebar.warning("API Key needed to run the AI.")


    # --- 2. MAIN PAGE CONTENT (Custom Centered Layout) ---
    # Create side padding columns and a center column (1:6:1 ratio)
    col_left, col_center, col_right = st.columns([1, 6, 1]) 
    
    with col_center:
        st.title("🚀 NoteScan: Multi-Format AI Suite")
        
        # --- A. OUTPUT SELECTION ---
        output_type = st.radio(
            "What type of output do you need?", 
            ["Presentation (PPTX)", "Word Document (DOCX) & Markdown", "Both"], 
            horizontal=True,
            index=0 # Default to Presentation
        )
        st.markdown("---")
        
        # Define what kind of outputs are needed based on user choice
        is_pptx_output = output_type in ["Presentation (PPTX)", "Both"]
        is_doc_output = output_type in ["Word Document (DOCX) & Markdown", "Both"]
        
        selected_style = None # Initialize selected_style
        
        # --- B. CONDITIONAL PRESENTATION SETUP ---
        if is_pptx_output:
            st.markdown("### 🎨 Presentation Template & Style ")
            
            col_template, col_style = st.columns([1, 1])

            # 1. PPTX Template Upload
            with col_template:
                uploaded_template = st.file_uploader(
                    "Optional: Upload PPTX Template (Limit 200MB)",
                    type="pptx",
                    key="pptx_template_uploader"
                )
                if uploaded_template:
                    st.session_state.uploaded_template_data = uploaded_template.read()
                    st.success(f"Template '{uploaded_template.name}' loaded.")
                else:
                    st.session_state.uploaded_template_data = None
                    st.info("Using default blank PowerPoint template.")

            # 2. Presentation Style Selection
            with col_style:
                if st.session_state.uploaded_template_data:
                    selected_style = "Custom Template (Styles Ignored)"
                    st.selectbox(
                        "Presentation Style:", 
                        [selected_style], 
                        disabled=True,
                        help="Custom template overrides default styles."
                    )
                    st.warning("Custom template overrides default styles.")
                else:
                    selected_style = st.selectbox(
                        "Presentation Style:", 
                        PPT_STYLES, 
                        index=0, 
                        help="Choose a default style: Professional, Creative, or Basic."
                    )
            
            st.markdown("---")
        
        # --- C. MAIN WORKFLOW ---
        if not api_key:
            st.error("Please provide a Gemini API Key in the sidebar to proceed.")
            return

        # 1. File Upload
        uploaded_file = st.file_uploader(
            "Upload a PDF Document (handwritten or printed)", 
            type="pdf"
        )

        if uploaded_file and st.button("Process Document & Generate Initial Blueprint"):
            run_extraction_and_cleaning(uploaded_file, api_key)
            
        st.markdown("---")

        # 2. Blueprint Editor (Tabs)
        if st.session_state.blueprint_json:
            
            st.subheader("Presentation Blueprint & Generation")
            
            # Show tabs based on required output
            tab_names = []
            if is_pptx_output:
                tab_names.extend(["👁️ Slide Preview", "✏️ Edit Content"])
            else:
                tab_names.append("✏️ Edit Content")
                 
            tab_names.append("💾 Download Files")
            
            # Dynamically create tabs
            tabs = st.tabs(tab_names)
            
            # Map tabs for easier reference
            tab_map = {name: tab for name, tab in zip(tab_names, tabs)}
            
            # --- TAB 1: Slide Preview (Only for PPTX output) ---
            if "👁️ Slide Preview" in tab_map:
                with tab_map["👁️ Slide Preview"]:
                    render_slide_preview(st.session_state.blueprint_json, selected_style) 

            # --- TAB 2: Edit JSON / AI Modification ---
            edit_tab = tab_map["✏️ Edit Content"] if "✏️ Edit Content" in tab_map else tabs[0] 
            with edit_tab:
                col1, col2 = st.columns([1, 1])

                with col1:
                    st.subheader("JSON Editor")
                    
                    edited_json = st.text_area(
                        "Edit the JSON structure below (MUST remain valid JSON)",
                        st.session_state.blueprint_json,
                        height=500
                    )

                    if edited_json != st.session_state.blueprint_json:
                        st.session_state.blueprint_json = edited_json
                        try:
                            json.loads(edited_json)
                            st.success("JSON updated locally. Check preview tab.")
                        except json.JSONDecodeError:
                            st.error("Invalid JSON format detected. Please correct the structure.")


                with col2:
                    st.subheader("AI Modification")
                    
                    modification_instruction = st.text_input(
                        "Instruct the AI to modify the structure (e.g., 'Combine slides 2 and 3')",
                        key="mod_instruction"
                    )
                    if st.button("Apply AI Modification") and modification_instruction:
                        run_blueprint_update(modification_instruction, api_key)
            
            # --- TAB 3: Download (MODIFIED FOR WIDE, STACKED BUTTONS) ---
            with tab_map["💾 Download Files"]:
                
                # 1. New Header
                st.markdown("### ⬇️ Download Options")
                
                final_json = st.session_state.blueprint_json
                
                # --- PowerPoint Download (Conditional) ---
                if is_pptx_output:
                    st.markdown("#### PowerPoint (.pptx)")
                    st.markdown(f"**Style:** {'Custom Template' if st.session_state.uploaded_template_data else selected_style}")
                    
                    # Use a wide button for generation
                    if st.button("Generate & Download PPTX", use_container_width=True, key="generate_pptx"):
                        with st.spinner(f"Generating PPTX..."):
                            pptx_stream, pptx_error = create_pptx_with_style( 
                                final_json, 
                                theme_name=selected_style, 
                                template_data=st.session_state.uploaded_template_data 
                            )
                        
                            if pptx_stream:
                                # Show the download button after generation (also wide)
                                st.download_button(
                                    label="Download PowerPoint File",
                                    data=pptx_stream,
                                    file_name="notescan_presentation.pptx",
                                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                                    use_container_width=True
                                )
                                st.success("PPTX generated! Click Download button above.")
                            elif pptx_error:
                                st.error(f"PPTX Error: {pptx_error}")
                    # st.markdown("---") # Separator between file types

                # --- Word Document Download (Conditional) ---
                if is_doc_output:
                    st.markdown("#### Word Document (.docx)")
                    docx_stream, docx_error = create_docx(final_json) 
                    
                    if docx_stream:
                        st.download_button(
                            label="Download Word Document (.docx)",
                            data=docx_stream,
                            file_name="notescan_report.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            use_container_width=True
                        )
                    elif docx_error:
                        st.error(f"DOCX Error: {docx_error}")
                    # st.markdown("---") # Separator between file types


                    # --- Markdown Report Download (Conditional) ---
                    st.markdown("#### Markdown Report (.md)")
                    markdown_content, markdown_error = create_markdown_report(final_json) 
                    
                    if markdown_content:
                        st.download_button(
                            label="Download Markdown Report (.md)",
                            data=markdown_content.encode('utf-8'),
                            file_name="notescan_report.md",
                            mime="text/markdown",
                            use_container_width=True
                        )
                    elif markdown_error:
                        st.error(f"Markdown Error: {markdown_error}")

# ----------------------------------------------------
# 3. FOOTER IMPLEMENTATION 
# ----------------------------------------------------
        st.markdown("---") # Optional separator line
        st.markdown(
            """
            <style>
            .footer {
                padding-top: 20px; /* Reduced padding from 50px */
                padding-bottom: 20px;
                text-align: center;
                font-size: 0.8rem;
                color: #555555; /* Changed color to dark gray for visibility */
            }
            </style>
            <div class="footer">
                Developed by Geetanjally | Powered by Google Gemini & OpenCV OCR
            </div>
            """, 
            unsafe_allow_html=True
        )


if __name__ == "__main__":
    main()
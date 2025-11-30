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
    # REMOVED: create_pptx (Now handled by pptx_designer.py)
    create_docx,
    create_markdown_report
)

# --- NEW IMPORT for the advanced PPTX generation ---
from pptx_designer import create_pptx_with_style # <--- NEW: Using the enhanced function

# --------------------------------
# CONFIGURATION
# --------------------------------
# Ensure your API key is set as an environment variable (GEMINI_API_KEY) or enter it below
# NOTE: We now pass the API_KEY directly to the core functions
API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyAzHf66I6a1uHUbC1-PnFCK6KyBUZTOJYI") 
MODEL_NAME = "models/gemini-2.5-flash"

# --- DESIGN SETTINGS: Dynamic Template Folder (Not used in this in-memory example, but kept for context) ---
TEMPLATE_DIR = "templates"
DYNAMIC_TEMPLATE_OPTIONS = {} # Holds the loaded options
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
# CALLBACK FUNCTIONS
# --------------------------------

def run_extraction_and_cleaning(uploaded_file, api_key):
    """Callback to run the PDF extraction and Gemini cleaning pipeline."""
    with st.spinner("Step 1: Extracting text from PDF (including OCR fallback if needed)..."):
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
        updated_json, error = update_structure(
            st.session_state.blueprint_json, 
            user_instruction,
            st.session_state.system_instruction, 
            api_key
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
def main():
    st.set_page_config(page_title="Gemini PPT Generator", layout="wide")
    st.title("💡 AI-Powered Presentation Generator")

    # --- Sidebar for Configuration ---
    st.sidebar.header("Configuration")
    
    # API Key Input
    if not st.session_state.api_key:
        st.session_state.api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")
    else:
        st.sidebar.success("API Key Loaded.")
        
    st.sidebar.markdown("---")
    
    # --- New Template Upload Feature ---
    uploaded_template = st.sidebar.file_uploader(
        "Optional: Upload PPTX Template",
        type="pptx",
        key="pptx_template_uploader"
    )

    if uploaded_template:
        # Read the file data into session state as bytes for core function use
        # This allows the function to use io.BytesIO(data) to load the presentation
        st.session_state.uploaded_template_data = uploaded_template.read()
        st.sidebar.success(f"Template '{uploaded_template.name}' loaded.")
    else:
        st.session_state.uploaded_template_data = None
        st.sidebar.info("Using default blank PowerPoint template.")


    st.sidebar.markdown("### Status")
    
    if st.session_state.api_key:
        st.sidebar.success(f"Model: {MODEL_NAME}")
    
    # --- Main Workflow ---
    api_key = st.session_state.api_key
    if not api_key:
        st.warning("Please enter your Gemini API Key in the sidebar to begin.")
        return

    # 1. File Upload
    uploaded_file = st.file_uploader(
        "Upload a PDF Document (handwritten or printed)", 
        type="pdf"
    )

    if uploaded_file and st.button("Process Document & Generate Initial Blueprint"):
        run_extraction_and_cleaning(uploaded_file, api_key)
        
    st.markdown("---")

    # 2. Blueprint Editor (Editable JSON)
    if st.session_state.blueprint_json:
        col1, col2 = st.columns([1, 1])

        with col1:
            st.subheader("Presentation Blueprint (JSON Editor)")
            
            # The user can edit the JSON directly here
            edited_json = st.text_area(
                "Edit the JSON structure below (MUST remain valid JSON)",
                st.session_state.blueprint_json,
                height=500
            )

            if edited_json != st.session_state.blueprint_json:
                st.session_state.blueprint_json = edited_json

            # User instruction for modification
            modification_instruction = st.text_input(
                "Or, instruct the AI to modify the structure (e.g., 'Combine slides 2 and 3')",
                key="mod_instruction"
            )
            if st.button("Apply AI Modification") and modification_instruction:
                run_blueprint_update(modification_instruction, api_key)

        with col2:
            st.subheader("Final Output Generation")
            
            # 3. Final Outputs
            final_json = st.session_state.blueprint_json
            
            # --- PPTX Generation ---
            # NOTE: Calling the new function 'create_pptx_with_style' and passing the raw template data bytes
            pptx_stream, pptx_error = create_pptx_with_style(
                final_json, 
                st.session_state.uploaded_template_data # <--- Passing the template bytes
            )
            
            if pptx_stream:
                st.download_button(
                    label="Download PowerPoint (.pptx)",
                    data=pptx_stream,
                    file_name="gemini_presentation.pptx",
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
                )
            elif pptx_error:
                 st.error(f"PPTX Error: {pptx_error}")
            
            # --- DOCX Generation (Unchanged) ---
            docx_stream, docx_error = create_docx(final_json)
            if docx_stream:
                st.download_button(
                    label="Download Word Document (.docx)",
                    data=docx_stream,
                    file_name="gemini_report.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            elif docx_error:
                 st.error(f"DOCX Error: {docx_error}")

            # --- Markdown Generation (Unchanged) ---
            markdown_content, markdown_error = create_markdown_report(final_json)
            if markdown_content:
                st.download_button(
                    label="Download Markdown Report (.md)",
                    data=markdown_content.encode('utf-8'),
                    file_name="gemini_report.md",
                    mime="text/markdown"
                )
            elif markdown_error:
                 st.error(f"Markdown Error: {markdown_error}")

if __name__ == "__main__":
    main()
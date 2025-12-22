import os
import json
import streamlit as st
import io
from dotenv import load_dotenv 

from core_document_generator import (
    process_document_to_cleaned_text,
    generate_initial_structure,
    update_structure,
    create_docx,
    create_markdown_report
)
from pptx_designer import create_pptx_with_style

# --------------------------------
# CONFIGURATION & SECRET LOADING
# --------------------------------

# 1. Load variables from .env if running locally. 
load_dotenv() 

# 2. Securely fetch the API key from the environment.
API_KEY = os.getenv("GEMINI_API_KEY") 
# MODEL_NAME = "models/gemini-2.5-flash" 
MODEL_NAME = "models/gemini-flash-latest"

# --- DESIGN SETTINGS ---
PPT_STYLES = ["Professional", "Creative", "Basic"] 

# --------------------------------
# SESSION STATE INITIALIZATION
# --------------------------------
# Initialize session state variables if they don't exist
if 'raw_text' not in st.session_state:
    st.session_state.raw_text = None
if 'blueprint_json' not in st.session_state:
    st.session_state.blueprint_json = None
if 'system_instruction' not in st.session_state:
    st.session_state.system_instruction = (
        "You are an expert presentation structure designer. "
        "Create a concise, structured outline where each slide is optimized for presentation. "
        "The output MUST be valid JSON: a list of objects with 'title' (string) and 'content' (list of strings)."
    )
if 'uploaded_template_data' not in st.session_state:
    st.session_state.uploaded_template_data = None


# --------------------------------
# HELPER FUNCTION FOR PREVIEW (kept as is)
# --------------------------------

def render_slide_preview(json_data, style_name="Professional"):
    """
    Renders a visual preview of the slides in Streamlit, simulating the chosen style's theme.
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
# CALLBACK FUNCTIONS (st.rerun() removed)
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
    # st.rerun() removed - state change triggers re-run

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
    # st.rerun() removed - state change triggers re-run


# --------------------------------
# MAIN APPLICATION FLOW
# --------------------------------

def main():
    # Set to wide layout for better use of space
    st.set_page_config(page_title="⚙️ NoteScan", layout="wide")

    # Access the global variables defined at the top of the script
    global API_KEY, MODEL_NAME 

    # --- API KEY CHECK (Silent Stop) ---
    if not API_KEY:
        st.error("🔑 **Critical Error:** Gemini API Key is missing.")
        st.info("Please set the `GEMINI_API_KEY` environment variable in a local `.env` file or in Streamlit Cloud Secrets.")
        st.stop()
    # --- END CRITICAL FAILURE BLOCK ---
    
    # --- Inject CSS for Button Styling (Best Practice: Inject early) ---
    # --- UPDATED CSS SECTION ---
    # Increased selector specificity to ensure it overrides Streamlit defaults
    st.markdown("""
        <style>
        /* Target buttons that contain the specific text for processing */
        div.stButton > button {
            transition: all 0.3s ease-in-out !important;
        }

        /* Targeting the specific process button by its text content proxy */
        /* Streamlit wraps text in a <p> or <span> inside the button */
        div.stButton > button:has(div[data-testid="stMarkdownContainer"] p:contains("Process")) {
            background-color: #6366f1 !important;
            color: white !important;
            border-radius: 12px !important;
            border: 2px solid #6366f1 !important;
            font-weight: 700 !important;
            height: 3em !important;
        }

        /* Fallback: styling based on the specific key 'process_step_2' */
        button[key="process_step_2"] {
            background-color: #6366f1 !important;
            color: white !important;
            border-radius: 12px !important;
            border: none !important;
            padding: 15px !important;
            font-size: 16px !important;
            font-weight: bold !important;
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4) !important;
        }

        button[key="process_step_2"]:hover {
            background-color: #4f46e5 !important;
            box-shadow: 0 6px 20px rgba(79, 70, 229, 0.6) !important;
            transform: translateY(-2px) !important;
        }

        /* Styling other specific buttons */
        button[key="generate_pptx"] {
            background-color: #10b981 !important;
            color: white !important;
        }
        
        /* Ensure the text inside the colored button is white */
        button[key="process_step_2"] p {
            color: white !important;
        }
        </style>
        """, unsafe_allow_html=True)


    # --- MAIN PAGE CONTENT (Custom Centered Layout) ---
    # NOTE: Adjusted ratio for slightly more padding, [1, 5, 1] works well too.
    col_left, col_center, col_right = st.columns([1, 5, 1]) 
    
    with col_center:
        st.markdown(
            """
            <h1 style='text-align: center;'>🚀 NoteScan: Multi-Format AI Suite</h1>
            """, 
            unsafe_allow_html=True
        )
        
        # --- A. OUTPUT SELECTION (Always Visible) ---
        st.markdown("### **What Type Of Document Do You Want To Create?**")
        output_type = st.radio( 
            "Placeholder",
            ["Presentation (PPTX)", "Word Document (DOCX) & Markdown", "Both"], 
            horizontal=True,
            index=0, # Default to Presentation
            label_visibility="collapsed"
        )
        st.markdown("---")
        
        # Define what kind of outputs are needed based on user choice
        is_pptx_output = output_type in ["Presentation (PPTX)", "Both"]
        is_doc_output = output_type in ["Word Document (DOCX) & Markdown", "Both"]
        
        selected_style = None # Initialize selected_style
        
        # ------------------------------------------------------------------
        # --- STEP 1: FILE UPLOAD (Always Visible) ---
        # ------------------------------------------------------------------
        
        # 1. Use st.markdown to display the large, bold label
        st.markdown("### **Upload a PDF Document (Handwritten or Printed)**")

        # 2. Use st.file_uploader with the label completely hidden
        uploaded_file = st.file_uploader(
            "Placeholder", # This string is required by the function, but won't be seen.
            type="pdf",
            label_visibility="collapsed"
        )

        # ------------------------------------------------------------------
        # --- STEP 2: OPTIONS & PROCESS (Conditional on File) ---
        # ------------------------------------------------------------------
        if uploaded_file:
            st.success("PDF file loaded. Proceed to options.")
            
            # B. CONDITIONAL PRESENTATION SETUP (Only appears if PPTX is chosen)
            if is_pptx_output:
                st.markdown("### 🎨 Presentation Template & Style ")
                
                # col_center = st.container() <-- REMOVED: Redundant and breaks layout inside this column block

                # 1. PPTX Template Upload
                # We are implicitly inside 'with col_center:'
                uploaded_template = st.file_uploader(
                    "**Optional: Upload PPTX Template (Limit 200MB)**",
                    type="pptx",
                    key="pptx_template_uploader"
                )
                if uploaded_template:
                    # Ensure template data is read and stored on re-run
                    st.session_state.uploaded_template_data = uploaded_template.read()
                    st.success(f"Template '{uploaded_template.name}' loaded.")
                # Part of the PPTX Template Upload logic
                else:
                    st.session_state.uploaded_template_data = None
                    st.info("No custom template uploaded. Default styles will be available below.")
                    st.markdown("---")

                # 2. Presentation Style Selection
                # We are implicitly inside 'with col_center:'
                if st.session_state.uploaded_template_data:
                    selected_style = "Custom Template (Styles Ignored)"
                    st.selectbox(
                        "Presentation Style:", 
                        [selected_style], 
                        disabled=True,
                        help="Custom template overrides default styles.",
                        key="selected_style_disabled" # Added explicit key
                    )
                    st.warning("Custom template overrides default styles.")
                else:
                    # Assuming PPT_STYLES is defined globally
                    selected_style = st.selectbox(
                        "**Presentation Style:**", 
                        PPT_STYLES, 
                        index=0, 
                        help="Choose a default style: Professional, Creative, or Basic.",
                        key="selected_style_enabled" # Added explicit key
                    )
                
            
            # C. Trigger button for processing - Now placed AFTER options are set
            # This uses the custom CSS defined at the top
            if st.button("Click to Process Document & Generate Initial Blueprint", use_container_width=True, key="process_step_2"):
                run_extraction_and_cleaning(uploaded_file, API_KEY)

        # ------------------------------------------------------------------
        # --- STEP 3: BLUEPRINT EDITOR & DOWNLOAD TABS (Conditional on Blueprint) ---
        # ------------------------------------------------------------------
        if st.session_state.get('blueprint_json'):
            
            st.subheader("Presentation Blueprint & Generation")
            
            # --- Tab creation logic (no change needed here) ---
            tab_names = []
            if is_pptx_output:
                tab_names.extend(["👁️ Slide Preview", "✏️ Edit Content"])
            else:
                tab_names.append("✏️ Edit Content")
            tab_names.append("💾 Download Files")
                
            tabs = st.tabs(tab_names)
            tab_map = {name: tab for name, tab in zip(tab_names, tabs)}
            
            # --- TAB 1: Slide Preview ---
            if "👁️ Slide Preview" in tab_map:
                with tab_map["👁️ Slide Preview"]:
                    # Pass the selected_style variable
                    render_slide_preview(st.session_state.blueprint_json, selected_style) 

            # --- TAB 2: Edit JSON / AI Modification ---
            edit_tab = tab_map.get("✏️ Edit Content", tabs[0]) 
            with edit_tab:
                col1, col2 = st.columns([1, 1])

                with col1:
                    st.subheader("JSON Editor")
                    edited_json = st.text_area(
                        "Edit the JSON structure below (MUST remain valid JSON)",
                        st.session_state.blueprint_json,
                        height=500,
                        key="json_editor_input" # Added explicit key
                    )
                    # JSON update logic
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
                    # ADDED EXPLICIT KEY HERE
                    if st.button("Apply AI Modification", use_container_width=True, key="apply_ai_mod_button"):
                        run_blueprint_update(modification_instruction, API_KEY)
            
            # --- TAB 3: Download ---
            with tab_map["💾 Download Files"]:
                
                st.markdown("### ⬇️ Download Options")
                
                final_json = st.session_state.blueprint_json
                
                # --- PowerPoint Download (Conditional) ---
                if is_pptx_output:
                    st.markdown("#### PowerPoint (.pptx)")
                    st.markdown(f"**Style:** {'Custom Template' if st.session_state.uploaded_template_data else selected_style}")
                    
                    # Generate PPTX button
                    if st.button("Click to Generate & Download PPTX", use_container_width=True, key="generate_pptx"):
                        with st.spinner(f"Generating PPTX with '{selected_style}' style..."):
                            pptx_stream, pptx_error = create_pptx_with_style( 
                                final_json, 
                                theme_name=selected_style, 
                                template_data=st.session_state.uploaded_template_data 
                            )
                        
                            if pptx_stream:
                                st.download_button(
                                    label="Download PowerPoint File",
                                    data=pptx_stream,
                                    file_name="notescan_presentation.pptx",
                                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                                    use_container_width=True,
                                    key="download_pptx_final" # Added explicit key
                                )
                                st.success("PPTX generated! Click the Download button above.")
                            elif pptx_error:
                                st.error(f"PPTX Error: {pptx_error}")

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
                            use_container_width=True,
                            key="download_docx" # Added explicit key
                        )
                    elif docx_error:
                        st.error(f"DOCX Error: {docx_error}")

                    # --- Markdown Report Download (Conditional) ---
                    st.markdown("#### Markdown Report (.md)")
                    markdown_content, markdown_error = create_markdown_report(final_json) 
                    
                    if markdown_content:
                        st.download_button(
                            label="Download Markdown Report (.md)",
                            data=markdown_content.encode('utf-8'),
                            file_name="notescan_report.md",
                            mime="text/markdown",
                            use_container_width=True,
                            key="download_md" # Added explicit key
                        )
                    elif markdown_error:
                        st.error(f"Markdown Error: {markdown_error}")
            
# ----------------------------------------------------
# 4. FOOTER IMPLEMENTATION 
# ----------------------------------------------------
        st.markdown("---") # Optional separator line
        st.markdown(
            """
            <style>
            .footer {
                padding-top: 20px; 
                padding-bottom: 20px;
                text-align: center;
                font-size: 0.8rem;
                color: #555555; 
            }
            </style>
            <div class="footer">
                Developed by Geetanjally | Powered by Google Gemini & OCR technologies
            </div>
            """, 
            unsafe_allow_html=True
        )


if __name__ == "__main__":
    main()
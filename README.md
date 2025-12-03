# 🚀 NoteScan AI Suite

**NoteScan** is a simple, powerful web tool that converts PDF notes (handwritten or printed) into professional, editable presentation slides and reports using the Google Gemini AI.

-----

## 🌐 Live Demo

Try the app right now:

➡️ **[NoteScan Live Demo](https://pdftotext-7etecv3crigzgo5cwnbvvn.streamlit.app/)** ⬅️


## ✨ Core Features

  * **PDF to Anything:** Convert any PDF into **PowerPoint (.pptx)**, **Word Document (.docx)**, and **Markdown (.md)** report.
  * **Smart AI Extraction:** Uses **Google Gemini** for smart summarization and **OpenCV OCR** for reliable text extraction from complex documents.
  * **Custom Templates:** Upload your own `.pptx` template for instant corporate branding.
  * **Easy Editing:** Edit the content structure live before generating the final files.

-----

## 🛠️ Tech Used

| Component | Purpose |
| :--- | :--- |
| **Streamlit** | Powers the easy-to-use web interface (UI). |
| **Google Gemini** | The main AI engine for data extraction and restructuring. |
| **OpenCV OCR** | Handles text recognition from images and PDFs. |
| **python-pptx/docx** | Generates the final, editable file formats. |

-----

## 💻 Quick Local Setup

1.  **Clone the code:**
    ```bash
    git clone https://github.com/Geetanjally/notescan-suite.git
    cd notescan-suite
    ```
2.  **Install requirements:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Get your Key:**
      * Obtain a **Gemini API Key** from Google AI Studio.
4.  **Run the app:**
    ```bash
    streamlit run main.py
    ```
    (Enter your API key in the sidebar when the app opens.)

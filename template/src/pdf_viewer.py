import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import io

def pdf_viewer(file_path: str, viewer_id: str):
    """
    A Streamlit component to view a PDF file.
    This component reads from and writes to st.session_state.pdf_page_number
    to control the displayed page.

    Args:
        file_path (str): The path to the PDF file.
        viewer_id (str): A unique identifier for this viewer instance's widgets.
    """
    # Ensure the session state for the page number is initialized.
    if 'pdf_page_number' not in st.session_state:
        st.session_state['pdf_page_number'] = 1

    try:
        doc = fitz.open(file_path)
    except Exception as e:
        st.error(f"Failed to open PDF file: {e}")
        return

    num_pages = len(doc)

    col1, col2, col3 = st.columns([2, 8, 2])

    with col1:
        if st.button("⬅️ Previous", key=f"prev_{viewer_id}"):
            if st.session_state.pdf_page_number > 1:
                st.session_state.pdf_page_number -= 1
                st.rerun()

    with col2:
        st.write(f"Page {st.session_state.pdf_page_number} of {num_pages}")

    with col3:
        if st.button("Next ➡️", key=f"next_{viewer_id}"):
            if st.session_state.pdf_page_number < num_pages:
                st.session_state.pdf_page_number += 1
                st.rerun()

    # Page numbers are 1-based for users, 0-based for the library.
    page_num = st.session_state.pdf_page_number - 1
    
    if 0 <= page_num < num_pages:
        page = doc.load_page(page_num)
        pix = page.get_pixmap()
        
        # Convert to PIL Image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # Display image
        st.image(img, use_container_width=True)
    else:
        st.warning("Invalid page number selected.")

    doc.close()

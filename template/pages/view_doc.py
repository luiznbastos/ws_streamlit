import os
import streamlit as st
from src.pdf_viewer import pdf_viewer

st.set_page_config(layout="wide")

st.title("Visualizador de Documentos")

current_dir = os.path.dirname(os.path.abspath(__file__))

pdf_file_path = os.path.join(current_dir, "resol175consolid.pdf")

pdf_viewer(file_path=pdf_file_path, initial_page=1)

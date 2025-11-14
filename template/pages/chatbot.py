import streamlit as st
import requests
import time
import os
from src.chat_manager import get_conversations, get_conversation_messages
from src.sidebar import render_sidebar
from src.settings import settings
from src.pdf_viewer import pdf_viewer
from src.s3_utils import get_s3_loader
from src.conversation_manager import get_conversation_manager

# --- Page Configuration ---
st.set_page_config(page_title="GPT 175", layout="wide")

# Initialize session state for the PDF viewer
if 'show_pdf_viewer' not in st.session_state:
    st.session_state['show_pdf_viewer'] = False
if 'pdf_page_number' not in st.session_state:
    st.session_state['pdf_page_number'] = 1

# Initialize conversation state
if 'conversation_id' not in st.session_state:
    st.session_state['conversation_id'] = None
if 'messages' not in st.session_state:
    st.session_state['messages'] = []
if 'selected_conversation' not in st.session_state:
    st.session_state['selected_conversation'] = None

# Initialize conversation manager
conversation_manager = get_conversation_manager()

# --- Custom Sidebar ---
render_sidebar()

st.sidebar.title("Conversations")

# Custom CSS for the conversation buttons
st.sidebar.markdown("""
<style>
    /* Main container for each conversation item */
    div[data-testid="stHorizontalBlock"] {
        border: 1px solid #e0e0e0;
        border-radius: 6px;
        padding: 6px 10px;
        margin-bottom: 3px; /* Tighter spacing */
        height: 40px; /* Slightly smaller height */
        display: flex;
        align-items: center;
        width: 95%; /* A bit smaller than sidebar */
        box-sizing: border-box;
        background-color: #fafafa;
    }

    /* Target the button containers inside the columns */
    div[data-testid="stHorizontalBlock"] .stButton {
        height: 100%;
        width: 100%;
    }

    /* Style for all buttons inside our custom component */
    div[data-testid="stHorizontalBlock"] .stButton button {
        background-color: transparent;
        border: none;
        padding: 0;
        margin: 0;
        height: 100%;
        width: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    /* Style for the main conversation button (the first one) */
    div[data-testid="stHorizontalBlock"] > div:first-child .stButton button {
        justify-content: flex-start; /* Align text to the left */
        font-weight: 500;
        color: #262730 !important; /* Dark text for better contrast */
        font-size: 0.9em;
    }
    div[data-testid="stHorizontalBlock"] > div:first-child .stButton button:hover {
        color: #FF4B4B !important;
        background-color: #f0f0f0;
    }

    /* Style for the action buttons (rename/delete) */
    div[data-testid="stHorizontalBlock"] > div:not(:first-child) .stButton button {
        font-size: 1.1em; /* Make icons a bit bigger */
        color: #666 !important; /* Darker gray for better visibility */
    }
    div[data-testid="stHorizontalBlock"] > div:not(:first-child) .stButton button:hover {
        color: #262730 !important;
        background-color: #f0f0f0;
    }

    /* Custom style for the source buttons (pill/tag style) */
    .source-btn button {
        background-color: transparent;
        border: 1px solid #ccc; /* Lighter border */
        border-radius: 15px; /* Pill shape */
        padding: 5px 10px;
        color: #333;
        font-weight: 400;
        font-size: 0.9em;
        transition: all 0.2s;
    }
    .source-btn button:hover {
        background-color: #f0f2f6; /* Light gray background on hover */
        border-color: #aaa;
        color: #000;
    }
</style>
""", unsafe_allow_html=True)

# Button to start a new chat with better styling
new_conversation_style = """
<style>
.new-conversation-btn {
    background: linear-gradient(45deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
    border-radius: 12px;
    padding: 16px 20px;
    margin: 8px 0 16px 0;
    width: 100%;
    font-size: 16px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s ease;
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
    text-align: center;
}
.new-conversation-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}
</style>
"""
st.sidebar.markdown(new_conversation_style, unsafe_allow_html=True)

if st.sidebar.button("New Chat", use_container_width=True, type="primary"):
    st.session_state.messages = []
    st.session_state.conversation_id = None
    st.session_state.selected_conversation = None
    st.rerun()

# Display conversation history
conversations = conversation_manager.list_conversations(limit=20)

if conversations:
    st.sidebar.markdown("---")
    
    for conversation in conversations:
        # Create a container for each conversation with custom styling
        with st.sidebar.container():
            # Use columns for layout
            col1, col2 = st.columns([0.8, 0.2])
            
            with col1:
                # Style the conversation button
                is_selected = st.session_state.get('selected_conversation') == conversation["conversation_id"]
                
                # Truncate long titles for better display
                title = conversation['title']
                if len(title) > 20:
                    display_title = title[:17] + "..."
                else:
                    display_title = title
                
                if st.button(
                    f"{display_title}", 
                    key=f"select_{conversation['conversation_id']}", 
                    use_container_width=True,
                    type="primary" if is_selected else "secondary",
                    help=f"{title}" if len(title) > 20 else None
                ):
                    st.session_state.selected_conversation = conversation["conversation_id"]
                    st.session_state.conversation_id = conversation["conversation_id"]
                    # Load and display messages for the selected conversation
                    messages = conversation_manager.load_conversation(conversation["conversation_id"])
                    st.session_state.messages = []
                    for msg in messages:
                        message_data = {"role": msg["role"], "content": msg["content"]}
                        if msg["sources"]:
                            message_data["sources"] = msg["sources"]
                        st.session_state.messages.append(message_data)
                    # To see the change immediately, we need a rerun
                    st.rerun()
            
            with col2:
                # Style the delete button with better visual design
                delete_button_style = """
                <style>
                .delete-btn {
                    background: linear-gradient(45deg, #ff6b6b 0%, #ee5a52 100%);
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 8px 12px;
                    font-size: 14px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    box-shadow: 0 2px 6px rgba(255, 107, 107, 0.3);
                    width: 100%;
                }
                .delete-btn:hover {
                    transform: translateY(-1px);
                    box-shadow: 0 4px 12px rgba(255, 107, 107, 0.4);
                    background: linear-gradient(45deg, #ff5252 0%, #e53935 100%);
                }
                </style>
                """
                st.markdown(delete_button_style, unsafe_allow_html=True)
                
                if st.button(
                    "🗑️", 
                    key=f"delete_{conversation['conversation_id']}", 
                    use_container_width=True,
                    help="Delete this conversation",
                    type="secondary"
                ):
                    try:
                        conversation_manager.delete_conversation(conversation["conversation_id"])
                        st.toast(f"🗑️ Deleted: '{conversation['title']}'")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error deleting conversation: {e}")
        
        # Add some spacing between conversations
        st.sidebar.markdown("")
else:
    st.sidebar.markdown("### 💬 No conversations yet")
    st.sidebar.markdown("Start a new conversation below!")

# --- UI Components ---
st.title("GPT 175")

# --- RAG API Configuration ---
RAG_API_URL = f"{settings.rag_api_base_url.rstrip('/')}/ask"

# --- PDF Configuration ---
# Try to get PDF from S3, fallback to local file
def get_pdf_path():
    """Get PDF file path, downloading from S3 if needed."""
    # Try AWS path first
    aws_path = "/usr/pkg/app/documents/resol175consolid.pdf"
    if os.path.exists(aws_path):
        return aws_path
    
    # Try to download from S3
    s3_loader = get_s3_loader()
    local_path = "/tmp/resol175consolid.pdf"
    if s3_loader.download_file_from_s3("documents/resol175consolid.pdf", local_path):
        return local_path
    
    # Fallback to local development path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, "resol175consolid.pdf")

PDF_FILE_PATH = get_pdf_path()

# Define main_col and an empty placeholder for sidebar_col.
if st.session_state.get('show_pdf_viewer', False):
    main_col, sidebar_col_placeholder = st.columns([2, 1])
else:
    main_col = st.container()
    sidebar_col_placeholder = None

with main_col:
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages from history on app rerun
    for i, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant" and "sources" in message and message["sources"]:
                sources = message["sources"]
                sources_container = st.container()
                with sources_container:
                    st.markdown("---")
                    max_cols = 4
                    cols = st.columns(max_cols)
                    col_idx = 0
                    for j, source in enumerate(sources):
                        doc = source if isinstance(source, dict) else {}
                        meta = doc.get("metadata", {}) if isinstance(doc.get("metadata"), dict) else {}
                        section_id = doc.get("section_id") or meta.get("section_id") or f"Source {j+1}"
                        page_number = doc.get("page_number") or meta.get("page_number")
                        preview = (doc.get("section_text") or meta.get("section_text") or "").strip()
                        if len(preview) > 150:
                            preview = preview[:150] + "..."

                        if page_number and str(page_number).isdigit():
                            with cols[col_idx]:
                                # The st.markdown calls below wrap the button in a div with the
                                # 'source-btn' class, allowing for custom CSS styling.
                                # st.markdown('<div class="source-btn">', unsafe_allow_html=True)
                                if st.button(
                                    f"{section_id}", 
                                    key=f"msg_{i}_source_btn_{j}",
                                    help=f"**Page {page_number}**: {preview}",
                                    use_container_width=True
                                ):
                                    st.session_state.show_pdf_viewer = True
                                    st.session_state.pdf_page_number = int(page_number)
                                    st.rerun()
                                # st.markdown('</div>', unsafe_allow_html=True)
                            col_idx = (col_idx + 1) % max_cols

    # --- Chat Logic ---
    def get_rag_response(prompt: str):
        """
        Function to get a response from the RAG API.
        """
        try:
            response = requests.post(
                RAG_API_URL,
                json={
                    "query": prompt,
                    "top_k": 3,
                    "use_reranking": True,
                },
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            answer_text = data.get("response") or data.get("answer") or ""
            sources = data.get("sources", [])
            return answer_text, sources
        except requests.exceptions.RequestException as e:
            st.error(f"Error connecting to the RAG API: {e}")
            return "Sorry, there was an error with the backend service.", []

    # --- User Interaction ---
    if prompt := st.chat_input("What is up?"):
        # Save user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Create conversation if this is the first message
        if st.session_state.conversation_id is None:
            with st.spinner("Creating conversation..."):
                # Generate title from first query
                title = conversation_manager.generate_conversation_title(prompt)
                # Create conversation
                st.session_state.conversation_id = conversation_manager.create_conversation(title)
        
        # Save user message to database
        conversation_manager.save_message(
            st.session_state.conversation_id, 
            "user", 
            prompt
        )
        
        with st.spinner("Thinking..."):
            assistant_response, sources = get_rag_response(prompt)
            st.session_state.messages.append({
                "role": "assistant",
                "content": assistant_response,
                "sources": sources
            })
            
            # Save assistant response to database
            conversation_manager.save_message(
                st.session_state.conversation_id,
                "assistant", 
                assistant_response,
                sources
            )
            
            st.rerun()

    # Add disclaimer at the bottom of the page
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666; font-size: 0.9em; padding: 10px;'>"
        "O GPT175 pode cometer erros. Considere verificar informações importantes."
        "</div>",
        unsafe_allow_html=True
    )

# --- Right Sidebar for PDF Viewer ---
if st.session_state.get('show_pdf_viewer', False) and sidebar_col_placeholder:
    with sidebar_col_placeholder:
        with st.container():
            st.markdown("### Visualizador de Documentos")
            if st.button("✖️ Fechar"):
                st.session_state.show_pdf_viewer = False
                st.rerun()
            pdf_viewer(
                file_path=PDF_FILE_PATH,
                viewer_id="sidebar_viewer"
            )

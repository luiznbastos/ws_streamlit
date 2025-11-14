import streamlit as st

def render_sidebar():
    """
    Renders a custom sidebar for the application.

    This function hides the default Streamlit page navigation and adds a
    button to navigate back to the main homepage.
    """
    # Hide the default Streamlit navigation
    st.markdown(
        """
        <style>
            [data-testid="stSidebarNav"] {
                display: none;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Add a button to go to the homepage
    if st.sidebar.button("Go to Homepage"):
        st.switch_page("main.py")

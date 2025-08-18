# background.py
"""Background customization for the TCG Deck Analyzer app"""

import streamlit as st
import base64
import os

def add_bg_from_url(url, fixed_position=True):
    """
    Add a background image to the Streamlit app from a URL.
    
    Args:
        url: URL of the background image
        fixed_position: Whether the background should be fixed (true) or scroll with content (false)
    """
    position = "fixed" if fixed_position else "absolute"
    
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("{url}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: {position};
        }}
        
        /* Add a semi-transparent overlay to improve text readability */
        .stApp::before {{
            content: "";
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(255, 255, 255, 0.7);  /* White with 70% opacity */
            z-index: -1;
        }}
        
        /* Make sure content containers have some transparency */
        .stTabs [data-baseweb="tab-panel"] > div {{
            background-color: rgba(255, 255, 255, 0.85);
            padding: 1rem;
            border-radius: 5px;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

def add_bg_from_local(image_file, fixed_position=True):
    """
    Add a background image to the Streamlit app from a local file.
    
    Args:
        image_file: Path to local image file
        fixed_position: Whether the background should be fixed (true) or scroll with content (false)
    """
    position = "fixed" if fixed_position else "absolute"
    
    with open(image_file, "rb") as f:
        img_data = f.read()
        
    b64_encoded = base64.b64encode(img_data).decode()
    
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url(data:image/png;base64,{b64_encoded});
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: {position};
        }}
        
        # /* Add a semi-transparent overlay to improve text readability */
        # .stApp::before {{
        #     content: "";
        #     position: fixed;
        #     top: 0;
        #     left: 0;
        #     width: 100%;
        #     height: 100%;
        #     background-color: rgba(255, 255, 255, 0.7);  /* White with 70% opacity */
        #     z-index: -1;
        # }}
        
        # /* Make sure content containers have some transparency */
        # .stTabs [data-baseweb="tab-panel"] > div {{
        #     background-color: rgba(255, 255, 255, 0.85);
        #     padding: 1rem;
        #     border-radius: 5px;
        # }}
        </style>
        """,
        unsafe_allow_html=True
    )

def add_app_background():
    """
    Add the default background image (background.png) from the repository root.
    """
    # Path to the background image in the repository
    image_path = "assets/background2.png"
    
    # Check if the file exists
    if os.path.exists(image_path):
        add_bg_from_local(image_path)
    else:
        st.warning(f"Background image not found: {image_path}")
        # Apply a fallback background
        st.markdown(
            """
            <style>
            .stApp {
                background-color: #f5f5f5;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

import streamlit as st

st.set_page_config(
    page_title="AI Tax Filing Agent",
    page_icon="💼",
    layout="wide"
)

st.markdown("""
<div style='text-align: center; padding: 2rem;'>
    <h1>🤖 AI Tax Filing Agent</h1>
    <p style='font-size: 1.2rem;'>Choose your workflow from the sidebar →</p>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    ### 📤 Quick Filing
    
    **Perfect for individuals:**
    - Fast 5-step process
    - Upload → Extract → Review → Generate → Download
    - Single return processing
    
    👉 Click **Quick Filing** in the sidebar
    """)

with col2:
    st.markdown("""
    ### 👥 Client Dashboard
    
    **For CAs and professionals:**
    - Manage multiple clients
    - Track filing history
    - Advanced ITR editor
    
    👉 Click **Client Dashboard** in the sidebar
    """)
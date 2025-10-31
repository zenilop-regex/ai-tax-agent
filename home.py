import streamlit as st

# --- Page Configuration ---
st.set_page_config(
    page_title="AI Tax Filing Agent",
    page_icon="💼",
    layout="wide"
)

# --- Header ---
st.markdown(
    """
    <div style='text-align: center; padding: 2rem;'>
        <h1>🤖 AI Tax Filing Agent</h1>
        <p style='font-size: 1.2rem;'>Choose your workflow from the sidebar ⇦</p>
    </div>
    """,
    unsafe_allow_html=True
)

# --- Layout ---
col1, col2 = st.columns(2)

# --- Quick Filing Section ---
with col1:
    st.markdown(
        """
        ### 📤 Quick Filing

        **Perfect for individuals:**
        - Fast 5-step process  
        - Upload → Extract → Review → Generate → Download  
        - Single return processing  

        👉 Click **Quick Filing** in the sidebar
        """
    )

# --- Client Dashboard Section ---
with col2:
    st.markdown(
        """
        ### 👥 Client Dashboard

        **For CAs and professionals:**
        - Manage multiple clients  
        - Track filing history  
        - Advanced ITR editor  

        👉 Click **Client Dashboard** in the sidebar
        """
    )

# --- Footer ---
st.markdown(
    """
    <hr style='margin-top:3rem;'>
    <p style='text-align:center; font-size:0.9rem; color:gray;'>
        Built with ❤️ using Streamlit | Powered by AI Tax Agent
    </p>
    """,
    unsafe_allow_html=True
)

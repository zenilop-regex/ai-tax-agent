# enhanced_main_app.py - FINAL FIXED VERSION
import streamlit as st
import os
import json
import traceback
from datetime import datetime
from io import BytesIO
import base64

# Import modules with error handling
try:
    from extractor import extract_form16
    from ai_agent import get_agent_recommendations, calculate_estimated_tax, validate_form16_data
    from itd_mapper import map_form16_to_itd, apply_overrides, get_placeholders
    from export_pdf import generate_pdf
    from export_excel import generate_excel
    from export_zip import generate_zip
except ImportError as e:
    st.error(f"Import Error: {e}")
    st.info("Make sure all required files are in the same directory")
    st.stop()

# Page config
st.set_page_config(
    page_title="AI Tax Filing Agent",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        text-align: center;
        background: linear-gradient(90deg, #1f4e79, #2980b9);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# App title
st.markdown("""
<div class="main-header">
    <h1>🤖 AI Tax Filing Agent</h1>
    <p>Automated Form-16 Processing & ITR-1 Generation for India</p>
</div>
""", unsafe_allow_html=True)

# Initialize session state
def init_session_state():
    defaults = {
        'current_client': None,
        'form16_data': None,
        'itr_json': None,
        'uploaded_file': None,
        'processing_stage': 'upload',
        'recommendations': None,
        'tax_calculation': None
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# Sidebar
with st.sidebar:
    st.header("📋 Navigation")
    
    stages = [
        ("📤 Upload PDF", "upload"),
        ("🔍 Extract Data", "extract"),
        ("✏️ Review & Edit", "review"),
        ("📊 Generate ITR", "generate"),
        ("📁 File & Export", "file")
    ]
    
    current_stage = st.session_state.processing_stage
    
    for label, stage in stages:
        if stage == current_stage:
            st.markdown(f"**▶️ {label}**")
        else:
            st.markdown(f"⏳ {label}")
    
    st.divider()
    
    if st.button("🔄 Reset Session"):
        for key in list(st.session_state.keys()):
            if key in ['form16_data', 'itr_json', 'uploaded_file', 'recommendations', 'tax_calculation']:
                del st.session_state[key]
        st.session_state.processing_stage = 'upload'
        st.rerun()
    
    # LLM Status
    st.subheader("🤖 AI Status")
    try:
        from extractor import LLMExtractor
        if LLMExtractor.is_server_available():
            st.success("✅ LLM Server Online")
        else:
            st.error("❌ LLM Server Offline")
            st.info("💡 Install LM Studio on localhost:1234")
    except Exception:
        st.warning("⚠️ Could not check LLM status")

# Main content
col1, col2 = st.columns([2, 1])

with col1:
    # Stage 1: Upload
    if st.session_state.processing_stage == 'upload':
        st.header("📤 Step 1: Upload Form-16 PDF")
        st.info("Upload your Form-16 PDF to begin automated tax processing")
        
        uploaded_file = st.file_uploader("Choose Form-16 PDF file", type=['pdf'])
        
        if uploaded_file:
            st.session_state.uploaded_file = uploaded_file
            
            st.write("**File Details:**")
            st.write(f"- Filename: {uploaded_file.name}")
            st.write(f"- Size: {uploaded_file.size / 1024:.1f} KB")
            
            with st.expander("Preview PDF"):
                try:
                    pdf_bytes = uploaded_file.getvalue()
                    base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
                    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="400"></iframe>'
                    st.components.v1.html(pdf_display, height=420)
                except Exception as e:
                    st.error(f"Could not preview PDF: {e}")
            
            if st.button("Process Form-16", type="primary"):
                st.session_state.processing_stage = 'extract'
                st.rerun()
    
    # Stage 2: Extract
    elif st.session_state.processing_stage == 'extract':
        st.header("🔍 Step 2: Extract Data")
        
        if not st.session_state.uploaded_file:
            st.error("No file uploaded")
            if st.button("Back to Upload"):
                st.session_state.processing_stage = 'upload'
                st.rerun()
            st.stop()  # FIXED: Changed from return to st.stop()
        
        if st.session_state.form16_data is None:
            with st.spinner("Extracting data..."):
                try:
                    pdf_bytes = st.session_state.uploaded_file.getvalue()
                    extracted_data = extract_form16(pdf_bytes)
                    st.session_state.form16_data = extracted_data
                except Exception as e:
                    st.error(f"Extraction failed: {e}")
                    st.code(traceback.format_exc())
                    st.stop()  # FIXED: Changed from return to st.stop()
        
        if 'error' in st.session_state.form16_data:
            st.error(f"Error: {st.session_state.form16_data['error']}")
            if st.button("Try Again"):
                st.session_state.form16_data = None
                st.rerun()
        else:
            st.success("✅ Extraction Complete")
            
            data = st.session_state.form16_data
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.subheader("Personal Info")
                st.write(f"**Name**: {data.get('employee_name', 'Not found')}")
                st.write(f"**PAN**: {data.get('pan_of_employee', 'Not found')}")
            
            with col_b:
                st.subheader("Financial Info")
                gross = data.get('gross_salary_paid', 0)
                tds = data.get('total_tds_deducted', 0)
                st.write(f"**Gross Salary**: ₹{gross:,}")
                st.write(f"**TDS**: ₹{tds:,}")
            
            if 'errors' in data.get('_meta', {}):
                errors = data['_meta']['errors']
                if errors:
                    st.warning("Validation Issues:")
                    for error in errors:
                        st.write(f"- {error}")
            
            source_map = data.get('source_map', {})
            if source_map:
                with st.expander("Data Sources"):
                    for field, source in source_map.items():
                        icon = "🔍" if source == "regex" else "🤖"
                        st.write(f"{icon} **{field}**: {source}")
            
            with st.expander("View Raw Data"):
                st.json(st.session_state.form16_data)
            
            if st.button("Continue to Review", type="primary"):
                st.session_state.processing_stage = 'review'
                st.rerun()
    
    # Stage 3: Review
    elif st.session_state.processing_stage == 'review':
        st.header("✏️ Step 3: Review & Edit")
        
        if not st.session_state.form16_data:
            st.error("No data available")
            st.stop()  # FIXED: Changed from return to st.stop()
        
        data = st.session_state.form16_data.copy()
        
        st.info("Review and correct the extracted data")
        
        with st.form("review_form"):
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.subheader("Personal Information")
                data['employee_name'] = st.text_input("Name", data.get('employee_name', ''))
                data['pan_of_employee'] = st.text_input("PAN", data.get('pan_of_employee', ''))
                data['company_name'] = st.text_input("Company", data.get('company_name', ''))
                data['tan'] = st.text_input("TAN", data.get('tan', ''))
            
            with col_b:
                st.subheader("Financial Information")
                data['gross_salary_paid'] = st.number_input(
                    "Gross Salary", 
                    value=float(data.get('gross_salary_paid', 0)),
                    min_value=0.0
                )
                data['total_tds_deducted'] = st.number_input(
                    "Total TDS",
                    value=float(data.get('total_tds_deducted', 0)),
                    min_value=0.0
                )
            
            st.subheader("Quarterly TDS")
            qtds = data.get('quarterly_tds', {})
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                qtds['Q1'] = st.number_input("Q1", value=float(qtds.get('Q1', 0)))
            with col2:
                qtds['Q2'] = st.number_input("Q2", value=float(qtds.get('Q2', 0)))
            with col3:
                qtds['Q3'] = st.number_input("Q3", value=float(qtds.get('Q3', 0)))
            with col4:
                qtds['Q4'] = st.number_input("Q4", value=float(qtds.get('Q4', 0)))
            data['quarterly_tds'] = qtds
            
            st.subheader("Deductions")
            deductions = data.get('deductions', {})
            col1, col2, col3 = st.columns(3)
            with col1:
                deductions['section_80C'] = st.number_input("80C", value=float(deductions.get('section_80C', 0)))
            with col2:
                deductions['section_80D'] = st.number_input("80D", value=float(deductions.get('section_80D', 0)))
            with col3:
                deductions['section_80G'] = st.number_input("80G", value=float(deductions.get('section_80G', 0)))
            data['deductions'] = deductions
            
            submitted = st.form_submit_button("Save & Continue", type="primary")
            
            if submitted:
                validation_issues = validate_form16_data(data)
                
                if validation_issues:
                    st.error("Please fix these issues:")
                    for issue in validation_issues:
                        st.write(f"- {issue['field']}: {issue['issue']}")
                else:
                    st.session_state.form16_data = data
                    st.session_state.processing_stage = 'generate'
                    st.success("Data saved!")
                    st.rerun()
    
    # Stage 4: Generate
    elif st.session_state.processing_stage == 'generate':
        st.header("📊 Step 4: Generate ITR-1")
        
        if not st.session_state.form16_data:
            st.error("No data available")
            st.stop()  # FIXED: Changed from return to st.stop()
        
        if st.session_state.itr_json is None:
            with st.spinner("Generating ITR-1 JSON..."):
                try:
                    st.session_state.itr_json = map_form16_to_itd(st.session_state.form16_data)
                    st.success("ITR-1 generated!")
                except Exception as e:
                    st.error(f"Failed: {e}")
                    st.code(traceback.format_exc())
                    st.stop()  # FIXED: Changed from return to st.stop()
        
        if st.session_state.recommendations is None:
            with st.spinner("Generating recommendations..."):
                try:
                    st.session_state.recommendations = get_agent_recommendations(
                        st.session_state.form16_data, 
                        st.session_state.itr_json
                    )
                except Exception as e:
                    st.warning(f"Could not generate recommendations: {e}")
                    st.session_state.recommendations = {}
        
        if st.session_state.tax_calculation is None:
            try:
                gross = int(st.session_state.form16_data.get('gross_salary_paid', 0))
                deductions = st.session_state.form16_data.get('deductions', {})
                st.session_state.tax_calculation = calculate_estimated_tax(gross, deductions)
            except Exception as e:
                st.warning(f"Could not calculate tax: {e}")
        
        tab1, tab2, tab3 = st.tabs(["ITR Preview", "AI Recommendations", "Tax Analysis"])
        
        with tab1:
            st.subheader("Generated ITR-1 JSON")
            
            try:
                placeholders = get_placeholders(st.session_state.itr_json)
                placeholder_count = len(placeholders)
                total_fields = 20
                filled = max(0, total_fields - placeholder_count)
                completeness = int((filled / total_fields) * 100)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Completeness", f"{completeness}%")
                with col2:
                    st.metric("Fields Filled", filled)
                with col3:
                    st.metric("Placeholders", placeholder_count)
            except Exception as e:
                st.warning(f"Could not analyze: {e}")
            
            st.download_button(
                "Download ITR-1 JSON",
                json.dumps(st.session_state.itr_json, indent=2),
                file_name="ITR1.json",
                mime="application/json"
            )
            
            with st.expander("Preview JSON"):
                st.json(st.session_state.itr_json)
        
        with tab2:
            st.subheader("AI Recommendations")
            
            recommendations = st.session_state.recommendations or {}
            
            missing = recommendations.get('missing_fields', [])
            if missing:
                st.warning(f"Found {len(missing)} missing fields:")
                for field in missing[:5]:
                    st.write(f"- {field.get('field_path', 'Unknown')}")
            
            suggestions = recommendations.get('suggestions', {})
            if suggestions:
                st.info(f"AI found {len(suggestions)} suggestions")
                
                if st.button("Apply All AI Suggestions", type="primary"):
                    st.session_state.itr_json = apply_overrides(st.session_state.itr_json, suggestions)
                    st.success("Suggestions applied!")
                    st.rerun()
            
            advice = recommendations.get('advice', [])
            if advice:
                st.subheader("Tax Advice")
                for tip in advice:
                    st.info(tip)
        
        with tab3:
            st.subheader("Tax Analysis")
            
            if st.session_state.tax_calculation:
                calc = st.session_state.tax_calculation
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Old Regime**")
                    old = calc.get('old_regime', {})
                    st.metric("Tax", f"₹{old.get('total_tax_liability', 0):,}")
                
                with col2:
                    st.write("**New Regime**")
                    new = calc.get('new_regime', {})
                    st.metric("Tax", f"₹{new.get('total_tax_liability', 0):,}")
                
                recommended = calc.get('recommended_regime', 'old')
                savings = abs(calc.get('savings_new_regime', 0))
                
                if recommended == 'new':
                    st.success(f"💡 Choose NEW regime to save ₹{savings:,}")
                else:
                    st.info(f"💡 Stay with OLD regime to save ₹{savings:,}")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("← Back"):
                st.session_state.processing_stage = 'review'
                st.rerun()
        with col2:
            if st.button("Continue →", type="primary"):
                st.session_state.processing_stage = 'file'
                st.rerun()
    
    # Stage 5: Export
    elif st.session_state.processing_stage == 'file':
        st.header("📁 Step 5: Export & File")
        
        if not st.session_state.itr_json:
            st.error("No ITR data available")
            st.stop()  # FIXED: Changed from return to st.stop()
        
        st.success("✅ Your ITR-1 is ready!")
        
        data = st.session_state.form16_data
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            gross = data.get('gross_salary_paid', 0)
            st.metric("Gross Salary", f"₹{gross:,}")
        
        with col2:
            tds = data.get('total_tds_deducted', 0)
            st.metric("TDS Paid", f"₹{tds:,}")
        
        with col3:
            itr_data = st.session_state.itr_json.get('ITR', {}).get('ITR1', {})
            refund = itr_data.get('Refund', {}).get('RefundDue', 0)
            if refund > 0:
                st.metric("Refund", f"₹{refund:,}")
            else:
                st.metric("Balance", "₹0")
        
        st.subheader("Download Options")
        
        json_data = json.dumps(st.session_state.itr_json, indent=2, ensure_ascii=False)
        excel_data = generate_excel(st.session_state.form16_data)
        pdf_data = generate_pdf(st.session_state.form16_data)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.download_button("📄 ITR JSON", json_data, file_name="ITR1.json", mime="application/json")
        
        with col2:
            st.download_button("📊 Excel", excel_data, file_name="Form16.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        
        with col3:
            st.download_button("📑 PDF", pdf_data, file_name="Form16.pdf", mime="application/pdf")
        
        with col4:
            zip_data = generate_zip(json_data.encode('utf-8'), excel_data, pdf_data)
            st.download_button("🗜️ ZIP", zip_data, file_name="Tax_Package.zip", mime="application/zip")
        
        st.subheader("Next Steps")
        
        st.info("""
        **To file your ITR-1:**
        1. Download the ITR JSON file
        2. Visit: https://www.incometax.gov.in
        3. Login and upload JSON
        4. Verify and submit
        
        **Important:** File before July 31st
        """)
        
        if st.button("🔄 Process Another Form-16"):
            for key in ['form16_data', 'itr_json', 'uploaded_file', 'recommendations', 'tax_calculation']:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state.processing_stage = 'upload'
            st.rerun()

# Right column
with col2:
    stage_info = {
        'upload': {'title': 'Upload Form-16', 'tips': ['Ensure PDF is clear', 'File size < 10MB']},
        'extract': {'title': 'AI Extraction', 'tips': ['Regex + LLM processing', 'Auto validation']},
        'review': {'title': 'Review Data', 'tips': ['Check PAN/TAN', 'Verify amounts']},
        'generate': {'title': 'Generate ITR', 'tips': ['Auto calculations', 'Tax optimization']},
        'file': {'title': 'Ready to File', 'tips': ['Upload to portal', 'File before deadline']}
    }
    
    current = stage_info.get(st.session_state.processing_stage, stage_info['upload'])
    
    st.subheader(current['title'])
    st.subheader("💡 Tips")
    for tip in current['tips']:
        st.write(f"• {tip}")
    
    if st.session_state.form16_data or st.session_state.itr_json:
        st.subheader("📊 Progress")
        stages_done = ['upload', 'extract']
        if st.session_state.processing_stage in ['review', 'generate', 'file']:
            stages_done.append('review')
        if st.session_state.processing_stage in ['generate', 'file']:
            stages_done.append('generate')
        if st.session_state.processing_stage == 'file':
            stages_done.append('file')
        
        progress = len(stages_done) / 5
        st.progress(progress)
        st.write(f"{int(progress * 100)}% Complete")
    
    st.subheader("⚙️ Status")
    if st.session_state.uploaded_file:
        st.success("✅ PDF Uploaded")
    if st.session_state.form16_data and 'error' not in st.session_state.form16_data:
        st.success("✅ Data Extracted")
    if st.session_state.itr_json:
        st.success("✅ ITR Generated")

st.divider()
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p><strong>AI Tax Filing Agent v2.4</strong></p>
    <p>Phase 1 MVP • For informational purposes only</p>
</div>
""", unsafe_allow_html=True)
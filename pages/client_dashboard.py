import streamlit as st
import os
import json
import uuid
from datetime import datetime
from io import BytesIO
import base64
import streamlit.components.v1 as components
import shutil
import re

# Import custom modules
from ai_agent import get_agent_recommendations
from itd_mapper import map_form16_to_itd, apply_overrides
from client_utils import load_clients, save_clients, generate_client_id, verify_pan, get_client_by_pan, get_client_by_id
from extractor import extract_form16
from export_pdf import generate_pdf
from export_excel import generate_excel

# ==================== Configuration ====================
st.set_page_config(page_title="AI-Powered Form-16 Client Manager", layout="wide")

DATA_DIR = "clients"
os.makedirs(DATA_DIR, exist_ok=True)

# ==================== Helper Functions ====================

def safe_float(value, default=0.0):
    """Safely convert value to float"""
    try:
        if value is None or value == "":
            return default
        return float(str(value).replace(",", "").strip())
    except Exception:
        return default

def safe_int(value, default=0):
    """Safely convert value to int"""
    try:
        if value is None or value == "":
            return default
        return int(float(str(value).replace(",", "").strip()))
    except Exception:
        return default

def load_client_data(client_id):
    """Load client data from JSON file"""
    try:
        json_path = os.path.join(DATA_DIR, f"{client_id}.json")
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    return data[0]
                elif isinstance(data, dict):
                    return data
        return None
    except Exception as e:
        st.error(f"Error loading client data: {str(e)}")
        return None

def save_client_data(client_data):
    """Save client data to JSON file"""
    try:
        client_id = client_data.get("client_id")
        if not client_id:
            raise ValueError("Client ID is required")
        
        json_path = os.path.join(DATA_DIR, f"{client_id}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(client_data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"Error saving client data: {str(e)}")
        return False

def load_form16_data(client_id):
    """Load Form-16 extracted data"""
    try:
        client_dir = os.path.join(DATA_DIR, client_id)
        json_path = os.path.join(client_dir, "form16_extracted.json")
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None
    except Exception as e:
        st.error(f"Error loading Form-16 data: {str(e)}")
        return None

def save_form16_data(client_id, form16_data):
    """Save Form-16 extracted data"""
    try:
        client_dir = os.path.join(DATA_DIR, client_id)
        os.makedirs(client_dir, exist_ok=True)
        json_path = os.path.join(client_dir, "form16_extracted.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(form16_data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"Error saving Form-16 data: {str(e)}")
        return False

def is_filled_value(v):
    """Check if a value is properly filled"""
    if v is None:
        return False
    if isinstance(v, (int, float)):
        try:
            return int(v) != 0
        except Exception:
            return False
    if isinstance(v, str):
        s = v.strip()
        if s == "":
            return False
        placeholder_patterns = ["REPLACE", "AAAAA0000A", "REPLACE_ACCOUNT", "REPLACE_BANK", "SW00000001"]
        if any(pattern in s.upper() for pattern in placeholder_patterns):
            return False
        if s in {"-"}:
            return False
        return True
    return True

def count_leafs_and_filled(node):
    """Count total and filled leaf nodes"""
    total = 0
    filled = 0
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(v, dict):
                t, f = count_leafs_and_filled(v)
                total += t
                filled += f
            else:
                total += 1
                if is_filled_value(v):
                    filled += 1
    else:
        total = 1
        filled = 1 if is_filled_value(node) else 0
    return total, filled

def approximate_tax(taxable_income):
    """Calculate approximate tax"""
    ti = int(max(0, taxable_income))
    tax = 0
    if ti <= 250000:
        tax = 0
    elif ti <= 500000:
        tax = (ti - 250000) * 0.05
    elif ti <= 1000000:
        tax = (250000 * 0.05) + (ti - 500000) * 0.2
    else:
        tax = (250000 * 0.05) + (500000 * 0.2) + (ti - 1000000) * 0.3
    tax = tax * 1.04
    return int(round(tax))

def hydrate_itd_from_form16(itd_instance, form16):
    """Hydrate ITD JSON with Form-16 data"""
    if not itd_instance:
        return itd_instance
    
    itr_root = itd_instance.setdefault("ITR", {}).setdefault("ITR1", {})
    
    gross = safe_int(form16.get("gross_salary_paid", 0))
    tds_total = safe_int(form16.get("total_tds_deducted", 0))
    deductions = form16.get("deductions", {}) or {}
    sec80c = safe_int(deductions.get("section_80C", 0))
    sec80d = safe_int(deductions.get("section_80D", 0))
    sec80g = safe_int(deductions.get("section_80G", 0))
    company = form16.get("company_name", "") or ""
    tan = form16.get("tan", "") or ""
    assessee = form16.get("employee_name", "") or ""
    pan_emp = form16.get("pan_of_employee", "") or ""
    
    itr1_income = itr_root.setdefault("ITR1_IncomeDeductions", {})
    itr1_income["GrossSalary"] = gross
    itr1_income["IncomeFromSal"] = gross
    itr1_income["NetSalary"] = gross
    
    usr_via = itr1_income.setdefault("UsrDeductUndChapVIA", {})
    deduct_via = itr1_income.setdefault("DeductUndChapVIA", {})
    
    usr_via["Section80C"] = sec80c
    usr_via["Section80D"] = sec80d
    usr_via["Section80G"] = sec80g
    
    deduct_via["Section80C"] = sec80c
    deduct_via["Section80D"] = sec80d
    deduct_via["Section80G"] = sec80g
    
    total_via = sec80c + sec80d + sec80g
    deduct_via["TotalChapVIADeductions"] = total_via
    
    itr1_income["GrossTotIncome"] = gross
    itr1_income["TotalIncome"] = max(0, gross - total_via)
    
    tds_section = itr_root.setdefault("TDSonSalaries", {})
    taxpaid_section = itr_root.setdefault("TaxPaid", {}).setdefault("TaxesPaid", {})
    
    tds_section["TotalTDSonSalaries"] = tds_total
    taxpaid_section["TDS"] = tds_total
    taxpaid_section["TotalTaxesPaid"] = tds_total
    
    tds_list = tds_section.get("TDSonSalary")
    if not isinstance(tds_list, list) or len(tds_list) == 0:
        first = {
            "EmployerOrDeductorOrCollectDetl": {
                "TAN": tan or "REPLACE_WITH_TAN",
                "EmployerOrDeductorOrCollecterName": company or "REPLACE_WITH_EMPLOYER"
            },
            "IncChrgSal": gross,
            "TotalTDSSal": tds_total
        }
        tds_section["TDSonSalary"] = [first]
    else:
        first = tds_list[0]
        ed = first.setdefault("EmployerOrDeductorOrCollectDetl", {})
        ed["TAN"] = tan or ed.get("TAN", "")
        ed["EmployerOrDeductorOrCollecterName"] = company or ed.get("EmployerOrDeductorOrCollecterName", "")
        first["IncChrgSal"] = gross
        first["TotalTDSSal"] = tds_total
        tds_section["TDSonSalary"][0] = first
    
    personal = itr_root.setdefault("PersonalInfo", {})
    if assessee:
        personal["AssesseeName"] = assessee
    if pan_emp:
        personal["PAN"] = pan_emp
    
    return itd_instance

# ==================== Main UI ====================

st.title("🧾 AI-Powered Form-16 Client Manager")

# ==================== Reset Logic ====================
if "current_client" in st.session_state:
    if st.button("🔄 Reset Client Selection"):
        keys_to_clear = ["current_client", "form16_data", "uploaded_pdf", "edit_fields_initialized", "itd_json", "show_upload_after_client_add"]
        for key in keys_to_clear:
            st.session_state.pop(key, None)
        st.success("Client selection reset.")
        st.rerun()

# ==================== Lookup Form ====================
st.markdown("### 🔍 Lookup Existing Client")
with st.form("lookup_form"):
    lookup_name = st.text_input("Client Name (optional)").strip().lower()
    lookup_pan = st.text_input("PAN (optional)").strip().upper()
    lookup_id = st.text_input("Client ID (optional)").strip()
    lookup_submit = st.form_submit_button("Lookup")

if lookup_submit:
    found = False
    try:
        for filename in os.listdir(DATA_DIR):
            if filename.endswith(".json"):
                client_data = load_client_data(filename.replace(".json", ""))
                if not client_data:
                    continue
                
                match_found = (
                    (lookup_pan and client_data.get("pan", "").upper() == lookup_pan) or
                    (lookup_id and client_data.get("client_id", "") == lookup_id) or
                    (lookup_name and lookup_name in client_data.get("name", "").lower())
                )
                
                if match_found:
                    st.session_state["current_client"] = client_data
                    found = True
                    st.success("✅ Client found and loaded.")
                    st.rerun()
                    break
    except Exception as e:
        st.error(f"Error during lookup: {str(e)}")
    
    if not found:
        st.warning("No matching client found.")

# ==================== Add New Client ====================
if "current_client" not in st.session_state:
    st.markdown("### ➕ Add New Client")
    with st.form("add_client_form"):
        name = st.text_input("Client Name").strip()
        pan = st.text_input("PAN (10 characters)").strip().upper()
        year = st.text_input("Assessment Year").strip()
        submitted = st.form_submit_button("Save Client")
        
        if submitted:
            pan_pattern = re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]$')
            if not pan_pattern.match(pan):
                st.error("Invalid PAN format. Must be like ABCDE1234F")
            elif not name or not year:
                st.error("Please fill all required fields.")
            else:
                unique_suffix = str(uuid.uuid4())[:8]
                client_id = f"{name.lower().replace(' ', '')}_{pan.lower()}_{unique_suffix}"
                
                client_data = {
                    "client_id": client_id,
                    "name": name,
                    "pan": pan,
                    "year": year,
                    "created_at": datetime.now().isoformat()
                }
                
                if save_client_data(client_data):
                    st.session_state["current_client"] = client_data
                    st.session_state["show_upload_after_client_add"] = True
                    st.session_state.pop("form16_data", None)
                    st.session_state.pop("uploaded_pdf", None)
                    st.success("✅ Client saved and loaded.")
                    st.rerun()

# ==================== Client Dashboard ====================
if "current_client" in st.session_state:
    client = st.session_state["current_client"]
    if client is None:
        st.error("No client selected or loaded.")
    else:
        client_id = client["client_id"]
        client_dir = os.path.join(DATA_DIR, client_id)
    
    st.markdown("### 👤 Client Dashboard")
    st.json(client)
    
    # ==================== Danger Zone ====================
    st.markdown("### 🗑️ Danger Zone")
    if st.button("🗑️ Delete This Client", type="primary"):
        try:
            if os.path.exists(client_dir):
                shutil.rmtree(client_dir)
            
            json_file_path = os.path.join(DATA_DIR, f"{client_id}.json")
            if os.path.exists(json_file_path):
                os.remove(json_file_path)
            
            keys_to_clear = ["current_client", "form16_data", "uploaded_pdf", "edit_fields_initialized", "itd_json"]
            for key in keys_to_clear:
                st.session_state.pop(key, None)
            
            st.success("✅ Client deleted successfully.")
            st.rerun()
        except Exception as e:
            st.error(f"Error deleting client: {str(e)}")
    
    # ==================== Load Previous Data ====================
    form16_data = load_form16_data(client_id)
    if form16_data:
        st.markdown("### 📄 Previously Extracted Data")
        st.json(form16_data)
        st.session_state["form16_data"] = form16_data
    else:
        st.info("ℹ️ No extracted Form-16 data found for this client.")
    
    # ==================== Upload or Replace Form-16 PDF ====================
    upload_expanded = st.session_state.get("show_upload_after_client_add", False)
    
    with st.expander("📤 Upload or Replace Form-16 PDF", expanded=upload_expanded):
        new_uploaded_file = st.file_uploader("Upload new Form-16 PDF", type=["pdf"], key="pdf_uploader")
        
        if new_uploaded_file:
            st.session_state["uploaded_pdf"] = new_uploaded_file
            st.success(f"📄 File uploaded: {new_uploaded_file.name}")
            
            with st.expander("📄 Preview Uploaded PDF", expanded=False):
                pdf_bytes = new_uploaded_file.getvalue()
                base64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
                pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
                components.html(pdf_display, height=620)
            
            if st.button("🔍 Extract Form-16 Data"):
                os.makedirs(client_dir, exist_ok=True)
                pdf_path = os.path.join(client_dir, "form16.pdf")
                
                with open(pdf_path, "wb") as f:
                    f.write(pdf_bytes)
                
                st.info("🔍 Extracting Form-16 data...")
                try:
                    result = extract_form16(BytesIO(pdf_bytes))
                    if save_form16_data(client_id, result):
                        st.session_state["form16_data"] = result
                        st.session_state["edit_fields_initialized"] = False
                        st.session_state.pop("itd_json", None)
                        st.success("✅ Extraction successful!")
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Extraction failed: {str(e)}")
        
        if "uploaded_pdf" in st.session_state:
            if st.button("🔄 Reset Uploaded File", type="secondary"):
                st.session_state.pop("uploaded_pdf", None)
                st.session_state.pop("form16_data", None)
                st.rerun()
    
    if "show_upload_after_client_add" in st.session_state:
        st.session_state["show_upload_after_client_add"] = False
    
    # ==================== Display Extracted Data ====================
    form16_data = st.session_state.get("form16_data")
    
    if form16_data:
        st.markdown("## 📄 Extracted Form-16 Data")
        st.json(form16_data)
        
        # ==================== Edit Extracted Fields ====================
        with st.expander("✏️ Review and Edit Extracted Fields", expanded=False):
            st.markdown("#### ✅ Top-Level Fields")
            
            company_name = st.text_input("Company Name", value=form16_data.get("company_name", ""))
            employee_name = st.text_input("Employee Name", value=form16_data.get("employee_name", ""))
            pan_of_employer = st.text_input("PAN of Employer", value=form16_data.get("pan_of_employer", ""))
            pan_of_employee = st.text_input("PAN of Employee", value=form16_data.get("pan_of_employee", ""))
            tan = st.text_input("TAN", value=form16_data.get("tan", ""))
            assessment_year = st.text_input("Assessment Year", value=form16_data.get("assessment_year", ""))
            gross_salary = st.number_input("Gross Salary Paid", value=safe_float(form16_data.get("gross_salary_paid", 0)))
            total_tds = st.number_input("Total TDS Deducted", value=safe_float(form16_data.get("total_tds_deducted", 0)))
            
            st.markdown("#### 📆 Quarterly TDS Details")
            qtds = form16_data.get("quarterly_tds", {})
            q1 = st.number_input("Q1 TDS", value=safe_float(qtds.get("Q1", 0)))
            q2 = st.number_input("Q2 TDS", value=safe_float(qtds.get("Q2", 0)))
            q3 = st.number_input("Q3 TDS", value=safe_float(qtds.get("Q3", 0)))
            q4 = st.number_input("Q4 TDS", value=safe_float(qtds.get("Q4", 0)))
            
            st.markdown("#### 💸 Deductions")
            deductions = form16_data.get("deductions", {})
            sec80c = st.number_input("Section 80C", value=safe_float(deductions.get("section_80C", 0)))
            sec80d = st.number_input("Section 80D", value=safe_float(deductions.get("section_80D", 0)))
            sec80g = st.number_input("Section 80G", value=safe_float(deductions.get("section_80G", 0)))
            
            if st.button("✅ Save All Changes"):
                updated_data = {
                    "company_name": company_name,
                    "employee_name": employee_name,
                    "pan_of_employer": pan_of_employer,
                    "pan_of_employee": pan_of_employee,
                    "tan": tan,
                    "assessment_year": assessment_year,
                    "gross_salary_paid": gross_salary,
                    "total_tds_deducted": total_tds,
                    "quarterly_tds": {"Q1": q1, "Q2": q2, "Q3": q3, "Q4": q4},
                    "deductions": {"section_80C": sec80c, "section_80D": sec80d, "section_80G": sec80g}
                }
                
                if save_form16_data(client_id, updated_data):
                    st.session_state["form16_data"] = updated_data
                    st.success("✅ All changes saved.")
                    st.rerun()
        
        # ==================== Download Extracted Files ====================
        st.markdown("### 💾 Download Extracted Files")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.download_button(
                "📥 JSON",
                json.dumps(form16_data, indent=4, ensure_ascii=False),
                file_name="form16_extracted.json",
                mime="application/json"
            )
        with col2:
            st.download_button(
                "📊 Excel",
                generate_excel(form16_data),
                file_name="form16.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        with col3:
            st.download_button(
                "📄 PDF",
                generate_pdf(form16_data),
                file_name="form16_summary.pdf",
                mime="application/pdf"
            )
        
        # ==================== Tax Addict Mode ====================
        st.markdown("### 🧾 Tax Addict Mode – Advanced ITR Editor & Live Preview")
        
        itd_obj = st.session_state.get("itd_json")
        if not itd_obj:
            try:
                itd_obj = map_form16_to_itd(form16_data)
                itd_obj = hydrate_itd_from_form16(itd_obj, form16_data)
                st.session_state["itd_json"] = itd_obj
            except Exception as e:
                st.error(f"Failed to map Form-16 to ITR JSON: {e}")
                itd_obj = None
        
        if itd_obj:
            itr1 = itd_obj.get("ITR", {}).get("ITR1", {})
            total_leafs, filled_leafs = count_leafs_and_filled(itr1)
            readiness_pct = int(round((filled_leafs / total_leafs) * 100)) if total_leafs > 0 else 0
            
            left_col, right_col = st.columns([2, 3])
            
            # ==================== Left: Advanced Editor ====================
            with left_col:
                st.subheader("✏️ Advanced ITR Editor")
                st.write("Fields marked ✅ are filled; ❌ are missing/placeholders.")
                st.markdown(f"**Readiness:** {readiness_pct}%")
                st.progress(min(max(readiness_pct, 0), 100))
                
                def render_leaves_collect(subtree, section_key, counter):
                    changes = {}
                    if not isinstance(subtree, dict):
                        return changes
                    
                    for k in sorted(subtree.keys()):
                        v = subtree[k]
                        path = f"{section_key}.{k}" if section_key else k
                        
                        if isinstance(v, dict):
                            st.markdown(f"**{k}**")
                            child = render_leaves_collect(v, path, counter)
                            changes.update(child)
                        else:
                            status = "✅" if is_filled_value(v) else "❌"
                            label = f"{path}  {status}"
                            
                            counter["count"] += 1
                            safe_key = f"itr_{counter['count']}"
                            
                            if isinstance(v, (int, float)):
                                try:
                                    nv = st.number_input(label, value=float(v), key=safe_key)
                                    if int(nv) != int(v):
                                        changes[path] = int(nv)
                                except Exception:
                                    nv = st.text_input(label, value=str(v), key=safe_key)
                                    if nv != str(v):
                                        changes[path] = nv
                            else:
                                nv = st.text_input(label, value=str(v), key=safe_key)
                                if nv != str(v):
                                    changes[path] = nv
                    return changes
                
                personal_sub = itr1.get("PersonalInfo", {})
                income_sub = itr1.get("ITR1_IncomeDeductions", {})
                
                tds_sub = {}
                if "TDSonSalaries" in itr1:
                    tds_sub["TDSonSalaries"] = itr1.get("TDSonSalaries", {})
                if "TaxPaid" in itr1:
                    tds_sub["TaxPaid"] = itr1.get("TaxPaid", {})
                
                refund_sub = itr1.get("Refund", {})
                verif_sub = itr1.get("Verification", {})
                
                grouped_keys = {"PersonalInfo", "ITR1_IncomeDeductions", "TDSonSalaries", "TaxPaid", "Refund", "Verification"}
                other_sub = {k: v for k, v in itr1.items() if k not in grouped_keys}
                
                section_changes = {}
                counter = {"count": 0}
                
                with st.expander("Personal Info", expanded=False):
                    section_changes.update(render_leaves_collect(personal_sub, "PersonalInfo", counter))
                
                with st.expander("Income & Deductions", expanded=False):
                    section_changes.update(render_leaves_collect(income_sub, "ITR1_IncomeDeductions", counter))
                
                with st.expander("TDS & Taxes Paid", expanded=False):
                    section_changes.update(render_leaves_collect(tds_sub, "", counter))
                
                with st.expander("Refund & Bank Details", expanded=False):
                    section_changes.update(render_leaves_collect(refund_sub, "Refund", counter))
                
                with st.expander("Verification", expanded=False):
                    section_changes.update(render_leaves_collect(verif_sub, "Verification", counter))
                
                if other_sub:
                    with st.expander("Other / Uncategorised", expanded=False):
                        section_changes.update(render_leaves_collect(other_sub, "", counter))
                
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("Apply Section Edits"):
                        if not section_changes:
                            st.info("No changes detected.")
                        else:
                            try:
                                itd_obj = apply_overrides(itd_obj, section_changes)
                                st.session_state["itd_json"] = itd_obj
                                
                                itd_path = os.path.join(client_dir, "itd_json.json")
                                with open(itd_path, "w", encoding="utf-8") as f:
                                    json.dump(itd_obj, f, indent=2, ensure_ascii=False)
                                
                                st.success("✅ Section edits applied and saved.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to apply edits: {e}")
                
                with col_b:
                    if st.button("Apply All & Refresh"):
                        if not section_changes:
                            st.info("No changes detected.")
                        else:
                            try:
                                itd_obj = apply_overrides(itd_obj, section_changes)
                                st.session_state["itd_json"] = itd_obj
                                
                                itd_path = os.path.join(client_dir, "itd_json.json")
                                with open(itd_path, "w", encoding="utf-8") as f:
                                    json.dump(itd_obj, f, indent=2, ensure_ascii=False)
                                
                                st.success("✅ All edits applied and saved.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to apply edits: {e}")
            
            # ==================== Right: Live Preview & Insights ====================
            with right_col:
                st.subheader("📘 Live Preview & Insights")
                current_itd = st.session_state.get("itd_json", itd_obj)
                
                st.progress(min(max(readiness_pct, 0), 100))
                st.markdown(f"**{readiness_pct}%** complete — {filled_leafs}/{total_leafs} fields filled")
                
                pretty = json.dumps(current_itd, indent=2, ensure_ascii=False)
                st.download_button(
                    "⬇️ Download Final ITR JSON",
                    data=pretty.encode("utf-8"),
                    file_name=f"{form16_data.get('employee_name', 'client')}_ITR1.json",
                    mime="application/json"
                )
                
                with st.expander("Preview ITR JSON", expanded=True):
                    st.code(pretty, language="json")
                
                try:
                    itr1_now = current_itd.get("ITR", {}).get("ITR1", {})
                    total_income = itr1_now.get("ITR1_IncomeDeductions", {}).get("TotalIncome", 0) or 0
                    if not total_income:
                        total_income = itr1_now.get("ITR1_IncomeDeductions", {}).get("GrossTotIncome", 0) or 0
                    
                    taxable = int(total_income)
                    estimated_tax = approximate_tax(taxable)
                    tds_paid = itr1_now.get("TDSonSalaries", {}).get("TotalTDSonSalaries", 0) or 0
                    refund_est = int(tds_paid) - int(estimated_tax)
                    
                    col_m1, col_m2 = st.columns(2)
                    with col_m1:
                        st.metric("Estimated Tax (approx)", f"₹{estimated_tax:,}")
                    with col_m2:
                        if refund_est >= 0:
                            st.metric("Estimated Refund (approx)", f"₹{refund_est:,}")
                        else:
                            st.metric("Estimated Tax Payable (approx)", f"₹{abs(refund_est):,}")
                    
                    st.markdown("*Note: Basic approximation using simple slab logic. Not legal or financial advice.*")
                except Exception as e:
                    st.warning(f"Could not compute tax estimate: {e}")
        
        # ==================== AI Agent Assistant ====================
        st.markdown("### 🤖 AI Agent Assistant")
        
        if "itd_json" not in st.session_state:
            try:
                st.session_state["itd_json"] = map_form16_to_itd(form16_data)
                st.session_state["itd_json"] = hydrate_itd_from_form16(st.session_state["itd_json"], form16_data)
            except Exception as e:
                st.error(f"Failed to initialize ITR JSON: {e}")
                st.session_state["itd_json"] = None
        
        if st.session_state.get("itd_json"):
            try:
                agent_data = get_agent_recommendations(form16_data, st.session_state["itd_json"])
            except Exception as e:
                st.error(f"AI Agent failed: {e}")
                agent_data = {"missing_fields": [], "suggestions": {}, "advice": [], "logs": []}
            
            missing_fields = agent_data.get("missing_fields", [])
            if not missing_fields:
                st.info("✅ No critical empty/placeholder fields detected. Your ITR looks close to complete.")
            else:
                st.warning(f"Found {len(missing_fields)} critical empty/placeholder fields.")
                with st.expander("📋 View Missing Fields"):
                    for m in missing_fields:
                        st.markdown(f"- **{m.get('field_path', 'Unknown')}** — {m.get('reason', 'No reason provided')}")
            
            suggestions = agent_data.get("suggestions", {})
            if suggestions:
                st.subheader("💡 AI Suggestions")
                
                suggestion_counter = 0
                for path, data in suggestions.items():
                    if not isinstance(data, dict) or "suggested_value" not in data:
                        continue
                    
                    suggestion_counter += 1
                    col_s1, col_s2, col_s3 = st.columns([3, 2, 1])
                    with col_s1:
                        st.markdown(f"**{path}**")
                    with col_s2:
                        st.markdown(f"_Suggested:_ `{data['suggested_value']}`  \n_Reason:_ {data.get('reason', '')}")
                    with col_s3:
                        if st.button("Apply", key=f"apply_suggestion_{suggestion_counter}"):
                            try:
                                val = data.get("suggested_value")
                                if val is None:
                                    st.warning(f"No valid suggested value for {path}")
                                else:
                                    st.session_state["itd_json"] = apply_overrides(
                                        st.session_state["itd_json"], {path: val}
                                    )
                                    
                                    itd_path = os.path.join(client_dir, "itd_json.json")
                                    with open(itd_path, "w", encoding="utf-8") as f:
                                        json.dump(st.session_state["itd_json"], f, indent=2, ensure_ascii=False)
                                    
                                    st.success(f"✅ Applied suggestion for {path}")
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Failed to apply suggestion: {e}")
                
                if st.button("🔥 Autofill All Missing Fields"):
                    try:
                        overrides = {
                            p: s["suggested_value"]
                            for p, s in suggestions.items()
                            if isinstance(s, dict) and s.get("suggested_value") is not None
                        }
                        
                        if not overrides:
                            st.warning("No valid suggestions found to apply.")
                        else:
                            st.session_state["itd_json"] = apply_overrides(
                                st.session_state["itd_json"], overrides
                            )
                            
                            itd_path = os.path.join(client_dir, "itd_json.json")
                            with open(itd_path, "w", encoding="utf-8") as f:
                                json.dump(st.session_state["itd_json"], f, indent=2, ensure_ascii=False)
                            
                            st.success("✅ All AI agent suggestions applied — preview updated.")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Failed to apply all suggestions: {e}")
            
            advice = agent_data.get("advice", [])
            if advice:
                st.subheader("📢 AI Tax Advice")
                for tip in advice:
                    st.info(f"💡 {tip}")
        
        # ==================== Export Bundle ====================
        st.markdown("### 📦 Save Versioned Export Bundle")
        
        if st.button("💾 Save Export Bundle to Client Folder"):
            try:
                export_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                export_dir = os.path.join(client_dir, "exports", export_time)
                os.makedirs(export_dir, exist_ok=True)
                
                json_export_path = os.path.join(export_dir, "form16_extracted.json")
                with open(json_export_path, "w", encoding="utf-8") as f:
                    json.dump(form16_data, f, indent=4, ensure_ascii=False)
                
                excel_bytes = generate_excel(form16_data)
                excel_export_path = os.path.join(export_dir, "form16.xlsx")
                with open(excel_export_path, "wb") as f:
                    f.write(excel_bytes)
                
                pdf_bytes = generate_pdf(form16_data)
                pdf_export_path = os.path.join(export_dir, "form16_summary.pdf")
                with open(pdf_export_path, "wb") as f:
                    f.write(pdf_bytes)
                
                try:
                    itd_to_save = st.session_state.get("itd_json")
                    if not itd_to_save:
                        itd_to_save = map_form16_to_itd(form16_data)
                        itd_to_save = hydrate_itd_from_form16(itd_to_save, form16_data)
                    
                    if itd_to_save:
                        itd_export_path = os.path.join(export_dir, "itd_json.json")
                        with open(itd_export_path, "w", encoding="utf-8") as f:
                            json.dump(itd_to_save, f, indent=2, ensure_ascii=False)
                        st.write(f"Included ITR JSON in export: `{itd_export_path}`")
                except Exception as e:
                    st.warning(f"Failed to include ITR JSON in export bundle: {e}")
                
                st.success(f"✅ Export bundle saved at: `{export_dir}`")
            except Exception as e:
                st.error(f"Failed to create export bundle: {e}")
        
        # ==================== Export History ====================
        export_root = os.path.join(client_dir, "exports")
        if os.path.exists(export_root):
            export_folders = sorted(os.listdir(export_root), reverse=True)
            if export_folders:
                st.markdown("### 🕐 Export History")
                for idx, folder in enumerate(export_folders):
                    export_path = os.path.join(export_root, folder)
                    st.markdown(f"#### 📁 {folder}")
                    
                    col_h1, col_h2, col_h3, col_h4 = st.columns(4)
                    
                    with col_h1:
                        json_file = os.path.join(export_path, "form16_extracted.json")
                        if os.path.exists(json_file):
                            with open(json_file, "r", encoding="utf-8") as f:
                                json_content = f.read()
                            st.download_button(
                                label="📥 JSON",
                                data=json_content,
                                file_name=f"{folder}_form16.json",
                                mime="application/json",
                                key=f"json_{idx}"
                            )
                    
                    with col_h2:
                        excel_file = os.path.join(export_path, "form16.xlsx")
                        if os.path.exists(excel_file):
                            with open(excel_file, "rb") as f:
                                excel_content = f.read()
                            st.download_button(
                                label="📊 Excel",
                                data=excel_content,
                                file_name=f"{folder}_form16.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key=f"excel_{idx}"
                            )
                    
                    with col_h3:
                        pdf_file = os.path.join(export_path, "form16_summary.pdf")
                        if os.path.exists(pdf_file):
                            with open(pdf_file, "rb") as f:
                                pdf_content = f.read()
                            st.download_button(
                                label="📄 PDF",
                                data=pdf_content,
                                file_name=f"{folder}_form16.pdf",
                                mime="application/pdf",
                                key=f"pdf_{idx}"
                            )
                    
                    with col_h4:
                        itd_file = os.path.join(export_path, "itd_json.json")
                        if os.path.exists(itd_file):
                            with open(itd_file, "r", encoding="utf-8") as f:
                                itd_content = f.read()
                            st.download_button(
                                label="📋 ITR JSON",
                                data=itd_content,
                                file_name=f"{folder}_itd.json",
                                mime="application/json",
                                key=f"itd_{idx}"
                            )
                    
                    st.markdown("---")
            else:
                st.info("No previous exports found.")
        else:
            st.info("No export folder created yet.")
    else:
        st.info("No extracted Form-16 data available yet. Please upload a Form-16 PDF to get started.")

# ==================== Footer ====================
st.markdown("---")
st.markdown("**ReturnPrep AI** - AI-Powered Tax Filing Assistant | Built with ❤️ using Streamlit")
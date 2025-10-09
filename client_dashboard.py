import streamlit as st
import os
import json
import uuid
from datetime import datetime
from io import BytesIO
import base64
import streamlit.components.v1 as components
from ai_agent import get_agent_recommendations
import shutil
import re
from itd_mapper import map_form16_to_itd, apply_overrides, get_placeholders
from client_utils import (
    load_clients,
    save_clients,
    generate_client_id,
    verify_pan,
    get_client_by_pan,
    get_client_by_id
)
from extractor import extract_form16
from export_pdf import generate_pdf
from export_excel import generate_excel

st.set_page_config(page_title="AI-Powered Form-16 Client Manager", layout="wide")

DATA_DIR = "clients"
os.makedirs(DATA_DIR, exist_ok=True)

st.title("🧾 AI-Powered Form-16 Client Manager")

# ========================== Reset Logic ==========================
if "current_client" in st.session_state and st.button("🔁 Reset Client Selection"):
    del st.session_state["current_client"]
    st.success("Client selection reset.")
    st.rerun()

# ========================== Lookup Form ==========================
st.markdown("### 🔍 Lookup Existing Client")
with st.form("lookup_form"):
    lookup_name = st.text_input("Client Name (optional)").strip().lower()
    lookup_pan = st.text_input("PAN (optional)").strip().upper()
    lookup_id = st.text_input("Client ID (optional)").strip()
    lookup_submit = st.form_submit_button("Lookup")

if lookup_submit:
    found = False
    for filename in os.listdir(DATA_DIR):
        if filename.endswith(".json"):
            with open(os.path.join(DATA_DIR, filename), "r") as f:
                try:
                    raw_data = json.load(f)
                    if isinstance(raw_data, list) and len(raw_data) > 0 and isinstance(raw_data[0], dict):
                        client_data = raw_data[0]
                    elif isinstance(raw_data, dict):
                        client_data = raw_data
                    else:
                        st.warning(f"Skipping malformed file: {filename}")
                        st.warning(f"Could not parse JSON file: {filename}")
                        continue
                except json.JSONDecodeError:
                    continue

                match_found = (
                    (lookup_pan and client_data.get("pan", "").upper() == lookup_pan) or
                    (lookup_id and client_data.get("client_id", "") == lookup_id) or
                    (lookup_name and lookup_name in client_data.get("name", "").lower())
                )

                if match_found:
                    st.session_state["current_client"] = client_data
                    found = True
                    st.success("Client found and loaded.")
                    st.rerun()

    if not found:
        st.warning("No matching client found.")

# ======================== Add New Client ==========================
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
                st.session_state["current_client"] = client_data
                st.session_state["show_upload_after_client_add"] = True

                file_path = os.path.join(DATA_DIR, f"{client_id}.json")
                with open(file_path, "w") as f:
                    json.dump(client_data, f, indent=4)
                st.session_state["form16_data"] = None
                st.session_state["uploaded_pdf"] = None
                st.success("Client saved and loaded.")
                st.rerun()

# ======================= Client Dashboard =======================
if "current_client" in st.session_state:
    client = st.session_state["current_client"]
    client_dir = os.path.join(DATA_DIR, client["client_id"])
    json_path = os.path.join(client_dir, "form16_extracted.json")

    st.markdown("### 👤 Client Dashboard")
    st.json(client)
    st.markdown("### 🗑 Danger Zone")
    if st.button("🗑 Delete This Client", type="primary"):
        try:
            if os.path.exists(client_dir):
                shutil.rmtree(client_dir)
            json_file_path = os.path.join(DATA_DIR, f"{client['client_id']}.json")
            if os.path.exists(json_file_path):
                os.remove(json_file_path)

            st.success("Client deleted successfully.")
            for key in ["current_client", "form16_data", "uploaded_pdf", "edit_fields_initialized", "itd_json"]:
                st.session_state.pop(key, None)
            st.rerun()

        except Exception as e:
            st.error(f"Error deleting client: {str(e)}")

    # Load previous extracted data if available
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            extracted_data = json.load(f)
        st.markdown("### 📄 Previously Extracted Data")
        st.json(extracted_data)
        st.session_state["form16_data"] = extracted_data
    else:
        st.info("ℹ️ No extracted Form-16 data found for this client.")

# Upload or Replace Form-16 PDF
if "show_upload_after_client_add" in st.session_state and st.session_state["show_upload_after_client_add"]:
    with st.expander("📤 Upload or Replace Form-16 PDF", expanded=True):
        new_uploaded_file = st.file_uploader("Upload new Form-16 PDF", type=["pdf"])
        if new_uploaded_file:
            st.session_state["uploaded_pdf"] = new_uploaded_file

    uploaded_pdf = st.session_state.get("uploaded_pdf")
    if uploaded_pdf:
        with st.expander("📄 Preview Uploaded PDF", expanded=False):
            pdf_bytes = uploaded_pdf.getvalue()
            base64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
            pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
            st.components.v1.html(pdf_display, height=620)
    st.session_state["show_upload_after_client_add"] = False

else:
    with st.expander("📤 Upload or Replace Form-16 PDF"):
        new_uploaded_file = st.file_uploader("Upload new Form-16 PDF", type=["pdf"])
        if new_uploaded_file:
            st.session_state["uploaded_pdf"] = new_uploaded_file
            st.success(f"📄 File uploaded: {new_uploaded_file.name}")

        if "uploaded_pdf" in st.session_state:
            if st.button("🔄 Reset Uploaded File", type="secondary"):
                del st.session_state["uploaded_pdf"]
                if "form16_data" in st.session_state:
                    del st.session_state["form16_data"]
                st.rerun()

            if new_uploaded_file:
                with st.expander("📄 Preview Uploaded PDF", expanded=False):
                    pdf_bytes = new_uploaded_file.getvalue()
                    base64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
                    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
                    st.components.v1.html(pdf_display, height=620)

        if "current_client" in st.session_state and new_uploaded_file is not None:
            client = st.session_state["current_client"]
            client_dir = os.path.join(DATA_DIR, client["client_id"])
            json_path = os.path.join(client_dir, "form16_extracted.json")

            os.makedirs(client_dir, exist_ok=True)
            pdf_path = os.path.join(client_dir, "form16.pdf")
            pdf_content = new_uploaded_file.getvalue()

            with open(pdf_path, "wb") as f:
                f.write(pdf_content)

            st.info("🔍 Extracting new Form-16 data...")
            try:
                result = extract_form16(BytesIO(pdf_content))
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(result, f, indent=4, ensure_ascii=False)
                st.session_state["form16_data"] = result
                st.success("✅ Extraction & replacement successful.")
                st.session_state["edit_fields_initialized"] = False
            except Exception as e:
                st.error(f"❌ Extraction failed: {str(e)}")

# Load form16_data
form16_data = None
if "current_client" in st.session_state:
    client = st.session_state["current_client"]
    client_dir = os.path.join(DATA_DIR, client["client_id"])
    json_path = os.path.join(client_dir, "form16_extracted.json")

    if "form16_data" in st.session_state:
        form16_data = st.session_state["form16_data"]
    elif os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            form16_data = json.load(f)

# Display Extracted Data and editable review (unchanged)
if form16_data:
    st.markdown("## 📄 Extracted Form-16 Data")
    st.json(form16_data)
    st.session_state["form16_data"] = form16_data

    with st.expander("✏️ Review and Edit Extracted Fields", expanded=False):
        if "form16_data" in st.session_state and not st.session_state.get("edit_fields_initialized"):
            data = st.session_state["form16_data"]

            st.session_state["edit_fields"] = {
                "company_name": data.get("company_name", ""),
                "employee_name": data.get("employee_name", ""),
                "pan_of_employer": data.get("pan_of_employer", ""),
                "pan_of_employee": data.get("pan_of_employee", ""),
                "tan": data.get("tan", ""),
                "assessment_year": data.get("assessment_year", ""),
                "gross_salary_paid": data.get("gross_salary_paid", 0.0),
                "total_tds_deducted": data.get("total_tds_deducted", 0.0),
                "quarterly_tds": data.get("quarterly_tds", {"Q1": 0.0, "Q2": 0.0, "Q3": 0.0, "Q4": 0.0}),
                "deductions": data.get("deductions", {"section_80C": 0.0, "section_80D": 0.0, "section_80G": 0.0}),
            }
            st.session_state["edit_fields_initialized"] = True

        def get_val(d, k, default=""):
            return d.get(k, default)

        data = form16_data

        st.markdown("#### ✅ Top-Level Fields")
        data['company_name'] = st.text_input("Company Name", get_val(data, "company_name"))
        data['employee_name'] = st.text_input("Employee Name", get_val(data, "employee_name"))
        data['pan_of_employer'] = st.text_input("PAN of Employer", get_val(data, "pan_of_employer"))
        data['pan_of_employee'] = st.text_input("PAN of Employee", get_val(data, "pan_of_employee"))
        data['tan'] = st.text_input("TAN", get_val(data, "tan"))
        data['assessment_year'] = st.text_input("Assessment Year", get_val(data, "assessment_year"))
        data['gross_salary_paid'] = st.number_input("Gross Salary Paid", value=float(get_val(data, "gross_salary_paid", 0)))
        data['total_tds_deducted'] = st.number_input("Total TDS Deducted", value=float(get_val(data, "total_tds_deducted", 0)))

        st.markdown("#### 📆 Quarterly TDS Details")
        if "quarterly_tds" not in data:
            data["quarterly_tds"] = {}
        qtds = data["quarterly_tds"]
        qtds["Q1"] = st.number_input("Q1 TDS", value=float(qtds.get("Q1", 0)))
        qtds["Q2"] = st.number_input("Q2 TDS", value=float(qtds.get("Q2", 0)))
        qtds["Q3"] = st.number_input("Q3 TDS", value=float(qtds.get("Q3", 0)))
        qtds["Q4"] = st.number_input("Q4 TDS", value=float(qtds.get("Q4", 0)))
        data["quarterly_tds"] = qtds

        st.markdown("#### 💸 Deductions")
        if "deductions" not in data:
            data["deductions"] = {}
        deductions = data["deductions"]
        deductions["section_80C"] = st.number_input("Section 80C", value=float(deductions.get("section_80C", 0)))
        deductions["section_80D"] = st.number_input("Section 80D", value=float(deductions.get("section_80D", 0)))
        deductions["section_80G"] = st.number_input("Section 80G", value=float(deductions.get("section_80G", 0)))
        data["deductions"] = deductions

        if st.button("✅ Save All Changes"):
            st.session_state["form16_data"] = data
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            st.success("✅ All changes saved to file.")
            st.rerun()

    st.markdown("### 💾 Download Extracted Files")
    st.download_button("📥 JSON", json.dumps(form16_data, indent=4), file_name="form16_extracted.json", mime="application/json")
    st.download_button("📊 Excel", generate_excel(form16_data), file_name="form16.xlsx")
    st.download_button("📄 PDF", generate_pdf(form16_data), file_name="form16_summary.pdf")

    # -------------------- Tax Addict Mode (sectioned advanced editor) --------------------
    st.markdown("### 🧾 Tax Addict Mode — Sectioned Advanced Editor & Live Preview")

    # Prefer edited JSON from session first, else build from form16
    itd_obj = st.session_state.get("itd_json")
    if not itd_obj:
        try:
            itd_obj = map_form16_to_itd(form16_data)
        except Exception as e:
            st.error(f"Failed to map Form-16 to ITR JSON: {e}")
            itd_obj = None

    def hydrate_itd_from_form16(itd_instance, form16):
        if not itd_instance:
            return itd_instance
        itr_root = itd_instance.setdefault("ITR", {}).setdefault("ITR1", {})
        def safe_int(x):
            try:
                if x is None or x == "":
                    return 0
                return int(float(str(x).replace(",", "").strip()))
            except Exception:
                return 0
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
        tds_section = itr_root.setdefault("TDSonSalaries", {})
        taxpaid_section = itr_root.setdefault("TaxPaid", {}).setdefault("TaxesPaid", {})
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
        total_via = sum(int(v) for v in [deduct_via.get("Section80C",0), deduct_via.get("Section80D",0), deduct_via.get("Section80G",0)] if isinstance(v, (int,float)))
        deduct_via["TotalChapVIADeductions"] = total_via
        itr1_income["GrossTotIncome"] = gross
        itr1_income["TotalIncome"] = max(0, gross - total_via)
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
            ed["TAN"] = tan or ed.get("TAN", ed.get("Tan",""))
            ed["EmployerOrDeductorOrCollecterName"] = company or ed.get("EmployerOrDeductorOrCollecterName", ed.get("Name",""))
            first["IncChrgSal"] = gross
            first["TotalTDSSal"] = tds_total
            tds_section["TDSonSalary"][0] = first
        personal = itr_root.setdefault("PersonalInfo", {})
        if assessee:
            personal["AssesseeName"] = assessee
        if pan_emp:
            personal["PAN"] = pan_emp
        return itd_instance

    def is_filled_value(v):
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
            if s.upper().startswith("REPLACE"):
                return False
            if s in {"-", "AAAAA0000A", "REPLACE_ACCOUNT", "REPLACE_BANK", "SW00000001"}:
                return False
            return True
        return True

    def count_leafs_and_filled(node):
        total = 0
        filled = 0
        if isinstance(node, dict):
            for k,v in node.items():
                if isinstance(v, dict):
                    t,f = count_leafs_and_filled(v)
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

    # hydrate the chosen itd_obj (prefer session-saved)
    if itd_obj:
        itd_obj = hydrate_itd_from_form16(itd_obj, form16_data)

        # readiness score calculation from the hydrated object
        itr1 = itd_obj.get("ITR", {}).get("ITR1", {})
        total_leafs, filled_leafs = count_leafs_and_filled(itr1)
        readiness_pct = int(round((filled_leafs / total_leafs) * 100)) if total_leafs > 0 else 0

        # single row layout: left advanced editor sections, right preview + insights
        left_col, right_col = st.columns([2, 3])

        # Left: Sectioned Advanced Editor
        with left_col:
            st.subheader("✍️ Advanced ITR Editor (sectioned)")
            st.write("Fields marked ✅ are filled; ❌ are missing/placeholders. Edit any value and click **Apply section edits** or **Apply all edits** to save.")
            # show progress small
            st.markdown(f"**Readiness:** {readiness_pct}%")
            st.progress(min(max(readiness_pct, 0), 100))

            # Helper to render leaves of a subtree and collect changes
            def render_leaves_collect(subtree, section_key):
                changes = {}
                if not isinstance(subtree, dict):
                    return changes
                for k in sorted(subtree.keys()):
                    v = subtree[k]
                    path = f"{section_key}.{k}" if section_key else k
                    if isinstance(v, dict):
                        st.markdown(f"**{k}**")
                        child = render_leaves_collect(v, path)
                        changes.update(child)
                    else:
                        status = "✅" if is_filled_value(v) else "❌"
                        label = f"{path}  {status}"
                        safe_key = f"sec_{path}".replace(".", "_").replace(" ", "_")
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

            # Build section subtrees (use shallow picks)
            personal_sub = itr1.get("PersonalInfo", {})
            income_sub = itr1.get("ITR1_IncomeDeductions", {})
            tds_sub = {}
            if "TDSonSalaries" in itr1:
                tds_sub["TDSonSalaries"] = itr1.get("TDSonSalaries", {})
            if "TaxPaid" in itr1:
                tds_sub["TaxPaid"] = itr1.get("TaxPaid", {})
            refund_sub = itr1.get("Refund", {})
            verif_sub = itr1.get("Verification", {})

            # Other keys not in above groups
            grouped_keys = {"PersonalInfo", "ITR1_IncomeDeductions", "TDSonSalaries", "TaxPaid", "Refund", "Verification"}
            other_sub = {}
            for k,v in itr1.items():
                if k not in grouped_keys:
                    other_sub[k] = v

            # Section expanders: personal, income, tds, refund, verification, other
            section_changes = {}
            with st.expander("Personal Info", expanded=False):
                section_changes.update(render_leaves_collect(personal_sub, "PersonalInfo"))

            with st.expander("Income & Deductions", expanded=False):
                section_changes.update(render_leaves_collect(income_sub, "ITR1_IncomeDeductions"))

            with st.expander("TDS & Taxes Paid", expanded=False):
                section_changes.update(render_leaves_collect(tds_sub, ""))  # tds_sub already contains top-level keys

            with st.expander("Refund & Bank Details", expanded=False):
                section_changes.update(render_leaves_collect(refund_sub, "Refund"))

            with st.expander("Verification", expanded=False):
                section_changes.update(render_leaves_collect(verif_sub, "Verification"))

            if other_sub:
                with st.expander("Other / Uncategorised", expanded=False):
                    section_changes.update(render_leaves_collect(other_sub, ""))

            # Buttons: apply section edits (apply whatever collected)
            c1, c2 = st.columns([1,1])
            with c1:
                if st.button("Apply section edits"):
                    if not section_changes:
                        st.info("No changes detected in the sections.")
                    else:
                        try:
                            itd_obj = apply_overrides(itd_obj, section_changes)
                            st.session_state["itd_json"] = itd_obj
                            os.makedirs(client_dir, exist_ok=True)
                            itd_path = os.path.join(client_dir, "itd_json.json")
                            with open(itd_path, "w", encoding="utf-8") as f:
                                json.dump(itd_obj, f, indent=2, ensure_ascii=False)
                            st.success(f"Section edits applied and saved to `{itd_path}`.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to apply section edits: {e}")
            with c2:
                if st.button("Apply all edits (save and refresh)"):
                    # use same collected edits: if none, inform user
                    if not section_changes:
                        st.info("No changes detected.")
                    else:
                        try:
                            itd_obj = apply_overrides(itd_obj, section_changes)
                            st.session_state["itd_json"] = itd_obj
                            os.makedirs(client_dir, exist_ok=True)
                            itd_path = os.path.join(client_dir, "itd_json.json")
                            with open(itd_path, "w", encoding="utf-8") as f:
                                json.dump(itd_obj, f, indent=2, ensure_ascii=False)
                            st.success(f"All edits applied and saved to `{itd_path}`.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to apply edits: {e}")

        # Right: Live Preview & Insights
        with right_col:
            st.subheader("📘 Live Preview & Insights")
            current_itd = st.session_state.get("itd_json", itd_obj)
            pretty = json.dumps(current_itd, indent=2, ensure_ascii=False)

            # show progress bar and textual status
            st.progress(min(max(readiness_pct, 0), 100))
            st.markdown(f"**{readiness_pct}%** complete — {filled_leafs}/{total_leafs} fields filled")

            st.download_button("⬇️ Download final ITR JSON", data=pretty.encode("utf-8"), file_name=f"{form16_data.get('employee_name','client')}_ITR1.json", mime="application/json")
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
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Estimated Tax (approx)", f"₹{estimated_tax:,}")
                with col2:
                    if refund_est >= 0:
                        st.metric("Estimated Refund (approx)", f"₹{refund_est:,}")
                    else:
                        st.metric("Estimated Tax Payable (approx)", f"₹{abs(refund_est):,}")

                st.markdown("*Note: This is a basic approximation using simple slab logic for quick insight. Not legal or financial advice.*")
            except Exception as e:
                st.warning(f"Could not compute quick tax estimate: {e}")

        # ==================== AI Agent Panel ====================
        from ai_agent import get_agent_recommendations
        from itd_mapper import apply_overrides  # ensure apply_overrides is from itd_mapper

        st.markdown("### 🤖 AI Agent Assistant")

        # Always work with the latest ITR JSON in session
        if "itd_json" not in st.session_state:
            st.session_state["itd_json"] = itd_obj

        try:
            agent_data = get_agent_recommendations(form16_data, st.session_state["itd_json"])
        except Exception as e:
            st.error(f"AI Agent failed: {e}")
            agent_data = {"missing_fields": [], "suggestions": {}, "advice": [], "logs": []}

        # ---- Missing Fields ----
        if not agent_data.get("missing_fields"):
            st.info("✅ No critical empty/placeholder fields detected. Your ITR looks close to complete.")
        else:
            st.warning(f"Found {len(agent_data['missing_fields'])} critical empty/placeholder fields.")
            with st.expander("📋 View Missing Fields"):
                for m in agent_data["missing_fields"]:
                    st.markdown(f"- **{m['field_path']}** — {m['reason']}")

        # ---- Suggestions List ----
        suggestions = agent_data.get("suggestions", {})
        if suggestions:
            st.subheader("💡 AI Suggestions")
            for path, data in suggestions.items():
                if not isinstance(data, dict) or "suggested_value" not in data:
                    continue  # skip invalid entries

                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.markdown(f"**{path}**")
                with col2:
                    st.markdown(f"_Suggested:_ `{data['suggested_value']}`  \n_reason:_ {data.get('reason','')}")
                with col3:
                    if st.button("Apply", key=f"apply_{path}"):
                        try:
                            val = data.get("suggested_value")
                            if val is None:
                                st.warning(f"No valid suggested value for {path}")
                            else:
                                st.session_state["itd_json"] = apply_overrides(
                                    st.session_state["itd_json"], {path: val}
                                )
                                # Save to file
                                os.makedirs(client_dir, exist_ok=True)
                                itd_path = os.path.join(client_dir, "itd_json.json")
                                with open(itd_path, "w", encoding="utf-8") as f:
                                    json.dump(st.session_state["itd_json"], f, indent=2, ensure_ascii=False)
                                st.success(f"✅ Applied suggestion for {path}")
                                st.rerun()
                        except Exception as e:
                            st.error(f"Failed to apply suggestion: {e}")

            # ---- Autofill All Button ----
            if st.button("📥 Autofill All Missing Fields"):
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
                        # Save to file
                        os.makedirs(client_dir, exist_ok=True)
                        itd_path = os.path.join(client_dir, "itd_json.json")
                        with open(itd_path, "w", encoding="utf-8") as f:
                            json.dump(st.session_state["itd_json"], f, indent=2, ensure_ascii=False)
                        st.success("✅ All AI agent suggestions applied — preview updated.")
                        st.rerun()
                except Exception as e:
                    st.error(f"Failed to apply all suggestions: {e}")

        # ---- Advice Section ----
        if agent_data.get("advice"):
            st.subheader("📢 AI Tax Advice")
            for tip in agent_data["advice"]:
                st.info(f"💡 {tip}")

        # ---- Live Preview ----
        st.subheader("📄 Live ITR JSON Preview")
        st.json(st.session_state["itd_json"])


    # Export bundle area (unchanged)
    if form16_data:
        st.markdown("### 📦 Save Versioned Export Bundle")
        if st.button("💾 Save Export Bundle to Client Folder"):
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
                    try:
                        itd_to_save = map_form16_to_itd(form16_data)
                        itd_to_save = hydrate_itd_from_form16(itd_to_save, form16_data)
                    except Exception as e_map:
                        itd_to_save = None
                        st.warning(f"Could not generate ITR JSON for export bundle: {e_map}")
                if itd_to_save:
                    itd_export_path = os.path.join(export_dir, "itd_json.json")
                    with open(itd_export_path, "w", encoding="utf-8") as f:
                        json.dump(itd_to_save, f, indent=2, ensure_ascii=False)
                    st.write(f"Included ITR JSON in export: `{itd_export_path}`")
            except Exception as e:
                st.warning(f"Failed to include ITR JSON in export bundle: {e}")
            st.success(f"✅ Export bundle saved at: `{export_dir}`")

            # show export history (unchanged)
            export_root = os.path.join(client_dir, "exports")
            if os.path.exists(export_root):
                export_folders = sorted(os.listdir(export_root), reverse=True)
                if export_folders:
                    st.markdown("### 🕓 Export History")
                    for folder in export_folders:
                        export_path = os.path.join(export_root, folder)
                        st.markdown(f"#### 📁 {folder}")
                        json_file = os.path.join(export_path, "form16_extracted.json")
                        if os.path.exists(json_file):
                            with open(json_file, "r", encoding="utf-8") as f:
                                json_content = f.read()
                            st.download_button(label="📥 JSON", data=json_content, file_name=f"{folder}_form16.json", mime="application/json")
                        excel_file = os.path.join(export_path, "form16.xlsx")
                        if os.path.exists(excel_file):
                            with open(excel_file, "rb") as f:
                                st.download_button(label="📊 Excel", data=f, file_name=f"{folder}_form16.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                        pdf_file = os.path.join(export_path, "form16_summary.pdf")
                        if os.path.exists(pdf_file):
                            with open(pdf_file, "rb") as f:
                                st.download_button(label="📄 PDF", data=f, file_name=f"{folder}_form16.pdf", mime="application/pdf")
                        st.markdown("---")
                else:
                    st.info("No previous exports found.")
            else:
                st.info("No export folder created yet.")
else:
    st.info("No extracted Form-16 data available yet.")

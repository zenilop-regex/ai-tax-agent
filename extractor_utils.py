import re
import json
import logging

LLM_ENDPOINT = "http://localhost:1234/v1/completions"
HEADERS = {
    "Content-Type": "application/json"
}

def extract_json_block(text: str) -> dict:
    """
    Attempts to extract a valid JSON dict from LLM output.
    Handles code-wrapped responses, partial JSON, and fallback regex patching.
    """
    try:
        # Try direct JSON block extraction
        match = re.search(r"\{[\s\S]*?\}", text)
        if match:
            json_str = match.group(0)
        else:
            # If no JSON block, fall back to known key-value extraction
            logging.warning("🧠 No JSON block found, falling back to regex-based patching")
            return extract_known_fields(text)

        # Clean and sanitize
        json_str = (
            json_str
            .replace("“", '"').replace("”", '"')
            .replace("‘", "'").replace("’", "'")
            .replace("'", '"').replace("`", '"')
            .replace(",}", "}").replace(",]", "]")
        )

        # Balance unclosed braces
        open_braces = json_str.count("{")
        close_braces = json_str.count("}")
        if open_braces > close_braces:
            json_str += "}" * (open_braces - close_braces)

        return json.loads(json_str)

    except json.JSONDecodeError as e:
        logging.error("🧠 JSON decode failed:\n%s\nSanitized:\n%s", e, json_str)
        return {}
    except Exception as e:
        logging.error("🧠 Unexpected error in JSON extraction:\n%s", e)
        return {}

def extract_known_fields(text: str) -> dict:
    """
    General-purpose regex fallback for extracting structured fields
    from Form-16 style documents if LLM response is unusable.
    """
    extracted = {}

    # Normalize text
    text = text.replace("Rs.", "Rs").replace("Amount (Rs)", "Amount")
    text = re.sub(r"\s+", " ", text)

    # General patterns
    fallback_patterns = {
        "tan": r"TAN\s*(?:of\s*Employer)?[:\-]?\s*([A-Z]{4}[0-9]{5}[A-Z]?)",
        "gross_salary_paid": r"Gross\s+Salary\s+Paid\s*[:\-]?\s*[\u20B9]?\s*([\d,]+)",
        "total_tds_deducted": r"Total\s+TDS\s+Deducted\s*[:\-]?\s*[\u20B9]?\s*([\d,]+)",
        "total_tds_deposited": r"Total\s+TDS\s+Deposited\s*[:\-]?\s*[\u20B9]?\s*([\d,]+)",
        "pan_of_employer": r"Employer\s+PAN\s*[:\-]?\s*([A-Z]{5}[0-9]{4}[A-Z])",
        "pan_of_employee": r"Employee\s+PAN\s*[:\-]?\s*([A-Z]{5}[0-9]{4}[A-Z])",
        "company_name": r"Employer\s+Name\s*[:\-]?\s*([A-Z].*?)\s+Employer\s+PAN",
        "employee_name": r"Employee\s+Name\s*[:\-]?\s*([A-Z].*?)\s+Employee\s+PAN",
        "assessment_year": r"Assessment\s+Year\s*[:\-]?\s*([0-9]{4}-[0-9]{2})"
    }

    for key, pattern in fallback_patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            val = match.group(1).strip().replace(",", "")
            extracted[key] = int(val) if val.isdigit() else val

    # Quarterly TDS (Q1–Q4)
    quarterly = {}
    for q in ["Q1", "Q2", "Q3", "Q4"]:
        match = re.search(rf"{q}\s*[:\-]?\s*[\u20B9]?\s*([\d,]+)", text)
        if match:
            try:
                quarterly[q] = int(match.group(1).replace(",", ""))
            except ValueError:
                continue
    if quarterly:
        extracted["quarterly_tds"] = quarterly

    # Deductions (80C, 80D, 80G)
    deductions = {}
    for sec in ["80C", "80D", "80G"]:
        match = re.search(rf"{sec}\s+([\d,]+)", text)
        if match:
            val = match.group(1).replace(",", "")
            try:
                deductions[f"section_{sec}"] = int(val)
            except ValueError:
                continue
    if deductions:
        extracted["deductions"] = deductions

    return extracted

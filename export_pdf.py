from fpdf import FPDF

def generate_pdf(data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt="Form-16 Extract Summary", ln=True, align='C')
    pdf.ln(10)

    for key, value in data.items():
        if isinstance(value, dict):  # for quarterly_summary or nested dicts
            pdf.cell(200, 10, txt=f"{key}:", ln=True)
            for subkey, subvalue in value.items():
                val_str = str(subvalue).replace("â‚¹", "Rs")  # Replace rupee symbol with Rs
                pdf.cell(200, 10, txt=f"   {subkey}: {val_str}", ln=True)
        else:
            val_str = str(value).replace("â‚¹", "Rs")  # Replace rupee symbol with Rs
            pdf.cell(200, 10, txt=f"{key}: {val_str}", ln=True)

    # Output PDF as bytes directly
    return pdf.output(dest='S').encode('latin-1')  # 'S' returns string, encode to bytes
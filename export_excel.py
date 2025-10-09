import pandas as pd
from io import BytesIO

def generate_excel(data):
    flat_data = data.copy()

    # Flatten quarterly_tds dict if present
    if isinstance(flat_data.get("quarterly_tds"), dict):
        for quarter, amount in flat_data["quarterly_tds"].items():
            flat_data[f"TDS_{quarter}"] = amount
        del flat_data["quarterly_tds"]

    df = pd.DataFrame([flat_data])

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Form16 Summary')
    return output.getvalue()

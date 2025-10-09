import zipfile
import io

def generate_zip(json_data: bytes, excel_data: bytes, pdf_data: bytes) -> bytes:
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr("form16_extracted.json", json_data)
        zip_file.writestr("form16_extracted.xlsx", excel_data)
        zip_file.writestr("form16_extracted.pdf", pdf_data)

    zip_buffer.seek(0)
    return zip_buffer.getvalue()

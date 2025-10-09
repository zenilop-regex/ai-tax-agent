# enhanced_extractor.py
import re
import json
import logging
import hashlib
import pdfplumber
import fitz  # PyMuPDF
import requests
import io
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
LLM_ENDPOINTS = [
    {"name": "LM Studio Chat", "url": "http://127.0.0.1:1234/v1/chat/completions", "type": "chat"},
    {"name": "LM Studio", "url": "http://127.0.0.1:1234/v1/completions", "type": "completion"},
]

LLM_CONFIG = {
    "headers": {"Content-Type": "application/json"},
    "timeout": 180,
    "max_tokens": 1024,
    "temperature": 0.1,  # Lower for better accuracy
    "model": "zephyr-7b-beta"
}

SCHEMA_VERSION = "2.4.1"

@dataclass
class ExtractionResult:
    """Structured result from Form-16 extraction"""
    company_name: Optional[str] = None
    employee_name: Optional[str] = None
    pan_of_employer: Optional[str] = None
    pan_of_employee: Optional[str] = None
    tan: Optional[str] = None
    assessment_year: Optional[str] = None
    gross_salary_paid: int = 0
    total_tds_deducted: int = 0
    quarterly_tds: Dict[str, int] = None
    deductions: Dict[str, int] = None
    errors: List[str] = None
    source_map: Dict[str, str] = None
    filing_ready: bool = False
    schema_version: str = SCHEMA_VERSION
    taxpayer_hash: Optional[str] = None

    def __post_init__(self):
        if self.quarterly_tds is None:
            self.quarterly_tds = {}
        if self.deductions is None:
            self.deductions = {}
        if self.errors is None:
            self.errors = []
        if self.source_map is None:
            self.source_map = {}

class PDFExtractor:
    """Enhanced PDF text extraction with fallback methods"""
    
    @staticmethod
    def extract_text(file_bytes: bytes) -> str:
        """Extract text from PDF with multiple fallback methods"""
        text = ""
        
        # Method 1: pdfplumber (best for structured PDFs)
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages)
                if text.strip():
                    logger.info("Successfully extracted text using pdfplumber")
                    return text
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed: {e}")
        
        # Method 2: PyMuPDF (fallback)
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            text = "\n".join(page.get_text() for page in doc)
            doc.close()
            if text.strip():
                logger.info("Successfully extracted text using PyMuPDF")
                return text
        except Exception as e:
            logger.warning(f"PyMuPDF extraction failed: {e}")
        
        # Method 3: OCR fallback (if available)
        try:
            import pytesseract
            from PIL import Image
            import pdf2image
            
            images = pdf2image.convert_from_bytes(file_bytes)
            ocr_text = ""
            for img in images:
                ocr_text += pytesseract.image_to_string(img) + "\n"
            
            if ocr_text.strip():
                logger.info("Successfully extracted text using OCR")
                return ocr_text
        except ImportError:
            logger.warning("OCR libraries not available (pytesseract, pdf2image)")
        except Exception as e:
            logger.warning(f"OCR extraction failed: {e}")
        
        return text

class ValidationEngine:
    """Data validation utilities"""
    
    @staticmethod
    def is_valid_pan(pan: str) -> bool:
        """Validate PAN format"""
        if not pan or not isinstance(pan, str):
            return False
        return bool(re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", pan.upper()))
    
    @staticmethod
    def is_valid_tan(tan: str) -> bool:
        """Validate TAN format"""
        if not tan or not isinstance(tan, str):
            return False
        return bool(re.fullmatch(r"[A-Z]{4}[0-9]{5}[A-Z]", tan.upper()))
    
    @staticmethod
    def normalize_amount(amount_str: str) -> int:
        """Convert amount string to integer"""
        if not amount_str:
            return 0
        try:
            # Remove currency symbols and commas
            clean_str = re.sub(r'[₹,\s]', '', str(amount_str))
            return int(float(clean_str))
        except (ValueError, TypeError):
            return 0

class RegexExtractor:
    """Enhanced regex-based extraction patterns"""
    
    # Core field patterns
    PATTERNS = {
        "company_name": [
            r"Employer\s+Name\s*[:\-]?\s*(.*?)\s+(?:Employer\s+PAN|PAN)",
            r"Name\s+of\s+Employer\s*[:\-]?\s*(.*?)(?:\n|$)",
            r"Deductor\s+Name\s*[:\-]?\s*(.*?)(?:\n|$)"
        ],
        "employee_name": [
            r"Employee\s+Name\s*[:\-]?\s*(.*?)\s+(?:Employee\s+PAN|PAN)",
            r"Name\s+of\s+Employee\s*[:\-]?\s*(.*?)(?:\n|$)",
            r"Deductee\s+Name\s*[:\-]?\s*(.*?)(?:\n|$)"
        ],
        "pan_of_employer": [
            r"Employer\s+PAN\s*[:\-]?\s*([A-Z]{5}[0-9]{4}[A-Z])",
            r"PAN\s+of\s+Employer\s*[:\-]?\s*([A-Z]{5}[0-9]{4}[A-Z])",
            r"Deductor\s+PAN\s*[:\-]?\s*([A-Z]{5}[0-9]{4}[A-Z])"
        ],
        "pan_of_employee": [
            r"Employee\s+PAN\s*[:\-]?\s*([A-Z]{5}[0-9]{4}[A-Z])",
            r"PAN\s+of\s+Employee\s*[:\-]?\s*([A-Z]{5}[0-9]{4}[A-Z])",
            r"Deductee\s+PAN\s*[:\-]?\s*([A-Z]{5}[0-9]{4}[A-Z])"
        ],
        "tan": [
            r"TAN\s*(?:of\s*Employer)?\s*[:\-]?\s*([A-Z]{4}[0-9]{5}[A-Z])",
            r"Tax\s+Deduction\s+(?:and\s+)?Collection\s+Account\s+Number\s*[:\-]?\s*([A-Z]{4}[0-9]{5}[A-Z])"
        ],
        "assessment_year": [
            r"Assessment\s+Year\s*[:\-]?\s*(\d{4}-\d{2})",
            r"A\.?Y\.?\s*[:\-]?\s*(\d{4}-\d{2})",
            r"Financial\s+Year\s*[:\-]?\s*(\d{4}-\d{2})"
        ],
        "gross_salary_paid": [
            r"Gross\s+Salary\s+Paid\s*[:\-]?\s*[\u20B9]?\s*([\d,]+)",
            r"Total\s+Income\s*[:\-]?\s*[\u20B9]?\s*([\d,]+)",
            r"Gross\s+Total\s+Income\s*[:\-]?\s*[\u20B9]?\s*([\d,]+)"
        ],
        "total_tds_deducted": [
            r"Total\s+TDS\s+Deducted\s*[:\-]?\s*[\u20B9]?\s*([\d,]+)",
            r"Total\s+Tax\s+Deducted\s*[:\-]?\s*[\u20B9]?\s*([\d,]+)",
            r"Tax\s+Deducted\s+at\s+Source\s*[:\-]?\s*[\u20B9]?\s*([\d,]+)"
        ]
    }
    
    # Quarterly TDS patterns
    QUARTERLY_PATTERNS = {
        "Q1": [
            r"(?:1st\s+Quarter|Q1|First\s+Quarter)[^₹\d]*₹?\s*([\d,]+)",
            r"April\s+to\s+June[^₹\d]*₹?\s*([\d,]+)"
        ],
        "Q2": [
            r"(?:2nd\s+Quarter|Q2|Second\s+Quarter)[^₹\d]*₹?\s*([\d,]+)",
            r"July\s+to\s+September[^₹\d]*₹?\s*([\d,]+)"
        ],
        "Q3": [
            r"(?:3rd\s+Quarter|Q3|Third\s+Quarter)[^₹\d]*₹?\s*([\d,]+)",
            r"October\s+to\s+December[^₹\d]*₹?\s*([\d,]+)"
        ],
        "Q4": [
            r"(?:4th\s+Quarter|Q4|Fourth\s+Quarter|Final\s+Quarter)[^₹\d]*₹?\s*([\d,]+)",
            r"January\s+to\s+March[^₹\d]*₹?\s*([\d,]+)"
        ]
    }
    
    # Deduction patterns
    DEDUCTION_PATTERNS = {
        "section_80C": [
            r"80C[^₹\d]*₹?\s*([\d,]+)",
            r"Section\s+80C[^₹\d]*₹?\s*([\d,]+)"
        ],
        "section_80D": [
            r"80D[^₹\d]*₹?\s*([\d,]+)",
            r"Section\s+80D[^₹\d]*₹?\s*([\d,]+)"
        ],
        "section_80G": [
            r"80G[^₹\d]*₹?\s*([\d,]+)",
            r"Section\s+80G[^₹\d]*₹?\s*([\d,]+)"
        ]
    }
    
    @classmethod
    def extract_field(cls, text: str, field_name: str) -> Optional[str]:
        """Extract a single field using multiple patterns"""
        patterns = cls.PATTERNS.get(field_name, [])
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                if value and value not in ['', '-', 'N/A', 'None']:
                    return value
        
        return None
    
    @classmethod
    def extract_quarterly_tds(cls, text: str) -> Dict[str, int]:
        """Extract quarterly TDS amounts"""
        quarterly = {}
        
        for quarter, patterns in cls.QUARTERLY_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        amount = ValidationEngine.normalize_amount(match.group(1))
                        if amount > 0:
                            quarterly[quarter] = amount
                            break
                    except (ValueError, IndexError):
                        continue
        
        return quarterly
    
    @classmethod
    def extract_deductions(cls, text: str) -> Dict[str, int]:
        """Extract deduction amounts"""
        deductions = {}
        
        for section, patterns in cls.DEDUCTION_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        amount = ValidationEngine.normalize_amount(match.group(1))
                        if amount > 0:
                            deductions[section] = amount
                            break
                    except (ValueError, IndexError):
                        continue
        
        return deductions

class LLMExtractor:
    """LLM-based extraction with robust error handling"""
    
    @staticmethod
    def is_server_available() -> bool:
        """Check if LLM server is available"""
        for endpoint in LLM_ENDPOINTS:
            try:
                test_url = endpoint["url"].replace("/completions", "/models").replace("/chat/completions", "/models")
                response = requests.get(test_url, timeout=5)
                if response.status_code == 200:
                    logger.info(f"✓ Found working LLM: {endpoint['name']}")
                    return True
            except:
                continue
        logger.warning("No LLM server available")
        return False
    
    @classmethod
    def extract_missing_fields(cls, text: str, missing_fields: List[str]) -> Dict[str, Any]:
        """Extract missing fields using LLM"""
        if not missing_fields:
            return {}
        
        # Try each endpoint
        for endpoint in LLM_ENDPOINTS:
            try:
                if not cls._test_endpoint(endpoint):
                    continue
                
                logger.info(f"Trying LLM extraction with {endpoint['name']}")
                
                prompt = cls._create_prompt(text, missing_fields)
                result = cls._call_endpoint(endpoint, prompt)
                
                if result:
                    logger.info(f"✓ LLM extraction successful with {endpoint['name']}")
                    return result
                    
            except Exception as e:
                logger.warning(f"Endpoint {endpoint['name']} failed: {e}")
                continue
        
        logger.warning("All LLM endpoints failed")
        return {}

    @staticmethod
    def _test_endpoint(endpoint: Dict) -> bool:
        """Test if endpoint is working"""
        try:
            test_url = endpoint["url"].replace("/completions", "/models").replace("/chat/completions", "/models")
            response = requests.get(test_url, timeout=3)
            return response.status_code == 200
        except:
            return False

    @staticmethod
    def _create_prompt(text: str, missing_fields: List[str]) -> str:
        """Create extraction prompt"""
        return f"""Extract these exact fields from the Form-16. Return ONLY valid JSON.

    Fields needed: {', '.join(missing_fields)}

    Rules:
    - Pure JSON only, no explanation
    - Numbers without commas/symbols
    - Exact field names

    Example:
    {{
    "company_name": "ABC Corp",
    "employee_name": "John Doe",
    "gross_salary_paid": 500000
    }}

    Form-16 Text:
    {text[:3500]}

    JSON:"""

    @classmethod
    def _call_endpoint(cls, endpoint: Dict, prompt: str) -> Dict[str, Any]:
        """Call LLM endpoint"""
        try:
            if endpoint["type"] == "chat":
                payload = {
                    "messages": [
                        {"role": "system", "content": "Extract data and return only JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 1000
                }
            else:
                payload = {
                    "prompt": prompt,
                    "temperature": 0.1,
                    "max_tokens": 1000
                }
            
            response = requests.post(
                endpoint["url"],
                json=payload,
                headers=LLM_CONFIG["headers"],
                timeout=LLM_CONFIG["timeout"]
            )
            response.raise_for_status()
            result = response.json()
            
            if endpoint["type"] == "chat":
                content = result["choices"][0]["message"]["content"]
            else:
                content = result["choices"][0]["text"]
            
            return cls._parse_llm_response(content)
            
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return {}
    
    @staticmethod
    def _parse_llm_response(raw_text: str) -> Dict[str, Any]:
        """Parse LLM response and extract JSON"""
        if not raw_text:
            return {}
        
        # Try direct parse first
        try:
            return json.loads(raw_text)
        except:
            pass
        
        # Try finding JSON in markdown or text
        patterns = [
            r'```json\s*(\{.*?\})\s*```',  # ```json {...} ```
            r'```\s*(\{.*?\})\s*```',       # ``` {...} ```
            r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})'  # Any {...}
        ]
        
        for pattern in patterns:
            match = re.search(pattern, raw_text, re.DOTALL)
            if match:
                try:
                    json_str = match.group(1)
                    # Clean it
                    json_str = json_str.replace("'", '"').replace(',}', '}').replace(',]', ']')
                    
                    # Balance braces
                    open_b = json_str.count('{')
                    close_b = json_str.count('}')
                    if open_b > close_b:
                        json_str += '}' * (open_b - close_b)
                    
                    return json.loads(json_str)
                except:
                    continue
        
        # Fallback: extract key-value pairs manually
        result = {}
        for match in re.finditer(r'"(\w+)":\s*"([^"]*)"', raw_text):
            result[match.group(1)] = match.group(2)
        for match in re.finditer(r'"(\w+)":\s*(\d+)', raw_text):
            result[match.group(1)] = int(match.group(2))
        
        return result if result else {}

class Form16Extractor:
    """Main Form-16 extraction engine"""
    
    def __init__(self):
        self.pdf_extractor = PDFExtractor()
        self.validator = ValidationEngine()
        self.regex_extractor = RegexExtractor()
        self.llm_extractor = LLMExtractor()
    
    def extract(self, file_bytes: bytes) -> Dict[str, Any]:
        """Extract data from Form-16 PDF"""
        try:
            # Step 1: Extract text from PDF
            text = self.pdf_extractor.extract_text(file_bytes)
            if not text.strip():
                return {"error": "Could not extract text from PDF"}
            
            logger.info(f"Extracted {len(text)} characters from PDF")
            
            # Step 2: Initialize result
            result = ExtractionResult()
            
            # Step 3: Regex extraction
            self._extract_with_regex(text, result)
            
            # Step 4: Validate extracted data
            self._validate_data(result)
            
            # Step 5: LLM fallback for missing fields
            self._llm_fallback(text, result)
            
            # Step 6: Final processing
            self._finalize_result(result)
            
            return asdict(result)
            
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            logger.error(traceback.format_exc())
            return {"error": f"Extraction failed: {str(e)}"}
    
    def _extract_with_regex(self, text: str, result: ExtractionResult):
        """Extract fields using regex patterns"""
        logger.info("Starting regex extraction")
        
        # Extract core fields
        for field_name in ['company_name', 'employee_name', 'pan_of_employer', 
                          'pan_of_employee', 'tan', 'assessment_year']:
            value = self.regex_extractor.extract_field(text, field_name)
            if value:
                setattr(result, field_name, value)
                result.source_map[field_name] = 'regex'
        
        # Extract amounts
        for field_name in ['gross_salary_paid', 'total_tds_deducted']:
            value = self.regex_extractor.extract_field(text, field_name)
            if value:
                amount = self.validator.normalize_amount(value)
                setattr(result, field_name, amount)
                result.source_map[field_name] = 'regex'
        
        # Extract quarterly TDS
        quarterly = self.regex_extractor.extract_quarterly_tds(text)
        if quarterly:
            result.quarterly_tds = quarterly
            result.source_map['quarterly_tds'] = 'regex'
        
        # Extract deductions
        deductions = self.regex_extractor.extract_deductions(text)
        if deductions:
            result.deductions = deductions
            result.source_map['deductions'] = 'regex'
    
    def _validate_data(self, result: ExtractionResult):
        """Validate extracted data"""
        logger.info("Validating extracted data")
        
        # Validate PANs
        if result.pan_of_employee and not self.validator.is_valid_pan(result.pan_of_employee):
            result.errors.append("Invalid Employee PAN format")
        
        if result.pan_of_employer and not self.validator.is_valid_pan(result.pan_of_employer):
            result.errors.append("Invalid Employer PAN format")
        
        # Validate TAN
        if result.tan and not self.validator.is_valid_tan(result.tan):
            result.errors.append("Invalid TAN format")
        
        # Check quarterly TDS sum
        if result.quarterly_tds and result.total_tds_deducted:
            quarterly_sum = sum(result.quarterly_tds.values())
            if abs(quarterly_sum - result.total_tds_deducted) > 100:  # Allow small differences
                result.errors.append(f"Quarterly TDS sum ({quarterly_sum}) doesn't match total TDS ({result.total_tds_deducted})")
    
    def _llm_fallback(self, text: str, result: ExtractionResult):
        """Use LLM to fill missing critical fields"""
        logger.info("Starting LLM fallback extraction")
        
        # Identify missing critical fields
        critical_fields = [
            'company_name', 'employee_name', 'pan_of_employee', 'tan',
            'gross_salary_paid', 'total_tds_deducted'
        ]
        
        missing_fields = []
        for field in critical_fields:
            value = getattr(result, field)
            if not value or (isinstance(value, (int, float)) and value == 0):
                missing_fields.append(field)
        
        if not missing_fields:
            logger.info("No critical fields missing, skipping LLM extraction")
            return
        
        logger.info(f"Missing fields for LLM extraction: {missing_fields}")
        
        # Extract using LLM
        llm_data = self.llm_extractor.extract_missing_fields(text, missing_fields)
        
        if llm_data:
            logger.info("LLM extraction successful")
            for field, value in llm_data.items():
                if field in missing_fields and value:
                    if field in ['gross_salary_paid', 'total_tds_deducted']:
                        value = self.validator.normalize_amount(str(value))
                    
                    setattr(result, field, value)
                    result.source_map[field] = 'llm'
            
            # Handle nested data
            if 'quarterly_tds' in llm_data and isinstance(llm_data['quarterly_tds'], dict):
                if not result.quarterly_tds:
                    result.quarterly_tds = {}
                for q, amount in llm_data['quarterly_tds'].items():
                    if q not in result.quarterly_tds or not result.quarterly_tds[q]:
                        result.quarterly_tds[q] = self.validator.normalize_amount(str(amount))
                result.source_map['quarterly_tds'] = 'llm'
            
            if 'deductions' in llm_data and isinstance(llm_data['deductions'], dict):
                if not result.deductions:
                    result.deductions = {}
                for section, amount in llm_data['deductions'].items():
                    if section not in result.deductions or not result.deductions[section]:
                        result.deductions[section] = self.validator.normalize_amount(str(amount))
                result.source_map['deductions'] = 'llm'
    
    def _finalize_result(self, result: ExtractionResult):
        """Finalize extraction result"""
        logger.info("Finalizing extraction result")
        
        # Generate taxpayer hash
        if result.pan_of_employee and result.employee_name:
            hash_input = f"{result.pan_of_employee}_{result.employee_name}"
            result.taxpayer_hash = hashlib.sha256(hash_input.encode()).hexdigest()
        
        # Check if ready for filing
        critical_fields_filled = all([
            result.company_name,
            result.employee_name,
            result.pan_of_employee,
            result.tan,
            result.gross_salary_paid > 0,
            result.total_tds_deducted >= 0
        ])
        
        result.filing_ready = critical_fields_filled and len(result.errors) == 0
        
        logger.info(f"Extraction complete. Filing ready: {result.filing_ready}")

# Main extraction function for backward compatibility
def extract_form16(file_bytes: bytes) -> Dict[str, Any]:
    """Extract Form-16 data from PDF bytes"""
    extractor = Form16Extractor()
    result = extractor.extract(file_bytes)
    
    # Add metadata for backward compatibility
    if 'error' not in result:
        result['_meta'] = {
            'source': result.get('source_map', {}),
            'errors': result.get('errors', []),
            'filing_ready': result.get('filing_ready', False),
            'schema_version': result.get('schema_version', SCHEMA_VERSION),
            'taxpayer_hash': result.get('taxpayer_hash', '')
        }
    
    return result

# Test function
if __name__ == "__main__":
    # Test with a sample file
    import sys
    
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'rb') as f:
            file_bytes = f.read()
        
        result = extract_form16(file_bytes)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("Usage: python enhanced_extractor.py <pdf_file>")
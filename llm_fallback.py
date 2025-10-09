# improved_llm_extractor.py
# Add this to your enhanced_extractor.py or use as separate module

import re
import json
import logging
import requests
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class ImprovedLLMExtractor:
    """Enhanced LLM extraction with multiple endpoints and better prompting"""
    
    # Try multiple LLM endpoints
    ENDPOINTS = [
        {
            "name": "LM Studio",
            "url": "http://127.0.0.1:1234/v1/chat/completions",
            "type": "chat"
        },
        {
            "name": "LM Studio Completions",
            "url": "http://127.0.0.1:1234/v1/completions",
            "type": "completion"
        },
        {
            "name": "Ollama",
            "url": "http://127.0.0.1:11434/api/generate",
            "type": "ollama"
        }
    ]
    
    def __init__(self):
        self.working_endpoint = None
        self.timeout = 60
    
    def is_server_available(self) -> bool:
        """Check if any LLM server is available"""
        for endpoint in self.ENDPOINTS:
            try:
                # Try to connect
                if endpoint["type"] == "ollama":
                    test_url = "http://127.0.0.1:11434/api/tags"
                else:
                    test_url = endpoint["url"].replace("/completions", "/models").replace("/chat/completions", "/models")
                
                response = requests.get(test_url, timeout=5)
                if response.status_code == 200:
                    self.working_endpoint = endpoint
                    logger.info(f"Found working LLM endpoint: {endpoint['name']}")
                    return True
            except Exception as e:
                logger.debug(f"Endpoint {endpoint['name']} not available: {e}")
                continue
        
        logger.warning("No LLM server available")
        return False
    
    def extract_missing_fields(self, text: str, missing_fields: List[str]) -> Dict[str, Any]:
        """Extract missing fields using LLM with improved prompting"""
        
        if not self.is_server_available():
            logger.warning("No LLM server available")
            return {}
        
        if not missing_fields:
            return {}
        
        # Create a better structured prompt
        prompt = self._create_extraction_prompt(text, missing_fields)
        
        # Try extraction with retries
        for attempt in range(3):
            try:
                result = self._call_llm(prompt)
                if result:
                    logger.info(f"LLM extraction successful on attempt {attempt + 1}")
                    return result
            except Exception as e:
                logger.warning(f"LLM attempt {attempt + 1} failed: {e}")
                continue
        
        logger.error("All LLM extraction attempts failed")
        return {}
    
    def _create_extraction_prompt(self, text: str, missing_fields: List[str]) -> str:
        """Create a well-structured extraction prompt"""
        
        # Field descriptions to help LLM understand what to extract
        field_descriptions = {
            'company_name': 'The name of the employer/company',
            'employee_name': 'The name of the employee',
            'pan_of_employee': 'Employee PAN in format ABCDE1234F (5 letters, 4 digits, 1 letter)',
            'pan_of_employer': 'Employer PAN in format ABCDE1234F',
            'tan': 'TAN (Tax Deduction Account Number) in format ABCD12345E (4 letters, 5 digits, 1 letter)',
            'gross_salary_paid': 'Total gross salary amount (number only)',
            'total_tds_deducted': 'Total TDS (Tax Deducted at Source) amount (number only)',
            'assessment_year': 'Assessment year in format YYYY-YY (e.g., 2024-25)',
            'quarterly_tds': 'Quarterly TDS breakdown with Q1, Q2, Q3, Q4'
        }
        
        # Build field list with descriptions
        field_list = []
        for field in missing_fields:
            desc = field_descriptions.get(field, field)
            field_list.append(f"- {field}: {desc}")
        
        prompt = f"""You are a data extraction expert. Extract ONLY the following fields from this Form-16 tax document.

CRITICAL RULES:
1. Return ONLY valid JSON, nothing else
2. Use exact field names provided
3. For PAN/TAN: Must match exact format (ABCDE1234F for PAN, ABCD12345E for TAN)
4. For amounts: Return only numbers, no currency symbols
5. If a field is not found, use null

FIELDS TO EXTRACT:
{chr(10).join(field_list)}

REQUIRED OUTPUT FORMAT:
{{
  "company_name": "Company Name Here or null",
  "employee_name": "Employee Name Here or null",
  "pan_of_employee": "ABCDE1234F or null",
  "gross_salary_paid": 500000,
  "total_tds_deducted": 50000
}}

FORM-16 TEXT (first 3000 characters):
{text[:3000]}

EXTRACT THE DATA NOW (JSON only):"""
        
        return prompt
    
    def _call_llm(self, prompt: str) -> Dict[str, Any]:
        """Call LLM based on endpoint type"""
        
        if not self.working_endpoint:
            return {}
        
        endpoint = self.working_endpoint
        
        try:
            if endpoint["type"] == "chat":
                return self._call_chat_endpoint(endpoint["url"], prompt)
            elif endpoint["type"] == "completion":
                return self._call_completion_endpoint(endpoint["url"], prompt)
            elif endpoint["type"] == "ollama":
                return self._call_ollama_endpoint(endpoint["url"], prompt)
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return {}
    
    def _call_chat_endpoint(self, url: str, prompt: str) -> Dict[str, Any]:
        """Call chat-style endpoint (LM Studio chat)"""
        
        payload = {
            "messages": [
                {
                    "role": "system",
                    "content": "You are a precise data extraction assistant. Return only valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1,  # Low temperature for factual extraction
            "max_tokens": 1000
        }
        
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=self.timeout
        )
        
        response.raise_for_status()
        result = response.json()
        
        # Extract content from chat response
        if "choices" in result and result["choices"]:
            content = result["choices"][0].get("message", {}).get("content", "")
            return self._parse_json_response(content)
        
        return {}
    
    def _call_completion_endpoint(self, url: str, prompt: str) -> Dict[str, Any]:
        """Call completion-style endpoint (LM Studio completion)"""
        
        payload = {
            "prompt": prompt,
            "temperature": 0.1,
            "max_tokens": 1000,
            "stop": ["\n\n", "###"]
        }
        
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=self.timeout
        )
        
        response.raise_for_status()
        result = response.json()
        
        if "choices" in result and result["choices"]:
            content = result["choices"][0].get("text", "")
            return self._parse_json_response(content)
        
        return {}
    
    def _call_ollama_endpoint(self, url: str, prompt: str) -> Dict[str, Any]:
        """Call Ollama endpoint"""
        
        payload = {
            "model": "llama2",  # or whatever model is available
            "prompt": prompt,
            "stream": False
        }
        
        response = requests.post(
            url,
            json=payload,
            timeout=self.timeout
        )
        
        response.raise_for_status()
        result = response.json()
        
        if "response" in result:
            return self._parse_json_response(result["response"])
        
        return {}
    
    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """Parse JSON from LLM response with multiple strategies"""
        
        if not text or not text.strip():
            return {}
        
        # Strategy 1: Direct JSON parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Strategy 2: Find JSON block in markdown code blocks
        json_patterns = [
            r'```json\s*(\{.*?\})\s*```',
            r'```\s*(\{.*?\})\s*```',
            r'(\{[^}]*"[^"]*"[^}]*\})',
            r'(\{.*\})'
        ]
        
        for pattern in json_patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                try:
                    json_str = match.group(1)
                    # Clean up common issues
                    json_str = self._clean_json_string(json_str)
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    continue
        
        # Strategy 3: Extract key-value pairs manually
        return self._extract_key_values(text)
    
    def _clean_json_string(self, json_str: str) -> str:
        """Clean common JSON formatting issues"""
        
        # Replace smart quotes
        json_str = json_str.replace('"', '"').replace('"', '"')
        json_str = json_str.replace("'", '"')
        
        # Remove trailing commas
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)
        
        # Balance braces
        open_braces = json_str.count('{')
        close_braces = json_str.count('}')
        if open_braces > close_braces:
            json_str += '}' * (open_braces - close_braces)
        
        return json_str
    
    def _extract_key_values(self, text: str) -> Dict[str, Any]:
        """Extract key-value pairs as fallback"""
        
        result = {}
        
        # Pattern to match: "key": "value" or "key": value
        patterns = [
            r'"(\w+)":\s*"([^"]*)"',
            r'"(\w+)":\s*(\d+)',
            r'(\w+):\s*"([^"]*)"',
            r'(\w+):\s*(\d+)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for key, value in matches:
                # Convert to proper type
                if value.isdigit():
                    result[key] = int(value)
                elif value.lower() == 'null':
                    result[key] = None
                else:
                    result[key] = value
        
        return result

# Integration function for enhanced_extractor.py
def create_improved_llm_extractor():
    """Factory function to create improved LLM extractor"""
    return ImprovedLLMExtractor()


# ============================================
# REPLACEMENT CODE FOR enhanced_extractor.py
# ============================================
# Replace the LLMExtractor class in your enhanced_extractor.py with this:

class LLMExtractor:
    """LLM extraction with improved reliability"""
    
    def __init__(self):
        self.improved_extractor = ImprovedLLMExtractor()
    
    @staticmethod
    def is_server_available() -> bool:
        """Check if LLM server is available"""
        extractor = ImprovedLLMExtractor()
        return extractor.is_server_available()
    
    def extract_missing_fields(self, text: str, missing_fields: List[str]) -> Dict[str, Any]:
        """Extract missing fields using improved LLM"""
        return self.improved_extractor.extract_missing_fields(text, missing_fields)


# ============================================
# TESTING FUNCTION
# ============================================
def test_llm_extraction():
    """Test the improved LLM extraction"""
    
    sample_text = """
    Form 16 - Part A
    
    Name of Employer: ABC Tech Solutions Pvt Ltd
    Address: 123 Business Park, Mumbai
    
    PAN of Deductor: AAACB1234C
    TAN of Deductor: MUMA12345D
    
    Name of Employee: RAJESH KUMAR SHARMA
    PAN of Employee: ABCDE1234F
    
    Assessment Year: 2024-25
    
    Gross Salary: Rs. 12,00,000
    Total TDS Deducted: Rs. 1,20,000
    
    Quarterly TDS:
    Q1: 30,000
    Q2: 30,000
    Q3: 30,000
    Q4: 30,000
    """
    
    extractor = ImprovedLLMExtractor()
    
    print("Testing LLM Server Availability...")
    if extractor.is_server_available():
        print(f"✓ Connected to: {extractor.working_endpoint['name']}")
        
        print("\nExtracting fields...")
        missing_fields = [
            'company_name',
            'employee_name',
            'pan_of_employee',
            'gross_salary_paid',
            'total_tds_deducted'
        ]
        
        result = extractor.extract_missing_fields(sample_text, missing_fields)
        
        print("\n" + "="*50)
        print("EXTRACTION RESULT:")
        print("="*50)
        print(json.dumps(result, indent=2))
        print("="*50)
        
        # Validate results
        if result:
            print("\n✓ Extraction successful!")
            for field, value in result.items():
                print(f"  - {field}: {value}")
        else:
            print("\n✗ Extraction failed - no data returned")
    else:
        print("✗ No LLM server available")
        print("\nTo fix:")
        print("1. Install LM Studio from https://lmstudio.ai/")
        print("2. Download a model (e.g., Mistral or Llama)")
        print("3. Start the local server on port 1234")


if __name__ == "__main__":
    test_llm_extraction()
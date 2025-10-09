# enhanced_itr_mapper.py
import json
import os
import copy
from datetime import date, datetime
from typing import Dict, Any, Optional, List, Tuple, Union
import logging

logger = logging.getLogger(__name__)

# Current schema version and defaults
SCHEMA_VERSION = "Ver1.0"
FORM_VERSION = "Ver1.0"

class ITRSchemaBuilder:
    """Build complete ITR-1 schema with proper defaults"""
    
    @staticmethod
    def get_creation_info() -> Dict[str, Any]:
        """Get creation info section"""
        return {
            "SWVersionNo": "1.0",
            "SWCreatedBy": "AI_TAX_AGENT",
            "JSONCreatedBy": "AI_TAX_AGENT",
            "JSONCreationDate": date.today().isoformat(),
            "IntermediaryCity": "Mumbai",
            "Digest": "-"
        }
    
    @staticmethod
    def get_form_itr1_info(assessment_year: str = "2025") -> Dict[str, Any]:
        """Get Form ITR1 section"""
        return {
            "FormName": "ITR-1",
            "Description": "For Individuals having Income from Salaries, one house property, other sources (Interest etc.) and having total income upto Rs. 50 lakh",
            "AssessmentYear": assessment_year,
            "SchemaVer": SCHEMA_VERSION,
            "FormVer": FORM_VERSION
        }
    
    @staticmethod
    def get_personal_info_template() -> Dict[str, Any]:
        """Get personal info template"""
        return {
            "AssesseeName": "REPLACE_WITH_NAME",
            "PAN": "AAAAA0000A",
            "Address": {
                "AddrDetail": "REPLACE_WITH_ADDRESS",
                "CityOrTownOrDistrict": "REPLACE_WITH_CITY",
                "StateCode": "27",  # Maharashtra as default
                "CountryCode": "IN",
                "PinCode": 400001
            },
            "DOB": "1990-01-01",
            "Status": "I",  # Individual
            "EmployerCategory": "OTH",  # Other
            "AadhaarCardNo": "",
            "AadhaarEnrolmentId": ""
        }
    
    @staticmethod
    def get_filing_status() -> Dict[str, Any]:
        """Get filing status section"""
        return {
            "ReturnFileSec": 11,  # Original return
            "OptOutNewTaxRegime": "N",  # Default to new regime (can be changed)
            "SeventhProvisoBusiness": "N",
            "ItrFilingDueDate": "2025-07-31",
            "ComplianceProviso139": "N"
        }
    
    @staticmethod
    def get_income_deductions_template() -> Dict[str, Any]:
        """Get income and deductions template"""
        return {
            # Salary income
            "GrossSalary": 0,
            "AllowExemptUs10": 0,  # Exemptions under section 10
            "DeductionUs16": 50000,  # Standard deduction
            "EntertainmentAllowanceUs16ii": 0,
            "ProfessionalTaxUs16iii": 0,
            "IncomeFromSal": 0,
            "NetSalary": 0,
            
            # House property income
            "IncomeFromHP": 0,
            
            # Other sources
            "IncomeFromOS": 0,
            
            # Deductions under Chapter VI-A
            "UsrDeductUndChapVIA": {
                "Section80C": 0,
                "Section80CCC": 0,
                "Section80CCD1": 0,
                "Section80CCD1B": 0,
                "Section80CCD2": 0,
                "Section80D": 0,
                "Section80DD": 0,
                "Section80DDB": 0,
                "Section80E": 0,
                "Section80EE": 0,
                "Section80EEA": 0,
                "Section80EEB": 0,
                "Section80G": 0,
                "Section80GG": 0,
                "Section80GGA": 0,
                "Section80GGC": 0,
                "Section80U": 0,
                "Section80TTA": 0,
                "Section80TTB": 0
            },
            "DeductUndChapVIA": {
                "Section80C": 0,
                "Section80CCC": 0,
                "Section80CCD1": 0,
                "Section80CCD1B": 0,
                "Section80CCD2": 0,
                "Section80D": 0,
                "Section80DD": 0,
                "Section80DDB": 0,
                "Section80E": 0,
                "Section80EE": 0,
                "Section80EEA": 0,
                "Section80EEB": 0,
                "Section80G": 0,
                "Section80GG": 0,
                "Section80GGA": 0,
                "Section80GGC": 0,
                "Section80U": 0,
                "Section80TTA": 0,
                "Section80TTB": 0,
                "TotalChapVIADeductions": 0
            },
            
            # Total income calculation
            "GrossTotIncome": 0,
            "TotalIncome": 0
        }
    
    @staticmethod
    def get_tds_template() -> Dict[str, Any]:
        """Get TDS section template"""
        return {
            "TDSonSalary": [],
            "TotalTDSonSalaries": 0
        }
    
    @staticmethod
    def get_tax_computation_template() -> Dict[str, Any]:
        """Get tax computation template"""
        return {
            "TotalTaxPayable": 0,
            "Rebate87A": 0,
            "TaxPayableOnRebate": 0,
            "SurchargeOnAbove": 0,
            "EducationCess": 0,
            "GrossTaxLiability": 0,
            "Section89": 0,
            "NetTaxLiability": 0,
            "TotalIntrstPay": 0,
            "IntrstPay": {
                "IntrstPayUs234A": 0,
                "IntrstPayUs234B": 0,
                "IntrstPayUs234C": 0,
                "IntrstPayUs234F": 0,
                "LateFilingFee": 0
            },
            "TotTaxPlusIntrstPay": 0
        }
    
    @staticmethod
    def get_taxes_paid_template() -> Dict[str, Any]:
        """Get taxes paid section template"""
        return {
            "TaxesPaid": {
                "AdvanceTax": 0,
                "TDS": 0,
                "TCS": 0,
                "SelfAssessmentTax": 0,
                "TotalTaxesPaid": 0
            },
            "BalTaxPayable": 0
        }
    
    @staticmethod
    def get_refund_template() -> Dict[str, Any]:
        """Get refund section template"""
        return {
            "RefundDue": 0,
            "BankAccountDtls": {
                "BankName": "REPLACE_BANK_NAME",
                "BankAccountNo": "REPLACE_ACCOUNT_NUMBER",
                "IFSCCode": "REPLACE_IFSC",
                "BankAddress": "REPLACE_BANK_ADDRESS",
                "AccountType": "S",  # Savings
                "UseForRefund": "Y"
            }
        }
    
    @staticmethod
    def get_verification_template() -> Dict[str, Any]:
        """Get verification section template"""
        return {
            "Declaration": {
                "AssesseeVerName": "REPLACE_VERIFIER_NAME",
                "FatherName": "REPLACE_FATHER_NAME",
                "AssesseeVerPAN": "AAAAA0000A"
            },
            "Capacity": "S",  # Self
            "Place": "REPLACE_PLACE",
            "Date": date.today().isoformat()
        }

class Form16ToITRMapper:
    """Enhanced mapper from Form-16 data to ITR JSON"""
    
    def __init__(self):
        self.schema_builder = ITRSchemaBuilder()
    
    def map_to_itr(self, form16_data: Dict[str, Any], 
                   assessment_year: Optional[str] = None) -> Dict[str, Any]:
        """Map Form-16 data to complete ITR-1 JSON"""
        try:
            # Determine assessment year
            if not assessment_year:
                assessment_year = self._derive_assessment_year(
                    form16_data.get('assessment_year', '')
                )
            
            # Build base ITR structure
            itr_json = self._build_base_structure(assessment_year)
            
            # Map all sections
            self._map_personal_info(form16_data, itr_json)
            self._map_income_deductions(form16_data, itr_json)
            self._map_tds_data(form16_data, itr_json)
            self._map_tax_computation(form16_data, itr_json)
            self._map_taxes_paid(form16_data, itr_json)
            self._map_refund_details(form16_data, itr_json)
            self._map_verification(form16_data, itr_json)
            
            # Calculate derived fields
            self._calculate_totals(itr_json)
            
            logger.info("Successfully mapped Form-16 to ITR JSON")
            return itr_json
            
        except Exception as e:
            logger.error(f"Error mapping Form-16 to ITR: {e}")
            raise
    
    def _derive_assessment_year(self, assessment_year_str: str) -> str:
        """Derive assessment year from Form-16 assessment year"""
        if not assessment_year_str:
            return "2025"  # Default to current AY
        
        try:
            # Handle formats like "2024-25" or "2024-2025"
            if '-' in assessment_year_str:
                parts = assessment_year_str.split('-')
                if len(parts) >= 2 and parts[0].isdigit():
                    return str(int(parts[0]) + 1)
            
            # Handle 4-digit years
            if assessment_year_str.isdigit() and len(assessment_year_str) == 4:
                return str(int(assessment_year_str) + 1)
            
        except (ValueError, IndexError):
            pass
        
        return "2025"  # Fallback
    
    def _build_base_structure(self, assessment_year: str) -> Dict[str, Any]:
        """Build base ITR structure"""
        return {
            "ITR": {
                "ITR1": {
                    "CreationInfo": self.schema_builder.get_creation_info(),
                    "Form_ITR1": self.schema_builder.get_form_itr1_info(assessment_year),
                    "PersonalInfo": self.schema_builder.get_personal_info_template(),
                    "FilingStatus": self.schema_builder.get_filing_status(),
                    "ITR1_IncomeDeductions": self.schema_builder.get_income_deductions_template(),
                    "TDSonSalaries": self.schema_builder.get_tds_template(),
                    "ITR1_TaxComputation": self.schema_builder.get_tax_computation_template(),
                    "TaxPaid": self.schema_builder.get_taxes_paid_template(),
                    "Refund": self.schema_builder.get_refund_template(),
                    "Verification": self.schema_builder.get_verification_template()
                }
            }
        }
    
    def _map_personal_info(self, form16_data: Dict[str, Any], itr_json: Dict[str, Any]):
        """Map personal information"""
        personal_info = itr_json["ITR"]["ITR1"]["PersonalInfo"]
        
        # Employee name
        if form16_data.get('employee_name'):
            personal_info["AssesseeName"] = self._normalize_name(form16_data['employee_name'])
        
        # PAN
        if form16_data.get('pan_of_employee'):
            pan = form16_data['pan_of_employee'].strip().upper()
            personal_info["PAN"] = pan
            # Also set in verification
            itr_json["ITR"]["ITR1"]["Verification"]["Declaration"]["AssesseeVerPAN"] = pan
        
        # Set default DOB if needed (can be updated later)
        if not personal_info.get("DOB") or personal_info["DOB"] == "1990-01-01":
            # Keep placeholder - user needs to fill this
            pass
    
    def _map_income_deductions(self, form16_data: Dict[str, Any], itr_json: Dict[str, Any]):
        """Map income and deductions"""
        income_section = itr_json["ITR"]["ITR1"]["ITR1_IncomeDeductions"]
        
        # Gross salary
        gross_salary = self._safe_int(form16_data.get('gross_salary_paid', 0))
        income_section["GrossSalary"] = gross_salary
        
        # Standard deduction (50,000 for AY 2024-25)
        standard_deduction = 50000
        income_section["DeductionUs16"] = standard_deduction
        
        # Income from salary after standard deduction
        income_from_salary = max(0, gross_salary - standard_deduction)
        income_section["IncomeFromSal"] = income_from_salary
        income_section["NetSalary"] = income_from_salary
        
        # Map deductions
        self._map_deductions(form16_data, income_section)
        
        # Calculate totals
        total_via_deductions = income_section["DeductUndChapVIA"]["TotalChapVIADeductions"]
        income_section["GrossTotIncome"] = income_from_salary
        income_section["TotalIncome"] = max(0, income_from_salary - total_via_deductions)
    
    def _map_deductions(self, form16_data: Dict[str, Any], income_section: Dict[str, Any]):
        """Map deductions under Chapter VI-A"""
        deductions_data = form16_data.get('deductions', {})
        
        user_deductions = income_section["UsrDeductUndChapVIA"]
        computed_deductions = income_section["DeductUndChapVIA"]
        
        # Section 80C
        section_80c = min(self._safe_int(deductions_data.get('section_80C', 0)), 150000)
        user_deductions["Section80C"] = section_80c
        computed_deductions["Section80C"] = section_80c
        
        # Section 80D
        section_80d = min(self._safe_int(deductions_data.get('section_80D', 0)), 25000)
        user_deductions["Section80D"] = section_80d
        computed_deductions["Section80D"] = section_80d
        
        # Section 80G (no limit typically, but validate amount)
        section_80g = self._safe_int(deductions_data.get('section_80G', 0))
        user_deductions["Section80G"] = section_80g
        computed_deductions["Section80G"] = section_80g
        
        # Calculate total deductions
        total_deductions = sum([
            computed_deductions.get("Section80C", 0),
            computed_deductions.get("Section80CCC", 0),
            computed_deductions.get("Section80CCD1", 0),
            computed_deductions.get("Section80CCD1B", 0),
            computed_deductions.get("Section80D", 0),
            computed_deductions.get("Section80DD", 0),
            computed_deductions.get("Section80DDB", 0),
            computed_deductions.get("Section80E", 0),
            computed_deductions.get("Section80EE", 0),
            computed_deductions.get("Section80EEA", 0),
            computed_deductions.get("Section80G", 0),
            computed_deductions.get("Section80GG", 0),
            computed_deductions.get("Section80GGA", 0),
            computed_deductions.get("Section80U", 0),
            computed_deductions.get("Section80TTA", 0),
            computed_deductions.get("Section80TTB", 0)
        ])
        
        computed_deductions["TotalChapVIADeductions"] = total_deductions
    
    def _map_tds_data(self, form16_data: Dict[str, Any], itr_json: Dict[str, Any]):
        """Map TDS data"""
        tds_section = itr_json["ITR"]["ITR1"]["TDSonSalaries"]
        
        total_tds = self._safe_int(form16_data.get('total_tds_deducted', 0))
        tds_section["TotalTDSonSalaries"] = total_tds
        
        # Create TDS entry for employer
        employer_entry = {
            "EmployerOrDeductorOrCollectDetl": {
                "TAN": form16_data.get('tan', 'REPLACE_WITH_TAN'),
                "EmployerOrDeductorOrCollecterName": self._normalize_name(
                    form16_data.get('company_name', 'REPLACE_WITH_EMPLOYER_NAME')
                )
            },
            "IncChrgSal": self._safe_int(form16_data.get('gross_salary_paid', 0)),
            "TotalTDSSal": total_tds
        }
        
        # Add quarterly breakup if available
        quarterly_tds = form16_data.get('quarterly_tds', {})
        if quarterly_tds:
            for quarter in ['Q1', 'Q2', 'Q3', 'Q4']:
                amount = self._safe_int(quarterly_tds.get(quarter, 0))
                if amount > 0:
                    employer_entry[f"TDSSal{quarter}"] = amount
        
        tds_section["TDSonSalary"] = [employer_entry]
    
    def _map_tax_computation(self, form16_data: Dict[str, Any], itr_json: Dict[str, Any]):
        """Map tax computation (will be calculated later)"""
        tax_comp = itr_json["ITR"]["ITR1"]["ITR1_TaxComputation"]
        
        # Initialize with zeros - will be calculated in _calculate_totals
        tax_comp["TotalTaxPayable"] = 0
        tax_comp["Rebate87A"] = 0
        tax_comp["TaxPayableOnRebate"] = 0
        tax_comp["EducationCess"] = 0
        tax_comp["GrossTaxLiability"] = 0
        tax_comp["NetTaxLiability"] = 0
        tax_comp["TotTaxPlusIntrstPay"] = 0
    
    def _map_taxes_paid(self, form16_data: Dict[str, Any], itr_json: Dict[str, Any]):
        """Map taxes paid section"""
        tax_paid = itr_json["ITR"]["ITR1"]["TaxPaid"]
        
        total_tds = self._safe_int(form16_data.get('total_tds_deducted', 0))
        
        tax_paid["TaxesPaid"]["TDS"] = total_tds
        tax_paid["TaxesPaid"]["TotalTaxesPaid"] = total_tds
        
        # Initialize other payments to 0
        tax_paid["TaxesPaid"]["AdvanceTax"] = 0
        tax_paid["TaxesPaid"]["SelfAssessmentTax"] = 0
        tax_paid["TaxesPaid"]["TCS"] = 0
    
    def _map_refund_details(self, form16_data: Dict[str, Any], itr_json: Dict[str, Any]):
        """Map refund details (placeholders for now)"""
        refund_section = itr_json["ITR"]["ITR1"]["Refund"]
        
        # Keep bank details as placeholders - user needs to fill
        refund_section["RefundDue"] = 0  # Will be calculated
        refund_section["BankAccountDtls"]["UseForRefund"] = "Y"
    
    def _map_verification(self, form16_data: Dict[str, Any], itr_json: Dict[str, Any]):
        """Map verification section"""
        verification = itr_json["ITR"]["ITR1"]["Verification"]
        
        # Set assessee name for verification
        if form16_data.get('employee_name'):
            verification["Declaration"]["AssesseeVerName"] = self._normalize_name(
                form16_data['employee_name']
            )
        
        # Set place as placeholder
        verification["Place"] = "REPLACE_WITH_PLACE"
        verification["Date"] = date.today().isoformat()
    
    def _calculate_totals(self, itr_json: Dict[str, Any]):
        """Calculate derived totals and tax liability"""
        itr1 = itr_json["ITR"]["ITR1"]
        income_section = itr1["ITR1_IncomeDeductions"]
        tax_comp = itr1["ITR1_TaxComputation"]
        tax_paid = itr1["TaxPaid"]
        refund_section = itr1["Refund"]
        
        try:
            # Get total taxable income
            total_income = income_section["TotalIncome"]
            
            # Calculate tax liability (simplified - basic slabs)
            tax_liability = self._calculate_basic_tax(total_income)
            
            # Apply rebate under 87A if applicable
            rebate_87a = 0
            if total_income <= 500000:  # Old regime limit
                rebate_87a = min(tax_liability, 12500)
            
            tax_after_rebate = max(0, tax_liability - rebate_87a)
            
            # Add cess (4%)
            cess = int(tax_after_rebate * 0.04)
            gross_tax_liability = tax_after_rebate + cess
            
            # Update tax computation
            tax_comp["TotalTaxPayable"] = int(tax_liability)
            tax_comp["Rebate87A"] = int(rebate_87a)
            tax_comp["TaxPayableOnRebate"] = int(tax_after_rebate)
            tax_comp["EducationCess"] = cess
            tax_comp["GrossTaxLiability"] = int(gross_tax_liability)
            tax_comp["NetTaxLiability"] = int(gross_tax_liability)
            tax_comp["TotTaxPlusIntrstPay"] = int(gross_tax_liability)
            
            # Calculate balance tax payable or refund
            total_taxes_paid = tax_paid["TaxesPaid"]["TotalTaxesPaid"]
            balance = total_taxes_paid - gross_tax_liability
            
            if balance >= 0:
                # Refund due
                refund_section["RefundDue"] = int(balance)
                tax_paid["BalTaxPayable"] = 0
            else:
                # Additional tax payable
                refund_section["RefundDue"] = 0
                tax_paid["BalTaxPayable"] = int(abs(balance))
            
        except Exception as e:
            logger.error(f"Error calculating totals: {e}")
            # Set safe defaults
            tax_comp["NetTaxLiability"] = 0
            tax_paid["BalTaxPayable"] = 0
            refund_section["RefundDue"] = 0
    
    def _calculate_basic_tax(self, taxable_income: int) -> int:
        """Calculate basic tax liability using old regime slabs"""
        if taxable_income <= 250000:
            return 0
        elif taxable_income <= 500000:
            return int((taxable_income - 250000) * 0.05)
        elif taxable_income <= 1000000:
            return int(250000 * 0.05 + (taxable_income - 500000) * 0.20)
        else:
            return int(250000 * 0.05 + 500000 * 0.20 + (taxable_income - 1000000) * 0.30)
    
    def _normalize_name(self, name: str) -> str:
        """Normalize name to proper case"""
        if not name:
            return name
        return " ".join(word.capitalize() for word in str(name).strip().split())
    
    def _safe_int(self, value: Any) -> int:
        """Safely convert value to integer"""
        if value is None:
            return 0
        try:
            if isinstance(value, (int, float)):
                return int(value)
            # Handle string with commas
            clean_value = str(value).replace(',', '').replace('₹', '').strip()
            if not clean_value:
                return 0
            return int(float(clean_value))
        except (ValueError, TypeError):
            return 0

class ITREnhancer:
    """Enhance ITR JSON with additional features"""
    
    @staticmethod
    def apply_overrides(itr_json: Dict[str, Any], 
                       overrides: Dict[str, Any]) -> Dict[str, Any]:
        """Apply field overrides to ITR JSON"""
        enhanced_json = copy.deepcopy(itr_json)
        
        for path, value in overrides.items():
            try:
                # Handle suggestion format from AI agent
                if isinstance(value, dict) and 'suggested_value' in value:
                    actual_value = value['suggested_value']
                else:
                    actual_value = value
                
                # Apply the override
                ITREnhancer._set_nested_value(enhanced_json, path, actual_value)
                
            except Exception as e:
                logger.warning(f"Failed to apply override for {path}: {e}")
        
        return enhanced_json
    
    @staticmethod
    def _set_nested_value(data: Dict[str, Any], path: str, value: Any):
        """Set nested dictionary value by dot-separated path"""
        # Handle paths that start with ITR.ITR1
        if path.startswith('ITR.ITR1.'):
            path = path[8:]  # Remove 'ITR.ITR1.'
            target = data.get('ITR', {}).get('ITR1', {})
        elif path.startswith('ITR1.'):
            path = path[5:]  # Remove 'ITR1.'
            target = data.get('ITR', {}).get('ITR1', {})
        else:
            target = data.get('ITR', {}).get('ITR1', {})
        
        keys = path.split('.')
        current = target
        
        # Navigate to the parent of the target key
        for key in keys[:-1]:
            if '[' in key and ']' in key:
                # Handle array indices like TDSonSalary[0]
                array_key = key[:key.index('[')]
                index = int(key[key.index('[')+1:key.index(']')])
                
                if array_key not in current:
                    current[array_key] = []
                
                # Extend array if needed
                while len(current[array_key]) <= index:
                    current[array_key].append({})
                
                current = current[array_key][index]
            else:
                if key not in current:
                    current[key] = {}
                current = current[key]
        
        # Set the final value
        final_key = keys[-1]
        if '[' in final_key and ']' in final_key:
            array_key = final_key[:final_key.index('[')]
            index = int(final_key[final_key.index('[')+1:final_key.index(']')])
            
            if array_key not in current:
                current[array_key] = []
            
            while len(current[array_key]) <= index:
                current[array_key].append({})
            
            current[array_key][index] = value
        else:
            # Try to convert string numbers to integers for numeric fields
            if isinstance(value, str) and value.strip():
                try:
                    # Check if it's a numeric field that should be an integer
                    if any(keyword in final_key.lower() for keyword in 
                           ['salary', 'income', 'tds', 'tax', 'amount', 'deduction', 'refund']):
                        clean_value = value.replace(',', '').replace('₹', '').strip()
                        if clean_value.replace('.', '').isdigit():
                            value = int(float(clean_value))
                except (ValueError, AttributeError):
                    pass
            
            current[final_key] = value

# Main functions for backward compatibility
def map_form16_to_itd(form16_data: Dict[str, Any], 
                      template_path: Optional[str] = None) -> Dict[str, Any]:
    """Map Form-16 data to ITR JSON (backward compatibility)"""
    mapper = Form16ToITRMapper()
    return mapper.map_to_itr(form16_data)

def apply_overrides(itd_json: Dict[str, Any], 
                   overrides: Dict[str, Any]) -> Dict[str, Any]:
    """Apply overrides to ITR JSON (backward compatibility)"""
    return ITREnhancer.apply_overrides(itd_json, overrides)

def get_placeholders(itd_obj: Dict[str, Any]) -> List[Tuple[str, Any]]:
    """Get placeholder fields in ITR JSON"""
    placeholders = []
    
    def _find_placeholders(obj: Any, path: str = ""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key
                _find_placeholders(value, current_path)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                current_path = f"{path}[{i}]"
                _find_placeholders(item, current_path)
        else:
            if _is_placeholder_value(obj):
                placeholders.append((path, obj))
    
    # Start from ITR.ITR1
    itr1 = itd_obj.get('ITR', {}).get('ITR1', {})
    _find_placeholders(itr1)
    
    return placeholders

def _is_placeholder_value(value: Any) -> bool:
    """Check if a value is a placeholder"""
    if value is None:
        return True
    
    if isinstance(value, str):
        s = value.strip().upper()
        placeholder_values = {
            '', 'REPLACE_WITH_NAME', 'REPLACE_WITH_ADDRESS', 'REPLACE_BANK_NAME',
            'REPLACE_ACCOUNT_NUMBER', 'REPLACE_IFSC', 'REPLACE_BANK_ADDRESS',
            'REPLACE_VERIFIER_NAME', 'REPLACE_FATHER_NAME', 'REPLACE_WITH_PLACE',
            'REPLACE_WITH_TAN', 'REPLACE_WITH_EMPLOYER_NAME', 'AAAAA0000A',
            'REPLACE_WITH_CITY', '-'
        }
        return s in placeholder_values or s.startswith('REPLACE')
    
    return False

# CLI test function
if __name__ == "__main__":
    # Test mapping
    sample_form16 = {
        "company_name": "Tech Solutions Pvt Ltd",
        "employee_name": "RAJESH KUMAR SHARMA",
        "pan_of_employee": "ABCDE1234F",
        "pan_of_employer": "ABCDE1234G",
        "tan": "MUMX12345A",
        "assessment_year": "2024-25",
        "gross_salary_paid": 1200000,
        "total_tds_deducted": 120000,
        "quarterly_tds": {
            "Q1": 30000,
            "Q2": 30000, 
            "Q3": 30000,
            "Q4": 30000
        },
        "deductions": {
            "section_80C": 150000,
            "section_80D": 25000,
            "section_80G": 10000
        }
    }
    
    mapper = Form16ToITRMapper()
    result = mapper.map_to_itr(sample_form16)
    
    print("Generated ITR JSON:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    print("\nPlaceholders found:")
    for path, value in get_placeholders(result):
        print(f"  {path}: {value}")
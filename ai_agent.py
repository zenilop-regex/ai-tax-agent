# enhanced_ai_agent.py - FIXED VERSION
import copy
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
import re
import logging

logger = logging.getLogger(__name__)

# Enhanced placeholder detection
PLACEHOLDERS = {
    "", " ", "-", "NA", "N/A", "NONE", "NULL", "0", "0.0",
    "REPLACE", "REPLACE_ADDRESS", "REPLACE_BANK", "REPLACE_ACCOUNT",
    "REPLACE_VERIFIER_NAME", "REPLACE_FATHER_NAME", "REPLACE_WITH_NAME",
    "REPLACE_WITH_EMPLOYER", "REPLACE_WITH_TAN", "SW00000001", "AAAAA0000A"
}

class TaxCalculator:
    """Enhanced tax calculation with current slabs and deductions"""
    
    OLD_REGIME_SLABS = [
        (250000, 0.0),
        (500000, 0.05),
        (1000000, 0.20),
        (float('inf'), 0.30)
    ]
    
    NEW_REGIME_SLABS = [
        (300000, 0.0),
        (600000, 0.05),
        (900000, 0.10),
        (1200000, 0.15),
        (1500000, 0.20),
        (float('inf'), 0.30)
    ]
    
    STANDARD_DEDUCTION = 50000
    SECTION_80C_LIMIT = 150000
    SECTION_80D_LIMIT = 25000
    REBATE_87A_LIMIT = 500000
    REBATE_87A_AMOUNT = 12500
    CESS_RATE = 0.04
    
    @classmethod
    def calculate_tax_old_regime(cls, gross_income: int, deductions: Dict[str, int] = None) -> Dict[str, int]:
        """Calculate tax under old regime"""
        if deductions is None:
            deductions = {}
        
        income_after_standard = max(0, gross_income - cls.STANDARD_DEDUCTION)
        
        total_via_deductions = min(
            deductions.get('section_80C', 0), cls.SECTION_80C_LIMIT
        ) + min(
            deductions.get('section_80D', 0), cls.SECTION_80D_LIMIT
        ) + deductions.get('section_80G', 0)
        
        taxable_income = max(0, income_after_standard - total_via_deductions)
        
        tax_before_rebate = cls._calculate_slab_tax(taxable_income, cls.OLD_REGIME_SLABS)
        
        rebate_87a = 0
        if taxable_income <= cls.REBATE_87A_LIMIT:
            rebate_87a = min(tax_before_rebate, cls.REBATE_87A_AMOUNT)
        
        tax_after_rebate = max(0, tax_before_rebate - rebate_87a)
        cess = tax_after_rebate * cls.CESS_RATE
        total_tax = tax_after_rebate + cess
        
        return {
            'gross_income': gross_income,
            'standard_deduction': cls.STANDARD_DEDUCTION,
            'income_after_standard': income_after_standard,
            'total_via_deductions': total_via_deductions,
            'taxable_income': taxable_income,
            'tax_before_rebate': int(tax_before_rebate),
            'rebate_87a': int(rebate_87a),
            'tax_after_rebate': int(tax_after_rebate),
            'cess': int(cess),
            'total_tax_liability': int(total_tax)
        }
    
    @classmethod
    def calculate_tax_new_regime(cls, gross_income: int) -> Dict[str, int]:
        """Calculate tax under new regime"""
        income_after_standard = max(0, gross_income - cls.STANDARD_DEDUCTION)
        taxable_income = income_after_standard
        
        tax_before_rebate = cls._calculate_slab_tax(taxable_income, cls.NEW_REGIME_SLABS)
        
        rebate_87a = 0
        if taxable_income <= 700000:
            rebate_87a = min(tax_before_rebate, 25000)
        
        tax_after_rebate = max(0, tax_before_rebate - rebate_87a)
        cess = tax_after_rebate * cls.CESS_RATE
        total_tax = tax_after_rebate + cess
        
        return {
            'gross_income': gross_income,
            'standard_deduction': cls.STANDARD_DEDUCTION,
            'income_after_standard': income_after_standard,
            'total_via_deductions': 0,
            'taxable_income': taxable_income,
            'tax_before_rebate': int(tax_before_rebate),
            'rebate_87a': int(rebate_87a),
            'tax_after_rebate': int(tax_after_rebate),
            'cess': int(cess),
            'total_tax_liability': int(total_tax)
        }
    
    @classmethod
    def _calculate_slab_tax(cls, income: int, slabs: List[Tuple[int, float]]) -> float:
        """Calculate tax using given slabs"""
        tax = 0
        prev_limit = 0
        
        for limit, rate in slabs:
            if income <= prev_limit:
                break
            
            taxable_in_slab = min(income, limit) - prev_limit
            tax += taxable_in_slab * rate
            prev_limit = limit
            
            if income <= limit:
                break
        
        return tax
    
    @classmethod
    def compare_regimes(cls, gross_income: int, deductions: Dict[str, int] = None) -> Dict[str, Any]:
        """Compare tax liability under both regimes"""
        old_calc = cls.calculate_tax_old_regime(gross_income, deductions)
        new_calc = cls.calculate_tax_new_regime(gross_income)
        
        savings = old_calc['total_tax_liability'] - new_calc['total_tax_liability']
        
        return {
            'old_regime': old_calc,
            'new_regime': new_calc,
            'savings_new_regime': savings,
            'recommended_regime': 'new' if savings > 0 else 'old',
            'recommendation_reason': f"New regime saves ₹{abs(savings):,}" if savings > 0 else f"Old regime saves ₹{abs(savings):,}"
        }

class DataValidator:
    """Enhanced data validation and normalization"""
    
    @staticmethod
    def is_placeholder(value: Any) -> bool:
        """Check if value is a placeholder"""
        if value is None:
            return True
        
        if isinstance(value, str):
            s = value.strip().upper()
            if s in PLACEHOLDERS:
                return True
            if s.startswith("REPLACE"):
                return True
            return False
        
        if isinstance(value, (int, float)):
            return value == 0
        
        return False
    
    @staticmethod
    def normalize_name(name: str) -> str:
        """Normalize names to proper case"""
        if not name:
            return name
        return " ".join(word.capitalize() for word in name.strip().split())
    
    @staticmethod
    def normalize_pan(pan: str) -> str:
        """Normalize PAN to uppercase"""
        if not pan:
            return pan
        return pan.strip().upper()
    
    @staticmethod
    def validate_pan(pan: str) -> bool:
        """Validate PAN format"""
        if not pan:
            return False
        return bool(re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$', pan))
    
    @staticmethod
    def validate_tan(tan: str) -> bool:
        """Validate TAN format"""
        if not tan:
            return False
        return bool(re.match(r'^[A-Z]{4}[0-9]{5}[A-Z]$', tan))

class ITRAnalyzer:
    """Analyze ITR JSON for completeness and issues"""
    
    @staticmethod
    def analyze_completeness(itr_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze ITR data completeness"""
        if not itr_data or 'ITR' not in itr_data:
            return {'score': 0, 'issues': ['Invalid ITR structure']}
        
        itr1 = itr_data.get('ITR', {}).get('ITR1', {})
        if not itr1:
            return {'score': 0, 'issues': ['Missing ITR1 data']}
        
        issues = []
        filled_fields = 0
        total_fields = 0
        
        critical_sections = [
            ('PersonalInfo', ['AssesseeName', 'PAN']),
            ('ITR1_IncomeDeductions', ['GrossSalary', 'TotalIncome']),
            ('TDSonSalaries', ['TotalTDSonSalaries']),
            ('TaxPaid', ['TaxesPaid']),
            ('Verification', ['Declaration'])
        ]
        
        for section_name, required_fields in critical_sections:
            section = itr1.get(section_name, {})
            if not section:
                issues.append(f'Missing {section_name} section')
                total_fields += len(required_fields)
                continue
            
            for field in required_fields:
                total_fields += 1
                value = section.get(field)
                if value and not DataValidator.is_placeholder(value):
                    filled_fields += 1
                else:
                    issues.append(f'Missing or placeholder value: {section_name}.{field}')
        
        score = int((filled_fields / total_fields) * 100) if total_fields > 0 else 0
        
        return {
            'score': score,
            'filled_fields': filled_fields,
            'total_fields': total_fields,
            'issues': issues
        }

class SmartRecommendationEngine:
    """Enhanced recommendation engine with smart suggestions"""
    
    def __init__(self):
        self.validator = DataValidator()
        self.calculator = TaxCalculator()
        self.analyzer = ITRAnalyzer()
    
    def generate_recommendations(self, form16_data: Dict[str, Any], 
                               itr_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive recommendations"""
        recommendations = {
            'field_suggestions': {},
            'missing_fields': [],
            'tax_advice': [],
            'compliance_issues': [],
            'optimization_tips': [],
            'filing_readiness': {}
        }
        
        try:
            analysis = self.analyzer.analyze_completeness(itr_data)
            recommendations['filing_readiness'] = analysis
            
            self._generate_field_suggestions(form16_data, itr_data, recommendations)
            self._generate_tax_advice(form16_data, itr_data, recommendations)
            self._check_compliance(form16_data, itr_data, recommendations)
            self._detect_missing_fields(itr_data, recommendations)
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            recommendations['error'] = str(e)
        
        return recommendations
    
    def _generate_field_suggestions(self, form16_data: Dict[str, Any], 
                                  itr_data: Dict[str, Any], 
                                  recommendations: Dict[str, Any]):
        """Generate field-level suggestions"""
        suggestions = {}
        
        if not form16_data or not itr_data:
            return
        
        itr1_path = "ITR.ITR1"
        
        if form16_data.get('employee_name'):
            normalized_name = self.validator.normalize_name(form16_data['employee_name'])
            suggestions[f"{itr1_path}.PersonalInfo.AssesseeName"] = {
                'suggested_value': normalized_name,
                'reason': 'Normalized employee name to proper case',
                'confidence': 'high'
            }
        
        if form16_data.get('pan_of_employee'):
            normalized_pan = self.validator.normalize_pan(form16_data['pan_of_employee'])
            suggestions[f"{itr1_path}.PersonalInfo.PAN"] = {
                'suggested_value': normalized_pan,
                'reason': 'Normalized PAN to uppercase format',
                'confidence': 'high'
            }
        
        if form16_data.get('tan'):
            suggestions[f"{itr1_path}.TDSonSalaries.TDSonSalary[0].EmployerOrDeductorOrCollectDetl.TAN"] = {
                'suggested_value': self.validator.normalize_pan(form16_data['tan']),
                'reason': 'Fill TAN from Form-16',
                'confidence': 'high'
            }
        
        if form16_data.get('gross_salary_paid'):
            gross = int(form16_data['gross_salary_paid'])
            suggestions[f"{itr1_path}.ITR1_IncomeDeductions.GrossSalary"] = {
                'suggested_value': gross,
                'reason': 'Fill gross salary from Form-16',
                'confidence': 'high'
            }
        
        recommendations['field_suggestions'] = suggestions
    
    def _generate_tax_advice(self, form16_data: Dict[str, Any], 
                           itr_data: Dict[str, Any], 
                           recommendations: Dict[str, Any]):
        """Generate tax optimization advice"""
        advice = []
        
        try:
            gross_salary = form16_data.get('gross_salary_paid', 0)
            if not gross_salary:
                return
            
            deductions = form16_data.get('deductions', {})
            comparison = self.calculator.compare_regimes(int(gross_salary), deductions)
            
            old_tax = comparison['old_regime']['total_tax_liability']
            new_tax = comparison['new_regime']['total_tax_liability']
            
            if new_tax < old_tax:
                advice.append({
                    'type': 'regime_optimization',
                    'message': f"Consider opting for new tax regime to save ₹{old_tax - new_tax:,}",
                    'priority': 'high'
                })
            else:
                advice.append({
                    'type': 'regime_optimization',
                    'message': f"Old tax regime is better for you, saving ₹{new_tax - old_tax:,}",
                    'priority': 'medium'
                })
            
        except Exception as e:
            logger.error(f"Error generating tax advice: {e}")
        
        recommendations['tax_advice'] = advice
    
    def _check_compliance(self, form16_data: Dict[str, Any], 
                         itr_data: Dict[str, Any], 
                         recommendations: Dict[str, Any]):
        """Check compliance issues"""
        issues = []
        
        pan = form16_data.get('pan_of_employee')
        if pan and not self.validator.validate_pan(pan):
            issues.append({
                'type': 'invalid_pan',
                'message': f'Invalid PAN format: {pan}',
                'severity': 'high'
            })
        
        tan = form16_data.get('tan')
        if tan and not self.validator.validate_tan(tan):
            issues.append({
                'type': 'invalid_tan',
                'message': f'Invalid TAN format: {tan}',
                'severity': 'high'
            })
        
        recommendations['compliance_issues'] = issues
    
    def _detect_missing_fields(self, itr_data: Dict[str, Any], 
                             recommendations: Dict[str, Any]):
        """Detect missing critical fields"""
        missing = []
        
        if not itr_data or 'ITR' not in itr_data:
            missing.append({
                'field': 'ITR structure',
                'reason': 'Invalid or missing ITR structure',
                'severity': 'critical'
            })
            recommendations['missing_fields'] = missing
            return
        
        itr1 = itr_data.get('ITR', {}).get('ITR1', {})
        
        critical_fields = [
            ('PersonalInfo.AssesseeName', 'Taxpayer name is required'),
            ('PersonalInfo.PAN', 'PAN is mandatory'),
            ('ITR1_IncomeDeductions.GrossSalary', 'Gross salary amount is required'),
        ]
        
        for field_path, message in critical_fields:
            value = self._get_nested_value(itr1, field_path)
            if self.validator.is_placeholder(value):
                missing.append({
                    'field': field_path,
                    'reason': message,
                    'severity': 'high'
                })
        
        recommendations['missing_fields'] = missing
    
    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get nested dictionary value by dot-separated path"""
        keys = path.split('.')
        current = data
        
        for key in keys:
            if not isinstance(current, dict) or key not in current:
                return None
            current = current[key]
        
        return current

def get_agent_recommendations(form16_data: Dict[str, Any], 
                            itd_json: Dict[str, Any]) -> Dict[str, Any]:
    """Generate AI agent recommendations"""
    try:
        engine = SmartRecommendationEngine()
        recommendations = engine.generate_recommendations(form16_data, itd_json)
        
        result = {
            'missing_fields': [
                {'field_path': item['field'], 'reason': item['reason']}
                for item in recommendations.get('missing_fields', [])
            ],
            'suggestions': recommendations.get('field_suggestions', {}),
            'advice': [
                item['message'] for item in recommendations.get('tax_advice', [])
            ],
            'compliance_issues': recommendations.get('compliance_issues', []),
            'filing_readiness': recommendations.get('filing_readiness', {}),
            'logs': []
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error in get_agent_recommendations: {e}")
        return {
            'missing_fields': [],
            'suggestions': {},
            'advice': [f'Error generating recommendations: {str(e)}'],
            'compliance_issues': [],
            'filing_readiness': {'score': 0, 'issues': ['Analysis failed']},
            'logs': []
        }

def calculate_estimated_tax(gross_salary: int, deductions: Dict[str, int] = None) -> Dict[str, Any]:
    """Calculate estimated tax liability"""
    return TaxCalculator.compare_regimes(gross_salary, deductions or {})

def validate_form16_data(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Validate Form-16 data and return issues"""
    validator = DataValidator()
    issues = []
    
    if 'pan_of_employee' in data:
        if not validator.validate_pan(data['pan_of_employee']):
            issues.append({
                'field': 'pan_of_employee',
                'issue': 'Invalid PAN format',
                'severity': 'high'
            })
    
    required_fields = ['employee_name', 'company_name', 'gross_salary_paid']
    for field in required_fields:
        if not data.get(field):
            issues.append({
                'field': field,
                'issue': 'Required field is missing',
                'severity': 'high'
            })
    
    return issues
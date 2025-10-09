# config.py
"""Configuration file for AI Tax Filing Agent"""

import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "clients"
EXPORTS_DIR = BASE_DIR / "exports"
LOGS_DIR = BASE_DIR / "logs"

# Ensure directories exist
for directory in [DATA_DIR, EXPORTS_DIR, LOGS_DIR]:
    directory.mkdir(exist_ok=True)

# LLM Configuration
LLM_CONFIG = {
    "endpoint": os.getenv("LLM_ENDPOINT", "http://127.0.0.1:1234/v1/completions"),
    "model": os.getenv("LLM_MODEL", "zephyr-7b-beta"),
    "timeout": int(os.getenv("LLM_TIMEOUT", "180")),
    "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "1024")),
    "temperature": float(os.getenv("LLM_TEMPERATURE", "0.3")),
    "headers": {"Content-Type": "application/json"}
}

# Tax Configuration (AY 2024-25)
TAX_CONFIG = {
    "assessment_year": "2025",
    "standard_deduction": 50000,
    "section_80c_limit": 150000,
    "section_80d_limit": 25000,
    "rebate_87a_limit_old": 500000,
    "rebate_87a_limit_new": 700000,
    "rebate_87a_amount_old": 12500,
    "rebate_87a_amount_new": 25000,
    "cess_rate": 0.04
}

# File Processing Configuration
FILE_CONFIG = {
    "max_file_size_mb": 10,
    "allowed_extensions": [".pdf"],
    "temp_dir": BASE_DIR / "temp",
    "backup_enabled": True,
    "cleanup_temp_files": True
}

# Database Configuration
DB_CONFIG = {
    "type": "sqlite",  # Can be changed to PostgreSQL for production
    "sqlite_path": DATA_DIR / "clients.db",
    "backup_interval_hours": 24,
    "max_backups": 7
}

# Security Configuration
SECURITY_CONFIG = {
    "encrypt_client_data": True,
    "hash_pan_numbers": True,
    "log_level": "INFO",
    "max_failed_attempts": 3,
    "session_timeout_minutes": 60
}

# Application Configuration
APP_CONFIG = {
    "app_name": "AI Tax Filing Agent",
    "version": "2.4.1",
    "phase": "MVP - Salaried Employee Support",
    "max_concurrent_users": 100,
    "enable_analytics": False,
    "debug_mode": os.getenv("DEBUG", "False").lower() == "true"
}

# Export formats and templates
EXPORT_CONFIG = {
    "formats": ["json", "excel", "pdf", "zip"],
    "json_indent": 2,
    "excel_template": "form16_template.xlsx",
    "pdf_template": "form16_template.pdf",
    "include_metadata": True
}

# Validation Rules
VALIDATION_CONFIG = {
    "pan_pattern": r"^[A-Z]{5}[0-9]{4}[A-Z]$",
    "tan_pattern": r"^[A-Z]{4}[0-9]{5}[A-Z]$",
    "min_salary": 0,
    "max_salary": 100000000,  # 10 crores
    "required_fields": [
        "employee_name", "pan_of_employee", "company_name", 
        "gross_salary_paid", "total_tds_deducted"
    ]
}

# Feature Flags for different phases
FEATURE_FLAGS = {
    "phase_1_salaried": True,
    "phase_2_freelancers": False,
    "phase_3_traders": False,
    "phase_4_businesses": False,
    "voice_input": False,
    "regional_languages": False,
    "eri_filing": False,
    "ca_integration": False
}

def get_config():
    """Get all configuration as a single dict"""
    return {
        "llm": LLM_CONFIG,
        "tax": TAX_CONFIG,
        "file": FILE_CONFIG,
        "db": DB_CONFIG,
        "security": SECURITY_CONFIG,
        "app": APP_CONFIG,
        "export": EXPORT_CONFIG,
        "validation": VALIDATION_CONFIG,
        "features": FEATURE_FLAGS,
        "directories": {
            "base": BASE_DIR,
            "data": DATA_DIR,
            "exports": EXPORTS_DIR,
            "logs": LOGS_DIR
        }
    }

# Environment-specific overrides
def load_env_config():
    """Load environment-specific configuration"""
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    if env == "production":
        # Production overrides
        APP_CONFIG["debug_mode"] = False
        SECURITY_CONFIG["log_level"] = "WARNING"
        DB_CONFIG["type"] = "postgresql"  # Would need connection details
        
    elif env == "testing":
        # Testing overrides
        APP_CONFIG["debug_mode"] = True
        DATA_DIR = BASE_DIR / "test_data"
        SECURITY_CONFIG["log_level"] = "DEBUG"
        
    return get_config()

if __name__ == "__main__":
    # Print current configuration
    import json
    config = get_config()
    
    # Convert Path objects to strings for JSON serialization
    def convert_paths(obj):
        if isinstance(obj, Path):
            return str(obj)
        elif isinstance(obj, dict):
            return {k: convert_paths(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_paths(item) for item in obj]
        else:
            return obj
    
    config_json = convert_paths(config)
    print(json.dumps(config_json, indent=2))

# requirements.txt content
REQUIREMENTS_TXT = """
# Core dependencies
streamlit>=1.28.0
pandas>=1.5.0
numpy>=1.24.0

# PDF processing
pdfplumber>=0.9.0
PyMuPDF>=1.23.0
pdf2image>=3.1.0  # Optional for OCR fallback
pytesseract>=0.3.10  # Optional for OCR fallback
Pillow>=10.0.0

# HTTP requests and JSON
requests>=2.31.0
httpx>=0.25.0  # Alternative to requests with async support

# Excel export
openpyxl>=3.1.0
xlsxwriter>=3.1.0

# PDF generation
fpdf2>=2.7.0
reportlab>=4.0.0  # Alternative PDF library

# Data validation and processing
marshmallow>=3.20.0  # For data validation schemas
pydantic>=2.4.0  # Alternative validation library
jsonschema>=4.19.0

# Encryption and security
cryptography>=41.0.0
hashlib2>=1.0.0  # For secure hashing

# Database (optional for future phases)
sqlite3  # Built into Python
sqlalchemy>=2.0.0  # For advanced database operations
alembic>=1.12.0  # For database migrations

# Logging and monitoring
loguru>=0.7.0  # Better logging than standard library
rich>=13.5.0  # Better console output

# Date and time handling
python-dateutil>=2.8.0

# Environment management
python-dotenv>=1.0.0

# Testing (development only)
pytest>=7.4.0
pytest-cov>=4.1.0
black>=23.7.0  # Code formatting
flake8>=6.0.0  # Linting

# Optional: Advanced features for future phases
spacy>=3.7.0  # For NLP processing
transformers>=4.35.0  # For local LLM alternatives
torch>=2.1.0  # For ML models
scikit-learn>=1.3.0  # For data analysis

# Optional: Voice processing (Phase 4)
speechrecognition>=3.10.0
pydub>=0.25.0

# Optional: Regional language support (Phase 4)
googletrans>=4.0.0
indic-transliteration>=2.3.0

# Deployment (production)
gunicorn>=21.2.0  # WSGI server
uvicorn>=0.23.0  # ASGI server
docker>=6.1.0  # Containerization
redis>=5.0.0  # Caching and session management

# Monitoring (production)
prometheus-client>=0.17.0
grafana-api>=1.0.0
"""

# Docker configuration
DOCKERFILE_CONTENT = """
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    tesseract-ocr \\
    poppler-utils \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p clients exports logs temp

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Run the application
CMD ["streamlit", "run", "enhanced_main_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
"""

# Docker Compose for full stack
DOCKER_COMPOSE_CONTENT = """
version: '3.8'

services:
  tax-agent:
    build: .
    ports:
      - "8501:8501"
    environment:
      - ENVIRONMENT=production
      - LLM_ENDPOINT=http://llm-server:1234/v1/completions
    volumes:
      - ./clients:/app/clients
      - ./exports:/app/exports
      - ./logs:/app/logs
    depends_on:
      - llm-server
      - redis
    restart: unless-stopped

  llm-server:
    image: ollama/ollama:latest
    ports:
      - "1234:11434"
    volumes:
      - ollama_data:/root/.ollama
    environment:
      - OLLAMA_HOST=0.0.0.0
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - tax-agent
    restart: unless-stopped

volumes:
  ollama_data:
  redis_data:
"""

# Save all configuration files
def save_config_files():
    """Save all configuration files to disk"""
    files_to_save = {
        "requirements.txt": REQUIREMENTS_TXT,
        "Dockerfile": DOCKERFILE_CONTENT,
        "docker-compose.yml": DOCKER_COMPOSE_CONTENT
    }
    
    for filename, content in files_to_save.items():
        with open(BASE_DIR / filename, 'w') as f:
            f.write(content.strip())
    
    print("Configuration files saved:")
    for filename in files_to_save.keys():
        print(f"  - {filename}")

if __name__ == "__main__":
    save_config_files()
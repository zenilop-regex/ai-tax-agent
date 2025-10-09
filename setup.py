# setup.py
"""
AI Tax Filing Agent - Setup and Installation Script
This script sets up the complete tax filing system from your existing codebase.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

class TaxAgentSetup:
    def __init__(self):
        self.base_dir = Path.cwd()
        self.required_dirs = [
            "clients", "exports", "logs", "temp", 
            "clients/exports", "clients/backups"
        ]
        self.config_created = False
        
    def print_step(self, step_num, message):
        """Print formatted step message"""
        print(f"\n{'='*50}")
        print(f"STEP {step_num}: {message}")
        print(f"{'='*50}")
    
    def create_directories(self):
        """Create required directories"""
        self.print_step(1, "Creating Directory Structure")
        
        for dir_path in self.required_dirs:
            full_path = self.base_dir / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
            print(f"✓ Created directory: {full_path}")
    
    def create_requirements_file(self):
        """Create requirements.txt file"""
        self.print_step(2, "Creating Requirements File")
        
        requirements = """
streamlit>=1.28.0
pandas>=1.5.0
numpy>=1.24.0
pdfplumber>=0.9.0
PyMuPDF>=1.23.0
requests>=2.31.0
openpyxl>=3.1.0
fpdf2>=2.7.0
python-dateutil>=2.8.0
python-dotenv>=1.0.0
cryptography>=41.0.0
        """.strip()
        
        with open(self.base_dir / "requirements.txt", "w") as f:
            f.write(requirements)
        
        print("✓ Created requirements.txt")
    
    def check_existing_files(self):
        """Check which files already exist from user's codebase"""
        self.print_step(3, "Checking Existing Files")
        
        existing_files = [
            "app.py", "client_dashboard.py", "extractor.py", 
            "ai_agent.py", "itd_mapper.py", "export_pdf.py",
            "export_excel.py", "export_zip.py"
        ]
        
        found_files = []
        missing_files = []
        
        for file in existing_files:
            if (self.base_dir / file).exists():
                found_files.append(file)
                print(f"✓ Found: {file}")
            else:
                missing_files.append(file)
                print(f"✗ Missing: {file}")
        
        return found_files, missing_files
    
    def create_env_file(self):
        """Create .env file for configuration"""
        self.print_step(4, "Creating Environment Configuration")
        
        env_content = """
# AI Tax Filing Agent Configuration
ENVIRONMENT=development
DEBUG=true

# LLM Configuration
LLM_ENDPOINT=http://127.0.0.1:1234/v1/completions
LLM_MODEL=zephyr-7b-beta
LLM_TIMEOUT=180
LLM_MAX_TOKENS=1024
LLM_TEMPERATURE=0.3

# Security
ENCRYPT_DATA=true
LOG_LEVEL=INFO

# File Processing
MAX_FILE_SIZE_MB=10
CLEANUP_TEMP_FILES=true
        """.strip()
        
        env_path = self.base_dir / ".env"
        if not env_path.exists():
            with open(env_path, "w") as f:
                f.write(env_content)
            print("✓ Created .env file")
        else:
            print("✓ .env file already exists")
    
    def create_gitignore(self):
        """Create .gitignore file"""
        gitignore_content = """
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Environment
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# Data directories
clients/
exports/
logs/
temp/
*.db
*.sqlite

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Streamlit
.streamlit/secrets.toml
        """.strip()
        
        gitignore_path = self.base_dir / ".gitignore"
        if not gitignore_path.exists():
            with open(gitignore_path, "w") as f:
                f.write(gitignore_content)
            print("✓ Created .gitignore")
        else:
            print("✓ .gitignore already exists")
    
    def install_dependencies(self):
        """Install Python dependencies"""
        self.print_step(5, "Installing Dependencies")
        
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
            ])
            print("✓ Dependencies installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to install dependencies: {e}")
            print("You can install manually with: pip install -r requirements.txt")
    
    def create_startup_script(self):
        """Create startup scripts"""
        self.print_step(6, "Creating Startup Scripts")
        
        # Windows batch file
        bat_content = """@echo off
echo Starting AI Tax Filing Agent...
echo.
echo Make sure LM Studio is running on localhost:1234
echo.
streamlit run enhanced_main_app.py --server.port=8501
pause
        """
        
        with open(self.base_dir / "start_windows.bat", "w") as f:
            f.write(bat_content)
        
        # Linux/Mac shell script
        sh_content = """#!/bin/bash
echo "Starting AI Tax Filing Agent..."
echo ""
echo "Make sure LM Studio is running on localhost:1234"
echo ""
streamlit run enhanced_main_app.py --server.port=8501
        """
        
        sh_path = self.base_dir / "start_unix.sh"
        with open(sh_path, "w") as f:
            f.write(sh_content)
        
        # Make shell script executable
        try:
            os.chmod(sh_path, 0o755)
        except:
            pass
        
        print("✓ Created startup scripts")
        print("  - start_windows.bat (for Windows)")  
        print("  - start_unix.sh (for Linux/Mac)")
    
    def create_readme(self):
        """Create comprehensive README"""
        self.print_step(7, "Creating Documentation")
        
        readme_content = """# AI Tax Filing Agent

Automated Form-16 processing and ITR-1 generation for Indian taxpayers.

## Features

- **PDF Processing**: Extract data from Form-16 PDFs using AI
- **Smart Validation**: Validate PAN, TAN, and financial data
- **Tax Calculation**: Compare old vs new tax regimes
- **ITR Generation**: Create official ITR-1 JSON for e-filing
- **AI Recommendations**: Get suggestions for optimization
- **Multiple Exports**: JSON, Excel, PDF, and ZIP formats

## Setup Instructions

### 1. Install Python Requirements
```bash
pip install -r requirements.txt
```

### 2. Set up LLM Server (Optional but recommended)
- Download and install [LM Studio](https://lmstudio.ai/)
- Load a model like "microsoft/DialoGPT-medium" or similar
- Start the server on localhost:1234
- The system will work without LLM but with reduced accuracy

### 3. Run the Application
```bash
# Windows
start_windows.bat

# Linux/Mac
./start_unix.sh

# Or directly with streamlit
streamlit run enhanced_main_app.py
```

### 4. Access the Application
- Open your browser to http://localhost:8501
- Upload your Form-16 PDF
- Follow the guided workflow

## File Structure
```
ai-tax-agent/
├── enhanced_main_app.py          # Main Streamlit application
├── enhanced_extractor.py         # Enhanced PDF extraction
├── enhanced_ai_agent.py         # AI recommendations engine  
├── enhanced_itr_mapper.py       # ITR JSON generation
├── config.py                    # Configuration settings
├── export_pdf.py               # PDF export functionality
├── export_excel.py             # Excel export functionality
├── export_zip.py               # ZIP export functionality
├── clients/                    # Client data storage
├── exports/                    # Export files
├── logs/                      # Application logs
└── temp/                      # Temporary files
```

## Usage Workflow

### Phase 1: MVP - Salaried Employees
1. **Upload Form-16**: Select PDF from your employer
2. **Data Extraction**: AI extracts salary, TDS, deductions
3. **Review & Edit**: Verify and correct extracted data
4. **ITR Generation**: Generate official ITR-1 JSON
5. **Download & File**: Get files and upload to IT portal

### Supported Data Points
- Employee and employer information
- Salary and TDS details
- Section 80C, 80D, 80G deductions
- Quarterly TDS breakdown
- Tax calculations and optimization

## AI Features

### Smart Extraction
- Regex patterns for structured data
- LLM fallback for complex formats
- Validation and error detection

### Tax Optimization
- Old vs new regime comparison
- Investment recommendations
- Refund/liability estimation

### Quality Assurance
- PAN/TAN format validation
- Cross-verification of amounts
- Completeness scoring

## Security

- No data stored permanently without consent
- PAN numbers can be hashed for privacy
- Local processing (no data sent to external APIs)
- Encryption support for sensitive data

## Troubleshooting

### Common Issues

1. **PDF not extracting properly**
   - Ensure PDF is readable (not password protected)
   - Try with a clearer scan
   - Check file size < 10MB

2. **LLM server connection failed**
   - Verify LM Studio is running on localhost:1234
   - Check firewall settings
   - System will work with reduced accuracy without LLM

3. **Data validation errors**
   - Double-check PAN format (ABCDE1234F)
   - Verify TAN format (MUMA12345A)
   - Ensure salary amounts are reasonable

### Getting Help
- Check the browser console for error messages
- Look in the logs/ directory for detailed logs
- Verify all dependencies are installed correctly

## Development Roadmap

### Phase 1 (Current): Salaried Employees
- Form-16 processing
- ITR-1 generation
- Basic tax optimization

### Phase 2: Freelancers & Consultants  
- Multiple income sources
- Business deductions
- ITR-4 support

### Phase 3: Full Automation
- Direct e-filing with ERI certification
- OTP-based authentication
- Automated form submission

### Phase 4: Advanced Features
- Voice input support
- Regional language support
- Mobile-first design
- Advanced tax planning

## Legal Disclaimer

This software is for informational purposes only and does not constitute professional tax advice. Always consult with a qualified Chartered Accountant for complex tax situations. Users are responsible for the accuracy of their tax filings.

## License

This project is intended for personal and educational use. Commercial use requires appropriate licensing.

## Support

For technical support or feature requests, please check the documentation or consult with a developer familiar with the codebase.
        """
        
        with open(self.base_dir / "README.md", "w") as f:
            f.write(readme_content)
        
        print("✓ Created comprehensive README.md")
    
    def check_file_integration(self):
        """Check integration with existing files"""
        self.print_step(8, "Checking File Integration")
        
        # Check if we need to update imports in existing files
        integration_notes = []
        
        # Check if user's files need updates
        existing_files = ["extractor.py", "ai_agent.py", "itd_mapper.py"]
        
        for file in existing_files:
            file_path = self.base_dir / file
            if file_path.exists():
                print(f"✓ Found existing {file}")
                integration_notes.append(f"Your existing {file} can be replaced with enhanced_{file} for better functionality")
        
        if integration_notes:
            print("\n📝 Integration Notes:")
            for note in integration_notes:
                print(f"  - {note}")
        
        return integration_notes
    
    def run_setup(self):
        """Run the complete setup process"""
        print("🤖 AI Tax Filing Agent - Setup & Installation")
        print("This will set up your enhanced tax filing system")
        print("")
        
        try:
            # Run setup steps
            self.create_directories()
            self.create_requirements_file()
            found_files, missing_files = self.check_existing_files()
            self.create_env_file()
            self.create_gitignore()
            self.create_startup_script()
            self.create_readme()
            integration_notes = self.check_file_integration()
            
            # Install dependencies (optional)
            install_deps = input("\nWould you like to install Python dependencies now? (y/n): ").lower()
            if install_deps == 'y':
                self.install_dependencies()
            
            # Final summary
            self.print_step(9, "Setup Complete!")
            
            print("✅ Setup completed successfully!")
            print("")
            print("📋 Next Steps:")
            print("1. Install dependencies: pip install -r requirements.txt")
            print("2. Set up LM Studio with a language model on localhost:1234 (optional)")
            print("3. Run the application:")
            print("   - Windows: double-click start_windows.bat")
            print("   - Linux/Mac: ./start_unix.sh")
            print("   - Or: streamlit run enhanced_main_app.py")
            print("")
            print("🌐 The application will be available at http://localhost:8501")
            print("")
            print("📖 Check README.md for detailed instructions and troubleshooting")
            
            if missing_files:
                print("")
                print("⚠️  Missing files from your original codebase:")
                for file in missing_files:
                    print(f"   - {file}")
                print("   These have been replaced with enhanced versions in the artifacts above")
            
            if integration_notes:
                print("")
                print("💡 Integration recommendations:")
                for note in integration_notes:
                    print(f"   - {note}")
        
        except Exception as e:
            print(f"❌ Setup failed with error: {e}")
            print("Please check the error message and try again")

def main():
    """Main setup function"""
    setup = TaxAgentSetup()
    setup.run_setup()

if __name__ == "__main__":
    main()

# Quick test function
def test_installation():
    """Test if the installation is working"""
    print("🧪 Testing installation...")
    
    try:
        import streamlit as st
        print("✓ Streamlit installed")
    except ImportError:
        print("❌ Streamlit not installed")
        return False
    
    try:
        import pdfplumber
        print("✓ PDF processing libraries available")
    except ImportError:
        print("❌ PDF processing libraries missing")
        return False
    
    try:
        import pandas as pd
        print("✓ Pandas available")
    except ImportError:
        print("❌ Pandas not installed")
        return False
    
    # Check directory structure
    required_dirs = ["clients", "exports", "logs"]
    for dir_name in required_dirs:
        if Path(dir_name).exists():
            print(f"✓ Directory {dir_name} exists")
        else:
            print(f"❌ Directory {dir_name} missing")
            return False
    
    print("✅ Installation test passed!")
    return True

if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "test":
    test_installation()
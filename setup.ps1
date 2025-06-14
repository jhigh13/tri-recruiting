###############################################################
# PowerShell script to set up the development environment
# Updated for SQLite (no PostgreSQL/Docker required)
# Run this script to initialize your local development environment
###############################################################

Write-Host "Setting up USA Triathlon Talent ID Pipeline environment..." -ForegroundColor Green

# Check if Python 3.11+ is available
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Found Python: $pythonVersion" -ForegroundColor Yellow
    # Extract version number and check if it's 3.11+
    if ($pythonVersion -match "Python (\d+)\.(\d+)") {
        $major = [int]$matches[1]
        $minor = [int]$matches[2]
        if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 11)) {
            Write-Host "Error: Python 3.11 or higher is required" -ForegroundColor Red
            exit 1
        }
    }
} catch {
    Write-Host "Error: Python not found. Please install Python 3.11+" -ForegroundColor Red
    exit 1
}

# Create virtual environment
Write-Host "Creating virtual environment..." -ForegroundColor Yellow
python -m venv .venv

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
.\.venv\Scripts\Activate.ps1

# Upgrade pip
Write-Host "Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

# Install dependencies
Write-Host "Installing dependencies from requirements.txt..." -ForegroundColor Yellow
pip install -r requirements.txt

# Install pre-commit hooks
Write-Host "Setting up pre-commit hooks..." -ForegroundColor Yellow
pre-commit install

# Create necessary directories
Write-Host "Creating project directories..." -ForegroundColor Yellow
$directories = @(
    "etl",
    "db", 
    "config",
    "reports",
    "automation",
    "data",
    "tests",
    "logs"
)

foreach ($dir in $directories) {
    if (!(Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir | Out-Null
        Write-Host "Created directory: $dir" -ForegroundColor Gray
    }
}

# Create .env file with SQLite configuration (no PostgreSQL)
if (!(Test-Path ".env")) {
    @"
# Database Configuration - Using SQLite for local development
DATABASE_URL=sqlite:///data/tri_talent.db

# Web Scraping Configuration
CHROMEDRIVER_PATH=C:\chromedriver\chromedriver.exe
USER_AGENT=USA-Triathlon-TalentID-Pipeline/1.0

# Rate Limiting (seconds between requests)
SCRAPE_DELAY=2
MAX_RETRIES=3

# Optional: AI Integration (for future use)
OPENAI_API_KEY=your_openai_api_key_here

# Pipeline Configuration
YEARS_TO_SCRAPE=5
MAX_ATHLETES_PER_EVENT=500
"@ | Out-File -FilePath ".env" -Encoding UTF8
    Write-Host "Created .env file with SQLite configuration." -ForegroundColor Yellow
}

Write-Host "`nSetup complete! Next steps:" -ForegroundColor Green
Write-Host "1. Update ChromeDriver path in .env file if needed" -ForegroundColor White
Write-Host "2. Run database setup: python db/create_tables.py" -ForegroundColor White
Write-Host "3. Load time standards: python etl/standards_loader.py" -ForegroundColor White

# NOTE: If using webdriver-manager, you can omit manual Chromedriver setup and use its auto-download in code.
Write-Host "NOTE: Selenium will auto-manage ChromeDriver via webdriver-manager; no CHROMEDRIVER_PATH required." -ForegroundColor Cyan

Write-Host "`nSetup complete! Next steps:" -ForegroundColor Green
Write-Host "1. Update ChromeDriver path in .env file if needed" -ForegroundColor White
Write-Host "2. Run database setup: python db/create_tables.py" -ForegroundColor White
Write-Host "3. Load time standards: python etl/standards_loader.py" -ForegroundColor White
Write-Host "`nTo activate the environment in the future, run:" -ForegroundColor Green
Write-Host ".\.venv\Scripts\Activate.ps1" -ForegroundColor White
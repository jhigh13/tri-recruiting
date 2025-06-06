# PowerShell script to start the database with error handling
# Supports both Docker and local PostgreSQL installations

Write-Host "Starting USA Triathlon Talent ID Database..." -ForegroundColor Green

# Check if Docker is available
$dockerAvailable = $false
try {
    $dockerVersion = docker --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        $dockerAvailable = $true
        Write-Host "Found Docker: $dockerVersion" -ForegroundColor Yellow
    }
} catch {
    Write-Host "Docker not found in PATH" -ForegroundColor Yellow
}

if ($dockerAvailable) {
    # Use Docker Compose
    Write-Host "Starting PostgreSQL with Docker..." -ForegroundColor Yellow
    
    # Check if Docker Desktop is running
    try {
        docker info 2>$null | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Docker Desktop is not running. Please start Docker Desktop and try again." -ForegroundColor Red
            Write-Host "1. Open Docker Desktop application" -ForegroundColor White
            Write-Host "2. Wait for it to start completely" -ForegroundColor White
            Write-Host "3. Run this script again" -ForegroundColor White
            exit 1
        }
    } catch {
        Write-Host "Cannot connect to Docker. Please ensure Docker Desktop is running." -ForegroundColor Red
        exit 1
    }
    
    # Start the PostgreSQL container
    docker compose -f docker/postgres-compose.yml up -d
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Success! PostgreSQL container started successfully!" -ForegroundColor Green
        Write-Host "Database will be available at: localhost:5432" -ForegroundColor White
        Write-Host "Database: tri_talent_db" -ForegroundColor White
        Write-Host "Username: tri_user" -ForegroundColor White
        Write-Host "Password: tri_password" -ForegroundColor White
        
        # Wait a moment for the container to be ready
        Write-Host "Waiting for database to be ready..." -ForegroundColor Yellow
        Start-Sleep -Seconds 10
        
        Write-Host "Next step: Initialize the database schema" -ForegroundColor Green
        Write-Host "Run: python db/create_tables.py" -ForegroundColor White
    } else {
        Write-Host "Failed to start PostgreSQL container" -ForegroundColor Red
        exit 1
    }
    
} else {
    # Docker not available - provide alternatives
    Write-Host "Docker not found. Please choose an option:" -ForegroundColor Red
    Write-Host ""
    Write-Host "Option 1 - Install Docker Desktop (Recommended):" -ForegroundColor Yellow
    Write-Host "1. Download from: https://www.docker.com/products/docker-desktop/" -ForegroundColor White
    Write-Host "2. Install and restart your computer" -ForegroundColor White
    Write-Host "3. Start Docker Desktop" -ForegroundColor White
    Write-Host "4. Run this script again" -ForegroundColor White
    Write-Host ""
    Write-Host "Option 2 - Use Local PostgreSQL:" -ForegroundColor Yellow
    Write-Host "1. Install PostgreSQL from: https://www.postgresql.org/download/windows/" -ForegroundColor White
    Write-Host "2. Create database tri_talent_db with user tri_user" -ForegroundColor White
    Write-Host "3. Update .env file with your local connection string" -ForegroundColor White
    Write-Host "4. Run: python db/create_tables.py" -ForegroundColor White
    Write-Host ""
    Write-Host "Option 3 - Use Cloud Database:" -ForegroundColor Yellow
    Write-Host "1. Set up PostgreSQL on AWS RDS, Azure, or similar" -ForegroundColor White
    Write-Host "2. Update .env file with cloud connection string" -ForegroundColor White
    Write-Host "3. Run: python db/create_tables.py" -ForegroundColor White
}

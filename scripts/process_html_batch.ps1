# Batch HTML Processing Script for TFRRS Data
# Usage: .\scripts\process_html_batch.ps1

param(
    [string]$HtmlDirectory = "data\html",
    [switch]$Verbose
)

Write-Host "=== TFRRS HTML Batch Processor ===" -ForegroundColor Green
Write-Host "Processing HTML files from: $HtmlDirectory" -ForegroundColor Yellow

# Create directory if it doesn't exist
if (!(Test-Path $HtmlDirectory)) {
    New-Item -ItemType Directory -Path $HtmlDirectory -Force
    Write-Host "Created directory: $HtmlDirectory" -ForegroundColor Yellow
}

# Find all HTML files
$htmlFiles = Get-ChildItem -Path $HtmlDirectory -Filter "*.html" -File

if ($htmlFiles.Count -eq 0) {
    Write-Host "No HTML files found in $HtmlDirectory" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please save TFRRS pages as HTML files in this directory:" -ForegroundColor Yellow
    Write-Host "1. Navigate to TFRRS qualifying lists"
    Write-Host "2. Right-click → Save as → HTML"
    Write-Host "3. Save to: $HtmlDirectory"
    Write-Host "4. Name format: event_gender_year.html (e.g., 800m_men_2025.html)"
    exit 1
}

Write-Host "Found $($htmlFiles.Count) HTML files to process:" -ForegroundColor Green

$totalAthletes = 0
$processedFiles = 0
$failedFiles = 0

foreach ($file in $htmlFiles) {
    Write-Host ""
    Write-Host "Processing: $($file.Name)" -ForegroundColor Cyan
    
    try {
        # Run the HTML processor
        $result = python -m etl.tfrrs_html_processor --file $file.FullName 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            $processedFiles++
            
            # Extract athlete count from output
            $athleteMatch = $result | Select-String "Successfully stored (\d+) athletes"
            if ($athleteMatch) {
                $count = [int]$athleteMatch.Matches[0].Groups[1].Value
                $totalAthletes += $count
                Write-Host "✅ Success: $count athletes stored" -ForegroundColor Green
            } else {
                Write-Host "✅ Processed (athlete count unknown)" -ForegroundColor Green
            }
        } else {
            $failedFiles++
            Write-Host "❌ Failed to process $($file.Name)" -ForegroundColor Red
            if ($Verbose) {
                Write-Host $result -ForegroundColor Red
            }
        }
    } catch {
        $failedFiles++
        Write-Host "❌ Error processing $($file.Name): $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "=== BATCH PROCESSING COMPLETE ===" -ForegroundColor Green
Write-Host "Files processed: $processedFiles" -ForegroundColor Green
Write-Host "Files failed: $failedFiles" -ForegroundColor $(if ($failedFiles -gt 0) { "Red" } else { "Green" })
Write-Host "Total athletes stored: $totalAthletes" -ForegroundColor Green

if ($totalAthletes -gt 0) {
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "1. Verify data in database"
    Write-Host "2. Proceed to Step 5: SwimCloud scraper"
    Write-Host "3. Run matching algorithm"
}

# Show database summary
Write-Host ""
Write-Host "Database Summary:" -ForegroundColor Cyan
python -c "from db.db_connection import get_engine; from db.models import Runner; from sqlalchemy.orm import Session; engine = get_engine(); session = Session(engine); runners = session.query(Runner).all(); print(f'Total runners in database: {len(runners)}'); session.close()"

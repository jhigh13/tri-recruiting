# Manual TFRRS Data Collection Guide

## Quick HTML Saving Method

### Step 1: Navigate to TFRRS Pages
1. Go to https://www.tfrrs.org
2. Navigate to: `Collegiate` → `Qualifying Lists` → `Division I`
3. Select your target events (800m, 1500m, 5000m, etc.)

### Step 2: Save HTML Files
**Chrome/Edge:**
1. Right-click on page → `Save as...`
2. Choose `Webpage, Complete` or `HTML Only`
3. Save to: `c:\Projects\tri-recruiting\data\html\`
4. Name format: `{event}_{gender}_{year}.html`
   - Example: `800m_men_2025.html`

**Firefox:**
1. Right-click → `Save Page As...`
2. Choose `Web Page, complete` or `Web Page, HTML only`

### Step 3: Process Saved Files
```powershell
# Process single file
python -m etl.tfrrs_html_processor --file "data/html/800m_men_2025.html"

# Process multiple files (batch script)
.\scripts\process_html_batch.ps1
```

## Target URLs for Manual Collection

### Men's Events
- 800m: https://www.tfrrs.org/lists/4706/2025_NCAA_Division_I_Outdoor_Qualifying_List
- 1500m: https://www.tfrrs.org/lists/4708/2025_NCAA_Division_I_Outdoor_Qualifying_List
- 5000m: https://www.tfrrs.org/lists/4712/2025_NCAA_Division_I_Outdoor_Qualifying_List
- 10000m: https://www.tfrrs.org/lists/4713/2025_NCAA_Division_I_Outdoor_Qualifying_List
- 3000m Steeplechase: https://www.tfrrs.org/lists/4714/2025_NCAA_Division_I_Outdoor_Qualifying_List

### Women's Events
- 800m: https://www.tfrrs.org/lists/4727/2025_NCAA_Division_I_Outdoor_Qualifying_List
- 1500m: https://www.tfrrs.org/lists/4729/2025_NCAA_Division_I_Outdoor_Qualifying_List
- 5000m: https://www.tfrrs.org/lists/4733/2025_NCAA_Division_I_Outdoor_Qualifying_List
- 10000m: https://www.tfrrs.org/lists/4734/2025_NCAA_Division_I_Outdoor_Qualifying_List
- 3000m Steeplechase: https://www.tfrrs.org/lists/4735/2025_NCAA_Division_I_Outdoor_Qualifying_List

## Efficiency Tips

### Browser Extensions
- **Save All Resources**: Browser extension to batch save pages
- **Batch Link Opener**: Open multiple TFRRS URLs in tabs
- **Auto Refresh**: If you need to wait for data updates

### Keyboard Shortcuts
- `Ctrl+S` → Quick save
- `Ctrl+Shift+S` → Save as (choose location)
- `F5` → Refresh if page doesn't load properly

"""
Simple test to check if Selenium is working and can access TFRRS.
"""
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

def test_basic_access():
    """Test basic Selenium access to TFRRS."""
    print("Creating Chrome driver...")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run headless for testing
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        print("Chrome driver created successfully!")
        
        url = "https://tf.tfrrs.org/lists/4515/2024_NCAA_Division_I_Rankings_FINAL"
        print(f"Loading URL: {url}")
        
        driver.set_page_load_timeout(30)
        driver.get(url)
        
        print("Page loaded, checking content...")
        
        # Check page title
        title = driver.title
        print(f"Page title: {title}")
        
        # Check for performance rows
        rows = driver.find_elements(By.CLASS_NAME, "performance-list-row")
        print(f"Found {len(rows)} performance rows")
        
        # Check if we're blocked
        page_text = driver.page_source.lower()
        if "access denied" in page_text or "forbidden" in page_text:
            print("WARNING: Page appears to be blocked!")
        
        print("Test completed successfully!")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if 'driver' in locals():
            driver.quit()
            print("Driver closed.")

if __name__ == "__main__":
    test_basic_access()

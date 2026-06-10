import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

options = Options()
options.add_argument("--headless")
options.add_argument("--window-size=1920,1080")
options.add_argument("--lang=fr")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
options.add_argument('--disable-extensions')

driver = webdriver.Chrome(options=options)
driver.get("https://maps.google.com/")
time.sleep(2)

print("Title:", driver.title)

# Consent
try:
    WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, 'button')))
    buttons = driver.find_elements(By.TAG_NAME, "button")
    for btn in buttons:
        if btn.text and ("Tout refuser" in btn.text or "Refuser tout" in btn.text):
            btn.click()
            print("Clicked consent button")
            time.sleep(1.5)
            break
except Exception as e:
    print("Consent error:", e)

# Search
try:
    try:
        text_input = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, '//*[@id="ucc-1"]')))
    except:
        text_input = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.NAME, 'q')))
    
    text_input.send_keys("Plombier Paris")
    text_input.send_keys(Keys.RETURN)
    print("Search submitted")
    time.sleep(5)
except Exception as e:
    print("Search input error:", e)

# Scroll
height = driver.execute_script("""
    const divs = document.querySelectorAll("h1");
    const targetDiv = Array.from(divs).find(div => div.textContent.includes("Résultats"));
    if (targetDiv) {
        const elementScroll = targetDiv.parentElement.parentElement.parentElement.parentElement;
        return elementScroll.scrollHeight;
    }
    return 0;
""")
print("Height via h1:", height)

if height == 0:
    height2 = driver.execute_script("""
        let scrollable = document.querySelector('div[role="feed"]');
        if(scrollable) return scrollable.scrollHeight;
        return 0;
    """)
    print("Height via role=feed:", height2)

results = driver.find_elements(By.CSS_SELECTOR, 'div[role="article"]')
print(f"Results found (article): {len(results)}")
if len(results) == 0:
    results = driver.find_elements(By.CSS_SELECTOR, 'a.hfpxzc')
    print(f"Results found (hfpxzc): {len(results)}")

driver.save_screenshot("screenshot2.png")
driver.quit()

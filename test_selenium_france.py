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

driver = webdriver.Chrome(options=options)
driver.get("https://maps.google.com/")
time.sleep(2)

try:
    buttons = driver.find_elements(By.TAG_NAME, "button")
    for btn in buttons:
        if btn.text and ("Tout refuser" in btn.text or "Refuser tout" in btn.text):
            btn.click()
            time.sleep(1.5)
            break
except Exception: pass

text_input = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.NAME, 'q')))
text_input.send_keys("Plombier France")
text_input.send_keys(Keys.RETURN)
time.sleep(5)

results = driver.find_elements(By.CSS_SELECTOR, 'div[role="article"]')
print(f"Results for 'Plombier France': {len(results)}")
driver.quit()

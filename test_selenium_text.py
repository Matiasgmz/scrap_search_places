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

driver = webdriver.Chrome(options=options)
driver.get("https://maps.google.com/")
time.sleep(2)

try:
    WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, 'button')))
    buttons = driver.find_elements(By.TAG_NAME, "button")
    for btn in buttons:
        if btn.text and ("Tout refuser" in btn.text or "Refuser tout" in btn.text):
            btn.click()
            time.sleep(1.5)
            break
except Exception: pass

text_input = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.NAME, 'q')))
text_input.send_keys("Plombier Paris")
text_input.send_keys(Keys.RETURN)
time.sleep(5)

articles = driver.find_elements(By.CSS_SELECTOR, 'div[role="article"]')
print(f"div[role=article]: {len(articles)}")
if len(articles) > 0:
    print("Article 0 text:", repr(articles[0].text[:100]))

feed = driver.find_element(By.CSS_SELECTOR, 'div[role="feed"]')
children = feed.find_elements(By.XPATH, "./div")
for c in children[:5]:
    print("Feed child text:", repr(c.text[:50]))

links = driver.find_elements(By.CSS_SELECTOR, 'a.hfpxzc')
print(f"a.hfpxzc: {len(links)}")
if len(links) > 0:
    print("Link 0 aria-label:", links[0].get_attribute("aria-label"))
    print("Link 0 href:", links[0].get_attribute("href"))

driver.quit()

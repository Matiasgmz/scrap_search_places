import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument("--headless")
options.add_argument("--window-size=1920,1080")
options.add_argument("--lang=fr")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

driver = webdriver.Chrome(options=options)
driver.get("https://maps.google.com/")
time.sleep(3)

print("Title:", driver.title)
buttons = driver.find_elements(By.TAG_NAME, "button")
for b in buttons:
    print("Button:", b.text.replace("\n", " "))
driver.quit()

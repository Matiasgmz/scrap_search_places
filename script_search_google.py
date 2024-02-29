from selenium import webdriver
import time
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
import pandas as pd
import re
import requests

data = []
url = input("Entrez l'URL de la recherche Google Lieux: ")
chrome_options = Options()


# Activer le mode navigation privée
chrome_options.add_argument("--incognito")

driver = webdriver.Chrome(options=chrome_options)

driver.get(
    url
)
def chercher_adresses_email(url_web_site):
    # Récupérer le contenu de la page web

    response = requests.get(url_web_site, verify=False)
    contenu = ""
    if response.status_code == 200:
        contenu = response.text
         
    pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    adresses_email = re.findall(pattern, contenu)
  
    if not adresses_email: adresses_email = ""
    return adresses_email

time.sleep(2)

try:
    button_dismiss_notice = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "W0wltc"))
    )
    button_dismiss_notice.click()
    for i in range(5):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

    while True:
        try:
            button_more_result = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "[aria-label='Plus de résultats']")
                )
            )
            button_more_result.click()
            time.sleep(2)  
        except:
            print("Bouton 'Plus de résultats' non trouvé ou non cliquable.")
            break

    table_content_data = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".rllt__details"))
    )

    for content in table_content_data:
        div_ancestor = content.find_element(By.XPATH, "ancestor::div[7]")

        try:
            link_website = div_ancestor.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
            if link_website.startswith("https://www.google.com"): 
                link_website = ""
                adresses_email = ""
            else:
                adresses_email = chercher_adresses_email(link_website)
        except NoSuchElementException:
            link_website = ""
            adresses_email = ""
        
        name = content.find_element(By.CSS_SELECTOR, "div > span").text
        try:
            content_info_element = content.find_element(
                By.CSS_SELECTOR, "div:nth-child(3)"
            ).text
            print(name, content_info_element, link_website)

        except NoSuchElementException:
            pass
        data.append(
            {
                "Nom": name,
                "Info": content_info_element,
                "Site Web": link_website,
                "adresses_email": adresses_email
            }
        )


finally:
    search_query = url.split("q=")[1].split("&")[0] 
    content_query = search_query.split("+")
    name_concat = ""
    for n in content_query:
        name_concat += n + "_"
    name_file = name_concat + "search_google.xlsx"
    df = pd.DataFrame(data)      
    df.to_excel(name_file, index=False) 
    driver.quit()


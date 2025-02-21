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
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

text_search = input("Entrez votre recherche: ")

data = []
url = "https://maps.google.com/"
chrome_options = Options()

# chrome_options.add_argument("--incognito")
chrome_options.add_argument("--disable-search-engine-choice-screen")


driver = webdriver.Chrome(options=chrome_options)

driver.get(
    url
)
def chercher_adresses_email(url_web_site):
    # Récupérer les addresses email
    contenu = ""

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    
    response = requests.get(url_web_site, headers=headers, verify=False)
    if response.status_code == 200:
        contenu = response.text
         
    pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    adresses_email = re.findall(pattern, contenu)
  
    if not adresses_email: adresses_email = ""
    return adresses_email

time.sleep(2)
try:

    # dismiss notice    
    button_dismiss_notice = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="yDmH0d"]/c-wiz/div/div/div/div[2]/div[1]/div[3]/div[1]/div[1]/form[1]/div/div/button/span[6]'))
    )
    button_dismiss_notice.click()

        # enter text search
    text_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="searchboxinput"]'))
    )
    text_input.send_keys(text_search)
    text_input.send_keys(Keys.RETURN)


    time.sleep(2)
 
    driver.execute_script('const divs = document.querySelectorAll("h1"); const targetDiv = Array.from(divs).find(div => div.textContent.includes("Résultats")); const elementScroll = targetDiv.parentElement.parentElement.parentElement.parentElement; elementScroll.scrollTop = elementScroll.scrollHeight;')

    last_height = 0  # Stocke la hauteur précédente

    while True:
        # Exécuter le script JavaScript pour trouver et faire défiler l'élément
        height = driver.execute_script('''
            const divs = document.querySelectorAll("h1");
            const targetDiv = Array.from(divs).find(div => div.textContent.includes("Résultats"));
            if (targetDiv) {
                const elementScroll = targetDiv.parentElement.parentElement.parentElement.parentElement;
                elementScroll.scrollTop = elementScroll.scrollHeight;
                return elementScroll.scrollHeight;
            }
            return 0;
        ''')

        # Si la hauteur de la page ne change plus, arrêter la boucle
        if height == last_height:
            print("Plus de nouveaux résultats à charger.")
            break
        
        last_height = height  # Mettre à jour la dernière hauteur
        time.sleep(2)  # Pause pour laisser le temps aux résultats de charger


    table_content_data = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.XPATH, "//*[@id=\"QA0Szd\"]/div/div/div[1]/div[2]/div/div[1]/div/div/div[1]/div[1]/div"))
    )
    print (table_content_data)
    

    for content in table_content_data:
        # div_ancestor = content.find_element(By.XPATH, "ancestor::div[7]")

        # try:
        #     link_website = content.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
        #     # if link_website.startswith("https://www.google.com"): 
        #     #     link_website = ""
        #     #     adresses_email = ""
        #     # else:
        #     #     adresses_email = chercher_adresses_email(link_website)
        # except NoSuchElementException:
        #     link_website = ""
        #     adresses_email = ""
        # print(link_website)
        
        try: 
            name = content.find_element(By.CSS_SELECTOR, ".fontHeadlineSmall").text
        except NoSuchElementException:
            name = ""    
        print(name)

        try: 
           link_website = content.find_element(By.CSS_SELECTOR, '[data-value="Site Web"]').get_attribute("href")
           adresses_email = chercher_adresses_email(link_website)

        except NoSuchElementException:
            link_website = ""
            adresses_email = ""
        # print(link_website)
        # try:
        #     content_info_element = content.find_element(
        #         By.CSS_SELECTOR, "div:nth-child(3)"
        #     ).text
        #     print(name, content_info_element, link_website)

        # except NoSuchElementException:
        #     pass
        if name != "":
            data.append(
                {
                    "Nom": name,
                    # "Info": content_info_element,
                    "Site Web": link_website,
                    "adresses_email": adresses_email
                }
            )


finally:
    name_concat = text_search.replace(" ", "_")
    name_file = name_concat.lower() + "_search_google.xlsx"
    df = pd.DataFrame(data)      
    df.to_excel(name_file, index=False) 
    driver.quit()


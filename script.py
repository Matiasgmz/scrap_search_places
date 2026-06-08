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
from colorama import Fore, init

init(autoreset=True)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def separator():
    print(Fore.BLUE + "=" * 100)


def log_info(message):
    print(Fore.CYAN + f"[INFO] {message}")


def log_success(message):
    print(Fore.GREEN + f"[OK] {message}")


def log_warning(message):
    print(Fore.YELLOW + f"[ATTENTION] {message}")


def log_error(message):
    print(Fore.RED + f"[ERREUR] {message}")


def afficher_resultat(index, total, nom, site_web, emails, infos):
    separator()

    print(Fore.MAGENTA + f" RESULTAT {index}/{total} ".center(100, "#"))

    print(Fore.WHITE + f"🏢 Nom       : {nom}")

    if site_web:
        print(Fore.CYAN + f"🌐 Site Web  : {site_web}")
    else:
        print(Fore.YELLOW + "🌐 Site Web  : Non trouvé")

    if emails:
        print(Fore.GREEN + f"📧 Emails    : {', '.join(emails)}")
    else:
        print(Fore.YELLOW + "📧 Emails    : Aucun trouvé")

    print(Fore.WHITE + f"📋 Infos     : {infos}")
    separator()


def chercher_adresses_email(url_web_site):
    contenu = ""

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        response = requests.get(
            url_web_site,
            headers=headers,
            verify=False,
            timeout=10
        )

        response.raise_for_status()
        contenu = response.text

    except requests.exceptions.RequestException as e:
        log_error(f"Impossible d'accéder à : {url_web_site}")
        log_error(str(e))
        return []

    pattern = r'\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}\\b'
    emails = list(set(re.findall(pattern, contenu)))

    if emails:
        log_success(f"{len(emails)} email(s) trouvé(s)")

    return emails


text_search = input("Entrez votre recherche : ")

separator()
log_info("Lancement du scraping Google Maps")
log_info(f"Recherche : {text_search}")
separator()

data = []

url = "https://maps.google.com/"

chrome_options = Options()
chrome_options.add_argument("--disable-search-engine-choice-screen")

driver = webdriver.Chrome(options=chrome_options)

driver.get(url)

time.sleep(2)

try:

    try:
        button_dismiss_notice = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    '//*[@id="yDmH0d"]/c-wiz/div/div/div/div[2]/div[1]/div[3]/div[1]/div[1]/form[1]/div/div/button/span[6]'
                )
            )
        )
        button_dismiss_notice.click()
        log_success("Fenêtre de consentement fermée")
    except Exception:
        log_warning("Fenêtre de consentement non trouvée")

    text_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="ucc-1"]'))
    )

    text_input.send_keys(text_search)
    text_input.send_keys(Keys.RETURN)

    log_info("Recherche lancée...")

    time.sleep(5)

    last_height = 0

    while True:

        height = driver.execute_script("""
            const divs = document.querySelectorAll("h1");
            const targetDiv = Array.from(divs).find(div => div.textContent.includes("Résultats"));
            if (targetDiv) {
                const elementScroll = targetDiv.parentElement.parentElement.parentElement.parentElement;
                elementScroll.scrollTop = elementScroll.scrollHeight;
                return elementScroll.scrollHeight;
            }
            return 0;
        """)

        if height == last_height:
            log_success("Tous les résultats semblent chargés")
            break

        last_height = height
        time.sleep(2)

    results = driver.find_elements(
        By.CSS_SELECTOR,
        'div[role="article"]'
    )

    log_success(f"{len(results)} résultats détectés")

    for index, content in enumerate(results, start=1):

        log_info(f"Analyse du résultat {index}/{len(results)}")

        name = ""
        link_website = ""
        adresses_email = []
        content_info_element = ""

        try:
            name = content.find_element(
                By.CSS_SELECTOR,
                ".fontHeadlineSmall"
            ).text
        except NoSuchElementException:
            pass

        try:
            link_website = content.find_element(
                By.CSS_SELECTOR,
                '[data-value="Site Web"]'
            ).get_attribute("href")

            if link_website:
                adresses_email = chercher_adresses_email(link_website)

        except NoSuchElementException:
            pass

        try:
            content_info_element = content.find_element(
                By.CSS_SELECTOR,
                "div:nth-child(3)"
            ).text
        except NoSuchElementException:
            pass

        afficher_resultat(
            index=index,
            total=len(results),
            nom=name,
            site_web=link_website,
            emails=adresses_email,
            infos=content_info_element
        )

        if name:

            data.append({
                "Nom": name,
                "Info": content_info_element,
                "Site Web": link_website,
                "adresses_email": ", ".join(adresses_email)
            })

finally:

    separator()
    log_info("Création du fichier Excel...")

    name_concat = text_search.replace(" ", "_")
    name_file = name_concat.lower() + "_search_google.xlsx"

    df = pd.DataFrame(data)
    df.to_excel(name_file, index=False)

    log_success(f"Fichier créé : {name_file}")
    log_success(f"{len(data)} entreprises sauvegardées")

    separator()

    driver.quit()

    input("\\nAppuyez sur Entrée pour fermer...")

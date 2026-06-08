from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import time
import urllib3
from core.osint import enrichir_contact, filter_best_email, filter_best_phone
from core.proxies import ProxyManager
import re
import logging
import concurrent.futures

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class GoogleMapsScraper:
    def __init__(self, headless=False, proxy=None):
        self.headless = headless
        self.proxy = ProxyManager.format_proxy(proxy)
        self.driver = None

    def _init_driver(self):
        chrome_options = Options()
        chrome_options.add_argument("--disable-search-engine-choice-screen")
        chrome_options.add_argument("--lang=fr") 
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Quelques optimisations légères
        chrome_options.add_argument('--disable-extensions')
        
        if self.headless:
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--window-size=1920,1080")
            
        if self.proxy:
            chrome_options.add_argument(f'--proxy-server={self.proxy}')
        
        self.driver = webdriver.Chrome(options=chrome_options)

    def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            finally:
                self.driver = None

    def scrape(self, country, region, domain, callback=None, max_scroll_attempts=15, filters=None):
        if not self.driver:
            self._init_driver()

        search_query = f"{domain} {region} {country}".strip()
        url = "https://maps.google.com/"
        
        try:
            self.driver.get(url)
            time.sleep(2)
        except Exception as e:
            if callback: callback({"status": "error", "message": f"Erreur de connexion (Proxy mort ?) : {str(e)}"})
            return []

        # Consentement
        try:
            button_dismiss_notice = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//*[@id="yDmH0d"]/c-wiz/div/div/div/div[2]/div[1]/div[3]/div[1]/div[1]/form[1]/div/div/button/span[6]')
                )
            )
            button_dismiss_notice.click()
            time.sleep(1)
        except Exception:
            pass

        # Recherche
        try:
            text_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="ucc-1"]'))
            )
        except Exception:
            try:
                text_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.NAME, 'q'))
                )
            except Exception:
                if callback: callback({"status": "error", "message": "Impossible de trouver la barre de recherche. Google a peut-être bloqué l'IP (Captcha)."})
                return []

        text_input.send_keys(search_query)
        text_input.send_keys(Keys.RETURN)
        
        time.sleep(5) 

        # Scroll
        last_height = 0
        attempts = 0
        while attempts < max_scroll_attempts:
            try:
                height = self.driver.execute_script("""
                    const divs = document.querySelectorAll("h1");
                    const targetDiv = Array.from(divs).find(div => div.textContent.includes("Résultats"));
                    if (targetDiv) {
                        const elementScroll = targetDiv.parentElement.parentElement.parentElement.parentElement;
                        elementScroll.scrollTop = elementScroll.scrollHeight;
                        return elementScroll.scrollHeight;
                    }
                    return 0;
                """)
                if height == last_height and height != 0:
                    break
                if height == 0:
                    self.driver.execute_script("""
                        let scrollable = document.querySelector('div[role="feed"]');
                        if(scrollable) scrollable.scrollTop = scrollable.scrollHeight;
                    """)
                last_height = height
                time.sleep(2)
                attempts += 1
            except Exception as e:
                break # Arrêter de scroller si ça crashe

        # Récupération
        try:
            results = self.driver.find_elements(By.CSS_SELECTOR, 'div[role="article"]')
            if not results:
                if callback: callback({"status": "error", "message": "Aucun résultat trouvé sur la page (Sélecteur CSS obsolète ou blocage Google)."})
                return []
        except Exception as e:
            if callback: callback({"status": "error", "message": "Échec de récupération des articles."})
            return []
        
        extracted_data = []

        # === MULTITHREADING (OSINT & Extraction de la page) ===
        def process_element(index, content):
            try:
                name = ""
                link_website = ""
                place_id = ""
                adresse = ""
                note = None
                nombre_avis = None
                
                try:
                    name = content.find_element(By.CSS_SELECTOR, ".fontHeadlineSmall").text
                except NoSuchElementException:
                    pass
                    
                if not name:
                    name = content.get_attribute("aria-label")
                    
                if not name:
                    try:
                        name = content.find_element(By.CSS_SELECTOR, "div.qBF1Pd").text
                    except NoSuchElementException:
                        pass
                        
                if not name:
                    return {"status": "ignored", "index": index, "name": f"Élément {index}", "reason": "Pas de nom (Publicité ou Séparateur)"}

                try:
                    a_tag = content.find_element(By.CSS_SELECTOR, 'a')
                    place_id = a_tag.get_attribute("href")
                except NoSuchElementException:
                    place_id = name

                try:
                    link_website = content.find_element(By.CSS_SELECTOR, '[data-value="Site Web"]').get_attribute("href")
                except NoSuchElementException:
                    pass

                try:
                    text_content = content.text
                    note_match = re.search(r'([\d,.]+)\s*\(\s*(\d+)\s*\)', text_content)
                    if note_match:
                        note = float(note_match.group(1).replace(',', '.'))
                        nombre_avis = int(note_match.group(2))

                    lines = [line.strip() for line in text_content.split('\n') if line.strip()]
                    for line in lines:
                        if "·" in line and not "Ouvert" in line and not "Fermé" in line:
                            parts = line.split("·")
                            if len(parts) > 1:
                                adresse = parts[-1].strip()
                except Exception:
                    pass

                # Filtres préliminaires
                ignored_reason = None
                if filters:
                    if filters.get("site_web") == "Avec site web uniquement" and not link_website:
                        ignored_reason = "Pas de site web"
                    elif filters.get("site_web") == "Sans site web uniquement" and link_website:
                        ignored_reason = "Possède un site web"

                if ignored_reason:
                    return {"status": "ignored", "index": index, "name": name, "reason": ignored_reason}

                # OSINT (Requête HTTP externe via BeautifulSoup)
                contact_data = {"emails": [], "telephones": [], "boss": ""}
                try:
                    if link_website:
                        contact_data = enrichir_contact(link_website)
                except Exception as e:
                    logging.error(f"Erreur OSINT sur {link_website}: {str(e)}")

                try:
                    gm_phones = re.findall(r'(?:(?:\+|00)33|0)[1-9](?:[\s.-]?\d{2}){4}', text_content)
                    for p in gm_phones:
                        p_clean = re.sub(r'[\s.-]', '', p)
                        contact_data["telephones"].append(p_clean)
                except Exception:
                    pass
                
                contact_data["telephones"] = list(set(contact_data["telephones"]))
                final_boss = contact_data["boss"]
                final_email = filter_best_email(contact_data["emails"], final_boss)
                final_phone = filter_best_phone(contact_data["telephones"])

                lead_data = {
                    "place_id": place_id,
                    "nom": name,
                    "adresse": adresse,
                    "site_web": link_website,
                    "note": note,
                    "nombre_avis": nombre_avis,
                    "emails": final_email,
                    "telephones": final_phone,
                    "boss": final_boss
                }

                return {"status": "success", "index": index, "data": lead_data}
            except Exception as e:
                return {"status": "ignored", "index": index, "name": f"Élément {index}", "reason": f"Crash interne : {str(e)}"}

        total_results = len(results)
        
        # Lancement du ThreadPool
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            # On soumet toutes les fiches d'un coup
            future_to_index = {executor.submit(process_element, i, content): i for i, content in enumerate(results, start=1)}
            
            # Au fur et à mesure qu'un site web répond, on le traite et on l'envoie à la BDD via callback
            for future in concurrent.futures.as_completed(future_to_index):
                res = future.result()
                
                if res["status"] == "ignored":
                    if callback:
                        callback({
                            "status": "ignored",
                            "current": res["index"],
                            "total": total_results,
                            "name": res["name"],
                            "reason": res["reason"]
                        })
                elif res["status"] == "success":
                    extracted_data.append(res["data"])
                    if callback:
                        callback({
                            "status": "progress",
                            "current": res["index"],
                            "total": total_results,
                            "data": res["data"]
                        })

        return extracted_data

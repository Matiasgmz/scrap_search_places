import sqlite3
import json
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re
import threading
from bs_get_email import process_all_leads_sync

DB_PATH = "leads_v2.db"

def init_db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    cursor = conn.cursor()
    cursor.execute('PRAGMA journal_mode=WAL;')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            place_id TEXT UNIQUE,
            opportunite TEXT,
            nom TEXT,
            pays TEXT,
            region TEXT,
            domaine TEXT,
            adresse TEXT,
            site_web TEXT,
            note REAL,
            nombre_avis INTEGER,
            dirigeant TEXT,
            email TEXT,
            telephone TEXT,
            statut TEXT DEFAULT 'À contacter',
            audit_site TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS doublons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            place_id TEXT,
            nom TEXT,
            pays TEXT,
            region TEXT,
            domaine TEXT,
            telephone TEXT,
            date_tentative TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scraping_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pays TEXT,
            region TEXT,
            domaine TEXT,
            UNIQUE(pays, region, domaine)
        )
    ''')
    
    conn.commit()
    conn.close()

def clear_database():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM leads')
    cursor.execute('DELETE FROM scraping_state')
    cursor.execute('DELETE FROM doublons')
    conn.commit()
    conn.close()
    init_db()

def validate_lead_data(data):
    if not data.get("place_id"): return None
    
    email = data.get("email", "")
    if email and not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email):
        data["email"] = ""
        
    phone = data.get("telephone", "")
    if phone:
        clean_phone = re.sub(r'\D', '', phone)
        if clean_phone.startswith('33') and len(clean_phone) == 11:
            clean_phone = '0' + clean_phone[2:]
        if len(clean_phone) != 10:
            clean_phone = ""
        data["telephone"] = clean_phone
        
    return data

def fire_webhook_async(url, payload):
    try: requests.post(url, json=payload, timeout=5)
    except: pass

def save_lead(data, webhook_url=None):
    valid_data = validate_lead_data(data)
    if not valid_data: return False
    
    conn = sqlite3.connect(DB_PATH, timeout=10)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO leads (place_id, opportunite, nom, pays, region, domaine, adresse, site_web, note, nombre_avis, dirigeant, email, telephone, audit_site)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            valid_data.get("place_id"), valid_data.get("opportunite"), valid_data.get("nom"), valid_data.get("pays"), valid_data.get("region"), valid_data.get("domaine"),
            valid_data.get("adresse"), valid_data.get("site_web"), valid_data.get("note"), valid_data.get("nombre_avis"),
            valid_data.get("dirigeant"), valid_data.get("email"), valid_data.get("telephone"), valid_data.get("audit_site")
        ))
        conn.commit()
        
        # Webhook asynchrone non-bloquant pour les leads à haute valeur
        if webhook_url and valid_data.get("opportunite"):
            threading.Thread(target=fire_webhook_async, args=(webhook_url, valid_data), daemon=True).start()
            
        return True
    except sqlite3.IntegrityError:
        try:
            cursor.execute('INSERT INTO doublons (place_id, nom, pays, region, domaine, telephone) VALUES (?, ?, ?, ?, ?, ?)', 
                           (valid_data.get("place_id"), valid_data.get("nom"), valid_data.get("pays"), valid_data.get("region"), valid_data.get("domaine"), valid_data.get("telephone")))
            conn.commit()
        except: pass
        return False
    finally:
        conn.close()

def get_all_leads():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM leads ORDER BY id DESC')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_all_doublons():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT nom, region, domaine, date_tentative FROM doublons ORDER BY id DESC')
        rows = cursor.fetchall()
    except:
        rows = []
    conn.close()
    return [dict(row) for row in rows]

def save_checkpoint(pays, region, domaine):
    conn = sqlite3.connect(DB_PATH, timeout=10)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO scraping_state (pays, region, domaine) 
            VALUES (?, ?, ?)
        ''', (pays, region, domaine))
        conn.commit()
    except Exception: pass
    finally: conn.close()

def get_checkpoints(pays):
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        cursor = conn.cursor()
        cursor.execute('SELECT region, domaine FROM scraping_state WHERE pays = ?', (pays,))
        results = cursor.fetchall()
        conn.close()
        return set(results)
    except sqlite3.OperationalError:
        return set()

def update_lead_status(lead_id, new_status):
    conn = sqlite3.connect(DB_PATH, timeout=10)
    cursor = conn.cursor()
    cursor.execute('UPDATE leads SET statut = ? WHERE id = ?', (new_status, lead_id))
    conn.commit()
    conn.close()

class GoogleMapsScraper:
    def __init__(self, headless=True):
        chrome_options = Options()
        if headless: chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # V33: Bandwidth Tuning - Désactivation des médias inutiles mais préservation du CSS pour le layout
        prefs = {
            "profile.managed_default_content_settings.images": 2,
            "profile.managed_default_content_settings.plugins": 2,
            "profile.managed_default_content_settings.geolocation": 2,
            "profile.managed_default_content_settings.media_stream": 2
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        # Header réaliste d'un navigateur standard moderne (Chrome)
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        chrome_options.add_argument("accept-language=fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7")
        
        self.driver = webdriver.Chrome(options=chrome_options)

    def scrape(self, country, region, domain, max_scrolls=15, focus_no_website=False, webhook_url=None, js_rendering=False, callback=None):
        search_query = f"{domain}, {region}, {country}"
        url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}"
        
        if callback: callback({"status": "info", "message": f"Recherche de '{search_query}' sur Google Maps..."})
        try: self.driver.get(url)
        except Exception as e: raise Exception(f"Erreur d'accès réseau à Google Maps: {e}")

        # Automation avancée : Attente dynamique du DOM
        try:
            accept_button = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//button[.//span[text()='Tout accepter']] | //button[.//span[text()='Accept all']]"))
            )
            accept_button.click()
        except: pass

        results = []
        try:
            # Automation avancée : Infinite Scroll via interception XHR
            scrollable_div = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@aria-label, 'Résultats pour')] | //div[contains(@role, 'feed')]"))
            )
            last_count = 0
            for i in range(max_scrolls):
                if callback: callback({"status": "info", "message": f"Défilement de la carte en cours (Étape {i+1}/{max_scrolls})..."})
                self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_div)
                time.sleep(0.8) # Délai optimisé pour le trigger XHR de Gmaps (Vitesse Max)
                results = self.driver.find_elements(By.CSS_SELECTOR, "div.Nv2PK")
                if len(results) == last_count:
                    break
                last_count = len(results)
                if len(results) >= 120: break
        except Exception as e:
            if callback: callback({"status": "error", "message": f"Délai d'attente XHR expiré : {e}"})
            
        if not results:
            results = self.driver.find_elements(By.CSS_SELECTOR, "a.hfpxzc")
            
        extracted_data = []
        total_results = len(results)
        
        if callback: callback({"status": "info", "message": f"Fin de l'extraction Google Maps. {total_results} entreprises trouvées. Lancement des requêtes OSINT..."})
        
        # Extraction structurelle Hybride Google Maps
        raw_leads = []
        for index, content in enumerate(results, start=1):
            try:
                name, link_website, place_id, adresse = "", "", "", ""
                note, nombre_avis = None, None
                
                try: name = content.find_element(By.CSS_SELECTOR, ".fontHeadlineSmall").text
                except: pass
                if not name:
                    try: name = (content.find_element(By.CSS_SELECTOR, 'a.hfpxzc') if content.tag_name != 'a' else content).get_attribute("aria-label")
                    except: pass
                if not name:
                    try: name = content.find_element(By.CSS_SELECTOR, "div.qBF1Pd").text
                    except: pass
                        
                if not name:
                    if callback: callback({"status": "ignored", "index": index, "total": total_results, "name": f"Lead {index}", "reason": "Nom introuvable"})
                    continue

                try: place_id = content.get_attribute("href") if content.tag_name == 'a' else content.find_element(By.CSS_SELECTOR, 'a').get_attribute("href")
                except: place_id = name

                try: link_website = content.find_element(By.CSS_SELECTOR, '[data-value="Site Web"]').get_attribute("href")
                except: pass

                text_content = content.text
                try:
                    note_match = re.search(r'([\d,.]+)\s*\(\s*(\d+)\s*\)', text_content)
                    if note_match:
                        note = float(note_match.group(1).replace(',', '.'))
                        nombre_avis = int(note_match.group(2))

                    lines = [line.strip() for line in text_content.split('\n') if line.strip()]
                    for line in lines:
                        if "·" in line and not "Ouvert" in line and not "Fermé" in line:
                            parts = line.split("·")
                            if len(parts) > 1: adresse = parts[-1].strip()
                except: pass

                gm_phones = re.findall(r'(?:(?:\+|00)33|0)[1-9](?:[\s.-]?\d{2}){4}', text_content)
                
                raw_leads.append({
                    "index": index, "name": name, "place_id": place_id, "link_website": link_website,
                    "adresse": adresse, "note": note, "nombre_avis": nombre_avis, "gm_phones": gm_phones,
                    "country": country, "region": region, "domain": domain
                })
            except Exception: pass
                
        self.close()

        def osint_callback(res):
            if res["status"] == "ignored":
                if callback: callback({"status": "ignored", "current": res["index"], "total": total_results, "name": res["name"], "reason": res["reason"]})
            elif res["status"] == "success":
                lead = res["data"]
                extracted_data.append(lead)
                is_new = save_lead(lead, webhook_url=webhook_url)
                if callback: callback({"status": "progress", "current": res["index"], "total": total_results, "data": lead, "is_new": is_new})
                
        if raw_leads:
            # Passe le flag js_rendering au pipeline asynchrone OSINT Enterprise
            process_all_leads_sync(raw_leads, focus_no_website, js_rendering=js_rendering, callback=osint_callback)

        return extracted_data

    def close(self):
        try: self.driver.quit()
        except: pass

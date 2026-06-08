import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import urllib3
import unicodedata
from fake_useragent import UserAgent

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ua = UserAgent(os=['windows', 'macos'], browsers=['chrome', 'firefox', 'safari'])

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])

def extract_emails(text):
    """Extrait toutes les adresses e-mail d'un texte."""
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(pattern, text)
    return list(set([e.lower() for e in emails]))

def filter_best_email(emails, boss_name=""):
    """
    Filtre les emails pour n'en garder qu'un seul :
    1. L'email nominatif du boss (si fourni).
    2. Sinon, un email de contact direct.
    3. Exclut les emails hyper génériques (info, contact, support) si mieux est disponible.
    """
    if not emails:
        return ""
        
    generic_prefixes = ['contact', 'info', 'hello', 'support', 'admin', 'direction', 'commercial', 'agence', 'reclamation', 'personnel', 'webmaster', 'accueil']
    
    nominative_email = None
    direct_email = None
    generic_email = None

    boss_parts = []
    if boss_name:
        clean_boss = remove_accents(boss_name).lower()
        boss_parts = [p for p in clean_boss.split() if len(p) > 2]

    for email in emails:
        prefix = email.split('@')[0]
        
        is_generic = any(gen == prefix for gen in generic_prefixes) or "contact@" in email
        
        # Test si nominatif
        is_nominative = False
        if boss_parts:
            # Si au moins une partie du nom du boss est dans le préfixe
            if any(part in prefix for part in boss_parts):
                is_nominative = True

        if is_nominative:
            nominative_email = email
            break
        elif not is_generic and not direct_email:
            direct_email = email
        elif is_generic and not generic_email:
            generic_email = email

    if nominative_email:
        return nominative_email
    if direct_email:
        return direct_email
    if generic_email:
        return generic_email
        
    return emails[0] # Fallback au premier email trouvé

def extract_phones(text):
    """Extrait les numéros de téléphone."""
    pattern = r'(?:(?:\+|00)33[\s.-]{0,3}(?:\(0\)[\s.-]{0,3})?|0)[1-9](?:(?:[\s.-]?\d{2}){4}|\d{2}(?:[\s.-]?\d{3}){2})\b'
    phones = re.findall(pattern, text)
    cleaned = []
    for p in phones:
        p_clean = re.sub(r'[\s.-]', '', p)
        # uniformiser en format commençant par 0
        if p_clean.startswith('+33'):
            p_clean = '0' + p_clean[3:]
        elif p_clean.startswith('0033'):
            p_clean = '0' + p_clean[4:]
        cleaned.append(p_clean)
    return list(set(cleaned))

def filter_best_phone(phones):
    """
    Garde un seul numéro : le mobile en priorité (06, 07), sinon un fixe.
    """
    if not phones:
        return ""
        
    best_fixed = None
    
    for phone in phones:
        if phone.startswith('06') or phone.startswith('07'):
            return phone # Mobile trouvé, priorité absolue
        elif not best_fixed:
            best_fixed = phone
            
    return best_fixed

def extract_boss(text):
    """Cherche précisément un seul nom de décisionnaire avec des mots-clés stricts."""
    text_lower = text.lower()
    keywords = [
        "directeur de la publication", "gérant", "gerant", "président", "president", 
        "ceo", "fondateur", "directeur général", "associé", "associe", "responsable commercial"
    ]
    
    for kw in keywords:
        if kw in text_lower:
            start = text_lower.find(kw)
            context = text[start:start+120] 
            
            # Recherche de schémas du type : "Gérant : Jean DUPONT"
            match = re.search(r'(?i)' + kw + r'[\s:;,-]+((?:(?:Mr|M\.|Mme)\s+)?(?:[A-Z][A-Za-zÀ-ÿ]+(?:\s+[A-Z][A-Za-zÀ-ÿ]+){0,3}))', context)
            if match:
                name = match.group(1).strip()
                # Exclure si le nom semble être une phrase (trop long)
                if len(name.split()) <= 4:
                    return name
                    
            # Approche mots majuscules
            words = context.replace(':', ' ').replace(',', ' ').split()
            for i, w in enumerate(words):
                if w.lower() == kw.split()[-1] and i + 1 < len(words):
                    potential_name = []
                    for next_w in words[i+1:i+5]:
                        if next_w.istitle() or next_w.isupper():
                            # Nettoyage ponctuation
                            clean_w = re.sub(r'[^\w\s]', '', next_w)
                            if len(clean_w) > 1:
                                potential_name.append(clean_w)
                        elif potential_name:
                            break
                    if potential_name and len(potential_name) >= 2:
                        return " ".join(potential_name)
    return ""

def enrichir_contact(url_base):
    """
    Extrait brutes (emails, téléphones, boss).
    Le filtrage final se fait ensuite.
    """
    if not url_base:
        return {"emails": [], "telephones": [], "boss": ""}
        
    try:
        headers = {"User-Agent": ua.random}
    except:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}
    
    data = {"emails": [], "telephones": [], "boss": ""}
    pages_to_visit = [url_base]
    visited = set()
    
    try:
        response = requests.get(url_base, headers=headers, verify=False, timeout=5)
        response.raise_for_status()
        html = response.text
        soup = BeautifulSoup(html, 'lxml')
        
        data["emails"].extend(extract_emails(html))
        data["telephones"].extend(extract_phones(soup.get_text()))
        
        keywords = ['contact', 'mention', 'propos', 'about', 'legal', 'equipe', 'team']
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            text = a_tag.get_text().lower()
            if any(k in text or k in href.lower() for k in keywords):
                full_url = urljoin(url_base, href)
                if full_url not in pages_to_visit and full_url.startswith('http'):
                    pages_to_visit.append(full_url)
                    
        for url in pages_to_visit[:5]:
            if url in visited: continue
            visited.add(url)
            
            if url != url_base:
                try:
                    res = requests.get(url, headers=headers, verify=False, timeout=5)
                    soup_page = BeautifulSoup(res.text, 'lxml')
                    text_page = soup_page.get_text()
                    
                    data["emails"].extend(extract_emails(res.text))
                    data["telephones"].extend(extract_phones(text_page))
                    
                    if not data["boss"]:
                        boss = extract_boss(text_page)
                        if boss: data["boss"] = boss
                        
                except Exception:
                    pass
                    
        data["emails"] = list(set(data["emails"]))
        data["telephones"] = list(set(data["telephones"]))
        
        return data
        
    except Exception as e:
        return data

import aiohttp
import asyncio
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, quote
import unicodedata
import random

# REGEX COMPILEES (Performances maximales)
EMAIL_REGEX = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
PHONE_REGEX = re.compile(r'(?:(?:\+|00)33[\s.-]{0,3}(?:\(0\)[\s.-]{0,3})?|0)[1-9](?:(?:[\s.-]?\d{2}){4}|\d{2}(?:[\s.-]?\d{3}){2})\b')
BOSS_KEYWORDS = ["gérant", "gerant", "président", "president", "ceo", "fondateur", "directeur général", "associé", "associe"]
BOSS_REGEX_TEMPLATE = r'(?i){}[\s:;,-]+((?:(?:Mr|M\.|Mme)\s+)?(?:[A-Z][A-Za-zÀ-ÿ]+(?:\s+[A-Z][A-Za-zÀ-ÿ]+){{0,3}}))'

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])

def extract_emails(text):
    emails = EMAIL_REGEX.findall(text)
    return list(set([e.lower() for e in emails]))

def filter_best_email(emails, boss_name=""):
    if not emails: return ""
    generic_prefixes = ['contact', 'info', 'hello', 'support', 'admin', 'direction', 'commercial', 'agence', 'reclamation', 'personnel', 'webmaster', 'accueil']
    nominative_email, direct_email, generic_email = None, None, None
    boss_parts = [p for p in remove_accents(boss_name).lower().split() if len(p) > 2] if boss_name else []

    for email in emails:
        prefix = email.split('@')[0]
        is_generic = any(gen == prefix for gen in generic_prefixes) or "contact@" in email
        is_nominative = boss_parts and any(part in prefix for part in boss_parts)

        if is_nominative: return email
        elif not is_generic and not direct_email: direct_email = email
        elif is_generic and not generic_email: generic_email = email

    return direct_email or generic_email or emails[0]

def extract_phones(text):
    phones = PHONE_REGEX.findall(text)
    cleaned = []
    for p in phones:
        p_clean = re.sub(r'[\s.-]', '', p)
        if p_clean.startswith('+33'): p_clean = '0' + p_clean[3:]
        elif p_clean.startswith('0033'): p_clean = '0' + p_clean[4:]
        cleaned.append(p_clean)
    return list(set(cleaned))

def filter_best_phone(phones):
    if not phones: return ""
    best_fixed = None
    for phone in phones:
        if phone.startswith('06') or phone.startswith('07'): return phone
        elif not best_fixed: best_fixed = phone
    return best_fixed or ""

def extract_boss(text):
    text_lower = text.lower()
    for kw in BOSS_KEYWORDS:
        if kw in text_lower:
            start = text_lower.find(kw)
            context = text[start:start+120] 
            match = re.search(BOSS_REGEX_TEMPLATE.format(kw), context)
            if match:
                name = match.group(1).strip()
                if len(name.split()) <= 4: return name
    return ""

def get_client_profile():
    profiles = [
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Sec-Ch-Ua": "\"Not_A Brand\";v=\"8\", \"Chromium\";v=\"120\", \"Google Chrome\";v=\"120\"",
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": "\"Windows\"",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1"
        },
        {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Connection": "keep-alive"
        },
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1"
        }
    ]
    return random.choice(profiles)

class AdaptiveSemaphore:
    def __init__(self, initial=20, max_concurrency=40, min_concurrency=5):
        self.value = initial
        self.max_concurrency = max_concurrency
        self.min_concurrency = min_concurrency
        self.active = 0
        self.cond = asyncio.Condition()

    async def acquire(self):
        async with self.cond:
            await self.cond.wait_for(lambda: self.active < self.value)
            self.active += 1

    async def release(self, success=True):
        async with self.cond:
            self.active -= 1
            if success and self.value < self.max_concurrency:
                self.value += 1
            elif not success and self.value > self.min_concurrency:
                self.value -= 2
            self.cond.notify()

async def fetch_html(session, url, retries=3, adaptive_sem=None):
    backoff = 2.0
    for attempt in range(retries + 1):
        try:
            headers = get_client_profile()
            async with session.get(url, timeout=5, headers=headers, allow_redirects=True) as resp:
                if adaptive_sem:
                    if resp.status in [429, 503, 403]:
                        await adaptive_sem.release(success=False)
                        await adaptive_sem.acquire()
                    else:
                        await adaptive_sem.release(success=True)
                        await adaptive_sem.acquire()
                        
                if resp.status in [429, 503]:
                    if attempt < retries:
                        await asyncio.sleep(backoff + random.uniform(0, 1.0))
                        backoff *= 2
                        continue
                if resp.status == 403:
                    return {"html": "", "status": 403}
                html = await resp.text()
                return {"html": html, "status": resp.status}
        except (aiohttp.ClientError, asyncio.TimeoutError):
            if adaptive_sem:
                await adaptive_sem.release(success=False)
                await adaptive_sem.acquire()
            if attempt < retries:
                await asyncio.sleep(backoff + random.uniform(0, 1.0))
                backoff *= 2
            else:
                return {"html": "", "status": 0}
        except Exception:
            return {"html": "", "status": 0}
    return {"html": "", "status": 0}

async def enrichir_sans_site_async(session, nom, adresse, adaptive_sem=None):
    data = {"emails": [], "telephones": [], "boss": "", "audit": ""}
    if not nom: return data
    clean_addr = adresse.split(',')[0] if adresse else ""
    query = f'"{nom}" {clean_addr} (site:facebook.com OR site:linkedin.com OR site:pagesjaunes.fr)'
    url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
    
    resp = await fetch_html(session, url, adaptive_sem=adaptive_sem)
    html = resp["html"]
    if html:
        soup = BeautifulSoup(html, 'lxml')
        snippets = [a.get_text() for a in soup.find_all('a', class_='result__snippet')]
        full_text = " ".join(snippets)
        data["emails"].extend(extract_emails(full_text))
        data["telephones"].extend(extract_phones(full_text))
        data["emails"] = list(set(data["emails"]))
        data["telephones"] = list(set(data["telephones"]))
        del soup
    return data

def hybrid_extraction(html):
    """
    V33 Hybrid Structured Data Extraction: 
    Scans raw HTML for <script> blocks that might contain JSON/API data,
    bypassing the need for a full JS rendering engine for simple state payloads.
    """
    found_emails = extract_emails(html)
    found_phones = extract_phones(html)
    
    # Extract from script tags explicitly in case text parsing missed JSON strings
    soup = BeautifulSoup(html, 'lxml')
    for script in soup.find_all('script'):
        if script.string:
            content = script.string
            if "{" in content and "}" in content:
                found_emails.extend(extract_emails(content))
                found_phones.extend(extract_phones(content))
                
    boss = extract_boss(soup.get_text())
    del soup
    return list(set(found_emails)), list(set(found_phones)), boss

async def enrichir_contact_async(session, url_base, nom, adresse, adaptive_sem, js_rendering=False):
    if not url_base:
        return {"emails": [], "telephones": [], "boss": "", "audit": ""}
    
    data = {"emails": [], "telephones": [], "boss": "", "audit": ""}
    audit_flags = ["Non sécurisé (HTTP)"] if url_base.startswith("http://") else []
        
    resp = await fetch_html(session, url_base, adaptive_sem=adaptive_sem)
    html = resp["html"]
    
    if resp["status"] == 403 or (not html and resp["status"] == 0):
        query = f'"{nom}" {adresse.split(",")[0]}'
        url_ddg = f"https://html.duckduckgo.com/html/?q={quote(query)}"
        resp_ddg = await fetch_html(session, url_ddg, adaptive_sem=adaptive_sem)
        html_ddg = resp_ddg["html"]
        if html_ddg:
            data["emails"].extend(extract_emails(html_ddg))
            data["telephones"].extend(extract_phones(html_ddg))
            data["audit"] = "Proxy Fallback (403)"
            return data
            
    if not html: return data
    
    if '<meta name="viewport"' not in html.lower():
        audit_flags.append("Non optimisé Mobile")
        
    if audit_flags: data["audit"] = " | ".join(audit_flags)
        
    e_list, p_list, boss = hybrid_extraction(html)
    data["emails"].extend(e_list)
    data["telephones"].extend(p_list)
    data["boss"] = boss
    
    if not data["emails"] or not data["boss"]:
        soup = BeautifulSoup(html, 'lxml')
        pages_to_visit = set()
        keywords = ['contact', 'mention', 'propos', 'about', 'legal', 'equipe', 'team']
        for a_tag in soup.find_all('a', href=True):
            try:
                href = a_tag['href']
                text = a_tag.get_text().lower()
                if any(k in text or k in href.lower() for k in keywords):
                    full_url = urljoin(url_base, href)
                    if full_url.startswith('http'):
                        pages_to_visit.add(full_url)
            except: pass
        del soup
                    
        if pages_to_visit:
            tasks = [fetch_html(session, url, adaptive_sem=adaptive_sem) for url in list(pages_to_visit)[:3]]
            results = await asyncio.gather(*tasks)
            for page_resp in results:
                page_html = page_resp["html"]
                if page_html:
                    pe_list, pp_list, pboss = hybrid_extraction(page_html)
                    data["emails"].extend(pe_list)
                    data["telephones"].extend(pp_list)
                    if not data["boss"] and pboss:
                        data["boss"] = pboss
                        
    del html
    
    data["emails"] = list(set(data["emails"]))
    data["telephones"] = list(set(data["telephones"]))
    return data

async def process_single_lead(session, lead_raw, focus_no_website, adaptive_sem, callback, js_rendering=False):
    await adaptive_sem.acquire()
    try:
        name = lead_raw.get("name", "")
        link_website = lead_raw.get("link_website", "")
        adresse = lead_raw.get("adresse", "")
        index = lead_raw.get("index", 0)
        
        blacklist_franchises = ['foncia', 'century 21', 'century21', 'laforet', 'orpi', 'stephane plaza', 'mcdonald', 'burger king', 'carrefour', 'leclerc', 'auchan', 'intermarche', 'lidl', 'kfc']
        name_lower, url_lower = name.lower(), link_website.lower() if link_website else ""
        if any(b in name_lower or b in url_lower for b in blacklist_franchises):
            res = {"status": "ignored", "index": index, "name": name, "reason": "Franchise ou Grand Groupe ignoré"}
            if callback: callback(res)
            return res
            
        blacklist_annuaires = ['pagesjaunes.fr', 'doctolib.fr', 'societe.com', 'mairie.com', 'pappers.fr', 'yelp.fr', 'tripadvisor.fr', 'mappy.com']
        if url_lower and any(ann in url_lower for ann in blacklist_annuaires):
            link_website = ""
        
        contact_data = {"emails": [], "telephones": [], "boss": "", "audit": ""}
        if link_website:
            contact_data = await enrichir_contact_async(session, link_website, name, adresse, adaptive_sem, js_rendering=js_rendering)
        else:
            contact_data = await enrichir_sans_site_async(session, name, adresse, adaptive_sem)
            
        audit_site = contact_data.get("audit", "")
        opportunite_tag = ""
        if focus_no_website:
            if link_website:
                if audit_site and "Proxy Fallback" not in audit_site:
                    opportunite_tag = "🔥 À REFONDRE"
                else:
                    res = {"status": "ignored", "index": index, "name": name, "reason": "Site récent (Ignoré par Focus Vente)"}
                    if callback: callback(res)
                    return res
            else:
                opportunite_tag = "🔥 SANS SITE WEB"
        else:
            if not link_website: opportunite_tag = "🔥 SANS SITE WEB"
            elif audit_site: opportunite_tag = "🔥 À REFONDRE"

        gm_phones = lead_raw.get("gm_phones", [])
        for p in gm_phones: contact_data["telephones"].append(re.sub(r'[\s.-]', '', p))
        
        lead_data = {
            "place_id": lead_raw.get("place_id"),
            "opportunite": opportunite_tag,
            "nom": name,
            "pays": lead_raw.get("country"),
            "region": lead_raw.get("region"),
            "domaine": lead_raw.get("domain"),
            "adresse": adresse,
            "site_web": link_website,
            "note": lead_raw.get("note"),
            "nombre_avis": lead_raw.get("nombre_avis"),
            "dirigeant": contact_data["boss"],
            "email": filter_best_email(list(set(contact_data["emails"])), contact_data["boss"]),
            "telephone": filter_best_phone(list(set(contact_data["telephones"]))),
            "audit_site": audit_site
        }

        res = {"status": "success", "index": index, "data": lead_data}
        if callback: callback(res)
        return res
    finally:
        await adaptive_sem.release()

async def process_all_leads_async(raw_leads, focus_no_website, js_rendering=False, callback=None):
    adaptive_sem = AdaptiveSemaphore(initial=50, max_concurrency=100, min_concurrency=10)
    
    # Maintien de la session stateful pour partager les cookies sur l'ensemble du run OSINT
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False, limit=0)) as session:
        tasks = [process_single_lead(session, lead, focus_no_website, adaptive_sem, callback, js_rendering) for lead in raw_leads]
        results = await asyncio.gather(*tasks)
        return results

def process_all_leads_sync(raw_leads, focus_no_website, js_rendering=False, callback=None):
    try: loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(process_all_leads_async(raw_leads, focus_no_website, js_rendering, callback))
import questionary
from colorama import Fore, init
from core.database import init_db, save_recherche, save_entreprise_et_contact
from core.scraper import GoogleMapsScraper
import sys

init(autoreset=True)

def separator():
    print(Fore.BLUE + "=" * 80)

def main():
    separator()
    print(Fore.CYAN + " Bienvenue dans le Google Maps Scraper CLI (v2) ".center(80, "#"))
    separator()

    init_db()

    country = questionary.text("Pays à cibler (ex: France, Belgique) :").ask()
    if not country: sys.exit(0)

    region = questionary.text("Région / Ville (ex: Ile-de-France, Paris, Wallonie) :").ask()
    if not region: sys.exit(0)

    domain = questionary.text("Domaine / Secteur (ex: Plombier, Agence Web) :").ask()
    if not domain: sys.exit(0)

    headless_choice = questionary.confirm("Lancer le navigateur en mode caché (headless) ?").ask()

    separator()
    print(Fore.YELLOW + f"Création de la recherche pour : {domain} à {region}, {country}")
    
    # On sauvegarde d'abord la recherche
    recherche_id = save_recherche(pays=country, region=region, domaine=domain)
    
    separator()
    print(Fore.YELLOW + "Lancement du scraping et OSINT...")
    separator()

    scraper = GoogleMapsScraper(headless=headless_choice)

    saved_count = 0
    linked_count = 0

    def progress_callback(data):
        nonlocal saved_count, linked_count
        if data["status"] == "progress":
            lead = data["data"]
            idx = data["current"]
            tot = data["total"]
            
            print(Fore.MAGENTA + f"\n[{idx}/{tot}] Analyse de {lead['nom']}...")
            if lead["boss"]:
                print(Fore.CYAN + f"   👤 Dirigeant: {lead['boss']}")
            if lead["emails"]:
                print(Fore.GREEN + f"   📧 Emails: {lead['emails']}")
            if lead["telephones"]:
                print(Fore.GREEN + f"   📞 Tél: {lead['telephones']}")
            
            success, is_new = save_entreprise_et_contact(recherche_id, lead)
            
            if success:
                if is_new:
                    print(Fore.GREEN + "   ✅ Nouvelle entreprise sauvegardée et liée.")
                    saved_count += 1
                else:
                    print(Fore.YELLOW + "   🔗 Entreprise existante. Liée à cette recherche.")
                    linked_count += 1
            else:
                print(Fore.RED + "   ❌ Erreur d'enregistrement.")

    try:
        scraper.scrape(country, region, domain, callback=progress_callback)
    except KeyboardInterrupt:
        print(Fore.RED + "\n[!] Scraping interrompu par l'utilisateur.")
    except Exception as e:
        print(Fore.RED + f"\n[!] Erreur lors du scraping : {e}")
    finally:
        scraper.close()
        separator()
        print(Fore.CYAN + f"Bilan : {saved_count} nouvelles entreprises, {linked_count} entreprises déjà existantes liées.")
        separator()

if __name__ == "__main__":
    main()

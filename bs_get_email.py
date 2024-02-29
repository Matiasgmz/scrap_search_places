import re
import requests

def chercher_adresses_email(url):
    # Récupérer le contenu de la page web
    response = requests.get(url)
    contenu = response.text

    # Utiliser une expression régulière pour trouver les adresses e-mail
    pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    adresses_email = re.findall(pattern, contenu)

    return adresses_email

# Exemple d'utilisation
url = 'http://somme.franceolympique.com/'
adresses_email = chercher_adresses_email(url)
for adresse_email in adresses_email:
    print(adresse_email)
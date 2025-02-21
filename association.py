import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import unicodedata

def slugify(string):
    string = unicodedata.normalize("NFKD", string)
    string = "".join([c for c in string if not unicodedata.combining(c)]) 
    string = string.lower()
    string = re.sub(r"[^\w\s-]", "-", string)
    string = re.sub(r"[\s_]+", "-", string)

    return string


url = "https://commerces.hautsdefrance.fr/annuaire/departement/oise/association-caritative"

# get total page 
soup_pagination = BeautifulSoup(requests.get(url).text, "html.parser")
title = soup_pagination.find("h1", id="title-search")
print(title)   
# pagination = soup_pagination.find("ul", class_="fr-pagination__list")
# total_page = pagination.find_all("li")[-2].text


# data = []
# for i in range(1, int(total_page) + 1):
#     print(f"Page {i}")
#     url = f"https://lannuaire.service-public.fr/navigation/{region}/{department}/mairie?page=" + str(i)
#     print(url)
#     response = requests.get(url)

#     if response.status_code == 200:

#         soup = BeautifulSoup(response.text, "html.parser")
        
#         section_city_hall = soup.find_all("div", attrs={"data-test": "link-annuaire"})
        
#         for city_hall in section_city_hall:

#             link_city_hall = city_hall.a["href"]
#             reponse_by_cuty_hall = requests.get(link_city_hall)
#             if reponse_by_cuty_hall.status_code == 200:
#                 soup_city_hall = BeautifulSoup(reponse_by_cuty_hall.text, "html.parser")
#                 email = soup_city_hall.find("a", class_="send-mail")
#                 name = soup_city_hall.find("h1", id="titlePage")   
#                 phone = soup_city_hall.find("span", id="contentPhone_1") 

#                 if email is None:
#                     email = ""
#                 else:
#                     email = email["href"].replace("mailto:", "")
#                 if name is None:
#                     name = ""
#                 else:
#                     name = name.text
#                 if phone is None:    
#                     phone = ""
#                 else:
#                     phone = phone.text
           
#                 data.append(
#                     {
#                         "Nom": name,
#                         "Adresse e-mail": email,
#                         "Téléphone": phone
#                     }
#                 )
            
#             else:
#                 print(f"Erreur : Impossible d'accéder à la page (Code {reponse_by_cuty_hall.status_code})")
#     else:
#         print(f"Erreur : Impossible d'accéder à la page (Code {response.status_code})")

# name_file = f"mairie_{department}_infos_scrap.xlsx"
# df = pd.DataFrame(data)      
# df.to_excel(name_file, index=False) 
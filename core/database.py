from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from .models import Base, Entreprise, Contact, Recherche
import os

# Nouvelle base de données pour la v2
DB_PATH = "sqlite:///leads_v2.db"
engine = create_engine(DB_PATH, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Crée les tables de la base de données si elles n'existent pas."""
    Base.metadata.create_all(bind=engine)

def clear_database():
    """Supprime toutes les données de la base de données et recrée les tables vides."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

def save_recherche(pays, region, domaine):
    """Sauvegarde ou récupère la recherche courante."""
    db = SessionLocal()
    try:
        recherche = Recherche(pays=pays, region=region, domaine=domaine)
        db.add(recherche)
        db.commit()
        db.refresh(recherche)
        return recherche.id
    finally:
        db.close()

def save_entreprise_et_contact(recherche_id, data):
    """
    Insère une entreprise si elle n'existe pas (vérification par place_id).
    Insère les contacts associés.
    Associe l'entreprise à la recherche.
    """
    db = SessionLocal()
    try:
        recherche = db.query(Recherche).filter(Recherche.id == recherche_id).first()
        if not recherche:
            return False, False # Recherche introuvable

        # Vérifier si l'entreprise existe déjà via place_id
        entreprise = None
        is_new = False
        if data.get("place_id"):
            entreprise = db.query(Entreprise).filter(Entreprise.place_id == data["place_id"]).first()
        
        # Fallback de vérification sur nom et adresse si place_id est manquant
        if not entreprise and data.get("nom") and data.get("adresse"):
             entreprise = db.query(Entreprise).filter(Entreprise.nom == data["nom"], Entreprise.adresse == data["adresse"]).first()

        if not entreprise:
            # Création de l'entreprise
            entreprise = Entreprise(
                place_id=data.get("place_id"),
                nom=data["nom"],
                adresse=data.get("adresse"),
                site_web=data.get("site_web"),
                note=data.get("note"),
                nombre_avis=data.get("nombre_avis")
            )
            db.add(entreprise)
            db.commit() # Commit pour avoir l'ID
            db.refresh(entreprise)
            is_new = True
            
            # Création du contact si données présentes
            if data.get("emails") or data.get("telephones") or data.get("boss"):
                contact = Contact(
                    entreprise_id=entreprise.id,
                    nom_dirigeant=data.get("boss"),
                    email=data.get("emails"),
                    telephone=data.get("telephones")
                )
                db.add(contact)

        # Lier à la recherche si pas déjà lié
        if recherche not in entreprise.recherches:
            entreprise.recherches.append(recherche)

        db.commit()
        return True, is_new

    except Exception as e:
        db.rollback()
        print(f"Erreur SQL: {e}")
        return False, False
    finally:
        db.close()

def get_all_dashboard_data():
    """Récupère toutes les données sous format plat pour le dashboard."""
    db = SessionLocal()
    try:
        results = []
        # On fait des jointures pour avoir les recherches, l'entreprise et les contacts
        entreprises = db.query(Entreprise).all()
        for ent in entreprises:
            contacts = ent.contacts
            contact = contacts[0] if contacts else None
            
            # Prendre la dernière recherche en date
            recherches = sorted(ent.recherches, key=lambda x: x.date_scraping, reverse=True)
            rech = recherches[0] if recherches else None

            results.append({
                "ID": ent.id,
                "Nom": ent.nom,
                "Pays": rech.pays if rech else "",
                "Région": rech.region if rech else "",
                "Domaine": rech.domaine if rech else "",
                "Adresse": ent.adresse,
                "Site Web": ent.site_web,
                "Note": ent.note,
                "Avis": ent.nombre_avis,
                "Dirigeant": contact.nom_dirigeant if contact else "",
                "Email": contact.email if contact else "",
                "Téléphone": contact.telephone if contact else "",
                "Date Scraping": rech.date_scraping.strftime("%Y-%m-%d %H:%M:%S") if rech else ""
            })
        return results
    finally:
        db.close()

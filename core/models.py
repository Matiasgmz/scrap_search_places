from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Table
from sqlalchemy.orm import declarative_base, relationship
import datetime

Base = declarative_base()

# Table de liaison pour relation Many-to-Many entre Entreprise et Recherche
entreprise_recherche = Table(
    'entreprise_recherche',
    Base.metadata,
    Column('entreprise_id', Integer, ForeignKey('entreprises.id'), primary_key=True),
    Column('recherche_id', Integer, ForeignKey('recherches.id'), primary_key=True)
)

class Recherche(Base):
    __tablename__ = "recherches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pays = Column(String, nullable=False)
    region = Column(String, nullable=False)
    domaine = Column(String, nullable=False)
    date_scraping = Column(DateTime, default=datetime.datetime.utcnow)

    entreprises = relationship('Entreprise', secondary=entreprise_recherche, back_populates='recherches')


class Entreprise(Base):
    __tablename__ = "entreprises"

    id = Column(Integer, primary_key=True, autoincrement=True)
    place_id = Column(String, unique=True, nullable=True) # Unique ID Google Maps
    nom = Column(String, nullable=False)
    adresse = Column(String, nullable=True)
    site_web = Column(String, nullable=True)
    note = Column(Float, nullable=True)
    nombre_avis = Column(Integer, nullable=True)

    contacts = relationship("Contact", back_populates="entreprise", cascade="all, delete-orphan")
    recherches = relationship('Recherche', secondary=entreprise_recherche, back_populates='entreprises')


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entreprise_id = Column(Integer, ForeignKey('entreprises.id'), nullable=False)
    nom_dirigeant = Column(String, nullable=True)
    email = Column(String, nullable=True)
    telephone = Column(String, nullable=True)

    entreprise = relationship("Entreprise", back_populates="contacts")

# Dockerfile pour déployer le Scraper sur un VPS / Serveur Cloud

# Utilisation d'une image Python avec Chromium préinstallé (indispensable pour Selenium)
FROM python:3.11-slim

# Variables d'environnement
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV STREAMLIT_SERVER_PORT 8501
ENV STREAMLIT_SERVER_ADDRESS 0.0.0.0

# Installation des dépendances système (Chromium et Webdriver)
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Définition du répertoire de travail
WORKDIR /app

# Copie des requirements et installation
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code source
COPY . .

# Exposition du port Streamlit
EXPOSE 8501

# Lancement de l'application Streamlit
CMD ["streamlit", "run", "web.py"]

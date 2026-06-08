import streamlit as st
import pandas as pd
import plotly.express as px
from core.database import init_db, get_all_dashboard_data, save_recherche, save_entreprise_et_contact, clear_database
from core.scraper import GoogleMapsScraper
from io import BytesIO

st.set_page_config(page_title="GMaps OSINT Scraper Pro", page_icon="🗺️", layout="wide")

# =========================
# CSS PERSONNALISÉ (UI/UX)
# =========================
st.markdown("""
<style>
    /* Style des boutons */
    .stButton>button {
        background: linear-gradient(135deg, #6366F1 0%, #4F46E5 100%);
        color: white;
        border-radius: 8px;
        padding: 10px 24px;
        border: none;
        font-weight: 600;
        letter-spacing: 0.5px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px -1px rgba(79, 70, 229, 0.2);
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(79, 70, 229, 0.3);
        color: white;
        border: none;
    }
    
    /* Blocs de contenu (Cards) */
    div[data-testid="stMetric"] {
        background-color: var(--secondary-background-color);
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        border: 1px solid rgba(128, 128, 128, 0.2);
    }
    
    /* Formulaire esthétique */
    div[data-testid="stForm"] {
        background-color: var(--secondary-background-color);
        padding: 30px;
        border-radius: 16px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);
        border: 1px solid rgba(128, 128, 128, 0.2);
    }
    
    /* Barre de progression personnalisée */
    .stProgress > div > div > div > div {
        background-image: linear-gradient(to right, #4F46E5, #818CF8);
    }
</style>
""", unsafe_allow_html=True)

init_db()

st.sidebar.title("Navigation")
page = st.sidebar.radio("Aller vers :", ["📊 Dashboard", "🔍 Nouveau Scraping"])

if page == "📊 Dashboard":
    st.title("📊 Dashboard Analytique")
    
    data = get_all_dashboard_data()
    
    if not data:
        st.info("Aucune donnée dans la base pour le moment. Allez dans 'Nouveau Scraping' pour commencer.")
    else:
        df = pd.DataFrame(data)
        
        # --- KPIs ---
        total_leads = len(df)
        total_emails = len(df[df['Email'] != ""])
        total_phones = len(df[df['Téléphone'] != ""])
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Entreprises", total_leads)
        col2.metric("Emails trouvés", total_emails, f"{int((total_emails/total_leads)*100)}%" if total_leads else "0%")
        col3.metric("Téléphones trouvés", total_phones, f"{int((total_phones/total_leads)*100)}%" if total_leads else "0%")
        col4.metric("Dirigeants identifiés", len(df[df['Dirigeant'] != ""]))

        st.markdown("<br>", unsafe_allow_html=True)

        # --- Filtres ---
        st.subheader("Filtres")
        col1, col2, col3 = st.columns(3)
        with col1:
            countries = ["Tous"] + list(df['Pays'].unique())
            selected_country = st.selectbox("Pays", countries)
        with col2:
            regions = ["Toutes"] + list(df[df['Pays'] == selected_country]['Région'].unique() if selected_country != "Tous" else df['Région'].unique())
            selected_region = st.selectbox("Région", regions)
        with col3:
            domains = ["Tous"] + list(df['Domaine'].unique())
            selected_domain = st.selectbox("Domaine", domains)
            
        filtered_df = df.copy()
        if selected_country != "Tous":
            filtered_df = filtered_df[filtered_df['Pays'] == selected_country]
        if selected_region != "Toutes":
            filtered_df = filtered_df[filtered_df['Région'] == selected_region]
        if selected_domain != "Tous":
            filtered_df = filtered_df[filtered_df['Domaine'] == selected_domain]

        # --- Graphiques Plotly ---
        if not filtered_df.empty:
            col_graph1, col_graph2 = st.columns(2)
            
            with col_graph1:
                fig_region = px.pie(filtered_df, names='Région', title='Répartition par Région', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig_region, use_container_width=True)
                
            with col_graph2:
                # Top Domaines
                domain_counts = filtered_df['Domaine'].value_counts().reset_index()
                domain_counts.columns = ['Domaine', 'Nombre']
                fig_domain = px.bar(domain_counts, x='Domaine', y='Nombre', title='Top Domaines', color='Nombre', color_continuous_scale='Purples')
                st.plotly_chart(fig_domain, use_container_width=True)

        st.markdown("---")

        # --- Tableau de données ---
        st.subheader(f"Données ({len(filtered_df)} résultats)")
        st.dataframe(filtered_df, use_container_width=True, height=400)
        
        # --- Exports ---
        col_exp1, col_exp2 = st.columns(2)
        
        def to_excel(df):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Leads')
            return output.getvalue()

        def to_csv(df):
            return df.to_csv(index=False).encode('utf-8')
            
        with col_exp1:
            st.download_button("📥 Télécharger en Excel (.xlsx)", data=to_excel(filtered_df), file_name='leads.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', use_container_width=True)
        
        with col_exp2:
            st.download_button("📥 Télécharger en CSV (.csv)", data=to_csv(filtered_df), file_name='leads.csv', mime='text/csv', use_container_width=True)

elif page == "🔍 Nouveau Scraping":
    st.title("🔍 Nouveau Scraping Pro + OSINT")
    st.info("🎯 **Stratégie** : Définissez vos critères avec précision. Les leads non qualifiés seront ignorés pour vous faire gagner du temps.")
    
    with st.form("scraping_form"):
        st.subheader("📍 Paramètres de la Recherche")
        col1, col2, col3 = st.columns(3)
        with col1:
            country = st.text_input("Pays *", "France", help="Ex: France, Suisse, Belgique...")
        with col2:
            region = st.text_input("Région / Ville (Optionnel)", "", help="Laissez vide pour chercher dans tout le pays. Ex: Paris, Île-de-France...")
        with col3:
            domain = st.text_input("Domaine / Secteur *", "Plombier", help="Ex: Plombier, Agence Web...")
            
        st.markdown("---")
        st.subheader("🎯 Critères de Qualification (Ciblage)")
        site_web_filter = st.selectbox("Présence Site Web", ["Tous", "Avec site web uniquement", "Sans site web uniquement"])
            
        st.markdown("---")
        st.subheader("⚙️ Paramètres Avancés")
        proxy = st.text_input("Proxy IP:PORT (Optionnel)", placeholder="Ex: 192.168.1.1:8080")
        
        col_adv1, col_adv2 = st.columns(2)
        with col_adv1:
            headless = st.checkbox("Mode invisible (Headless)", value=True, help="Ouvre Google Chrome en tâche de fond (Fortement recommandé)")
        with col_adv2:
            clear_db = st.checkbox("Vider la base de données (Remise à zéro)", value=False, help="Supprime tous les anciens résultats avant de commencer ce nouveau scraping.")
            
        st.markdown("<br>", unsafe_allow_html=True)
        if st.form_submit_button("🚀 Lancer la Collecte", use_container_width=True):
            if not country or not domain:
                st.error("Vieuillez remplir le Pays et le Domaine obligatoires (*)")
                st.stop()
                
            if clear_db:
                clear_database()
                st.toast("Base de données vidée avec succès.", icon="🗑️")
            
            recherche_id = save_recherche(pays=country, region=region, domaine=domain)
            
            # --- UI DYNAMIQUE PENDANT LE SCRAPING ---
            st.markdown("### 🔄 Progression de la collecte")
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Conteneur de logs stylisé
            log_container = st.container()
            with log_container:
                log_box = st.empty()
            logs = []
            
            def update_logs(message, level="info"):
                icon = "🟢" if level == "success" else "🟠" if level == "warning" else "🔴" if level == "error" else "🔵"
                logs.insert(0, f"{icon} {message}")
                log_box.code("\n".join(logs[:15]), language="text")

            counts = {"saved": 0, "linked": 0, "ignored": 0}
            
            def progress_callback(data):
                if data["status"] == "error":
                    update_logs(data["message"], "error")
                    return
                    
                if data["status"] == "ignored":
                    idx = data["current"]
                    tot = data["total"]
                    progress_bar.progress(idx / tot)
                    status_text.markdown(f"**Analyse {idx}/{tot} :** {data['name']} *(Ignoré)*")
                    counts["ignored"] += 1
                    update_logs(f"Ignoré : {data['name']} ({data['reason']})", "info")
                    return
                    
                if data["status"] == "progress":
                    idx = data["current"]
                    tot = data["total"]
                    lead = data["data"]
                    
                    progress_bar.progress(idx / tot)
                    status_text.markdown(f"**Analyse {idx}/{tot} :** {lead['nom']}...")
                    
                    success, is_new = save_entreprise_et_contact(recherche_id, lead)
                    
                    if success:
                        if is_new:
                            counts["saved"] += 1
                            boss_info = f" (Dirigeant: {lead['boss']})" if lead.get('boss') else ""
                            update_logs(f"Nouveau : {lead['nom']}{boss_info}", "success")
                        else:
                            counts["linked"] += 1
                            update_logs(f"Lié : {lead['nom']} (Déjà en base)", "warning")
                    else:
                        update_logs(f"Erreur d'insertion pour {lead['nom']}", "error")

            filters = {
                "site_web": site_web_filter
            }
            
            scraper = GoogleMapsScraper(headless=headless, proxy=proxy)
            try:
                with st.spinner("Initialisation du navigateur et extraction Google Maps en cours..."):
                    scraper.scrape(country, region, domain, callback=progress_callback, filters=filters)
                st.balloons()
                st.success(f"🎉 Terminé ! {counts['saved']} nouveaux leads qualifiés, {counts['linked']} mis à jour, {counts['ignored']} ignorés.")
            except Exception as e:
                st.error(f"Une erreur critique s'est produite : {e}")
            finally:
                scraper.close()

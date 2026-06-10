import streamlit as st
import pandas as pd
from io import BytesIO
import concurrent.futures
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
from script import GoogleMapsScraper, init_db, clear_database, get_all_leads, update_lead_status, save_checkpoint, get_checkpoints, get_all_doublons
import time
import requests
import random

st.set_page_config(page_title="ZenScraper Pro", page_icon="⚡", layout="wide")

# --- CSS INJECTION: PREMIUM SAAS DARK MODE ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"], .stApp {
        font-family: 'Inter', sans-serif !important;
        background-color: #0F172A !important;
        color: #F8FAFC !important;
    }
    
    section[data-testid="stSidebar"] {
        background-color: #0B0F19 !important;
        border-right: 1px solid #1E293B !important;
    }
    
    [data-testid="stMetric"] {
        background-color: #1E293B !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
        padding: 20px 24px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1) !important;
    }
    
    [data-testid="stMetric"] label {
        color: #94A3B8 !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
    }
    
    [data-testid="stMetricValue"] {
        color: #FFFFFF !important;
        font-weight: 700 !important;
        font-size: 2.2rem !important;
    }

    .stButton>button {
        background-color: #3B82F6 !important;
        color: #FFFFFF !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        border: none !important;
        padding: 12px 24px !important;
        transition: all 0.2s ease !important;
    }
    .stButton>button:hover {
        background-color: #2563EB !important;
        box-shadow: 0 4px 14px rgba(59, 130, 246, 0.4) !important;
        transform: translateY(-2px) !important;
    }

    div[data-testid="stForm"] {
        background-color: #1E293B !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
        padding: 28px !important;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1) !important;
    }

    .stTextInput>div>div>input, .stSelectbox>div>div>select, .stMultiSelect>div>div>div {
        background-color: #0F172A !important;
        color: #F8FAFC !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
    }
    
    .stTextInput>div>div>input:focus, .stSelectbox>div>div>select:focus {
        border-color: #3B82F6 !important;
        box-shadow: 0 0 0 1px #3B82F6 !important;
    }
    
    .stCodeBlock {
        background-color: #0B0F19 !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
    }
    
    h1, h2, h3 { font-weight: 700 !important; color: #FFFFFF !important; }
    h1 { font-size: 2rem !important; margin-bottom: 1.5rem !important; }
    h2 { font-size: 1.4rem !important; color: #E2E8F0 !important; margin-top: 1.5rem !important; margin-bottom: 1rem !important; }
    h3 { font-size: 1.1rem !important; color: #94A3B8 !important; margin-bottom: 0.8rem !important; }
    
    .stCheckbox label span { color: #D1D5DB !important; }
    
    hr { border-color: #334155 !important; }
    
    /* Pitch Container Override */
    .pitch-header {
        color: #10B981;
        font-weight: 600;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

init_db()

def wait_for_internet():
    while True:
        try:
            requests.get("https://1.1.1.1", timeout=3)
            return True
        except:
            time.sleep(5)

st.sidebar.markdown("## ⚡ Menu ZenScraper")
page = st.sidebar.radio("", ["📊 CRM & Statistiques", "🚀 Nouveau Scraping"])

if page == "📊 CRM & Statistiques":
    st.markdown("<h1>📊 Console CRM & Data</h1>", unsafe_allow_html=True)
    
    data = get_all_leads()
    if not data:
        st.info("Aucune donnée dans la base. Basculez sur 'Nouveau Scraping' pour extraire des prospects.")
    else:
        df = pd.DataFrame(data)
        
        # --- 2. Filtres ---
        st.markdown("<h3>🔍 Filtres Rapides</h3>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            selected_country = st.selectbox("Pays", ["Tous"] + list(df['pays'].dropna().unique()))
        with col2:
            regions_list = df['region'].dropna().unique() if selected_country == "Tous" else df[df['pays'] == selected_country]['region'].dropna().unique()
            selected_region = st.selectbox("Région", ["Toutes"] + list(regions_list))
        with col3:
            selected_domain = st.selectbox("Domaine", ["Tous"] + list(df['domaine'].dropna().unique()))
            
        filtered_df = df.copy()
        if selected_country != "Tous": filtered_df = filtered_df[filtered_df['pays'] == selected_country]
        if selected_region != "Toutes": filtered_df = filtered_df[filtered_df['region'] == selected_region]
        if selected_domain != "Tous": filtered_df = filtered_df[filtered_df['domaine'] == selected_domain]

        full_filtered_df = filtered_df.copy()
        cols_to_keep = ['id', 'opportunite', 'audit_site', 'statut', 'nom', 'site_web', 'telephone', 'email', 'region']
        existing_cols = [c for c in cols_to_keep if c in filtered_df.columns]
        display_df = filtered_df[existing_cols]

        st.markdown(f"<h2>💼 Vos Prospects ({len(display_df)} résultats)</h2>", unsafe_allow_html=True)
        
        status_options = ["À contacter", "Intéressé / Produit vendu", "Pas intéressé / Refusé", "Pas de réponse / Injoignable"]
        
        edited_df = st.data_editor(
            display_df,
            column_config={
                "id": None,
                "opportunite": st.column_config.TextColumn("Cible"),
                "audit_site": st.column_config.TextColumn("Audit (Problèmes)"),
                "statut": st.column_config.SelectboxColumn("Suivi Client", options=status_options, required=True),
                "nom": st.column_config.TextColumn("Entreprise"),
                "site_web": st.column_config.LinkColumn("Site Web"),
                "telephone": st.column_config.TextColumn("Téléphone"),
                "email": st.column_config.TextColumn("Email"),
                "region": st.column_config.TextColumn("Ville")
            },
            disabled=[c for c in display_df.columns if c != "statut"],
            use_container_width=True, hide_index=True,
            height=400
        )
        
        for index, row in edited_df.iterrows():
            old_statut = display_df.loc[index, 'statut']
            new_statut = row['statut']
            if old_statut != new_statut:
                update_lead_status(row['id'], new_statut)
                st.toast(f"Statut mis à jour : {row['nom']} -> {new_statut}", icon="✅")
                
        # Update full df with edited status for export & AI
        full_filtered_df['statut'] = edited_df['statut'].values
                
        col_exp1, col_exp2 = st.columns(2)
        def to_excel(df):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer: df.to_excel(writer, index=False, sheet_name='Leads')
            return output.getvalue()
        def to_csv(df): return df.to_csv(index=False).encode('utf-8')
            
        with col_exp1: st.download_button("📥 Exporter la vue en CSV", data=to_csv(full_filtered_df), file_name='leads.csv', use_container_width=True)
        with col_exp2: st.download_button("📥 Exporter la vue en Excel", data=to_excel(full_filtered_df), file_name='leads.xlsx', use_container_width=True)

        # --- 3. Générateur de Pitch ---
        st.markdown("<hr><h2>🤖 Générateur de Pitch IA</h2>", unsafe_allow_html=True)
        
        pitch_leads = full_filtered_df[full_filtered_df['opportunite'].str.contains("SANS SITE WEB|À REFONDRE", na=False)]
        if not pitch_leads.empty:
            lead_options = pitch_leads['nom'].tolist()
            selected_lead_name = st.selectbox("Sélectionner un Prospect Cible :", ["-- Choisir un Prospect --"] + lead_options)
            
            if selected_lead_name != "-- Choisir un Prospect --":
                lead_data = pitch_leads[pitch_leads['nom'] == selected_lead_name].iloc[0]
                note = lead_data.get('note', 'excellente')
                if pd.isna(note) or not note: note = "excellente"
                region = lead_data.get('region', 'votre région')
                if pd.isna(region) or not region: region = "votre région"
                domaine = lead_data.get('domaine', 'votre secteur')
                if pd.isna(domaine) or not domaine: domaine = "votre secteur"
                
                competitors = df[(df['domaine'] == domaine) & (df['region'] == region) & (df['site_web'] != "")]
                comp_text = ""
                if not competitors.empty:
                    comp_names = competitors.head(2)['nom'].tolist()
                    comp_text = f"Pendant ce temps, des concurrents locaux comme {' et '.join(comp_names)} captent toute la clientèle digitale grâce à leur site internet optimisé."
                else:
                    comp_text = "Vos concurrents captent actuellement toute la clientèle digitale en étant présents et bien référencés sur Internet."

                if "À REFONDRE" in lead_data['opportunite']:
                    audit = lead_data.get('audit_site', 'obsolète')
                    pitch = f"[PHASE 1 : ACCROCHE]\n\"Bonjour, c'est bien le gérant de {lead_data['nom']} ?\nEnchanté. Je vous appelle car j'ai vu votre excellente réputation locale ({note}/5), mais j'ai aussi détecté une erreur critique sur votre site qui vous fait perdre des clients en ce moment-même.\"\n\n[PHASE 2 : DOULEUR]\n\"L'audit que j'ai réalisé montre ce problème : {audit}.\nConcrètement, Google vous pénalise et les clients qui cliquent sur votre lien repartent directement chez la concurrence...\n{comp_text}\"\n\n[PHASE 3 : SOLUTION]\n\"Un site avec cette erreur fait pire que pas de site du tout. L'objectif est de le refondre avec les standards actuels :\n1. 100% Sécurisé et Ultra-rapide.\n2. Adapté aux mobiles (80% des recherches).\n3. Construit pour convertir les visiteurs en appels.\"\n\n[PHASE 4 : ENGAGEMENT]\n\"L'idée n'est pas de vous engager à quoi que ce soit, mais j'aimerais vous montrer l'impact exact de cette erreur et comment on peut la réparer. Avez-vous 5 minutes mardi ou jeudi prochain ?\""
                else:
                    pitch = f"[PHASE 1 : ACCROCHE]\n\"Bonjour, c'est bien le responsable de {lead_data['nom']} ?\nSuper. Je vous appelle car je suis tombé sur votre page à {region} et vous avez une excellente réputation ({note}/5). Par contre, je me suis rendu compte que vous perdiez sûrement des dizaines de clients par mois.\"\n\n[PHASE 2 : DOULEUR]\n\"Aujourd'hui, quand un client cherche votre service, la première chose qu'il fait c'est cliquer sur le site web pour se rassurer. Sauf que vous n'en avez pas... \n{comp_text}\"\n\n[PHASE 3 : SOLUTION]\n\"Je ne vous propose pas une dépense, je vous propose un investissement. Un site professionnel c'est :\n1. Un vendeur ouvert 24h/24 et 7j/7.\n2. Une crédibilité immédiate.\n3. Du temps gagné au téléphone.\"\n\n[PHASE 4 : ENGAGEMENT]\n\"L'idée n'est pas de vous vendre quoi que ce soit aujourd'hui, mais simplement de vous montrer en 5 minutes ce qu'on peut faire pour développer votre chiffre d'affaires. Quand êtes-vous disponible la semaine prochaine ?\""
                
                st.markdown(f"<div class='pitch-header'>✅ Script généré pour : {lead_data['opportunite']}</div>", unsafe_allow_html=True)
                st.code(pitch, language="text")
        else:
            st.info("Aucun prospect qualifié sans site web ou avec site à refondre dans cette vue.")

        # --- 4. Doublons ---
        st.markdown("<hr><h2>🗑️ Historique des Doublons (Déjà traités)</h2>", unsafe_allow_html=True)
        doublons_data = get_all_doublons()
        if doublons_data:
            df_doublons = pd.DataFrame(doublons_data)
            with st.expander(f"Voir les {len(df_doublons)} prospects ignorés car déjà présents dans le CRM"):
                st.dataframe(df_doublons, use_container_width=True, hide_index=True)
        else:
            st.info("Aucun doublon n'a été détecté pour le moment.")

elif page == "🚀 Nouveau Scraping":
    st.markdown("<h1>🚀 Pipeline d'Extraction de Données</h1>", unsafe_allow_html=True)
    st.caption("Propulsé par l'Extraction Hybride, les Sessions Asynchrones Stateful et le Bandwidth Tuning.")
    
    with st.form("scraping_form"):
        st.markdown("<h3>🎯 Critères de Ciblage</h3>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1: country = st.text_input("Pays", "France")
        with col2: 
            macro_zones = [
                "Toute la France", "Zone Nord", "Zone Sud", "Zone Est", "Zone Ouest",
                "Paris", "Marseille", "Lyon", "Toulouse", "Nice", "Nantes",
                "Montpellier", "Strasbourg", "Bordeaux", "Lille", "Rennes",
                "Reims", "Toulon", "Saint-Étienne", "Le Havre", "Grenoble",
                "Dijon", "Angers", "Nîmes", "Villeurbanne"
            ]
            region_input = st.multiselect("Zone(s) ou Ville(s)", options=macro_zones, default=["Paris"], help="Sélectionnez une ou plusieurs zones/villes")
        with col3: 
            popular_domains = [
                "Plombier", "Électricien", "Serrurier", "Chauffagiste", "Menuisier",
                "Peintre en bâtiment", "Couvreur", "Maçon", "Carreleur", "Paysagiste",
                "Agence Immobilière", "Boulangerie", "Boucherie", "Coiffeur", "Institut de beauté",
                "Garage automobile", "Auto école", "Chirurgien dentiste", "Avocat", "Expert-comptable",
                "Restaurant", "Pizzeria", "Pharmacie", "Opticien", "Fleuriste"
            ]
            domain_input = st.multiselect("Secteur(s) d'Activité", options=popular_domains, default=["Plombier", "Électricien"], help="Sélectionnez plusieurs secteurs")
            
        st.markdown("<hr><h3>⚙️ Paramètres Avancés</h3>", unsafe_allow_html=True)
        focus_no_website = st.checkbox("🎯 Cible Prioritaire : Sans Site Web (Active l'OSINT ciblé profond)", value=True)
        webhook_url = st.text_input("🔗 URL Webhook Externe (Make/Zapier)", help="Envoi asynchrone des cibles prioritaires.")
        
        col_adv1, col_adv2 = st.columns(2)
        with col_adv1: 
            headless = st.checkbox("Activer le mode Headless (Chrome Invisible)", value=True)
            clear_db = st.checkbox("⚠️ Vider la Base de Données & Réinitialiser les Checkpoints", value=False)
        with col_adv2: 
            js_rendering = st.checkbox("⚙️ Forcer le Moteur de Rendu JS (Forte consommation RAM)", value=False)
            max_scrolls = st.slider("⚡ Profondeur (Vitesse vs Quantité)", min_value=1, max_value=15, value=5, help="1 = Ultra Rapide (20 résultats/zone), 15 = Lent (120 résultats/zone)")
            
        st.markdown("<br>", unsafe_allow_html=True)
        submit_standard = st.form_submit_button("🚀 Lancer l'Extraction Mondiale (Multithreading)", use_container_width=True)

        if submit_standard:
            if not country or not domain_input:
                st.error("Le Pays et le Secteur d'Activité sont obligatoires.")
                st.stop()
                
            MACRO_ZONES = {
                "Toute la France": [f"{i:02d}" for i in range(1, 96)] + ["971", "972", "973", "974", "976"],
                "Zone Nord": ["59", "62", "80", "02", "60", "75", "77", "78", "91", "92", "93", "94", "95", "76", "27"],
                "Zone Sud": ["13", "06", "34", "31", "83", "33", "2A", "2B", "84", "30", "11", "66"],
                "Zone Est": ["67", "68", "57", "54", "21", "25", "39", "71", "69", "42", "38"],
                "Zone Ouest": ["44", "35", "49", "29", "56", "85", "37", "86", "17", "36"]
            }
            
            raw_regions = region_input if region_input else [""]
            regions = []
            for r in raw_regions:
                if r in MACRO_ZONES:
                    regions.extend(["Département " + dep for dep in MACRO_ZONES[r]])
                elif r == "Paris":
                    regions.extend([f"Paris {i}er arrondissement" if i == 1 else f"Paris {i}e arrondissement" for i in range(1, 21)])
                elif r == "Lyon":
                    regions.extend([f"Lyon {i}er arrondissement" if i == 1 else f"Lyon {i}e arrondissement" for i in range(1, 10)])
                elif r == "Marseille":
                    regions.extend([f"Marseille {i}er arrondissement" if i == 1 else f"Marseille {i}e arrondissement" for i in range(1, 17)])
                else:
                    regions.append(r)
            regions = list(dict.fromkeys(regions))
            
            domains = domain_input if domain_input else [""]
            
            combinations = [(r, d) for r in regions for d in domains if d]
            
            if clear_db:
                clear_database()
                st.toast("Base de données et Checkpoints réinitialisés avec succès.", icon="🗑️")
                
            completed_checkpoints = get_checkpoints(country)
            original_len = len(combinations)
            combinations = [(r, d) for r, d in combinations if (r, d) not in completed_checkpoints]
            
            if not combinations:
                st.success(f"Toutes les {original_len} requêtes ont déjà été complétées. Videz la base pour recommencer.")
                st.stop()
            elif len(combinations) < original_len:
                st.info(f"🔄 Checkpoint Actif : Ignorés {original_len - len(combinations)} requêtes déjà validées.")
            
            st.markdown(f"### 🔄 Traitement Parallèle Actif ({len(combinations)} requêtes)")
            global_status = st.empty()
            progress_bar = st.progress(0)
            
            log_box = st.empty()
            logs = []
            def update_logs(msg, level="info"):
                icon = "🟢" if level == "success" else "🟠" if level == "warning" else "🔴" if level == "error" else "🔵"
                logs.insert(0, f"{icon} {msg}")
                log_box.code("\n".join(logs[:15]), language="text")

            counts = {"saved": 0, "linked": 0, "ignored": 0}

            def run_scrape_job(idx, total_idx, r, d):
                time.sleep(random.uniform(0.5, 2.5))
                while True:
                    scraper = GoogleMapsScraper(headless=headless)
                    try:
                        def progress_callback(data):
                            if data["status"] == "error":
                                update_logs(f"[{d}-{r}] ⚠️ {data['message']}", "error")
                                return
                            if data["status"] == "info":
                                update_logs(f"[{d}-{r}] ⏳ {data['message']}", "info")
                                return
                            if data["status"] == "ignored":
                                counts["ignored"] += 1
                            if data["status"] == "progress":
                                lead = data["data"]
                                is_new = data.get("is_new", False)
                                if is_new:
                                    counts["saved"] += 1
                                    update_logs(f"Extrait : {lead['nom']} ({lead['opportunite']})", "success")
                                else:
                                    counts["linked"] += 1
                                    update_logs(f"Doublon : {lead['nom']}", "warning")

                        scraper.scrape(country, r, d, max_scrolls=max_scrolls, focus_no_website=focus_no_website, webhook_url=webhook_url, js_rendering=js_rendering, callback=progress_callback)
                        save_checkpoint(country, r, d)
                        break
                    except Exception as e:
                        update_logs(f"[{d}-{r}] 🚨 Crash du robot : {e}. Tentative de reprise...", "error")
                        wait_for_internet()
                        update_logs(f"[{d}-{r}] 🌐 Reprise du processus de secours...", "warning")
                    finally:
                        try: scraper.close()
                        except: pass

            try:
                ctx = get_script_run_ctx()
                
                def run_with_ctx(idx, total_idx, r, d):
                    add_script_run_ctx(ctx=ctx)
                    run_scrape_job(idx, total_idx, r, d)

                with st.spinner("🚀 Propulsion des Moteurs d'Extraction (Ultra-Vitesse)..."):
                    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                        futures = []
                        for idx, (r, d) in enumerate(combinations):
                            future = executor.submit(run_with_ctx, idx, len(combinations), r, d)
                            futures.append(future)
                            
                        for i, future in enumerate(concurrent.futures.as_completed(futures)):
                            global_status.markdown(f"**Tâche complétée {i+1}/{len(combinations)}**")
                            progress_bar.progress((i+1) / len(combinations))

                st.balloons()
                global_status.markdown(f"**✅ Protocole d'Extraction Terminé avec Succès.**")
                progress_bar.progress(1.0)
                st.success(f"🎉 Bilan : {counts['saved']} insérés, {counts['linked']} doublons, {counts['ignored']} ignorés.")
            except Exception as e:
                st.error(f"Erreur Fatale : {e}")

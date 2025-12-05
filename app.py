import streamlit as st
import pandas as pd
from scraper import AuchanScraper
import time

# Configuration de la page
st.set_page_config(
    page_title="INFOTHOR - Extracteur Auchan",
    page_icon="🦊",
    layout="wide"
)

# Titre
st.title("🦊 INFOTHOR - Extracteur de Commandes Auchan")
st.markdown("---")

# Zone de logs
log_container = st.empty()
logs = []

def add_log(message, status="info"):
    """Ajoute un log avec timestamp"""
    timestamp = time.strftime("%H:%M:%S")
    icon = {
        "info": "ℹ️",
        "success": "✅",
        "warning": "⚠️",
        "error": "❌",
        "loading": "⏳"
    }.get(status, "ℹ️")
    
    logs.append(f"[{timestamp}] {icon} {message}")
    log_container.markdown("\n".join(logs))

# Bouton d'extraction
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    if st.button("🚀 EXTRAIRE LES COMMANDES", type="primary", use_container_width=True):
        logs.clear()
        
        try:
            # Récupération des credentials depuis secrets
            add_log("Chargement des identifiants...", "loading")
            
            email = st.secrets.get("AUCHAN_EMAIL", "")
            password = st.secrets.get("AUCHAN_PASSWORD", "")
            
            if not email or not password:
                add_log("❌ ERREUR : Identifiants manquants dans les secrets Streamlit", "error")
                st.error("⚠️ Configurez AUCHAN_EMAIL et AUCHAN_PASSWORD dans les secrets Streamlit")
                st.stop()
            
            add_log("Identifiants chargés avec succès", "success")
            
            # Initialisation du scraper
            add_log("Initialisation du navigateur Firefox...", "loading")
            scraper = AuchanScraper(email, password, headless=True)
            
            add_log("Firefox démarré avec succès", "success")
            
            # Vérifier si déjà connecté
            add_log("Vérification de la session...", "loading")
            if scraper.is_already_logged_in():
                add_log("✅ Déjà connecté ! Pas besoin de login", "success")
            else:
                add_log("Session expirée, connexion nécessaire", "info")
                
                # Connexion
                add_log("Navigation vers la page de connexion...", "loading")
                scraper.navigate_to_login()
                add_log("Page de connexion chargée", "success")
                
                add_log("Authentification en cours...", "loading")
                scraper.login()
                add_log("Authentification réussie ✓", "success")
                
                # Navigation vers commandes
                add_log("Navigation vers la liste des commandes...", "loading")
                scraper.navigate_to_orders()
                add_log("Page des commandes chargée", "success")
            
            # Réinitialisation des filtres
            add_log("Réinitialisation des filtres...", "loading")
            scraper.reset_filters()
            add_log("Filtres réinitialisés", "success")
            
            # Configuration de la pagination
            add_log("Configuration : 100 lignes par page...", "loading")
            scraper.set_pagination(100)
            add_log("Pagination configurée", "success")
            
            # Tri par date de création
            add_log("Tri par date de création (décroissant)...", "loading")
            scraper.sort_by_creation_date()
            add_log("Tri appliqué", "success")
            
            # Extraction des données
            add_log("Extraction des 20 premières commandes...", "loading")
            data = scraper.extract_orders(limit=20)
            add_log(f"✅ {len(data)} commandes extraites avec succès !", "success")
            
            # Fermeture du navigateur
            scraper.close()
            add_log("Navigateur fermé", "info")
            
            # Affichage des résultats
            st.markdown("---")
            st.subheader(f"📊 Résultats : {len(data)} commandes")
            
            if data:
                df = pd.DataFrame(data)
                
                # Affichage du tableau
                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "numero": st.column_config.TextColumn("Numéro", width="small"),
                        "client": st.column_config.TextColumn("Client", width="medium"),
                        "livrer_a": st.column_config.TextColumn("Livrer à", width="medium"),
                        "creation_le": st.column_config.TextColumn("Création", width="small"),
                        "livrer_le": st.column_config.TextColumn("Livraison", width="small"),
                        "gln": st.column_config.TextColumn("GLN", width="medium"),
                        "montant": st.column_config.NumberColumn("Montant", width="small", format="%.2f €"),
                        "statut": st.column_config.TextColumn("Statut", width="small")
                    }
                )
                
                # Bouton de téléchargement CSV
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Télécharger en CSV",
                    data=csv,
                    file_name=f"commandes_auchan_{time.strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.warning("Aucune commande trouvée")
                
        except Exception as e:
            add_log(f"❌ ERREUR : {str(e)}", "error")
            st.error(f"⚠️ Une erreur s'est produite : {str(e)}")
            
            # Tentative de fermeture du navigateur en cas d'erreur
            try:
                if 'scraper' in locals():
                    scraper.close()
            except:
                pass

# Informations dans la sidebar
with st.sidebar:
    st.markdown("### ℹ️ À propos")
    st.markdown("""
    **INFOTHOR** est un extracteur automatique de commandes depuis la plateforme Auchan.
    
    **Configuration requise :**
    - Firefox installé
    - Geckodriver installé
    - Secrets Streamlit configurés
    
    **Secrets nécessaires :**
    - `AUCHAN_EMAIL`
    - `AUCHAN_PASSWORD`
    """)
    
    st.markdown("---")
    st.markdown("### 🔧 Fonctionnalités")
    st.markdown("""
    - ✅ Connexion automatique
    - ✅ Reset des filtres
    - ✅ Pagination (100 lignes)
    - ✅ Tri par date
    - ✅ Export CSV
    - ✅ Logs en temps réel
    """)
    
    st.markdown("---")
    st.markdown("**Version 1.0** | 🦊 Firefox + Selenium")

import streamlit as st
import pandas as pd
from scraper import AuchanScraper
from datetime import datetime
import time
import os

# Configuration de la page
st.set_page_config(
    page_title="INFOTHOR - Extracteur Commandes",
    page_icon="⚡",
    layout="wide"
)

# Fonction pour récupérer les identifiants (compatible Streamlit Cloud ET Render)
def get_credentials():
    """Récupère les identifiants depuis secrets Streamlit ou variables d'environnement"""
    try:
        # Essayer secrets Streamlit d'abord
        login = st.secrets["auchan"]["login"]
        password = st.secrets["auchan"]["password"]
        return login, password, "Streamlit Secrets"
    except:
        # Sinon, essayer variables d'environnement (Render)
        login = os.environ.get("AUCHAN_LOGIN")
        password = os.environ.get("AUCHAN_PASSWORD")
        
        if login and password:
            return login, password, "Environment Variables"
        else:
            return None, None, "Non configuré"

# Style CSS personnalisé
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        color: #E30613;
        font-weight: bold;
        margin-bottom: 1rem;
    }
    .status-box {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #d4edda;
        border-left: 5px solid #28a745;
    }
    .error-box {
        background-color: #f8d7da;
        border-left: 5px solid #dc3545;
    }
    .info-box {
        background-color: #d1ecf1;
        border-left: 5px solid #0c5460;
    }
    </style>
""", unsafe_allow_html=True)

# Titre principal
st.markdown('<p class="main-header">⚡ INFOTHOR - Extracteur de Commandes</p>', unsafe_allow_html=True)

# Initialisation de la session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'orders_data' not in st.session_state:
    st.session_state.orders_data = None
if 'last_update' not in st.session_state:
    st.session_state.last_update = None

# Sidebar pour la connexion
with st.sidebar:
    st.header("🔐 Connexion")
    
    # Récupération des identifiants depuis secrets ou env vars
    login, password, source = get_credentials()
    
    if login and password:
        st.success(f"✅ Identifiants chargés")
        st.caption(f"Source: {source}")
    else:
        st.error("❌ Erreur : Identifiants non configurés")
        st.info("Configurez AUCHAN_LOGIN et AUCHAN_PASSWORD dans les variables d'environnement")
    
    st.divider()
    
    # Bouton de connexion/extraction
    if st.button("🚀 Extraire les commandes", type="primary", use_container_width=True):
        if not login or not password:
            st.error("❌ Secrets non configurés")
        else:
            # Container pour afficher les étapes en temps réel
            steps_container = st.empty()
            progress_bar = st.progress(0)
            
            # Liste pour stocker les étapes
            steps_display = []
            
            def update_progress(log_entry):
                """Callback pour afficher les étapes en temps réel"""
                status_colors = {
                    'success': '🟢',
                    'error': '🔴',
                    'warning': '🟡',
                    'info': '🔵'
                }
                icon = status_colors.get(log_entry['status'], '⚪')
                
                step_text = f"{icon} {log_entry['step']}"
                if log_entry['details']:
                    step_text += f"\n   ↳ *{log_entry['details']}*"
                
                steps_display.append(step_text)
                
                # Afficher toutes les étapes
                with steps_container.container():
                    for step in steps_display[-10:]:  # Afficher les 10 dernières étapes
                        st.text(step)
            
            try:
                # Créer le scraper avec callback
                scraper = AuchanScraper(login, password, progress_callback=update_progress)
                
                progress_bar.progress(10)
                
                # Processus de connexion
                if scraper.login():
                    progress_bar.progress(50)
                    
                    # Extraction des commandes
                    orders = scraper.extract_orders()
                    progress_bar.progress(90)
                    
                    if orders and len(orders) > 0:
                        st.session_state.orders_data = orders
                        st.session_state.last_update = datetime.now()
                        st.session_state.logged_in = True
                        progress_bar.progress(100)
                        
                        time.sleep(0.5)
                        steps_container.empty()
                        progress_bar.empty()
                        
                        st.success(f"✅ {len(orders)} commandes extraites avec succès !")
                        st.balloons()
                    else:
                        progress_bar.empty()
                        st.warning("⚠️ Aucune commande trouvée")
                        
                        # Suggestion si aucune commande
                        with st.expander("💡 Suggestions"):
                            st.markdown("""
                            **Pourquoi aucune commande ?**
                            - Le tableau est peut-être vide sur le site
                            - La structure HTML a peut-être changé
                            - Des filtres sont peut-être encore actifs
                            
                            **Actions possibles :**
                            1. Vérifiez manuellement sur le site qu'il y a bien des commandes
                            2. Consultez le log détaillé ci-dessous
                            3. Réessayez l'extraction
                            """)
                else:
                    progress_bar.empty()
                    st.error("❌ Impossible de se connecter")
                    
                    # Afficher suggestions en cas d'échec
                    with st.expander("💡 Que faire ?"):
                        st.markdown("""
                        **Le mode secours a été testé automatiquement.**
                        
                        Si l'échec persiste :
                        1. ✅ Vérifiez vos identifiants dans les Secrets
                        2. ✅ Testez la connexion manuelle sur le site
                        3. ✅ Vérifiez que le site est accessible
                        4. 📋 Consultez le log détaillé ci-dessous
                        
                        **Note :** Si vous êtes déjà connecté sur le site dans votre navigateur,
                        le processus devrait fonctionner via le mode secours.
                        """)
                
                scraper.close()
                
                # Afficher le log complet dans un expander
                with st.expander("📋 Voir le log détaillé complet"):
                    for log in scraper.get_steps_log():
                        status_emoji = {
                            'success': '✅',
                            'error': '❌', 
                            'warning': '⚠️',
                            'info': 'ℹ️'
                        }
                        st.text(f"{status_emoji.get(log['status'], '•')} {log['step']}")
                        if log['details']:
                            st.caption(f"   {log['details']}")
                
            except Exception as e:
                progress_bar.empty()
                st.error(f"❌ Erreur inattendue: {str(e)}")
                with st.expander("🔍 Détails de l'erreur"):
                    st.exception(e)
    
    # Informations sur la dernière mise à jour
    if st.session_state.last_update:
        st.divider()
        st.caption(f"🕐 Dernière extraction: {st.session_state.last_update.strftime('%H:%M:%S')}")
        
        if st.button("🔄 Rafraîchir", use_container_width=True):
            st.session_state.orders_data = None
            st.session_state.last_update = None
            st.rerun()

# Zone principale - Affichage des données
if st.session_state.orders_data is not None:
    df = pd.DataFrame(st.session_state.orders_data)
    
    # Statistiques en haut
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📦 Total commandes", len(df))
    
    with col2:
        if 'montant_calcule' in df.columns:
            total_amount = df['montant_calcule'].astype(str).str.replace(',', '.').astype(float).sum()
            st.metric("💰 Montant total", f"{total_amount:.2f} €")
        else:
            st.metric("💰 Montant total", "N/A")
    
    with col3:
        if 'client' in df.columns:
            unique_clients = df['client'].nunique()
            st.metric("👥 Clients uniques", unique_clients)
        else:
            st.metric("👥 Clients uniques", "N/A")
    
    with col4:
        if 'livrer_le' in df.columns:
            pending_deliveries = len(df[pd.to_datetime(df['livrer_le'], errors='coerce') >= pd.Timestamp.now()])
            st.metric("🚚 Livraisons à venir", pending_deliveries)
        else:
            st.metric("🚚 Livraisons à venir", "N/A")
    
    st.divider()
    
    # Filtres
    st.subheader("🔍 Filtres")
    
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    
    with filter_col1:
        if 'client' in df.columns:
            clients = ['Tous'] + sorted(df['client'].unique().tolist())
            selected_client = st.selectbox("Client", clients)
        else:
            selected_client = 'Tous'
    
    with filter_col2:
        if 'livrer_a' in df.columns:
            livrer_a = ['Tous'] + sorted(df['livrer_a'].unique().tolist())
            selected_livrer_a = st.selectbox("Livrer à", livrer_a)
        else:
            selected_livrer_a = 'Tous'
    
    with filter_col3:
        search_term = st.text_input("🔍 Recherche (numéro, GLN...)", "")
    
    # Application des filtres
    filtered_df = df.copy()
    
    if selected_client != 'Tous':
        filtered_df = filtered_df[filtered_df['client'] == selected_client]
    
    if selected_livrer_a != 'Tous':
        filtered_df = filtered_df[filtered_df['livrer_a'] == selected_livrer_a]
    
    if search_term:
        mask = filtered_df.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)
        filtered_df = filtered_df[mask]
    
    st.info(f"📊 Affichage de {len(filtered_df)} commande(s) sur {len(df)}")
    
    # Affichage du tableau
    st.dataframe(
        filtered_df,
        use_container_width=True,
        height=600,
        column_config={
            "numero": st.column_config.TextColumn("Numéro", width="small"),
            "client": st.column_config.TextColumn("Client", width="medium"),
            "livrer_a": st.column_config.TextColumn("Livrer à", width="medium"),
            "creation_le": st.column_config.DateColumn("Création", width="small"),
            "livrer_le": st.column_config.DateColumn("Livraison", width="small"),
            "gln_commande_par": st.column_config.TextColumn("GLN Commande", width="medium"),
            "montant_calcule": st.column_config.NumberColumn("Montant", width="small", format="%.2f €"),
            "statut": st.column_config.TextColumn("Statut", width="small"),
        }
    )
    
    # Boutons d'export
    st.divider()
    st.subheader("💾 Export des données")
    
    export_col1, export_col2, export_col3 = st.columns(3)
    
    with export_col1:
        # Export CSV
        csv = filtered_df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 Télécharger CSV",
            data=csv,
            file_name=f"infothor_commandes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with export_col2:
        # Export Excel
        from io import BytesIO
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            filtered_df.to_excel(writer, sheet_name='Commandes', index=False)
        
        st.download_button(
            label="📥 Télécharger Excel",
            data=buffer.getvalue(),
            file_name=f"infothor_commandes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    with export_col3:
        # Export JSON
        json_str = filtered_df.to_json(orient='records', force_ascii=False, indent=2)
        st.download_button(
            label="📥 Télécharger JSON",
            data=json_str,
            file_name=f"infothor_commandes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )

else:
    # Message d'accueil si pas de données
    st.markdown("""
    <div class="info-box">
        <h3>👋 Bienvenue sur INFOTHOR !</h3>
        <p>Système d'extraction automatique des commandes</p>
        <ol>
            <li>Vérifiez que les secrets sont configurés (barre latérale)</li>
            <li>Cliquez sur "🚀 Extraire les commandes"</li>
            <li>Consultez et filtrez vos données</li>
            <li>Exportez les résultats au format souhaité</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    # Instructions pour la configuration
    with st.expander("⚙️ Configuration des secrets Streamlit Cloud"):
        st.markdown("""
        ### Configuration des identifiants
        
        Dans les paramètres de votre app Streamlit Cloud :
        
        1. Allez dans **Settings** → **Secrets**
        2. Ajoutez le contenu suivant :
        
        ```toml
        [auchan]
        login = "bakfrance@baktat.com"
        password = "votre_mot_de_passe"
        ```
        
        3. Cliquez sur **Save**
        4. L'application va redémarrer automatiquement
        """)
    
    with st.expander("📖 Guide d'utilisation"):
        st.markdown("""
        ### Fonctionnalités INFOTHOR :
        
        - ⚡ Extraction automatique ultra-rapide
        - 🔍 Filtrage avancé multi-critères
        - 📊 Statistiques en temps réel
        - 💾 Export CSV, Excel, JSON
        - 🔐 Connexion sécurisée
        
        ### Prochaines versions :
        
        - 🎨 Code couleur DESADV/SSCC
        - 🔔 Notifications automatiques
        - 📈 Tableaux de bord analytics
        - 🌐 Support multi-sites
        """)

# Footer
st.divider()
st.caption("⚡ INFOTHOR v1.0 - Automatisation du traitement des commandes")

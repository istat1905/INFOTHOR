import streamlit as st
import pandas as pd
# On garde l'import scraper au cas où tu utilises la méthode serveur en backup, 
# sinon tu peux le commenter si tu n'utilises que Tampermonkey
# from scraper import AuchanScraper 
from datetime import datetime
import json
import base64
import os

# Configuration de la page
st.set_page_config(
    page_title="INFOTHOR - Extracteur Commandes",
    page_icon="⚡",
    layout="wide"
)

# --- FONCTIONS UTILITAIRES ---

def decode_data_from_url():
    """Décode les données envoyées depuis Tampermonkey via URL"""
    try:
        query_params = st.query_params
        if "data" in query_params:
            compressed = query_params["data"]
            json_string = base64.b64decode(compressed).decode('utf-8')
            orders = json.loads(json_string)
            return orders
        return None
    except Exception as e:
        st.error(f"Erreur décodage données : {str(e)}")
        return None

# --- STYLE CSS ---
st.markdown("""
    <style>
    .main-header { font-size: 2.5rem; color: #E30613; font-weight: bold; margin-bottom: 0rem; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if 'orders_data' not in st.session_state:
    st.session_state.orders_data = None
if 'last_update' not in st.session_state:
    st.session_state.last_update = None

# --- HEADER & LOGIQUE DE RÉCEPTION ---
st.markdown('<p class="main-header">⚡ INFOTHOR</p>', unsafe_allow_html=True)

# Vérifier réception données
incoming_data = decode_data_from_url()
if incoming_data:
    st.session_state.orders_data = incoming_data
    st.session_state.last_update = datetime.now()
    st.toast(f"✅ {len(incoming_data)} commandes reçues !", icon="🎉")
    st.query_params.clear() # Nettoyer l'URL

# --- INTERFACE DE COMMANDE ---

col_btn, col_info = st.columns([1, 3])

with col_btn:
    # URL Cible : Ajout du paramètre ?autostart=true pour déclencher Tampermonkey
    auchan_url = "https://auchan.atgpedi.net/gui.php?page=documents_commandes_liste&autostart=true"
    
    # Bouton qui ouvre l'onglet Auchan et déclenche le script
    st.link_button("🚀 LANCER L'EXTRACTION", min_width=200, url=auchan_url, type="primary", help="Ouvre Auchan et lance l'extraction automatique")

with col_info:
    if st.session_state.last_update:
        st.caption(f"Dernière mise à jour : {st.session_state.last_update.strftime('%H:%M:%S')}")
    else:
        st.info("Cliquez sur le bouton pour récupérer les commandes depuis Auchan.")

st.divider()

# --- AFFICHAGE DES DONNÉES ---
if st.session_state.orders_data is not None:
    df = pd.DataFrame(st.session_state.orders_data)
    
    # Métriques
    m1, m2, m3 = st.columns(3)
    m1.metric("Commandes", len(df))
    if 'montant_calcule' in df.columns:
        total = df['montant_calcule'].astype(str).str.replace(',', '.').astype(float).sum()
        m2.metric("Total €", f"{total:.2f} €")
    if 'livrer_le' in df.columns:
        a_venir = len(df[pd.to_datetime(df['livrer_le'], errors='coerce') >= pd.Timestamp.now()])
        m3.metric("A livrer", a_venir)

    # Tableau
    st.dataframe(
        df, 
        use_container_width=True, 
        height=600,
        column_config={
            "montant_calcule": st.column_config.NumberColumn("Montant", format="%.2f €"),
        }
    )
    
    # Exports
    col_dl1, col_dl2 = st.columns(2)
    csv = df.to_csv(index=False).encode('utf-8')
    col_dl1.download_button("📥 CSV", csv, "commandes.csv", "text/csv", use_container_width=True)
    
    json_str = df.to_json(orient='records', force_ascii=False)
    col_dl2.download_button("📥 JSON", json_str, "commandes.json", "application/json", use_container_width=True)

else:
    st.empty() # Page vide si pas de données

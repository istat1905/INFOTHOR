import streamlit as st
import pandas as pd
from datetime import datetime
import json
import base64
from streamlit.components.v1 import html

st.set_page_config(page_title="INFOTHOR", page_icon="⚡", layout="wide")

# Décodage données
def decode_data():
    try:
        if "data" in st.query_params:
            compressed = st.query_params["data"]
            json_string = base64.b64decode(compressed).decode('utf-8')
            return json.loads(json_string)
    except:
        pass
    return None

# Style CSS
st.markdown("""
<style>
.main-header {font-size: 2.5rem; color: #E30613; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-header">⚡ INFOTHOR</p>', unsafe_allow_html=True)

# Check données entrantes
incoming = decode_data()
if incoming:
    st.session_state.orders_data = incoming
    st.session_state.last_update = datetime.now()
    st.success(f"✅ {len(incoming)} commandes reçues")
    st.balloons()
    st.query_params.clear()

# Init session
if 'orders_data' not in st.session_state:
    st.session_state.orders_data = None
if 'last_update' not in st.session_state:
    st.session_state.last_update = None

# Composant HTML avec iframe et extraction
extraction_component = """
<div id="extraction-container">
    <iframe id="auchan-iframe" 
            src="https://auchan.atgpedi.net/gui.php?page=documents_commandes_liste" 
            style="display: none; width: 100%; height: 600px; border: 1px solid #ccc;">
    </iframe>
    
    <div style="padding: 20px; text-align: center;">
        <button id="extract-btn" 
                style="padding: 15px 30px; font-size: 18px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                       color: white; border: none; border-radius: 10px; cursor: pointer; font-weight: bold;">
            ⚡ EXTRAIRE LES COMMANDES
        </button>
        
        <div id="status" style="margin-top: 20px; font-size: 16px; color: #666;"></div>
        
        <label style="display: block; margin-top: 20px;">
            <input type="checkbox" id="show-iframe"> Afficher l'iframe (debug)
        </label>
    </div>
</div>

<script>
const iframe = document.getElementById('auchan-iframe');
const btn = document.getElementById('extract-btn');
const status = document.getElementById('status');
const showIframeCheckbox = document.getElementById('show-iframe');

// Toggle iframe visibility
showIframeCheckbox.addEventListener('change', (e) => {
    iframe.style.display = e.target.checked ? 'block' : 'none';
});

// Fonction d'extraction depuis l'iframe
function extractFromIframe() {
    try {
        const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
        const tbody = iframeDoc.querySelector('tbody');
        
        if (!tbody) {
            status.textContent = '❌ Tableau non trouvé. Êtes-vous connecté ?';
            return null;
        }
        
        const orders = [];
        const rows = tbody.querySelectorAll('tr');
        
        rows.forEach(row => {
            const cells = row.querySelectorAll('td');
            if (cells.length < 8) return;
            
            const order = {
                numero: cells[1]?.innerText?.trim() || '',
                client: cells[2]?.innerText?.trim() || '',
                livrer_a: cells[3]?.innerText?.trim() || '',
                creation_le: cells[4]?.innerText?.trim() || '',
                livrer_le: cells[5]?.innerText?.trim() || '',
                gln_commande_par: cells[6]?.innerText?.trim() || '',
                montant_calcule: cells[7]?.innerText?.trim() || '',
                statut: cells[8]?.innerText?.trim() || ''
            };
            
            if (order.numero && order.numero.length > 3) {
                orders.push(order);
            }
        });
        
        return orders;
    } catch (error) {
        console.error('Erreur extraction:', error);
        status.textContent = '❌ Erreur: ' + error.message;
        return null;
    }
}

// Envoi des données à Streamlit
function sendToStreamlit(orders) {
    const compressed = btoa(unescape(encodeURIComponent(JSON.stringify(orders))));
    const currentUrl = window.location.href.split('?')[0];
    window.location.href = currentUrl + '?data=' + encodeURIComponent(compressed);
}

// Bouton d'extraction
btn.addEventListener('click', () => {
    status.textContent = '🔄 Extraction en cours...';
    btn.disabled = true;
    
    // Attendre que l'iframe soit chargée
    setTimeout(() => {
        const orders = extractFromIframe();
        
        if (orders && orders.length > 0) {
            status.textContent = `✅ ${orders.length} commandes extraites !`;
            setTimeout(() => sendToStreamlit(orders), 500);
        } else {
            status.textContent = '❌ Aucune commande trouvée';
            btn.disabled = false;
        }
    }, 2000);
});

// Message de chargement initial
iframe.addEventListener('load', () => {
    status.textContent = '✅ Iframe chargée. Cliquez pour extraire.';
});

status.textContent = '⏳ Chargement iframe...';
</script>
"""

# Sidebar
with st.sidebar:
    st.header("📋 INFOTHOR")
    
    if st.session_state.last_update:
        st.success(f"🕐 {st.session_state.last_update.strftime('%H:%M:%S')}")
        if st.button("🔄 Reset"):
            st.session_state.orders_data = None
            st.session_state.last_update = None
            st.rerun()
    
    st.divider()
    st.caption("⚡ Version iframe")

# Affichage
if st.session_state.orders_data:
    df = pd.DataFrame(st.session_state.orders_data)
    
    # Stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📦 Commandes", len(df))
    with col2:
        if 'montant_calcule' in df.columns:
            total = df['montant_calcule'].astype(str).str.replace(',', '.').astype(float).sum()
            st.metric("💰 Total", f"{total:.2f} €")
    with col3:
        if 'client' in df.columns:
            st.metric("👥 Clients", df['client'].nunique())
    with col4:
        if 'livrer_le' in df.columns:
            pending = len(df[pd.to_datetime(df['livrer_le'], errors='coerce') >= pd.Timestamp.now()])
            st.metric("🚚 À livrer", pending)
    
    st.divider()
    
    # Filtres
    col1, col2, col3 = st.columns(3)
    
    with col1:
        clients = ['Tous'] + sorted(df['client'].unique().tolist()) if 'client' in df.columns else ['Tous']
        client_filter = st.selectbox("Client", clients)
    
    with col2:
        livrer = ['Tous'] + sorted(df['livrer_a'].unique().tolist()) if 'livrer_a' in df.columns else ['Tous']
        livrer_filter = st.selectbox("Livrer à", livrer)
    
    with col3:
        search = st.text_input("🔍 Recherche")
    
    # Filtrage
    filtered = df.copy()
    if client_filter != 'Tous':
        filtered = filtered[filtered['client'] == client_filter]
    if livrer_filter != 'Tous':
        filtered = filtered[filtered['livrer_a'] == livrer_filter]
    if search:
        mask = filtered.astype(str).apply(lambda x: x.str.contains(search, case=False, na=False)).any(axis=1)
        filtered = filtered[mask]
    
    st.info(f"📊 {len(filtered)} / {len(df)} commandes")
    
    # Tableau
    st.dataframe(filtered, use_container_width=True, height=600)
    
    # Export
    st.divider()
    col1, col2, col3 = st.columns(3)
    
    with col1:
        csv = filtered.to_csv(index=False, encoding='utf-8-sig')
        st.download_button("📥 CSV", csv, f"infothor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", "text/csv", use_container_width=True)
    
    with col2:
        from io import BytesIO
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            filtered.to_excel(writer, sheet_name='Commandes', index=False)
        st.download_button("📥 Excel", buffer.getvalue(), f"infothor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx", use_container_width=True)
    
    with col3:
        json_str = filtered.to_json(orient='records', force_ascii=False, indent=2)
        st.download_button("📥 JSON", json_str, f"infothor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", use_container_width=True)

else:
    # Afficher le composant d'extraction
    html(extraction_component, height=700)
    
    st.divider()
    
    st.warning("""
    ⚠️ **Important** : 
    - Connectez-vous d'abord sur Auchan dans un autre onglet
    - Les cookies de session doivent être partagés
    - Si l'iframe est bloquée, utilisez la méthode Tampermonkey
    """)

st.divider()
st.caption("⚡ INFOTHOR v3.0 - Extraction iframe")

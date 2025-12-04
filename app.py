import streamlit as st
import pandas as pd
from datetime import datetime
import json
import base64
from streamlit.components.v1 import html

st.set_page_config(page_title="INFOTHOR", page_icon="⚡", layout="wide")

# Style CSS
st.markdown("""
<style>
.main-header {font-size: 2.5rem; color: #E30613; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-header">⚡ INFOTHOR</p>', unsafe_allow_html=True)

# Init session
if 'orders_data' not in st.session_state:
    st.session_state.orders_data = None
if 'last_update' not in st.session_state:
    st.session_state.last_update = None
if 'auchan_window_opened' not in st.session_state:
    st.session_state.auchan_window_opened = False

# Composant HTML avec communication inter-onglets
extraction_component = """
<div style="padding: 20px;">
    <div style="text-align: center; margin-bottom: 30px;">
        <button id="open-auchan-btn" 
                style="padding: 15px 30px; font-size: 18px; background: #10b981; 
                       color: white; border: none; border-radius: 10px; cursor: pointer; 
                       font-weight: bold; margin-right: 10px;">
            🌐 1. OUVRIR AUCHAN
        </button>
        
        <button id="extract-btn" 
                style="padding: 15px 30px; font-size: 18px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                       color: white; border: none; border-radius: 10px; cursor: pointer; font-weight: bold;"
                disabled>
            ⚡ 2. EXTRAIRE
        </button>
    </div>
    
    <div id="status" style="padding: 15px; background: #f3f4f6; border-radius: 10px; 
                             text-align: center; font-size: 16px; color: #374151;">
        📋 Cliquez sur "OUVRIR AUCHAN" pour commencer
    </div>
</div>

<script>
let auchanWindow = null;
const openBtn = document.getElementById('open-auchan-btn');
const extractBtn = document.getElementById('extract-btn');
const status = document.getElementById('status');

// Ouvrir l'onglet Auchan
openBtn.addEventListener('click', () => {
    auchanWindow = window.open(
        'https://auchan.atgpedi.net/gui.php?page=documents_commandes_liste',
        'auchan_tab'
    );
    
    if (auchanWindow) {
        status.innerHTML = '✅ Onglet Auchan ouvert !<br>Connectez-vous si nécessaire, puis cliquez sur EXTRAIRE';
        extractBtn.disabled = false;
        extractBtn.style.opacity = '1';
        openBtn.style.opacity = '0.5';
    } else {
        status.innerHTML = '❌ Erreur: Autorisez les popups pour ce site';
    }
});

// Extraire les données
extractBtn.addEventListener('click', () => {
    if (!auchanWindow || auchanWindow.closed) {
        status.innerHTML = '❌ L\'onglet Auchan est fermé. Cliquez sur OUVRIR AUCHAN.';
        extractBtn.disabled = true;
        openBtn.style.opacity = '1';
        return;
    }
    
    status.innerHTML = '🔄 Extraction en cours...';
    extractBtn.disabled = true;
    
    // Vérifier localStorage périodiquement
    localStorage.removeItem('infothor_data');
    
    // Envoyer commande d'extraction
    auchanWindow.postMessage({
        action: 'EXTRACT_ORDERS'
    }, 'https://auchan.atgpedi.net');
    
    // Polling localStorage
    let attempts = 0;
    const checkData = setInterval(() => {
        attempts++;
        
        const data = localStorage.getItem('infothor_data');
        
        if (data) {
            clearInterval(checkData);
            const parsed = JSON.parse(data);
            
            if (parsed.orders && parsed.orders.length > 0) {
                status.innerHTML = `✅ ${parsed.orders.length} commandes extraites ! Redirection...`;
                
                // Envoyer à Streamlit
                const compressed = btoa(unescape(encodeURIComponent(JSON.stringify(parsed.orders))));
                const currentUrl = window.location.href.split('?')[0];
                
                setTimeout(() => {
                    window.location.href = currentUrl + '?data=' + encodeURIComponent(compressed);
                }, 1000);
            } else {
                status.innerHTML = '⚠️ Aucune commande trouvée. Êtes-vous sur la bonne page ?';
                extractBtn.disabled = false;
            }
        } else if (attempts > 20) {
            clearInterval(checkData);
            status.innerHTML = '❌ Timeout. Vérifiez que le script Tampermonkey est actif.';
            extractBtn.disabled = false;
        }
    }, 500);
});

// Raccourci clavier Ctrl+Shift+E
document.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.shiftKey && e.key === 'E') {
        e.preventDefault();
        if (!extractBtn.disabled) {
            extractBtn.click();
        }
    }
});

console.log('✅ INFOTHOR Interface chargée');
</script>
"""

# Décodage données
incoming = None
if "data" in st.query_params:
    try:
        compressed = st.query_params["data"]
        json_string = base64.b64decode(compressed).decode('utf-8')
        incoming = json.loads(json_string)
    except:
        pass

if incoming:
    st.session_state.orders_data = incoming
    st.session_state.last_update = datetime.now()
    st.success(f"✅ {len(incoming)} commandes reçues !")
    st.balloons()
    st.query_params.clear()
    st.rerun()

# Sidebar
with st.sidebar:
    st.header("⚡ INFOTHOR")
    
    if st.session_state.last_update:
        st.success(f"🕐 {st.session_state.last_update.strftime('%H:%M:%S')}")
        st.metric("📦 Commandes", len(st.session_state.orders_data) if st.session_state.orders_data else 0)
        
        if st.button("🔄 Nouvelle extraction", use_container_width=True):
            st.session_state.orders_data = None
            st.session_state.last_update = None
            st.rerun()
    else:
        st.info("En attente d'extraction...")
    
    st.divider()
    
    st.markdown("""
    **Instructions:**
    1. Cliquez "OUVRIR AUCHAN"
    2. Connectez-vous (si nécessaire)
    3. Cliquez "EXTRAIRE"
    
    **Raccourci:** Ctrl+Shift+E
    """)

# Affichage données
if st.session_state.orders_data:
    df = pd.DataFrame(st.session_state.orders_data)
    
    # Stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📦 Total", len(df))
    with col2:
        if 'montant_calcule' in df.columns:
            total = df['montant_calcule'].astype(str).str.replace(',', '.').astype(float).sum()
            st.metric("💰 Montant", f"{total:.2f} €")
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
    
    st.info(f"📊 Affichage: {len(filtered)} / {len(df)}")
    
    # Tableau
    st.dataframe(filtered, use_container_width=True, height=600)
    
    # Export
    st.divider()
    col1, col2, col3 = st.columns(3)
    
    with col1:
        csv = filtered.to_csv(index=False, encoding='utf-8-sig')
        st.download_button("📥 CSV", csv, f"infothor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", use_container_width=True)
    
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
    # Interface d'extraction
    html(extraction_component, height=200)

st.divider()
st.caption("⚡ INFOTHOR v3.0 - Communication inter-onglets")

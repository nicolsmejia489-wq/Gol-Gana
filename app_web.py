import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import time

# ==============================================================================
# 1. CONFIGURACIÓN E IDENTIDAD
# ==============================================================================
st.set_page_config(page_title="Gol Gana", layout="centered", page_icon="⚽")

# --- ASSETS GRÁFICOS ---
URL_FONDO_BASE = "https://res.cloudinary.com/dlvczeqlp/image/upload/v1769030979/fondo_base_l7i0k6.png"
URL_PORTADA = "https://res.cloudinary.com/dlvczeqlp/image/upload/v1769050565/a906a330-8b8c-4b52-b131-8c75322bfc10_hwxmqb.png"
COLOR_MARCA = "#FFD700"  # Dorado Gol Gana

# ==============================================================================
# 2. GESTIÓN DE CONEXIÓN A BASE DE DATOS (A PRUEBA DE FALLOS)
# ==============================================================================
@st.cache_resource
def get_db_connection():
    # INTENTO 1: Buscar en st.secrets (Producción / Local bien configurado)
    try:
        # Verificamos si existe el archivo de secretos
        if hasattr(st, "secrets") and "connections" in st.secrets:
            db_url = st.secrets["connections"]["postgresql"]["url"]
            return create_engine(db_url, pool_pre_ping=True)
    except Exception as e:
        print(f"Nota: No se usaron secrets ({e})")
    
    # INTENTO 2: String directo (Pega tu link de NEON aquí si fallan los secrets)
    # db_url = "postgresql://usuario:pass@host/db..." 
    # return create_engine(db_url)

    return None # Si retorna None, la app funcionará en modo "Solo Diseño"

conn = get_db_connection()

# ==============================================================================
# 3. ESTILOS CSS (AJUSTADO: MENOS OSCURO)
# ==============================================================================
st.markdown(f"""
    <style>
        /* A. FONDO GENERAL (Aclarado al 85% para que veas el fondo) */
        .stApp {{
            background: linear-gradient(rgba(14, 17, 23, 0.85), rgba(14, 17, 23, 0.90)), 
                        url("{URL_FONDO_BASE}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
            color: white;
        }}
        
        /* B. INPUTS Y SELECTORES */
        div[data-testid="stTextInput"] input, div[data-testid="stSelectbox"] > div > div {{
            background-color: #262730 !important;
            border: 1px solid #444 !important;
            color: white !important;
            height: 48px !important;
            border-radius: 8px !important;
        }}
        
        /* C. BOTONES */
        button[kind="secondary"], div[data-testid="stLinkButton"] a {{
            background-color: #262730 !important;
            border: 1px solid #555 !important;
            color: white !important;
        }}
        button[kind="secondary"]:hover, div[data-testid="stLinkButton"] a:hover {{
            border-color: {COLOR_MARCA} !important;
            color: {COLOR_MARCA} !important;
        }}
        button[kind="primary"] {{
            background-color: {COLOR_MARCA} !important;
            color: black !important;
            font-weight: 800 !important;
            border: none !important;
        }}
        
        /* D. TARJETAS */
        .lobby-card {{
            background-color: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 15px 20px;
            margin-bottom: 15px;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        
        /* E. ANIMACIONES DEL BOT */
        @keyframes slideInUp {{ from {{ transform: translateY(20px); opacity: 0; }} to {{ transform: translateY(0); opacity: 1; }} }}
        .bot-bar {{
            animation: slideInUp 0.5s ease-out;
            background-color: rgba(30, 30, 40, 0.95);
            border-left: 4px solid {COLOR_MARCA};
            border-radius: 8px;
            padding: 8px 15px;
            margin-bottom: 15px;
            display: flex; align-items: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
        }}
        .bot-icon {{ animation: float 3s ease-in-out infinite; font-size: 22px; }}
        @keyframes float {{ 0% {{ transform: translateY(0px); }} 50% {{ transform: translateY(-3px); }} 100% {{ transform: translateY(0px); }} }}
        
        /* REACCIONES */
        div[data-testid="column"] button.reaccion-btn {{ background: transparent !important; border: none !important; }}
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 4. COMPONENTE: BOT GANA (MINI)
# ==============================================================================
def mostrar_bot_mini(mensaje, key_unica):
    session_key = f"bot_closed_{key_unica}"
    if session_key not in st.session_state: st.session_state[session_key] = False
    if st.session_state[session_key]: return

    c_bot = st.container()
    with c_bot:
        cols = st.columns([0.1, 0.75, 0.075, 0.075], vertical_alignment="center")
        with cols[0]: st.markdown('<div class="bot-icon">🤖</div>', unsafe_allow_html=True)
        with cols[1]: st.markdown(f"<span style='color:#ddd; font-size:14px; font-style:italic;'>{mensaje}</span>", unsafe_allow_html=True)
        with cols[2]: 
            if st.button("👍", key=f"lk_{key_unica}", help="Útil"):
                st.session_state[session_key] = True; st.toast("¡Anotado!"); time.sleep(0.2); st.rerun()
        with cols[3]: 
            if st.button("✖️", key=f"cl_{key_unica}", help="Cerrar"):
                st.session_state[session_key] = True; st.rerun()
        st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)

# ==============================================================================
# 5. LÓGICA DEL LOBBY
# ==============================================================================
def render_lobby():
    # --- HEADER ---
    try:
        st.image(URL_PORTADA, use_container_width=True)
    except:
        st.header("🏆 GOL GANA") # Fallback si la imagen falla

    # --- DIAGNÓSTICO DE BASE DE DATOS ---
    if conn is None:
        st.warning("⚠️ **Modo Diseño (Sin Base de Datos):** No se detectaron credenciales en secrets.toml. La interfaz se muestra pero no guardará datos.")

    # BOT INTRO
    mostrar_bot_mini("¡Hola! Soy Bot Gana. Abajo encuentras los torneos activos.", "bot_lobby_intro")

    st.markdown("---")
    st.subheader("🔥 Torneos en Curso")

    # --- LISTAR TORNEOS ---
    try:
        if conn:
            query = text("SELECT id, nombre, organizador, color_primario, fase, formato FROM torneos WHERE fase != 'Terminado' ORDER BY fecha_creacion DESC")
            df_torneos = pd.read_sql_query(query, conn)
        else:
            df_torneos = pd.DataFrame()
    except Exception as e:
        # st.error(f"Error SQL: {e}") # Descomentar para ver error real
        df_torneos = pd.DataFrame()

    if not df_torneos.empty:
        for _, t in df_torneos.iterrows():
            with st.container():
                st.markdown(f"""
                <div class="lobby-card" style="border-left: 5px solid {t['color_primario']};">
                    <h3 style="margin:0; color:white;">{t['nombre']}</h3>
                    <p style="margin:0; font-size:13px; opacity:0.7; color:#ccc;">👮 {t['organizador']} | 🎮 {t['formato']}</p>
                    <span style="color:{t['color_primario']}; font-size:11px; border:1px solid {t['color_primario']}; padding:2px 5px; border-radius:4px;">{t['fase']}</span>
                </div>""", unsafe_allow_html=True)
                if st.button(f"⚽ Ver Torneo", key=f"btn_{t['id']}", use_container_width=True):
                    st.query_params["id"] = str(t['id']); st.rerun()
    else:
        st.info("No hay torneos activos (o no hay conexión a BD).")

    st.markdown("<br>", unsafe_allow_html=True)

    # --- CREAR TORNEO ---
    with st.expander("✨ ¿Eres Organizador? Crea tu Torneo", expanded=False):
        mostrar_bot_mini("Elige un color único para tu marca.", "bot_crear_color")
        with st.form("form_crear"):
            new_nombre = st.text_input("Nombre del Torneo")
            c1, c2 = st.columns(2)
            new_formato = c1.selectbox("Formato", ["Grupos", "Liga"])
            new_color = c2.color_picker("Color", "#00FF00")
            c3, c4 = st.columns(2)
            new_org = c3.text_input("Organizador")
            new_pin = c4.text_input("PIN (4 dígitos)", type="password", max_chars=4)
            
            if st.form_submit_button("🚀 Crear", use_container_width=True, type="primary"):
                if conn and new_nombre and new_pin:
                    try:
                        with conn.connect() as db:
                            res = db.execute(text("INSERT INTO torneos (nombre, organizador, whatsapp_admin, pin_admin, color_primario, fase, formato) VALUES (:n, :o, '', :p, :c, 'inscripcion', :f) RETURNING id"), 
                                            {"n": new_nombre, "o": new_org, "p": new_pin, "c": new_color, "f": new_formato})
                            nid = res.fetchone()[0]; db.commit()
                        st.balloons(); time.sleep(1); st.query_params["id"] = str(nid); st.rerun()
                    except Exception as e: st.error(f"Error: {e}")
                else:
                    st.warning("Faltan datos o conexión.")

# ==============================================================================
# 6. ENRUTADOR
# ==============================================================================
params = st.query_params
if "id" in params:
    st.title(f"🚧 Torneo ID: {params['id']}")
    if st.button("Volver"): st.query_params.clear(); st.rerun()
else:
    render_lobby()

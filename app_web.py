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

# --- CONEXIÓN A BASE DE DATOS (SEGURA CON SECRETS) ---
@st.cache_resource
def get_db_connection():
    try:
        if "connections" not in st.secrets or "postgresql" not in st.secrets["connections"]:
            return None # Modo diseño si no hay conexión
        db_url = st.secrets["connections"]["postgresql"]["url"]
        return create_engine(db_url, pool_pre_ping=True)
    except Exception as e:
        return None

conn = get_db_connection()

# ==============================================================================
# 2. ESTILOS CSS (TIPOGRAFÍA + BLINDAJE + TABS)
# ==============================================================================
st.markdown(f"""
    <style>
        /* IMPORTAR FUENTE DEPORTIVA/TECNOLÓGICA */
       # @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;600;700&display=swap');

        /* 1. FONDO GENERAL Y TIPOGRAFÍA */
        .stApp {{
            background: linear-gradient(rgba(14, 17, 23, 0.92), rgba(14, 17, 23, 0.96)), 
                        url("{URL_FONDO_BASE}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
            color: white;
            font-family: ''Oswald'', sans-serif !important;
        }}
        
        /* Forzar fuente en todos los elementos */
        h1, h2, h3, h4, h5, h6, p, div, button, input, label {{
            font-family: 'Rajdhani', sans-serif !important;
        }}

        /* 2. INPUTS Y BOTONES */
        div[data-testid="stTextInput"] input, div[data-testid="stSelectbox"] > div > div {{
            background-color: #262730 !important;
            border: 1px solid #444 !important;
            color: white !important;
            height: 50px !important;
            font-size: 18px !important; /* Letra más grande en inputs */
            border-radius: 8px !important;
        }}
        button[kind="secondary"], div[data-testid="stLinkButton"] a {{
            background-color: #262730 !important;
            border: 1px solid #555 !important;
            color: white !important;
            font-weight: 600 !important;
            border-radius: 8px !important;
        }}
        button[kind="secondary"]:hover {{
            border-color: {COLOR_MARCA} !important;
            color: {COLOR_MARCA} !important;
        }}
        button[kind="primary"] {{
            background-color: {COLOR_MARCA} !important;
            color: black !important;
            font-weight: 800 !important;
            border: none !important;
            height: 50px !important;
            font-size: 18px !important;
            border-radius: 8px !important;
        }}

        /* 3. ESTILO DE LAS PESTAÑAS (TABS) - EXPERIENCIA GOL GANA */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 10px;
        }}
        .stTabs [data-baseweb="tab"] {{
            background-color: rgba(255,255,255,0.05);
            border-radius: 8px 8px 0 0;
            color: #aaa;
            font-weight: 600;
        }}
        .stTabs [aria-selected="true"] {{
            background-color: rgba(255, 215, 0, 0.1) !important;
            color: {COLOR_MARCA} !important;
            border-top: 2px solid {COLOR_MARCA} !important;
        }}

        /* 4. TARJETAS DE LOBBY */
        .lobby-card {{
            background-color: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            border: 1px solid rgba(255,255,255,0.1);
            transition: transform 0.2s;
        }}
        .lobby-card:hover {{
            transform: scale(1.02);
            border-color: {COLOR_MARCA};
            background-color: rgba(255, 255, 255, 0.08);
        }}
        
        /* 5. BURBUJA DEL BOT (Simple y Limpia) */
        .bot-bubble {{
            background-color: rgba(30, 30, 40, 0.9);
            border-left: 4px solid {COLOR_MARCA};
            border-radius: 8px;
            padding: 12px 20px;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 15px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.3);
            animation: fadeIn 1s ease-in;
        }}
        .bot-text {{
            color: #ddd;
            font-size: 16px;
            font-weight: 500;
            line-height: 1.4;
        }}
        .bot-avatar {{
            font-size: 28px;
        }}
        @keyframes fadeIn {{ from {{ opacity:0; transform:translateY(10px); }} to {{ opacity:1; transform:translateY(0); }} }}
    </style>
""", unsafe_allow_html=True)

def mostrar_bot(mensaje):
    """Componente visual del asistente (Solo lectura)"""
    st.markdown(f"""
        <div class="bot-bubble">
            <div class="bot-avatar">🤖</div>
            <div class="bot-text">{mensaje}</div>
        </div>
    """, unsafe_allow_html=True)

# ==============================================================================
# 3. LÓGICA DEL LOBBY
# ==============================================================================

def render_lobby():
    # --- A. PORTADA ---
    st.image(URL_PORTADA, use_container_width=True)
    
    # SALUDO DEL BOT
    mostrar_bot("¡Hola! Soy <b>Bot Gana</b>. Organizo tus torneos y estadísticas. <br>Explora las ligas activas abajo o crea tu propia competencia.")

    # --- NUEVA SECCIÓN: EXPERIENCIA GOL GANA ---
    st.markdown(f"<h3 style='text-align:center; color:{COLOR_MARCA}; margin-top:10px;'>EXPERIENCIA GOL GANA</h3>", unsafe_allow_html=True)
    
    # Pestañas de información
    tab_eq, tab_dt, tab_adm = st.tabs(["🛡️ Equipos", "🧠 DTs / Capitanes", "👮 Administradores"])
    
    with tab_eq:
        st.info("📊 **Ranking Global Unificado:** No importa en qué torneo juegues, si es Gol Gana, tus goles y victorias suman a tu historial único.")
    
    with tab_dt:
        st.info("📲 **Gestión sin Papel:** Olvídate de las planillas físicas. Inscribe tu nómina una vez y úsala en múltiples torneos con tu PIN.")
        
    with tab_adm:
        st.info("🎨 **Tu Marca, Tu Torneo:** Personaliza los colores de la web, automatiza la tabla de posiciones y deja que el Bot ayude a tus usuarios.")

    st.markdown("---")

    # --- B. TORNEOS VIGENTES ---
    st.subheader("🔥 Torneos en Curso")

    try:
        if conn:
            query = text("""
                SELECT id, nombre, organizador, color_primario, fase, formato, fecha_creacion 
                FROM torneos 
                WHERE fase != 'Terminado' 
                ORDER BY fecha_creacion DESC
            """)
            df_torneos = pd.read_sql_query(query, conn)
        else:
            df_torneos = pd.DataFrame()
    except:
        st.error("Conectando al servidor...")
        df_torneos = pd.DataFrame()

    if not df_torneos.empty:
        for _, t in df_torneos.iterrows():
            with st.container():
                # Tarjeta visual
                st.markdown(f"""
                <div class="lobby-card" style="border-left: 6px solid {t['color_primario']};">
                    <h3 style="margin:0; font-weight:700; color:white; font-size:22px;">{t['nombre']}</h3>
                    <p style="margin:5px 0 0 0; font-size:15px; opacity:0.8; color:#ccc;">
                        👮 {t['organizador']} | 🎮 {t['formato']}
                    </p>
                    <div style="margin-top:8px;">
                        <span style="border:1px solid {t['color_primario']}; color:{t['color_primario']}; padding:2px 8px; border-radius:4px; font-size:12px; font-weight:bold;">
                            {t['fase'].upper()}
                        </span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Botón de acción
                if st.button(f"⚽ Ver Torneo", key=f"btn_lobby_{t['id']}", use_container_width=True):
                    st.query_params["id"] = str(t['id'])
                    st.rerun()
    else:
        st.info("No hay torneos activos. ¡Sé el primero en crear uno!")

    st.markdown("<br>", unsafe_allow_html=True)

    # --- C. CREAR NUEVO TORNEO ---
    with st.expander("✨ ¿Eres Organizador? Crea tu Torneo", expanded=False):
        
        mostrar_bot("Configura tu torneo aquí. <br>Recuerda: <b>El PIN es sagrado</b>, será tu única llave para editar resultados.")
        
        with st.form("form_crear_torneo"):
            st.markdown("##### 1. Identidad")
            new_nombre = st.text_input("Nombre de la Competencia", placeholder="Ej: Relámpago Jueves")
            
            c_f1, c_f2 = st.columns(2)
            new_formato = c_f1.selectbox("Formato", ["Grupos + Eliminatoria", "Todos contra Todos", "Eliminación Directa"])
            
            with c_f2:
                new_color = st.color_picker("Color de Marca", "#00FF00")
            
            st.caption("🤖 Bot: El color que elijas pintará la web para tus jugadores.")

            st.markdown("##### 2. Admin")
            c_adm1, c_adm2 = st.columns(2)
            new_org = c_adm1.text_input("Tu Nombre / Cancha")
            new_wa = c_adm2.text_input("WhatsApp (Sin +)")
            
            st.markdown("##### 3. Seguridad")
            new_pin = st.text_input("Crea un PIN (4 dígitos)", type="password", max_chars=4)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.form_submit_button("🚀 Lanzar Torneo", use_container_width=True, type="primary"):
                if new_nombre and new_pin and new_org and conn:
                    try:
                        with conn.connect() as db:
                            result = db.execute(text("""
                                INSERT INTO torneos (nombre, organizador, whatsapp_admin, pin_admin, color_primario, fase, formato)
                                VALUES (:n, :o, :w, :p, :c, 'inscripcion', :f) RETURNING id
                            """), {
                                "n": new_nombre, "o": new_org, "w": new_wa, 
                                "p": new_pin, "c": new_color, "f": new_formato
                            })
                            nuevo_id = result.fetchone()[0]
                            db.commit()
                        
                        st.balloons()
                        time.sleep(1)
                        st.query_params["id"] = str(nuevo_id)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error creando el torneo: {e}")
                else:
                    st.warning("⚠️ Faltan datos obligatorios.")

# ==============================================================================
# 4. ENRUTADOR PRINCIPAL
# ==============================================================================

params = st.query_params

if "id" in params:
    # AQUÍ IRÁ LA LÓGICA DE 'RENDER_TORNEO' (Próximo paso)
    st.title("🚧 Cargando Torneo...")
    st.write(f"ID del Torneo: {params['id']}")
    if st.button("Volver al Lobby"):
        st.query_params.clear()
        st.rerun()
else:
    render_lobby()


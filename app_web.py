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
            st.error("⚠️ No se encontraron las credenciales en st.secrets")
            return None
        db_url = st.secrets["connections"]["postgresql"]["url"]
        return create_engine(db_url, pool_pre_ping=True)
    except Exception as e:
        st.error(f"⚠️ Error conectando a BD: {e}")
        return None

conn = get_db_connection()

# ==============================================================================
# 2. ESTILOS CSS & COMPONENTE BOT
# ==============================================================================
st.markdown(f"""
    <style>
        /* 1. FONDO GENERAL */
        .stApp {{
            background: linear-gradient(rgba(14, 17, 23, 0.92), rgba(14, 17, 23, 0.96)), 
                        url("{URL_FONDO_BASE}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
            color: white;
        }}
        
        /* 2. INPUTS Y BOTONES (Blindaje Visual) */
        div[data-testid="stTextInput"] input, div[data-testid="stSelectbox"] > div > div {{
            background-color: #262730 !important;
            border: 1px solid #444 !important;
            color: white !important;
            height: 50px !important;
            font-size: 16px !important;
            border-radius: 8px !important;
        }}
        button[kind="secondary"], div[data-testid="stLinkButton"] a {{
            background-color: #262730 !important;
            border: 1px solid #555 !important;
            color: white !important;
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
        }}

        /* 3. TARJETAS DE LOBBY */
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
        }}
        
        /* 4. BURBUJA DEL BOT (Personalización) */
        .bot-bubble {{
            background-color: rgba(255, 215, 0, 0.1);
            border-left: 3px solid {COLOR_MARCA};
            border-radius: 0 10px 10px 0;
            padding: 10px 15px;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 15px;
        }}
        .bot-text {{
            color: #eee;
            font-size: 14px;
            font-style: italic;
        }}
        .bot-avatar {{
            font-size: 24px;
            animation: float 3s ease-in-out infinite;
        }}
        @keyframes float {{
            0% {{ transform: translateY(0px); }}
            50% {{ transform: translateY(-5px); }}
            100% {{ transform: translateY(0px); }}
        }}
    </style>
""", unsafe_allow_html=True)

def mostrar_bot(mensaje):
    """Componente reutilizable para el asistente virtual"""
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
    
    # SALUDO DEL BOT (Primera interacción)
    mostrar_bot("¡Hola! Soy <b>Bot Gana</b>. Estoy aquí para organizar tus torneos y estadísticas. <br>Abajo encontrarás las ligas activas o puedes crear la tuya.")

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
    except Exception as e:
        st.error("Error de conexión.")
        df_torneos = pd.DataFrame()

    if not df_torneos.empty:
        for _, t in df_torneos.iterrows():
            with st.container():
                # Tarjeta visual
                st.markdown(f"""
                <div class="lobby-card" style="border-left: 6px solid {t['color_primario']};">
                    <h2 style="margin:0; font-weight:800; font-size: 22px; color:white;">{t['nombre']}</h2>
                    <p style="margin:5px 0 0 0; font-size:14px; opacity:0.7; color:#ccc;">
                        👮 Organiza: {t['organizador']} | 🎮 {t['formato']}
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                # Botón de acción
                if st.button(f"⚽ Entrar al Torneo", key=f"btn_lobby_{t['id']}", use_container_width=True):
                    st.query_params["id"] = str(t['id'])
                    st.rerun()
    else:
        st.info("No hay torneos activos. ¡Sé el primero en crear uno!")

    st.markdown("<br>", unsafe_allow_html=True)

    # --- C. CREAR NUEVO TORNEO (Con guía del Bot) ---
    with st.expander("✨ ¡Soy Organizador! Crear mi Torneo", expanded=False):
        
        # EL BOT GUÍA AL ADMIN
        mostrar_bot("¡Excelente decisión! Configura tu torneo aquí. <br>Recuerda: <b>El PIN es sagrado</b>, será tu única llave para editar resultados.")
        
        with st.form("form_crear_torneo"):
            st.markdown("##### 1. Identidad del Torneo")
            new_nombre = st.text_input("Nombre de la Competencia", placeholder="Ej: Relámpago Gol Gana Jueves")
            
            c_f1, c_f2 = st.columns(2)
            new_formato = c_f1.selectbox("Formato", ["Grupos + Eliminatoria", "Todos contra Todos", "Eliminación Directa"])
            
            with c_f2:
                # AQUÍ REEMPLAZAMOS EL HELP TEXT POR UNA INTERVENCIÓN DEL BOT
                # El bot explica para qué sirve el color antes de elegirlo
                new_color = st.color_picker("Color de Marca", "#00FF00")
            
            # Mensaje contextual del Bot sobre el color
            mostrar_bot(f"El color que elijas arriba pintará toda la web para tus jugadores. ¡Haz que se vea único!")

            st.markdown("---")
            st.markdown("##### 2. Tus Datos (Admin)")
            c_adm1, c_adm2 = st.columns(2)
            new_org = c_adm1.text_input("Tu Nombre / Cancha")
            new_wa = c_adm2.text_input("WhatsApp (Sin +)")
            
            st.markdown("##### 3. Llave de Acceso")
            new_pin = st.text_input("Crea un PIN de 4 dígitos", type="password", max_chars=4)
            
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
                    st.warning("⚠️ Faltan datos obligatorios o no hay conexión.")

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

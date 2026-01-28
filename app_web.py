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
# 2. ESTILOS CSS (FUENTE OSWALD + BLINDAJE)
# ==============================================================================
st.markdown(f"""
    <style>
        /* IMPORTAR FUENTE OSWALD (Estilo Deportivo) */
        @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@300;400;600&display=swap');

        /* 1. FONDO GENERAL Y TIPOGRAFÍA */
        .stApp {{
            background: linear-gradient(rgba(14, 17, 23, 0.92), rgba(14, 17, 23, 0.96)), 
                        url("{URL_FONDO_BASE}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
            color: white;
            font-family: 'Oswald', sans-serif !important;
        }}
        
        /* Forzar fuente en todos los elementos */
        h1, h2, h3, h4, h5, h6, p, div, button, input, label, span, textarea {{
            font-family: 'Oswald', sans-serif !important;
        }}

        /* 2. INPUTS Y BOTONES */
        div[data-testid="stTextInput"] input, div[data-testid="stSelectbox"] > div > div {{
            background-color: #262730 !important;
            border: 1px solid #444 !important;
            color: white !important;
            height: 50px !important;
            font-size: 18px !important;
            letter-spacing: 0.5px;
            border-radius: 8px !important;
        }}
        button[kind="secondary"], div[data-testid="stLinkButton"] a {{
            background-color: #262730 !important;
            border: 1px solid #555 !important;
            color: white !important;
            font-weight: 400 !important;
            letter-spacing: 1px;
            border-radius: 8px !important;
        }}
        button[kind="secondary"]:hover {{
            border-color: {COLOR_MARCA} !important;
            color: {COLOR_MARCA} !important;
        }}
        button[kind="primary"] {{
            background-color: {COLOR_MARCA} !important;
            color: black !important;
            font-weight: 600 !important;
            border: none !important;
            height: 50px !important;
            font-size: 18px !important;
            border-radius: 8px !important;
            letter-spacing: 1px;
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
            background-color: rgba(255, 255, 255, 0.08);
        }}
        
        /* 4. BURBUJA DEL BOT */
        .bot-bubble {{
            background-color: rgba(30, 30, 40, 0.9);
            border-left: 4px solid {COLOR_MARCA};
            border-radius: 8px;
            padding: 15px 20px;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 15px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.3);
            animation: fadeIn 1s ease-in;
        }}
        .bot-text {{
            color: #ddd;
            font-size: 17px; 
            font-weight: 300;
            line-height: 1.4;
        }}
        .bot-avatar {{
            font-size: 28px;
        }}
        @keyframes fadeIn {{ from {{ opacity:0; transform:translateY(10px); }} to {{ opacity:1; transform:translateY(0); }} }}

        /* 5. ESTILO MANIFIESTO (INTRO) */
        .intro-quote {{
            font-size: 22px;
            font-style: italic;
            color: {COLOR_MARCA};
            text-align: center;
            margin-bottom: 20px;
            font-weight: 300;
        }}
        .intro-text {{
            font-size: 16px;
            text-align: justify;
            color: #e0e0e0;
            line-height: 1.6;
            margin-bottom: 10px;
            font-weight: 300;
        }}
        .intro-highlight {{
            color: white;
            font-weight: 600;
        }}
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
    
    # --- B. MANIFIESTO / INTRODUCCIÓN ---
    st.markdown(f"""
        <div class="intro-quote">
            “Mientras otros solo anotan goles, tú construyes una historia”
        </div>
        <div class="intro-text">
            El mundo ha cambiado. La tecnología y la Inteligencia Artificial han redefinido cada industria, y hoy, 
            ese poder llega finalmente a la comunidad de Clubes Pro. Ya no se trata solo de jugar un partido; 
            se trata del legado que dejas en cada cancha virtual.
        </div>
        <div class="intro-text">
            En la élite, los equipos más grandes no solo se miden por sus títulos, sino por los datos e indicadores 
            que respaldan cada trofeo. Por eso, en <b>Gol-Gana</b>, cada victoria, cada rivalidad y cada estadística 
            forman parte de una historia viva y objetiva. La evolución no se detiene, es momento de dar paso a un 
            ecosistema inteligente donde la historia de cada club puede ser eterna.
        </div>
        <div style="text-align:center; margin-top:15px; font-size:18px; font-weight:600; color:{COLOR_MARCA};">
            ¿Estás listo para transformar tu comunidad? Únete a los clubes que ya compiten en el futuro.
        </div>
        <br>
    """, unsafe_allow_html=True)

    # --- C. SALUDO DEL BOT ---
    mostrar_bot("Hola, Soy <b>Gol Bot</b>. Guardaré las estadísticas de equipo y apoyaré al admin en la organización de cada torneo.")

    st.markdown("---")

    # --- D. TORNEOS VIGENTES ---
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
                    <h3 style="margin:0; font-weight:600; color:white; font-size:24px; letter-spacing:1px;">{t['nombre']}</h3>
                    <p style="margin:5px 0 0 0; font-size:16px; opacity:0.8; color:#ccc; font-weight:300;">
                        👮 {t['organizador']} | 🎮 {t['formato']}
                    </p>
                    <div style="margin-top:8px;">
                        <span style="border:1px solid {t['color_primario']}; color:{t['color_primario']}; padding:2px 8px; border-radius:4px; font-size:13px; font-weight:400;">
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

    # --- E. CREAR NUEVO TORNEO ---
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

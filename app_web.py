import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import time

# ==============================================================================
# 1. CONFIGURACIÓN INICIAL Y ASSETS
# ==============================================================================
st.set_page_config(page_title="Gol Gana", layout="centered", page_icon="⚽")

# URLS E IDENTIDAD
URL_FONDO_BASE = "https://res.cloudinary.com/dlvczeqlp/image/upload/v1769030979/fondo_base_l7i0k6.png"
URL_PORTADA = "https://res.cloudinary.com/dlvczeqlp/image/upload/v1769050565/a906a330-8b8c-4b52-b131-8c75322bfc10_hwxmqb.png"
COLOR_MARCA = "#FFD700"  # Dorado Gol Gana

# ==============================================================================
# 2. GESTIÓN DE CONEXIÓN A BASE DE DATOS (NEON)
# ==============================================================================
@st.cache_resource
def get_db_connection():
    try:
        # Busca en secrets.toml o usa una variable de entorno si prefieres
        if "connections" not in st.secrets or "postgresql" not in st.secrets["connections"]:
            st.error("⚠️ Error: No se encontraron las credenciales en .streamlit/secrets.toml")
            return None
            
        db_url = st.secrets["connections"]["postgresql"]["url"]
        # pool_pre_ping ayuda a reconectar si la conexión se cae
        return create_engine(db_url, pool_pre_ping=True)
    except Exception as e:
        st.error(f"⚠️ Error conectando a BD: {e}")
        return None

conn = get_db_connection()

# ==============================================================================
# 3. ESTILOS CSS (BLINDAJE VISUAL + BOT)
# ==============================================================================
st.markdown(f"""
    <style>
        /* A. FONDO GENERAL */
        .stApp {{
            background: linear-gradient(rgba(14, 17, 23, 0.92), rgba(14, 17, 23, 0.96)), 
                        url("{URL_FONDO_BASE}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
            color: white;
        }}
        
        /* B. INPUTS Y SELECTORES (Estilo Oscuro y Grande) */
        div[data-testid="stTextInput"] input, div[data-testid="stSelectbox"] > div > div {{
            background-color: #262730 !important;
            border: 1px solid #444 !important;
            color: white !important;
            height: 50px !important;
            font-size: 16px !important;
            border-radius: 8px !important;
        }}
        
        /* C. BOTONES */
        button[kind="secondary"], div[data-testid="stLinkButton"] a {{
            background-color: #262730 !important;
            border: 1px solid #555 !important;
            color: white !important;
            height: 45px !important;
            border-radius: 8px !important;
            transition: all 0.3s ease;
        }}
        /* Hover Dorado */
        button[kind="secondary"]:hover, div[data-testid="stLinkButton"] a:hover {{
            border-color: {COLOR_MARCA} !important;
            color: {COLOR_MARCA} !important;
            transform: translateY(-2px);
        }}
        /* Botón Primario (Acción) */
        button[kind="primary"] {{
            background-color: {COLOR_MARCA} !important;
            color: black !important;
            font-weight: 800 !important;
            border: none !important;
            height: 50px !important;
            border-radius: 8px !important;
            font-size: 16px !important;
        }}
        
        /* D. TARJETAS DEL LOBBY */
        .lobby-card {{
            background-color: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            border: 1px solid rgba(255,255,255,0.1);
            transition: transform 0.2s;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }}
        .lobby-card:hover {{
            transform: scale(1.02);
            border-color: {COLOR_MARCA};
        }}
        
        /* E. ANIMACIÓN Y ESTILO DEL BOT GANA */
        @keyframes slideInRight {{
            from {{ transform: translateX(100%); opacity: 0; }}
            to {{ transform: translateX(0); opacity: 1; }}
        }}
        
        .bot-container {{
            animation: slideInRight 0.6s ease-out;
            background-color: rgba(30, 30, 40, 0.95);
            border-left: 5px solid {COLOR_MARCA};
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.5);
            display: flex;
            flex-direction: column;
        }}
        .bot-header {{
            display: flex; 
            align-items: center; 
            gap: 10px; 
            margin-bottom: 8px;
        }}
        .bot-message {{
            font-style: italic; 
            color: #eee; 
            font-size: 15px;
            line-height: 1.4;
        }}
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 4. COMPONENTE: BOT GANA INTERACTIVO
# ==============================================================================
def mostrar_bot_interactivo(mensaje, key_unica):
    """
    Muestra al Bot Gana con animación y botones de cerrar.
    key_unica: Identificador para que la sesión recuerde si ya se cerró este mensaje específico.
    """
    # Nombre de la variable en session state
    session_key = f"bot_closed_{key_unica}"

    # Inicializar si no existe
    if session_key not in st.session_state:
        st.session_state[session_key] = False

    # Si el usuario ya lo cerró, no mostramos nada
    if st.session_state[session_key]:
        return

    # Contenedor del Bot
    contenedor = st.container()
    with contenedor:
        # 1. HTML Visual del Bot
        st.markdown(f"""
            <div class="bot-container">
                <div class="bot-header">
                    <span style="font-size:24px;">🤖</span>
                    <span style="font-weight:bold; color:{COLOR_MARCA};">Bot Gana:</span>
                </div>
                <div class="bot-message">
                    "{mensaje}"
                </div>
            </div>
        """, unsafe_allow_html=True)

        # 2. Botones de Interacción (Invisibles visualmente, pero funcionales)
        # Usamos columnas para ponerlos "debajo" o "dentro" logicamente
        c1, c2, c3 = st.columns([1, 1, 5])
        
        with c1:
            if st.button("👍 Entendido", key=f"like_{key_unica}", help="Cerrar mensaje"):
                st.session_state[session_key] = True
                st.toast("¡Anotado! 😎")
                time.sleep(0.5)
                st.rerun()
        
        with c2:
            if st.button("👎 Ocultar", key=f"dislike_{key_unica}", help="No mostrar más"):
                st.session_state[session_key] = True
                st.rerun()

# ==============================================================================
# 5. VISTA: LOBBY PRINCIPAL
# ==============================================================================
def render_lobby():
    # --- HEADER ---
    st.image(URL_PORTADA, use_container_width=True)
    
    st.markdown("""
        <div style="text-align: center; margin-bottom: 30px;">
            <p style="font-size: 18px; opacity: 0.8; margin-top: -10px;">
                La plataforma definitiva para gestionar tus torneos.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # --- BOT: SALUDO INICIAL ---
    mostrar_bot_interactivo(
        "¡Hola crack! 👋 Soy tu asistente inteligente. <br>Aquí abajo puedes ver los torneos activos o crear el tuyo propio si eres organizador.", 
        "bienvenida_lobby_v1"
    )

    st.markdown("---")

    # --- SECCIÓN: TORNEOS VIGENTES ---
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
        st.error(f"Error de conexión: {e}")
        df_torneos = pd.DataFrame()

    if not df_torneos.empty:
        for _, t in df_torneos.iterrows():
            with st.container():
                # Tarjeta HTML
                st.markdown(f"""
                <div class="lobby-card" style="border-left: 6px solid {t['color_primario']};">
                    <h2 style="margin:0; font-weight:800; font-size: 22px; color:white;">{t['nombre']}</h2>
                    <p style="margin:5px 0 0 0; font-size:14px; opacity:0.7; color:#ccc;">
                        👮 Organiza: <strong>{t['organizador']}</strong> | 🎮 {t['formato']}
                    </p>
                    <div style="margin-top:10px;">
                        <span style="background-color:{t['color_primario']}40; color:{t['color_primario']}; padding:3px 8px; border-radius:4px; font-size:12px; border:1px solid {t['color_primario']};">
                            {t['fase'].upper()}
                        </span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Botón de Acción
                if st.button(f"⚽ Entrar al Torneo", key=f"btn_enter_{t['id']}", use_container_width=True):
                    st.query_params["id"] = str(t['id'])
                    st.rerun()
    else:
        st.info("No hay torneos activos por el momento.")

    st.markdown("<br><br>", unsafe_allow_html=True)

    # --- SECCIÓN: CREAR TORNEO ---
    with st.expander("✨ ¡Soy Organizador! Crear mi Torneo", expanded=False):
        
        # BOT: CONSEJO DE CREACIÓN
        mostrar_bot_interactivo(
            "Un consejo de amigo: El <b>PIN de Admin</b> es tu llave maestra. No lo pierdas, porque sin él no podrás editar resultados ni aceptar equipos.", 
            "consejo_pin_admin"
        )
        
        with st.form("form_crear_torneo"):
            st.markdown("##### 1. Datos del Evento")
            new_nombre = st.text_input("Nombre del Torneo", placeholder="Ej: Relámpago Jueves")
            
            c1, c2 = st.columns(2)
            new_formato = c1.selectbox("Formato", ["Grupos + Eliminatoria", "Todos contra Todos", "Eliminación Directa"])
            new_color = c2.color_picker("Color de tu Marca", "#00FF00")
            
            st.markdown("##### 2. Tus Datos")
            c3, c4 = st.columns(2)
            new_org = c3.text_input("Tu Nombre / Cancha")
            new_wa = c4.text_input("WhatsApp Admin")
            
            st.markdown("##### 3. Seguridad")
            new_pin = st.text_input("Crea un PIN (4 dígitos)", type="password", max_chars=4)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.form_submit_button("🚀 Lanzar Torneo", use_container_width=True, type="primary"):
                if new_nombre and new_pin and new_org and conn:
                    try:
                        with conn.connect() as db:
                            # Insertar y retornar ID
                            res = db.execute(text("""
                                INSERT INTO torneos (nombre, organizador, whatsapp_admin, pin_admin, color_primario, fase, formato)
                                VALUES (:n, :o, :w, :p, :c, 'inscripcion', :f) RETURNING id
                            """), {
                                "n": new_nombre, "o": new_org, "w": new_wa, 
                                "p": new_pin, "c": new_color, "f": new_formato
                            })
                            nuevo_id = res.fetchone()[0]
                            db.commit()
                        
                        st.balloons()
                        time.sleep(1)
                        st.query_params["id"] = str(nuevo_id)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error creando torneo: {e}")
                else:
                    st.warning("⚠️ Faltan datos obligatorios.")


# ==============================================================================
# 6. VISTA: TORNEO ESPECÍFICO (Placeholder para futura integración)
# ==============================================================================
def render_torneo(torneo_id):
    # Aquí iría toda tu lógica anterior (Login, Tabs, Admin, Resultados)
    # Por ahora solo mostramos que la redirección funciona
    st.success(f"✅ Cargando módulo del Torneo ID: {torneo_id}")
    st.info("Aquí cargaremos el Login y las Pestañas de la versión anterior.")
    
    if st.button("⬅️ Volver al Lobby"):
        st.query_params.clear()
        st.rerun()

# ==============================================================================
# 7. ENRUTADOR PRINCIPAL (MAIN LOOP)
# ==============================================================================

params = st.query_params

if "id" in params:
    # Si la URL tiene ?id=X, cargamos el torneo X
    render_torneo(params["id"])
else:
    # Si no, cargamos el Lobby
    render_lobby()

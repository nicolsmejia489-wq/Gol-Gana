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

# --- CONEXIÓN A BASE DE DATOS (NEON) ---
# Reemplaza esto con tu string real de Neon Console
# "postgresql://usuario:password@host/nombre_db?sslmode=require"
try:
    # Intenta buscar en st.secrets si existe, si no, usa un string directo (cuidado al compartir)
    DATABASE_URL = st.secrets["connections"]["postgresql"]["dialect"] + "://" + \
                   st.secrets["connections"]["postgresql"]["username"] + ":" + \
                   st.secrets["connections"]["postgresql"]["password"] + "@" + \
                   st.secrets["connections"]["postgresql"]["host"] + "/" + \
                   st.secrets["connections"]["postgresql"]["database"]
except:
    # Pega tu Link de Neon aquí si no usas secrets.toml
    DATABASE_URL = "TU_LINK_DE_NEON_AQUI" 

try:
    engine = create_engine(DATABASE_URL)
    conn = engine.connect()
except Exception as e:
    st.error(f"⚠️ Error de conexión a la base de datos: {e}")
    st.stop()

# ==============================================================================
# 2. ESTILOS CSS (BLINDAJE VISUAL + FONDO)
# ==============================================================================
st.markdown(f"""
    <style>
        /* 1. FONDO GENERAL CON TEXTURA */
        .stApp {{
            background: linear-gradient(rgba(14, 17, 23, 0.92), rgba(14, 17, 23, 0.96)), 
                        url("{URL_FONDO_BASE}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
            color: white;
        }}
        
        /* 2. ARREGLO DE INPUTS (Grandes y Estilizados) */
        div[data-testid="stTextInput"] input, div[data-testid="stSelectbox"] > div > div {{
            background-color: #262730 !important;
            border: 1px solid #444 !important;
            color: white !important;
            height: 50px !important; /* Más altos para que se vean bien */
            font-size: 16px !important;
            border-radius: 8px !important;
        }}
        /* Color del texto placeholder */
        input::placeholder {{ color: #rgba(255,255,255,0.5) !important; }}
        
        /* 3. ARREGLO DE BOTONES */
        button[kind="secondary"], div[data-testid="stLinkButton"] a {{
            background-color: #262730 !important;
            color: white !important;
            border: 1px solid #555 !important;
            height: 45px !important;
            border-radius: 8px !important;
            transition: all 0.3s ease;
        }}
        /* Hover Dorado (Marca Gol Gana) */
        button[kind="secondary"]:hover, div[data-testid="stLinkButton"] a:hover {{
            border-color: {COLOR_MARCA} !important;
            color: {COLOR_MARCA} !important;
            transform: translateY(-2px);
        }}
        /* Botones Primarios (Acción Principal) */
        button[kind="primary"] {{
            background-color: {COLOR_MARCA} !important;
            color: black !important;
            font-weight: 800 !important;
            border: none !important;
            height: 50px !important;
            border-radius: 8px !important;
            font-size: 16px !important;
        }}
        button[kind="primary"]:hover {{
            background-color: #FFC000 !important; /* Dorado un poco más oscuro */
            color: black !important;
        }}

        /* 4. EXPANDERS (Acordeones) */
        div[data-testid="stExpander"] details summary {{
            background-color: #262730 !important;
            border: 1px solid #444;
            color: white !important;
            border-radius: 8px;
        }}
        div[data-testid="stExpander"] details {{
            border-color: #444 !important;
            background-color: rgba(14, 17, 23, 0.5) !important; 
        }}
        div[data-testid="stExpander"] p, label, h1, h2, h3, span {{
            color: white !important;
        }}

        /* 5. TARJETAS DE LOBBY (Diseño personalizado) */
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
            background-color: rgba(255, 255, 255, 0.08);
            border-color: {COLOR_MARCA};
        }}
        .badge-fase {{
            background-color: rgba(255,255,255,0.1);
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 12px;
            letter-spacing: 1px;
            text-transform: uppercase;
        }}
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 3. LÓGICA DEL LOBBY
# ==============================================================================

def render_lobby():
    # --- A. PORTADA (HEADER) ---
    st.image(URL_PORTADA, use_container_width=True)
    
    st.markdown("""
        <div style="text-align: center; margin-bottom: 30px;">
            <p style="font-size: 18px; opacity: 0.8; margin-top: -10px;">
                La plataforma definitiva para torneos relámpago y ligas amateur.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # --- B. TORNEOS VIGENTES ---
    st.subheader("🔥 Torneos en Curso")

    try:
        # Consulta segura a la nueva tabla 'torneos'
        query = text("""
            SELECT id, nombre, organizador, color_primario, fase, formato, fecha_creacion 
            FROM torneos 
            WHERE fase != 'Terminado' 
            ORDER BY fecha_creacion DESC
        """)
        df_torneos = pd.read_sql_query(query, conn)
    except Exception as e:
        st.error("Error conectando con el servidor.")
        df_torneos = pd.DataFrame()

    if not df_torneos.empty:
        for _, t in df_torneos.iterrows():
            with st.container():
                # Renderizamos la tarjeta HTML
                st.markdown(f"""
                <div class="lobby-card" style="border-left: 6px solid {t['color_primario']};">
                    <div style="display:flex; justify-content:space-between; align-items:start;">
                        <div>
                            <h2 style="margin:0; font-weight:800; font-size: 24px;">{t['nombre']}</h2>
                            <p style="margin:5px 0 0 0; font-size:14px; opacity:0.7;">
                                👮 Organiza: <strong>{t['organizador']}</strong>
                            </p>
                            <p style="margin:0; font-size:12px; opacity:0.5;">
                                📅 {t['fecha_creacion'].strftime('%d/%m/%Y')} | 🎮 {t['formato']}
                            </p>
                        </div>
                        <div style="text-align:right;">
                            <span class="badge-fase" style="border: 1px solid {t['color_primario']}; color: {t['color_primario']};">
                                {t['fase']}
                            </span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Botón de acción (Streamlit Button para manejar la lógica)
                col_btn = st.columns([1, 2, 1])[1] # Centrado
                if st.button(f"⚽ Entrar al Torneo", key=f"btn_lobby_{t['id']}", use_container_width=True):
                    # Inyectamos el ID en la URL y recargamos
                    st.query_params["id"] = str(t['id'])
                    st.rerun()
    else:
        st.info("No hay torneos activos en este momento.")

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("---")

    # --- C. CREAR NUEVO TORNEO ---
    st.markdown(f"<h3 style='text-align:center; color:{COLOR_MARCA} !important;'>¿Eres Organizador?</h3>", unsafe_allow_html=True)
    
    with st.expander("✨ Crear Nuevo Torneo en Gol Gana", expanded=False):
        st.write("Configura tu competencia en segundos y comparte el link.")
        
        with st.form("form_crear_torneo"):
            st.markdown("##### 1. Detalles del Evento")
            new_nombre = st.text_input("Nombre del Torneo", placeholder="Ej: Relámpago Nocturno Jueves")
            
            c_f1, c_f2 = st.columns(2)
            new_formato = c_f1.selectbox("Formato de Juego", ["Grupos + Eliminatoria", "Todos contra Todos", "Eliminación Directa"])
            new_color = c_f2.color_picker("Color Identidad", "#00FF00", help="Este color te diferenciará de otros torneos.")
            
            st.markdown("##### 2. Datos del Admin")
            c_adm1, c_adm2 = st.columns(2)
            new_org = c_adm1.text_input("Tu Nombre / Cancha")
            new_wa = c_adm2.text_input("WhatsApp (Sin +)")
            
            st.markdown("##### 3. Acceso")
            new_pin = st.text_input("Crea un PIN de Admin (4 dígitos)", type="password", max_chars=4, help="No lo olvides. Es tu llave maestra.")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.form_submit_button("🚀 Crear y Gestionar", use_container_width=True, type="primary"):
                if new_nombre and new_pin and new_org:
                    try:
                        with conn.connect() as db:
                            # Insertamos el nuevo torneo
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
                        # Redirección inmediata al nuevo torneo
                        st.query_params["id"] = str(nuevo_id)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error creando el torneo: {e}")
                else:
                    st.warning("⚠️ Faltan datos obligatorios (Nombre, Organizador o PIN).")


# ==============================================================================
# 4. ENRUTADOR PRINCIPAL (MAIN)
# ==============================================================================

# Leemos la URL
params = st.query_params

if "id" in params:
    # SI HAY ID -> AQUÍ CARGAREMOS EL TORNEO (Paso siguiente)
    st.title("🚧 Cargando Torneo...")
    st.write(f"ID detectado: {params['id']}")
    if st.button("Volver al Lobby"):
        st.query_params.clear()
        st.rerun()
else:
    # SI NO HAY ID -> MOSTRAMOS EL LOBBY GOL GANA
    render_lobby()

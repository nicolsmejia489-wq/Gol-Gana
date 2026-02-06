import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import time
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
import re
import cv2
import numpy as np
import easyocr
from difflib import SequenceMatcher





# --- CONFIGURACIÓN DE CLOUDINARY CORREGIDA ---
cloudinary.config( 
    # Accedemos primero a la sección ["cloudinary"] y luego a la clave específica
    cloud_name = st.secrets["cloudinary"]["cloud_name"], 
    api_key = st.secrets["cloudinary"]["api_key"], 
    api_secret = st.secrets["cloudinary"]["api_secret"],
    secure = True
)

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

st.markdown(f"""
    <style>
        /* 0. IMPORTACIÓN Y BLINDAJE DE FUENTE OSWALD (Pesos más fuertes) */
        @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;600;700&display=swap');

        /* Forzado universal de la fuente con ajuste de espaciado (Impacto) */
        .stApp, h1, h2, h3, h4, h5, h6, p, div, button, input, label, span, textarea, a {{
            font-family: 'Oswald', sans-serif !important;
            letter-spacing: -0.02em !important;
        }}

        /* 1. FONDO GENERAL */
        .stApp {{
            background: linear-gradient(rgba(14, 17, 23, 0.92), rgba(14, 17, 23, 0.96)), 
                        url("{URL_FONDO_BASE}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
            color: white;
            -webkit-font-smoothing: antialiased;
        }}

        /* Títulos con negrilla máxima (700) */
        h1, h2, h3, .tournament-title {{
            font-weight: 700 !important;
            text-transform: uppercase;
        }}

        /* ============================================================ */
        /* 2. AJUSTE DE PESTAÑAS (TABS) - VERSIÓN COMPACTA (MÓVIL)      */
        /* ============================================================ */
        
        button[data-baseweb="tab"] {{
            flex-grow: 1 !important;
            justify-content: center !important;
            /* min-width: 150px;  <-- ELIMINADO para evitar scroll en móviles */
            min-width: 50px !important; /* Mínimo pequeño para permitir encogerse */
            
            background-color: rgba(255,255,255,0.05);
            border-radius: 8px 8px 0 0;
            color: #aaa;
            font-weight: 600 !important;
            letter-spacing: 0px !important;
            transition: all 0.3s ease;
            text-transform: uppercase;
            
            /* --- AJUSTES DE REDUCCIÓN DE TAMAÑO (~20%) --- */
            padding-left: 8px !important;   /* Antes era mayor */
            padding-right: 8px !important;  /* Antes era mayor */
            gap: 5px !important;            /* Menos espacio entre icono y texto */
            height: 45px !important;        /* Altura controlada */
        }}

        /* Reducción específica del tamaño de letra dentro de la pestaña */
        .stTabs [data-baseweb="tab"] p {{
            font-size: 14px !important; /* Reducido para que quepa todo */
        }}
        
        .stTabs [data-baseweb="tab-list"] {{ gap: 5px; }} /* Menos hueco entre pestañas */
        
        .stTabs [aria-selected="true"] {{
            background-color: rgba(255, 215, 0, 0.1) !important;
            color: {COLOR_MARCA} !important;
            border-top: 3px solid {COLOR_MARCA} !important;
        }}

        /* 3. INPUTS Y BOTONES ESTÁNDAR */
        div[data-testid="stTextInput"] input, div[data-testid="stSelectbox"] > div > div {{
            background-color: #262730 !important;
            border: 1px solid #444 !important;
            color: white !important;
            height: 50px !important;
            font-size: 18px !important;
            border-radius: 8px !important;
        }}
        
        button[kind="secondary"], div[data-testid="stLinkButton"] a {{
            background-color: #262730 !important;
            border: 1px solid #555 !important;
            color: white !important;
            font-weight: 600 !important;
            border-radius: 8px !important;
        }}
        
        button[kind="primary"] {{
            background-color: {COLOR_MARCA} !important;
            color: black !important;
            font-weight: 700 !important;
            border: none !important;
            height: 50px !important;
            font-size: 18px !important;
            border-radius: 8px !important;
            text-transform: uppercase;
        }}

        /* 4. TARJETAS DE LOBBY */
        .lobby-card {{
            background-color: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            border: 1px solid rgba(255,255,255,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
            position: relative;
        }}
        
        .lobby-card:hover {{
            transform: scale(1.01);
            border-color: {COLOR_MARCA};
            background-color: rgba(255, 255, 255, 0.08);
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        }}

        /* 5. BURBUJA DEL BOT */
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
        
        .bot-text {{ color: #ddd; font-size: 16px; font-weight: 400; line-height: 1.4; }}
        .bot-avatar {{ font-size: 28px; }}
        
        @keyframes fadeIn {{ 
            from {{ opacity:0; transform:translateY(10px); }} 
            to {{ opacity:1; transform:translateY(0); }} 
        }}

        /* 6. MANIFIESTO (FOOTER) */
        .manifesto-container {{
            margin-top: 50px; 
            padding: 30px;
            background: rgba(0,0,0,0.3);
            border-top: 1px solid #333; 
            border-radius: 15px;
        }}
        
        .intro-quote {{ font-size: 20px; font-style: italic; color: {COLOR_MARCA}; text-align: center; margin-bottom: 20px; font-weight: 400; }}
        .intro-text {{ font-size: 15px; text-align: justify; color: #aaa; line-height: 1.6; margin-bottom: 10px; font-weight: 400; }}
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






# ------------------------------------------------------------
# 1. CARGA LIGERA DEL MOTOR (Cache de Recurso)
# ------------------------------------------------------------
@st.cache_resource(show_spinner="Iniciando Cerebro Gol-Bot...")
def cargar_motor_ia():
    # Cargamos solo inglés/números para ahorrar espacio en RAM
    return easyocr.Reader(['en'], gpu=False) # Cloud no suele tener GPU

# ------------------------------------------------------------
# 2. FUNCIÓN DE VISIÓN OPTIMIZADA (V. Lite)
# ------------------------------------------------------------
def leer_marcador_ia(imagen_bytes, local_real, visitante_real):
    try:
        # A. Carga y Redimensionamiento (Crítico para la RAM)
        imagen_bytes.seek(0)
        file_bytes = np.asarray(bytearray(imagen_bytes.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        if img is None: return None, "Imagen corrupta"

        # Reducimos tamaño: Si es > 800px, la bajamos. 
        # Esto hace que la IA vuele y no consuma casi nada.
        alto, ancho = img.shape[:2]
        if ancho > 800:
            escala = 800 / ancho
            img = cv2.resize(img, (800, int(alto * escala)))

        # B. Pre-procesamiento para pantallas (Grises + Contraste)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # CLAHE ayuda a leer pantallas con mucho brillo o reflejo
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        gray = clahe.apply(gray)
        
        # C. Ejecución del OCR (Solo en la zona de interés)
        reader = cargar_motor_ia()
        # Leemos solo el 60% superior para ignorar el césped o controles
        zona = gray[0:int(gray.shape[0]*0.6), :]
        
        # Solo pedimos texto y confianza, sin detalles pesados
        resultados = reader.readtext(zona, detail=1, paragraph=False)

        candidatos_num = []
        # ... (resto de tu lógica de anclaje de nombres igual) ...
        
        # 

        # Ejemplo simplificado de extracción:
        for (bbox, texto, prob) in resultados:
            txt = texto.upper().strip()
            if prob < 0.25: continue # Ignoramos lecturas dudosas
            
            # Buscamos números de 1 o 2 dígitos (goles)
            if txt.isdigit() and int(txt) < 30:
                # Centro X para triangular
                cx = (bbox[0][0] + bbox[1][0]) / 2
                candidatos_num.append({'v': int(txt), 'x': cx})

        if len(candidatos_num) >= 2:
            candidatos_num.sort(key=lambda k: k['x'])
            return (candidatos_num[0]['v'], candidatos_num[1]['v']), "Escaneo Exitoso"

        return None, "No detecté los goles. Intenta una foto más nítida."

    except Exception as e:
        return None, f"Fallo técnico: {str(e)}"








    
# ==============================================================================
# 2. LIMPIEZA DE ESCUDO CLUDINARY
# ==============================================================================
def procesar_y_subir_escudo(archivo_imagen, nombre_equipo, id_torneo):
    """
    Sube la imagen a Cloudinary con eliminación de fondo.
    Si falla por complejidad, retorna None para ser manejado por la UI.
    """
    try:
        # Intentamos subir con IA de Cloudinary
        resultado = cloudinary.uploader.upload(
            archivo_imagen,
            folder=f"gol_gana/torneo_{id_torneo}/escudos",
            public_id=f"escudo_{nombre_equipo.replace(' ', '_').lower()}",
            background_removal="cloudinary_ai", 
            format="png" 
        )
        return resultado['secure_url']
    except Exception as e:
        # LOG interno para el desarrollador
        print(f"Error Cloudinary IA: {e}")
        # Retornamos None explícitamente para indicar que la imagen no fue válida
        return None



def validar_acceso(id_torneo, pin_ingresado):
    try:
        with conn.connect() as db:
            # 1. VERIFICAR ADMIN
            q_admin = text("SELECT nombre FROM torneos WHERE id = :id AND pin_admin = :pin")
            res_admin = db.execute(q_admin, {"id": id_torneo, "pin": pin_ingresado}).fetchone()
            if res_admin:
                return {"rol": "Admin", "id_equipo": None, "nombre_equipo": "Organizador"}
            
            # 2. VERIFICAR DT (Con Estado)
            q_dt = text("SELECT id, nombre, estado FROM equipos_globales WHERE id_torneo = :id AND pin_equipo = :pin")
            res_dt = db.execute(q_dt, {"id": id_torneo, "pin": pin_ingresado}).fetchone()
            
            if res_dt:
                # El PIN existe, ahora miramos el estado
                if res_dt.estado == 'aprobado':
                    return {"rol": "DT", "id_equipo": res_dt.id, "nombre_equipo": res_dt.nombre}
                elif res_dt.estado == 'pendiente':
                    return "PENDIENTE" # Señal especial para la UI
                else:
                    return None # Baja u otro estado (No entra)

        return None
    except: return None




    
# ==============================================================================
# 3. LÓGICA DEL LOBBY
# ==============================================================================

def render_lobby():
    # --- A. PORTADA ---
    st.image(URL_PORTADA, use_container_width=True)
    
    # --- B. SALUDO DEL BOT ---
    mostrar_bot("Hola, Soy <b>Gol Bot</b>. Guardaré las estadísticas de equipo y apoyaré al admin en la organización de cada torneo.")

    # --- C. SECCIÓN: NOVEDADES (TABS) ---
    st.markdown(f"<h3 style='text-align:center; color:{COLOR_MARCA}; margin-top:10px; letter-spacing:2px;'>NOVEDADES</h3>", unsafe_allow_html=True)
    
    tab_eq, tab_dt, tab_adm = st.tabs(["🛡️ Equipos", "🧠 DTs / Capitanes", "👮 Administradores"])
    
    with tab_eq:
        mostrar_bot("Olvídate de los debates subjetivos; aquí hablamos con datos, no opiniones. Te muestro contra quién compites más, a quién has dominado siempre o quién no has podido vencer nunca. Cada partido, título y victoria forma parte de la historia de Clubes Pro.")
    
    with tab_dt:
        mostrar_bot("Sé que gestionar un equipo es difícil. He simplificado todo para que cada competencia sea más fluida. Te facilitaré el Contacto con rivales, la revisión de marcadores y una actualización Instantánea.")
        
    with tab_adm:
        mostrar_bot("Yo te apoyaré con el trabajo sucio: lectura y proceso de marcadores, actualización de tablas, rondas y estadísticas. Tú tomas las decisiones importantes y defines los colores de tu competición para que tu comunidad resalte sobre las demás.")

    # --- LÍNEA DIVISORIA ---
    st.markdown("---")

    # ==============================================================================
    # D. TORNEOS EN CURSO (ESTE ES EL BLOQUE QUE MOVIMOS BAJO NOVEDADES)
    # ==============================================================================
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
                # 1. Diseño Visual de la Tarjeta (HTML)
                estado_txt = "INSCRIPCIONES ABIERTAS" if t['fase'] == 'inscripcion' else t['fase'].upper()
                
                st.markdown(f"""
                    <div style="border-left: 6px solid {t['color_primario']}; 
                                background: rgba(255,255,255,0.05); 
                                padding: 15px; 
                                border-radius: 0 12px 12px 0; 
                                margin-bottom: -10px;">
                        <h3 style="margin:0; color:white;">🏆 {t['nombre']}</h3>
                        <p style="margin:0; color:{t['color_primario']}; font-weight:bold; font-size:14px;">
                            ● {estado_txt}
                        </p>
                        <p style="margin:5px 0 0 0; opacity:0.7; font-size:14px;">
                            👮 {t['organizador']} | 🎮 {t['formato']}
                        </p>
                    </div>
                """, unsafe_allow_html=True)

                # 2. Botones de Acción (Nativos)
                c1, c2 = st.columns(2)
                with c1:
                    if st.button(f"Ver Torneo", key=f"v_{t['id']}", use_container_width=True):
                        st.query_params["id"] = str(t['id'])
                        st.rerun()
                with c2:
                    if st.button(f"Inscribir mi equipo", key=f"i_{t['id']}", use_container_width=True, type="primary"):
                        st.query_params["id"] = str(t['id'])
                        st.query_params["action"] = "inscribir"
                        st.rerun()
                st.markdown("<br>", unsafe_allow_html=True)
    else:
        st.info("No hay torneos activos actualmente.")

    

    # --- E. CREAR NUEVO TORNEO (Sin cambios) ---
    with st.expander("✨ ¿Eres Organizador? Crea tu Torneo", expanded=False):
        mostrar_bot("Configura tu torneo aquí. <br>Recuerda: <b>El PIN es sagrado</b>.")
        with st.form("form_crear_torneo"):
            st.markdown("##### 1. Identidad")
            new_nombre = st.text_input("Nombre de la Competencia", placeholder="Ej: Relámpago Jueves")
            c_f1, c_f2 = st.columns(2)
            new_formato = c_f1.selectbox("Formato", ["Grupos + Eliminatoria", "Todos contra Todos", "Eliminación Directa"])
            with c_f2: new_color = st.color_picker("Color de Marca", "#00FF00")
            
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
                        st.error(f"Error: {e}")
                else:
                    st.warning("⚠️ Faltan datos.")

     # --- F. MANIFIESTO (FOOTER) ---
    st.markdown(f"""
        <div class="manifesto-container">
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
        </div>
    """, unsafe_allow_html=True)






# ==============================================================================
# 4.1 LOGICA DE VALIDACIÓN DE ACCESO
# ==============================================================================
def validar_acceso(id_torneo, pin_ingresado):
    try:
        with conn.connect() as db:
            # 1. VERIFICAR ADMIN (Prioridad absoluta)
            q_admin = text("SELECT nombre FROM torneos WHERE id = :id AND pin_admin = :pin")
            res_admin = db.execute(q_admin, {"id": id_torneo, "pin": pin_ingresado}).fetchone()
            if res_admin:
                return {"rol": "Admin", "id_equipo": None, "nombre_equipo": "Organizador"}
            
            # 2. VERIFICAR DT APROBADO (Solo entran los 'aprobado')
            # Nota: Agregamos explícitamente AND estado = 'aprobado' en el SQL
            q_ok = text("""
                SELECT id, nombre 
                FROM equipos_globales 
                WHERE id_torneo = :id AND pin_equipo = :pin AND estado = 'aprobado'
            """)
            res_ok = db.execute(q_ok, {"id": id_torneo, "pin": pin_ingresado}).fetchone()
            
            if res_ok:
                return {"rol": "DT", "id_equipo": res_ok.id, "nombre_equipo": res_ok.nombre}
            
            # 3. VERIFICAR SI ESTÁ PENDIENTE (Para dar el aviso correcto)
            q_pend = text("""
                SELECT 1 
                FROM equipos_globales 
                WHERE id_torneo = :id AND pin_equipo = :pin AND estado = 'pendiente'
            """)
            # Si existe un pendiente, devolvemos la señal de alerta
            if db.execute(q_pend, {"id": id_torneo, "pin": pin_ingresado}).fetchone():
                return "PENDIENTE"

        # Si llegamos aquí, es porque no es Admin, ni DT aprobado, ni pendiente.
        # (Puede ser estado NULL, 'baja' o PIN incorrecto)
        return None

    except Exception as e:
        print(f"Error login: {e}")
        return None

        

 # ------------------------------------------------------------
#FUNCION DE PESTAÑA TORNEO
 # ------------------------------------------------------------
def contenido_pestana_torneo(id_torneo, t_color):
    """
    Renderiza la vista pública del torneo.
    Versión: Ingeniería de precisión (Alineación milimétrica y celdas fijas).
    """
    
    # ------------------------------------------------------------
    # 1. PARÁMETROS DE INGENIERÍA ESTÉTICA (TANTEA AQUÍ)
    # ------------------------------------------------------------
    # 👉 ESPACIO ENTRE TARJETAS DE PARTIDOS
    MT_PARTIDOS = "-15px"      # Más negativo = más pegadas las tarjetas del fixture

    # 👉 ESTRUCTURA DE LA TABLA (Clasificación)
    T_ALTO_FILA = "32px"       # Altura fija de cada registro (Garantiza regularidad)
    T_PAD_CELDA = "0px 5px"    # Aire interno de la celda (Arriba/Abajo Izquierda/Derecha)
    T_FONT_SIZE = "13px"       # Tamaño de la fuente
    
    # 👉 ALINEACIÓN DE LA COLUMNA "EQUIPO"
    T_W_ESCUDO_BOX = "30px"    # Ancho del 'contenedor' del escudo (El nombre empezará tras este ancho)
    T_W_ESCUDO_IMG = "22px"    # Tamaño real del escudo/emoji dentro de su caja
    T_OPACIDAD = "0.7"         # Transparencia del fondo

    st.markdown(f"""
        <style>
        /* 📦 FIXTURE: RECORTE DE ESPACIO */
        [data-testid="stImage"] {{
            margin-bottom: {MT_PARTIDOS} !important;
            padding: 0px !important;
        }}

        /* 📊 TABLA: ALINEACIÓN MILIMÉTRICA */
        .tabla-pro {{
            width: 100%;
            border-collapse: collapse;
            font-family: 'Oswald', sans-serif;
            background: rgba(0,0,0,{T_OPACIDAD});
            border: 1px solid {t_color};
        }}
        .tabla-pro th {{
            background: #000;
            color: #888;
            font-size: 10px;
            text-transform: uppercase;
            padding: 8px 2px;
            border-bottom: 2px solid {t_color};
            text-align: center;
        }}
        .tabla-pro td {{
            color: #fff;
            font-size: {T_FONT_SIZE};
            padding: {T_PAD_CELDA};
            height: {T_ALTO_FILA}; /* Altura rígida para regularidad vertical */
            border-bottom: 1px solid #222;
            text-align: center;
            vertical-align: middle;
        }}
        
        /* Contenedor Flex para la columna equipo */
        .equipo-wrapper {{
            display: flex;
            align-items: center; /* Centrado vertical del contenido interno */
            text-align: left;
            width: 100%;
        }}
        
        /* Caja fija para el escudo (Invisible pero con ancho) */
        .escudo-box {{
            width: {T_W_ESCUDO_BOX};
            display: flex;
            justify-content: center;
            align-items: center;
            flex-shrink: 0; /* Evita que la caja se encoja */
        }}
        
        .escudo-img {{
            width: {T_W_ESCUDO_IMG};
            height: {T_W_ESCUDO_IMG};
            object-fit: contain;
        }}

        .nombre-txt {{
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            padding-left: 5px;
        }}
        </style>
    """, unsafe_allow_html=True)

    # ------------------------------------------------------------
    # 2. CARGA DE DATOS
    # ------------------------------------------------------------
    try:
        with conn.connect() as db:
            res_t = db.execute(text("SELECT formato, escudo_defecto FROM torneos WHERE id=:id"), {"id": id_torneo}).fetchone()
            t_formato = res_t.formato if res_t else "Liga"
            t_escudo_defecto = res_t.escudo_defecto if res_t and res_t.escudo_defecto else None

            q_master = text("""
                SELECT p.jornada, p.goles_l, p.goles_v, p.estado, 
                       el.nombre as local, el.escudo as escudo_l,
                       ev.nombre as visitante, ev.escudo as escudo_v
                FROM partidos p
                JOIN equipos_globales el ON p.local_id = el.id
                JOIN equipos_globales ev ON p.visitante_id = ev.id
                WHERE p.id_torneo = :id ORDER BY p.jornada ASC, p.id ASC
            """)
            df_partidos = pd.read_sql_query(q_master, db, params={"id": id_torneo})
    except Exception as e:
        st.error(f"Error DB: {e}"); return

    # 3. PESTAÑAS
    titulos_tabs = []
    tiene_tabla = t_formato in ["Liga", "Grupos y Cruces", "Liga y Playoff"]
    if tiene_tabla: titulos_tabs.append("📊 Clasificación")
    if not df_partidos.empty:
        jornadas_unicas = sorted(df_partidos['jornada'].unique(), key=lambda x: int(x) if str(x).isdigit() else x)
        for j in jornadas_unicas: titulos_tabs.append(f"Jornada {j}" if str(j).isdigit() else str(j))
    else: return

    tabs = st.tabs(titulos_tabs)
    idx_tab = 0 

    # --- A. TABLA DE POSICIONES ---
    if tiene_tabla:
        with tabs[idx_tab]:
            df_fin = df_partidos[df_partidos['estado'] == 'Finalizado']
            if df_fin.empty:
                st.info("Esperando resultados...")
            else:
                equipos_set = set(df_partidos['local']).union(set(df_partidos['visitante']))
                stats = {e: {'PJ':0, 'PTS':0, 'GF':0, 'GC':0} for e in equipos_set}
                for _, f in df_fin.iterrows():
                    l, v, gl, gv = f['local'], f['visitante'], int(f['goles_l']), int(f['goles_v'])
                    stats[l]['PJ']+=1; stats[v]['PJ']+=1
                    stats[l]['GF']+=gl; stats[l]['GC']+=gv
                    stats[v]['GF']+=gv; stats[v]['GC']+=gl
                    if gl > gv: stats[l]['PTS']+=3
                    elif gv > gl: stats[v]['PTS']+=3
                    else: stats[l]['PTS']+=1; stats[v]['PTS']+=1

                df_f = pd.DataFrame.from_dict(stats, orient='index').reset_index()
                df_f.columns = ['EQ', 'PJ', 'PTS', 'GF', 'GC']
                df_f['DG'] = df_f['GF'] - df_f['GC']
                df_f = df_f.sort_values(by=['PTS', 'DG', 'GF'], ascending=False).reset_index(drop=True)
                df_f.insert(0, 'POS', range(1, len(df_f) + 1))
                
                mapa_escudos = dict(zip(df_partidos['local'], df_partidos['escudo_l']))
                mapa_escudos.update(dict(zip(df_partidos['visitante'], df_partidos['escudo_v'])))

                # HTML Tabla con Columnas Alineadas
                html = f'<table class="tabla-pro"><thead><tr><th>#</th><th style="text-align:left; padding-left:20px;">EQUIPO</th><th>PTS</th><th>PJ</th><th>GF</th><th>GC</th><th>DG</th></tr></thead><tbody>'
                for _, r in df_f.iterrows():
                    esc_url = mapa_escudos.get(r['EQ']) if mapa_escudos.get(r['EQ']) else t_escudo_defecto
                    
                    # El escudo o emoji va dentro de la caja fija .escudo-box
                    img_html = f'<img src="{esc_url}" class="escudo-img">' if esc_url else '<span style="font-size:16px">🛡️</span>'
                    
                    html += f"""<tr>
                        <td style="color:#888; font-size:11px;">{r['POS']}</td>
                        <td>
                            <div class="equipo-wrapper">
                                <div class="escudo-box">{img_html}</div>
                                <div class="nombre-txt"><b>{r['EQ']}</b></div>
                            </div>
                        </td>
                        <td style="color:{t_color}; font-weight:bold; font-size:15px;">{r['PTS']}</td>
                        <td>{r['PJ']}</td>
                        <td style="color:#777;">{r['GF']}</td>
                        <td style="color:#777;">{r['GC']}</td>
                        <td style="background:rgba(255,255,255,0.05); font-weight:bold;">{r['DG']}</td>
                    </tr>"""
                st.markdown(html + "</tbody></table>", unsafe_allow_html=True)
        idx_tab += 1

    # --- B. JORNADAS ---
    for j_actual in jornadas_unicas:
        with tabs[idx_tab]:
            df_j = df_partidos[df_partidos['jornada'] == j_actual]
            if df_j.empty: st.info("Sin partidos."); continue
            
            for _, row in df_j.iterrows():
                txt_m = f"{int(row['goles_l'])} - {int(row['goles_v'])}" if row['estado'] == 'Finalizado' else "VS"
                u_l = row['escudo_l'] if row['escudo_l'] else t_escudo_defecto
                u_v = row['escudo_v'] if row['escudo_v'] else t_escudo_defecto

                img_partido = generar_tarjeta_imagen(row['local'], row['visitante'], u_l, u_v, txt_m, t_color)
                st.image(img_partido, use_container_width=True)
        idx_tab += 1







def generar_calendario(id_torneo):
    """
    Genera el fixture automáticamente usando IDs de equipos_globales.
    Soporta: 'Grupos y Cruces' (3 Fechas), 'Liga' y 'Eliminación Directa'.
    """
    import random
    
    try:
        with conn.connect() as db:
            # 1. Validar formato del torneo
            res_t = db.execute(text("SELECT formato FROM torneos WHERE id=:id"), {"id": id_torneo}).fetchone()
            if not res_t: return False
            formato = res_t.formato

            # 2. OBTENER IDs DE EQUIPOS APROBADOS
            # Sacamos los IDs directamente de equipos_globales
            res_eq = db.execute(text("SELECT id FROM equipos_globales WHERE id_torneo=:id AND estado='aprobado'"), {"id": id_torneo})
            equipos_ids = [row[0] for row in res_eq.fetchall()] 
            
            # Mezclamos los IDs para que el sorteo sea aleatorio
            random.shuffle(equipos_ids) 
            
            n_reales = len(equipos_ids)
            if n_reales < 2:
                st.error("❌ Se necesitan al menos 2 equipos para iniciar el torneo.")
                return False

            # =========================================================
            # LÓGICA A: GRUPOS / LIGA (Round Robin o Sistema Suizo)
            # =========================================================
            if formato in ["Grupos y Cruces", "Liga", "Liga y Playoff"]:
                
                # Definir cuántas jornadas jugaremos
                if formato == "Grupos y Cruces":
                    total_jornadas = 3  # Regla de negocio: Solo 3 partidos clasificatorios
                    nueva_fase = 'clasificacion'
                else:
                    # En Liga es todos contra todos
                    total_jornadas = n_reales - 1 if n_reales % 2 == 0 else n_reales
                    nueva_fase = 'competencia'

                # Copia para manipular en el algoritmo Berger
                equipos_sorteo = equipos_ids.copy()
                
                # Si es impar, agregamos un 'None' (Descansa)
                if n_reales % 2 != 0:
                    equipos_sorteo.append(None) 

                n = len(equipos_sorteo)
                indices = list(range(n)) # Índices [0, 1, 2, 3...]

                # Bucle de Jornadas
                for jor in range(1, total_jornadas + 1):
                    # Emparejamiento (Primero con Último, Segundo con Penúltimo...)
                    for i in range(n // 2):
                        idx_l = indices[i]
                        idx_v = indices[n - 1 - i]
                        
                        id_local = equipos_sorteo[idx_l]
                        id_visitante = equipos_sorteo[idx_v]

                        # Solo insertamos si ambos son equipos reales (ninguno es None)
                        if id_local is not None and id_visitante is not None:
                            db.execute(text("""
                                INSERT INTO partidos (id_torneo, local_id, visitante_id, jornada, estado) 
                                VALUES (:idt, :l, :v, :j, 'Programado')
                            """), {"idt": id_torneo, "l": id_local, "v": id_visitante, "j": jor})
                    
                    # Rotación de índices (Algoritmo Berger para que no repitan rival)
                    indices = [indices[0]] + [indices[-1]] + indices[1:-1]

            # =========================================================
            # LÓGICA B: ELIMINACIÓN DIRECTA (Bracket Inicial)
            # =========================================================
            elif formato == "Eliminación Directa":
                nueva_fase = 'cruces'
                
                # Emparejamos 1 vs 2, 3 vs 4, etc.
                for i in range(0, n_reales, 2):
                    if i + 1 < n_reales:
                        id_local = equipos_ids[i]
                        id_visitante = equipos_ids[i+1]
                        
                        # Usamos 1 como jornada inicial por defecto
                        db.execute(text("""
                            INSERT INTO partidos (id_torneo, local_id, visitante_id, jornada, estado) 
                            VALUES (:idt, :l, :v, 1, 'Programado')
                        """), {"idt": id_torneo, "l": id_local, "v": id_visitante})

            # 3. ACTUALIZAR FASE DEL TORNEO
            db.execute(text("UPDATE torneos SET fase=:f WHERE id=:id"), {"f": nueva_fase, "id": id_torneo})
            db.commit()
            return True

    except Exception as e:
        st.error(f"Error crítico generando calendario: {e}")
        return False


  # =========================================================
       ##  ESTETICA DE PARTIDOS - RENDERIZAR 
 # =========================================================

def renderizar_tarjeta_partido(local, visita, escudo_l, escudo_v, marcador_texto, color_tema, url_fondo):
    """
    Genera el HTML de la tarjeta con estilo Gamer/Elegante y Fondo Texturizado.
    """
    # 1. Configuración de Bordes y Brillo (Lógica de Ganador)
    border_style = f"1px solid rgba(255,255,255,0.1)"
    box_shadow = "none"
    
    # Detectar ganador para iluminar borde
    try:
        if "-" in marcador_texto and marcador_texto != "VS":
            parts = marcador_texto.split('-')
            g_l = int(parts[0])
            g_v = int(parts[1])
            if g_l != g_v or (g_l == g_v and g_l > -1): 
                border_style = f"1px solid {color_tema}"
                box_shadow = f"0 0 10px {color_tema}40" # Glow
    except:
        pass

    # 2. Manejo de Escudos (Imagen vs Emoji)
    def render_img(url):
        if url and len(str(url)) > 5: # Si hay URL válida
            return f'<img src="{url}" style="width: 45px; height: 45px; object-fit: contain; filter: drop-shadow(0 2px 3px rgba(0,0,0,0.5));">'
        else: # Si es None o vacío -> Emoji
            return '<span style="font-size:30px; line-height:1;">🛡️</span>'

    html_l = render_img(escudo_l)
    html_v = render_img(escudo_v)

    # 3. HTML (Estructura idéntica a la que funcionaba)
    html_code = f"""
    <div style="
        position: relative;
        background: linear-gradient(180deg, rgba(30,30,35,0.95) 0%, rgba(15,15,20,0.98) 100%);
        border-radius: 12px;
        border: {border_style};
        box-shadow: {box_shadow};
        padding: 15px;
        margin-bottom: 12px;
        overflow: hidden;
        font-family: 'Oswald', sans-serif;
    ">
        <div style="
            position: absolute; top: 0; left: 0; width: 100%; height: 100%; 
            background-image: url('{url_fondo}'); 
            background-size: cover; opacity: 0.05; pointer-events: none; z-index: 0;
        "></div>

        <div style="display: flex; align-items: center; justify-content: space-between; position: relative; z-index: 1;">
            
            <div style="flex: 1; display: flex; align-items: center; justify-content: flex-end; gap: 10px;">
                <span style="font-weight: 600; font-size: 15px; color: #fff; text-align: right; line-height: 1.1; text-shadow: 1px 1px 2px black;">{local}</span>
                {html_l}
            </div>

            <div style="width: 90px; text-align: center;">
                <div style="
                    font-size: 24px; font-weight: 700; color: #fff; letter-spacing: 1px;
                    background: rgba(0,0,0,0.3); border-radius: 6px; padding: 2px 0; margin: 0 5px;
                ">
                    {marcador_texto}
                </div>
            </div>

            <div style="flex: 1; display: flex; align-items: center; justify-content: flex-start; gap: 10px;">
                {html_v}
                <span style="font-weight: 600; font-size: 15px; color: #fff; text-align: left; line-height: 1.1; text-shadow: 1px 1px 2px black;">{visita}</span>
            </div>
            
        </div>
    </div>
    """
    return html_code
    



   # ---------------------------------------------------------
##EN PRUEBA - FUNCION DE TARJETAS DE PARTIDOS
# ---------------------------------------------------------
@st.cache_data(show_spinner=False)
def generar_tarjeta_imagen(local, visita, url_escudo_l, url_escudo_v, marcador, color_tema):
    """
    Genera tarjeta con diseño CENTRALIZADO:
    [Nombre Local] [Escudo L] [  VS/Score  ] [Escudo V] [Nombre Visitante]
    """
    # ------------------------------------------------------------
    # 1. CONFIGURACIÓN DEL LIENZO
    # ------------------------------------------------------------
    URL_PLANTILLA = "https://res.cloudinary.com/dlvczeqlp/image/upload/v1769117628/Enfrentamientos_zbrqpf.png" 
    W, H = 800, 100 
    CENTRO_Y = H // 2 
    CENTRO_X = W // 2 # Punto crítico para el nuevo diseño

    def hex_to_rgb(hex_color):
        try:
            hex_color = hex_color.lstrip('#')
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        except: return (100, 100, 100)

    try:
        response = requests.get(URL_PLANTILLA, timeout=3)
        fondo = Image.open(BytesIO(response.content)).convert("RGBA")
        fondo = fondo.resize((W, H))
        fondo.putalpha(10) # Tu transparencia actual
        img = Image.new("RGBA", (W, H), (0,0,0,0))
        img.paste(fondo, (0,0), fondo)
    except:
        img = Image.new('RGBA', (W, H), (40, 44, 52, 200))

    draw = ImageDraw.Draw(img)

    # ------------------------------------------------------------
    # 2. FUENTES
    # ------------------------------------------------------------
    SIZE_EQUIPO = 23    
    SIZE_MARCADOR = 35  
    SIZE_VS = 30        

    FUENTES_SISTEMA = ["DejaVuSans-Bold.ttf", "arialbd.ttf", "Arial Bold.ttf", "LiberationSans-Bold.ttf"]
    font_team = None; font_score = None; font_vs = None

    for f_nombre in FUENTES_SISTEMA:
        try:
            font_team = ImageFont.truetype(f_nombre, SIZE_EQUIPO)
            font_score = ImageFont.truetype(f_nombre, SIZE_MARCADOR)
            font_vs = ImageFont.truetype(f_nombre, SIZE_VS)
            break 
        except: continue
    
    if font_team is None:
        font_team = ImageFont.load_default(); font_score = ImageFont.load_default(); font_vs = ImageFont.load_default()

    # ------------------------------------------------------------
    # 3. PROCESAR Y POSICIONAR ESCUDOS (AHORA AL CENTRO)
    # ------------------------------------------------------------
    def procesar_logo(url):
        try:
            if not url or str(url) == "None": return None
            resp = requests.get(url, timeout=2)
            im = Image.open(BytesIO(resp.content)).convert("RGBA")
            im.thumbnail((80, 80)) 
            return im
        except: return None

    esc_l = procesar_logo(url_escudo_l)
    esc_v = procesar_logo(url_escudo_v)

    # 👉 TANTEA AQUÍ: ESPACIO CENTRAL
    GAP_CENTRAL = 45 

    # --- Escudo Local o Emoji ---
    if esc_l:
        pos_y = (H - esc_l.height) // 2 
        img.paste(esc_l, (CENTRO_X - GAP_CENTRAL - esc_l.width, pos_y), esc_l)
    else:
        # AJUSTE: Si no hay escudo, se pone emoji 🛡️
        draw.text((CENTRO_X - GAP_CENTRAL - 40, CENTRO_Y), "🛡️", font=font_vs, anchor="mm")

    # --- Escudo Visitante o Emoji ---
    if esc_v:
        pos_y = (H - esc_v.height) // 2
        img.paste(esc_v, (CENTRO_X + GAP_CENTRAL, pos_y), esc_v)
    else:
        # AJUSTE: Si no hay escudo, se pone emoji 🛡️
        draw.text((CENTRO_X + GAP_CENTRAL + 40, CENTRO_Y), "🛡️", font=font_vs, anchor="mm")

    # ------------------------------------------------------------
    # 4. PINTAR NOMBRES (PEGADOS A LOS ESCUDOS HACIA AFUERA)
    # ------------------------------------------------------------
    color_texto = (255, 255, 255)
    color_sombra = (0, 0, 0)
    GAP_NOMBRE = 10 

    # == LOCAL (Anclaje a la Derecha "rm") ==
    x_text_l = CENTRO_X - GAP_CENTRAL - (esc_l.width if esc_l else 80) - GAP_NOMBRE
    draw.text((x_text_l+2, CENTRO_Y+2), local[:14], font=font_team, fill=color_sombra, anchor="rm")
    draw.text((x_text_l, CENTRO_Y), local[:14], font=font_team, fill=color_texto, anchor="rm")

    # == VISITANTE (Anclaje a la Izquierda "lm") ==
    x_text_v = CENTRO_X + GAP_CENTRAL + (esc_v.width if esc_v else 80) + GAP_NOMBRE
    draw.text((x_text_v+2, CENTRO_Y+2), visita[:14], font=font_team, fill=color_sombra, anchor="lm")
    draw.text((x_text_v, CENTRO_Y), visita[:14], font=font_team, fill=color_texto, anchor="lm")

    # ------------------------------------------------------------
    # 5. MARCADOR O VS (CENTRADO PERFECTO)
    # ------------------------------------------------------------
    if "-" in marcador:
        draw.text((CENTRO_X, CENTRO_Y), marcador, font=font_score, fill=(255, 215, 0), anchor="mm")
    else:
        draw.text((CENTRO_X + 2, CENTRO_Y + 2), "VS", font=font_vs, fill=(0,0,0), anchor="mm")
        draw.text((CENTRO_X, CENTRO_Y), "VS", font=font_vs, fill=(200, 200, 200), anchor="mm")

    # ------------------------------------------------------------
    # 6. BORDE (SÓLO LÍNEA HORIZONTAL SUPERIOR)
    # ------------------------------------------------------------
    try:
        rgb_borde = hex_to_rgb(color_tema)
        
        # 👉 TANTEA AQUÍ: GROSOR DE LA LÍNEA
        # Si quieres que la línea sea más notoria, sube el rango a 2 o 3.
        GROSOR_LINEA = 2 
        
        for i in range(GROSOR_LINEA):
            # Dibujamos una línea desde el extremo izquierdo (0) al derecho (W)
            # La 'i' hace que si el grosor es > 1, se dibujen líneas una debajo de otra.
            draw.line([(0, i), (W, i)], fill=rgb_borde, width=1)
            
    except: 
        pass

    return img
# ---------------------------------------------------------
##FIN PRUEBA - FUNCION DE TARJETAS DE PARTIDOS
# ---------------------------------------------------------





        
def render_torneo(id_torneo):
    # ---------------------------------------------------------
    # 1. DATOS MAESTROS Y CONFIGURACIÓN VISUAL
    # ---------------------------------------------------------
    try:
        query = text("SELECT nombre, organizador, color_primario, url_portada, fase FROM torneos WHERE id = :id")
        with conn.connect() as db:
            t = db.execute(query, {"id": id_torneo}).fetchone()
        
        if not t:
            st.error("Torneo no encontrado."); return
        
        t_nombre, t_org, t_color, t_portada, t_fase = t
    
    except Exception as e:
        st.error(f"Error DB: {e}"); return

    # --- CSS Personalizado (Oswald Impact) ---
    st.markdown(f"""
        <style>
            button[kind="primary"] {{ background-color: {t_color} !important; color: black !important; font-weight: 700 !important; }}
            .stTabs [aria-selected="true"] p {{ color: {t_color} !important; font-weight: 700 !important; }}
            [data-baseweb="tab-highlight-renderer"] {{ background-color: {t_color} !important; }}
            .tournament-title {{ color: white; font-size: 32px; font-weight: 700; text-transform: uppercase; margin-top: 10px; margin-bottom: 0px; letter-spacing: -0.02em; }}
            .tournament-subtitle {{ color: {t_color}; font-size: 16px; opacity: 0.9; margin-bottom: 25px; font-weight: 400; }}
            div[data-testid="stExpander"] {{ border: 1px solid {t_color}; }}
        </style>
    """, unsafe_allow_html=True)

    # --- Cabecera y Navegación ---
    st.image(t_portada if t_portada else URL_PORTADA, use_container_width=True)
    
    # Botón Salir al Lobby (Limpia sesión)
    if st.button("⬅ LOBBY", use_container_width=False):
        for k in ["rol", "id_equipo", "nombre_equipo", "login_error", "datos_temp", "reg_estado", "msg_bot_ins"]:
            if k in st.session_state: del st.session_state[k]
        st.query_params.clear(); st.rerun()

    # Títulos
    st.markdown(f'<p class="tournament-title">{t_nombre}</p>', unsafe_allow_html=True)
    
    rol_actual = st.session_state.get("rol", "Espectador")
    label_modo = f"DT: {st.session_state.get('nombre_equipo')}" if rol_actual == "DT" else rol_actual
    st.markdown(f'<p class="tournament-subtitle">Organiza: {t_org} | Modo: {label_modo}</p>', unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 2. GESTOR DE PESTAÑAS POR ROL (Esqueleto)
    # ---------------------------------------------------------
    
# --- ESCENARIO A: ADMINISTRADOR ---
    if rol_actual == "Admin":
        
        # BOTÓN SALIR (Arriba a la derecha para consistencia)
        c_vacio, c_salir = st.columns([6, 1])
        if c_salir.button("🔴 Salir", key="btn_salir_admin", use_container_width=True):
            st.session_state.clear(); st.rerun()

        tabs = st.tabs(["🏆 Torneo", "⚙️ Control de Torneo"])

        # 1. TORNEO
        with tabs[0]:
            contenido_pestana_torneo(id_torneo, t_color)

        # 2. CONTROL (Panel de Gestión)
        with tabs[1]:
            st.markdown(f"#### ⚙️ Administración de {t_nombre}")
            
            # Estilos Admin
            st.markdown(f"""<style>div[data-testid="stExpander"] {{ border: 1px solid {t_color}; border-radius: 5px; }}</style>""", unsafe_allow_html=True)

            # Lógica de Sub-Pestañas Dinámicas
            if t_fase == "inscripcion":
                sub_tabs = st.tabs(["⏳ Lista de Espera", "📋 Directorio", "⚙️ Configuración"])
            else:
                sub_tabs = st.tabs(["⚽ Gestión Partidos", "📋 Directorio", "⚙️ Configuración"])

            # =========================================================
            # SUB-TAB 1: DINÁMICA (LISTA DE ESPERA / PARTIDOS)
            # =========================================================
            with sub_tabs[0]:
                
                # --- CASO A: INSCRIPCIONES (Lista de Espera) ---
                if t_fase == "inscripcion":
                    try:
                        with conn.connect() as db:
                            q_pend = text("SELECT * FROM equipos_globales WHERE id_torneo = :id AND estado = 'pendiente'")
                            df_pend = pd.read_sql_query(q_pend, db, params={"id": id_torneo})
                        
                        if df_pend.empty:
                            mostrar_bot("Todo tranquilo por aquí, Presi. <b>No hay solicitudes pendientes</b>.")
                        else:
                            mostrar_bot(f"¡Atención! Tienes <b>{len(df_pend)} equipos</b> esperando tu visto bueno.")
                            
                            for _, r in df_pend.iterrows():
                                with st.container(border=True):
                                    c1, c2, c3 = st.columns([0.5, 3, 1], vertical_alignment="center")
                                    with c1: 
                                        if r['escudo']: st.image(r['escudo'], width=50)
                                        else: st.write("🛡️")
                                    with c2:
                                        st.markdown(f"**{r['nombre']}**")
                                        st.markdown(f"📞 {r['prefijo']} {r['celular_capitan']}")
                                    with c3:
                                        if st.button("Aprobar ✅", key=f"apr_{r['id']}", use_container_width=True):
                                            with conn.connect() as db:
                                                db.execute(text("UPDATE equipos_globales SET estado='aprobado' WHERE id=:id"), {"id": r['id']})
                                                db.commit()
                                            st.toast(f"{r['nombre']} Aprobado"); time.sleep(1); st.rerun()
                    except Exception as e:
                        st.error(f"Error cargando lista: {e}")

                # --- CASO B: COMPETENCIA (Gestión de Partidos) ---
                else:
                    mostrar_bot("🏆 **Torneo en curso.** Los equipos están jugando por la gloria. Tú tienes el control del silbato.")
                    
                    # Filtros de Control
                    filtro_partidos = st.radio("Filtrar por:", ["Todos", "Pendientes", "Conflictos"], horizontal=True, label_visibility="collapsed")
                    
                    # Query con JOIN para traer nombres (usando IDs)
                    try:
                        with conn.connect() as db:
                            q_gest = text("""
                                SELECT 
                                    p.id, p.jornada, p.goles_l, p.goles_v, p.estado, p.conflicto, 
                                    p.url_foto_l, p.url_foto_v,
                                    el.nombre as local, el.escudo as escudo_l,
                                    ev.nombre as visitante, ev.escudo as escudo_v
                                FROM partidos p
                                JOIN equipos_globales el ON p.local_id = el.id
                                JOIN equipos_globales ev ON p.visitante_id = ev.id
                                WHERE p.id_torneo = :id
                                ORDER BY p.jornada ASC, p.id ASC
                            """)
                            df_p = pd.read_sql_query(q_gest, db, params={"id": id_torneo})
                    except Exception as e:
                        df_p = pd.DataFrame(); st.error(f"Error SQL: {e}")

                    # Aplicar Filtros DataFrame
                    if not df_p.empty:
                        if filtro_partidos == "Conflictos": 
                            df_p = df_p[(df_p['conflicto'] == True) | (df_p['estado'] == 'Revision')]
                        elif filtro_partidos == "Pendientes": 
                            df_p = df_p[df_p['goles_l'].isna() | df_p['goles_v'].isna()]

                    if df_p.empty:
                        st.info(f"No hay partidos bajo el criterio: {filtro_partidos}")
                    else:
                        # Pestañas por Jornada
                        jornadas = sorted(df_p['jornada'].unique())
                        # Manejo seguro de nombres de jornada (Si es número "J1", si es texto se deja igual)
                        tabs_j = st.tabs([f"Jornada {j}" if str(j).isdigit() else str(j) for j in jornadas])
                        
                        for i, tab in enumerate(tabs_j):
                            with tab:
                                df_j = df_p[df_p['jornada'] == jornadas[i]]
                                
                                for _, row in df_j.iterrows():
                                    # Tarjeta de Partido
                                    st.markdown(f"""
                                        <div style='background: linear-gradient(180deg, rgba(30,30,30,0.9) 0%, rgba(15,15,15,0.95) 100%); 
                                        border-left: 4px solid {t_color}; border-radius: 8px; padding: 10px; margin-bottom: 15px;'>
                                    """, unsafe_allow_html=True)
                                    
                                    c_p1 = st.columns([0.5, 2, 0.8, 0.2, 0.8, 2, 0.5], vertical_alignment="center")
                                    
                                    # Local
                                    with c_p1[0]: 
                                        if row['escudo_l']: st.image(row['escudo_l'], width=35)
                                    with c_p1[1]: st.markdown(f"<div style='text-align:right; font-weight:bold; font-size:14px; line-height:1.2'>{row['local']}</div>", unsafe_allow_html=True)
                                    
                                    # Goles Local
                                    with c_p1[2]:
                                        vl = str(int(row['goles_l'])) if pd.notna(row['goles_l']) else ""
                                        gl = st.text_input("L", value=vl, max_chars=2, label_visibility="collapsed", key=f"gL_{row['id']}")
                                    
                                    # Separador
                                    with c_p1[3]: st.markdown("<div style='text-align:center; font-weight:bold; opacity:0.7'>-</div>", unsafe_allow_html=True)
                                    
                                    # Goles Visitante
                                    with c_p1[4]:
                                        vv = str(int(row['goles_v'])) if pd.notna(row['goles_v']) else ""
                                        gv = st.text_input("V", value=vv, max_chars=2, label_visibility="collapsed", key=f"gV_{row['id']}")
                                    
                                    # Visitante
                                    with c_p1[5]: st.markdown(f"<div style='text-align:left; font-weight:bold; font-size:14px; line-height:1.2'>{row['visitante']}</div>", unsafe_allow_html=True)
                                    with c_p1[6]: 
                                        if row['escudo_v']: st.image(row['escudo_v'], width=35)

                                    st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True)
                                    
                                    # Acciones
                                    c_act = st.columns([1, 1])
                                    with c_act[0]:
                                        if st.button("💾 Guardar", key=f"btn_s_{row['id']}", use_container_width=True):
                                            if gl == "" or gv == "": st.toast("⚠️ Faltan goles")
                                            elif not (gl.isdigit() and gv.isdigit()): st.toast("⚠️ Solo números")
                                            else:
                                                with conn.connect() as db:
                                                    db.execute(text("UPDATE partidos SET goles_l=:l, goles_v=:v, estado='Finalizado', conflicto=False, metodo_registro='Manual Admin' WHERE id=:id"),
                                                             {"l":int(gl), "v":int(gv), "id":row['id']})
                                                    db.commit()
                                                st.toast("Partido Actualizado"); time.sleep(0.5); st.rerun()
                                    with c_act[1]:
                                        url_ev = row['url_foto_l'] if row['url_foto_l'] else row['url_foto_v']
                                        if url_ev: 
                                            with st.popover("📷 Evidencia"):
                                                st.image(url_ev)
                                        else: st.caption("🚫 Sin foto")
                                    st.markdown("</div>", unsafe_allow_html=True)

            # =========================================================
            # SUB-TAB 2: DIRECTORIO
            # =========================================================
            with sub_tabs[1]:
                st.subheader("Equipos Aprobados")
                
                # --- LÓGICA DE CONFIRMACIÓN DE BAJA ---
                if "baja_equipo_id" in st.session_state:
                    with st.container(border=True):
                        st.warning(f"⚠️ **CONFIRMACIÓN REQUERIDA**")
                        st.write(f"¿Seguro que quieres dar de baja al equipo **{st.session_state.baja_equipo_nombre}** del torneo **{t_nombre}**?")
                        st.caption("El equipo saldrá del torneo pero sus datos permanecerán guardados.")
                        
                        col_si, col_no = st.columns(2)
                        if col_si.button("✅ Sí, dar de baja", type="primary", use_container_width=True):
                            with conn.connect() as db:
                                db.execute(text("UPDATE equipos_globales SET estado='baja' WHERE id=:id"), {"id": st.session_state.baja_equipo_id})
                                db.commit()
                            del st.session_state.baja_equipo_id
                            del st.session_state.baja_equipo_nombre
                            st.success("Equipo dado de baja del torneo."); time.sleep(1); st.rerun()
                            
                        if col_no.button("❌ Cancelar", use_container_width=True):
                            del st.session_state.baja_equipo_id
                            del st.session_state.baja_equipo_nombre
                            st.rerun()
                    st.divider()

                # --- LISTADO ---
                try:
                    with conn.connect() as db:
                        q_aprob = text("SELECT id, nombre, celular_capitan, prefijo, escudo FROM equipos_globales WHERE id_torneo = :id AND estado = 'aprobado' ORDER BY nombre ASC")
                        df_aprob = pd.read_sql_query(q_aprob, db, params={"id": id_torneo})
                    
                    if df_aprob.empty:
                        st.warning("Aún no has aprobado equipos.")
                    else:
                        st.markdown(f"**Total:** {len(df_aprob)} equipos listos.")
                        for _, row in df_aprob.iterrows():
                            with st.container():
                                c_img, c_info, c_del = st.columns([0.5, 3.5, 1], vertical_alignment="center")
                                with c_img:
                                    if row['escudo']: st.image(row['escudo'], width=35)
                                    else: st.write("🛡️")
                                with c_info:
                                    pref_url = str(row['prefijo']).replace('+', '')
                                    cel_url = str(row['celular_capitan']).replace(' ', '')
                                    link_wa = f"https://wa.me/{pref_url}{cel_url}"
                                    st.markdown(f"**{row['nombre']}** • [`Chat`]({link_wa})")
                                with c_del:
                                    if st.button("⛔", key=f"del_{row['id']}", help="Dar de baja"):
                                        st.session_state.baja_equipo_id = row['id']
                                        st.session_state.baja_equipo_nombre = row['nombre']
                                        st.rerun()
                            st.divider()
                except Exception as e:
                    st.error(f"Error listando equipos: {e}")

            # =========================================================
            # SUB-TAB 3: CONFIGURACIÓN
            # =========================================================
            with sub_tabs[2]:
                st.subheader("Ajustes del Torneo")
                
                # Color
                st.markdown("##### 🎨 Identidad")
                c_col1, c_col2 = st.columns([1, 2])
                new_color = c_col1.color_picker("Color Principal", value=t_color)
                if c_col2.button("Aplicar Color"):
                    with conn.connect() as db:
                        db.execute(text("UPDATE torneos SET color_primario = :c WHERE id = :id"), {"c": new_color, "id": id_torneo})
                        db.commit(); st.rerun()
                
                st.divider()

                # Control de Fases
                st.markdown(f"##### 🚀 Fase Actual: `{t_fase.upper()}`")
                
                if t_fase == "inscripcion":
                    if st.button("🔐 Cerrar Inscripciones e Iniciar Competencia", type="primary", use_container_width=True):
                        st.session_state.confirmar_inicio = True
                    
                    if st.session_state.get("confirmar_inicio"):
                        st.markdown("---")
                        
                        # Contamos equipos
                        with conn.connect() as db:
                            cant = db.execute(text("SELECT COUNT(*) FROM equipos_globales WHERE id_torneo=:id AND estado='aprobado'"), {"id": id_torneo}).scalar()
                        
                        mostrar_bot(f"¿Estás seguro, Presi? Tienes **{cant} equipos aprobados**. Al confirmar, generaré el calendario automáticamente.")
                        
                        col_si, col_no = st.columns(2)
                        
                        # --- BOTÓN DE INICIO (Sin Globos) ---
                        if col_si.button("✅ Sí, ¡A rodar el balón!", use_container_width=True):
                            with st.spinner("Sorteando partidos y generando cruces..."):
                                exito = generar_calendario(id_torneo)
                                if exito:
                                    del st.session_state.confirmar_inicio
                                    st.toast("🏆 ¡Torneo Iniciado con éxito!")
                                    time.sleep(1.5)
                                    st.rerun()
                        
                        if col_no.button("❌ Cancelar", use_container_width=True):
                            del st.session_state.confirmar_inicio
                            st.rerun()
                else:
                    mostrar_bot("🏆 **Torneo en curso.** Los equipos están jugando por la gloria. Tú tienes el control del silbato.")



                

 # --- ESCENARIO B: DT (Director Técnico) ---
    elif rol_actual == "DT":
        
        # 0. BOTÓN SALIR
        c_vacio, c_salir = st.columns([6, 1])
        if c_salir.button("🔴 Cerrar sesión de Club", key="btn_salir_dt", use_container_width=True):
            st.session_state.clear()
            st.rerun()

        # Pestañas
        tabs = st.tabs(["🏆 Torneo", "📅 Calendario", "👤 Mi Equipo"])

        # 1. TORNEO
        with tabs[0]:
             contenido_pestana_torneo(id_torneo, t_color)

# 2. CALENDARIO Y GESTIÓN (DT) - VERSIÓN ULTRA-COMPACTA MÓVIL
        with tabs[1]:
            # ------------------------------------------------------------
            # 0. CSS PARA FORZAR BOTONES LADO A LADO EN MÓVIL
            # ------------------------------------------------------------
            st.markdown("""
                <style>
                /* Forzamos que las columnas de botones no se rompan en móvil */
                [data-testid="column"] {
                    width: calc(50% - 5px) !important;
                    flex: 1 1 calc(50% - 5px) !important;
                    min-width: 0px !important;
                }
                /* Estilizamos los botones para que se vean uniformes */
                .stButton button {
                    height: 40px !important;
                    padding: 0px !important;
                    font-size: 13px !important;
                }
                </style>
            """, unsafe_allow_html=True)

            if t_fase == "inscripcion":
                mostrar_bot("El balón aún no rueda, Profe. Aquí verás tu fixture cuando inicie.")
            else:
                st.subheader(f"📅 Mi Calendario")
                
                try:
                    with conn.connect() as db:
                        q_mis = text("""
                            SELECT 
                                p.id, p.jornada, p.goles_l, p.goles_v, p.estado,
                                p.local_id, p.visitante_id,
                                el.nombre as nombre_local, el.escudo as escudo_l, el.prefijo as pref_l, el.celular_capitan as cel_l,
                                ev.nombre as nombre_visitante, ev.escudo as escudo_v, ev.prefijo as pref_v, ev.celular_capitan as cel_v
                            FROM partidos p
                            JOIN equipos_globales el ON p.local_id = el.id
                            JOIN equipos_globales ev ON p.visitante_id = ev.id
                            WHERE p.id_torneo = :idt 
                            AND (p.local_id = :my_id OR p.visitante_id = :my_id)
                            ORDER BY p.jornada ASC, p.id ASC
                        """)
                        mis = pd.read_sql_query(q_mis, db, params={"idt": id_torneo, "my_id": st.session_state.id_equipo})
                    
                    if mis.empty:
                        st.info("No tienes partidos asignados aún.")
                    
                    for _, p in mis.iterrows():
                        # --- INFO DEL PARTIDO ---
                        es_local = (p['local_id'] == st.session_state.id_equipo)
                        rival_pref = p['pref_v'] if es_local else p['pref_l']
                        rival_cel = p['cel_v'] if es_local else p['cel_l']
                        txt_score = f"{int(p['goles_l'])}-{int(p['goles_v'])}" if p['estado'] == 'Finalizado' else "VS"

                        # Tarjeta Imagen
                        st.image(generar_tarjeta_imagen(
                            p['nombre_local'], p['nombre_visitante'],
                            p['escudo_l'], p['escudo_v'],
                            txt_score, t_color
                        ), use_container_width=True)

                        # --- FILA DE BOTONES (ANCLAJE HORIZONTAL) ---
                        c1, c2 = st.columns(2)
                        
                        # Botón 1: WhatsApp
                        with c1:
                            if rival_pref and rival_cel:
                                num = f"{str(rival_pref).replace('+','')}{str(rival_cel).replace(' ','')}"
                                st.link_button("📞 WhatsApp", f"https://wa.me/{num}", use_container_width=True)
                            else:
                                st.button("🚫 Sin Tel.", disabled=True, use_container_width=True)

                        # Botón 2: Acción
                        with c2:
                            if p['estado'] == 'Finalizado':
                                if st.button("🚩 Reclamar", key=f"rec_{p['id']}", use_container_width=True):
                                    with conn.connect() as db:
                                        db.execute(text("UPDATE partidos SET estado='Revision', conflicto=true WHERE id=:id"), {"id": p['id']})
                                        db.commit()
                                    st.rerun()
                            elif p['estado'] == 'Revision':
                                st.button("⚠️ En Revisión", disabled=True, use_container_width=True)
                            else:
                                # Botón que activa el área de carga (Lógica de Estado)
                                if st.button("📸 Subir", key=f"btn_show_{p['id']}", type="primary", use_container_width=True):
                                    st.session_state[f"show_up_{p['id']}"] = True

                        # --- ÁREA DE CARGA CONDICIONAL (Sustituye al Popover) ---
                        if st.session_state.get(f"show_up_{p['id']}"):
                            with st.container(border=True):
                                st.markdown("##### 📸 Escanear Resultado")
                                foto = st.file_uploader("Selecciona la foto del marcador", type=['jpg','png','jpeg'], key=f"file_{p['id']}")
                                
                                col_ca, col_ok = st.columns(2)
                                if col_ca.button("Cancelar", key=f"can_{p['id']}", use_container_width=True):
                                    del st.session_state[f"show_up_{p['id']}"]; st.rerun()
                                
                                if foto and col_ok.button("Escanear", key=f"go_{p['id']}", type="primary", use_container_width=True):
                                    with st.spinner("IA procesando..."):
                                        res_ia, msg_ia = leer_marcador_ia(foto, p['nombre_local'], p['nombre_visitante'])
                                        if res_ia:
                                            gl, gv = res_ia
                                            with conn.connect() as db:
                                                db.execute(text("UPDATE partidos SET goles_l=:gl, goles_v=:gv, estado='Finalizado', metodo_registro='IA' WHERE id=:id"),
                                                           {"gl": gl, "gv": gv, "id": p['id']})
                                                db.commit()
                                            st.success(f"Detectado: {gl}-{gv}"); time.sleep(1); st.rerun()
                                        else:
                                            st.error(msg_ia)

                        st.markdown("<br>", unsafe_allow_html=True) # Espacio entre partidos

                except Exception as e:
                    st.error(f"Error: {e}")
        

                    

        # 3. MI EQUIPO
        with tabs[2]:
            sub_tabs = st.tabs(["📊 Estadísticas", "✏️ Editar Equipo"])
            
            with sub_tabs[0]:
                st.subheader("📊 Historia del Club")
                mostrar_bot("Estoy recopilando los datos. Pronto verás aquí tu rendimiento.")
                st.image("https://cdn-icons-png.flaticon.com/512/3094/3094845.png", width=100)
            
        # --- LÓGICA DE EDICIÓN ROBUSTA ---
        with sub_tabs[1]:
            id_eq = st.session_state.id_equipo
            
            try:
                with conn.connect() as db:
                    # Traemos el registro específico de ESTE torneo
                    q_me = text("SELECT * FROM equipos_globales WHERE id = :id")
                    me = db.execute(q_me, {"id": id_eq}).fetchone()

                if me:
                    # 1. Recuperar datos actuales de la DB
                    p1 = me.prefijo_dt1 if me.prefijo_dt1 else "+57"
                    n1 = me.celular_dt1 if me.celular_dt1 else ""
                    p2 = me.prefijo_dt2 if me.prefijo_dt2 else "+57"
                    n2 = me.celular_dt2 if me.celular_dt2 else ""
                    
                    # ¿Tiene dos números registrados válidos?
                    tiene_dos = (len(str(n1)) > 5 and len(str(n2)) > 5)

                    with st.form("form_mi_equipo"):
                        
                        # ==========================================
                        # A. SELECTOR DE CAPITÁN (Lógica Torneo)
                        # ==========================================
                        sel_capitan = "Unico" # Valor por defecto
                        if tiene_dos:
                            st.markdown(f"#### ©️ Contacto Visible (Capitán del Torneo)")
                            st.caption("¿A quién deben llamar los rivales y el Admin **en este torneo**?")
                            
                            # Opciones claras
                            lbl_opt1 = f"👑 DT Principal ({p1} {n1})"
                            lbl_opt2 = f"🤝 Co-DT ({p2} {n2})"
                            
                            # Pre-selección inteligente
                            idx_activo = 1 if me.celular_capitan == n2 else 0
                            
                            sel_capitan = st.radio("Selecciona el responsable activo:", 
                                                 [lbl_opt1, lbl_opt2], 
                                                 index=idx_activo, 
                                                 horizontal=True)
                            st.divider()

                        # ==========================================
                        # B. EDICIÓN DE DATOS GLOBALES
                        # ==========================================
                        st.subheader("✏️ Datos del Club")
                        
                        # IDENTIDAD
                        with st.container(border=True):
                            st.markdown("**🪪 Identidad**")
                            c_id1, c_id2 = st.columns([2, 1])
                            with c_id1:
                                new_nom = st.text_input("Nombre", value=me.nombre).strip().upper()
                            with c_id2:
                                new_pin = st.text_input("PIN", value=me.pin_equipo, type="password", max_chars=6).strip().upper()
                            
                            c_esc1, c_esc2 = st.columns([1, 4], vertical_alignment="center")
                            with c_esc1:
                                if me.escudo: st.image(me.escudo, width=50)
                                else: st.write("🛡️")
                            with c_esc2:
                                new_escudo = st.file_uploader("Nuevo Escudo", type=['png', 'jpg'], label_visibility="collapsed")

                        # Lista Países
                        paises = {
                            "Argentina": "+54", "Belice": "+501", "Bolivia": "+591", "Brasil": "+55",
                            "Chile": "+56", "Colombia": "+57", "Costa Rica": "+506", "Ecuador": "+593",
                            "EEUU/CANADA": "+1", "El Salvador": "+503", "Guatemala": "+502", 
                            "Guayana Fran": "+594", "Guyana": "+592", "Honduras": "+504", "México": "+52",
                            "Nicaragua": "+505", "Panamá": "+507", "Paraguay": "+595", "Perú": "+51",
                            "Surinam": "+597", "Uruguay": "+598", "Venezuela": "+58"
                        }
                        l_paises = [f"{k} ({paises[k]})" for k in sorted(paises.keys())]

                        # DT 1
                        with st.container(border=True):
                            st.markdown("**👤 DT Principal**")
                            c_dt1_p, c_dt1_n = st.columns([1.5, 2])
                            try: 
                                current_val = next((k for k, v in paises.items() if v == p1), "Colombia")
                                idx_p1 = sorted(paises.keys()).index(current_val)
                            except: idx_p1 = 0
                            
                            s_p1 = c_dt1_p.selectbox("P-DT1", l_paises, index=idx_p1, label_visibility="collapsed")
                            val_p1 = s_p1.split('(')[-1].replace(')', '')
                            val_n1 = c_dt1_n.text_input("N-DT1", value=n1, label_visibility="collapsed")

                        # DT 2
                        with st.container(border=True):
                            st.markdown("**👥 Co-DT (Opcional)**")
                            c_dt2_p, c_dt2_n = st.columns([1.5, 2])
                            try: 
                                current_val2 = next((k for k, v in paises.items() if v == p2), "Colombia")
                                idx_p2 = sorted(paises.keys()).index(current_val2)
                            except: idx_p2 = 0
                            
                            s_p2 = c_dt2_p.selectbox("P-DT2", l_paises, index=idx_p2, label_visibility="collapsed")
                            val_p2 = s_p2.split('(')[-1].replace(')', '')
                            val_n2 = c_dt2_n.text_input("N-DT2", value=n2, label_visibility="collapsed")

                        st.write("")
                        
                        # ==========================================
                        # C. PROCESADO Y GUARDADO
                        # ==========================================
                        if st.form_submit_button("💾 Guardar Cambios", use_container_width=True):
                            
                            # 1. Escudo
                            url_final = me.escudo
                            if new_escudo:
                                url_final = procesar_y_subir_escudo(new_escudo, new_nom, id_torneo)
                            
                            # 2. Lógica: ¿Quién es el capitán HOY?
                            if tiene_dos and sel_capitan and ("Co-DT" in sel_capitan) and len(val_n2) > 5:
                                pub_cel = val_n2
                                pub_pref = val_p2
                            else:
                                pub_cel = val_n1
                                pub_pref = val_p1

                            try:
                                with conn.connect() as db:
                                    # 3. UPDATE GLOBAL (Identidad y Contactos Base)
                                    # Actualizamos ESTE equipo por ID para asegurar precisión
                                    db.execute(text("""
                                        UPDATE equipos_globales 
                                        SET nombre=:n, pin_equipo=:new_pin, escudo=:e, 
                                            celular_dt1=:c1, prefijo_dt1=:p1,
                                            celular_dt2=:c2, prefijo_dt2=:p2
                                        WHERE id=:id_eq
                                    """), {
                                        "n": new_nom, "new_pin": new_pin, "e": url_final,
                                        "c1": val_n1, "p1": val_p1,
                                        "c2": val_n2, "p2": val_p2,
                                        "id_eq": id_eq
                                    })
                                    
                                    # PROPAGACIÓN POR PIN (OPCIONAL PERO RECOMENDADO)
                                    # Si quieres que el cambio de nombre/escudo aplique a futuros torneos
                                    db.execute(text("""
                                        UPDATE equipos_globales 
                                        SET nombre=:n, escudo=:e, pin_equipo=:new_pin
                                        WHERE pin_equipo=:old_pin
                                    """), {
                                        "n": new_nom, "e": url_final, "new_pin": new_pin, "old_pin": me.pin_equipo
                                    })
                                    
                                    # 4. UPDATE LOCAL (Capitán del Torneo)
                                    db.execute(text("""
                                        UPDATE equipos_globales 
                                        SET celular_capitan=:cp, prefijo=:pp
                                        WHERE id=:id
                                    """), {
                                        "cp": pub_cel, "pp": pub_pref, "id": id_eq
                                    })

                                    # 5. SINCRONIZACIÓN PARTIDOS (CRÍTICO PARA FIXTURE)
                                    # Si el nombre cambió, debemos actualizar la tabla partidos
                                    if new_nom != me.nombre:
                                        try:
                                            # Actualizamos local usando el ID del equipo
                                            db.execute(text("UPDATE partidos SET local=:n WHERE local_id=:id_eq"), 
                                                       {"n": new_nom, "id_eq": id_eq})
                                            # Actualizamos visitante usando el ID del equipo
                                            db.execute(text("UPDATE partidos SET visitante=:n WHERE visitante_id=:id_eq"), 
                                                       {"n": new_nom, "id_eq": id_eq})
                                        except Exception as e_match:
                                            print(f"Warning partidos: {e_match}")
                                    
                                    # Finalizar
                                    st.session_state.nombre_equipo = new_nom
                                    db.commit()
                                
                                st.toast("✅ Datos actualizados correctamente")
                                time.sleep(1.5); st.rerun()
                            
                            except Exception as e_main:
                                st.error(f"Error guardando datos: {e_main}")

            except Exception as e_load:
                st.error(f"Error cargando perfil: {e_load}")
                    


                


# --- ESCENARIO C: ESPECTADOR (Por defecto) ---
    else:
        # LÓGICA DE VISIBILIDAD DE PESTAÑAS SEGÚN FASE
        if t_fase == "inscripcion":
            tabs = st.tabs(["📝 Inscripciones", "🏆 Torneo", "🔐 Ingreso"])
            idx_torneo = 1
            idx_ingreso = 2
        else:
            # Si el torneo ya empezó, ocultamos Inscripciones
            tabs = st.tabs(["🏆 Torneo", "🔐 Ingreso"])
            idx_torneo = 0
            idx_ingreso = 1

        # ==========================================
        # 1. INSCRIPCIONES (Solo visible en fase inscripción)
        # ==========================================
        if t_fase == "inscripcion":
            with tabs[0]:
                
                # CEREBRO GOL BOT
                if "msg_bot_ins" not in st.session_state:
                    st.session_state.msg_bot_ins = "👋 ¡Hola! Si tu club ya esta registrado, recuerdame el PIN para inscribirte. Si eres nuevo, registra tu club en el formulario de abajo."
                mostrar_bot(st.session_state.msg_bot_ins)

                # --- OPCIÓN A: VÍA RÁPIDA (YA TENGO PIN) ---
                with st.container(border=True):
                    st.markdown("#### ⚡ ¿Ya tienes un Club registrado?")
                    st.caption("Usa tu PIN existente para inscribirte o reactivar tu solicitud.")
                    
                    c_pin_fast, c_btn_fast = st.columns([3, 1])
                    # AJUSTE: .upper() aquí también para facilitar la búsqueda
                    pin_fast = c_pin_fast.text_input("Tu PIN", max_chars=6, key="pin_fast", label_visibility="collapsed", placeholder="Ej: A1B2").strip().upper()
                    
                    if c_btn_fast.button("Inscribirme", use_container_width=True):
                        if not pin_fast:
                            st.warning("Escribe un PIN.")
                        else:
                            with conn.connect() as db:
                                # PASO 1: BÚSQUEDA LOCAL
                                q_local = text("SELECT id, nombre, estado FROM equipos_globales WHERE id_torneo=:idt AND pin_equipo=:p")
                                local = db.execute(q_local, {"idt": id_torneo, "p": pin_fast}).fetchone()
                                
                                if local:
                                    if local.estado == 'pendiente':
                                        st.info(f"🤖 **Gol Bot:** Tranquilo, tu solicitud con **{local.nombre}** ya está enviada.")
                                    elif local.estado == 'aprobado':
                                        st.success(f"🤖 **Gol Bot:** ¡Pero si ya estás adentro! **{local.nombre}** es oficial.")
                                        st.session_state.rol = "DT"
                                        st.session_state.id_equipo = local.id
                                        st.session_state.nombre_equipo = local.nombre
                                        time.sleep(1.5); st.rerun()
                                    else: # Reactivar baja
                                        db.execute(text("UPDATE equipos_globales SET estado='pendiente' WHERE id=:id"), {"id": local.id})
                                        db.commit()
                                        st.balloons()
                                        st.success(f"✅ ¡Solicitud Reactivada! He vuelto a poner a **{local.nombre}** en la lista de espera.")
                                else:
                                    # PASO 2: BÚSQUEDA GLOBAL
                                    q_global = text("SELECT * FROM equipos_globales WHERE pin_equipo=:p ORDER BY id DESC LIMIT 1")
                                    origen = db.execute(q_global, {"p": pin_fast}).fetchone()
                                    
                                    if origen:
                                        try:
                                            db.execute(text("""
                                                INSERT INTO equipos_globales 
                                                (id_torneo, nombre, pin_equipo, escudo, prefijo, celular_capitan, 
                                                 celular_dt1, prefijo_dt1, celular_dt2, prefijo_dt2, estado)
                                                VALUES 
                                                (:idt, :n, :pi, :e, :pr, :cc, :c1, :p1, :c2, :p2, 'pendiente')
                                            """), {
                                                "idt": id_torneo, "n": origen.nombre, "pi": origen.pin_equipo, 
                                                "e": origen.escudo, "pr": origen.prefijo, "cc": origen.celular_capitan,
                                                "c1": origen.celular_dt1, "p1": origen.prefijo_dt1,
                                                "c2": origen.celular_dt2, "p2": origen.prefijo_dt2
                                            })
                                            db.commit()
                                            nuevo = db.execute(text("SELECT id FROM equipos_globales WHERE id_torneo=:idt AND pin_equipo=:p"),
                                                             {"idt": id_torneo, "p": pin_fast}).fetchone()
                                            st.balloons()
                                            st.success(f"✅ ¡Te encontré! He traído los datos de **{origen.nombre}**.")
                                        except Exception as e:
                                            st.error(f"Error técnico: {e}")
                                    else:
                                        st.error("❌ No reconozco ese PIN. Regístrate como club nuevo abajo.")

                st.markdown("---")

                # --- OPCIÓN B: REGISTRO NUEVO ---
                st.markdown("#### 🌱 ¿Club Nuevo? Registra tu club")
                
                if "reg_estado" not in st.session_state: st.session_state.reg_estado = "formulario"
                if "datos_temp" not in st.session_state: st.session_state.datos_temp = {}

                # ESTADO: CONFIRMACIÓN
                if st.session_state.reg_estado == "confirmar":
                    d = st.session_state.datos_temp
                    with st.container(border=True):
                        c_img, c_txt = st.columns([1, 3], vertical_alignment="center")
                        with c_img:
                             if d['escudo_obj']: 
                                 d['escudo_obj'].seek(0)
                                 st.image(d['escudo_obj'])
                             else: st.write("🛡️")
                        with c_txt:
                            st.markdown(f"**{d['n']}**") # Aquí ya se verá en MAYÚSCULAS
                            st.markdown(f"📞 {d['pref']} {d['wa']}")
                            st.markdown(f"🔐 PIN: `{d['pin']}`")
                    
                    c1, c2 = st.columns(2)
                    if c1.button("✅ Confirmar Inscripción", use_container_width=True):
                         with st.spinner("Procesando club..."):
                            url_escudo = None
                            if d['escudo_obj']:
                                d['escudo_obj'].seek(0)
                                url_escudo = procesar_y_subir_escudo(d['escudo_obj'], d['n'], id_torneo)
                            
                            # --- VALIDACIÓN GOL BOT PARA ESCUDO COMPLEJO ---
                            if d['escudo_obj'] and url_escudo is None:
                                mostrar_bot("⚠️ <b>¡Ojo con esa imagen, Presi!</b> La foto es muy compleja para procesarla como escudo. He registrado el club con un escudo genérico, podrás intentar subir uno más claro luego en tu panel.")
                                # No detenemos el registro, usamos None para que la DB guarde el default
                            
                            try:
                                with conn.connect() as db:
                                    db.execute(text("""
                                        INSERT INTO equipos_globales (id_torneo, nombre, celular_capitan, prefijo, pin_equipo, escudo, estado, celular_dt1, prefijo_dt1)
                                        VALUES (:id_t, :n, :c, :p, :pi, :e, 'pendiente', :c, :p)
                                    """), {
                                        "id_t": int(id_torneo), "n": d['n'], "c": d['wa'], 
                                        "p": d['pref'], "pi": d['pin'], "e": url_escudo # Aquí irá la URL o None
                                    })
                                    db.commit()
                                    
                                    # Recuperar ID para Auto Login
                                    new_id = db.execute(text("SELECT id FROM equipos_globales WHERE id_torneo=:idt AND pin_equipo=:p AND estado='pendiente'"), 
                                                      {"idt": id_torneo, "p": d['pin']}).fetchone()
                                    
                                    st.session_state.rol = "DT"
                                    st.session_state.id_equipo = new_id.id
                                    st.session_state.nombre_equipo = d['n']
                                    st.success("¡Club Registrado!")
                                    time.sleep(2)
                                    st.rerun()
                            except Exception as e_sql:
                                st.error(f"Error crítico en base de datos: {e_sql}")

                    if c2.button("✏️ Editar", use_container_width=True):
                        st.session_state.reg_estado = "formulario"; st.rerun()

                # ESTADO: FORMULARIO
                else:
                    with st.form("registro_nuevo"):
                        d = st.session_state.get("datos_temp", {})
                        
                        # =========================================================
                        # AJUSTE CLAVE: .upper() AL FINAL DEL INPUT DE NOMBRE
                        # =========================================================
                        nom_f = st.text_input("Nombre del Equipo", value=d.get('n', '')).strip().upper()
                        
                        c_p, c_w = st.columns([1, 2])
                        paises = {
                            "Argentina": "+54", "Belice": "+501", "Bolivia": "+591", "Brasil": "+55",
                            "Chile": "+56", "Colombia": "+57", "Costa Rica": "+506", "Ecuador": "+593",
                            "EEUU/CANADA": "+1", "El Salvador": "+503", "Guatemala": "+502", 
                            "Guayana Fran": "+594", "Guyana": "+592", "Honduras": "+504", "México": "+52",
                            "Nicaragua": "+505", "Panamá": "+507", "Paraguay": "+595", "Perú": "+51",
                            "Surinam": "+597", "Uruguay": "+598", "Venezuela": "+58"
                        }
                        claves_ordenadas = sorted(paises.keys())
                        l_paises = [f"{k} ({paises[k]})" for k in claves_ordenadas]
                        
                        pais_sel = c_p.selectbox("País", l_paises)
                        wa_f = c_w.text_input("WhatsApp DT", value=d.get('wa', ''))
                        
                        # =========================================================
                        # AJUSTE CLAVE: .upper() AL FINAL DEL INPUT DE PIN
                        # =========================================================
                        pin_f = st.text_input("Crea un PIN (Evita una contraseña generica)", value=d.get('pin', ''), max_chars=6).strip().upper()
                        escudo_f = st.file_uploader("Escudo (Opcional)", type=['png', 'jpg'])

                        if st.form_submit_button("Siguiente", use_container_width=True):
                            err = False
                            with conn.connect() as db:
                                # Validación Nombre (Ya llega en Mayúsculas, la comparación funciona igual)
                                q_nom = text("SELECT 1 FROM equipos_globales WHERE id_torneo=:i AND nombre=:n AND (estado='aprobado' OR estado='pendiente')")
                                if db.execute(q_nom, {"i": id_torneo, "n": nom_f}).fetchone():
                                    st.error("Ese nombre ya existe activo en este torneo."); err = True
                                
                                q_pin = text("SELECT nombre FROM equipos_globales WHERE pin_equipo=:p LIMIT 1")
                                res_global = db.execute(q_pin, {"p": pin_f}).fetchone()
                                if res_global:
                                    st.warning(f"🤖 **Gol Bot:** El PIN NO ES VALIDO O YA ESTA REGISTRADO")
                                    err = True
                            
                            if not err and nom_f and wa_f and len(pin_f) > 3:
                                st.session_state.datos_temp = {
                                    "n": nom_f, "wa": wa_f, "pin": pin_f, 
                                    "pref": pais_sel.split('(')[-1][:-1], "escudo_obj": escudo_f
                                }
                                st.session_state.reg_estado = "confirmar"
                                st.rerun()

        # ==========================================
        # 2. TORNEO (Siempre Visible)
        # ==========================================
        with tabs[idx_torneo]:
             # LLAMADA A LA FUNCIÓN
             contenido_pestana_torneo(id_torneo, t_color)
             
        # ==========================================
        # 3. INGRESO (Siempre Visible)
        # ==========================================
        with tabs[idx_ingreso]:
            st.subheader("🔐 Acceso DT / Admin")
            with st.container(border=True):
                c_in, c_btn = st.columns([3, 1])
                pin_log = c_in.text_input("PIN", type="password", label_visibility="collapsed", placeholder="Ingresa PIN")
                
                if c_btn.button("Entrar", type="primary", use_container_width=True):
                    acc = validar_acceso(id_torneo, pin_log)
                    
                    # CASO 1: Login Exitoso (Devuelve Diccionario)
                    if isinstance(acc, dict):
                        st.session_state.update(acc)
                        st.rerun()
                    
                    # CASO 2: En Lista de Espera (Devuelve String "PENDIENTE")
                    elif acc == "PENDIENTE":
                        st.warning("⏳ Tu equipo está en **Lista de Espera**. El Admin debe aprobarte antes de que puedas gestionar tu plantilla.")
                    
                    # CASO 3: PIN Incorrecto o Baja
                    else:
                        st.error("PIN no válido en este torneo.")


                        

            


                        
# --- 4.3 EJECUCIÓN ---
params = st.query_params
if "id" in params: render_torneo(params["id"])
else: render_lobby()






























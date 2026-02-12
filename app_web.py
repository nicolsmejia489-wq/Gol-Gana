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
# SUBIR MARCADOR A CLOUDINARY 
# ------------------------------------------------------------

def subir_foto_cloudinary(archivo_foto, id_partido):
    """
    Sube la foto directamente a Cloudinary y retorna la URL.
    Usa el ID del partido para nombrar el archivo y evitar desorden.
    """
    try:
        # CRÍTICO: Reiniciar el puntero porque la IA ya leyó el archivo antes
        archivo_foto.seek(0) 
        
        # Subida directa
        respuesta = cloudinary.uploader.upload(
            archivo_foto, 
            public_id=f"partido_{id_partido}_evidencia", 
            folder="torneo_evidencias", # Carpeta en tu Cloudinary
            resource_type="image"
        )
        return respuesta.get('secure_url')
    except Exception as e:
        st.error(f"Error subiendo evidencia a la nube: {e}")
        return None


# ------------------------------------------------------------
# ALGORITMO LECTURA DE IMAGEN
# ------------------------------------------------------------
# ------------------------------------------------------------
# 1. HELPERS (Motores y Limpieza)
# ------------------------------------------------------------
@st.cache_resource(show_spinner="Despertando a Gol Bot...")
def cargar_motor_ia():
    # gpu=False es vital para la estabilidad en la nube
    return easyocr.Reader(['en'], gpu=False)

def limpiar_texto_ocr(t):
    # Solo letras y números en mayúsculas
    return re.sub(r'[^A-Z0-9]', '', t.upper())

def similitud(a, b):
    # Retorna % de parecido (0.0 a 1.0)
    return SequenceMatcher(None, a, b).ratio()

# ------------------------------------------------------------
# 2. FUNCIÓN MAESTRA CON PERSONALIDAD GOL BOT
# ------------------------------------------------------------
def leer_marcador_ia(imagen_bytes, local_real, visitante_real):
    """
    Analiza la imagen y retorna:
    - (goles_local, goles_visita), "Mensaje Éxito" -> Si todo sale bien.
    - None, "Mensaje Error" -> Si falla algo.
    """
    try:
        # --- A. CARGA Y OPTIMIZACIÓN ---
        imagen_bytes.seek(0)
        file_bytes = np.asarray(bytearray(imagen_bytes.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        if img is None: 
            return None, "🤖 : ¡Tarjeta Roja! La imagen está corrupta o no es válida."

        # Resize inteligente a 800px para velocidad
        alto, ancho = img.shape[:2]
        if ancho > 800:
            escala = 800 / ancho
            img = cv2.resize(img, (800, int(alto * escala)))

        # Pre-procesamiento (Grises + Contraste)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        gray = clahe.apply(gray)
        
        # Recorte (60% superior)
        alto_zona = int(gray.shape[0] * 0.60)
        zona_interes = gray[0:alto_zona, :]

        # --- B. LECTURA OCR ---
        reader = cargar_motor_ia()
        resultados = reader.readtext(zona_interes, detail=1, paragraph=False)

        # --- C. ANÁLISIS DE IDENTIDAD (ANTIFRAUDE) ---
        STOP_WORDS = {"FC", "CD", "CLUB", "DEPORTIVO", "ATHLETIC", "UNITED", "CITY", "REAL", "ATLETICO", "INTER", "VS"}
        
        def obtener_tokens(nombre_equipo):
            raw = limpiar_texto_ocr(nombre_equipo).split()
            tokens = [t for t in raw if len(t) > 3 and t not in STOP_WORDS]
            return tokens if tokens else raw # Fallback si el nombre es corto

        keys_l = obtener_tokens(local_real)
        keys_v = obtener_tokens(visitante_real)
        
        match_local = False
        match_visita = False
        coord_local_x = 0
        coord_visita_x = ancho
        
        candidatos_goles = []

        # --- D. BARRIDO DE RESULTADOS ---
        for (bbox, texto, prob) in resultados:
            txt = limpiar_texto_ocr(texto)
            if prob < 0.35: continue 

            centro_x = (bbox[0][0] + bbox[1][0]) / 2

            # 1. Buscar Equipos
            if not match_local:
                for k in keys_l:
                    if similitud(k, txt) > 0.8:
                        match_local = True; coord_local_x = centro_x; break
            
            if not match_visita:
                for k in keys_v:
                    if similitud(k, txt) > 0.8:
                        match_visita = True; coord_visita_x = centro_x; break

            # 2. Buscar Goles (Números < 20)
            if txt.isdigit():
                val = int(txt)
                if val < 20: 
                    candidatos_goles.append({'v': val, 'x': centro_x})

        # --- E. DIAGNÓSTICO DE GOL BOT ---
        
        # CASO 1: NO SE VEN LOS EQUIPOS (Riesgo de fraude o mala foto)
        if not (match_local or match_visita):
            return None, f"🤖 : **¡Problemas!** No logro leer los nombres de **{local_real}** o **{visitante_real}**. ¿Puedes darme una mejor foto del marcador? O puedes dejarla para que el Admin la vea personalmente"

        # CASO 2: SE VEN EQUIPOS, PERO NO LOS GOLES
        if len(candidatos_goles) < 2:
            return None, "🤖 : **¡Jugada confusa!** No indentifico bien los equipos o los goles no son claros. ¿Puedes darme una mejor foto del marcador? O puedes dejarla para que el Admin la vea personalmente"

        # CASO 3: ÉXITO (TRIANGULACIÓN)
        candidatos_goles.sort(key=lambda k: k['x'])
        
        # Filtro geométrico simple
        goles_finales = []
        for g in candidatos_goles:
            # Ignorar números muy lejos a la izquierda del local o muy a la derecha de la visita
            if match_local and g['x'] < (coord_local_x - 60): continue
            if match_visita and g['x'] > (coord_visita_x + 60): continue
            goles_finales.append(g)

        if len(goles_finales) < 2: goles_finales = candidatos_goles # Restaurar si filtramos de más

        gl = goles_finales[0]['v']
        gv = goles_finales[1]['v']

        # Detección de Inversión (Si detectó ambos y están al revés en pantalla)
        if match_local and match_visita and coord_local_x > coord_visita_x:
            # Si el Local está a la derecha del Visitante en la foto, invertimos los goles
            return (gv, gl), "🤖 :Marcador recibido."

        return (gl, gv), "🤖 Gol Bot: Marcador actualizado correctamente."

    except Exception as e:
        return None, f"🤖 Gol Bot: Error técnico en la jugada ({str(e)})."







    
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







####FUNCIONES EN PRUEBA  ##############################################################










    
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

    

   # --- E. CREAR NUEVO TORNEO ---
    with st.expander("✨ ¿Eres Organizador? Crea tu Torneo", expanded=False):
        mostrar_bot("Configura tu torneo aquí. <br>Recuerda: <b>El PIN es sagrado</b>, no lo pierdas.")
        
        with st.form("form_crear_torneo"):
            st.markdown("##### 1. Identidad")
            new_nombre = st.text_input("Nombre de la Competencia", placeholder="Ej: Relámpago Jueves")
            
            c_f1, c_f2 = st.columns(2)
            with c_f1:
                # CORRECCIÓN AQUÍ: Comilla agregada y nombres estandarizados
                new_formato = st.selectbox("Formato", [
                    "Clasificatoria y Cruces", 
                    "Liga", 
                    "Liga y Playoff", 
                    "Eliminación Directa"
                ])
            with c_f2: 
                new_color = st.color_picker("Color de Marca", "#00FF00")
            
            st.markdown("##### 2. Admin")
            c_adm1, c_adm2 = st.columns(2)
            with c_adm1: new_org = st.text_input("Tu Nombre / Cancha")
            with c_adm2: new_wa = st.text_input("WhatsApp (Sin +)")
            
            st.markdown("##### 3. Seguridad")
            new_pin = st.text_input("Crea un PIN (4 dígitos)", type="password", max_chars=4)
            st.markdown("<br>", unsafe_allow_html=True)
            
            # --- BOTÓN DE ENVÍO ---
            if st.form_submit_button("🚀 Lanzar Torneo", use_container_width=True, type="primary"):
                if new_nombre and new_pin and new_org:
                    try:
                        with conn.connect() as db:
                            # Insertamos usando RETURNING id para obtener el ID creado al instante
                            query_crear = text("""
                                INSERT INTO torneos (nombre, organizador, whatsapp_admin, pin_admin, color_primario, fase, formato)
                                VALUES (:n, :o, :w, :p, :c, 'inscripcion', :f) 
                                RETURNING id
                            """)
                            
                            result = db.execute(query_crear, {
                                "n": new_nombre, 
                                "o": new_org, 
                                "w": new_wa, 
                                "p": new_pin, 
                                "c": new_color, 
                                "f": new_formato
                            })
                            
                            # Obtenemos el ID del nuevo torneo
                            nuevo_id = result.fetchone()[0]
                            db.commit()
                        
                        st.balloons()
                        st.success(f"¡Torneo '{new_nombre}' creado! Redirigiendo...")
                        time.sleep(1.5)
                        
                        # Redirección automática al nuevo torneo
                        st.query_params["id"] = str(nuevo_id)
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Error al crear: {e}")
                else:
                    st.warning("⚠️ Faltan datos obligatorios (Nombre, Organizador o PIN).")

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





#### FUNCIONES DE TORNEO EN PRUEBA ##############################################################
  # =========================================================

def analizar_estado_torneo(id_torneo):
    """
    Revisa si el torneo está listo para avanzar de fase.
    Retorna un diccionario con:
    - 'listo': True/False
    - 'mensaje': Texto para el usuario
    - 'fase_actual': La fase en la que está ahora
    - 'accion_siguiente': Qué pasará si avanza (ej: 'Generar Octavos')
    """
    try:
        with conn.connect() as db:
            # 1. Obtener Info Torneo
            t = db.execute(text("SELECT fase, formato FROM torneos WHERE id=:id"), {"id": id_torneo}).fetchone()
            if not t: return {"listo": False, "mensaje": "Torneo no encontrado"}
            
            fase = t.fase
            formato = t.formato

            # CASO 0: INSCRIPCIÓN (Siempre listo si hay equipos)
            if fase == 'inscripcion':
                cant = db.execute(text("SELECT COUNT(*) FROM equipos_globales WHERE id_torneo=:id AND estado='aprobado'"), {"id": id_torneo}).scalar()
                if cant < 2:
                    return {"listo": False, "mensaje": f"Solo hay {cant} equipos inscritos. Mínimo 2."}
                return {
                    "listo": True, 
                    "mensaje": "✅ Inscripciones abiertas. ¿Cerrar e Iniciar Torneo?",
                    "accion_siguiente": "Generar Calendario Inicial",
                    "fase_actual": fase
                }

            # CASO 1: VALIDAR PARTIDOS PENDIENTES
            # Buscamos partidos que NO estén finalizados en la fase actual
            # Nota: Si tu tabla partidos no tiene columna 'fase', usamos la fecha o estado. 
            # Asumiré que validamos TODOS los partidos activos del torneo para simplificar, 
            # o idealmente filtrar por la fase actual si agregaste esa columna.
            pendientes = db.execute(text("""
                SELECT COUNT(*) FROM partidos 
                WHERE id_torneo=:id AND (estado != 'Finalizado' OR conflicto = true)
            """), {"id": id_torneo}).scalar()

            if pendientes > 0:
                return {
                    "listo": False, 
                    "mensaje": f"Aún faltan <b>{pendientes} partidos</b> por jugar o tienen conflictos pendientes.", 
                    "fase_actual": fase
                }

            # CASO 2: LISTO PARA AVANZAR
            # Aquí determinamos cuál es la siguiente fase según el formato
            siguiente = "Siguiente Ronda"
            
            if formato == "Clasificatoria y Cruces":
                if fase == 'clasificacion': siguiente = "Generar Eliminatorias (Mata-Mata)"
                elif fase == 'octavos': siguiente = "Generar Cuartos de Final"
                elif fase == 'cuartos': siguiente = "Generar Semifinales"
                elif fase == 'semis': siguiente = "Generar Gran Final"
                elif fase == 'final': siguiente = "🏆 FINALIZAR TORNEO"
            
            elif formato == "Liga":
                siguiente = "🏆 FINALIZAR TORNEO (Coronar Campeón)"

            return {
                "listo": True,
                "mensaje": f"✅ Todo listo en {fase}. Se procederá a: {siguiente}",
                "accion_siguiente": siguiente,
                "fase_actual": fase
            }

    except Exception as e:
        return {"listo": False, "mensaje": f"Error análisis: {e}"}


  # ==============================================================================
            # 00. FUNCION PRINCIPAL AVANCE DE TORNEO
 # ==============================================================================
        
def ejecutar_avance_fase(id_torneo):
    """
    Ejecuta la transición de fase: Calcula tablas, genera cruces y actualiza el torneo.
    AHORA INCLUYE: Guardado de historial y jornadas en texto (Varchar).
    """
    import math
    
    # Análisis previo para seguridad
    estado = analizar_estado_torneo(id_torneo)
    if not estado['listo']:
        return False, estado['mensaje']

    fase_act = estado['fase_actual']
    
    try:
        with conn.connect() as db:
            # Recuperar formato y datos clave
            t = db.execute(text("SELECT formato, clasifica_play_off FROM torneos WHERE id=:id"), {"id": id_torneo}).fetchone()
            formato = t.formato
            
            # ==============================================================================
            # 1. DE INSCRIPCIÓN A JUEGO (Generar Calendario)
            # ==============================================================================
            if fase_act == 'inscripcion':
                # Llamamos a tu función externa generar_calendario. 
                # Asumimos que esa función ya inserta '1', '2', '3' como strings en jornada.
                if generar_calendario(id_torneo):
                    nueva_fase = 'clasificacion' if formato == 'Clasificatoria y Cruces' else 'regular'
                    db.execute(text("UPDATE torneos SET fase=:f WHERE id=:id"), {"f": nueva_fase, "id": id_torneo})
                    db.commit()
                    return True, f"¡Balón al centro! Torneo iniciado en fase: {nueva_fase}"
                else:
                    return False, "Error generando el calendario inicial."

            # ==============================================================================
            # 2. FORMATO: CLASIFICATORIA Y CRUCES
            # ==============================================================================
            if formato == 'Clasificatoria y Cruces':
                
                # A. DE CLASIFICACIÓN -> PRIMER CRUCE (Octavos/Cuartos/Semi)
                if fase_act == 'clasificacion':
                    # 1. Calcular Tabla General
                    partidos = db.execute(text("SELECT local_id, visitante_id, goles_l, goles_v FROM partidos WHERE id_torneo=:id AND estado='Finalizado'"), {"id": id_torneo}).fetchall()
                    eqs = db.execute(text("SELECT id FROM equipos_globales WHERE id_torneo=:id AND estado='aprobado'"), {"id": id_torneo}).fetchall()
                    
                    stats = {e[0]: {'pts':0, 'gf':0, 'dg':0, 'id': e[0]} for e in eqs}

                    for p in partidos:
                        lid, vid, gl, gv = p
                        stats[lid]['gf'] += gl; stats[lid]['dg'] += (gl - gv)
                        stats[vid]['gf'] += gv; stats[vid]['dg'] += (gv - gl)
                        if gl > gv: stats[lid]['pts'] += 3
                        elif gv > gl: stats[vid]['pts'] += 3
                        else: stats[lid]['pts'] += 1; stats[vid]['pts'] += 1
                    
                    # Ordenar Tabla
                    tabla = sorted(stats.values(), key=lambda x: (x['pts'], x['dg'], x['gf']), reverse=True)
                    N = len(tabla)
                    
                    # Definir corte y nombre de fase (TEXTO)
                    if 8 <= N <= 12:
                        clasificados = tabla[:4]; next_phase_name = 'semis'; jornada_txt = 'Semifinal'
                    elif 13 <= N <= 19:
                        clasificados = tabla[:8]; next_phase_name = 'cuartos'; jornada_txt = 'Cuartos'
                    elif 20 <= N <= 32:
                        clasificados = tabla[:16]; next_phase_name = 'octavos'; jornada_txt = 'Octavos'
                    else:
                        clasificados = tabla[:2]; next_phase_name = 'final'; jornada_txt = 'Final'
                    
                    # Generar Cruces (1 vs Último)
                    num_clas = len(clasificados)
                    for i in range(num_clas // 2):
                        loc = clasificados[i]['id']
                        vis = clasificados[num_clas - 1 - i]['id']
                        
                        # INSERTAMOS LA JORNADA COMO TEXTO
                        db.execute(text("""
                            INSERT INTO partidos (id_torneo, local_id, visitante_id, jornada, estado)
                            VALUES (:id, :l, :v, :jtxt, 'Programado') 
                        """), {"id": id_torneo, "l": loc, "v": vis, "jtxt": jornada_txt})

                    db.execute(text("UPDATE torneos SET fase=:f WHERE id=:id"), {"f": next_phase_name, "id": id_torneo})
                    db.commit()
                    return True, f"¡Clasificación terminada! Se generaron los partidos de: {jornada_txt}."

                # B. AVANCE DE ELIMINATORIAS (Octavos->Cuartos->Semis->Final)
                elif fase_act in ['octavos', 'cuartos', 'semis']:
                    limit = 8 if fase_act == 'octavos' else 4 if fase_act == 'cuartos' else 2
                    
                    # Traer partidos recientes
                    matches = db.execute(text("""
                        SELECT id, local_id, visitante_id, goles_l, goles_v, penales_l, penales_v 
                        FROM partidos 
                        WHERE id_torneo=:id AND estado='Finalizado'
                        ORDER BY id DESC LIMIT :lim
                    """), {"id": id_torneo, "lim": limit}).fetchall()
                    
                    # Ordenar por ID para mantener llaves
                    matches = sorted(matches, key=lambda x: x[0])
                    
                    ganadores = []
                    for m in matches:
                        # Desempate con penales
                        pl = m.penales_l if m.penales_l is not None else 0
                        pv = m.penales_v if m.penales_v is not None else 0
                        gl = m.goles_l + (0.1 if pl > pv else 0)
                        gv = m.goles_v + (0.1 if pv > pl else 0)
                        
                        if gl > gv: ganadores.append(m.local_id)
                        else: ganadores.append(m.visitante_id)
                    
                    if len(ganadores) < 2: return False, "Error crítico: No hay suficientes ganadores."
                    
                    # Definir siguiente fase y etiqueta de jornada
                    next_ph = ""; j_txt = ""
                    if fase_act == 'octavos': next_ph = 'cuartos'; j_txt = 'Cuartos'
                    elif fase_act == 'cuartos': next_ph = 'semis'; j_txt = 'Semifinal'
                    elif fase_act == 'semis': next_ph = 'final'; j_txt = 'Final'
                    
                    # Emparejar
                    for i in range(0, len(ganadores), 2):
                        db.execute(text("""
                            INSERT INTO partidos (id_torneo, local_id, visitante_id, jornada, estado)
                            VALUES (:id, :l, :v, :jtxt, 'Programado')
                        """), {"id": id_torneo, "l": ganadores[i], "v": ganadores[i+1], "jtxt": j_txt})
                    
                    db.execute(text("UPDATE torneos SET fase=:f WHERE id=:id"), {"f": next_ph, "id": id_torneo})
                    db.commit()
                    return True, f"Ronda finalizada. Bienvenidos a: {j_txt}."

                # ==============================================================================
                # 3. GRAN FINAL -> GUARDADO DE HISTORIA
                # ==============================================================================
                elif fase_act == 'final':
                    # A. Determinar al Campeón (Ganador del último partido)
                    final_match = db.execute(text("""
                        SELECT local_id, visitante_id, goles_l, goles_v, penales_l, penales_v 
                        FROM partidos WHERE id_torneo=:id AND estado='Finalizado' ORDER BY id DESC LIMIT 1
                    """), {"id": id_torneo}).fetchone()
                    
                    campeon_id = None
                    if final_match:
                        pl = final_match.penales_l if final_match.penales_l is not None else 0
                        pv = final_match.penales_v if final_match.penales_v is not None else 0
                        if (final_match.goles_l + (0.1*pl)) > (final_match.goles_v + (0.1*pv)):
                            campeon_id = final_match.local_id
                        else:
                            campeon_id = final_match.visitante_id

                    # B. Recopilar Estadísticas de TODO el torneo para TODOS los equipos
                    all_matches = db.execute(text("""
                        SELECT local_id, visitante_id, goles_l, goles_v, penales_l, penales_v 
                        FROM partidos WHERE id_torneo=:id AND estado='Finalizado'
                    """), {"id": id_torneo}).fetchall()

                    # Diccionario acumulador {id_equipo: {stats...}}
                    team_stats = {} 

                    for m in all_matches:
                        lid, vid = m.local_id, m.visitante_id
                        gl, gv = m.goles_l, m.goles_v
                        # Ganador del partido (incluyendo penales para saber quien ganó)
                        pl = m.penales_l if m.penales_l is not None else 0
                        pv = m.penales_v if m.penales_v is not None else 0
                        
                        # Inicializar si no existen
                        if lid not in team_stats: team_stats[lid] = {'pj':0, 'pg':0, 'pe':0, 'pp':0, 'gf':0, 'gc':0}
                        if vid not in team_stats: team_stats[vid] = {'pj':0, 'pg':0, 'pe':0, 'pp':0, 'gf':0, 'gc':0}

                        # Sumar PJ, GF, GC
                        team_stats[lid]['pj'] += 1; team_stats[lid]['gf'] += gl; team_stats[lid]['gc'] += gv
                        team_stats[vid]['pj'] += 1; team_stats[vid]['gf'] += gv; team_stats[vid]['gc'] += gl

                        # Definir G/E/P (Consideramos penales como decisivos para PG/PP en historial)
                        score_l = gl + (0.1 * pl)
                        score_v = gv + (0.1 * pv)

                        if score_l > score_v:
                            team_stats[lid]['pg'] += 1
                            team_stats[vid]['pp'] += 1
                        elif score_v > score_l:
                            team_stats[vid]['pg'] += 1
                            team_stats[lid]['pp'] += 1
                        else:
                            team_stats[lid]['pe'] += 1
                            team_stats[vid]['pe'] += 1
                    
                    # C. Escribir en la Tabla Histórica (Upsert Manual)
                    # Obtenemos identidades (Nombre y PIN)
                    equipos_participantes = db.execute(text("SELECT id, nombre, pin_equipo FROM equipos_globales WHERE id_torneo=:id"), 
                                                       {"id": id_torneo}).fetchall()
                    
                    for eq in equipos_participantes:
                        eid = eq.id
                        enombre = eq.nombre
                        epin = eq.pin_equipo
                        
                        if eid in team_stats:
                            s = team_stats[eid]
                            es_campeon = 1 if eid == campeon_id else 0
                            
                            # 1. Verificar si ya existe en historial
                            existe = db.execute(text("SELECT id FROM historia_equipos_res WHERE nombre=:n AND pin=:p"), 
                                                {"n": enombre, "p": epin}).fetchone()
                            
                            if existe:
                                # UPDATE
                                db.execute(text("""
                                    UPDATE historia_equipos_res 
                                    SET torneos_jugados = torneos_jugados + 1,
                                        titulos = titulos + :tit,
                                        partidos_jugados = partidos_jugados + :pj,
                                        partidos_ganados = partidos_ganados + :pg,
                                        partidos_empatados = partidos_empatados + :pe,
                                        partidos_perdidos = partidos_perdidos + :pp,
                                        goles_favor = goles_favor + :gf,
                                        goles_contra = goles_contra + :gc,
                                        ultima_actualizacion = CURRENT_TIMESTAMP
                                    WHERE id = :hid
                                """), {
                                    "tit": es_campeon, "pj": s['pj'], "pg": s['pg'], "pe": s['pe'], 
                                    "pp": s['pp'], "gf": s['gf'], "gc": s['gc'], "hid": existe.id
                                })
                            else:
                                # INSERT
                                db.execute(text("""
                                    INSERT INTO historia_equipos_res 
                                    (nombre, pin, torneos_jugados, titulos, partidos_jugados, partidos_ganados, partidos_empatados, partidos_perdidos, goles_favor, goles_contra)
                                    VALUES (:n, :p, 1, :tit, :pj, :pg, :pe, :pp, :gf, :gc)
                                """), {
                                    "n": enombre, "p": epin, "tit": es_campeon,
                                    "pj": s['pj'], "pg": s['pg'], "pe": s['pe'], "pp": s['pp'], "gf": s['gf'], "gc": s['gc']
                                })

                    # D. Cerrar Torneo
                    db.execute(text("UPDATE torneos SET fase='FINALIZADO', estado='Historial' WHERE id=:id"), {"id": id_torneo})
                    db.commit()
                    return True, "🏆 ¡Torneo Finalizado! Historia actualizada y Campeón coronado."

            # ==============================================================================
            # 4. OTROS FORMATOS (LIGA, ETC) - Lógica simple por ahora
            # ==============================================================================
            return False, "Formato o fase no reconocida."

    except Exception as e:
        return False, f"Error ejecutando avance: {e}"


####FIN FUNCIONES EN PRUEBA ##############################################################





  # =========================================================



# ------------------------------------------------------------
# FUNCIÓN DE PESTAÑA TORNEO (LÓGICA HÍBRIDA + ORDENAMIENTO)
# ------------------------------------------------------------
def contenido_pestana_torneo(id_torneo, t_color):
    """
    Renderiza la vista pública del torneo.
    Estructura: 
    1. Clasificación/Llaves (Situación actual)
    2. Partidos (Desglose por Jornadas/Fases en pestañas)
    """
    
    # ------------------------------------------------------------
    # 1. ESTILOS CSS (Mantenemos tu ingeniería de precisión)
    # ------------------------------------------------------------
    T_OPACIDAD = "0.7"
    st.markdown(f"""
        <style>
        /* Ajuste de márgenes para tarjetas */
        [data-testid="stImage"] {{ margin-bottom: -15px !important; }}
        
        /* Tabla de Posiciones */
        .tabla-pro {{
            width: 100%; border-collapse: collapse; font-family: 'Oswald', sans-serif;
            background: rgba(0,0,0,{T_OPACIDAD}); border: 1px solid {t_color};
        }}
        .tabla-pro th {{
            background: #000; color: #888; font-size: 10px; text-transform: uppercase;
            padding: 8px 2px; border-bottom: 2px solid {t_color}; text-align: center;
        }}
        .tabla-pro td {{
            color: #fff; font-size: 13px; padding: 0px 5px; height: 32px;
            border-bottom: 1px solid #222; text-align: center; vertical-align: middle;
        }}
        .equipo-wrapper {{ display: flex; align-items: center; width: 100%; }}
        .escudo-box {{ width: 30px; display: flex; justify-content: center; flex-shrink: 0; }}
        .escudo-img {{ width: 22px; height: 22px; object-fit: contain; }}
        .nombre-txt {{ white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding-left: 5px; }}
        
        /* Estilo simple para el Bracket (Columnas) */
        .bracket-header {{
            text-align: center; color: {t_color}; font-weight: bold; 
            border-bottom: 1px solid #333; margin-bottom: 10px; padding-bottom: 5px;
        }}
        </style>
    """, unsafe_allow_html=True)

    # ------------------------------------------------------------
    # 2. CARGA DE DATOS INTELIGENTE
    # ------------------------------------------------------------
    try:
        with conn.connect() as db:
            # Info Torneo
            res_t = db.execute(text("SELECT formato, escudo_defecto FROM torneos WHERE id=:id"), {"id": id_torneo}).fetchone()
            if not res_t: st.error("Torneo no encontrado"); return
            
            t_formato = res_t.formato
            t_escudo_defecto = res_t.escudo_defecto

            # Traer TODOS los partidos
            q_master = text("""
                SELECT p.jornada, p.goles_l, p.goles_v, p.estado, p.penales_l, p.penales_v,
                       el.nombre as local, el.escudo as escudo_l,
                       ev.nombre as visitante, ev.escudo as escudo_v
                FROM partidos p
                JOIN equipos_globales el ON p.local_id = el.id
                JOIN equipos_globales ev ON p.visitante_id = ev.id
                WHERE p.id_torneo = :id 
                ORDER BY p.id ASC
            """)
            df = pd.read_sql_query(q_master, db, params={"id": id_torneo})

    except Exception as e:
        st.error(f"Error cargando datos: {e}"); return

    if df.empty:
        st.info("🗓️ El calendario aún no se ha generado.")
        return

    # ------------------------------------------------------------
    # 3. PROCESAMIENTO: SEPARAR FASES Y ORDENAR
    # ------------------------------------------------------------
    
    # Función de ordenamiento personalizada (Clave del éxito)
    def sorter_fases(j):
        # 1. Si es número, valor real
        if str(j).isdigit(): return int(j)
        # 2. Si es texto, asignamos peso artificial alto
        mapa_fases = {
            'Octavos': 100, 'Cuartos': 101, 'Semifinal': 102, 'Final': 103,
            'Repechaje': 99 # Por si acaso
        }
        return mapa_fases.get(j, 999) # 999 para desconocidos al final

    # Separamos DataFrames
    # df_regular: Jornadas numéricas (Fase de Grupos / Liga)
    df_regular = df[df['jornada'].apply(lambda x: str(x).isdigit())]
    
    # df_playoff: Jornadas de texto (Fase KO)
    df_playoff = df[~df['jornada'].apply(lambda x: str(x).isdigit())]

    # ------------------------------------------------------------
    # 4. RENDERIZADO: PESTAÑAS MAESTRAS
    # ------------------------------------------------------------
    # Dos grandes áreas: Situación (Tabla/Bracket) y Partidos (El detalle)
    main_tabs = st.tabs(["📊 Situación del Torneo", "📅 Calendario de Partidos"])

    # ============================================================
    # TAB A: SITUACIÓN (TABLA DE POSICIONES Y BRACKET)
    # ============================================================
    with main_tabs[0]:
        
        # 1. TABLA DE POSICIONES (Si existe fase regular)
        if not df_regular.empty:
            st.markdown("##### 🏆 Fase de Clasificación")
            
            # Cálculo de Tabla (Tu lógica optimizada)
            df_fin = df_regular[df_regular['estado'] == 'Finalizado']
            equipos_set = set(df_regular['local']).union(set(df_regular['visitante']))
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
            
            # Mapa de Escudos
            mapa_escudos = dict(zip(df_regular['local'], df_regular['escudo_l']))
            mapa_escudos.update(dict(zip(df_regular['visitante'], df_regular['escudo_v'])))

            # Render HTML
            html = f'<table class="tabla-pro"><thead><tr><th>#</th><th style="text-align:left; padding-left:20px;">EQUIPO</th><th>PTS</th><th>PJ</th><th>GF</th><th>GC</th><th>DG</th></tr></thead><tbody>'
            for _, r in df_f.iterrows():
                esc_url = mapa_escudos.get(r['EQ']) if mapa_escudos.get(r['EQ']) else t_escudo_defecto
                img_html = f'<img src="{esc_url}" class="escudo-img">' if esc_url else '🛡️'
                html += f"""<tr>
                    <td style="color:#888;">{r['POS']}</td>
                    <td><div class="equipo-wrapper"><div class="escudo-box">{img_html}</div><div class="nombre-txt"><b>{r['EQ']}</b></div></div></td>
                    <td style="color:{t_color}; font-weight:bold;">{r['PTS']}</td>
                    <td>{r['PJ']}</td><td style="color:#777;">{r['GF']}</td><td style="color:#777;">{r['GC']}</td>
                    <td style="background:rgba(255,255,255,0.05); font-weight:bold;">{r['DG']}</td>
                </tr>"""
            st.markdown(html + "</tbody></table>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

        # 2. BRACKET / LLAVES (Si existe fase KO)
        if not df_playoff.empty:
            st.markdown("##### ⚔️ Fase Eliminatoria")
            
            # Identificar fases únicas y ordenarlas (Octavos -> Cuartos -> Semi...)
            fases_ko = sorted(df_playoff['jornada'].unique(), key=sorter_fases)
            
            # Renderizado en Columnas (Layout tipo Bracket simple por ahora)
            cols = st.columns(len(fases_ko))
            
            for idx, fase in enumerate(fases_ko):
                with cols[idx]:
                    st.markdown(f"<div class='bracket-header'>{fase}</div>", unsafe_allow_html=True)
                    
                    matches_fase = df_playoff[df_playoff['jornada'] == fase]
                    for _, row in matches_fase.iterrows():
                        # Lógica visual simple para cruces
                        txt_score = "VS"
                        if row['estado'] == 'Finalizado':
                            # Incluir penales si existen
                            txt_score = f"{int(row['goles_l'])}-{int(row['goles_v'])}"
                            if row['penales_l'] is not None:
                                txt_score += f" ({int(row['penales_l'])}-{int(row['penales_v'])})"
                        
                        u_l = row['escudo_l'] if row['escudo_l'] else t_escudo_defecto
                        u_v = row['escudo_v'] if row['escudo_v'] else t_escudo_defecto
                        
                        # Reusamos tu generador de tarjetas pero más pequeño si es necesario
                        st.image(generar_tarjeta_imagen(row['local'], row['visitante'], u_l, u_v, txt_score, t_color), use_container_width=True)

    # ============================================================
    # TAB B: CALENDARIO (DETALLE POR JORNADAS)
    # ============================================================
    with main_tabs[1]:
        # 1. Obtener lista completa de jornadas únicas ordenadas
        jornadas_todas = sorted(df['jornada'].unique(), key=sorter_fases)
        
        # 2. Crear las sub-pestañas navegables (Scroll horizontal nativo)
        tabs_jornadas = st.tabs([str(j) for j in jornadas_todas])
        
        # 3. Llenar cada pestaña
        for i, j_actual in enumerate(jornadas_todas):
            with tabs_jornadas[i]:
                df_j = df[df['jornada'] == j_actual]
                
                if df_j.empty: 
                    st.info("Sin partidos programados.")
                else:
                    for _, row in df_j.iterrows():
                        # Marcador inteligente con penales
                        txt_m = "VS"
                        if row['estado'] == 'Finalizado':
                            txt_m = f"{int(row['goles_l'])} - {int(row['goles_v'])}"
                            if row['penales_l'] is not None:
                                # Agregamos indicador de penales pequeño
                                txt_m += f" ({int(row['penales_l'])}-{int(row['penales_v'])})"
                        
                        u_l = row['escudo_l'] if row['escudo_l'] else t_escudo_defecto
                        u_v = row['escudo_v'] if row['escudo_v'] else t_escudo_defecto

                        img_partido = generar_tarjeta_imagen(row['local'], row['visitante'], u_l, u_v, txt_m, t_color)
                        st.image(img_partido, use_container_width=True)







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
 #FUNCION DE TARJETAS DE PARTIDOS
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
#- FUNCION DE TARJETAS DE PARTIDOS
# ---------------------------------------------------------







@st.dialog("📝 Gestión del Partido")
def modal_edicion_admin(row, id_torneo):
    # 1. Cabecera Visual (Nombres Reales)
    st.markdown(f"""
    <div style='text-align: center; font-weight: 900; font-size: 20px; margin-bottom: 20px; color: white;'>
        {row['local']} <span style='color: #666; font-size: 16px; font-weight: normal;'>vs</span> {row['visitante']}
    </div>
    """, unsafe_allow_html=True)
    
    # 2. Inputs de Goles (Etiquetados con el Nombre del Equipo)
    c1, c_vs, c2 = st.columns([2, 0.5, 2], vertical_alignment="bottom")
    
    val_l = int(row['goles_l']) if pd.notna(row['goles_l']) else 0
    val_v = int(row['goles_v']) if pd.notna(row['goles_v']) else 0
    
    with c1: 
        # Label dinámico: Nombre del equipo
        gl = st.number_input(f"{row['local']}", value=val_l, min_value=0, key="m_gl")
    with c_vs:
        st.markdown("<div style='text-align:center; font-size: 20px; font-weight:bold; margin-bottom: 15px;'>-</div>", unsafe_allow_html=True)
    with c2: 
        # Label dinámico: Nombre del equipo
        gv = st.number_input(f"{row['visitante']}", value=val_v, min_value=0, key="m_gv")

    # 3. Sección de Evidencia
    has_l = row['url_foto_l'] and str(row['url_foto_l']) != "None"
    has_v = row['url_foto_v'] and str(row['url_foto_v']) != "None"

    if has_l or has_v:
        st.divider()
        st.markdown("##### 📷 Evidencia Disponible")
        
        if has_l and has_v:
            t1, t2 = st.tabs([f"{row['local'][:10]}...", f"{row['visitante'][:10]}..."])
            with t1: st.image(row['url_foto_l'], use_container_width=True)
            with t2: st.image(row['url_foto_v'], use_container_width=True)
        elif has_l:
            st.caption(f"De: {row['local']}")
            st.image(row['url_foto_l'], use_container_width=True)
        elif has_v:
            st.caption(f"De: {row['visitante']}")
            st.image(row['url_foto_v'], use_container_width=True)
    else:
        st.caption("ℹ️ Sin evidencia fotográfica.")

    st.write("") 
    
    # 4. Botón Guardar
    if st.button("💾 Guardar Resultado Oficial", type="primary", use_container_width=True):
        try:
            with conn.connect() as db:
                db.execute(text("""
                    UPDATE partidos 
                    SET goles_l=:l, goles_v=:v, estado='Finalizado', conflicto=False, metodo_registro='Manual Admin' 
                    WHERE id=:id
                """), {"l": gl, "v": gv, "id": row['id']})
                db.commit()
            
            st.toast("✅ Marcador actualizado")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")







        
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
        if c_salir.button("🔴 Cerrar Sesión Admin", key="btn_salir_admin", use_container_width=True):
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

                # --- CASO B: GESTIÓN DE PARTIDOS (TARJETAS IMAGEN + MODAL) ---
                else:
                    # 1. MENSAJE EXPLICATIVO GOL BOT (Actualizado)
                    mostrar_bot("""
                    <b>Gol Bot</b> procesa los resultados automáticamente. <br>
                    Tu trabajo es intervenir solo en los partidos marcados como <b>'En Revisión'</b> 
                    (reclamos o dudas de la IA) y confirmar el marcador final.
                    """)
                    
                    # Filtros
                    filtro_partidos = st.radio("Filtrar:", ["Todos", "Pendientes", "En Revisión"], horizontal=True, label_visibility="collapsed")
                    
                    # Query
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

                    if not df_p.empty:
                        # Filtro actualizado: "En Revisión" busca conflictos o estado 'Revision'
                        if filtro_partidos == "En Revisión": 
                            df_p = df_p[(df_p['conflicto'] == True) | (df_p['estado'] == 'Revision')]
                        elif filtro_partidos == "Pendientes": 
                            df_p = df_p[df_p['goles_l'].isna() | df_p['goles_v'].isna()]

                    if df_p.empty:
                        st.info("No hay partidos mpor revisar.")
                    else:
                        jornadas = sorted(df_p['jornada'].unique())
                        tabs_j = st.tabs([f"J{j}" for j in jornadas])
                        
                        for i, tab in enumerate(tabs_j):
                            with tab:
                                df_j = df_p[df_p['jornada'] == jornadas[i]]
                                
                                for _, row in df_j.iterrows():
                                    
                                    # 1. TEXTO MARCADOR
                                    if pd.notna(row['goles_l']) and pd.notna(row['goles_v']):
                                        txt_marcador = f"{int(row['goles_l'])} - {int(row['goles_v'])}"
                                    else:
                                        txt_marcador = "VS"
                                    
                                    # 2. COLOR BORDE (Rojo si hay revisión, sino color torneo)
                                    c_borde = t_color
                                    if row['conflicto'] or row['estado'] == 'Revision':
                                        c_borde = "#ff4b4b" # Rojo alerta
                                    
                                    # 3. GENERAR IMAGEN TARJETA
                                    img_card = generar_tarjeta_imagen(
                                        row['local'], row['visitante'],
                                        row['escudo_l'], row['escudo_v'],
                                        txt_marcador, c_borde
                                    )
                                    
                                    # MOSTRAR IMAGEN
                                    st.image(img_card, use_container_width=True)
                                    
                                    # 4. INFO Y BOTONES
                                    c_info, c_btn = st.columns([1.5, 1], vertical_alignment="center")
                                    
                                    with c_info:
                                        # BADGES (Etiquetas)
                                        info_badges = []
                                        
                                        # Cambio de terminología: Conflicto -> En Revisión
                                        if row['conflicto'] or row['estado'] == 'Revision': 
                                            info_badges.append("🔴 En Revisión")
                                        
                                        if row['url_foto_l'] or row['url_foto_v']: 
                                            info_badges.append("📷 Hay Fotos")
                                        
                                        # Eliminamos el badge "Listo" o "Finalizado" (Menos es más)
                                        
                                        if info_badges:
                                            st.caption(" | ".join(info_badges))
                                        else:
                                            # Si no hay nada especial y no se ha jugado
                                            if txt_marcador == "VS": st.caption("Por jugar")
                                            else: st.caption("") # Espacio vacío si ya acabó y está limpio

                                    with c_btn:
                                        # Texto botón cambia si requiere atención
                                        if row['conflicto'] or row['estado'] == 'Revision':
                                            label_btn = "⚠️ Resolver"
                                            tipo_btn = "primary"
                                        else:
                                            label_btn = "✏️ Editar"
                                            tipo_btn = "secondary"
                                        
                                        if st.button(label_btn, key=f"btn_m_{row['id']}", type=tipo_btn, use_container_width=True):
                                            modal_edicion_admin(row, id_torneo)
                                    
                                    st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)


            

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
            # SUB-TAB 3: CONFIGURACIÓN (CENTRO DE MANDO)
            # =========================================================
            with sub_tabs[2]:
                st.subheader("⚙️ Centro de Mando")

                # ---------------------------------------------------------
                # 1. CONTROL DE FASES (PRIORIDAD ALTA)
                # ---------------------------------------------------------
                st.markdown(f"##### 🚀 Estado Actual: `{t_fase.upper().replace('_', ' ')}`")
                
                # A. DIAGNÓSTICO
                estado_torneo = analizar_estado_torneo(id_torneo)
                
                # B. INTERFAZ DE AVANCE
                if estado_torneo['listo']:
                    # CASO VERDE: Todo listo
                    # Usamos un mensaje de éxito estándar para las buenas noticias
                    st.success(estado_torneo['mensaje'], icon="✅")
                    
                    label_accion = estado_torneo['accion_siguiente']
                    
                    if st.button(f"⏩ {label_accion}", type="primary", use_container_width=True):
                        st.session_state[f"conf_avance_{id_torneo}"] = True
                    
                    # C. ZONA DE CONFIRMACIÓN
                    if st.session_state.get(f"conf_avance_{id_torneo}"):
                        st.markdown("""
                        <div style='background-color: rgba(255, 215, 0, 0.15); padding: 15px; border-radius: 8px; border-left: 5px solid #FFD700; margin: 10px 0;'>
                            <h4 style='margin:0; color: #FFD700;'>⚠️ Atención, Presi</h4>
                            <p style='margin:5px 0 0 0; font-size:14px;'>
                                Estás a punto de cerrar la fase actual. <b>Gol Bot</b> calculará la tabla y generará los nuevos partidos.<br>
                                <b>Esta acción no se puede deshacer.</b>
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        col_si, col_no = st.columns(2)
                        
                        if col_si.button("✅ Sí, Ejecutar", key="btn_yes_adv", type="primary", use_container_width=True):
                            with st.spinner("🤖 Gol Bot procesando lógica del torneo..."):
                                exito, msg = ejecutar_avance_fase(id_torneo)
                                if exito:
                                    st.balloons()
                                    st.success(msg)
                                    del st.session_state[f"conf_avance_{id_torneo}"]
                                    time.sleep(3)
                                    st.rerun()
                                else:
                                    st.error(f"Error: {msg}")
                        
                        if col_no.button("❌ Cancelar", key="btn_no_adv", use_container_width=True):
                            del st.session_state[f"conf_avance_{id_torneo}"]
                            st.rerun()

                else:
                    # CASO NO LISTO: GOL BOT HABLA AQUÍ
                    # Tomamos el mensaje que viene de la función (ej: "Faltan 2 partidos") y lo dice el Bot
                    mostrar_bot(f"{estado_torneo['mensaje']} <br>No podemos avanzar hasta resolverlo.")
                    st.button("🚫 Avanzar Fase", disabled=True, use_container_width=True)

                st.divider()

                # ---------------------------------------------------------
                # 2. IDENTIDAD DEL TORNEO (PRIORIDAD MEDIA)
                # ---------------------------------------------------------
                st.markdown("##### 🎨 Identidad Visual")
                c_col1, c_col2 = st.columns([1, 2], vertical_alignment="bottom")
                new_color = c_col1.color_picker("Color Principal", value=t_color)
                if c_col2.button("Guardar Color", use_container_width=True):
                    with conn.connect() as db:
                        db.execute(text("UPDATE torneos SET color_primario = :c WHERE id = :id"), {"c": new_color, "id": id_torneo})
                        db.commit()
                    st.toast("Color actualizado")
                    time.sleep(1); st.rerun()

                st.divider()

                # ---------------------------------------------------------
                # 3. ZONA DE PELIGRO (CANCELAR TORNEO)
                # ---------------------------------------------------------
                st.markdown("##### 💀 Zona de Peligro")
                
                # Advertencia de GolBot antes de mostrar el botón
                mostrar_bot("Si decides <b>Cancelar el Torneo</b>, borraré todos los partidos, resultados y fotos. <br><b>Esta acción es irreversible.</b>")
                
                if st.button("🚨 Cancelar Torneo Definitivamente", type="secondary", use_container_width=True):
                     st.session_state.confirm_reset = True
                
                if st.session_state.get("confirm_reset"):
                    st.error("¿ESTÁS TOTALMENTE SEGURO?")
                    col_r1, col_r2 = st.columns(2)
                    
                    if col_r1.button("💥 SÍ, BORRAR TODO", type="primary", use_container_width=True):
                        with conn.connect() as db:
                            db.execute(text("DELETE FROM partidos WHERE id_torneo=:id"), {"id": id_torneo})
                            # Lo regresamos a inscripción (o podrías borrarlo de la tabla torneos si prefieres eliminarlo del todo)
                            db.execute(text("UPDATE torneos SET fase='inscripcion' WHERE id=:id"), {"id": id_torneo})
                            db.commit()
                        st.toast("Torneo reseteado")
                        del st.session_state.confirm_reset
                        time.sleep(1); st.rerun()
                        
                    if col_r2.button("Cancelar", key="cancel_reset", use_container_width=True):
                        del st.session_state.confirm_reset
                        st.rerun()



                

 # --- ESCENARIO B: DT (Director Técnico) ---
    elif rol_actual == "DT":
        
        # 0. BOTÓN SALIR
        c_vacio, c_salir = st.columns([6, 1])
        if c_salir.button("🔴 Cerrar sesión de Club", key="btn_salir_dt", use_container_width=True):
            st.session_state.clear()
            st.rerun()

        # Pestañas Principales
        tabs = st.tabs(["🏆 Torneo", "📅 Calendario", "👤 Mi Equipo"])

        # ------------------------------------------------------------
        # 1. TORNEO
        # ------------------------------------------------------------
        with tabs[0]:
             contenido_pestana_torneo(id_torneo, t_color)

        # ------------------------------------------------------------
        # 2. CALENDARIO Y GESTIÓN (DT)
        # ------------------------------------------------------------
        with tabs[1]:
            # CSS MÓVIL ESPECÍFICO
            st.markdown("""
                <style>
                [data-testid="column"] {
                    width: calc(50% - 5px) !important;
                    flex: 1 1 calc(50% - 5px) !important;
                    min-width: 0px !important;
                }
                .stButton button {
                    height: 40px !important;
                    padding: 0px !important;
                    font-size: 13px !important;
                    width: 100% !important;
                }
                </style>
            """, unsafe_allow_html=True)

            if t_fase == "inscripcion":
                mostrar_bot("El balón aún no rueda, Profe.")
            else:
                st.subheader(f"📅 Mi Calendario")
                
                try:
                    with conn.connect() as db:
                        # TRAEMOS AMBOS CAMPOS DE FOTO Y DATOS
                        q_mis = text("""
                            SELECT 
                                p.id, p.jornada, p.goles_l, p.goles_v, p.estado, p.metodo_registro,
                                p.local_id, p.visitante_id,
                                p.url_foto_l, p.url_foto_v,
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
                    
                    ultima_jornada_vista = -1

                    for _, p in mis.iterrows():
                        # --- DETERMINAR ROL ---
                        soy_local = (p['local_id'] == st.session_state.id_equipo)
                        columna_foto_target = "url_foto_l" if soy_local else "url_foto_v"

                        # --- RENDERIZADO VISUAL ---
                        if p['jornada'] != ultima_jornada_vista:
                            st.markdown(f"##### 📍 Jornada {p['jornada']}")
                            ultima_jornada_vista = p['jornada']

                        rival_pref = p['pref_v'] if soy_local else p['pref_l']
                        rival_cel = p['cel_v'] if soy_local else p['cel_l']
                        txt_score = f"{int(p['goles_l'])}-{int(p['goles_v'])}" if p['estado'] == 'Finalizado' else "VS"

                        # Tarjeta Generada
                        st.image(generar_tarjeta_imagen(
                            p['nombre_local'], p['nombre_visitante'],
                            p['escudo_l'], p['escudo_v'],
                            txt_score, t_color
                        ), use_container_width=True)

                        # --- BOTONES DE ACCIÓN ---
                        c1, c2 = st.columns(2)
                        
                        # Columna 1: Contacto
                        with c1:
                            if rival_pref and rival_cel:
                                num = f"{str(rival_pref).replace('+','')}{str(rival_cel).replace(' ','')}"
                                st.link_button("📞 Contactar", f"https://wa.me/{num}", use_container_width=True)
                            else:
                                st.button("🚫 Sin Tel.", key=f"dt_notel_{p['id']}", disabled=True, use_container_width=True)

                        # Columna 2: Estado / Carga
                        with c2:
                            if p['estado'] == 'Finalizado':
                                if p['metodo_registro'] == 'IA':
                                    if st.button("🚩 Reclamar", key=f"dt_rec_{p['id']}", use_container_width=True):
                                        with conn.connect() as db:
                                            db.execute(text("UPDATE partidos SET estado='Revision', conflicto=true WHERE id=:id"), {"id": p['id']})
                                            db.commit()
                                        st.rerun()
                                else:
                                    st.button("🔒 Oficial", key=f"dt_ofi_{p['id']}", disabled=True, use_container_width=True)
                            
                            elif p['estado'] == 'Revision':
                                st.button("⚠️ En Revisión", key=f"dt_rev_{p['id']}", disabled=True, use_container_width=True)
                            
                            else:
                                # Botón para subir foto
                                if st.button("📸 Subir", key=f"dt_btn_show_{p['id']}", type="primary", use_container_width=True):
                                    if st.session_state.get(f"show_up_{p['id']}"):
                                        del st.session_state[f"show_up_{p['id']}"]
                                    else:
                                        st.session_state[f"show_up_{p['id']}"] = True
                                    st.rerun()

                        # --- ÁREA DE CARGA (EXPANDIBLE) ---
                        if st.session_state.get(f"show_up_{p['id']}"):
                            with st.container(border=True):
                                st.markdown("##### 📸 Escanear Resultado")
                                foto = st.file_uploader("Sube la foto del marcador", type=['jpg','png','jpeg'], key=f"dt_file_{p['id']}")
                                
                                if foto:
                                    if st.button("🤖 Leer marcador", key=f"dt_go_{p['id']}", type="primary", use_container_width=True):
                                        with st.spinner("Gol Bot está analizando la jugada..."):
                                            
                                            # 1. ANÁLISIS IA
                                            res_ia, msg_ia = leer_marcador_ia(foto, p['nombre_local'], p['nombre_visitante'])
                                            
                                            # CASO A: ÉXITO ROTUNDO
                                            if res_ia:
                                                gl, gv = res_ia
                                                st.success(msg_ia)
                                                
                                                # 2. SUBIR FOTO
                                                url_foto = subir_foto_cloudinary(foto, p['id'])
                                                
                                                # 3. GUARDAR EN BD
                                                with conn.connect() as db:
                                                    query_update = text(f"""
                                                        UPDATE partidos 
                                                        SET goles_l=:gl, goles_v=:gv, estado='Finalizado', 
                                                            metodo_registro='IA', fecha_registro=CURRENT_TIMESTAMP,
                                                            {columna_foto_target}=:url
                                                        WHERE id=:id
                                                    """)
                                                    db.execute(query_update, {
                                                        "gl": gl, "gv": gv, "id": p['id'], 
                                                        "url": url_foto
                                                    })
                                                    db.commit()
                                                
                                                time.sleep(2)
                                                del st.session_state[f"show_up_{p['id']}"]
                                                st.rerun()
                                            
                                            # CASO B: FALLO DETECTADO
                                            else:
                                                st.error(msg_ia)
                                                st.session_state[f"error_ia_{p['id']}"] = True

                                # Modo Rescate (Si falló la IA)
                                if st.session_state.get(f"error_ia_{p['id']}"):
                                    st.divider()
                                    col_r1, col_r2 = st.columns(2)
                                    
                                    if col_r1.button("🔄 Reintentar", key=f"dt_retry_{p['id']}", use_container_width=True):
                                        del st.session_state[f"error_ia_{p['id']}"]
                                        st.rerun()
                                    
                                    if col_r2.button("📩 Enviar a Admin", key=f"dt_manual_{p['id']}", use_container_width=True):
                                        with st.spinner("Enviando evidencia al VAR..."):
                                            url_foto_fail = subir_foto_cloudinary(foto, f"{p['id']}_revision")
                                            
                                            with conn.connect() as db:
                                                query_manual = text(f"""
                                                    UPDATE partidos 
                                                    SET estado='Revision', conflicto=true, {columna_foto_target}=:url 
                                                    WHERE id=:id
                                                """)
                                                db.execute(query_manual, {"id": p['id'], "url": url_foto_fail})
                                                db.commit()
                                            
                                            st.info("Enviado a revisión manual con evidencia.")
                                            del st.session_state[f"show_up_{p['id']}"]
                                            del st.session_state[f"error_ia_{p['id']}"]
                                            time.sleep(1); st.rerun()

                        st.markdown("<br>", unsafe_allow_html=True)

                except Exception as e:
                    st.error(f"Error cargando calendario: {e}")

        # ------------------------------------------------------------
        # 3. MI EQUIPO (Sub-pestañas: Estadísticas y Edición)
        # ------------------------------------------------------------
        with tabs[2]:
            sub_tabs = st.tabs(["📊 Estadísticas", "✏️ Editar Equipo"])

            # --------------------------------------------------------
            # SUB-PESTAÑA 1: ESTADÍSTICAS (HISTORIA DEL CLUB)
            # --------------------------------------------------------
            with sub_tabs[0]:
                st.subheader("📊 Historia del Club")
                
                # CORRECCIÓN: Usamos directamente la sesión porque YA estamos logueados
                id_equipo = st.session_state.id_equipo

                try:
                    with conn.connect() as db:
                        # 1. Buscamos datos del equipo actual en este torneo
                        me_row = db.execute(text("SELECT nombre, pin_equipo, escudo FROM equipos_globales WHERE id=:id"), {"id": id_equipo}).fetchone()
                        
                        if me_row:
                            mi_nombre = me_row.nombre
                            mi_pin = me_row.pin_equipo
                            mi_escudo = me_row.escudo
                            
                            # 2. Consultamos la Tabla Histórica
                            historia = db.execute(text("""
                                SELECT torneos_jugados, partidos_jugados, titulos, goles_favor 
                                FROM historia_equipos_res 
                                WHERE nombre=:n AND pin=:p
                            """), {"n": mi_nombre, "p": mi_pin}).fetchone()

                            # A. CON HISTORIA
                            if historia:
                                mostrar_bot(f"¡Qué gusto verte de nuevo, <b>{mi_nombre}</b>! <br>Aquí reposa la gloria de tus campañas anteriores.")
                                st.markdown("<br>", unsafe_allow_html=True)
                                
                                with st.container(border=True):
                                    c_h1, c_h2 = st.columns([1, 3], vertical_alignment="center")
                                    with c_h1:
                                        img_show = mi_escudo if mi_escudo else "https://cdn-icons-png.flaticon.com/512/1165/1165187.png"
                                        st.image(img_show, use_container_width=True)
                                    with c_h2:
                                        st.markdown(f"### 🏛️ Legado: {historia.torneos_jugados} Torneos")
                                        st.markdown(f"**Partidos Históricos:** {historia.partidos_jugados} | **Goles:** {historia.goles_favor}")
                                        if historia.titulos > 0:
                                            st.caption(f"🏆 {historia.titulos} Títulos")
                                        else:
                                            st.caption("En busca de la primera estrella.")
                                st.info("Sigue compitiendo. Al finalizar este torneo, actualizaré tus números históricos aquí.")

                            # B. SIN HISTORIA
                            else:
                                st.markdown("""
                                <div style='text-align: center; padding: 20px;'>
                                    <h3 style='color: #888;'>🌑 Página en Blanco</h3>
                                </div>
                                """, unsafe_allow_html=True)
                                mostrar_bot(f"""
                                Veo que esta es la primera vez de <b>{mi_nombre}</b> en nuestros registros.
                                <br><br>
                                📜 <b>La historia no se compra, se escribe en la cancha.</b>
                                <br>
                                Juega este torneo, deja todo en el campo, y cuando termine, 
                                empezaremos a escribir la historia del club.
                                """)
                                
                        else:
                            st.error("No pude identificar los datos de tu equipo.")

                except Exception as e:
                    st.error(f"Error cargando historia: {e}")

            # --------------------------------------------------------
            # SUB-PESTAÑA 2: EDITAR EQUIPO
            # --------------------------------------------------------
            with sub_tabs[1]:
                id_eq = st.session_state.id_equipo
                
                # SNAPSHOT
                try:
                    with conn.connect() as db:
                        q_me = text("SELECT * FROM equipos_globales WHERE id = :id")
                        me = db.execute(q_me, {"id": id_eq}).fetchone()
                except Exception as e_load:
                    mostrar_bot(f"Error técnico cargando perfil: {e_load}")
                    st.stop()

                if me:
                    PIN_ANTERIOR = me.pin_equipo
                    ESCUDO_ANTERIOR = me.escudo
                    NOMBRE_ANTERIOR = me.nombre
                    
                    p1 = me.prefijo_dt1 if me.prefijo_dt1 else "+57"
                    n1 = me.celular_dt1 if me.celular_dt1 else ""
                    p2 = me.prefijo_dt2 if me.prefijo_dt2 else "+57"
                    n2 = me.celular_dt2 if me.celular_dt2 else ""
                    
                    tiene_dos = (len(str(n1)) > 5 and len(str(n2)) > 5)

                    with st.form("form_mi_equipo"):
                        
                        # A. CAPITÁN
                        sel_capitan = "Unico"
                        if tiene_dos:
                            st.markdown(f"#### ©️ Contacto Visible")
                            st.caption("¿A quién llamar en este torneo?")
                            lbl_opt1 = f"👑 DT Principal ({p1} {n1})"
                            lbl_opt2 = f"🤝 Co-DT ({p2} {n2})"
                            idx_activo = 1 if me.celular_capitan == n2 else 0
                            sel_capitan = st.radio("Responsable activo:", [lbl_opt1, lbl_opt2], index=idx_activo, horizontal=True)
                            st.divider()

                        # B. DATOS DEL CLUB
                        st.subheader("✏️ Datos del Club")
                        
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

                        # Listas y Cuerpo Técnico
                        paises = {
                            "Argentina": "+54", "Belice": "+501", "Bolivia": "+591", "Brasil": "+55",
                            "Chile": "+56", "Colombia": "+57", "Costa Rica": "+506", "Ecuador": "+593",
                            "EEUU/CANADA": "+1", "El Salvador": "+503", "Guatemala": "+502", 
                            "Guayana Fran": "+594", "Guyana": "+592", "Honduras": "+504", "México": "+52",
                            "Nicaragua": "+505", "Panamá": "+507", "Paraguay": "+595", "Perú": "+51",
                            "Surinam": "+597", "Uruguay": "+598", "Venezuela": "+58"
                        }
                        l_paises = [f"{k} ({paises[k]})" for k in sorted(paises.keys())]

                        with st.container(border=True):
                            st.markdown("**👤 Cuerpo Técnico**")
                            # DT1
                            c_dt1_p, c_dt1_n = st.columns([1.5, 2])
                            try: idx_p1 = sorted(paises.keys()).index(next((k for k, v in paises.items() if v == p1), "Colombia"))
                            except: idx_p1 = 0
                            s_p1 = c_dt1_p.selectbox("P-DT1", l_paises, index=idx_p1, label_visibility="collapsed")
                            val_p1 = s_p1.split('(')[-1].replace(')', '')
                            val_n1 = c_dt1_n.text_input("N-DT1", value=n1, label_visibility="collapsed")

                            # DT2
                            st.caption("Asistente (Opcional)")
                            c_dt2_p, c_dt2_n = st.columns([1.5, 2])
                            try: idx_p2 = sorted(paises.keys()).index(next((k for k, v in paises.items() if v == p2), "Colombia"))
                            except: idx_p2 = 0
                            s_p2 = c_dt2_p.selectbox("P-DT2", l_paises, index=idx_p2, label_visibility="collapsed")
                            val_p2 = s_p2.split('(')[-1].replace(')', '')
                            val_n2 = c_dt2_n.text_input("N-DT2", value=n2, label_visibility="collapsed")

                        st.write("")
                        
                        # C. VALIDACIÓN Y GUARDADO
                        if st.form_submit_button("💾 Guardar Cambios", use_container_width=True):
                            
                            if len(new_nom) < 3:
                                mostrar_bot("¡Epa Profe! El nombre del equipo es muy corto.")
                                st.stop()
                            if len(new_pin) < 4:
                                mostrar_bot("El PIN debe tener al menos 4 caracteres.")
                                st.stop()

                            try:
                                with conn.connect() as db:
                                    # Chequeo Nombre
                                    if new_nom != NOMBRE_ANTERIOR:
                                        res_name = db.execute(text("SELECT count(*) FROM equipos_globales WHERE nombre = :n AND id != :my_id"), 
                                                                {"n": new_nom, "my_id": id_eq}).scalar()
                                        if res_name > 0:
                                            mostrar_bot(f"✋ El nombre **'{new_nom}'** ya está en uso.")
                                            st.stop()

                                    # Chequeo PIN
                                    if new_pin != PIN_ANTERIOR:
                                        res_pin = db.execute(text("SELECT count(*) FROM equipos_globales WHERE pin_equipo = :p AND id != :my_id"), 
                                                            {"p": new_pin, "my_id": id_eq}).scalar()
                                        if res_pin > 0:
                                            mostrar_bot("⚠️ Ese PIN ya está en uso. Elige otro.")
                                            st.stop()

                            except Exception as e_val:
                                mostrar_bot(f"Error verificando disponibilidad: {e_val}")
                                st.stop()

                            # Preparar datos finales
                            url_final = ESCUDO_ANTERIOR
                            if new_escudo:
                                url_final = procesar_y_subir_escudo(new_escudo, new_nom, id_torneo)
                            
                            if tiene_dos and sel_capitan and ("Co-DT" in sel_capitan) and len(val_n2) > 5:
                                pub_cel = val_n2; pub_pref = val_p2
                            else:
                                pub_cel = val_n1; pub_pref = val_p1

                            # Transacción DB
                            try:
                                with conn.connect() as db:
                                    transaccion = db.begin()
                                    try:
                                        # 1. Update Global
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
                                        
                                        # 2. Propagación PIN
                                        if PIN_ANTERIOR:
                                            db.execute(text("""
                                                UPDATE equipos_globales 
                                                SET nombre=:n, escudo=:e, pin_equipo=:new_pin
                                                WHERE pin_equipo=:old_pin AND id != :id_eq
                                            """), {
                                                "n": new_nom, "e": url_final, "new_pin": new_pin, 
                                                "old_pin": PIN_ANTERIOR, "id_eq": id_eq
                                            })
                                        
                                        # 3. Update Capitán
                                        db.execute(text("""
                                            UPDATE equipos_globales 
                                            SET celular_capitan=:cp, prefijo=:pp
                                            WHERE id=:id
                                        """), {"cp": pub_cel, "pp": pub_pref, "id": id_eq})
                                        
                                        transaccion.commit()
                                        st.session_state.nombre_equipo = new_nom
                                        
                                        mostrar_bot("✅ ¡Datos actualizados correctamente, Profe!")
                                        time.sleep(2)
                                        st.rerun()

                                    except Exception as e_sql:
                                        transaccion.rollback()
                                        mostrar_bot(f"❌ Error guardando en base de datos: {e_sql}")

                            except Exception as e_main:
                                mostrar_bot(f"❌ Error de conexión: {e_main}")
                    


                


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






















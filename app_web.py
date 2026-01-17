import streamlit as st
#import sqlite3
import pandas as pd
import random
import easyocr
import cloudinary
import cloudinary.uploader
import io
import numpy as np
from PIL import Image
import cv2
import re  # Para expresiones regulares (encontrar números difíciles)
from thefuzz import fuzz # Para comparación flexible de nombres
import json
import os
import streamlit as st
from sqlalchemy.engine import make_url
from sqlalchemy import text
from contextlib import contextmanager
import streamlit as st
import time


#PROVISIONAL PARA HACER PRUEBAS DE DESARROLLO
# Nombre del archivo donde se guardará todo
DB_FILE = "data_torneo.json"

# --- CONFIGURACIÓN DE BASE DE DATOS (Supabase) ---

def get_db_connection():
    """Establece la conexión con la base de datos PostgreSQL de Supabase"""
    return st.connection("postgresql", type="sql")

def obtener_fase_actual():
    """Consulta la fase actual del torneo en la base de datos"""
    conn = get_db_connection()
    try:
        # ttl=0 para asegurar que siempre lea el dato más reciente de la nube
        df = conn.query("SELECT valor FROM config WHERE clave = 'fase_actual'", ttl=0)
        if not df.empty:
            return df.iloc[0]['valor']
    except Exception:
        pass
    return "inscripcion" # Valor por defecto si hay error



# 1. CONFIGURACIÓN PRINCIPAL DE SITIO
st.set_page_config(page_title="Gol-Gana Pro", layout="centered", initial_sidebar_state="collapsed")

# 2. Inyectar el Meta Tag de "color-scheme"
st.markdown('<meta name="color-scheme" content="light">', unsafe_allow_html=True)


# --- CONFIGURACIÓN DE CLOUDINARY (Usando Secrets) ---
# Esto lee los datos que acabas de guardar en el panel de Streamlit
cloudinary.config( 
  cloud_name = st.secrets["cloudinary"]["cloud_name"], 
  api_key = st.secrets["cloudinary"]["api_key"], 
  api_secret = st.secrets["cloudinary"]["api_secret"],
  secure = True
)




# --- 1. CONFIGURACIÓN Y TEMA FIJO CLARO ---
DB_NAME = "gol_gana.db"
ADMIN_PIN = "2025" 






#### TEMAS Y COLORES ####

st.markdown("""
    <style>
    /* 1. RESET GLOBAL: Fondo blanco y texto negro absoluto */
    html, body, .stApp, [data-testid="stAppViewContainer"], .st-emotion-cache-1h9usn1 {
        background-color: white !important;
        color: black !important;
    }

    /* 2. FORZAR LUZ EN MÓVILES (Incluso si el sistema está en Dark Mode) */
    @media (prefers-color-scheme: dark) {
        .stApp, [data-testid="stAppViewContainer"] {
            background-color: white !important;
            color: black !important;
        }
    }

    /* 3. TEXTO: Blindaje para iPhone y Android */
    h1, h2, h3, p, span, label, div, b, .stMarkdown, [data-testid="stWidgetLabel"] p {
        color: black !important;
        -webkit-text-fill-color: black !important;
    }

    /* 4. BOTONES: Fix para botón "Siguiente", "Aprobar" y estándar */
    div.stButton > button, 
    div.stFormSubmitButton > button, 
    [data-testid="baseButton-secondary"], 
    [data-testid="baseButton-primary"] {
        background-color: #f0f2f6 !important;
        color: #31333f !important;
        border: 1px solid #dcdfe4 !important;
        border-radius: 8px !important;
        width: 100%;
        height: 3em;
        font-weight: bold !important;
        -webkit-text-fill-color: #31333f !important;
    }

    div.stButton > button:active, div.stFormSubmitButton > button:active {
        background-color: #e0e2e6 !important;
        border-color: #ff4b4b !important;
    }

    /* 5. INPUTS Y CAJA DEL SELECTBOX */
    input[type="text"], input[type="password"], textarea, div[data-baseweb="select"] > div {
        background-color: #ffffff !important;
        color: black !important;
        border: 1px solid #ccc !important;
        -webkit-text-fill-color: black !important;
    }

    /* 6. FIX DEFINITIVO PARA EL DESPLEGABLE (MENU FLOTANTE) */
    /* Este bloque ataca la capa que flota cuando abres el país/prefijo */
    div[data-baseweb="popover"], 
    div[data-baseweb="menu"], 
    ul[role="listbox"] {
        background-color: white !important;
        border: 1px solid #ddd !important;
    }

    li[role="option"], 
    li[role="option"] div, 
    li[role="option"] span {
        background-color: white !important;
        color: black !important;
        -webkit-text-fill-color: black !important;
    }

    /* Color cuando pasas el dedo o seleccionas una opción */
    li[role="option"]:hover, 
    li[role="option"]:active, 
    li[role="option"][aria-selected="true"] {
        background-color: #f0f2f6 !important;
        color: #ff4b4b !important;
    }

    /* El ícono de la flechita del selectbox */
    div[data-baseweb="select"] svg {
        fill: black !important;
    }

    /* 7. EXPANDERS */
    [data-testid="stExpander"] {
        background-color: white !important;
        border: 1px solid #eee !important;
    }

    /* 8. TABLAS Y CAJAS DE PARTIDO */
    .mobile-table { 
        width: 100%; border-collapse: collapse; font-size: 12px; 
        background-color: white !important; color: black !important;
    }
    .mobile-table th { background: #f0f2f6 !important; color: black !important; padding: 8px; }
    .mobile-table td { padding: 8px; border-bottom: 1px solid #eee; color: black !important; }

    .match-box { 
        border: 1px solid #eee; padding: 15px; border-radius: 10px; 
        margin-bottom: 15px; background: white !important; color: black !important;
    }

    .wa-btn { 
        display: inline-block; background-color: #25D366; color: white !important; 
        padding: 10px; border-radius: 8px; text-decoration: none; 
        font-weight: bold; width: 100%; text-align: center;
    }

    * { -webkit-tap-highlight-color: transparent !important; }
    </style>
""", unsafe_allow_html=True)



############# FIN COLORES


# --- INICIALIZACIÓN DE DATOS ---

if "datos_cargados" not in st.session_state:
    st.session_state["datos_cargados"] = True
    # Inicializamos listas vacías solo si el resto de tu código las requiere para arrancar
    if "equipos" not in st.session_state: st.session_state["equipos"] = []
    if "partidos" not in st.session_state: st.session_state["partidos"] = []

# Conexión profesional a Supabase (Postgres)
def get_db_connection():
    # Streamlit maneja el pool de conexiones automáticamente aquí
    return st.connection("postgresql", type="sql")

def inicializar_db():
    conn = get_db_connection()
    # Usamos conn.session para ejecutar comandos de creación (DDL)
    with conn.session as s:
        # 1. Tabla Equipos
        s.execute(text('''CREATE TABLE IF NOT EXISTS equipos (
            nombre TEXT PRIMARY KEY, 
            celular TEXT, 
            prefijo TEXT, 
            pin TEXT, 
            escudo TEXT,
            estado TEXT DEFAULT 'pendiente'
        )'''))

        # 2. Tabla Partidos (SERIAL es el equivalente a AUTOINCREMENT en Postgres)
        s.execute(text('''CREATE TABLE IF NOT EXISTS partidos (
            id SERIAL PRIMARY KEY, 
            local TEXT, 
            visitante TEXT, 
            goles_l INTEGER DEFAULT NULL, 
            goles_v INTEGER DEFAULT NULL, 
            jornada INTEGER, 
            estado TEXT DEFAULT 'programado',
            url_foto_l TEXT, 
            url_foto_v TEXT, 
            ia_goles_l INTEGER, 
            ia_goles_v INTEGER, 
            conflicto INTEGER DEFAULT 0
        )'''))

        # 3. Tabla Config (Postgres usa ON CONFLICT en lugar de INSERT OR IGNORE)
        s.execute(text('''CREATE TABLE IF NOT EXISTS config (
            llave TEXT PRIMARY KEY, 
            valor TEXT
        )'''))
        
        s.execute(text("""
            INSERT INTO config (llave, valor) 
            VALUES ('fase', 'inscripcion') 
            ON CONFLICT (llave) DO NOTHING
        """))
        s.commit()

def migrar_db():
    conn = get_db_connection()
    with conn.session as s:
        # Columnas a verificar/añadir
        columnas = [
            ("url_foto_l", "TEXT"),
            ("url_foto_v", "TEXT"),
            ("ia_goles_l", "INTEGER"),
            ("ia_goles_v", "INTEGER"),
            ("conflicto", "INTEGER DEFAULT 0"),
            ("escudo", "TEXT")
        ]
        
        for nombre_col, tipo in columnas:
            try:
                # Intentamos añadir la columna. Si ya existe, Postgres lanzará un error que capturamos.
                if nombre_col == "escudo":
                    s.execute(text(f"ALTER TABLE equipos ADD COLUMN {nombre_col} {tipo}"))
                else:
                    s.execute(text(f"ALTER TABLE partidos ADD COLUMN {nombre_col} {tipo}"))
                s.commit()
            except Exception:
                # Si la columna ya existe, la sesión falla, por lo que hacemos rollback para poder seguir
                s.rollback()
                continue

# --- EJECUCIÓN ---
def inicializar_db():
    conn = get_db_connection()
    # Usar el motor directamente para evitar problemas de sesión
    with conn.engine.connect() as s:
        try:
            s.execute(text("""
                CREATE TABLE IF NOT EXISTS equipos (
                    nombre TEXT PRIMARY KEY,
                    pin TEXT NOT NULL,
                    celular TEXT,
                    prefijo TEXT,
                    escudo TEXT,
                    puntos INTEGER DEFAULT 0,
                    pj INTEGER DEFAULT 0,
                    pg INTEGER DEFAULT 0,
                    pe INTEGER DEFAULT 0,
                    pp INTEGER DEFAULT 0,
                    gf INTEGER DEFAULT 0,
                    gc INTEGER DEFAULT 0,
                    dg INTEGER DEFAULT 0,
                    estado TEXT DEFAULT 'pendiente'
                );
            """))
            s.commit() # Importante confirmar
        except Exception as e:
            st.warning(f"Aviso en DB: {e}")
migrar_db()      # 2. Asegura que la estructura esté al día





##### ALGORITMO IA #####
##NORMALIZAR Y SUBIR ESCUDO##


def procesar_y_subir_escudo(archivo_imagen, nombre_equipo):
    try:
        # Subir a Cloudinary pidiendo eliminación de fondo (IA)
        # 'background_removal': 'cloudinary_ai' hace la magia
        resultado = cloudinary.uploader.upload(
            archivo_imagen,
            folder="escudos_torneo",
            public_id=f"escudo_{nombre_equipo.replace(' ', '_')}",
            background_removal="cloudinary_ai", 
            format="png" # Forzamos PNG para mantener la transparencia
        )
        # Retornamos la URL de la imagen ya procesada
        return resultado['secure_url']
    except Exception as e:
        st.error(f"Error procesando imagen con IA: {e}")
        # Si falla la IA, intentamos subirla normal sin procesar
        resultado_fallback = cloudinary.uploader.upload(archivo_imagen)
        return resultado_fallback['secure_url']




##LEER MARCADOR
def limpiar_nombre(nombre):
    """Elimina sufijos comunes para quedarse con la raíz del nombre."""
    palabras_basura = ["FC", "MX", "CLUB", "REAL", "DEPORTIVO", "10", "A", "B"]
    nombre = nombre.upper()
    for palabra in palabras_basura:
        nombre = nombre.replace(palabra, "")
    return nombre.strip().split()

@st.cache_resource
def obtener_lector():
    return easyocr.Reader(['es', 'en'], gpu=False)

def leer_marcador_ia(imagen_bytes, local_real, visitante_real):
    try:
        datos_puros = imagen_bytes.getvalue()  
        reader = obtener_lector()
        file_bytes = np.asarray(bytearray(datos_puros), dtype=np.uint8) 
        # --- PASO 1: MEJORA DE IMAGEN PROFESIONAL ---
        file_bytes = np.asarray(bytearray(imagen_bytes.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        
        # Convertir a escala de grises
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Aumentar contraste y binarizar (hacer que lo gris sea negro y lo blanco brille)
        # Esto es clave para leer pantallas
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
        
        # --- PASO 2: OCR ---
        # Leemos sobre la imagen procesada (thresh)
        resultados = reader.readtext(thresh, detail=1) # detail=1 nos da la posición
        
        textos_detectados = [res[1].upper() for res in resultados]
        toda_la_data = " ".join(textos_detectados)
        
        # --- PASO 3: VALIDACIÓN FLEXIBLE DE EQUIPOS ---
        keywords_l = limpiar_nombre(local_real)
        keywords_v = limpiar_nombre(visitante_real)
        
        # Buscamos si AL MENOS UNA palabra clave de cada equipo aparece
        encontrado_l = any(fuzz.partial_ratio(kw, toda_la_data) > 85 for kw in keywords_l)
        encontrado_v = any(fuzz.partial_ratio(kw, toda_la_data) > 85 for kw in keywords_v)

        # Si no encuentra nombres, intentamos una segunda pasada con el texto original
        if not (encontrado_l or encontrado_v):
            # A veces el pre-procesamiento es muy agresivo, probamos con la original
            resultados_raw = reader.readtext(img, detail=0)
            toda_la_data = " ".join(resultados_raw).upper()
            encontrado_l = any(fuzz.partial_ratio(kw, toda_la_data) > 85 for kw in keywords_l)
            encontrado_v = any(fuzz.partial_ratio(kw, toda_la_data) > 85 for kw in keywords_v)

        if not encontrado_l and not encontrado_v:
             return None, f"⚠️ No identifico a {local_real} o {visitante_real}. Asegúrate de que el marcador sea legible."

        # --- PASO 4: EXTRACCIÓN DE GOLES ---
        # Buscamos patrones tipo "2-0", "2 - 0", "2 0"
        patron_marcador = re.findall(r'(\d+)\s*[-|]\s*(\d+)', toda_la_data)
        
        if patron_marcador:
            gl, gv = patron_marcador[0]
            return (int(gl), int(gv)), "OK"
        
        # Si no hay guion, buscamos números sueltos pero filtramos el "90" del tiempo
        numeros = [int(n) for n in re.findall(r'\d+', toda_la_data) if int(n) < 20]
        if len(numeros) >= 2:
            return (numeros[0], numeros[1]), "OK"

        return None, "🚫 No detecto el puntaje (ej: 2-0). Limpia el lente o evita reflejos."

    except Exception as e:
        return None, f"Error en el motor de visión: {str(e)}"

#####FIN IA
# --- 2. LÓGICA DE JORNADAS ---
def generar_calendario():
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT nombre FROM equipos WHERE estado = 'aprobado'")
        equipos = [row[0] for row in cur.fetchall()]
        while len(equipos) < 32:
            nombre_wo = f"(WO) {len(equipos)+1}"
            conn.execute("INSERT OR IGNORE INTO equipos (nombre, estado) VALUES (?, 'aprobado')", (nombre_wo,))
            equipos.append(nombre_wo)
        random.shuffle(equipos)
        n = len(equipos)
        indices = list(range(n))
        for jor in range(1, 4):
            for i in range(n // 2):
                loc = equipos[indices[i]]
                vis = equipos[indices[n - 1 - i]]
                conn.execute("INSERT INTO partidos (local, visitante, jornada) VALUES (?, ?, ?)", (loc, vis, jor))
            indices = [indices[0]] + [indices[-1]] + indices[1:-1]
        conn.execute("UPDATE config SET valor = 'clasificacion' WHERE llave = 'fase'")
        conn.commit()

# --- 3. NAVEGACIÓN ---
if "reg_estado" not in st.session_state: st.session_state.reg_estado = "formulario"
if "pin_usuario" not in st.session_state: st.session_state.pin_usuario = ""

####################PORTADA EN PRUEBA

# --- CONSTANTES DE DISEÑO ---

URL_PORTADA = "https://res.cloudinary.com/dlvczeqlp/image/upload/v1768595248/PORTADA_TEMP_cok7nv.png" 

# --- ESTILO CSS INYECTADO ---
st.markdown(f"""
    <style>
    /* Eliminamos el espacio blanco superior que Streamlit pone por defecto */
    .stAppHeader {{
        display: none;
    }}
    .block-container {{
        padding-top: 0rem !important;
    }}

    .main-banner {{
        width: 100%;
        height: 200px;
        background-image: linear-gradient(rgba(0,0,0,0.3), rgba(0,0,0,0.3)), url("{URL_PORTADA}");
        background-size: cover;
        background-position: center;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 25px;
        border-bottom: 5px solid #FFD700;
    }}

    .banner-title {{
        color: white;
        font-family: 'Impact', sans-serif;
        font-size: 3.5rem;
        text-shadow: 3px 3px 15px rgba(0,0,0,0.9);
        letter-spacing: 3px;
    }}
    </style>

    <div class="main-banner">
        <h1 class="banner-title"></h1>
    </div>
""", unsafe_allow_html=True)





######FIN PRUEBA


# --- NAVEGACIÓN (Botones originales) ---
c_nav1, c_nav2 = st.columns(2)
with c_nav1:
    if st.button("🔙 Inicio"):
        st.session_state.reg_estado = "formulario"
        st.session_state.pin_usuario = ""
        st.rerun()
#with c_nav2:
 #   if st.button("🔄 Refrescar"): 
  #      st.rerun()



# --- CAMPO DE PIN Y BOTÓN DE ENTRAR ---
pin_input = st.text_input("🔑 PIN de Acceso", value=st.session_state.get("pin_usuario", ""), type="password")
btn_entrar = st.button("🔓 Entrar", use_container_width=True)

# Actualizamos el estado con lo que se escriba
st.session_state.pin_usuario = pin_input

# Conexión a Supabase
conn = get_db_connection()

# Obtener fase actual (ttl=0 para que sea tiempo real)
df_fase = conn.query("SELECT valor FROM config WHERE clave = 'fase'", ttl=0)
fase_actual = df_fase.iloc[0]['valor'] if not df_fase.empty else "inscripcion"

rol = "espectador"
equipo_usuario = None

# --- LÓGICA DE VALIDACIÓN (Solo al dar click en Entrar) ---
if btn_entrar:
    if st.session_state.pin_usuario == ADMIN_PIN:
        rol = "admin"
        st.rerun()
    elif st.session_state.pin_usuario:
        # Consulta parametrizada en Postgres
        df_equipo = conn.query(
            "SELECT nombre FROM equipos WHERE pin = :p AND estado = 'aprobado'",
            params={"p": st.session_state.pin_usuario},
            ttl=0
        )
        
        if not df_equipo.empty:
            rol = "dt"
            equipo_usuario = df_equipo.iloc[0]['nombre']
            st.rerun()
        else:
            # Aviso visual de error
            st.markdown("""
                <div style="position: fixed; top: 40px; left: 50%; transform: translateX(-50%);
                            background-color: white; color: black; padding: 12px 24px;
                            border-radius: 8px; border: 2px solid #ff4b4b;
                            box-shadow: 0 4px 12px rgba(0,0,0,0.3); z-index: 9999;
                            font-weight: bold;">
                    ⚠️ PIN no registrado o no aprobado
                </div>
            """, unsafe_allow_html=True)
            
            # Limpieza y reinicio
            st.session_state.pin_usuario = ""
            st.session_state.reg_estado = "formulario"
            time.sleep(1.5) 
            st.rerun()

# --- MANTENER LA SESIÓN ACTIVA ---
if st.session_state.pin_usuario:
    if st.session_state.pin_usuario == ADMIN_PIN:
        rol = "admin"
    else:
        df_session = conn.query(
            "SELECT nombre FROM equipos WHERE pin = :p AND estado = 'aprobado'",
            params={"p": st.session_state.pin_usuario},
            ttl=0
        )
        if not df_session.empty:
            rol = "dt"
            equipo_usuario = df_session.iloc[0]['nombre']




# --- DEFINICIÓN DINÁMICA DE PESTAÑAS ---
# 'fase_actual' ya viene de la consulta a Supabase que hicimos en el bloque anterior
if fase_actual == "inscripcion":
    titulos = ["📊 Posiciones", "📝 Inscripción", "⚙️ Gestión"]
else:
    titulos = ["📊 Posiciones", "📅 Partidos", "⚙️ Gestión"]

tabs = st.tabs(titulos)
conn = get_db_connection()

# --- PESTAÑA 0: POSICIONES (Siempre igual) ---
with tabs[0]:
    st.subheader("🏆 Tabla de Clasificación")
    
    # Consulta a Supabase para obtener equipos aprobados
    df_posiciones = conn.query(
        "SELECT nombre, escudo, estado FROM equipos WHERE estado = 'aprobado'", 
        ttl=0
    )
    
    if df_posiciones.empty:
        st.info("Esperando a que se aprueben los primeros equipos para generar la tabla.")
    else:
        # Aquí irá tu lógica de cálculo de puntos (PG, PE, PP, etc.)
        st.dataframe(df_posiciones, use_container_width=True)

# --- PESTAÑA 1: INSCRIPCIÓN O PARTIDOS (Dinámica) ---
with tabs[1]:
    if fase_actual == "inscripcion":
        st.subheader("📝 Registro de Equipos")
        # Aquí se insertará el bloque del Formulario de Inscripción que usa s.commit()
        
        st.divider()
        st.markdown("### 📋 Equipos Inscritos")
        # Mostramos todos los equipos (pendientes y aprobados) desde Supabase
        df_inscritos = conn.query("SELECT nombre, estado FROM equipos", ttl=0)
        if not df_inscritos.empty:
            st.table(df_inscritos)
    else:
        st.subheader("📅 Calendario de Juegos")
        # Aquí se insertará el bloque de Partidos/Jornadas con diseño de tarjetas
        df_partidos = conn.query("SELECT * FROM partidos ORDER BY jornada ASC", ttl=0)
        if df_partidos.empty:
            st.warning("El administrador aún no ha generado el calendario.")

# --- PESTAÑA 2: GESTIÓN (ADMIN O DT) ---
with tabs[2]:
    if rol == "admin":
        st.header("👑 Panel de Administración")
        # Aquí pegaremos el bloque de aprobación de equipos y control de fase
        
    elif rol == "dt":
        st.header(f"⚽ Gestión: {equipo_usuario}")
        if fase_actual == "inscripcion":
            st.info(f"👋 ¡Hola DT de **{equipo_usuario}**! Tu equipo ya está aprobado. El torneo aún no comienza, espera a que el administrador genere el calendario.")
        else:
            st.success(f"✅ Torneo en curso para **{equipo_usuario}**. Aquí podrás reportar tus marcadores.")
            # Aquí irá el formulario de reporte de resultados para el DT
            
    else:
        st.markdown("### 🔒 Acceso Restringido")
        st.info("Esta sección es solo para **Administradores** o **Directores Técnicos** registrados.")
        st.write("Por favor, ingresa tu PIN en la parte superior para acceder.")




# --- TAB: CLASIFICACIÓN (Versión Supabase / Postgres) ---
with tabs[0]:
    # 1. Obtenemos la conexión establecida arriba
    conn = get_db_connection()
    
    # 2. Traemos equipos aprobados (usamos ttl=0 para datos frescos)
    df_eq = conn.query("SELECT nombre, escudo FROM equipos WHERE estado = 'aprobado'", ttl=0)
    
    if df_eq.empty: 
        st.info("No hay equipos aprobados todavía.")
    else:
        # Mapeo de escudos para acceso rápido
        mapa_escudos = dict(zip(df_eq['nombre'], df_eq['escudo']))
        
        # Inicializamos estadísticas
        stats = {e: {'PJ':0, 'PTS':0, 'GF':0, 'GC':0} for e in df_eq['nombre']}
        
        # 3. Traemos partidos jugados (con goles registrados)
        df_p = conn.query("SELECT local, visitante, goles_l, goles_v FROM partidos WHERE goles_l IS NOT NULL", ttl=0)
        
        # Procesamos resultados para la tabla
        if not df_p.empty:
            for _, f in df_p.iterrows():
                l, v = f['local'], f['visitante']
                # Convertimos a int por seguridad
                gl, gv = int(f['goles_l']), int(f['goles_v'])
                
                if l in stats and v in stats:
                    stats[l]['PJ'] += 1
                    stats[v]['PJ'] += 1
                    stats[l]['GF'] += gl
                    stats[l]['GC'] += gv
                    stats[v]['GF'] += gv
                    stats[v]['GC'] += gl
                    
                    if gl > gv: stats[l]['PTS'] += 3
                    elif gv > gl: stats[v]['PTS'] += 3
                    else:
                        stats[l]['PTS'] += 1
                        stats[v]['PTS'] += 1
        
        # Convertimos diccionario a DataFrame para ordenar
        df_f = pd.DataFrame.from_dict(stats, orient='index').reset_index()
        df_f.columns = ['EQ', 'PJ', 'PTS', 'GF', 'GC']
        df_f['DG'] = df_f['GF'] - df_f['GC']
        
        # Ordenamos por Puntos, luego Diferencia de Goles, luego Goles a Favor
        df_f = df_f.sort_values(by=['PTS', 'DG', 'GF'], ascending=False).reset_index(drop=True)
        df_f.insert(0, 'POS', range(1, len(df_f) + 1))

        # --- RENDERIZADO HTML (Mantenemos tu diseño original) ---
        # CSS para asegurar que no se rompa en móvil
        st.markdown("""
            <style>
            .mobile-table { width: 100%; border-collapse: collapse; font-size: 14px; }
            .mobile-table th { background-color: #f0f2f6; padding: 8px; text-align: center; }
            .mobile-table td { padding: 8px; border-bottom: 1px solid #ddd; text-align: center; }
            .team-cell { text-align: left !important; display: flex; align-items: center; }
            </style>
        """, unsafe_allow_html=True)

        html = '<table class="mobile-table"><thead><tr><th>POS</th><th style="text-align:left">EQ</th><th>PTS</th><th>PJ</th><th>DG</th></tr></thead><tbody>'
        
        for _, r in df_f.iterrows():
            url = mapa_escudos.get(r['EQ'])
            
            if url:
                prefijo_img = f'<img src="{url}" style="width:22px; height:22px; object-fit:contain; margin-right:8px;">'
            else:
                prefijo_img = '<span style="margin-right:8px;">🛡️</span>'
            
            html += f"""
                <tr>
                    <td>{r['POS']}</td>
                    <td class='team-cell'>{prefijo_img} {r['EQ']}</td>
                    <td><b>{r['PTS']}</b></td>
                    <td>{r['PJ']}</td>
                    <td>{r['DG']}</td>
                </tr>
            """
        
        st.markdown(html + "</tbody></table>", unsafe_allow_html=True)
            


            


# --- TAB: REGISTRO (Versión Supabase / Postgres) ---
if fase_actual == "inscripcion":
    with tabs[1]:
        if st.session_state.get("reg_estado") == "exito":
            st.success("✅ ¡Inscripción recibida!")
            if st.button("Nuevo Registro"): 
                st.session_state.reg_estado = "formulario"
                st.rerun()
        
        elif st.session_state.get("reg_estado") == "confirmar":
            d = st.session_state.datos_temp
            st.warning("⚠️ **Confirma tus datos:**")
            
            col_info, col_img = st.columns([2, 1])
            with col_info:
                st.write(f"**Equipo:** {d['n']}")
                st.write(f"**WA:** {d['pref']} {d['wa']}")
                st.write(f"**PIN:** {d['pin']}")
            
            with col_img:
                if d['escudo_obj']:
                    st.image(d['escudo_obj'], width=100)
                else:
                    st.write("🛡️ Sin escudo")

            c1, c2 = st.columns(2)
            if c1.button("✅ Confirmar"):
                url_temporal = None
                if d['escudo_obj']:
                    with st.spinner("Subiendo a Cloudinary..."):
                        try:
                            res = cloudinary.uploader.upload(d['escudo_obj'], folder="escudos_pendientes")
                            url_temporal = res['secure_url']
                        except Exception as e:
                            st.error(f"Error en Cloudinary: {e}")
                
                # INSERCIÓN EN SUPABASE
                conn = get_db_connection()
                try:
                    with conn.session as s:
                        s.execute(text("""
                            INSERT INTO equipos (nombre, celular, prefijo, pin, escudo, estado) 
                            VALUES (:n, :c, :pre, :p, :e, 'pendiente')
                        """), {
                            "n": d['n'], 
                            "c": d['wa'], 
                            "pre": d['pref'], 
                            "p": d['pin'], 
                            "e": url_temporal
                        })
                        s.commit()
                    st.session_state.reg_estado = "exito"
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar en base de datos: {e}")

            if c2.button("✏️ Editar"): 
                st.session_state.reg_estado = "formulario"
                st.rerun()
        
        else:
            # --- CSS REFINADO (Se mantiene igual) ---
            st.markdown("""
                <style>
                [data-testid="stFileUploader"] section { padding: 0; background-color: transparent !important; }
                [data-testid="stFileUploader"] section > div:first-child { display: none; }
                [data-testid="stFileUploader"] button[data-testid="baseButton-secondary"] { 
                    width: 100%; background-color: white !important; color: black !important; 
                    border: 2px solid #FFD700 !important; padding: 10px; border-radius: 8px; font-weight: bold;
                }
                [data-testid="stFileUploaderFileData"] button { width: auto !important; border: none !important; }
                [data-testid="stFileUploader"] button[data-testid="baseButton-secondary"]::before { 
                    content: "🛡️ SELECCIONAR ESCUDO"; 
                }
                [data-testid="stFileUploader"] button div { display: none; }
                [data-testid="stFileUploader"] small { display: none; }
                [data-testid="stFileUploaderFileName"], [data-testid="stFileUploaderFileData"] p {
                    color: black !important;
                }
                </style>
            """, unsafe_allow_html=True)

            with st.form("reg_preventivo"):
                nom = st.text_input("Nombre Equipo").strip()
                paises = {"Colombia": "+57", "EEUU": "+1", "México": "+52", "Ecuador": "+593", "Panamá": "+507"}
                pais_sel = st.selectbox("País", [f"{p} ({pref})" for p, pref in paises.items()])
                tel = st.text_input("WhatsApp").strip()
                pin_r = st.text_input("PIN (4 dígitos)", max_chars=4, type="password").strip()
                
                st.markdown("**🛡️ Sube el escudo de tu equipo** (Opcional)")
                archivo_escudo = st.file_uploader("", type=['png', 'jpg', 'jpeg'], label_visibility="collapsed")
                
                if st.form_submit_button("Siguiente", use_container_width=True):
                    if not nom or not tel or len(pin_r) < 4: 
                        st.error("Datos incompletos.")
                    else:
                        # VALIDACIÓN DE DUPLICADOS EN SUPABASE
                        conn = get_db_connection()
                        df_check = conn.query(
                            text("SELECT 1 FROM equipos WHERE nombre = :n OR celular = :c"),
                            params={"n": nom, "c": tel},
                            ttl=0
                        )
                        
                        if not df_check.empty: 
                            st.error("❌ Equipo o teléfono ya registrados.")
                        else:
                            st.session_state.datos_temp = {
                                "n": nom, "wa": tel, "pin": pin_r, 
                                "pref": pais_sel.split('(')[-1].replace(')', ''),
                                "escudo_obj": archivo_escudo
                            }
                            st.session_state.reg_estado = "confirmar"
                            st.rerun()
                                







    
# --- 5. CALENDARIO Y GESTIÓN DE PARTIDOS ---
elif fase_actual == "clasificacion":
    with tabs[1]:
        st.subheader("📅 Calendario Oficial")
        
        conn = get_db_connection()
        
        # Consultas optimizadas a Supabase
        df_p = conn.query("SELECT * FROM partidos ORDER BY jornada ASC", ttl=0)
        df_escudos = conn.query("SELECT nombre, escudo FROM equipos", ttl=0)
        
        # Diccionario de escudos para acceso rápido (Fallback a icono genérico si no hay escudo)
        GENERIC_SHIELD = "https://cdn-icons-png.flaticon.com/512/5329/5329945.png"
        escudos_dict = dict(zip(df_escudos['nombre'], df_escudos['escudo']))
        
        # Determinamos cuántas jornadas mostrar dinámicamente
        max_jornada = int(df_p['jornada'].max()) if not df_p.empty else 3
        jornadas_lista = [f"J{i+1}" for i in range(max_jornada)]
        
        j_tabs = st.tabs(jornadas_lista)
        
        for i, jt in enumerate(j_tabs):
            with jt:
                # Filtramos partidos de la jornada actual
                df_j = df_p[df_p['jornada'] == (i + 1)]
                
                if df_j.empty:
                    st.info(f"No hay partidos programados para la Jornada {i+1}")
                    continue
                
                for _, p in df_j.iterrows():
                    # Lógica de marcador
                    res_text = "vs"
                    if p['goles_l'] is not None and p['goles_v'] is not None:
                        try:
                            res_text = f"{int(p['goles_l'])}-{int(p['goles_v'])}"
                        except: 
                            res_text = "vs"
                    
                    # Obtener URLs de escudos
                    esc_l = escudos_dict.get(p['local']) or GENERIC_SHIELD
                    esc_v = escudos_dict.get(p['visitante']) or GENERIC_SHIELD

                    # --- DISEÑO DE FILA ULTRA COMPACTA ---
                    with st.container():
                        col_izq, col_cnt, col_der = st.columns([1, 0.8, 1])
                        
                        # Local
                        with col_izq:
                            st.markdown(f"""
                                <div style='display: flex; align-items: center; gap: 5px; font-size: 11px;'> 
                                    <img src='{esc_l}' width='22' height='22' style='object-fit: contain;'> 
                                    <b>{p['local'][:8]}</b> 
                                </div>
                            """, unsafe_allow_html=True)
                        
                        # Marcador
                        with col_cnt:
                            st.markdown(f"""
                                <div style='text-align: center; background: #31333F; color: white; border-radius: 4px; font-weight: bold; font-size: 12px; padding: 2px 0;'>
                                    {res_text}
                                </div>
                            """, unsafe_allow_html=True)
                        
                        # Visitante
                        with col_der:
                            st.markdown(f"""
                                <div style='display: flex; align-items: center; justify-content: flex-end; gap: 5px; font-size: 11px;'> 
                                    <b>{p['visitante'][:8]}</b> 
                                    <img src='{esc_v}' width='22' height='22' style='object-fit: contain;'> 
                                </div>
                            """, unsafe_allow_html=True)
                        
                        # Evidencias (Fotos de reporte)
                        if p.get('url_foto_l') or p.get('url_foto_v'):
                            with st.expander(f"📷 Ver evidencias"):
                                c_ev1, c_ev2 = st.columns(2)
                                if p['url_foto_l']: 
                                    c_ev1.image(p['url_foto_l'], caption="Local")
                                if p['url_foto_v']: 
                                    c_ev2.image(p['url_foto_v'], caption="Visitante")
                    
                    st.divider()
                    



                          



# --- TAB: MIS PARTIDOS (SOLO PARA DT) ---
if rol == "dt":
    with tabs[2]:
        st.subheader(f"🏟️ Mis Partidos: {equipo_usuario}")
        
        conn = get_db_connection()
        
        # Consultar partidos donde participa el DT (usando sintaxis Postgres)
        mis_partidos = conn.query(
            text("SELECT * FROM partidos WHERE (local = :eq OR visitante = :eq) ORDER BY jornada ASC"),
            params={"eq": equipo_usuario},
            ttl=0
        )
        
        if mis_partidos.empty:
            st.info("Aún no tienes partidos asignados en el calendario.")
        
        for _, p in mis_partidos.iterrows():
            es_local = (p['local'] == equipo_usuario)
            rival = p['visitante'] if es_local else p['local']
            
            with st.container():
                # Caja visual del encuentro
                st.markdown(f"""
                    <div style='background: #f0f2f6; padding: 15px; border-radius: 10px; border-left: 5px solid #FFD700; margin-bottom: 10px;'>
                        <small>JORNADA {p['jornada']}</small><br>
                        <span style='font-size: 18px;'>🆚 Rival: <b>{rival}</b></span>
                    </div>
                """, unsafe_allow_html=True)
                
                # --- CONTACTO WHATSAPP ---
                # Buscamos el teléfono del rival en la tabla de equipos
                df_rival = conn.query(
                    text("SELECT prefijo, celular FROM equipos WHERE nombre = :r"),
                    params={"r": rival},
                    ttl=3600 # El teléfono no cambia seguido, podemos cachear 1 hora
                )
                
                if not df_rival.empty:
                    row = df_rival.iloc[0]
                    num_wa = f"{str(row['prefijo']).replace('+', '')}{row['celular']}"
                    st.markdown(f"""
                        <a href='https://wa.me/{num_wa}' target='_blank' style='text-decoration: none;'>
                            <div style='background-color: #25D366; color: white; text-align: center; padding: 8px; border-radius: 5px; font-weight: bold; margin-bottom: 15px;'>
                                💬 Contactar DT Rival
                            </div>
                        </a>
                    """, unsafe_allow_html=True)

                # --- EXPANDER PARA REPORTE CON IA ---
                with st.expander(f"📸 Reportar Resultado J{p['jornada']}", expanded=False):
                    opcion = st.radio("Fuente:", ["Cámara", "Galería"], key=f"src_{p['id']}", horizontal=True)
                    
                    foto = st.camera_input("Capturar marcador", key=f"cam_{p['id']}") if opcion == "Cámara" else \
                           st.file_uploader("Cargar imagen", type=['png', 'jpg', 'jpeg'], key=f"file_{p['id']}")
                    
                    if foto:
                        if st.button("🔍 Validar con IA y Enviar", key=f"btn_ia_{p['id']}", use_container_width=True):
                            with st.spinner("Analizando marcador..."):
                                # 1. Análisis de IA (Función externa definida al inicio)
                                res_ia, mensaje_ia = leer_marcador_ia(foto, p['local'], p['visitante'])
                                
                                if res_ia is None:
                                    st.error(f"Error de lectura: {mensaje_ia}")
                                else:
                                    gl_ia, gv_ia = res_ia
                                    st.info(f"🤖 IA detectó: {gl_ia} - {gv_ia}")
                                    
                                    try:
                                        # 2. Subida a Cloudinary
                                        foto.seek(0)
                                        res_cloud = cloudinary.uploader.upload(foto, folder="reportes_partidos")
                                        url_nueva = res_cloud['secure_url']
                                        
                                        col_foto_db = "url_foto_l" if es_local else "url_foto_v"
                                        
                                        # 3. Lógica de Consenso / Conflicto en Supabase
                                        with conn.session as s:
                                            # Verificamos si ya hay goles reportados por el otro DT
                                            # (Usamos datos del DataFrame actual 'p')
                                            if p['goles_l'] is not None:
                                                if int(p['goles_l']) != gl_ia or int(p['goles_v']) != gv_ia:
                                                    # HAY CONFLICTO
                                                    s.execute(text(f"""
                                                        UPDATE partidos SET 
                                                        conflicto = 1, {col_foto_db} = :url,
                                                        ia_goles_l = :gl, ia_goles_v = :gv
                                                        WHERE id = :pid
                                                    """), {"url": url_nueva, "gl": gl_ia, "gv": gv_ia, "pid": p['id']})
                                                    st.warning("⚠️ Marcador diferente al reportado por el rival. El administrador revisará.")
                                                else:
                                                    # HAY CONSENSO
                                                    s.execute(text(f"""
                                                        UPDATE partidos SET 
                                                        {col_foto_db} = :url, conflicto = 0, estado = 'Finalizado'
                                                        WHERE id = :pid
                                                    """), {"url": url_nueva, "pid": p['id']})
                                                    st.success("✅ ¡Coincidencia total! Partido finalizado.")
                                            else:
                                                # PRIMER REPORTE
                                                s.execute(text(f"""
                                                    UPDATE partidos SET 
                                                    goles_l = :gl, goles_v = :gv, {col_foto_db} = :url,
                                                    ia_goles_l = :gl, ia_goles_v = :gv, estado = 'Revision'
                                                    WHERE id = :pid
                                                """), {"gl": gl_ia, "gv": gv_ia, "url": url_nueva, "pid": p['id']})
                                                st.success("⚽ Reporte enviado. Esperando confirmación del rival.")
                                            
                                            s.commit()
                                        st.rerun()
                                        
                                    except Exception as e:
                                        st.error(f"Error técnico: {e}")
                
                st.divider()




  
  
# --- TAB: GESTIÓN ADMIN (Consolidado Final para Supabase) ---
if rol == "admin":
    with tabs[2]:
        st.header("⚙️ Panel de Control Admin")
        
        conn = get_db_connection()
        
        # --- 1. SECCIÓN DE APROBACIONES ---
        st.subheader("📩 Equipos por Aprobar")
        
        # Consultamos pendientes y conteo de aprobados
        df_pendientes = conn.query("SELECT * FROM equipos WHERE estado='pendiente'", ttl=0)
        df_aprobados = conn.query("SELECT nombre FROM equipos WHERE estado='aprobado'", ttl=0)
        aprobados_count = len(df_aprobados)
        
        st.write(f"**Progreso: {aprobados_count} Equipos Aprobados**")
        
        if not df_pendientes.empty:
            for _, r in df_pendientes.iterrows():
                with st.container():
                    col_data, col_btn = st.columns([2, 1])
                    prefijo = str(r.get('prefijo', '')).replace('+', '')
                    wa_link = f"https://wa.me/{prefijo}{r['celular']}"
                    
                    with col_data:
                        st.markdown(f"**{r['nombre']}**")
                        st.markdown(f"<a href='{wa_link}' target='_blank' style='color: #25D366; text-decoration: none;'>🟢 Contactar DT</a>", unsafe_allow_html=True)
                    
                    with col_btn:
                        if st.button(f"✅ Aprobar", key=f"aprob_{r['nombre']}", use_container_width=True):
                            url_final = r['escudo']
                            
                            # Si tiene escudo, usamos la IA de Cloudinary para quitar el fondo
                            if url_final and "res.cloudinary.com" in url_final:
                                with st.spinner("🤖 IA Limpiando Fondo..."):
                                    try:
                                        # background_removal="cloudinary_ai" quita el fondo automáticamente
                                        res_ia = cloudinary.uploader.upload(
                                            url_final,
                                            background_removal="cloudinary_ai",
                                            folder="escudos_limpios",
                                            format="png"
                                        )
                                        url_final = res_ia['secure_url']
                                        # Agregamos timestamp para evitar que el navegador use la imagen vieja (Cache Busting)
                                        url_final = f"{url_final}?v={int(time.time())}"
                                    except Exception as e:
                                        st.error(f"Error IA Cloudinary: {e}")
                            
                            # Actualizamos en Supabase usando SQL puro (SQLAlchemy)
                            with conn.session as s:
                                s.execute(
                                    text("UPDATE equipos SET estado='aprobado', escudo=:esc WHERE nombre=:nom"),
                                    {"esc": url_final, "nom": r['nombre']}
                                )
                                s.commit()
                            st.success(f"¡{r['nombre']} aprobado!")
                            st.rerun()
                st.divider()
        else:
            st.info("No hay equipos pendientes de aprobación.")

        # --- 2. GESTIÓN DE RESULTADOS Y CONFLICTOS ---
        st.divider()
        opcion_admin = st.radio("Tarea:", ["⚽ Resolver Conflictos", "🛠️ Directorio de Equipos"], horizontal=True)
        
        if opcion_admin == "⚽ Resolver Conflictos":
            st.subheader("⚠️ Conflictos detectados por IA")
            df_conf = conn.query("SELECT * FROM partidos WHERE conflicto=1", ttl=0)
            
            if df_conf.empty:
                st.success("No hay conflictos de resultados pendientes.")
            else:
                for _, p in df_conf.iterrows():
                    with st.expander(f"Conflicto J{p['jornada']}: {p['local']} vs {p['visitante']}"):
                        st.write("La IA leyó cosas distintas o los DT reportaron diferente.")
                        c1, c2 = st.columns(2)
                        if p['url_foto_l']: c1.image(p['url_foto_l'], caption="Foto Local")
                        if p['url_foto_v']: c2.image(p['url_foto_v'], caption="Foto Visitante")
                        
                        # Formulario manual para el Admin
                        with st.form(f"f_conf_{p['id']}"):
                            nl = st.number_input("Goles Local", value=0, min_value=0)
                            nv = st.number_input("Goles Visitante", value=0, min_value=0)
                            if st.form_submit_button("🔨 Dictar Sentencia Final"):
                                with conn.session as s:
                                    s.execute(text("""
                                        UPDATE partidos SET 
                                        goles_l=:gl, goles_v=:gv, conflicto=0, estado='Finalizado' 
                                        WHERE id=:pid
                                    """), {"gl": nl, "gv": nv, "pid": p['id']})
                                    s.commit()
                                st.rerun()

        elif opcion_admin == "🛠️ Directorio de Equipos":
            st.subheader("📋 Base de Datos de Equipos")
            df_maestro = conn.query("SELECT * FROM equipos ORDER BY nombre ASC", ttl=0)
            st.dataframe(df_maestro[['nombre', 'pin', 'estado', 'celular']])
            
            equipo_a_borrar = st.selectbox("Eliminar Equipo:", [""] + df_maestro['nombre'].tolist())
            if equipo_a_borrar != "" and st.button("🚨 ELIMINAR EQUIPO DEFINITIVAMENTE"):
                with conn.session as s:
                    s.execute(text("DELETE FROM equipos WHERE nombre=:n"), {"n": equipo_a_borrar})
                    s.commit()
                st.rerun()

        # --- 3. ACCIONES MAESTRAS ---
        st.divider()
        st.subheader("🚀 Control del Torneo")
        
        col_torneo, col_reset = st.columns(2)
        
        with col_torneo:
            if fase_actual == "inscripcion":
                if st.button("🏁 CERRAR INSCRIPCIÓN Y GENERAR CALENDARIO", type="primary", use_container_width=True):
                    if aprobados_count >= 2:
                        generar_calendario() # Esta función debe estar definida al inicio
                        st.rerun()
                    else:
                        st.error("Necesitas al menos 2 equipos aprobados.")
        
        with col_reset:
            if st.button("🚨 REINICIAR TODO EL SISTEMA", use_container_width=True, help="Borra equipos y partidos"):
                with conn.session as s:
                    s.execute(text("DELETE FROM partidos"))
                    s.execute(text("DELETE FROM equipos"))
                    s.execute(text("UPDATE config SET valor='inscripcion' WHERE clave='fase_actual'"))
                    s.commit()
                st.session_state.clear()
                st.rerun()











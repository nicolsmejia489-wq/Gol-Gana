import streamlit as st
import sqlite3
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


#PROVISIONAL PARA HACER PRUEBAS DE DESARROLLO
# Nombre del archivo donde se guardará todo
DB_FILE = "data_torneo.json"

def guardar_datos():
    """Guarda el estado actual de session_state en un archivo JSON"""
    # Filtramos solo lo que queremos persistir (equipos, resultados, etc.)
    datos_a_guardar = {
        "equipos": st.session_state.get("equipos", []),
        "partidos": st.session_state.get("partidos", []),
        "registrados": st.session_state.get("registrados", False)
    }
    with open(DB_FILE, "w") as f:
        json.dump(datos_a_guardar, f)

def cargar_datos():
    """Carga los datos desde el archivo JSON al session_state"""
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            datos = json.load(f)
            for key, value in datos.items():
                st.session_state[key] = value
        return True
    return False



####FIN PROVISIONAL


# 1. CONFIGURACIÓN PRINCIPAL DE SITIO
st.set_page_config(page_title="Gol-Gana Pro", layout="centered", initial_sidebar_state="collapsed")

# 2. Inyectar el Meta Tag de "color-scheme"
st.markdown('<meta name="color-scheme" content="light">', unsafe_allow_html=True)


# Configura credenciales (Cloudinary) Base de datos en Nube
cloudinary.config( 
  cloud_name = "dlvczeqlp", 
  api_key = "276694391654197", 
  api_secret = "j-_6AaUam_Acwng0GGr8tmb8Zyk",
  secure = True
)


from contextlib import contextmanager

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


# --- INICIALIZACIÓN DE DATOS --- #PROVISIONAL PARTE 2
if "datos_cargados" not in st.session_state:
    if cargar_datos():
        st.session_state["datos_cargados"] = True
    else:
        # Si no hay archivo, inicializamos vacío
        if "equipos" not in st.session_state: st.session_state["equipos"] = []
        if "partidos" not in st.session_state: st.session_state["partidos"] = []
        st.session_state["datos_cargados"] = True

####FIN PROVISIONAL PARTE 2


@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False, timeout=15)
    try: yield conn
    finally: conn.close()

def inicializar_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS equipos (
            nombre TEXT PRIMARY KEY, celular TEXT, prefijo TEXT, pin TEXT, estado TEXT DEFAULT 'pendiente'
        )''')
        # Agregamos las columnas nuevas aquí también para que si la base de datos es nueva, nazca completa
        cursor.execute('''CREATE TABLE IF NOT EXISTS partidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            local TEXT, visitante TEXT, 
            goles_l INTEGER DEFAULT NULL, goles_v INTEGER DEFAULT NULL, 
            jornada INTEGER, estado TEXT DEFAULT 'programado',
            url_foto_l TEXT, url_foto_v TEXT, 
            ia_goles_l INTEGER, ia_goles_v INTEGER, 
            conflicto INTEGER DEFAULT 0
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS config (llave TEXT PRIMARY KEY, valor TEXT)''')
        cursor.execute("INSERT OR IGNORE INTO config (llave, valor) VALUES ('fase', 'inscripcion')")
        conn.commit()

def migrar_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Estas son las columnas que añadimos por si la base de datos ya existía de antes
        columnas = [
            ("url_foto_l", "TEXT"),
            ("url_foto_v", "TEXT"),
            ("ia_goles_l", "INTEGER"),
            ("ia_goles_v", "INTEGER"),
            ("conflicto", "INTEGER DEFAULT 0")
        ]
        for nombre_col, tipo in columnas:
            try:
                cursor.execute(f"ALTER TABLE partidos ADD COLUMN {nombre_col} {tipo}")
            except sqlite3.OperationalError:
                pass # Si la columna ya existe, no hace nada
        conn.commit()

# --- EJECUCIÓN ---
inicializar_db() # 1. Crea lo básico
migrar_db()      # 2. Asegura que lo nuevo esté ahí


##### ALGORITMO IA #####


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

st.title("⚽ Gol Gana")
c_nav1, c_nav2 = st.columns(2)
with c_nav1:
    if st.button("🔙 Inicio"):
        st.session_state.reg_estado = "formulario"
        st.session_state.pin_usuario = ""
        st.rerun()
with c_nav2:
    if st.button("🔄 Refrescar"): st.rerun()

pin_input = st.text_input("🔑 PIN de Acceso", value=st.session_state.pin_usuario, type="password")
st.session_state.pin_usuario = pin_input

with get_db_connection() as conn:
    cur = conn.cursor()
    cur.execute("SELECT valor FROM config WHERE llave = 'fase'")
    fase_actual = cur.fetchone()[0]

rol = "espectador"
equipo_usuario = None
if st.session_state.pin_usuario == ADMIN_PIN:
    rol = "admin"
elif st.session_state.pin_usuario:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT nombre FROM equipos WHERE pin = ? AND estado = 'aprobado'", (st.session_state.pin_usuario,))
        res = cur.fetchone()
        if res: rol = "dt"; equipo_usuario = res[0]



# --- LÓGICA DINÁMICA DE PESTAÑAS ---
if fase_actual == "inscripcion":
    if rol == "admin":
        titulos = ["📊 Clasificación", "📝 Inscripciones", "⚙️ Gestión Admin"]
    else:
        titulos = ["📊 Clasificación", "📝 Inscribirse"]
else:
    # Fase de Torneo
    if rol == "admin":
        titulos = ["📊 Clasificación", "📅 Calendario", "⚙️ Gestión Admin"]
    elif rol == "dt": 
        titulos = ["📊 Clasificación", "📅 Calendario", "⚽ Mis Partidos"]
    else: 
        titulos = ["📊 Clasificación", "📅 Calendario"]

tabs = st.tabs(titulos)

# --- CONTENIDO DE LAS PESTAÑAS ---
with tabs[0]:
    st.subheader("Tabla de Posiciones")
    # Tu código de tabla...

with tabs[1]:
    if fase_actual == "inscripcion":
        st.subheader("Registro de Equipos")
        # Aquí va tu formulario de inscripción o lista para el admin
    else:
        st.subheader("Calendario de Juegos")
        # Aquí va el calendario

# La pestaña [2] solo existe si eres Admin o DT en fase de juego
if len(titulos) > 2:
    with tabs[2]:
        if rol == "admin":
            st.subheader("⚙️ Panel de Control Admin")
            if fase_actual == "inscripcion":
                st.info("Acepta a los equipos inscritos aquí abajo:")
                # Aquí pondremos el código para validar equipos
            else:
                st.info("Gestiona los resultados de los partidos:")
                # Aquí va tu código de gestión de resultados que ya hicimos
        elif rol == "dt":
            st.subheader("⚽ Gestión de mi Equipo")





# TAB: CLASIFICACIÓN
with tabs[0]:
    with get_db_connection() as conn:
        df_eq = pd.read_sql_query("SELECT nombre FROM equipos WHERE estado = 'aprobado'", conn)
        if df_eq.empty: st.info("No hay equipos todavía.")
        else:
            stats = {e: {'PJ':0, 'PTS':0, 'GF':0, 'GC':0} for e in df_eq['nombre']}
            df_p = pd.read_sql_query("SELECT * FROM partidos WHERE goles_l IS NOT NULL", conn)
            for _, f in df_p.iterrows():
                l, v, gl, gv = f['local'], f['visitante'], int(f['goles_l']), int(f['goles_v'])
                if l in stats and v in stats:
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
            html = '<table class="mobile-table"><thead><tr><th>POS</th><th style="text-align:left">EQ</th><th>PTS</th><th>PJ</th><th>GF</th><th>GC</th><th>DG</th></tr></thead><tbody>'
            for _, r in df_f.iterrows():
                html += f"<tr><td>{r['POS']}</td><td class='team-cell'>{r['EQ']}</td><td><b>{r['PTS']}</b></td><td>{r['PJ']}</td><td>{r['GF']}</td><td>{r['GC']}</td><td>{r['DG']}</td></tr>"
            st.markdown(html + "</tbody></table>", unsafe_allow_html=True)

# TAB: REGISTRO (CON FIX DEFINITIVO)
if fase_actual == "inscripcion":
    with tabs[1]:
        if st.session_state.reg_estado == "exito":
            st.success("✅ ¡Inscripción recibida!")
            if st.button("Nuevo Registro"): st.session_state.reg_estado = "formulario"; st.rerun()
        
        elif st.session_state.reg_estado == "confirmar":
            d = st.session_state.datos_temp
            st.warning("⚠️ **Confirma tus datos:**")
            st.write(f"**Equipo:** {d['n']}\n\n**WA:** {d['pref']} {d['wa']}\n\n**PIN:** {d['pin']}")
            c1, c2 = st.columns(2)
            
            if c1.button("✅ Confirmar"):
                registro_ok = False
                with get_db_connection() as conn:
                    try:
                        conn.execute("INSERT INTO equipos (nombre, celular, prefijo, pin) VALUES (?,?,?,?)", (d['n'], d['wa'], d['pref'], d['pin']))
                        conn.commit()
                        registro_ok = True
                    except sqlite3.Error as e:
                        st.error(f"Error real de base de datos: {e}")
                
                if registro_ok: # Rerun FUERA del try-except
                    st.session_state.reg_estado = "exito"
                    st.rerun()

            if c2.button("✏️ Editar"): st.session_state.reg_estado = "formulario"; st.rerun()
        
        else:
            with st.form("reg_preventivo"):
                nom = st.text_input("Nombre Equipo").strip()
                paises = {"Colombia": "+57",    "EEUU": "+1",    "México": "+52",    "Canadá": "+1",    "Costa Rica": "+506",    "Ecuador": "+593",    "Panamá": "+507",    "Perú": "+51",    "Uruguay": "+598",    "Argentina": "+54",    "Bolivia": "+591", "Brasil": "+55",    "Chile": "+56",    "Venezuela": "+58",    "Belice": "+501",    "Guatemala": "+502",    "El Salvador": "+503",    "Honduras": "+504",    "Nicaragua": "+505"}
                pais_sel = st.selectbox("País", [f"{p} ({pref})" for p, pref in paises.items()])
                tel = st.text_input("WhatsApp").strip()
                pin_r = st.text_input("PIN (4 dígitos)", max_chars=4, type="password").strip()
                if st.form_submit_button("Siguiente"):
                    if not nom or not tel or len(pin_r) < 4: st.error("Datos incompletos.")
                    else:
                        with get_db_connection() as conn:
                            cur = conn.cursor()
                            cur.execute("SELECT 1 FROM equipos WHERE nombre=? OR pin=? OR celular=?", (nom, pin_r, tel))
                            if cur.fetchone(): st.error("❌ Nombre, PIN o Teléfono ya registrados.")
                            else:
                                st.session_state.datos_temp = {"n": nom, "wa": tel, "pin": pin_r, "pref": pais_sel.split('(')[-1].replace(')', '')}
                                st.session_state.reg_estado = "confirmar"; st.rerun()


    
# --- 5. CALENDARIO Y GESTIÓN DE PARTIDOS ---
elif fase_actual == "clasificacion":
    # 1. Pestaña de Calendario (tabs[1])
    with tabs[1]:
        st.subheader("📅 Calendario Oficial")
        with get_db_connection() as conn:
            df_p = pd.read_sql_query("SELECT * FROM partidos ORDER BY jornada ASC", conn)
        
        j_tabs = st.tabs(["Jornada 1", "Jornada 2", "Jornada 3"])
        for i, jt in enumerate(j_tabs):
            with jt:
                df_j = df_p[df_p['jornada'] == (i + 1)]
                for _, p in df_j.iterrows():
                    # Manejo de marcadores
                    if p['goles_l'] is not None and p['goles_v'] is not None:
                        try:
                            res_text = f"{int(p['goles_l'])} - {int(p['goles_v'])}"
                        except:
                            res_text = "vs"
                    else:
                        res_text = "vs"
                    
                    c1, c2 = st.columns([0.8, 0.2])
                    c1.write(f"**{p['local']}** {res_text} **{p['visitante']}**")
                    
                    if p['url_foto_l'] or p['url_foto_v']:
                        if c2.button("👁️", key=f"view_{p['id']}"):
                            if p['url_foto_l']: st.image(p['url_foto_l'], caption=f"Evidencia {p['local']}")
                            if p['url_foto_v']: st.image(p['url_foto_v'], caption=f"Evidencia {p['visitante']}")


# --- TAB: MIS PARTIDOS (SOLO PARA DT) ---
if rol == "dt":
    with tabs[2]:
        st.subheader(f"🏟️ Mis Partidos: {equipo_usuario}")
        
        # Consultar partidos del usuario
        with get_db_connection() as conn:
            mis = pd.read_sql_query(
                "SELECT * FROM partidos WHERE (local=? OR visitante=?) ORDER BY jornada ASC", 
                conn, params=(equipo_usuario, equipo_usuario)
            )
            
            if mis.empty:
                st.info("Aún no tienes partidos asignados.")
            
            for _, p in mis.iterrows():
                es_local = (p['local'] == equipo_usuario)
                rival = p['visitante'] if es_local else p['local']
                
                with st.container():
                    # Caja de información visual
                    st.markdown(f"""
                        <div class='match-box'>
                            <b>Jornada {p['jornada']}</b><br>
                            Rival: {rival}
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # --- CONTACTO WHATSAPP ---
                    cur = conn.cursor()
                    cur.execute("SELECT prefijo, celular FROM equipos WHERE nombre=?", (rival,))
                    r = cur.fetchone()
                    
                    if r and r[0] and r[1]:
                        numero_wa = f"{str(r[0]).replace('+', '')}{r[1]}"
                        st.markdown(f"""
                            <a href='https://wa.me/{numero_wa}' class='wa-btn' style='text-decoration: none;'>
                                💬 Contactar Rival (WhatsApp)
                            </a>
                        """, unsafe_allow_html=True)
                    else:
                        st.caption("🚫 Sin contacto registrado.")

                    # --- EXPANDER PARA REPORTE ---
                    with st.expander(f"📸 Reportar Marcador J{p['jornada']}", expanded=False):
                        # Selección de fuente con llave única
                        opcion = st.radio(
                            "Selecciona fuente:", 
                            ["Cámara", "Galería"], 
                            key=f"dt_opt_{p['id']}", 
                            horizontal=True
                        )
                        
                        foto = None
                        if opcion == "Cámara":
                            foto = st.camera_input("Capturar pantalla", key=f"dt_cam_{p['id']}")
                        else:
                            foto = st.file_uploader("Subir imagen", type=['png', 'jpg', 'jpeg'], key=f"dt_gal_{p['id']}")
                        
                        if foto:
                            st.image(foto, width=250, caption="Evidencia cargada")
                            
                            if st.button("🔍 Analizar y Enviar Resultado", key=f"dt_btn_ia_{p['id']}"):
                                with st.spinner("La IA está analizando la imagen..."):
                                    # 1. Análisis de IA
                                    res_ia, mensaje_ia = leer_marcador_ia(foto, p['local'], p['visitante'])
                                    
                                    if res_ia is None:
                                        st.error(mensaje_ia)
                                    else:
                                        gl_ia, gv_ia = res_ia
                                        st.info(f"🤖 IA detectó marcador: {gl_ia} - {gv_ia}")

                                        try:
                                            # --- SOLUCIÓN ERROR 'EMPTY FILE' ---
                                            # Rebobinamos el archivo porque la IA ya lo leyó
                                            foto.seek(0)
                                            
                                            # 2. Subida a Cloudinary
                                            res_cloud = cloudinary.uploader.upload(foto, folder="gol_gana_evidencias")
                                            url_nueva = res_cloud['secure_url']
                                            
                                            # Determinar columna de foto según rol
                                            col_foto = "url_foto_l" if es_local else "url_foto_v"

                                            with get_db_connection() as conn_up:
                                                # 3. Lógica de Consenso / Conflicto
                                                gl_existente = p['goles_l']
                                                gv_existente = p['goles_v']

                                                # Si ya hay un reporte previo (del rival)
                                                if gl_existente is not None:
                                                    if int(gl_existente) != gl_ia or int(gv_existente) != gv_ia:
                                                        # CONFLICTO: Marcadores diferentes
                                                        conn_up.execute(f"""
                                                            UPDATE partidos SET 
                                                            goles_l=NULL, goles_v=NULL, 
                                                            conflicto=1, {col_foto}=?, 
                                                            ia_goles_l=?, ia_goles_v=? 
                                                            WHERE id=?""", (url_nueva, gl_ia, gv_ia, p['id']))
                                                        st.warning("⚠️ Conflicto: Los resultados no coinciden. El Admin decidirá.")
                                                    else:
                                                        # CONSENSO: Ambos coinciden
                                                        conn_up.execute(f"""
                                                            UPDATE partidos SET 
                                                            {col_foto}=?, conflicto=0, estado='Finalizado' 
                                                            WHERE id=?""", (url_nueva, p['id']))
                                                        st.success("✅ ¡Marcador verificado y finalizado!")
                                                else:
                                                    # PRIMER REPORTE: Nadie había subido nada
                                                    conn_up.execute(f"""
                                                        UPDATE partidos SET 
                                                        goles_l=?, goles_v=?, 
                                                        {col_foto}=?, ia_goles_l=?, 
                                                        ia_goles_v=?, estado='Revision' 
                                                        WHERE id=?""", (gl_ia, gv_ia, url_nueva, gl_ia, gv_ia, p['id']))
                                                    st.success("⚽ Resultado guardado. Esperando reporte del rival.")
                                                
                                                conn_up.commit()
                                            
                                            # Pausa breve y recarga
                                            st.rerun()

                                        except Exception as e:
                                            st.error(f"❌ Error al procesar: {e}")
                    
                    st.markdown("<hr style='margin:10px 0; opacity:0.2;'>", unsafe_allow_html=True)

  #########


  
  
# --- TAB: GESTIÓN ADMIN ---
if rol == "admin":
    with tabs[2]:
        # Selector de sub-sección para móviles
        opcion_admin = st.radio("Selecciona Tarea:", ["⚽ Gestionar Resultados", "🛠️ Control de Equipos"], horizontal=True)
        st.divider()

        if opcion_admin == "⚽ Gestionar Resultados":
            st.subheader("⚙️ Gestión de Marcadores")
            
            with get_db_connection() as conn:
                df_adm = pd.read_sql_query("SELECT * FROM partidos ORDER BY jornada ASC, id ASC", conn)
                df_equipos = pd.read_sql_query("SELECT nombre, prefijo, celular FROM equipos", conn)
                contactos = {
                    r['nombre']: f"https://wa.me/{str(r['prefijo']).replace('+','')}{r['celular']}"
                    for _, r in df_equipos.iterrows() if r['celular']
                }

            jornadas = sorted(df_adm['jornada'].unique())
            if jornadas:
                tab_names = [f"J{j}" for j in jornadas]
                mini_tabs = st.tabs(tab_names)

                for i, j_num in enumerate(jornadas):
                    with mini_tabs[i]:
                        partidos_jornada = df_adm[df_adm['jornada'] == j_num]
                        for _, p in partidos_jornada.iterrows():
                            label = f"{p['local']} vs {p['visitante']}"
                            if p.get('conflicto') == 1:
                                label = f"⚠️ CONFLICTO: {label}"

                            with st.expander(label):
                                if p['url_foto_l'] or p['url_foto_v']:
                                    f1, f2 = st.columns(2)
                                    with f1:
                                        if p['url_foto_l']: st.image(p['url_foto_l'], caption=f"Foto {p['local']}", width=150)
                                    with f2:
                                        if p['url_foto_v']: st.image(p['url_foto_v'], caption=f"Foto {p['visitante']}", width=150)

                                c1, c2, c3 = st.columns([2, 1, 2])
                                gl_val = int(p['goles_l']) if pd.notna(p['goles_l']) else 0
                                gv_val = int(p['goles_v']) if pd.notna(p['goles_v']) else 0
                                
                                gl = c1.number_input(f"{p['local']}", value=gl_val, step=1, key=f"adm_l_{p['id']}")
                                c2.markdown("<div style='text-align:center; padding-top:25px;'>VS</div>", unsafe_allow_html=True)
                                gv = c3.number_input(f"{p['visitante']}", value=gv_val, step=1, key=f"adm_v_{p['id']}")
                                
                                wa1, wa2 = st.columns(2)
                                if p['local'] in contactos:
                                    wa1.markdown(f"<a href='{contactos[p['local']]}' class='wa-btn' style='font-size:10px'>💬 WA {p['local']}</a>", unsafe_allow_html=True)
                                if p['visitante'] in contactos:
                                    wa2.markdown(f"<a href='{contactos[p['visitante']]}' class='wa-btn' style='font-size:10px'>💬 WA {p['visitante']}</a>", unsafe_allow_html=True)
                                
                                if st.button("Guardar Resultado Oficial", key=f"save_adm_{p['id']}", use_container_width=True):
                                    with get_db_connection() as conn:
                                        conn.execute("""
                                            UPDATE partidos 
                                            SET goles_l=?, goles_v=?, estado='finalizado', conflicto=0 
                                            WHERE id=?
                                        """, (gl, gv, p['id']))
                                        conn.commit()
                                    st.success("Marcador Actualizado")
                                    st.rerun()
            else:
                st.info("No hay partidos programados.")

        # --- NUEVA SECCIÓN: CONTROL DE EQUIPOS ---
        elif opcion_admin == "🛠️ Control de Equipos":
            st.subheader("📋 Directorio Maestro")
            
            with get_db_connection() as conn:
                df_maestro = pd.read_sql_query("SELECT id, nombre, celular, pin FROM equipos", conn)
            
            if df_maestro.empty:
                st.warning("No hay equipos registrados aún.")
            else:
                # 1. Visualización rápida para celular
                for _, eq in df_maestro.iterrows():
                    st.markdown(f"**{eq['nombre']}** | 🔑 PIN: `{eq['pin']}` | 📞 {eq['celular']}")
                
                st.divider()
                st.subheader("✏️ Corregir Datos")
                
                # Buscador de equipo para editar
                equipo_sel = st.selectbox("Equipo a modificar:", df_maestro['nombre'].tolist())
                datos_eq = df_maestro[df_maestro['nombre'] == equipo_sel].iloc[0]
                
                with st.form("edicion_equipo_form"):
                    new_name = st.text_input("Nombre del Equipo", datos_eq['nombre'])
                    new_cel = st.text_input("Celular (sin prefijo)", datos_eq['celular'])
                    new_pin = st.text_input("PIN de acceso", datos_eq['pin'])
                    
                    st.info("💡 Al cambiar el nombre, se actualizará en todos los partidos.")
                    
                    c_btn1, c_btn2 = st.columns(2)
                    with c_btn1:
                        btn_save = st.form_submit_button("✅ Guardar", use_container_width=True)
                    with c_btn2:
                        btn_del = st.form_submit_button("🗑️ Eliminar", use_container_width=True)
                    
                    if btn_save:
                        with get_db_connection() as conn:
                            # 1. Actualizar tabla equipos
                            conn.execute("UPDATE equipos SET nombre=?, celular=?, pin=? WHERE id=?", 
                                         (new_name, new_cel, new_pin, int(datos_eq['id'])))
                            # 2. Actualizar nombres en partidos (cascada manual)
                            conn.execute("UPDATE partidos SET local=? WHERE local=?", (new_name, equipo_sel))
                            conn.execute("UPDATE partidos SET visitante=? WHERE visitante=?", (new_name, equipo_sel))
                            conn.commit()
                        st.success("Cambios aplicados correctamente.")
                        st.rerun()
                    
                    if btn_del:
                        with get_db_connection() as conn:
                            conn.execute("DELETE FROM equipos WHERE id=?", (int(datos_eq['id']),))
                            conn.commit()
                        st.warning("Equipo eliminado.")
                        st.rerun()




# SECCIÓN ADMIN (INFERIOR)
if rol == "admin":
    st.divider()
    if fase_actual == "inscripcion":
        with get_db_connection() as conn:
            pend = pd.read_sql_query("SELECT * FROM equipos WHERE estado='pendiente'", conn)
            st.write(f"Aprobados: {len(pd.read_sql_query('SELECT 1 FROM equipos WHERE estado=\'aprobado\'', conn))}/32")
            for _, r in pend.iterrows():
                if st.button(f"Aprobar {r['nombre']}"):
                    conn.execute("UPDATE equipos SET estado='aprobado' WHERE nombre=?", (r['nombre'],))
                    conn.commit(); st.rerun()
        if st.button("🚀 INICIAR TORNEO"): generar_calendario(); st.rerun()
    if st.button("🚨 REINICIAR TODO"):
        with get_db_connection() as conn:
            conn.execute("DROP TABLE IF EXISTS equipos"); conn.execute("DROP TABLE IF EXISTS partidos")
            conn.execute("UPDATE config SET valor='inscripcion'"); conn.commit()
        st.rerun()


































































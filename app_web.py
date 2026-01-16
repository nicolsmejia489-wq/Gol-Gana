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
import streamlit as st


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


# --- INICIALIZACIÓN DE DATOS 
if "datos_cargados" not in st.session_state:
    if cargar_datos():
        st.session_state["datos_cargados"] = True
    else:
        # Si no hay archivo, inicializamos vacío
        if "equipos" not in st.session_state: st.session_state["equipos"] = []
        if "partidos" not in st.session_state: st.session_state["partidos"] = []
        st.session_state["datos_cargados"] = True

####


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


# BORRAR--- BLOQUE DE VERIFICACIÓN (Solo para estar seguros) ---
with get_db_connection() as conn:
    columnas = pd.read_sql_query("PRAGMA table_info(equipos)", conn)
    st.write("Columnas detectadas en la tabla equipos:", columnas['name'].tolist())




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

####################PORTADA EN PRUEBA

# --- CONSTANTES DE DISEÑO ---
# Reemplaza este link con el que obtengas de Cloudinary o GitHub
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
with c_nav2:
    if st.button("🔄 Refrescar"): 
        st.rerun()

# --- CAMPO DE PIN Y BOTÓN DE ENTRAR ---
pin_input = st.text_input("🔑 PIN de Acceso", value=st.session_state.pin_usuario, type="password")
btn_entrar = st.button("🔓 Entrar", use_container_width=True)

# Actualizamos el estado con lo que se escriba
st.session_state.pin_usuario = pin_input

with get_db_connection() as conn:
    cur = conn.cursor()
    cur.execute("SELECT valor FROM config WHERE llave = 'fase'")
    fase_actual = cur.fetchone()[0]

rol = "espectador"
equipo_usuario = None

# --- LÓGICA DE VALIDACIÓN (Solo al dar click en Entrar) ---
if btn_entrar:
    if st.session_state.pin_usuario == ADMIN_PIN:
        rol = "admin"
        st.rerun()
    elif st.session_state.pin_usuario:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT nombre FROM equipos WHERE pin = ? AND estado = 'aprobado'", (st.session_state.pin_usuario,))
            res = cur.fetchone()
            
            if res:
                rol = "dt"
                equipo_usuario = res[0]
                st.rerun()
            else:
                # ACCIÓN DEFINITIVA: Aviso + Limpieza + Rerun (Como botón Inicio)
                st.markdown("""
                    <div style="position: fixed; top: 40px; left: 50%; transform: translateX(-50%);
                                background-color: white; color: black; padding: 12px 24px;
                                border-radius: 8px; border: 2px solid #ff4b4b;
                                box-shadow: 0 4px 12px rgba(0,0,0,0.3); z-index: 9999;
                                font-weight: bold;">
                        ⚠️ PIN no registrado o no aprobado
                    </div>
                """, unsafe_allow_html=True)
                
                # Forzamos la limpieza y el reinicio al estado inicial
                st.session_state.pin_usuario = ""
                st.session_state.reg_estado = "formulario"
                # Opcional: un pequeño delay para que alcancen a leer el mensaje antes del rerun
                import time
                time.sleep(1.5) 
                st.rerun()

# Mantener la sesión activa si el PIN ya es correcto
if st.session_state.pin_usuario:
    if st.session_state.pin_usuario == ADMIN_PIN:
        rol = "admin"
    else:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT nombre FROM equipos WHERE pin = ? AND estado = 'aprobado'", (st.session_state.pin_usuario,))
            res = cur.fetchone()
            if res:
                rol = "dt"
                equipo_usuario = res[0]




# --- DEFINICIÓN DINÁMICA DE PESTAÑAS ---
if fase_actual == "inscripcion":
    # Fase inicial: No hay partidos, hay inscripciones
    titulos = ["📊 Posiciones", "📝 Inscripción", "⚙️ Gestión"]
else:
    # Fase de juego: Se cambia Inscripción por Calendario/Partidos
    titulos = ["📊 Posiciones", "📅 Partidos", "⚙️ Gestión"]

tabs = st.tabs(titulos)



# --- PESTAÑA 0: POSICIONES (Siempre igual) ---
with tabs[0]:
    st.subheader("🏆 Tabla de Clasificación")
    # Tu código para mostrar la tabla de posiciones aquí...

# --- PESTAÑA 1: INSCRIPCIÓN O PARTIDOS (Dinámica) ---
with tabs[1]:
    if fase_actual == "inscripcion":
        st.subheader("📝 Registro de Equipos")
        # Aquí va tu código del Formulario de Inscripción para usuarios
        # y la lista de equipos ya inscritos.
    else:
        st.subheader("📅 Calendario de Juegos")
        # Aquí va tu código para mostrar las Jornadas y Resultados
        # que ven los espectadores y Dts.

# --- PESTAÑA 2: GESTIÓN (ADMIN O DT) ---
with tabs[2]:
    if rol == "admin":
        # --- BLOQUE DE GESTIÓN ADMIN (El que ya pulimos) ---
        st.header("⚙️ Panel de Control Admin")
        # Aquí pegas todo el código de: Aprobaciones, Radio de Tareas, 
        # Directorio de Equipos y Botones de Iniciar/Reiniciar.
        
    elif rol == "dt":
        # --- BLOQUE DE GESTIÓN DT ---
        st.header(f"⚽ Gestión: {equipo_usuario}")
        if fase_actual == "inscripcion":
            st.info("👋 ¡Hola DT! Tu equipo ya está aprobado. El torneo aún no comienza, espera a que el administrador genere el calendario.")
        else:
            st.success("✅ Torneo en curso. Aquí podrás reportar tus marcadores.")
            # Próximo paso: Formulario de reporte para el DT
            
    else:
        # Lo que ve alguien que no ha puesto un PIN válido
        st.markdown("### 🔒 Acceso Restringido")
        st.info("Esta sección es solo para **Administradores** o **Directores Técnicos** registrados.")
        st.write("Por favor, ingresa tu PIN en la parte superior para acceder a las funciones de gestión.")






# --- TAB: CLASIFICACIÓN (Versión Definitiva) ---
with tabs[0]:
    with get_db_connection() as conn:
        # Traemos nombre y escudo
        df_eq = pd.read_sql_query("SELECT nombre, escudo FROM equipos WHERE estado = 'aprobado'", conn)
        
        if df_eq.empty:
            st.info("No hay equipos todavía.")
        else:
            # LIMPIEZA TOTAL: Forzamos a que el nombre sea texto puro, no tuplas
            df_eq['nombre'] = df_eq['nombre'].astype(str).str.replace(r"[\(\)',]", "", regex=True).str.strip()
            
            # Diccionario para estadísticas
            stats = {e: {'PJ':0, 'PTS':0, 'GF':0, 'GC':0} for e in df_eq['nombre']}
            # Diccionario para escudos (Nombre -> URL)
            escudos_dict = dict(zip(df_eq['nombre'], df_eq['escudo']))

            # Procesar partidos terminados
            df_p = pd.read_sql_query("SELECT * FROM partidos WHERE goles_l IS NOT NULL", conn)
            for _, f in df_p.iterrows():
                # Limpiar nombres de los equipos en los partidos también
                l = str(f['local']).replace("('", "").replace("',)", "").replace("'", "").strip()
                v = str(f['visitante']).replace("('", "").replace("',)", "").replace("'", "").strip()
                
                if l in stats and v in stats:
                    gl, gv = int(f['goles_l']), int(f['goles_v'])
                    stats[l]['PJ']+=1; stats[v]['PJ']+=1
                    stats[l]['GF']+=gl; stats[l]['GC']+=gv
                    stats[v]['GF']+=gv; stats[v]['GC']+=gl
                    if gl > gv: stats[l]['PTS']+=3
                    elif gv > gl: stats[v]['PTS']+=3
                    else: stats[l]['PTS']+=1; stats[v]['PTS']+=1

            # Crear DataFrame final
            df_f = pd.DataFrame.from_dict(stats, orient='index').reset_index()
            df_f.columns = ['Equipo', 'PJ', 'PTS', 'GF', 'GC'] # Nombre cambiado a 'Equipo'
            df_f['DG'] = df_f['GF'] - df_f['GC']
            df_f = df_f.sort_values(by=['PTS', 'DG', 'GF'], ascending=False).reset_index(drop=True)
            df_f.insert(0, 'POS', range(1, len(df_f) + 1))

            # --- RENDERIZADO HTML ---
            # CSS para que la tabla se vea épica y no como texto plano
            st.markdown("""
                <style>
                    .tabla-posiciones { width: 100%; border-collapse: collapse; margin-top: 10px; font-family: sans-serif; }
                    .tabla-posiciones th { background-color: #f8f9fa; color: #333; padding: 10px; border-bottom: 2px solid #dee2e6; }
                    .tabla-posiciones td { padding: 12px; border-bottom: 1px solid #eee; text-align: center; color: #444; }
                    .escudo-tabla { width: 30px; height: 30px; object-fit: contain; vertical-align: middle; margin-right: 10px; }
                    .celda-equipo { display: flex; align-items: center; justify-content: flex-start; font-weight: bold; }
                </style>
            """, unsafe_allow_html=True)

            html = '<table class="tabla-posiciones"><thead><tr><th>POS</th><th style="text-align:left">Equipo</th><th>PTS</th><th>PJ</th><th>DG</th></tr></thead><tbody>'
            
            for _, r in df_f.iterrows():
                url = escudos_dict.get(r['Equipo'])
                # Lógica: Si hay URL de Cloudinary ponemos la imagen, si no, un espacio
                if url and str(url) != 'None' and str(url).strip() != "":
                    img_tag = f'<img src="{url}" class="escudo-tabla">'
                else:
                    img_tag = '<div style="width:30px; display:inline-block;"></div>'
                
                html += f"""
                <tr>
                    <td>{r['POS']}</td>
                    <td><div class="celda-equipo">{img_tag} {r['Equipo']}</div></td>
                    <td><b>{r['PTS']}</b></td>
                    <td>{r['PJ']}</td>
                    <td>{r['DG']}</td>
                </tr>
                """
            
            # FINALMENTE: Renderizamos la tabla como HTML real
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


  
  
# --- TAB: GESTIÓN ADMIN (Versión Final Pulida) ---
if rol == "admin":
    with tabs[2]:
        st.header("⚙️ Panel de Control Admin")
        
        # --- 1. SECCIÓN DE APROBACIONES ---
        st.subheader("📩 Equipos por Aprobar")
        with get_db_connection() as conn:
            pend = pd.read_sql_query("SELECT * FROM equipos WHERE estado='pendiente'", conn)
            aprobados_count = len(pd.read_sql_query("SELECT 1 FROM equipos WHERE estado='aprobado'", conn))
            st.write(f"**Progreso: {aprobados_count}/32 Equipos**")
        
        if not pend.empty:
            for _, r in pend.iterrows():
                with st.container():
                    col_data, col_btn = st.columns([2, 1])
                    prefijo = str(r.get('prefijo', '')).replace('+', '')
                    wa_link = f"https://wa.me/{prefijo}{r['celular']}"
                    
                    with col_data:
                        # Link con emoji verde
                        st.markdown(f"**{r['nombre']}** \n<a href='{wa_link}' style='color: #25D366; text-decoration: none; font-weight: bold;'>🟢 📞 Contactar DT</a>", unsafe_allow_html=True)
                    
                    with col_btn:
                        if st.button(f"✅ Aprobar", key=f"aprob_{r['nombre']}", use_container_width=True):
                            with get_db_connection() as conn:
                                conn.execute("UPDATE equipos SET estado='aprobado' WHERE nombre=?", (r['nombre'],))
                                conn.commit()
                            st.rerun()
                    st.markdown("---") 
        else:
            st.info("No hay equipos pendientes.")

        st.divider()

        # --- 2. SELECCIÓN DE TAREA (Con persistencia de estado) ---
        # Usamos 'key' para que Streamlit recuerde la selección al recargar la página
        opcion_admin = st.radio(
            "Selecciona Tarea:", 
            ["⚽ Resultados", "🛠️ Directorio de Equipos"], 
            horizontal=True,
            key="admin_tab_selected" 
        )
        st.divider()

        if opcion_admin == "⚽ Resultados":
            st.subheader("🏁 Gestión de Marcadores")
            with get_db_connection() as conn:
                df_adm = pd.read_sql_query("SELECT * FROM partidos ORDER BY jornada ASC, id ASC", conn)
            
            if df_adm.empty:
                st.info("El calendario aún no ha sido generado.")
            else:
                jornadas = sorted(df_adm['jornada'].unique())
                mini_tabs = st.tabs([f"J{j}" for j in jornadas])
                for i, j_num in enumerate(jornadas):
                    with mini_tabs[i]:
                        partidos_j = df_adm[df_adm['jornada'] == j_num]
                        for _, p in partidos_j.iterrows():
                            with st.expander(f"{p['local']} vs {p['visitante']}"):
                                # Aquí va tu lógica de marcadores (inputs y botón guardar)
                                pass

        elif opcion_admin == "🛠️ Directorio de Equipos":
            st.subheader("📋 Directorio de Equipos")
            try:
                with get_db_connection() as conn:
                    df_maestro = pd.read_sql_query("SELECT * FROM equipos", conn)
                
                if df_maestro.empty:
                    st.warning("No hay equipos registrados.")
                else:
                    for _, eq in df_maestro.iterrows():
                        pref = str(eq.get('prefijo', ''))
                        cel = str(eq.get('celular', ''))
                        pin = str(eq.get('pin', 'N/A'))
                        wa_url = f"https://wa.me/{pref.replace('+','')}{cel}"
                        
                        # PIN estilizado para evitar el fondo negro
                        pin_html = f'<span style="background-color: white; color: black; border: 1px solid #ddd; padding: 2px 6px; border-radius: 4px; font-family: monospace; font-weight: bold;">{pin}</span>'
                        
                        st.markdown(f"""
                        **{eq['nombre']}** | 🔑 PIN: {pin_html}  
                        📞 {pref} {cel} | [💬 WhatsApp DT]({wa_url})
                        """, unsafe_allow_html=True)
                        st.markdown("---")
                    
                    st.subheader("✏️ Corregir Datos")
                    equipo_sel = st.selectbox("Selecciona equipo:", df_maestro['nombre'].tolist())
                    datos_sel = df_maestro[df_maestro['nombre'] == equipo_sel].iloc[0]
                    
                    with st.form("edit_master_form"):
                        c1, c2 = st.columns(2)
                        new_name = st.text_input("Nombre", datos_sel['nombre'])
                        new_pref = c1.text_input("Prefijo", str(datos_sel.get('prefijo', '')))
                        new_cel = c2.text_input("Celular", str(datos_sel.get('celular', '')))
                        new_pin = st.text_input("PIN", str(datos_sel.get('pin', '')))
                        
                        if st.form_submit_button("💾 Guardar Cambios", use_container_width=True):
                            with get_db_connection() as conn:
                                conn.execute("""
                                    UPDATE equipos SET nombre=?, prefijo=?, celular=?, pin=? WHERE nombre=?
                                """, (new_name, new_pref, new_cel, new_pin, equipo_sel))
                                conn.commit()
                            st.success("Cambios guardados")
                            st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

        # --- 3. ACCIONES FINALES ---
        st.divider()
        c_ini, c_res = st.columns(2)
        with c_ini:
            if st.button("🚀 INICIAR TORNEO", use_container_width=True):
                # Tu función generar_calendario()
                st.rerun()
        with c_res:
            if st.button("🚨 REINICIAR", use_container_width=True):
                with get_db_connection() as conn:
                    conn.execute("DROP TABLE IF EXISTS equipos")
                    conn.execute("DROP TABLE IF EXISTS partidos")
                    conn.commit()
                st.rerun()

























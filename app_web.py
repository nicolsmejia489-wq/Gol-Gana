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
from sqlalchemy import create_engine, text
import time



# 1. CONFIGURACIÓN PRINCIPAL DE SITIO
st.set_page_config(
    page_title="Gol-Gana Pro", 
    layout="centered", 
    initial_sidebar_state="collapsed"
)

# Estilo para móviles y tema claro forzado #st.markdown('<meta name="color-scheme" content="light">', unsafe_allow_html=True)



# 2. CONEXIÓN A NEON (POSTGRESQL) - La parte más importante
@st.cache_resource
def get_db_connection():
    try:
        # Verifica que exista el secreto antes de intentar conectar
        if "connections" not in st.secrets or "postgresql" not in st.secrets["connections"]:
            st.error("❌ Faltan los datos de conexión en .streamlit/secrets.toml")
            return None
            
        db_url = st.secrets["connections"]["postgresql"]["url"]
        
        # Creamos el motor
        engine = create_engine(db_url, pool_pre_ping=True)
        
        # Probamos una conexión rápida para ver si funciona
        with engine.connect() as test_conn:
            pass
            
        return engine
    except Exception as e:
        st.error(f"❌ Error crítico conectando a Neon: {e}")
        return None

# Inicializamos la variable global 'conn'
conn = get_db_connection()

# BLOQUE DE SEGURIDAD: Si la conexión falló, detenemos la app aquí
# Esto evita el error 'NoneType has no attribute connect' más adelante
if conn is None:
    st.warning("La aplicación se detuvo porque no hay conexión a la base de datos.")
    st.stop()



# 3. CONFIGURACIÓN CLOUDINARY
# (Toma las claves de secrets.toml para mayor seguridad)
cloudinary.config(
    cloud_name = st.secrets["cloudinary"]["cloud_name"],
    api_key = st.secrets["cloudinary"]["api_key"],
    api_secret = st.secrets["cloudinary"]["api_secret"],
    secure = True
)

# Constantes de Lógica
ADMIN_PIN = "2025"







#### TEMAS Y COLORES (VERSIÓN DARK MODE) ####
st.markdown("""
    <style>
    /* 1. RESET GLOBAL: Fondo oscuro y texto blanco */
    html, body, .stApp, [data-testid="stAppViewContainer"], .st-emotion-cache-1h9usn1 {
        background-color: #0e1117 !important; /* Color fondo estándar oscuro */
        color: white !important;
    }

    /* 2. TEXTO: Todo a blanco */
    h1, h2, h3, h4, h5, h6, p, span, label, div, b, .stMarkdown, [data-testid="stWidgetLabel"] p, .caption {
        color: white !important;
        -webkit-text-fill-color: white !important;
    }

    /* 3. BOTONES: Fondo gris oscuro, texto blanco */
    div.stButton > button, 
    div.stFormSubmitButton > button, 
    [data-testid="baseButton-secondary"], 
    [data-testid="baseButton-primary"] {
        background-color: #262730 !important;
        color: white !important;
        border: 1px solid #4f4f4f !important;
        border-radius: 20px !important; /* Mantenemos tu radio de 20px */
        width: 100%;
        height: 3em;
        font-weight: bold !important;
        -webkit-text-fill-color: white !important;
    }

    div.stButton > button:active, div.stFormSubmitButton > button:active {
        background-color: #FFD700 !important; /* Dorado al pulsar */
        color: black !important;
        -webkit-text-fill-color: black !important;
        border-color: #FFD700 !important;
    }

    /* 4. INPUTS Y CAJAS DE TEXTO */
    input[type="text"], input[type="password"], textarea, div[data-baseweb="select"] > div {
        background-color: #262730 !important;
        color: white !important;
        border: 1px solid #4f4f4f !important;
        -webkit-text-fill-color: white !important;
    }

    /* 5. FIX PARA DESPLEGABLES (Menú flotante oscuro) */
    div[data-baseweb="popover"], 
    div[data-baseweb="menu"], 
    ul[role="listbox"] {
        background-color: #262730 !important;
        border: 1px solid #444 !important;
    }

    li[role="option"], 
    li[role="option"] div, 
    li[role="option"] span {
        background-color: #262730 !important;
        color: white !important;
        -webkit-text-fill-color: white !important;
    }

    /* Color al seleccionar opción */
    li[role="option"]:hover, 
    li[role="option"]:active, 
    li[role="option"][aria-selected="true"] {
        background-color: #FFD700 !important;
        color: black !important;
        -webkit-text-fill-color: black !important;
    }

    /* Flechita del selectbox en blanco */
    div[data-baseweb="select"] svg {
        fill: white !important;
    }

    /* 6. EXPANDERS */
    [data-testid="stExpander"] {
        background-color: #262730 !important;
        border: 1px solid #444 !important;
        color: white !important;
    }
    div[data-testid="stExpander"] div[role="button"] p { 
        font-size: 1.1rem; 
        font-weight: bold; 
        color: white !important;
    }

    /* 7. TABLAS MÓVILES */
    .mobile-table { 
        width: 100%; border-collapse: collapse; font-size: 12px; 
        background-color: #0e1117 !important; color: white !important;
    }
    .mobile-table th { background: #262730 !important; color: #FFD700 !important; padding: 8px; border-bottom: 2px solid #444; }
    .mobile-table td { padding: 8px; border-bottom: 1px solid #333; color: white !important; }
    .team-cell { text-align: left !important; display: flex; align-items: center; color: white !important; }

    /* 8. CAJAS DE PARTIDO (Estilo tarjeta oscura) */
    .match-box { 
        border: 1px solid #444; padding: 15px; border-radius: 10px; 
        margin-bottom: 15px; background: #1c1c1c !important; color: white !important;
    }

    /* WHATSAPP BUTTON */
    .wa-btn { 
        display: inline-block; background-color: #25D366; color: white !important; 
        padding: 10px; border-radius: 8px; text-decoration: none; 
        font-weight: bold; width: 100%; text-align: center;
        -webkit-text-fill-color: white !important;
    }
    
    * { -webkit-tap-highlight-color: transparent !important; }
    </style>
""", unsafe_allow_html=True)



############# FIN COLORES







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
#with c_nav2:
 #   if st.button("🔄 Refrescar"): 
  #      st.rerun()

# --- CAMPO DE PIN Y BOTÓN DE ENTRAR ---
pin_input = st.text_input("🔑 PIN de Acceso", value=st.session_state.pin_usuario, type="password")
btn_entrar = st.button("🔓 Entrar", use_container_width=True)





# --- OBTENER FASE ACTUAL (Versión Neon) ---
try:
    with conn.connect() as connection:
        # Usamos text() para la consulta SQL segura
        # Nota: En Neon la columna se llama 'clave', no 'llave'
        query_fase = text("SELECT valor FROM config WHERE clave = 'fase_actual'")
        result = connection.execute(query_fase)
        
        # .scalar() obtiene el valor limpio directamente
        fase_actual = result.scalar()
        
        if not fase_actual:
            fase_actual = "inscripcion" # Valor por defecto si falla
except Exception as e:
    st.error(f"Error al leer la fase: {e}")
    fase_actual = "inscripcion"

    

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
        st.header("👑")
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





# --- TAB: CLASIFICACIÓN ---
with tabs[0]:
    # YA NO usamos 'with get_db_connection() as conn:'. 
    # Usamos la variable global 'conn' directamente.

    # 1. Aseguramos traer el escudo
    try:
        df_eq = pd.read_sql_query("SELECT nombre, escudo FROM equipos WHERE estado = 'aprobado'", conn)
        
        if df_eq.empty: 
            st.info("No hay equipos todavía.")
        else:
            mapa_escudos = dict(zip(df_eq['nombre'], df_eq['escudo']))
            
            stats = {e: {'PJ':0, 'PTS':0, 'GF':0, 'GC':0} for e in df_eq['nombre']}
            
            # Consultamos partidos jugados
            df_p = pd.read_sql_query("SELECT * FROM partidos WHERE goles_l IS NOT NULL", conn)
            
            for _, f in df_p.iterrows():
                # Validación extra para evitar errores si hay datos sucios
                if f['local'] in stats and f['visitante'] in stats:
                    l, v = f['local'], f['visitante']
                    # En Postgres los enteros vienen bien, pero forzamos int por seguridad
                    gl = int(f['goles_l'])
                    gv = int(f['goles_v'])
                    
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

            # --- ESTRUCTURA ORIGINAL MANTENIDA ---
            html = '<table class="mobile-table"><thead><tr><th>POS</th><th style="text-align:left">EQ</th><th>PTS</th><th>PJ</th><th>GF</th><th>GC</th><th>DG</th></tr></thead><tbody>'
            
            for _, r in df_f.iterrows():
                url = mapa_escudos.get(r['EQ'])
                
                if url:
                    prefijo_img = f'<img src="{url}" style="width:20px; vertical-align:middle; margin-right:5px;">'
                else:
                    prefijo_img = '<span style="margin-right:5px;">🛡️</span>'
                
                html += f"<tr><td>{r['POS']}</td><td class='team-cell'>{prefijo_img}{r['EQ']}</td><td><b>{r['PTS']}</b></td><td>{r['PJ']}</td><td>{r['GF']}</td><td>{r['GC']}</td><td>{r['DG']}</td></tr>"
            
            st.markdown(html + "</tbody></table>", unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Error cargando tabla de posiciones: {e}")
        
            


            

# --- TAB: REGISTRO (Versión Neon / SQLAlchemy) ---
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
                
                # Subida a Cloudinary
                if d['escudo_obj']:
                    with st.spinner("Subiendo..."):
                        try:
                            res = cloudinary.uploader.upload(d['escudo_obj'], folder="escudos_pendientes")
                            url_temporal = res['secure_url']
                        except Exception as e: 
                            st.error(f"Error subiendo imagen: {e}")
                
                # Inserción en NEON
                try:
                    with conn.connect() as db:
                        query_insert = text("""
                            INSERT INTO equipos (nombre, celular, prefijo, pin, escudo, estado) 
                            VALUES (:n, :c, :p, :pi, :e, 'pendiente')
                        """)
                        db.execute(query_insert, {
                            "n": d['n'], 
                            "c": d['wa'], 
                            "p": d['pref'], 
                            "pi": d['pin'], 
                            "e": url_temporal
                        })
                        db.commit()
                    
                    st.session_state.reg_estado = "exito"
                    st.rerun()
                except Exception as e:
                    st.error(f"Error guardando en base de datos: {e}")

            if c2.button("✏️ Editar"): 
                st.session_state.reg_estado = "formulario"
                st.rerun()
        
        else:
            # --- CSS REFINADO (ADAPTADO A DARK MODE) ---
            st.markdown("""
                <style>
                [data-testid="stFileUploader"] section { padding: 0; background-color: transparent !important; }
                [data-testid="stFileUploader"] section > div:first-child { display: none; }
                
                /* Botón de carga adaptado a OSCURO */
                [data-testid="stFileUploader"] button[data-testid="baseButton-secondary"] { 
                    width: 100%; 
                    background-color: #262730 !important; /* Gris oscuro */
                    color: white !important; 
                    border: 2px solid #FFD700 !important; 
                    padding: 10px; border-radius: 8px; font-weight: bold;
                }
                
                [data-testid="stFileUploaderFileData"] button { width: auto !important; border: none !important; }
                
                /* Texto del botón */
                [data-testid="stFileUploader"] button[data-testid="baseButton-secondary"]::before { 
                    content: "🛡️ SELECCIONAR ESCUDO"; 
                }
                [data-testid="stFileUploader"] button div { display: none; }
                [data-testid="stFileUploader"] small { display: none; }
                
                /* Nombre del archivo en blanco para que se vea */
                [data-testid="stFileUploaderFileName"], [data-testid="stFileUploaderFileData"] p {
                    color: white !important;
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
                        # --- VALIDACIÓN CON NEON ---
                        try:
                            with conn.connect() as db:
                                # Usamos text() y parámetros :nombre
                                query_check = text("SELECT 1 FROM equipos WHERE nombre = :n OR celular = :c")
                                result = db.execute(query_check, {"n": nom, "c": tel}).fetchone()
                                
                                if result: 
                                    st.error("❌ Equipo o teléfono ya registrados.")
                                else:
                                    st.session_state.datos_temp = {
                                        "n": nom, "wa": tel, "pin": pin_r, 
                                        "pref": pais_sel.split('(')[-1].replace(')', ''),
                                        "escudo_obj": archivo_escudo
                                    }
                                    st.session_state.reg_estado = "confirmar"
                                    st.rerun()
                        except Exception as e:
                            st.error(f"Error de conexión: {e}")
                                
                                
### FIN DESARROLLO






    
# --- 5. CALENDARIO Y GESTIÓN DE PARTIDOS (Versión Ultra-Compacta Móvil) ---
elif fase_actual == "clasificacion":
    with tabs[1]:
        st.subheader("📅 Calendario Oficial")
        
        with get_db_connection() as conn:
            df_p = pd.read_sql_query("SELECT * FROM partidos ORDER BY jornada ASC", conn)
            df_escudos = pd.read_sql_query("SELECT nombre, escudo FROM equipos", conn)
            escudos_dict = dict(zip(df_escudos['nombre'], df_escudos['escudo']))
        
        j_tabs = st.tabs(["J1", "J2", "J3"]) # Nombres cortos para ahorrar espacio en móvil
        
        for i, jt in enumerate(j_tabs):
            with jt:
                df_j = df_p[df_p['jornada'] == (i + 1)]
                
                for _, p in df_j.iterrows():
                    res_text = "vs"
                    if p['goles_l'] is not None and p['goles_v'] is not None:
                        try:
                            res_text = f"{int(p['goles_l'])}-{int(p['goles_v'])}"
                        except: res_text = "vs"
                    
                    esc_l = escudos_dict.get(p['local']) or "https://cdn-icons-png.flaticon.com/512/5329/5329945.png"
                    esc_v = escudos_dict.get(p['visitante']) or "https://cdn-icons-png.flaticon.com/512/5329/5329945.png"

                    # --- DISEÑO DE FILA ULTRA COMPACTA ---
                    # Reducimos a 3 columnas principales para evitar que Streamlit las apile en el celular
                    with st.container():
                        col_izq, col_cnt, col_der = st.columns([1, 0.8, 1])
                        
                        # Local: Escudo + Nombre (Markdown pegado)
                        with col_izq:
                            st.markdown(f"<div style='display: flex; align-items: center; gap: 5px; font-size: 12px;'> <img src='{esc_l}' width='25'> <b>{p['local'][:8]}</b> </div>", unsafe_allow_html=True)
                        
                        # Marcador: Centro
                        with col_cnt:
                            st.markdown(f"<div style='text-align: center; background: #31333F; color: white; border-radius: 5px; font-weight: bold; font-size: 12px;'>{res_text}</div>", unsafe_allow_html=True)
                        
                        # Visitante: Nombre + Escudo (Markdown pegado)
                        with col_der:
                            st.markdown(f"<div style='display: flex; align-items: center; justify-content: flex-end; gap: 5px; font-size: 12px;'> <b>{p['visitante'][:8]}</b> <img src='{esc_v}' width='25'> </div>", unsafe_allow_html=True)
                        
                        # Evidencias: Botón minimalista
                        if p['url_foto_l'] or p['url_foto_v']:
                            if st.button(f"📷 Ver", key=f"v_{p['id']}", use_container_width=True):
                                c_ev1, c_ev2 = st.columns(2)
                                if p['url_foto_l']: c_ev1.image(p['url_foto_l'])
                                if p['url_foto_v']: c_ev2.image(p['url_foto_v'])
                    
                    st.divider() # Línea más delgada que st.markdown("---")



                            ###PARTIDOS

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


  
  
# --- TAB: GESTIÓN ADMIN (Versión Neon / SQLAlchemy) ---
if rol == "admin":
    with tabs[2]:
        st.header("⚙️ Panel de Control Admin")
        
        # --- 1. SECCIÓN DE APROBACIONES ---
        st.subheader("📩 Equipos por Aprobar")
        
        # Lectura directa con el motor global 'conn'
        try:
            pend = pd.read_sql_query(text("SELECT * FROM equipos WHERE estado='pendiente'"), conn)
            # Contamos aprobados
            res_count = pd.read_sql_query(text("SELECT count(*) FROM equipos WHERE estado='aprobado'"), conn)
            aprobados_count = res_count.iloc[0,0]
            st.write(f"**Progreso: {aprobados_count}/32 Equipos**")
        except Exception as e:
            st.error(f"Error leyendo base de datos: {e}")
            pend = pd.DataFrame() # DataFrame vacío para no romper el código
        
        if not pend.empty:
            for _, r in pend.iterrows():
                with st.container():
                    col_data, col_btn = st.columns([2, 1])
                    prefijo = str(r.get('prefijo', '')).replace('+', '')
                    wa_link = f"https://wa.me/{prefijo}{r['celular']}"
                    
                    with col_data:
                        st.markdown(f"**{r['nombre']}** \n<a href='{wa_link}' style='color: #25D366; text-decoration: none; font-weight: bold;'>🟢 📞 Contactar DT</a>", unsafe_allow_html=True)
                        st.caption("🖼️ Escudo recibido" if r['escudo'] else "⚠️ Sin escudo")
                    
                    with col_btn:
                        if st.button(f"✅ Aprobar", key=f"aprob_{r['nombre']}", use_container_width=True):
                            url_final = r['escudo']
                            # --- Lógica de IA Cloudinary (Intacta) ---
                            if url_final:
                                with st.spinner("🤖 IA Limpiando Escudo..."):
                                    try:
                                        res_ia = cloudinary.uploader.upload(
                                            url_final,
                                            background_removal="cloudinary_ai",
                                            folder="escudos_limpios",
                                            format="png"
                                        )
                                        url_final = f"{res_ia['secure_url']}?v={int(time.time())}"
                                    except Exception as e:
                                        st.error(f"Error IA: {e}")
                            
                            # --- ACTUALIZACIÓN EN NEON ---
                            with conn.connect() as db:
                                db.execute(
                                    text("UPDATE equipos SET estado='aprobado', escudo=:e WHERE nombre=:n"),
                                    {"e": url_final, "n": r['nombre']}
                                )
                                db.commit()
                            st.rerun()
                st.markdown("---") 
        else:
            st.info("No hay equipos pendientes.")

        st.divider()

        # --- 2. SELECCIÓN DE TAREA ---
        opcion_admin = st.radio("Tarea:", ["⚽ Resultados", "🛠️ Directorio de Equipos"], horizontal=True, key="adm_tab")
        
        if opcion_admin == "🛠️ Directorio de Equipos":
            st.subheader("📋 Directorio de Equipos")
            
            try:
                df_maestro = pd.read_sql_query(text("SELECT * FROM equipos ORDER BY nombre"), conn)
            except:
                df_maestro = pd.DataFrame()

            if not df_maestro.empty:
                for _, eq in df_maestro.iterrows():
                    estado_icon = "✅" if eq['estado'] == 'aprobado' else "⏳"
                    st.markdown(f"{estado_icon} **{eq['nombre']}** | 🔑 {eq['pin']} | 📞 {eq['prefijo']} {eq['celular']}")
                
                # --- SUB-SECCIÓN: GESTIÓN Y EDICIÓN ---
                st.markdown("---")
                st.subheader("✏️ Gestión y Edición")
                equipo_sel = st.selectbox("Selecciona equipo:", df_maestro['nombre'].tolist())
                
                if equipo_sel:
                    datos_sel = df_maestro[df_maestro['nombre'] == equipo_sel].iloc[0]

                    with st.form("edit_master_form"):
                        col1, col2 = st.columns(2)
                        new_name = col1.text_input("Nombre del Equipo", datos_sel['nombre'])
                        new_pin = col2.text_input("PIN de acceso", str(datos_sel['pin']))
                        
                        st.write("**🛡️ Actualizar Escudo**")
                        nuevo_escudo_img = st.file_uploader("Subir nuevo escudo", type=['png', 'jpg', 'jpeg'])
                        quitar_escudo = st.checkbox("❌ Eliminar escudo actual")
                        
                        if st.form_submit_button("💾 Guardar Cambios", use_container_width=True):
                            url_final = datos_sel['escudo']
                            
                            if quitar_escudo:
                                url_final = None
                            elif nuevo_escudo_img:
                                # Lógica simple de subida para no complicar
                                res_std = cloudinary.uploader.upload(nuevo_escudo_img, folder="escudos_limpios")
                                url_final = res_std['secure_url']

                            with conn.connect() as db:
                                db.execute(
                                    text("UPDATE equipos SET nombre=:nn, pin=:np, escudo=:ne WHERE nombre=:viejo"),
                                    {"nn": new_name, "np": new_pin, "ne": url_final, "viejo": equipo_sel}
                                )
                                db.commit()
                            st.success(f"✅ ¡{new_name} actualizado!")
                            st.rerun()

                    # --- SECCIÓN DE PELIGRO ---
                    if st.button(f"✖️ Eliminar: {equipo_sel}", use_container_width=True):
                        with conn.connect() as db:
                            db.execute(text("DELETE FROM equipos WHERE nombre = :n"), {"n": equipo_sel})
                            db.commit()
                        st.error(f"Equipo eliminado.")
                        st.rerun()
            else:
                st.info("No hay equipos registrados.")

        # --- 3. ACCIONES MAESTRAS ---
        st.divider()
        st.subheader("🚀 Control Global")
        
        col_torneo, col_reset = st.columns(2)
        
        with col_torneo:
            if fase_actual == "inscripcion":
                if st.button("🏁 INICIAR TORNEO", use_container_width=True, type="primary"):
                    if aprobados_count >= 2:
                        generar_calendario() # Asegúrate de que esta función también use 'conn'
                        st.rerun()
                    else:
                        st.error("Mínimo 2 equipos aprobados.")
        
        with col_reset:
            if st.button("🚨 REINICIAR TODO", use_container_width=True):
                with conn.connect() as db:
                    # IMPORTANTE: Usamos DELETE, no DROP, para mantener la estructura
                    db.execute(text("DELETE FROM equipos"))
                    db.execute(text("DELETE FROM partidos"))
                    db.execute(text("UPDATE config SET valor='inscripcion' WHERE clave='fase_actual'"))
                    db.commit()
                st.session_state.clear()
                st.rerun()




















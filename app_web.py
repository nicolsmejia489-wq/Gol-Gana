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
import motor_colores
import motor_grafico
from io import BytesIO
import PIL.Image
import requests
import extcolors





# 1. CONFIGURACIÓN PRINCIPAL
st.set_page_config(
    page_title="Gol-Gana Pro", 
    layout="centered", 
    initial_sidebar_state="collapsed"
)


# --- 1. CONEXIÓN (Siempre al principio) ---
try:
    conn = st.connection("postgresql", type="sql")
except Exception as e:
    st.error(f"Error de conexión: {e}")
    conn = None

# --- 2. INICIALIZACIÓN DE VARIABLES (Valores de Respaldo) ---
color_maestro = "#FFD700"  # Dorado por defecto
fondo_url = "https://res.cloudinary.com/dlvczeqlp/image/upload/v1769056355/fondos_dinamicos/fondo_activo_golgana.png"

# --- 3. LÓGICA DE IDENTIDAD (Si hay conexión) ---
if conn is not None:
    try:
        with conn.connect() as db:
            # Buscamos el equipo activo en la configuración
            res_conf = db.execute(text("SELECT valor FROM configuracion WHERE clave = 'equipo_activo'")).fetchone()
            equipo_nombre = res_conf[0] if res_conf else "Sistema"

            # Buscamos el color principal de ese equipo
            res_eq = db.execute(
                text("SELECT color_principal FROM equipos WHERE nombre = :nom"),
                {"nom": equipo_nombre}
            ).fetchone()
            
            if res_eq and res_eq[0]:
                color_maestro = res_eq[0]
                
            # Buscamos el fondo dinámico actual
            res_f = db.execute(text("SELECT valor FROM configuracion WHERE clave = 'fondo_url'")).fetchone()
            if res_f:
                fondo_url = res_f[0]
    except Exception as e:
        pass # Mantiene los valores por defecto si la consulta falla





# --- 2. GESTIÓN DE CONEXIÓN ---
@st.cache_resource
def get_db_connection():
    try:
        if "connections" not in st.secrets or "postgresql" not in st.secrets["connections"]:
            return None
        db_url = st.secrets["connections"]["postgresql"]["url"]
        return create_engine(db_url, pool_pre_ping=True)
    except:
        return None

conn = get_db_connection()

# --- 3. RECUPERACIÓN EXCLUSIVA DEL FONDO ---
# Fondo por defecto (Estadio base)
fondo_actual = "https://res.cloudinary.com/dlvczeqlp/image/upload/v1/assets/fondo_base.jpg"
fondo_url = "https://res.cloudinary.com/dlvczeqlp/image/upload/v1769049958/fondos_dinamicos/fondo_web_v2.png"




if conn:
    try:
        with conn.connect() as db:
            df_config = pd.read_sql(text("SELECT clave, valor FROM configuracion"), db)
            if not df_config.empty:
                row_f = df_config[df_config['clave'] == 'fondo_url']
                if not row_f.empty:
                    fondo_actual = row_f['valor'].values[0]
    except:
        pass




# --- INYECCIÓN DE CSS GLOBAL DINÁMICO ---
plantilla_estilo = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@200;400;700&display=swap');

    /* Fuente y Fondo */
    * { font-family: 'Oswald', sans-serif !important; color: #ffffff !important; }
    
    [data-testid="stAppViewContainer"] {
        background-image: url("URL_FONDO") !important;
        background-size: cover !important;
        background-attachment: fixed !important;
    }

    /* Acentos con el Color del Equipo Insignia */
    [data-testid="stDecoration"] { background: COLOR_MAESTRO !important; }
    
    div[data-baseweb="tab-highlight"] { background-color: COLOR_MAESTRO !important; }
    
    button[data-baseweb="tab"][aria-selected="true"] p { color: COLOR_MAESTRO !important; }

    div.stButton > button { 
        border: 1px solid COLOR_MAESTRO !important; 
        background-color: rgba(0,0,0,0.6) !important;
    }
    
    div.stButton > button:hover { 
        background-color: COLOR_MAESTRO !important; 
        color: #000000 !important; 
    }
</style>
"""

# El único punto de control: Reemplazamos los marcadores con las variables de la DB
css_final = plantilla_estilo.replace("URL_FONDO", fondo_url).replace("COLOR_MAESTRO", color_maestro)
st.markdown(css_final, unsafe_allow_html=True)






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



def generar_calendario():
    import random
    try:
        with conn.connect() as db:
            # 1. LIMPIEZA CRÍTICA: Borramos partidos previos
            # Sin esto, los partidos de intentos fallidos o anteriores se acumulan
            db.execute(text("DELETE FROM partidos"))
            
            # 2. Obtener solo los equipos reales aprobados
            res = db.execute(text("SELECT nombre FROM equipos WHERE estado = 'aprobado' AND nombre != 'Sistema'"))
            equipos = [row[0] for row in res.fetchall()]
            n_reales = len(equipos)

            if n_reales < 2:
                st.error("Se necesitan al menos 2 equipos para generar un calendario.")
                return

            # 3. DETERMINAR CUPOS PARA PLAY-OFFS
            if 25 <= n_reales <= 32: cupos = 16
            elif 16 <= n_reales <= 24: cupos = 8
            elif 8 <= n_reales < 16: cupos = 4
            else: cupos = 2

            # Guardamos los cupos en la tabla 'config'
            db.execute(text("""
                INSERT INTO config (clave, valor) 
                VALUES ('cupos_clasificados', :v) 
                ON CONFLICT (clave) DO UPDATE SET valor = :v
            """), {"v": str(cupos)})

            # 4. PREPARACIÓN ROUND ROBIN
            random.shuffle(equipos)
            equipos_sorteo = equipos.copy()
            
            # Si es impar, añadimos un 'Descanso' (None) para que el algoritmo sea par
            if n_reales % 2 != 0:
                equipos_sorteo.append(None)

            n = len(equipos_sorteo)
            indices = list(range(n))

            # 5. GENERACIÓN DE 3 JORNADAS REALES
            for jor in range(1, 4):
                # Emparejamiento por extremos (1° vs último, 2° vs penúltimo...)
                for i in range(n // 2):
                    idx_l = indices[i]
                    idx_v = indices[n - 1 - i]
                    
                    loc = equipos_sorteo[idx_l]
                    vis = equipos_sorteo[idx_v]

                    # Solo insertamos si ninguno es 'None' (el que descanse no tiene partido)
                    if loc and vis:
                        db.execute(text("""
                            INSERT INTO partidos (local, visitante, jornada, estado) 
                            VALUES (:l, :v, :j, 'Programado')
                        """), {"l": loc, "v": vis, "j": jor})
                
                # ROTACIÓN BERGER (Mantiene el índice 0 fijo y rota el resto)
                # Esto garantiza que NO se repitan partidos en las primeras jornadas
                indices = [indices[0]] + [indices[-1]] + indices[1:-1]

            # 6. ACTUALIZAR FASE Y CONFIRMAR
            db.execute(text("UPDATE config SET valor = 'clasificacion' WHERE clave = 'fase_actual'"))
            db.commit()
            
    except Exception as e:
        st.error(f"Error crítico en el calendario: {e}")
        
###FIN GENERAR CALENDARIO




#####EN DESARROLLO/PRUEBA
# --- FUNCIÓN GRÁFICA: TARJETA DE PARTIDO (MODO LABORATORIO) ---
def renderizar_tarjeta_partido(local, visita, escudo_l, escudo_v, marcador_texto, color_tema, url_fondo):
    if not color_tema: color_tema = "#FFD700"
    
    estilo = f"""
    <style>
        .card-container {{
            position: relative;
            width: 100%;
            
            /* TANTEAR: Ancho máximo en PC. */
            max-width: 840px; 
            
            /* TANTEAR: Altura de la barra en PC. Si quieres que sea mas "gorda", sube a 120px */
            height: 108px;    
            
            /* TANTEAR: El '15px' es el espacio vacio entre una tarjeta y otra */
            margin: 0 auto 15px auto; 
            
            background-image: url('{url_fondo}');
            background-size: 100% 100%;
            background-repeat: no-repeat;
            
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-family: 'Oswald', sans-serif;
            color: white;
            
            /* EFECTO DE SOMBRA / COLOR */
            box-shadow: 
                0 4px 6px -2px rgba(0,0,0,0.5), 
                /* TANTEAR: El '10px' es qué tan difuminado está el color abajo. El '{color_tema}60' es la transparencia (60 es suave, 99 es fuerte) */
                0 2px 10px -3px {color_tema}60; 
            
            /* TANTEAR: El '1px' es el grosor de la línea de color inferior. */
            border-bottom: 1px solid {color_tema}30;

            transition: transform 0.2s, box-shadow 0.2s;
        }}
        
        .card-container:hover {{
            transform: translateY(-2px); 
            box-shadow: 
                0 6px 8px -2px rgba(0,0,0,0.6),
                0 4px 15px -3px {color_tema}80; 
        }}

        /* --- ZONAS (OJO: Las sumas de width deben dar cerca de 100%) --- */
        
        .zona-equipo {{
            /* TANTEAR: Espacio horizontal para Nombre + Escudo. Si subes esto, baja la .zona-centro */
            width: 60%; 
            height: 100%;
            display: flex;
            align-items: center;
            
            /* TANTEAR: Espacio entre el Escudo y el Nombre */
            gap: 3px; 
            overflow: hidden; 
        }}
        
        .zona-centro {{
            /* TANTEAR: Espacio para el marcador. Si los números no caben, sube a 10% o 12% */
            width: 8%; 
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            
            /* TANTEAR: Tamaño del número del marcador en PC */
            font-size: 30px; 
            font-weight: bold;
            text-shadow: 0 2px 4px black;
            color: {color_tema}; 
            padding-top: 6px;
            z-index: 2;
        }}
        
        /* --- TEXTOS --- */
        
        .txt-local {{ 
            text-align: right; width: 100%; 
            
            /* TANTEAR: Tamaño del nombre del equipo en PC. */
            font-size: 17px; 
            font-weight: 500;
            text-transform: uppercase; 
            
            /* TANTEAR: Distancia entre el final del nombre y el marcador central */
            padding-right: 2px; 
            line-height: 1.1; 
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis; letter-spacing: 0.5px;
        }}
        .txt-visit {{ 
            text-align: left; width: 100%; 
            
            /* TANTEAR: Igual que arriba, tamaño del nombre visitante */
            font-size: 17px; 
            font-weight: 500;
            text-transform: uppercase; 
            
            /* TANTEAR: Distancia entre el marcador central y el inicio del nombre */
            padding-left: 2px; 
            line-height: 1.1; 
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis; letter-spacing: 0.5px;
        }}
        
        .logo-img {{
            /* TANTEAR: Tamaño del escudo en PC. Si cambias 46px, cambia min-width también */
            width: 46px; height: 50px; min-width: 50px; 
            object-fit: contain; filter: drop-shadow(0 3px 3px black);
        }}
        
        /* TANTEAR: Relleno izquierdo (distancia del borde izquierdo al primer escudo) */
        .pad-l {{ padding-left: 10px; }}
        
        /* TANTEAR: Relleno derecho (distancia del borde derecho al segundo escudo) */
        .pad-r {{ padding-right: 10px; justify-content: flex-end; }}


        /* --- ¡AQUI EMPIEZA LO IMPORTANTE PARA EL MOVIL! --- */
        @media (max-width: 480px) {{
            
            /* TANTEAR: Altura de la tarjeta en celular. Prueba 90px si se ve muy apretado */
            .card-container {{ height: 84px; }} 
            
            /* TANTEAR: Tamaño de letra en celular. Si los nombres se cortan mucho, baja a 10px */
            .txt-local, .txt-visit {{ font-size: 13px; }} 
            
            /* TANTEAR: Tamaño del escudo en celular. Prueba 30px o 38px */
            .logo-img {{ width: 34px; height: 38px; min-width: 34px; }} 
            
            /* TANTEAR: Tamaño del marcador en celular y ancho de la zona central */
            .zona-centro {{ font-size: 20px; width: 10%; }} 
            
            /* TANTEAR: Ancho para equipos en celular. (43% + 43% + 10% = 96%) */
            .zona-equipo {{ width: 50%; }}
            
            /* TANTEAR: Márgenes laterales en celular. Si están muy pegados al borde, sube a 20px */
            .pad-l {{ padding-left: 15px; }}
            .pad-r {{ padding-right: 15px; }}
        }}
    </style>
    """

    html = f"""
    <div class="card-container">
        <div class="zona-equipo pad-l">
            <img src="{escudo_l}" class="logo-img">
            <div class="txt-local">{local}</div>
        </div>
        <div class="zona-centro">{marcador_texto}</div>
        <div class="zona-equipo pad-r">
            <div class="txt-visit">{visita}</div>
            <img src="{escudo_v}" class="logo-img">
        </div>
    </div>
    """
    return estilo + html
####FIN DESARROLLO/PRUEBA






############FUNCIÓN EN PRUEBA DATOS FUTUROS
def actualizar_historial_post_partido(equipo_local, equipo_visitante, goles_l, goles_v, conn):
    """
    Se ejecuta AUTOMÁTICAMENTE después de guardar un resultado.
    Actualiza la racha y el ganador.
    """
    # 1. Determinar Ganador y Letra de Racha
    if goles_l > goles_v:
        ganador = equipo_local
        res_l, res_v = 'W', 'L' # W=Win, L=Loss
    elif goles_v > goles_l:
        ganador = equipo_visitante
        res_l, res_v = 'L', 'W'
    else:
        ganador = 'Empate'
        res_l, res_v = 'D', 'D' # D=Draw

    with conn.connect() as db:
        # 2. Guardar el ganador explícito en el partido (Facilita consultas futuras del Oráculo)
        # Asumimos que ya tienes el ID del partido o usas los nombres para filtrar
        db.execute(text("""
            UPDATE partidos 
            SET ganador = :g 
            WHERE local = :l AND visitante = :v AND estado = 'Finalizado'
        """), {"g": ganador, "l": equipo_local, "v": equipo_visitante})

        # 3. Actualizar la Racha de los Equipos (Concatenación simple)
        # Esto agrega la nueva letra al final de la cadena existente
        # Para el Local
        db.execute(text("""
            UPDATE equipos 
            SET racha_actual = CONCAT(COALESCE(racha_actual, ''), :r, ',') 
            WHERE nombre = :n
        """), {"r": res_l, "n": equipo_local})

        # Para el Visitante
        db.execute(text("""
            UPDATE equipos 
            SET racha_actual = CONCAT(COALESCE(racha_actual, ''), :r, ',') 
            WHERE nombre = :n
        """), {"r": res_v, "n": equipo_visitante})
        
        db.commit()

#######FUNCIÓN EN PRUEBA








# --- 3. NAVEGACIÓN (Inicialización de Estado) ---
if "reg_estado" not in st.session_state: st.session_state.reg_estado = "formulario"
if "pin_usuario" not in st.session_state: st.session_state.pin_usuario = ""

####################PORTADA EN PRUEBA

URL_PORTADA = "https://res.cloudinary.com/dlvczeqlp/image/upload/v1769050565/a906a330-8b8c-4b52-b131-8c75322bfc10_hwxmqb.png" 



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

    
# --- 1. ESTADO INICIAL ---
rol = "espectador"
equipo_usuario = None

# --- 2. BOTÓN ENTRAR (Solo guarda y recarga) ---
if btn_entrar:
    st.session_state.pin_usuario = pin_input
    st.rerun()

# --- 3. VALIDACIÓN CENTRALIZADA ---
# Si hay un PIN en memoria, validamos quién es (Admin o DT)
if st.session_state.pin_usuario:
    
    # A. Es Admin?
    if st.session_state.pin_usuario == ADMIN_PIN:
        rol = "admin"

    # B. Es DT? (Consultamos Neon)
    else:
        try:
            with conn.connect() as db:
                query = text("SELECT nombre FROM equipos WHERE pin = :p AND estado = 'aprobado'")
                result = db.execute(query, {"p": st.session_state.pin_usuario}).fetchone()
                
                if result:
                    rol = "dt"
                    equipo_usuario = result[0]
                else:
                    # PIN incorrecto: Avisamos y borramos
                    st.toast("⚠️ PIN incorrecto o no aprobado", icon="❌")
                    st.session_state.pin_usuario = ""
                    time.sleep(1)
                    st.rerun()
        except Exception as e:
            st.error(f"Error de conexión: {e}")

# (Opcional para debug: Si ves esto, es que el rol ya cambió)
# st.write(f"DEBUG: Rol asignado -> {rol}")





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
        st.subheader("📅 Calendario Oficial")
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
            st.info("👋 ¡Hola DT! Tu equipo ya está aprobado. El torneo aún no comienza, espera a que se genere el calendario.")
        else:
            st.success("✅ Torneo en curso. Aquí podrás reportar tus marcadores.")
            # Próximo paso: Formulario de reporte para el DT
            
    else:
        # Lo que ve alguien que no ha puesto un PIN válido
        st.markdown("### 🔒 Acceso Restringido")
        st.info("Esta sección es solo para **Administradores** o **Directores Técnicos** registrados.")
        st.write("Por favor, ingresa tu PIN en la parte superior para acceder a las funciones de gestión.")





# --- TAB: CLASIFICACIÓN (Versión Alineación Elite) ---
with tabs[0]:
    try:
        # A. VALIDACIÓN DE SEGURIDAD
        if 'color_maestro' not in locals() and 'color_maestro' not in globals():
            color_maestro = "#FFD700" 

        # 1. Obtener datos de Neon
        df_eq = pd.read_sql_query("SELECT nombre, escudo FROM equipos WHERE estado = 'aprobado'", conn)
        
        if df_eq.empty:
            st.info("No hay equipos todavía.")
        else:
            mapa_escudos = dict(zip(df_eq['nombre'], df_eq['escudo']))
            stats = {e: {'PJ':0, 'PTS':0, 'GF':0, 'GC':0} for e in df_eq['nombre']}
            df_p = pd.read_sql_query("SELECT * FROM partidos WHERE goles_l IS NOT NULL", conn)
            
            for _, f in df_p.iterrows():
                if f['local'] in stats and f['visitante'] in stats:
                    l, v = f['local'], f['visitante']
                    gl, gv = int(f['goles_l']), int(f['goles_v'])
                    stats[l]['PJ'] += 1; stats[v]['PJ'] += 1
                    stats[l]['GF'] += gl; stats[l]['GC'] += gv
                    stats[v]['GF'] += gv; stats[v]['GC'] += gl
                    
                    if gl > gv: 
                        stats[l]['PTS'] += 3
                    elif gv > gl: 
                        stats[v]['PTS'] += 3
                    else: 
                        stats[l]['PTS'] += 1; stats[v]['PTS'] += 1
            
            df_f = pd.DataFrame.from_dict(stats, orient='index').reset_index()
            df_f.columns = ['EQ', 'PJ', 'PTS', 'GF', 'GC']
            df_f['DG'] = df_f['GF'] - df_f['GC']
            df_f = df_f.sort_values(by=['PTS', 'DG', 'GF'], ascending=False).reset_index(drop=True)
            df_f.insert(0, 'POS', range(1, len(df_f) + 1))

            # 2. DISEÑO DE TABLA (Espaciado Estandarizado)
            plantilla_tabla = """
            <style>
                .tabla-pro { 
                    width: 100%; border-collapse: collapse; table-layout: fixed; 
                    background-color: rgba(0,0,0,0.5); font-family: 'Oswald', sans-serif; 
                    border: 1px solid COLOR_MAESTRO !important;
                }
                .tabla-pro th { 
                    background-color: #111; color: #ffffff !important; 
                    padding: 4px 1px; font-size: 11px; 
                    border-bottom: 2px solid COLOR_MAESTRO !important; 
                    text-align: center; height: 32px !important; 
                }
                .tabla-pro td { 
                    padding: 0px 1px !important; text-align: center; 
                    vertical-align: middle !important; border-bottom: 1px solid #222; 
                    font-size: 13px; color: white; height: 30px !important; 
                }
                /* Contenedor del escudo para estandarizar espacio */
                .escudo-wrapper {
                    display: inline-block;
                    width: 25px; /* Ancho fijo para el área del escudo */
                    text-align: center;
                    margin-right: 12px; /* Espacio estándar hacia el texto */
                    vertical-align: middle;
                }
            </style>
            """
            
            estilo_tabla_final = plantilla_tabla.replace("COLOR_MAESTRO", color_maestro)

            tabla_html = '<table class="tabla-pro"><thead><tr>'
            tabla_html += '<th style="width:8%">POS</th>'
            tabla_html += '<th style="width:47%; text-align:left; padding-left:10px">EQUIPO</th>'
            tabla_html += '<th style="width:10%">PTS</th>'
            tabla_html += '<th style="width:9%">PJ</th>'
            tabla_html += '<th style="width:9%">GF</th>'
            tabla_html += '<th style="width:9%">GC</th>'
            tabla_html += '<th style="width:8%">DG</th>'
            tabla_html += '</tr></thead><tbody>'

            for _, r in df_f.iterrows():
                url = mapa_escudos.get(r['EQ'])
                
                # Definimos el contenido del escudo
                if url:
                    img_html = f'<img src="{url}" style="height:22px; width:22px; object-fit:contain; vertical-align:middle;">'
                else:
                    img_html = '<span style="font-size:16px;"> </span>'
                
                # Envolvemos el escudo en el contenedor de ancho fijo
                escudo_final = f'<div class="escudo-wrapper">{img_html}</div>'
                
                tabla_html += "<tr>"
                tabla_html += f"<td>{r['POS']}</td>"
                # Aplicamos el escudo y el nombre con el nuevo wrapper
                tabla_html += f"<td style='text-align:left; padding-left:10px; font-weight:bold; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;'>"
                tabla_html += f"{escudo_final}{r['EQ']}</td>"
                
                tabla_html += f"<td style='color:{color_maestro}; font-weight:bold;'>{r['PTS']}</td>"
                tabla_html += f"<td>{r['PJ']}</td>"
                tabla_html += f"<td>{r['GF']}</td>"
                tabla_html += f"<td>{r['GC']}</td>"
                tabla_html += f"<td style='font-size:11px; color:#888;'>{r['DG']}</td>"
                tabla_html += "</tr>"

            tabla_html += "</tbody></table>"

            st.markdown(estilo_tabla_final + tabla_html, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Error al cargar la clasificación: {e}")
        

            

# --- TAB: REGISTRO (Versión Restaurada con Guardado Real en Neon) ---
if fase_actual == "inscripcion":
    with tabs[1]:
        # 1. Inicialización de estados
        if "datos_temp" not in st.session_state:
            st.session_state.datos_temp = {"n": "", "wa": "", "pin": "", "pref": "+57", "escudo_obj": None}
        if "reg_estado" not in st.session_state:
            st.session_state.reg_estado = "formulario"

        # --- ESTADO: ÉXITO ---
        if st.session_state.reg_estado == "exito":
            st.success("✅ ¡Inscripción recibida! Se estara revisando tu solicitud.")
            if st.button("Nuevo Registro"): 
                st.session_state.datos_temp = {"n": "", "wa": "", "pin": "", "pref": "+57", "escudo_obj": None}
                st.session_state.reg_estado = "formulario"
                st.rerun()
        
        # --- ESTADO: CONFIRMAR ---
        elif st.session_state.reg_estado == "confirmar":
            d = st.session_state.datos_temp
            st.warning("⚠️ **Confirma tus datos antes de enviar:**")
            
            col_info, col_img = st.columns([2, 1])
            with col_info:
                st.write(f"**Equipo:** {d['n']}")
                st.write(f"**WhatsApp:** {d['pref']} {d['wa']}")
                st.write(f"**PIN de Acceso:** {d['pin']}") # Visible como pediste
            
            with col_img:
                if d['escudo_obj']: st.image(d['escudo_obj'], width=100)
                else: st.write("🛡️ Sin escudo")

            c1, c2 = st.columns(2)
            
            # --- BOTÓN DE CONFIRMACIÓN (Aquí es donde se guarda en la DB) ---
            if c1.button("✅ Confirmar y Enviar"):
                url_escudo = None
                
                # 1. Subida a Cloudinary
                if d['escudo_obj']:
                    with st.spinner("Subiendo escudo..."):
                        try:
                            res = cloudinary.uploader.upload(d['escudo_obj'], folder="escudos_pendientes")
                            url_escudo = res['secure_url']
                        except Exception as e: 
                            st.error(f"Error en Cloudinary: {e}")
                
                # 2. Inserción en Neon (Postgres)
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
                            "e": url_escudo
                        })
                        db.commit()
                    
                    st.session_state.reg_estado = "exito"
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar en la base de datos: {e}")

            if c2.button("✏️ Editar Datos"): 
                st.session_state.reg_estado = "formulario"
                st.rerun()
        
        # --- ESTADO: FORMULARIO ---
        else:
            d = st.session_state.datos_temp
            
            with st.form("reg_preventivo"):
                nom = st.text_input("Nombre Equipo", value=d['n']).strip()
                
                paises = {"Colombia": "+57", "EEUU": "+1", "México": "+52", "Ecuador": "+593", "Panamá": "+507", "Perú": "+51", "Argentina": "+54", "Chile": "+56", "Venezuela": "+58"}
                opciones = [f"{p} ({pref})" for p, pref in paises.items()]
                
                try:
                    idx_pref = [d['pref'] in opt for opt in opciones].index(True)
                except:
                    idx_pref = 0

                pais_sel = st.selectbox("País", opciones, index=idx_pref)
                tel = st.text_input("WhatsApp", value=d['wa']).strip()
                # PIN Visible
                pin_r = st.text_input("PIN de Acceso (4 dígitos)", max_chars=4, value=d['pin']).strip()
                
                archivo_escudo = st.file_uploader("🛡️ Escudo (Opcional)", type=['png', 'jpg', 'jpeg'])
                
                if st.form_submit_button("Siguiente", use_container_width=True):
                    if not nom or not tel or len(pin_r) < 4: 
                        st.error("Completa todos los campos correctamente.")
                    else:
                        # --- VALIDACIÓN DE DUPLICADOS CONTRA EQUIPOS APROBADOS ---
                        try:
                            with conn.connect() as db:
                                query = text("SELECT nombre, pin FROM equipos WHERE (nombre = :n OR pin = :p) AND estado = 'aprobado'")
                                check = db.execute(query, {"n": nom, "p": pin_r}).fetchone()
                                
                                if check:
                                    if check[0].lower() == nom.lower():
                                        st.error(f"❌ El nombre '{nom}' ya está ocupado.")
                                    else:
                                        st.error("❌ Este PIN ya está en uso. Elige otro.")
                                else:
                                    # Guardamos temporalmente y vamos a Confirmar
                                    st.session_state.datos_temp = {
                                        "n": nom, "wa": tel, "pin": pin_r, 
                                        "pref": pais_sel.split('(')[-1].replace(')', ''),
                                        "escudo_obj": archivo_escudo if archivo_escudo else d['escudo_obj']
                                    }
                                    st.session_state.reg_estado = "confirmar"
                                    st.rerun()
                        except Exception as e:
                            st.error(f"Error de conexión: {e}")






# --- 5. CALENDARIO Y GESTIÓN DE PARTIDOS (DISEÑO PREMIUM) ---
elif fase_actual == "clasificacion":
    with tabs[1]:
        
        # --- CONFIGURACIÓN GRÁFICA ---
        # 🔴 PEGA AQUÍ LA URL DE TU IMAGEN HORIZONTAL DE CLOUDINARY
        URL_PLANTILLA_FONDO = "https://res.cloudinary.com/..../tu_imagen_barra.png" 
        
        placeholder_escudo = "https://cdn-icons-png.flaticon.com/512/33/33736.png"

        try:
            # Lectura de datos
            df_p = pd.read_sql_query("SELECT * FROM partidos ORDER BY jornada ASC", conn)
            df_escudos = pd.read_sql_query("SELECT nombre, escudo FROM equipos", conn)
            escudos_dict = dict(zip(df_escudos['nombre'], df_escudos['escudo']))
        except Exception as e:
            st.error(f"Error al cargar partidos: {e}")
            df_p = pd.DataFrame()

        if not df_p.empty:
            j_tabs = st.tabs(["Jornada 1", "Jornada 2", "Jornada 3"])
            
            for i, jt in enumerate(j_tabs):
                with jt:
                    # Filtramos por jornada
                    df_j = df_p[df_p['jornada'] == (i + 1)]
                    
                    if df_j.empty:
                        st.info("No hay partidos programados para esta fecha.")
                    
                    # BUCLE DE GENERACIÓN DE TARJETAS
                    for _, p in df_j.iterrows():
                        
                        # 1. Preparar Escudos
                        esc_l = escudos_dict.get(p['local']) or placeholder_escudo
                        esc_v = escudos_dict.get(p['visitante']) or placeholder_escudo
                        
                        # 2. Preparar Marcador
                        if p['goles_l'] is not None and p['goles_v'] is not None:
                            txt_marcador = f"{int(p['goles_l'])} - {int(p['goles_v'])}"
                        else:
                            txt_marcador = "VS"
                        
                        # 3. Construir la Tarjeta HTML
                        html_tarjeta = renderizar_tarjeta_partido(
                            local=p['local'],
                            visita=p['visitante'],
                            escudo_l=esc_l,
                            escudo_v=esc_v,
                            marcador_texto=txt_marcador,
                            color_tema=color_maestro, # Usa el color del equipo activo
                            url_fondo=URL_PLANTILLA_FONDO
                        )
                        
                        # 4. Renderizar en Pantalla
                        st.markdown(html_tarjeta, unsafe_allow_html=True)
                        
                        # 5. (Opcional) Botón de Evidencia discreto debajo de la tarjeta
                        if p.get('url_foto_l') or p.get('url_foto_v'):
                            with st.expander(f"📷 Ver evidencia {p['local']} vs {p['visitante']}"):
                                c1, c2 = st.columns(2)
                                if p['url_foto_l']: c1.image(p['url_foto_l'])
                                if p['url_foto_v']: c2.image(p['url_foto_v'])
                            st.write("") # Espacio extra

        else:
            st.info("El calendario se mostrará cuando inicie el torneo.")




            

# --- TAB: MIS PARTIDOS (SOLO PARA DT) ---
if rol == "dt":
    with tabs[2]:
        st.subheader(f"🏟️ Panel de Director Técnico: {equipo_usuario}")
        
        # 🔴 RECUERDA: Define tu URL de fondo aquí o al inicio
        URL_FONDO_GESTION = "https://res.cloudinary.com/..../tu_imagen_barra.png" 

        # --- ESTILOS CSS ESPECÍFICOS PARA GESTIÓN ---
        # Definimos clases para compactar y separar
        st.markdown(f"""
        <style>
            /* BLOQUE 1: EL CONTENEDOR DE INFORMACIÓN DEBAJO DE LA TARJETA */
            .info-block {{
                /* TANTEAR: Color de fondo del bloque de estado/whatsapp */
                background-color: rgba(0,0,0,0.2); 
                
                /* TANTEAR: Redondeo de las esquinas inferiores (para que encaje con la tarjeta si quieres) */
                border-radius: 8px; 
                
                /* TANTEAR: Espacio interno del texto */
                padding: 10px; 
                
                /* TANTEAR: Margen negativo para "chupar" este bloque hacia arriba y pegarlo a la tarjeta */
                margin-top: -15px; 
                
                /* TANTEAR: Margen abajo antes de llegar al desplegable de subir foto */
                margin-bottom: 5px; 
                
                text-align: center;
                border: 1px solid {color_maestro}30;
                border-top: none; /* Sin borde arriba para que parezca unido a la tarjeta */
            }}

            /* BLOQUE 2: EL TEXTO DE ESTADO */
            .status-text {{
                /* TANTEAR: Tamaño de letra del estado (Finalizado, etc) */
                font-size: 14px; 
                margin-bottom: 8px; /* Espacio entre el estado y el botón de WhatsApp */
            }}

            /* BLOQUE 3: EL BOTÓN DE WHATSAPP */
            .wa-button {{
                /* TANTEAR: Color de fondo verde WhatsApp */
                background-color: #25D366; 
                color: white; 
                
                /* TANTEAR: Relleno del botón (Gordura) */
                padding: 6px 12px; 
                
                border-radius: 5px; 
                text-decoration: none; 
                font-weight: bold; 
                
                /* TANTEAR: Tamaño de letra del botón */
                font-size: 13px; 
                
                display: inline-flex; 
                align-items: center; 
                gap: 5px;
                transition: background 0.3s;
            }}
            .wa-button:hover {{ background-color: #1DA851; color: white; }}

            /* BLOQUE 4: EL SEPARADOR DE JORNADAS (LA LÍNEA GRUESA) */
            .mega-divider {{
                /* TANTEAR: Altura de la línea divisoria */
                height: 2px; 
                
                /* TANTEAR: Color de la línea (Degradado con el color de tu equipo) */
                background: linear-gradient(90deg, transparent, {color_maestro}, transparent); 
                
                border: none;
                
                /* TANTEAR: Espacio gigante antes y después de la línea para separar partidos */
                margin: 40px 0; 
                
                opacity: 0.7;
            }}
            
            /* BLOQUE 5: TÍTULO DE JORNADA ENCIMA DE CADA PARTIDO */
            .jornada-header {{
                color: {color_maestro};
                
                /* TANTEAR: Tamaño de letra de "JORNADA X" */
                font-size: 14px; 
                
                font-weight: bold;
                text-transform: uppercase;
                letter-spacing: 2px;
                margin-bottom: 5px; /* TANTEAR: Espacio entre este título y la tarjeta gráfica */
                opacity: 0.8;
            }}
        </style>
        """, unsafe_allow_html=True)

        try:
            query_mis = text("SELECT * FROM partidos WHERE (local=:eq OR visitante=:eq) ORDER BY jornada ASC")
            mis = pd.read_sql_query(query_mis, conn, params={"eq": equipo_usuario})
            
            df_esc = pd.read_sql_query("SELECT nombre, escudo, prefijo, celular FROM equipos", conn)
            dict_escudos = dict(zip(df_esc['nombre'], df_esc['escudo']))
            dict_celulares = dict(zip(df_esc['nombre'], zip(df_esc['prefijo'], df_esc['celular'])))

            if mis.empty:
                st.info("🏖️ No tienes partidos programados por ahora.")
            
            for index, p in mis.iterrows():
                es_local = (p['local'] == equipo_usuario)
                rival = p['visitante'] if es_local else p['local']
                
                esc_l = dict_escudos.get(p['local']) or "https://cdn-icons-png.flaticon.com/512/33/33736.png"
                esc_v = dict_escudos.get(p['visitante']) or "https://cdn-icons-png.flaticon.com/512/33/33736.png"
                
                if p['goles_l'] is not None and p['goles_v'] is not None:
                    txt_score = f"{int(p['goles_l'])} - {int(p['goles_v'])}"
                else:
                    txt_score = "VS"

                # 1. HEADER DE JORNADA (Fuera de la tarjeta para identificar)
                st.markdown(f"<div class='jornada-header'>📍 Jornada {p['jornada']}</div>", unsafe_allow_html=True)

                # 2. TARJETA GRÁFICA (Tu función premium)
                html_card = renderizar_tarjeta_partido(
                    local=p['local'],
                    visita=p['visitante'],
                    escudo_l=esc_l,
                    escudo_v=esc_v,
                    marcador_texto=txt_score,
                    color_tema=color_maestro,
                    url_fondo=URL_FONDO_GESTION
                )
                st.markdown(html_card, unsafe_allow_html=True)

                # 3. BLOQUE DE INFO COMPACTO (Estado + WhatsApp pegados)
                # Unificamos esto en un solo HTML para evitar espacios de Streamlit
                estado_str = p['estado']
                
                # Colores de estado
                color_css = "#888" # Gris por defecto
                icon_est = "📅"
                if estado_str == "Finalizado": 
                    color_css = "#28a745" # Verde
                    icon_est = "✅"
                elif estado_str == "Conflicto": 
                    color_css = "#dc3545" # Rojo
                    icon_est = "⚠️"
                elif estado_str == "Revision": 
                    color_css = "#ffc107" # Naranja
                    icon_est = "⏳"

                # Lógica botón WhatsApp
                btn_wa_html = ""
                if estado_str != "Finalizado":
                    datos_wa = dict_celulares.get(rival)
                    if datos_wa and datos_wa[0] and datos_wa[1]:
                        num_wa = f"{str(datos_wa[0]).replace('+','')}{datos_wa[1]}"
                        btn_wa_html = f"""
                        <a href='https://wa.me/{num_wa}' target='_blank' class='wa-button'>
                            <span>💬</span> Contactar {rival}
                        </a>
                        """
                
                # Renderizamos el bloque info pegado
                st.markdown(f"""
                <div class='info-block'>
                    <div class='status-text' style='color:{color_css}'>
                        {icon_est} <b>{estado_str}</b>
                    </div>
                    {btn_wa_html}
                </div>
                """, unsafe_allow_html=True)

                # 4. EXPANDER DE ACCIÓN (Solo si es necesario)
                if estado_str in ["Programado", "Revision", "Conflicto"]:
                    mi_col_foto = "url_foto_l" if es_local else "url_foto_v"
                    ya_reporte = pd.notnull(p[mi_col_foto]) and p[mi_col_foto] != ""

                    if ya_reporte and estado_str != "Conflicto":
                        # Mensaje compacto si ya cumplió
                        st.info("👍 Reporte enviado. Esperando rival.")
                    else:
                        # Expander minimizado
                        with st.expander(f"📸 Subir Marcador", expanded=False):
                            st.caption("Evidencia del resultado final:")
                            tab_cam, tab_gal = st.tabs(["📷 Cámara", "📂 Galería"])
                            
                            img_file = None
                            with tab_cam:
                                img_cam = st.camera_input("Foto", key=f"cam_{p['id']}", label_visibility="collapsed")
                                if img_cam: img_file = img_cam
                            with tab_gal:
                                img_upl = st.file_uploader("Archivo", type=['jpg','png'], key=f"upl_{p['id']}", label_visibility="collapsed")
                                if img_upl: img_file = img_upl

                            if img_file:
                                st.image(img_file, width=150)
                                if st.button("Enviar", key=f"s_{p['id']}", use_container_width=True):
                                    # ... (LÓGICA DE ENVÍO DE SIEMPRE) ...
                                    # Para brevedad, aquí va tu bloque de IA/DB existente
                                    st.toast("Procesando...") 
                                    pass

                # 5. EL DIVISOR NOTORIO (Solo si no es el último partido)
                if index < len(mis) - 1:
                    st.markdown("<hr class='mega-divider'>", unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Error panel gestión: {e}")



            

  
  
# --- TAB: GESTIÓN ADMIN (Completo con Diseño Dinámico) ---
if rol == "admin":
    with tabs[2]:
        st.header("⚙️ Panel de Control Admin")
        
        # --- 1. SECCIÓN DE APROBACIONES (Sin cambios, ya extrae color_principal) ---
        st.subheader("📩 Equipos por Aprobar")
        try:
            pend = pd.read_sql_query(text("SELECT * FROM equipos WHERE estado='pendiente'"), conn)
            res_count = pd.read_sql_query(text("SELECT count(*) FROM equipos WHERE estado='aprobado' AND nombre != 'Sistema'"), conn)
            aprobados_count = res_count.iloc[0,0]
            st.write(f"**Progreso: {aprobados_count}/32 Equipos**")
        except Exception as e:
            st.error(f"Error leyendo base de datos: {e}")
            pend = pd.DataFrame() 

        if not pend.empty:
            for _, r in pend.iterrows():
                with st.container():
                    col_img, col_data, col_btn = st.columns([1, 2, 1], vertical_alignment="center")
                    prefijo = str(r.get('prefijo', '')).replace('+', '')
                    wa_link = f"https://wa.me/{prefijo}{r['celular']}"
                    
                    with col_img:
                        if r['escudo']: st.image(r['escudo'], width=60)
                        else: st.write("❌")

                    with col_data:
                        st.markdown(f"**{r['nombre']}**")
                        st.markdown(f"<a href='{wa_link}' style='color: #25D366; text-decoration: none; font-weight: bold; font-size: 0.9em;'>📞 Contactar DT</a>", unsafe_allow_html=True)
                    
                    with col_btn:
                        if st.button(f"✅", key=f"aprob_{r['nombre']}", use_container_width=True):
                            url_final = r['escudo']
                            if url_final:
                                with st.spinner("🤖 Limpiando escudo..."):
                                    try:
                                        res_ia = cloudinary.uploader.upload(url_final, background_removal="cloudinary_ai", folder="escudos_limpios", format="png")
                                        url_final = f"{res_ia['secure_url']}?v={int(time.time())}"
                                    except: pass
                            
                            with st.spinner("🎨 Extrayendo ADN..."):
                                color_adn = motor_colores.obtener_color_dominante(url_final)
                            
                            with conn.connect() as db:
                                db.execute(text("UPDATE equipos SET estado='aprobado', escudo=:e, color_principal=:c WHERE nombre=:n"),
                                           {"e": url_final, "c": color_adn, "n": r['nombre']})
                                db.commit()
                            st.rerun()
                st.markdown("---") 
        else:
            st.info("No hay equipos pendientes.")

        st.divider()

        # --- 2. SELECCIÓN DE TAREA ---
        opcion_admin = st.radio("Tarea:", ["⚽ Resultados", "🛠️ Directorio de Equipos", "🎨 Diseño Web"], horizontal=True, key="adm_tab")
        
        # --- A. OPCIÓN: DIRECTORIO (Sin cambios) ---
        if opcion_admin == "🛠️ Directorio de Equipos":
            st.subheader("📋 Directorio de Equipos")
            # ... (Toda tu lógica de Directorio se mantiene igual) ...
            st.info("Directorio cargado correctamente.") # Simplificado para el ejemplo

        # --- B. OPCIÓN: DISEÑO WEB (AQUÍ ESTÁ EL ARREGLO) ---
        elif opcion_admin == "🎨 Diseño Web":
            st.subheader("🎨 Personalización Maestro")
            st.info("Cambia la identidad visual de toda la web en un clic.")
            
            with conn.connect() as db:
                # Traemos nombre, escudo y el color ya guardado en la tabla equipos
                equipos_dispo = db.execute(text("SELECT nombre, escudo, color_principal FROM equipos WHERE (estado = 'aprobado' AND escudo IS NOT NULL) OR nombre ='Sistema'")).fetchall()

            if not equipos_dispo:
                st.warning("No hay equipos con ADN completo para diseñar.")
            else:
                # Creamos un diccionario con toda la info del equipo para no repetir consultas
                dict_equipos = {eq[0]: {"escudo": eq[1], "color": eq[2]} for eq in equipos_dispo}
                nombre_sel = st.selectbox("Equipo Inspiración:", list(dict_equipos.keys()))
                
                info_sel = dict_equipos[nombre_sel]
                col_prev, col_action = st.columns([1, 2])
                
                with col_prev:
                    st.image(info_sel['escudo'], width=80, caption=f"Color: {info_sel['color']}")
                
                with col_action:
                    if st.button(f"✨ Vestir Web de {nombre_sel}", type="primary", use_container_width=True):
                        try:
                            # 1. Usar el color que ya tiene el equipo (o detectar si es Sistema)
                            color_a_usar = info_sel['color'] if info_sel['color'] else "#FFD700"
                            
                            # 2. Generar Fondo con Motor Gráfico
                            with st.spinner("🧑‍🎨 Construyendo nueva piel para la web..."):
                                img_pil = motor_grafico.construir_portada(color_a_usar, info_sel['escudo'])
                                buffer = BytesIO()
                                img_pil.save(buffer, format="PNG")
                                buffer.seek(0)
                            
                            # 3. Subir a Cloudinary (Usamos el nombre del equipo en el ID para forzar cambio)
                            with st.spinner("☁️ Sincronizando con la nube..."):
                                res = cloudinary.uploader.upload(
                                    buffer, 
                                    folder="fondos_dinamicos",
                                    public_id=f"fondo_activo_golgana", # ID fijo para el fondo actual
                                    overwrite=True
                                )
                                # Cache buster vital para que el navegador note el cambio
                                url_fondo_nueva = f"{res['secure_url']}?v={int(time.time())}"
                                
                                # 4. Actualizar las 3 llaves maestras en 'configuracion'
                                with conn.connect() as db:
                                    def update_cfg(k, v):
                                        db.execute(text("INSERT INTO configuracion (clave, valor) VALUES (:k, :v) ON CONFLICT (clave) DO UPDATE SET valor = :v"), {"k": k, "v": v})
                                    
                                    update_cfg('fondo_url', url_fondo_nueva)
                                    update_cfg('color_primario', color_a_usar) # Guardamos el HEX exacto
                                    update_cfg('equipo_activo', nombre_sel)
                                    db.commit()
                            
                            st.balloons()
                            st.success("¡Identidad actualizada! Refresca la web para ver los cambios.")
                            time.sleep(1)
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"Error en motor gráfico: {e}")

          # --- 3. ACCIONES MAESTRAS ---
        st.divider()
        st.subheader("🚀 Control Global")
        
        col_torneo, col_reset = st.columns(2)
        
        with col_torneo:
            if fase_actual == "inscripcion":
                if st.button("🏁 INICIAR TORNEO", use_container_width=True, type="primary"):
                    if aprobados_count >= 2:
                        try:
                            generar_calendario() 
                            st.rerun()
                        except NameError:
                            st.error("Función generar_calendario no encontrada")
                    else:
                        st.error("Mínimo 2 equipos aprobados.")
        
        with col_reset:
            if st.button("🚨 REINICIAR TODO", use_container_width=True):
                with conn.connect() as db:
                    db.execute(text("DELETE FROM equipos"))
                    db.execute(text("DELETE FROM partidos"))
                    db.commit()
                st.session_state.clear()
                st.rerun()
                

































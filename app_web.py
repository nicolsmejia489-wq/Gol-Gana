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
from difflib import SequenceMatcher





# --- BLINDAJE VISUAL V2: FORZAR MODO OSCURO TOTAL ---
st.markdown("""
    <style>
        /* 1. FONDO GENERAL */
        .stApp {
            background-color: #0E1117;
            color: white;
        }
        
        /* 2. ARREGLO DE INPUTS (PIN, Nombres, Números) */
        div[data-baseweb="input"] {
            background-color: #262730 !important;
            border: 1px solid #444 !important;
        }
        div[data-baseweb="input"] > div {
            background-color: transparent !important;
            color: white !important;
        }
        input { color: white !important; }
        
        /* 3. ARREGLO DE BOTONES (Contactar DT, Guardar) */
        /* Ataca tanto a botones normales como a link_buttons */
        button[kind="secondary"], div[data-testid="stLinkButton"] a {
            background-color: #262730 !important;
            color: white !important;
            border: 1px solid #555 !important;
        }
        /* Efecto Hover para que se note que es botón */
        button[kind="secondary"]:hover, div[data-testid="stLinkButton"] a:hover {
            border-color: #FFD700 !important;
            color: #FFD700 !important;
        }

        /* 4. ARREGLO DE EXPANDERS (Reportar Marcador) */
        /* El encabezado del expander */
        div[data-testid="stExpander"] details summary {
            background-color: #262730 !important;
            color: white !important;
            border-radius: 5px;
        }
        /* El contenido interno del expander */
        div[data-testid="stExpander"] details {
            border-color: #444 !important;
            background-color: #0E1117 !important; 
        }
        /* Texto del título del expander */
        div[data-testid="stExpander"] p {
            color: white !important;
        }

        /* 5. ARREGLO DE FILE UPLOADER (Subir Foto) */
        div[data-testid="stFileUploader"] section {
            background-color: #262730 !important;
        }
        div[data-testid="stFileUploader"] span {
            color: #ccc !important;
        }

        /* 6. Textos generales */
        p, label, h1, h2, h3 {
            color: white !important;
        }
    </style>
""", unsafe_allow_html=True)







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
















###############  FUNCION LEER RESULTADO DE FOTO - EN PRUEBA
# Cargamos el motor una vez (Cache)
@st.cache_resource
def obtener_lector():
    # 'en' funciona mejor para números y nombres universales que 'es'
    return easyocr.Reader(['en'], gpu=False)

def similitud(a, b):
    """Calcula qué tan parecidas son dos palabras (0 a 1)."""
    return SequenceMatcher(None, a.upper(), b.upper()).ratio()

def limpiar_texto_ocr(texto):
    """Quita caracteres raros que el OCR confunde."""
    return re.sub(r'[^A-Z0-9\- ]', '', texto.upper())

def leer_marcador_ia(imagen_bytes, local_real, visitante_real):
    try:
        # 1. CORRECCIÓN DE LECTURA DE ARCHIVO
        # Usamos getvalue() directamente y rebobinamos por seguridad
        imagen_bytes.seek(0)
        file_bytes = np.asarray(bytearray(imagen_bytes.getvalue()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        
        if img is None: return None, "Error: Imagen corrupta."

        # 2. PRE-PROCESAMIENTO INTELIGENTE (CLAHE)
        # Convertimos a escala de grises
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Aplicamos CLAHE (Contrast Limited Adaptive Histogram Equalization)
        # Esto es MUCHO mejor que un threshold fijo para pantallas con brillo/reflejos
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        gray = clahe.apply(gray)
        
        # Opcional: Reducir ruido
        gray = cv2.fastNlMeansDenoising(gray, h=10)

        # 3. LECTURA ESPACIAL (EasyOCR)
        reader = obtener_lector()
        # detail=1 devuelve: [ [[x1,y1], [x2,y2]...], "texto", confianza ]
        # Leemos solo la mitad superior para optimizar (asumiendo que nadie toma foto al suelo)
        alto, ancho = gray.shape
        zona_interes = gray[0:int(alto*0.6), :] 
        
        resultados = reader.readtext(zona_interes, detail=1)

        # 4. LÓGICA DE ANCLAJE
        # Vamos a buscar dónde están los equipos y los números
        candidatos_local = []
        candidatos_visita = []
        candidatos_numeros = []

        # Palabras clave limpias de la BD
        keywords_local = local_real.upper().split()
        keywords_visita = visitante_real.upper().split()

        for (bbox, texto, prob) in resultados:
            texto_limpio = limpiar_texto_ocr(texto)
            if not texto_limpio: continue

            # Coordenadas del centro de la palabra (Eje X)
            # bbox = [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
            centro_x = (bbox[0][0] + bbox[1][0]) / 2

            # A. ¿Es un número (posible gol)?
            if re.match(r'^\d+$', texto_limpio) and int(texto_limpio) < 25:
                candidatos_numeros.append({'val': int(texto_limpio), 'x': centro_x, 'conf': prob})
                continue
            
            # B. ¿Es el marcador completo (ej: "3-1")?
            match_completo = re.match(r'(\d+)\s*[-]\s*(\d+)', texto_limpio)
            if match_completo:
                return (int(match_completo.group(1)), int(match_completo.group(2))), "Marcador Directo Detectado"

            # C. ¿Es el equipo LOCAL?
            # Si alguna palabra coincide con el nombre del local
            if any(similitud(k, texto_limpio) > 0.8 for k in keywords_local):
                candidatos_local.append({'x': centro_x, 'conf': prob})
            
            # D. ¿Es el equipo VISITANTE?
            if any(similitud(k, texto_limpio) > 0.8 for k in keywords_visita):
                candidatos_visita.append({'x': centro_x, 'conf': prob})

        # 5. TRIANGULACIÓN DEL RESULTADO
        # Ordenamos los números encontrados de izquierda a derecha
        candidatos_numeros.sort(key=lambda k: k['x'])
        
        # Caso Ideal: Encontramos números sueltos
        if len(candidatos_numeros) >= 2:
            
            # Si encontramos la posición de los equipos, usamos esa info
            x_local = candidatos_local[0]['x'] if candidatos_local else 0
            x_visita = candidatos_visita[0]['x'] if candidatos_visita else ancho
            
            # Filtramos números que estén "entre" los equipos (geográficamente)
            # O si no hay equipos, tomamos los dos más centrales o claros
            
            goles_finales = []
            
            # Estrategia: Tomar los dos números con mayor confianza que estén cerca uno del otro
            # Pero respetando el orden izquierda (Local) -> derecha (Visita)
            
            # Si detectamos equipos, validamos que los números estén en medio
            numeros_validos = []
            for n in candidatos_numeros:
                # Un número válido suele estar a la derecha del nombre local (si existe)
                # y a la izquierda del nombre visitante (si existe)
                # Damos un margen de error de pixeles
                es_valido = True
                if candidatos_local and n['x'] < x_local: es_valido = False
                if candidatos_visita and n['x'] > x_visita: es_valido = False
                
                if es_valido:
                    numeros_validos.append(n)
            
            # Si el filtro fue muy agresivo y nos quedamos sin nada, volvemos a todos los números
            if len(numeros_validos) < 2:
                numeros_validos = candidatos_numeros

            # Tomamos los 2 primeros (Izquierda -> Derecha)
            if len(numeros_validos) >= 2:
                gl = numeros_validos[0]['val']
                gv = numeros_validos[1]['val']
                return (gl, gv), "Lectura por Posición"

        return None, "No se pudo triangular el marcador. Intenta tomar la foto más cerca."

    except Exception as e:
        return None, f"Error Visión: {str(e)}"
        
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
            width: 12%; 
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
            padding-right: 5px; 
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
            .zona-centro {{ font-size: 20px; width: 20%; }} 
            
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






            

# --- 5. CALENDARIO Y GESTIÓN DE PARTIDOS (PÚBLICO - SIN EVIDENCIAS) ---
elif fase_actual == "clasificacion":
    with tabs[1]:
        # st.subheader("📅 Calendario Oficial")
        
        # URL de Fondo
        URL_PLANTILLA_FONDO = "https://res.cloudinary.com/..." 
        placeholder_escudo = "https://cdn-icons-png.flaticon.com/512/5329/5329945.png"

        try:
            # Leemos los partidos
            df_p = pd.read_sql_query("SELECT * FROM partidos ORDER BY jornada ASC", conn)
            # Leemos escudos
            df_escudos = pd.read_sql_query("SELECT nombre, escudo FROM equipos", conn)
            escudos_dict = dict(zip(df_escudos['nombre'], df_escudos['escudo']))
        except Exception as e:
            st.error(f"Error al cargar partidos: {e}")
            df_p = pd.DataFrame()

        if not df_p.empty:
            j_tabs = st.tabs(["Jornada 1", "Jornada 2", "Jornada 3"])
            
            for i, jt in enumerate(j_tabs):
                with jt:
                    df_j = df_p[df_p['jornada'] == (i + 1)]
                    
                    if df_j.empty:
                        st.info("No hay partidos programados para esta fecha.")
                    
                    for _, p in df_j.iterrows():
                        # 1. Preparar Escudos
                        esc_l = escudos_dict.get(p['local']) or placeholder_escudo
                        esc_v = escudos_dict.get(p['visitante']) or placeholder_escudo
                        
                        # 2. Preparar Marcador
                        try:
                            if pd.notna(p['goles_l']) and pd.notna(p['goles_v']):
                                txt_marcador = f"{int(p['goles_l'])} - {int(p['goles_v'])}"
                            else:
                                txt_marcador = "VS"
                        except ValueError:
                            txt_marcador = "VS"
                        
                        # 3. Construir la Tarjeta HTML
                        html_tarjeta = renderizar_tarjeta_partido(
                            local=p['local'],
                            visita=p['visitante'],
                            escudo_l=esc_l,
                            escudo_v=esc_v,
                            marcador_texto=txt_marcador,
                            color_tema=color_maestro,
                            url_fondo=URL_PLANTILLA_FONDO
                        )
                        
                        st.markdown(html_tarjeta, unsafe_allow_html=True)
                        # (Sección de evidencias eliminada para el público)
        else:
            st.info("El calendario se mostrará cuando inicie el torneo.")

            






# --- TAB: MIS PARTIDOS (DT - FLUJO MEJORADO CON ORIGEN DE DATOS) ---
if rol == "dt":
    with tabs[2]:
        st.subheader(f"🏟️ Mis Partidos: {equipo_usuario}")
        
        try:
            # 1. CONSULTA
            query_mis = text("SELECT * FROM partidos WHERE (local=:eq OR visitante=:eq) ORDER BY jornada ASC")
            mis = pd.read_sql_query(query_mis, conn, params={"eq": equipo_usuario})
            
            if mis.empty:
                st.info("Aún no tienes partidos asignados.")
            
            ultima_jornada_vista = -1

            for _, p in mis.iterrows():
                
                # --- A. SEPARADOR JORNADA ---
                if p['jornada'] != ultima_jornada_vista:
                    st.divider()
                    c_spacer, c_title, c_spacer2 = st.columns([1, 2, 1])
                    with c_title:
                        st.header(f"JORNADA {p['jornada']}")
                    ultima_jornada_vista = p['jornada']

                es_local = (p['local'] == equipo_usuario)
                rival = p['visitante'] if es_local else p['local']
                
                with st.container(border=True):
                    # 1. INFO RIVAL
                    c_riv, c_wa = st.columns([3, 1])
                    with c_riv:
                        st.caption("Tu Rival")
                        st.subheader(f"{rival}")
                    with c_wa:
                        link_wa = None
                        try:
                            with conn.connect() as db:
                                r = db.execute(text("SELECT prefijo, celular FROM equipos WHERE nombre=:n"), {"n": rival}).fetchone()
                                if r and r[0] and r[1]:
                                    num = f"{str(r[0]).replace('+', '')}{r[1]}"
                                    link_wa = f"https://wa.me/{num}"
                        except: pass
                        if link_wa:
                            st.link_button("💬 Chat", link_wa, type="primary")
                        else:
                            st.caption("🚫")

                    st.markdown("<div style='height:1px; background-color:#333; margin: 15px 0;'></div>", unsafe_allow_html=True)

                    # 2. ZONA DE ACCIÓN
                    # Extraemos el método de registro (por defecto Algoritmo si es nulo)
                    metodo = p['metodo_registro'] if 'metodo_registro' in p and pd.notna(p['metodo_registro']) else "Algoritmo"

                    if p['estado'] == 'Finalizado':
                        st.success(f"✅ Finalizado ({metodo}): {int(p['goles_l'])} - {int(p['goles_v'])}")
                        
                        # BOTÓN DE CORRECCIÓN: No resetea goles, solo cambia estado
                        if st.button("❌ ¿Marcador Incorrecto?", key=f"err_{p['id']}", use_container_width=True):
                            try:
                                with conn.connect() as db:
                                    # Mantenemos los goles, solo cambiamos estado y conflicto
                                    q = text("UPDATE partidos SET estado='Revision', conflicto=1 WHERE id=:id")
                                    db.execute(q, {"id": p['id']})
                                    db.commit()
                                st.warning("Partido marcado como incorrecto. Se mantiene el marcador para revisión del Admin.")
                                time.sleep(1.5)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error al reportar: {e}")

                    elif p['estado'] == 'Revision':
                        st.warning(f"⏳ En Revisión: {int(p['goles_l']) if pd.notna(p['goles_l']) else '?'} - {int(p['goles_v']) if pd.notna(p['goles_v']) else '?'}")
                        st.caption("El Administrador está verificando este resultado.")

                    else:
                        st.caption("📸 CARGAR RESULTADO")
                        tipo_carga = st.radio("Método:", ["Ocultar", "Usar Cámara", "Subir Foto"], horizontal=True, label_visibility="collapsed", key=f"radio_{p['id']}")
                        
                        foto = None
                        if tipo_carga == "Usar Cámara":
                            foto = st.camera_input("Toma la foto", key=f"cam_{p['id']}")
                        elif tipo_carga == "Subir Foto":
                            foto = st.file_uploader("Selecciona imagen", type=['jpg','png','jpeg'], key=f"upl_{p['id']}")

                        if foto:
                            st.image(foto, width=200)
                            
                            if st.button("📤 ENVIAR AHORA", key=f"send_{p['id']}", type="primary", use_container_width=True):
                                with st.spinner("🔍 Analizando imagen..."):
                                    
                                    res_ia, msg_ia = leer_marcador_ia(foto, p['local'], p['visitante'])

                                    if res_ia:
                                        gl_ia, gv_ia = res_ia
                                        st.info(f"🔢 Resultado Detectado: {gl_ia} - {gv_ia}")

                                        try:
                                            foto.seek(0)
                                            res_c = cloudinary.uploader.upload(foto, folder="gol_gana_evidencias")
                                            url = res_c['secure_url']
                                            cf = "url_foto_l" if es_local else "url_foto_v"

                                            with conn.connect() as db:
                                                gl_ex = int(p['goles_l']) if pd.notna(p['goles_l']) else None
                                                gv_ex = int(p['goles_v']) if pd.notna(p['goles_v']) else None

                                                if gl_ex is not None:
                                                    # Verificamos coincidencia con reporte previo
                                                    if gl_ex != gl_ia or gv_ex != gv_ia:
                                                        # Conflicto: Goles nulos para forzar revisión manual
                                                        q = text(f"UPDATE partidos SET goles_l=NULL, goles_v=NULL, conflicto=1, {cf}=:u, ia_goles_l=:gl, ia_goles_v=:gv, estado='Revision', metodo_registro='Algoritmo' WHERE id=:id")
                                                        db.execute(q, {"u": url, "gl": gl_ia, "gv": gv_ia, "id": p['id']})
                                                        st.warning("⚠️ Los resultados no coinciden. Admin notificado.")
                                                    else:
                                                        # Coincidencia: Finalizado
                                                        q = text(f"UPDATE partidos SET {cf}=:u, conflicto=0, estado='Finalizado', metodo_registro='Algoritmo' WHERE id=:id")
                                                        db.execute(q, {"u": url, "id": p['id']})
                                                        st.balloons()
                                                        st.success("✅ Verificado y Finalizado.")
                                                else:
                                                    # Primer reporte: Finalizado directo (Algoritmo)
                                                    q = text(f"UPDATE partidos SET goles_l=:gl, goles_v=:gv, {cf}=:u, ia_goles_l=:gl, ia_goles_v=:gv, estado='Finalizado', conflicto=0, metodo_registro='Algoritmo' WHERE id=:id")
                                                    db.execute(q, {"gl": gl_ia, "gv": gv_ia, "u": url, "id": p['id']})
                                                    st.balloons()
                                                    st.success("✅ Resultado registrado con éxito.")
                                                
                                                db.commit()
                                            
                                            time.sleep(2)
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Error BD: {e}")
                                    else:
                                        st.error(f"❌ {msg_ia}")

        except Exception as e:
            st.error(f"Error carga: {e}")


            

            
# --- TAB: GESTIÓN ADMIN (FINAL: FILTROS + TEXT INPUTS + BLINDAJE) ---
if rol == "admin":
    with tabs[2]:
        st.header("⚙️ Gestión del Torneo")

        # 0. OBTENER COLOR PRIMARIO
        try:
            c_res = pd.read_sql_query("SELECT valor FROM config WHERE clave='color_primario'", conn)
            color_primario = c_res.iloc[0,0] if not c_res.empty else "#FFD700"
        except: color_primario = "#FFD700"
        
        # 1. APROBACIONES
        try:
            pend = pd.read_sql_query(text("SELECT * FROM equipos WHERE estado='pendiente'"), conn)
            if not pend.empty:
                st.info(f"Tienes {len(pend)} solicitudes.")
                for _, r in pend.iterrows():
                    with st.container():
                        c1, c2, c3 = st.columns([0.8, 3, 1], vertical_alignment="center")
                        pref = str(r.get('prefijo', '')).replace('+', '')
                        with c1: st.image(r['escudo'], width=35) if r['escudo'] else st.write("❌")
                        with c2: 
                            st.markdown(f"**{r['nombre']}**")
                            st.markdown(f"[WhatsApp](https://wa.me/{pref}{r['celular']})")
                        with c3:
                            if st.button("✅", key=f"ok_{r['nombre']}"):
                                url = r['escudo']
                                if url:
                                    try:
                                        res = cloudinary.uploader.upload(url, background_removal="cloudinary_ai", folder="escudos_limpios")
                                        url = res['secure_url']
                                    except: pass
                                try: c_adn = motor_colores.obtener_color_dominante(url)
                                except: c_adn = "#333"
                                with conn.connect() as db:
                                    db.execute(text("UPDATE equipos SET estado='aprobado', escudo=:e, color_principal=:c WHERE nombre=:n"),{"e":url, "c":c_adn, "n":r['nombre']})
                                    db.commit()
                                st.rerun()
                    st.divider()
        except: pass

        st.write("")
        opcion_admin = st.radio("Acción:", ["⚽ Resultados", "🛠️ Directorio"], horizontal=True, label_visibility="collapsed")
        
        # ------------------------------------------
        # A. RESULTADOS
        # ------------------------------------------
        if opcion_admin == "⚽ Resultados":
            st.subheader("📝 Marcadores")
            
            # --- NUEVO SELECTOR DE FILTROS ---
            filtro_partidos = st.radio("Filtrar por:", ["Todos", "Pendientes", "Conflictos"], horizontal=True)
            
            # CSS (Mismo estilo limpio anterior)
            st.markdown(f"""
            <style>
                @media (max-width: 640px) {{
                    div[data-testid="stHorizontalBlock"] {{ flex-direction: row !important; flex-wrap: nowrap !important; gap: 2px !important; }}
                    div[data-testid="stColumn"] {{ min-width: 0px !important; flex: 1 1 auto !important; padding: 0px !important; }}
                }}
                div[data-testid="stTextInput"] input {{
                    text-align: center !important; font-weight: 800 !important; font-size: 18px !important;
                    color: {color_primario} !important; background-color: rgba(255,255,255,0.05) !important;
                    border: 1px solid rgba(255,255,255,0.2) !important; border-radius: 4px !important;
                    padding: 0px !important; height: 35px !important;
                }}
                div[data-testid="stTextInput"] {{ width: 40px !important; min-width: 40px !important; margin: auto !important; }}
                [data-testid="stLinkButton"] a, .stButton button {{
                    background-color: rgba(255,255,255,0.08) !important; border: 1px solid rgba(255,255,255,0.1) !important;
                    color: #ddd !important; border-radius: 6px !important; min-height: 32px !important; height: auto !important; width: 100% !important;
                    display: flex !important; align-items: center !important; justify-content: center !important;
                    text-decoration: none !important; font-size: 11px !important; line-height: 1.1 !important;
                    padding: 4px 1px !important; white-space: normal !important; text-align: center !important;
                }}
                [data-testid="stLinkButton"] a:hover, .stButton button:hover {{ border-color: {color_primario} !important; color: {color_primario} !important; }}
                .match-card {{
                    background: linear-gradient(180deg, rgba(30,30,30,0.9) 0%, rgba(15,15,15,0.95) 100%);
                    border-bottom: 2px solid {color_primario}; border-top: 1px solid rgba(255,255,255,0.1);
                    border-left: 1px solid rgba(255,255,255,0.1); border-right: 1px solid rgba(255,255,255,0.1);
                    border-radius: 12px; padding: 8px 4px; margin-bottom: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);
                }}
                .conflict {{ border: 2px solid #FF4B4B; background: rgba(50,0,0,0.6); }}
                .team-l {{ text-align: right; font-weight: 800; margin-right: 5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 15px; }}
                .team-v {{ text-align: left; font-weight: 800; margin-left: 5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 15px; }}
            </style>
            """, unsafe_allow_html=True)

            try:
                df_p = pd.read_sql_query("SELECT * FROM partidos ORDER BY jornada ASC, id ASC", conn)
                df_e = pd.read_sql_query("SELECT nombre, escudo, celular, prefijo FROM equipos", conn)
                placeholder = "https://cdn-icons-png.flaticon.com/512/5329/5329945.png"
                
                info_equipos = {}
                for _, row in df_e.iterrows():
                    escudo_seguro = row['escudo'] if (row['escudo'] and len(str(row['escudo'])) > 5) else placeholder
                    info_equipos[row['nombre']] = {
                        'escudo': escudo_seguro,
                        'cel': f"{str(row['prefijo']).replace('+','')}{row['celular']}"
                    }
            except: df_p = pd.DataFrame(); info_equipos = {}

            # --- APLICAR FILTROS ---
            if not df_p.empty:
                if filtro_partidos == "Conflictos":
                    df_p = df_p[(df_p['estado']=='Revision') | (df_p['conflicto']==1)]
                elif filtro_partidos == "Pendientes":
                    # Filtramos donde los goles sean NaN (no jugados)
                    df_p = df_p[df_p['goles_l'].isna() | df_p['goles_v'].isna()]
            
            # --- BLINDAJE: SI EL DATAFRAME QUEDÓ VACÍO TRAS EL FILTRO, NO MOSTRAR TABS ---
            if df_p.empty:
                st.info(f"No hay partidos en la categoría: {filtro_partidos}")
            else:
                jornadas = sorted(df_p['jornada'].unique())
                tabs_j = st.tabs([f"J{int(j)}" for j in jornadas]) 

                for i, tab in enumerate(tabs_j):
                    with tab:
                        df_j = df_p[df_p['jornada'] == jornadas[i]]
                        if df_j.empty: st.caption("Sin partidos.")
                        
                        for _, row in df_j.iterrows():
                            d_l = info_equipos.get(row['local'], {'escudo': placeholder, 'cel': ''})
                            d_v = info_equipos.get(row['visitante'], {'escudo': placeholder, 'cel': ''})
                            rev = row['estado']=='Revision' or row['conflicto']==1
                            css_card = "match-card conflict" if rev else "match-card"
                            
                            st.markdown(f'<div class="{css_card}">', unsafe_allow_html=True)
                            
                            # PISO 1: MARCADOR
                            c_p1 = st.columns([0.6, 2.5, 1, 0.2, 1, 2.5, 0.6], vertical_alignment="center")
                            with c_p1[0]: st.image(d_l['escudo'], width=30)
                            with c_p1[1]: st.markdown(f"<div class='team-l'>{row['local']}</div>", unsafe_allow_html=True)
                            
                            with c_p1[2]:
                                vl = str(int(row['goles_l'])) if pd.notna(row['goles_l']) else ""
                                gl = st.text_input("L", value=vl, max_chars=2, label_visibility="collapsed", key=f"gL_{row['id']}")
                                
                            with c_p1[3]: st.markdown("<div style='text-align:center; opacity:0.5'>-</div>", unsafe_allow_html=True)
                            
                            with c_p1[4]:
                                vv = str(int(row['goles_v'])) if pd.notna(row['goles_v']) else ""
                                gv = st.text_input("V", value=vv, max_chars=2, label_visibility="collapsed", key=f"gV_{row['id']}")
                                
                            with c_p1[5]: st.markdown(f"<div class='team-v'>{row['visitante']}</div>", unsafe_allow_html=True)
                            with c_p1[6]: st.image(d_v['escudo'], width=30)

                            st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
                            
                            # PISO 2: ACCIONES
                            c_row1 = st.columns(2, gap="small")
                            with c_row1[0]:
                                if st.button("💾 Guardar", key=f"s_{row['id']}", use_container_width=True):
                                    if gl == "" or gv == "":
                                        st.toast("⚠️ Faltan goles")
                                    elif not (gl.isdigit() and gv.isdigit()):
                                        st.toast("⚠️ Solo números")
                                    else:
                                        with conn.connect() as db:
                                            db.execute(text("UPDATE partidos SET goles_l=:l, goles_v=:v, estado='Finalizado', conflicto=0, metodo_registro='Manual' WHERE id=:id"),
                                                       {"l":int(gl), "v":int(gv), "id":row['id']})
                                            db.commit()
                                        st.toast("Guardado")
                                        st.rerun()

                            with c_row1[1]:
                                url_ev = row['url_foto_l'] or row['url_foto_v']
                                if url_ev:
                                    st.link_button("📷 Ver Foto", url_ev, use_container_width=True)
                                else:
                                    st.button("🚫 Sin Foto", key=f"no_{row['id']}", disabled=True, use_container_width=True)

                            st.markdown("<div style='height: 2px;'></div>", unsafe_allow_html=True)
                            c_row2 = st.columns(2, gap="small")

                            with c_row2[0]:
                                if d_l['cel']:
                                    st.link_button(f"📞 {row['local']}", f"https://wa.me/{d_l['cel']}", use_container_width=True)
                                else:
                                    st.button(f"🚫 {row['local']}", key=f"nl_{row['id']}", disabled=True, use_container_width=True)

                            with c_row2[1]:
                                if d_v['cel']:
                                    st.link_button(f"📞 {row['visitante']}", f"https://wa.me/{d_v['cel']}", use_container_width=True)
                                else:
                                    st.button(f"🚫 {row['visitante']}", key=f"nv_{row['id']}", disabled=True, use_container_width=True)

                            st.markdown("</div>", unsafe_allow_html=True)

# ------------------------------------------
        # B. DIRECTORIO (LISTA SIMPLE Y ESTABLE)
        # ------------------------------------------
        elif opcion_admin == "🛠️ Directorio":
            st.subheader("📋 Directorio de Equipos")
            
            try:
                # 1. CONSULTA FILTRADA
                df_maestro = pd.read_sql_query(text("SELECT * FROM equipos WHERE nombre NOT IN ('Admin', 'Sistema') ORDER BY nombre"), conn)
            except:
                df_maestro = pd.DataFrame()

            if not df_maestro.empty:
                st.caption("Equipos registrados:")
                
                # BUCLE DIRECTO (Sin contenedores complejos para evitar errores de renderizado)
                for _, eq in df_maestro.iterrows():
                    # Preparación de variables
                    estado_icon = "✅" if eq['estado'] == 'aprobado' else "⏳"
                    src_escudo = eq['escudo'] if (eq['escudo'] and len(str(eq['escudo'])) > 5) else "https://cdn-icons-png.flaticon.com/512/5329/5329945.png"
                    
                    # Limpieza del número para WhatsApp
                    celular_limpio = f"{str(eq['prefijo']).replace('+','')}{eq['celular']}"
                    link_wa = f"https://wa.me/{celular_limpio}"
                    
                    # HTML PURO Y SIMPLE
                    # Usamos f-string con triple comilla para evitar conflictos
                    html_card = f"""
                    <div style="
                        display: flex; 
                        justify-content: space-between; 
                        align-items: center; 
                        background-color: rgba(255,255,255,0.05); 
                        padding: 10px; 
                        border-radius: 8px; 
                        margin-bottom: 8px; 
                        border-left: 4px solid {color_primario};
                    ">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <span style="font-size: 18px;">{estado_icon}</span>
                            <img src="{src_escudo}" style="width: 30px; height: 30px; border-radius: 50%; object-fit: cover;">
                            <div style="line-height: 1.2;">
                                <div style="font-weight: bold; color: white; font-size: 14px;">{eq['nombre']}</div>
                                <div style="font-size: 11px; color: #aaa;">PIN: {eq['pin']}</div>
                            </div>
                        </div>

                        <a href="{link_wa}" target="_blank" style="text-decoration: none;">
                            <div style="
                                background-color: rgba(37, 211, 102, 0.15); 
                                border: 1px solid #25D366; 
                                color: #25D366; 
                                padding: 6px 12px; 
                                border-radius: 20px; 
                                font-size: 12px; 
                                font-weight: bold;
                                display: flex; 
                                align-items: center; 
                                gap: 5px;
                                transition: 0.3s;
                            ">
                                <span>📞</span> Chat
                            </div>
                        </a>
                    </div>
                    """
                    
                    st.markdown(html_card, unsafe_allow_html=True)

                st.markdown("<div style='margin-bottom: 30px'></div>", unsafe_allow_html=True)
                st.markdown("---")

                # 2. ZONA DE EDICIÓN
                st.subheader("✏️ Editar o Eliminar")
                
                # Selector de equipo
                lista_nombres = df_maestro['nombre'].tolist()
                equipo_sel = st.selectbox("Selecciona equipo a gestionar:", lista_nombres)
                
                if equipo_sel:
                    datos_sel = df_maestro[df_maestro['nombre'] == equipo_sel].iloc[0]

                    # FORMULARIO DE EDICIÓN
                    with st.form("edit_master_form"):
                        c_nm, c_pin = st.columns([2, 1])
                        new_name = c_nm.text_input("Nombre", datos_sel['nombre'])
                        new_pin = c_pin.text_input("PIN", str(datos_sel['pin']))
                        
                        c_img1, c_img2 = st.columns([1, 3])
                        with c_img1:
                            st.caption("Actual:")
                            e_show = datos_sel['escudo'] if (datos_sel['escudo'] and len(str(datos_sel['escudo'])) > 5) else "https://cdn-icons-png.flaticon.com/512/5329/5329945.png"
                            st.image(e_show, width=50)
                        
                        with c_img2:
                            nuevo_escudo_img = st.file_uploader("Nuevo Escudo (Opcional)", type=['png', 'jpg', 'jpeg'])
                        
                        if st.form_submit_button("💾 Guardar Cambios", use_container_width=True):
                            url_final = datos_sel['escudo']
                            
                            # Si subió imagen nueva
                            if nuevo_escudo_img:
                                try:
                                    res_std = cloudinary.uploader.upload(nuevo_escudo_img, folder="escudos_limpios")
                                    url_final = res_std['secure_url']
                                except:
                                    st.error("Error subiendo imagen.")

                            try:
                                with conn.connect() as db:
                                    # 1. Actualizar tabla EQUIPOS
                                    db.execute(
                                        text("UPDATE equipos SET nombre=:nn, pin=:np, escudo=:ne WHERE nombre=:viejo"),
                                        {"nn": new_name, "np": new_pin, "ne": url_final, "viejo": equipo_sel}
                                    )
                                    
                                    # 2. Actualizar tabla PARTIDOS
                                    if new_name != equipo_sel:
                                        db.execute(text("UPDATE partidos SET local=:nn WHERE local=:viejo"), {"nn": new_name, "viejo": equipo_sel})
                                        db.execute(text("UPDATE partidos SET visitante=:nn WHERE visitante=:viejo"), {"nn": new_name, "viejo": equipo_sel})
                                    
                                    db.commit()
                                st.success(f"✅ {new_name} actualizado.")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error BD: {e}")

                    # ZONA DE BORRADO
                    st.markdown("<div style='height:15px'></div>", unsafe_allow_html=True)
                    
                    col_del1, col_del2 = st.columns([3, 1], vertical_alignment="bottom")
                    with col_del1:
                        confirmar_borrado = st.checkbox(f"🔴 Confirmar borrado de {equipo_sel}")
                    
                    with col_del2:
                        if st.button("Eliminar", type="primary", use_container_width=True, disabled=not confirmar_borrado):
                            with conn.connect() as db:
                                db.execute(text("DELETE FROM equipos WHERE nombre = :n"), {"n": equipo_sel})
                                db.execute(text("DELETE FROM partidos WHERE local = :n OR visitante = :n"), {"n": equipo_sel})
                                db.commit()
                            st.toast(f"🗑️ Equipo eliminado.")
                            time.sleep(1)
                            st.rerun()
            else:
                st.info("El directorio está vacío.")








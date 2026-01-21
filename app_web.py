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



# 1. CONFIGURACIÓN PRINCIPAL DE SITIO
st.set_page_config(
    page_title="Gol-Gana Pro", 
    layout="centered", 
    initial_sidebar_state="collapsed"
)

# --- VALORES INICIALES (Seguridad) ---
fondo_actual = "https://res.cloudinary.com/dlvczeqlp/image/upload/v1/assets/fondo_base.jpg"
color_primario = "#FFD700" # Dorado por defecto

try:
    conn = st.connection("postgresql", type="sql")
    
    # Forzamos una limpieza de caché para leer el cambio instantáneo
    df_config = conn.query("SELECT clave, valor FROM configuracion;", ttl=0)
    
    if not df_config.empty:
        # Buscamos la fila del fondo
        row_fondo = df_config[df_config['clave'] == 'fondo_url']
        if not row_fondo.empty:
            fondo_actual = row_fondo['valor'].values[0]
            
        # Buscamos la fila del color
        row_color = df_config[df_config['clave'] == 'color_primario']
        if not row_color.empty:
            color_primario = row_color['valor'].values[0]

    # LOG DE DEPURACIÓN (Solo para que tú lo veas en la consola de Streamlit Cloud)
    # st.write(f"DEBUG: Fondo: {fondo_actual} | Color: {color_primario}")

except Exception as e:
    st.error(f"Error de conexión: {e}")



# --- INYECCIÓN DE CSS DINÁMICO (CORREGIDO) ---
st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@200;400;700&display=swap');

        /* Usamos DOBLE LLAVE para el CSS y SIMPLE para la variable de Python */
        html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{
            background-color: #000000 !important;
            background-image: url("{fondo_actual}");
            background-size: cover;
            background-position: center center;
            background-attachment: fixed;
            background-repeat: no-repeat;
            color: #ffffff !important;
            font-family: 'Oswald', sans-serif !important;
        }}

        .stApp::before {{
            content: "";
            position: absolute;
            top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0, 0, 0, 0.6);
            pointer-events: none;
            z-index: 0;
        }}

        [data-testid="stDecoration"] {{
            background-image: linear-gradient(90deg, {color_primario}, #000000) !important;
        }}

        button[data-baseweb="tab"] {{
            color: #888 !important;
        }}
        
        button[data-baseweb="tab"][aria-selected="true"] {{
            color: {color_primario} !important;
            border-bottom-color: {color_primario} !important;
        }}

        h1, h2, h3, h4, h5, h6 {{
            font-family: 'Oswald', sans-serif !important;
            color: {color_primario} !important;
            text-transform: uppercase;
            text-shadow: 2px 2px 4px rgba(0,0,0,1);
            position: relative;
            z-index: 1;
        }}

        div.stButton > button, div.stFormSubmitButton > button {{
            background-color: rgba(26, 26, 26, 0.8) !important;
            color: white !important;
            border: 1px solid {color_primario} !important;
            border-radius: 20px !important;
            font-weight: bold !important;
        }}

        div.stButton > button:hover {{
            background-color: {color_primario} !important;
            color: black !important;
        }}

        .big-table th {{ 
            background-color: rgba(17, 17, 17, 0.9); 
            color: {color_primario} !important; 
            border-bottom: 2px solid {color_primario};
        }}
        
        /* ... el resto de tus reglas con doble llave ... */
        
    </style>
""", unsafe_allow_html=True)





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
    try:
        with conn.connect() as db:
            # 1. Obtener equipos aprobados
            res = db.execute(text("SELECT nombre FROM equipos WHERE estado = 'aprobado'"))
            # fetchall devuelve tuplas, extraemos el primer elemento
            equipos = [row[0] for row in res.fetchall()]
            
            # 2. Rellenar con W.O. hasta llegar a 32 (o par)
            while len(equipos) < 32:
                nombre_wo = f"(WO) {len(equipos)+1}"
                
                # Sintaxis Postgres para "Si existe, no hagas nada"
                query_wo = text("""
                    INSERT INTO equipos (nombre, estado) 
                    VALUES (:n, 'aprobado') 
                    ON CONFLICT (nombre) DO NOTHING
                """)
                db.execute(query_wo, {"n": nombre_wo})
                
                # Lo agregamos a la lista local para el sorteo
                equipos.append(nombre_wo)
            
            random.shuffle(equipos)
            n = len(equipos)
            indices = list(range(n))
            
            # 3. Generar cruces (Algoritmo Round Robin)
            for jor in range(1, 4): # Genera 3 jornadas
                for i in range(n // 2):
                    loc = equipos[indices[i]]
                    vis = equipos[indices[n - 1 - i]]
                    
                    query_partido = text("""
                        INSERT INTO partidos (local, visitante, jornada, estado) 
                        VALUES (:l, :v, :j, 'Programado')
                    """)
                    db.execute(query_partido, {"l": loc, "v": vis, "j": jor})
                
                # Rotación de índices para la siguiente fecha
                indices = [indices[0]] + [indices[-1]] + indices[1:-1]
            
            # 4. Actualizar Fase del Torneo
            # OJO: En Neon la columna es 'clave' y el valor es 'fase_actual'
            db.execute(text("UPDATE config SET valor = 'clasificacion' WHERE clave = 'fase_actual'"))
            db.commit()
            
    except Exception as e:
        st.error(f"Error generando calendario: {e}")

# --- 3. NAVEGACIÓN (Inicialización de Estado) ---
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





# --- TAB: CLASIFICACIÓN (Versión Blindada Anti-Errores) ---
with tabs[0]:
    try:
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

            # 2. CONSTRUIMOS TODO EL DISEÑO EN UNA SOLA VARIABLE 'salida_visual'
            # Primero los estilos
            estilos = """
            <style>
                .tabla-pro { width: 100%; border-collapse: collapse; table-layout: fixed; background-color: #000; font-family: 'Oswald', sans-serif; }
                .tabla-pro th { background-color: #111; color: #FFD700; padding: 6px 2px; font-size: 14px; border-bottom: 2px solid #FFD700; text-align: center; }
                .tabla-pro td { padding: 10px 2px; text-align: center; vertical-align: middle; border-bottom: 1px solid #222; font-size: 21px; color: white; }
                .tabla-pro .team-cell { text-align: left; padding-left: 8px; font-size: 18px; font-weight: bold; }
            </style>
            """
            
            # Iniciamos el HTML de la tabla
            tabla_html = '<table class="tabla-pro"><thead><tr>'
            tabla_html += '<th style="width:10%">POS</th><th style="width:45%; text-align:left; padding-left:8px">EQUIPO</th>'
            tabla_html += '<th style="width:10%">PTS</th><th style="width:9%">PJ</th><th style="width:9%">GF</th><th style="width:9%">GC</th><th style="width:8%">DG</th>'
            tabla_html += '</tr></thead><tbody>'

            # Agregamos las filas una por una a la variable
            for _, r in df_f.iterrows():
                url = mapa_escudos.get(r['EQ'])
                escudo = f'<img src="{url}" style="width:32px; height:32px; object-fit:contain; vertical-align:middle; margin-right:8px;">' if url else '<span style="font-size:22px; margin-right:8px;">🛡️</span>'
                
                tabla_html += f"<tr>"
                tabla_html += f"<td>{r['POS']}</td>"
                tabla_html += f"<td class='team-cell'>{escudo}{r['EQ']}</td>"
                tabla_html += f"<td style='color:#FFD700; font-weight:bold;'>{r['PTS']}</td>"
                tabla_html += f"<td>{r['PJ']}</td><td>{r['GF']}</td><td>{r['GC']}</td>"
                tabla_html += f"<td style='font-size:15px; color:#888;'>{r['DG']}</td>"
                tabla_html += f"</tr>"

            tabla_html += "</tbody></table>"

            # 3. EL ÚNICO COMANDO QUE MUESTRA COSAS (Inyecta Estilo + Tabla)
            # Al concatenar (estilos + tabla_html), Streamlit lo trata como un solo objeto.
            st.markdown(estilos + tabla_html, unsafe_allow_html=True)

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
            st.success("✅ ¡Inscripción recibida! El administrador revisará tu solicitud.")
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
        
        # 1. Consultar partidos del usuario (Lectura segura Neon)
        try:
            query_mis = text("SELECT * FROM partidos WHERE (local=:eq OR visitante=:eq) ORDER BY jornada ASC")
            mis = pd.read_sql_query(query_mis, conn, params={"eq": equipo_usuario})
            
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
                    
                    # --- CONTACTO WHATSAPP (Consulta puntual sin cursores) ---
                    numero_wa = None
                    try:
                        with conn.connect() as db:
                            q_wa = text("SELECT prefijo, celular FROM equipos WHERE nombre=:n")
                            r = db.execute(q_wa, {"n": rival}).fetchone()
                            if r and r[0] and r[1]:
                                numero_wa = f"{str(r[0]).replace('+', '')}{r[1]}"
                    except:
                        pass # Si falla, solo no muestra el botón

                    if numero_wa:
                        st.markdown(f"""
                            <a href='https://wa.me/{numero_wa}' class='wa-btn' style='text-decoration: none;'>
                                💬 Contactar Rival (WhatsApp)
                            </a>
                        """, unsafe_allow_html=True)
                    else:
                        st.caption("🚫 Sin contacto registrado.")

                    # --- EXPANDER PARA REPORTE ---
                    with st.expander(f"📸 Reportar Marcador J{p['jornada']}", expanded=False):
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
                                    # (Asegúrate de que la función leer_marcador_ia esté definida arriba)
                                    res_ia, mensaje_ia = leer_marcador_ia(foto, p['local'], p['visitante'])
                                    
                                    if res_ia is None:
                                        st.error(mensaje_ia)
                                    else:
                                        gl_ia, gv_ia = res_ia
                                        st.info(f"🤖 IA detectó marcador: {gl_ia} - {gv_ia}")

                                        try:
                                            # Rebobinamos el archivo
                                            foto.seek(0)
                                            
                                            # 2. Subida a Cloudinary
                                            res_cloud = cloudinary.uploader.upload(foto, folder="gol_gana_evidencias")
                                            url_nueva = res_cloud['secure_url']
                                            
                                            col_foto = "url_foto_l" if es_local else "url_foto_v"

                                            # 3. Lógica de Consenso / Conflicto (Escritura segura Neon)
                                            with conn.connect() as db:
                                                gl_existente = p['goles_l']
                                                gv_existente = p['goles_v']

                                                # Si ya hay reporte previo (del rival)
                                                # Convertimos a int si existen para poder comparar
                                                if gl_existente is not None:
                                                    # Comparación
                                                    if int(gl_existente) != gl_ia or int(gv_existente) != gv_ia:
                                                        # CONFLICTO
                                                        # Usamos :params para seguridad
                                                        query_conf = text(f"""
                                                            UPDATE partidos SET 
                                                            goles_l=NULL, goles_v=NULL, 
                                                            conflicto=1, {col_foto}=:url, 
                                                            ia_goles_l=:gl, ia_goles_v=:gv 
                                                            WHERE id=:id
                                                        """)
                                                        db.execute(query_conf, {
                                                            "url": url_nueva, "gl": gl_ia, "gv": gv_ia, "id": p['id']
                                                        })
                                                        st.warning("⚠️ Conflicto: Los resultados no coinciden. El Admin decidirá.")
                                                    else:
                                                        # CONSENSO
                                                        query_ok = text(f"""
                                                            UPDATE partidos SET 
                                                            {col_foto}=:url, conflicto=0, estado='Finalizado' 
                                                            WHERE id=:id
                                                        """)
                                                        db.execute(query_ok, {"url": url_nueva, "id": p['id']})
                                                        st.success("✅ ¡Marcador verificado y finalizado!")
                                                else:
                                                    # PRIMER REPORTE
                                                    query_first = text(f"""
                                                        UPDATE partidos SET 
                                                        goles_l=:gl, goles_v=:gv, 
                                                        {col_foto}=:url, ia_goles_l=:gl, 
                                                        ia_goles_v=:gv, estado='Revision' 
                                                        WHERE id=:id
                                                    """)
                                                    db.execute(query_first, {
                                                        "gl": gl_ia, "gv": gv_ia, "url": url_nueva, "id": p['id']
                                                    })
                                                    st.success("⚽ Resultado guardado. Esperando reporte del rival.")
                                                
                                                db.commit() # ¡Importante guardar cambios!
                                            
                                            time.sleep(1.5)
                                            st.rerun()

                                        except Exception as e:
                                            st.error(f"❌ Error al procesar: {e}")
                    
                    st.markdown("<hr style='margin:10px 0; opacity:0.2;'>", unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Error cargando partidos: {e}")
  #########


  
  
# --- TAB: GESTIÓN ADMIN (Completo con Diseño Dinámico) ---
if rol == "admin":
    with tabs[2]:
        st.header("⚙️ Panel de Control Admin")
        
        # --- 1. SECCIÓN DE APROBACIONES ---
        st.subheader("📩 Equipos por Aprobar")
        
        try:
            # Lectura segura con SQLAlchemy
            pend = pd.read_sql_query(text("SELECT * FROM equipos WHERE estado='pendiente'"), conn)
            
            # Contamos aprobados
            res_count = pd.read_sql_query(text("SELECT count(*) FROM equipos WHERE estado='aprobado'"), conn)
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
                    
                    # COLUMNA 1: VISTA PREVIA
                    with col_img:
                        if r['escudo']:
                            st.image(r['escudo'], width=60)
                        else:
                            st.write("❌")

                    # COLUMNA 2: DATOS
                    with col_data:
                        st.markdown(f"**{r['nombre']}**")
                        st.markdown(f"<a href='{wa_link}' style='color: #25D366; text-decoration: none; font-weight: bold; font-size: 0.9em;'>📞 Contactar DT</a>", unsafe_allow_html=True)
                        if not r['escudo']: st.caption("⚠️ Sin escudo")
                    
                    # COLUMNA 3: APROBAR
                    with col_btn:
                        if st.button(f"✅", key=f"aprob_{r['nombre']}", help="Aprobar equipo", use_container_width=True):
                            url_final = r['escudo']
                            
                            # Procesamiento IA Cloudinary (Quitar fondo escudo)
                            if url_final:
                                with st.spinner("🤖 Limpiando escudo..."):
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
                            
                            # Guardar en NEON
                            try:
                                with conn.connect() as db:
                                    db.execute(
                                        text("UPDATE equipos SET estado='aprobado', escudo=:e WHERE nombre=:n"),
                                        {"e": url_final, "n": r['nombre']}
                                    )
                                    db.commit()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error DB: {e}")

                st.markdown("---") 
        else:
            st.info("No hay equipos pendientes.")

        st.divider()

        # --- 2. SELECCIÓN DE TAREA (Aquí añadimos la opción de Diseño) ---
        opcion_admin = st.radio("Tarea:", ["⚽ Resultados", "🛠️ Directorio de Equipos", "🎨 Diseño Web"], horizontal=True, key="adm_tab")
        
        # --- A. OPCIÓN: DIRECTORIO ---
        if opcion_admin == "🛠️ Directorio de Equipos":
            st.subheader("📋 Directorio de Equipos")
            
            try:
                df_maestro = pd.read_sql_query(text("SELECT * FROM equipos ORDER BY nombre"), conn)
            except:
                df_maestro = pd.DataFrame()

            if not df_maestro.empty:
                for _, eq in df_maestro.iterrows():
                    estado_icon = "✅" if eq['estado'] == 'aprobado' else "⏳"
                    escudo_mini = f'<img src="{eq["escudo"]}" width="20" style="vertical-align:middle; margin-right:5px">' if eq['escudo'] else ""
                    st.markdown(f"{estado_icon} {escudo_mini} **{eq['nombre']}** | 🔑 {eq['pin']} | 📞 {eq['prefijo']} {eq['celular']}", unsafe_allow_html=True)
                
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
                        if datos_sel['escudo']:
                            st.image(datos_sel['escudo'], width=100, caption="Escudo Actual")
                            
                        nuevo_escudo_img = st.file_uploader("Subir nuevo escudo", type=['png', 'jpg', 'jpeg'])
                        quitar_escudo = st.checkbox("❌ Eliminar escudo actual")
                        
                        if st.form_submit_button("💾 Guardar Cambios", use_container_width=True):
                            url_final = datos_sel['escudo']
                            if quitar_escudo: url_final = None
                            elif nuevo_escudo_img:
                                res_std = cloudinary.uploader.upload(nuevo_escudo_img, folder="escudos_limpios")
                                url_final = res_std['secure_url']

                            try:
                                with conn.connect() as db:
                                    db.execute(
                                        text("UPDATE equipos SET nombre=:nn, pin=:np, escudo=:ne WHERE nombre=:viejo"),
                                        {"nn": new_name, "np": new_pin, "ne": url_final, "viejo": equipo_sel}
                                    )
                                    db.commit()
                                st.success(f"✅ ¡{new_name} actualizado!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error actualizando: {e}")

                    if st.button(f"✖️ Eliminar: {equipo_sel}", use_container_width=True):
                        with conn.connect() as db:
                            db.execute(text("DELETE FROM equipos WHERE nombre = :n"), {"n": equipo_sel})
                            db.commit()
                        st.error(f"Equipo eliminado.")
                        st.rerun()
            else:
                st.info("No hay equipos registrados.")

        # --- B. OPCIÓN: DISEÑO WEB (NUEVA FUNCIONALIDAD) ---
        elif opcion_admin == "🎨 Diseño Web":
            st.subheader("🎨 Personalización Automática")
            st.info("Selecciona un equipo para 'vestir' la web con sus colores y escudo.")
            
            with conn.connect() as db:
                # Solo traemos equipos aprobados con escudo
                equipos_con_escudo = db.execute(text("SELECT nombre, escudo FROM equipos WHERE estado = 'aprobado' AND escudo IS NOT NULL")).fetchall()

            if not equipos_con_escudo:
                st.warning("No hay equipos aprobados con escudo disponibles.")
            else:
                opciones_equipos = {eq[0]: eq[1] for eq in equipos_con_escudo}
                nombre_seleccionado = st.selectbox("Equipo Inspiración:", list(opciones_equipos.keys()))
                
                url_escudo_elegido = opciones_equipos[nombre_seleccionado]
                col_prev, col_action = st.columns([1, 2])
                with col_prev:
                    st.image(url_escudo_elegido, width=80, caption="Escudo Base")
                
                with col_action:
                    if st.button(f"✨ Aplicar Estilo de: {nombre_seleccionado}", type="primary", use_container_width=True):
                        try:
                            # 1. Detectar Color
                            with st.spinner("🕵️ Analizando colores del equipo..."):
                                color_detectado = motor_colores.obtener_color_dominante(url_escudo_elegido)
                            
                            # 2. Generar Imagen (Sándwich)
                            with st.spinner(f"🧑‍🎨 Diseñando portada con color {color_detectado}..."):
                                imagen_final_pil = motor_grafico.construir_portada(color_detectado, url_escudo_elegido)
                                
                                buffer_subida = BytesIO()
                                imagen_final_pil.save(buffer_subida, format="PNG")
                                buffer_subida.seek(0)
                            
                            # 3. Subir y Guardar
                            with st.spinner("☁️ Subiendo a la nube..."):
                                res = cloudinary.uploader.upload(
                                    buffer_subida, 
                                    folder="fondos_dinamicos",
                                    public_id="fondo_web_v2", 
                                    overwrite=True
                                )
                                nueva_url_fondo = f"{res['secure_url']}?v={int(time.time())}" # Cache buster
                                
                                with conn.connect() as db:
                                    # Guardamos en tabla configuracion (Upsert manual)
                                    # Nota: Asegúrate de haber creado la tabla configuracion en Neon
                                    check = db.execute(text("SELECT 1 FROM configuracion WHERE clave='fondo_url'")).fetchone()
                                    if check:
                                        db.execute(text("UPDATE configuracion SET valor=:v WHERE clave='fondo_url'"), {"v": nueva_url_fondo})
                                        db.execute(text("UPDATE configuracion SET valor=:v WHERE clave='color_primario'"), {"v": color_detectado})
                                    else:
                                        db.execute(text("INSERT INTO configuracion (clave, valor) VALUES ('fondo_url', :v)"), {"v": nueva_url_fondo})
                                        db.execute(text("INSERT INTO configuracion (clave, valor) VALUES ('color_primario', :v)"), {"v": color_detectado})
                                    db.commit()
                            
                            st.balloons()
                            st.success("✅ ¡Diseño actualizado con éxito!")
                            time.sleep(1) # Pausa dramática
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"Error en el proceso gráfico: {e}")


        # --- 3. ACCIONES MAESTRAS (Sin cambios) ---
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
                    # Asumimos que existe tabla config o similar para la fase
                    # db.execute(text("UPDATE config SET valor='inscripcion' WHERE clave='fase_actual'"))
                    db.commit()
                st.session_state.clear()
                st.rerun()











import streamlit as st
import easyocr
import sqlite3
import pandas as pd
import re
import numpy as np
from PIL import Image
from datetime import datetime

# --- 1. CONFIGURACIÓN INICIAL ---
EQUIPOS_ACEPTADOS = [
    'ATLINTERGOL', 'PLMX ALEBRIJES', 'UNITED PLEBES', 'ATLAS MX', 
    'PLMX TIGRES A', 'KENNEDY MAS10', 'CHILUDOS FC', 'THE BOYZFC', 
    'BLACK DEMONDS', 'TRAKA', 'ESPARTAFC'
]
DB_NAME = "torneo_fifa.db"

def inicializar_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historial (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            local TEXT,
            goles_l INTEGER,
            goles_v INTEGER,
            visitante TEXT,
            imagen TEXT UNIQUE
        )
    ''')
    conn.commit()
    return conn

def normalizar_nombre(texto):
    t_limpio = texto.upper().replace(" ", "")
    for e in EQUIPOS_ACEPTADOS:
        if e.upper().replace(" ", "") in t_limpio or t_limpio in e.upper().replace(" ", ""):
            return e
    return None

# --- 2. CONFIGURACIÓN DE LA PÁGINA WEB ---
st.set_page_config(page_title="Gestor Torneo FIFA IA", layout="wide")
st.title("🏆 Administrador de Torneo con IA")
st.markdown("Sube la captura del marcador y la IA actualizará la tabla automáticamente.")

# Creamos dos columnas: Izquierda para subir fotos, Derecha para resultados
col1, col2 = st.columns([1, 1.5])

# --- 3. COLUMNA IZQUIERDA: PROCESAMIENTO ---
with col1:
    st.header("📸 Subir Resultado")
    uploaded_file = st.file_uploader("Arrastra aquí la imagen del partido", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption='Imagen detectada', use_container_width=True)
        
        if st.button('🚀 Procesar Marcador'):
            with st.spinner('Analizando imagen con Inteligencia Artificial...'):
                # Convertir imagen para el lector
                img_array = np.array(image)
                reader = easyocr.Reader(['es'], gpu=False)
                resultados = reader.readtext(img_array)
                
                # Buscar el marcador (ejemplo: 4 - 5)
                patron = re.compile(r'(\d+)\s*-\s*(\d+)')
                exito = False
                
                for i, (bbox, texto, prob) in enumerate(resultados):
                    match = patron.search(texto)
                    if match:
                        gl, gv = int(match.group(1)), int(match.group(2))
                        el = None; ev = None
                        
                        # Buscar nombres de equipos en los textos cercanos
                        entorno = resultados[max(0, i-4):min(len(resultados), i+5)]
                        for _, txt, _ in entorno:
                            n = normalizar_nombre(txt)
                            if n:
                                if not el: el = n
                                elif n != el: ev = n
                        
                        if el and ev:
                            try:
                                conn = inicializar_db()
                                cursor = conn.cursor()
                                cursor.execute('''
                                    INSERT INTO historial (fecha, local, goles_l, goles_v, visitante, imagen)
                                    VALUES (?, ?, ?, ?, ?, ?)
                                ''', (datetime.now().strftime("%d/%m/%Y %H:%M"), el, gl, gv, ev, uploaded_file.name))
                                conn.commit()
                                conn.close()
                                st.success(f"✅ ¡Partido Registrado! {el} {gl} - {gv} {ev}")
                                exito = True
                            except sqlite3.IntegrityError:
                                st.info("ℹ️ Este resultado ya fue registrado anteriormente.")
                                exito = True
                        break
                
                if not exito:
                    st.error("No se detectaron equipos válidos. Revisa que los nombres coincidan con la lista oficial.")

# --- 4. COLUMNA DERECHA: TABLA Y HISTORIAL ---
with col2:
    st.header("📊 Tabla de Clasificación")
    
    conn = inicializar_db()
    df_partidos = pd.read_sql_query("SELECT local, goles_l, goles_v, visitante FROM historial", conn)
    
    # Diccionario para calcular estadísticas
    stats = {e: {'PJ':0, 'G':0, 'E':0, 'P':0, 'GF':0, 'GC':0, 'Pts':0} for e in EQUIPOS_ACEPTADOS}
    
    for _, fila in df_partidos.iterrows():
        l, gl, gv, v = fila['local'], fila['goles_l'], fila['goles_v'], fila['visitante']
        for equipo, goles_f, goles_c in [(l, gl, gv), (v, gv, gl)]:
            stats[equipo]['PJ'] += 1
            stats[equipo]['GF'] += goles_f
            stats[equipo]['GC'] += goles_c
        if gl > gv:
            stats[l]['Pts'] += 3; stats[l]['G'] += 1; stats[v]['P'] += 1
        elif gv > gl:
            stats[v]['Pts'] += 3; stats[v]['G'] += 1; stats[l]['P'] += 1
        else:
            stats[l]['Pts'] += 1; stats[v]['Pts'] += 1; stats[l]['E'] += 1; stats[v]['E'] += 1

    # 1. Crear DataFrame y calcular DG
    tabla_df = pd.DataFrame.from_dict(stats, orient='index').reset_index()
    tabla_df.columns = ['Equipo', 'PJ', 'G', 'E', 'P', 'GF', 'GC', 'Pts']
    tabla_df['DG'] = tabla_df['GF'] - tabla_df['GC']
    
    # 2. Ordenar por Puntos y DG
    tabla_df = tabla_df[tabla_df['PJ'] > 0].sort_values(by=['Pts', 'DG'], ascending=False)
    
    # 3. CREAR COLUMNA POSICIÓN (Enumeración real 1, 2, 3...)
    tabla_df.insert(0, 'POS', range(1, len(tabla_df) + 1))
    
    # 4. REORGANIZAR COLUMNAS: POS, EQUIPO, PTS, PJ, ...
    columnas_ordenadas = ['POS', 'Equipo', 'Pts', 'PJ', 'G', 'E', 'P', 'GF', 'GC', 'DG']
    tabla_df = tabla_df[columnas_ordenadas]
    
    # 5. Mostrar la tabla final
    st.dataframe(
        tabla_df, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "POS": st.column_config.NumberColumn("Pos", format="%d"),
            "Pts": st.column_config.NumberColumn("Pts", help="Puntos Totales"),
            "Equipo": st.column_config.TextColumn("Equipo")
        }
    )

    # --- HISTORIAL POR PARTIDO ---
    st.header("📝 Últimos Encuentros")
    df_historial = pd.read_sql_query("SELECT local, goles_l, goles_v, visitante FROM historial ORDER BY id DESC", conn)
    
    if df_historial.empty:
        st.write("Aún no hay partidos registrados.")
    else:
        for _, r in df_historial.iterrows():
            st.write(f"({r['local']} {r['goles_l']} - {r['goles_v']} {r['visitante']})")
    
    conn.close()


# --- 5. BARRA LATERAL (SEGURIDAD Y CONFIGURACIÓN) ---
st.sidebar.title("🔐 Administración")
password = st.sidebar.text_input("Contraseña de Admin", type="password")

# Definimos una contraseña simple para tus pruebas
PASSWORD_CORRECTA = "admin123" 

if password == PASSWORD_CORRECTA:
    st.sidebar.success("Modo Administrador Activo")
    
    st.sidebar.divider()
    st.sidebar.subheader("Acciones Críticas")
    
    # Botón de Reset Total
    if st.sidebar.button("🚨 RESET TOTAL DEL TORNEO"):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            # Borramos todos los registros del historial
            cursor.execute("DELETE FROM historial")
            # Reiniciamos el contador de IDs para que el siguiente partido sea el ID 1
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='historial'")
            conn.commit()
            st.sidebar.success("¡Base de datos limpiada por completo!")
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Error al limpiar: {e}")
        finally:
            conn.close()
            
    st.sidebar.info("Nota: Este botón elimina todos los partidos y estadísticas. Los equipos aceptados se mantienen según la lista inicial.")

else:
    if password != "":
        st.sidebar.error("Contraseña incorrecta")
    st.sidebar.warning("Ingresa la clave para subir resultados o resetear el torneo.")
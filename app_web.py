import streamlit as st
import easyocr
import sqlite3
import pandas as pd
import re
import numpy as np
from PIL import Image
from datetime import datetime

# --- CONFIGURACIÓN Y ESTILOS ---
DB_NAME = "gol_gana.db"
ADMIN_PIN = "2025"  # Tu clave maestra

st.set_page_config(page_title="Gol-Gana", layout="centered")

# CSS para que se vea mejor en móviles
st.markdown("""
    <style>
    .stApp { max-width: 600px; margin: 0 auto; }
    .whatsapp-link { color: #25D366; text-decoration: none; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- BASE DE DATOS ---
def inicializar_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # LÍNEA TEMPORAL para borrar bd: cursor.execute("DROP TABLE IF EXISTS equipos")
        cursor.execute('''CREATE TABLE IF NOT EXISTS equipos (
        nombre TEXT PRIMARY KEY, celular TEXT, prefijo TEXT, pin TEXT, estado TEXT DEFAULT 'pendiente'
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS historial (
        id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, local TEXT, goles_l INTEGER, goles_v INTEGER, visitante TEXT
    )''')
    conn.commit()
    return conn

conn = inicializar_db()

# --- CABECERA Y PIN (SIEMPRE VISIBLE) ---
st.title("⚽ Gol-Gana")
col_pin, col_esp = st.columns([1, 1])
with col_pin:
    user_pin = st.text_input("🔑 PIN de Acceso", type="password", help="Ingresa tu PIN para gestionar")

# Determinar Rol
rol = "espectador"
equipo_usuario = None
if user_pin == ADMIN_PIN:
    rol = "admin"
elif user_pin != "":
    cur = conn.cursor()
    cur.execute("SELECT nombre FROM equipos WHERE pin = ? AND estado = 'aprobado'", (user_pin,))
    res = cur.fetchone()
    if res:
        rol = "dt"
        equipo_usuario = res[0]

# --- VISTA ESPECTADOR (TABLA Y REGISTRO) ---
if rol == "espectador":
    tab1, tab2 = st.tabs(["📊 Clasificación", "📝 Inscribirse"])

    with tab1:
        # Obtener todos los equipos aprobados
        cur = conn.cursor()
        cur.execute("SELECT nombre, prefijo, celular FROM equipos WHERE estado = 'aprobado'")
        equipos_db = cur.fetchall()
        
        if not equipos_db:
            st.info("Esperando aprobación de equipos...")
        else:
            # Inicializar estadísticas en 0 para todos
            stats = {e[0]: {'PJ':0, 'Pts':0, 'DG':0, 'GF':0, 'GC':0, 'WA': f"https://wa.me/{e[1].replace('+','')}{e[2]}"} for e in equipos_db}
            
            # Cargar partidos
            df_p = pd.read_sql_query("SELECT * FROM historial", conn)
            for _, fila in df_p.iterrows():
                l, gl, gv, v = fila['local'], fila['goles_l'], fila['goles_v'], fila['visitante']
                if l in stats and v in stats:
                    stats[l]['PJ'] += 1; stats[v]['PJ'] += 1
                    stats[l]['GF'] += gl; stats[l]['GC'] += gv
                    stats[v]['GF'] += gv; stats[v]['GC'] += gl
                    if gl > gv: stats[l]['Pts'] += 3
                    elif gv > gl: stats[v]['Pts'] += 3
                    else: stats[l]['Pts'] += 1; stats[v]['Pts'] += 1

            # Crear DataFrame
            df_final = pd.DataFrame.from_dict(stats, orient='index').reset_index()
            df_final.columns = ['Equipo', 'PJ', 'Pts', 'DG', 'GF', 'GC', 'WA_Link']
            df_final['DG'] = df_final['GF'] - df_final['GC']
            df_final = df_final.sort_values(by=['Pts', 'DG'], ascending=False)
            df_final.insert(0, 'Pos', range(1, len(df_final) + 1))

            # Mostrar tabla con link de WhatsApp
            st.write("Toca el nombre para ir al WhatsApp del DT:")
            for _, row in df_final.iterrows():
                with st.container():
                    c1, c2, c3 = st.columns([1, 4, 2])
                    c1.write(f"#{row['Pos']}")
                    c2.markdown(f"[{row['Equipo']}]({row['WA_Link']})", unsafe_allow_html=True)
                    c3.write(f"**{row['Pts']} Pts** ({row['PJ']}pj)")
                    st.divider()

    with tab2:
        st.subheader("Formulario de Inscripción")
        with st.form("registro"):
            nombre_e = st.text_input("Nombre del Equipo")
            prefijos = {"Colombia": "+57", "México": "+52", "Venezuela": "+58", "Argentina": "+54", "España": "+34", "Otros": "+1"}
            pais = st.selectbox("País", list(prefijos.keys()))
            whatsapp = st.text_input("Número de WhatsApp (Sin prefijo)")
            nuevo_pin = st.text_input("Crea tu PIN (4 números)", max_chars=4)
            
            if st.form_submit_button("Enviar"):
                if nombre_e and whatsapp and nuevo_pin:
                    try:
                        conn.execute("INSERT INTO equipos (nombre, celular, prefijo, pin) VALUES (?, ?, ?, ?)",
                                     (nombre_e, whatsapp, prefijos[pais], nuevo_pin))
                        conn.commit()
                        st.success("✅ Solicitud enviada. Espera la aprobación del Admin.")
                    except:
                        st.error("Error: El nombre o PIN ya existen.")

# --- VISTA ADMIN ---
elif rol == "admin":
    st.header("👑 Panel Admin")
    pendientes = pd.read_sql_query("SELECT nombre, celular, prefijo FROM equipos WHERE estado = 'pendiente'", conn)
    
    if not pendientes.empty:
        st.write("Solicitudes nuevas:")
        st.dataframe(pendientes, hide_index=True)
        aprobar = st.selectbox("Aprobar equipo:", [""] + list(pendientes['nombre']))
        if st.button("Aprobar Ahora") and aprobar:
            conn.execute("UPDATE equipos SET estado = 'aprobado' WHERE nombre = ?", (aprobar,))
            conn.commit()
            st.rerun()
    else:
        st.info("No hay equipos pendientes.")

    if st.button("🚨 RESET TOTAL"):
        conn.execute("DELETE FROM historial"); conn.execute("DELETE FROM equipos")
        conn.commit(); st.rerun()

# --- VISTA DT ---
elif rol == "dt":
    st.header(f"🎮 Panel de {equipo_usuario}")
    st.info("Sube la captura de tu partido para actualizar la tabla.")
    archivo = st.file_uploader("Captura de pantalla", type=['jpg', 'png'])
    if archivo:
        st.image(archivo)
        if st.button("Analizar con IA"):
            st.warning("IA Procesando... (Implementando lógica de EasyOCR personalizada)")
            # Aquí se integra el lector que ya teníamos



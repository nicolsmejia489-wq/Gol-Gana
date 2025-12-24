import streamlit as st
import easyocr
import sqlite3
import pandas as pd
import re
import numpy as np
from PIL import Image
from datetime import datetime

# --- CONFIGURACIÓN ---
DB_NAME = "gol_gana.db"
ADMIN_PIN = "2025"  # Cambia este PIN por el que tú quieras

# --- BASE DE DATOS MEJORADA ---
def inicializar_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Tabla de Equipos (Aprobados y Pendientes)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS equipos (
            nombre TEXT PRIMARY KEY,
            celular TEXT,
            pin TEXT,
            estado TEXT DEFAULT 'pendiente' 
        )
    ''')
    # Tabla de Partidos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historial (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT, local TEXT, goles_l INTEGER, goles_v INTEGER, visitante TEXT, imagen TEXT UNIQUE
        )
    ''')
    conn.commit()
    return conn

conn = inicializar_db()

# --- LÓGICA DE USUARIOS ---
st.sidebar.title("⚽ Gol-Gana")
user_pin = st.sidebar.text_input("Ingresa tu PIN de Acceso", type="password")

# Determinamos el Rol
rol = "espectador"
equipo_usuario = None

if user_pin == ADMIN_PIN:
    rol = "admin"
    st.sidebar.success("Modo: Administrador")
elif user_pin != "":
    # Buscamos si el PIN pertenece a un equipo aprobado
    cur = conn.cursor()
    cur.execute("SELECT nombre FROM equipos WHERE pin = ? AND estado = 'aprobado'", (user_pin,))
    res = cur.fetchone()
    if res:
        rol = "dt"
        equipo_usuario = res[0]
        st.sidebar.success(f"Modo: DT - {equipo_usuario}")
    else:
        st.sidebar.error("PIN no reconocido o equipo pendiente")

# --- FUNCIONES DE NORMALIZACIÓN ---
def obtener_equipos_aprobados():
    cur = conn.cursor()
    cur.execute("SELECT nombre FROM equipos WHERE estado = 'aprobado'")
    return [r[0] for r in cur.fetchall()]

def normalizar_nombre(texto, lista_equipos):
    t_limpio = texto.upper().replace(" ", "")
    for e in lista_equipos:
        if e.upper().replace(" ", "") in t_limpio:
            return e
    return None

# --- VISTA: ESPECTADOR ---
st.title("🏆 Torneo Gol-Gana")

if rol == "espectador":
    tab1, tab2 = st.tabs(["📊 Clasificación", "📝 Inscripción"])
    
    with tab1:
        # Aquí va la lógica de la tabla que ya teníamos (filtrando por equipos aprobados)
        equipos_oficiales = obtener_equipos_aprobados()
        if not equipos_oficiales:
            st.info("El torneo aún no tiene equipos aprobados.")
        else:
            # (Lógica de procesamiento de tabla similar a la anterior...)
            df_p = pd.read_sql_query("SELECT * FROM historial", conn)
            stats = {e: {'PJ':0, 'Pts':0, 'DG':0} for e in equipos_oficiales}
            # ... [Cálculo de estadísticas] ...
            st.write("Tabla de posiciones oficial")
            # Mostrar tabla ordenada
            
    with tab2:
        st.header("📩 Inscribe a tu Equipo")
        with st.form("form_inscripcion"):
            nombre = st.text_input("Nombre del Equipo")
            cel = st.text_input("WhatsApp (10 dígitos)")
            pin_dt = st.text_input("Crea tu PIN de acceso (4 números)", max_chars=4)
            if st.form_submit_button("Enviar Solicitud"):
                if nombre and cel and pin_dt:
                    try:
                        cur = conn.cursor()
                        cur.execute("INSERT INTO equipos (nombre, celular, pin) VALUES (?, ?, ?)", (nombre, cel, pin_dt))
                        conn.commit()
                        st.success("¡Solicitud enviada! El admin te avisará cuando estés aprobado.")
                    except:
                        st.error("Ese nombre de equipo ya está registrado.")

# --- VISTA: ADMIN ---
if rol == "admin":
    st.header("🛠️ Panel de Control")
    
    # Gestión de Equipos
    st.subheader("Equipos Pendientes")
    pendientes = pd.read_sql_query("SELECT nombre, celular FROM equipos WHERE estado = 'pendiente'", conn)
    st.dataframe(pendientes)
    
    equipo_a_aprobar = st.selectbox("Selecciona equipo para aprobar", [""] + list(pendientes['nombre']))
    if st.button("Aprobar Equipo") and equipo_a_aprobar:
        conn.execute("UPDATE equipos SET estado = 'aprobado' WHERE nombre = ?", (equipo_a_aprobar,))
        conn.commit()
        st.rerun()

    if st.button("🚨 RESET TOTAL"):
        conn.execute("DELETE FROM historial"); conn.execute("DELETE FROM equipos")
        conn.commit(); st.rerun()

# --- VISTA: DT ---
if rol == "dt":
    st.header(f"📱 Panel de {equipo_usuario}")
    uploaded_file = st.file_uploader("Sube la foto del marcador", type=["jpg", "png"])
    # Aquí iría el código de EasyOCR que ya tenemos...

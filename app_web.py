import streamlit as st
import sqlite3
import pandas as pd

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Gol-Gana", layout="centered", page_icon="⚽")

# --- BASE DE DATOS (Lógica Robusta) ---
DB_NAME = "gol_gana.db"
ADMIN_PIN = "2025"

def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

# Crear tablas si no existen
conn = get_connection()
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS equipos (
    nombre TEXT PRIMARY KEY, celular TEXT, prefijo TEXT, pin TEXT, estado TEXT DEFAULT 'pendiente'
)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS historial (
    id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, local TEXT, goles_l INTEGER, goles_v INTEGER, visitante TEXT
)''')
conn.commit()

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .stApp { max-width: 600px; margin: 0 auto; }
    .stButton>button { width: 100%; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- GESTIÓN DE SESIÓN ---
if 'confirmado' not in st.session_state: st.session_state.confirmado = False
if 'rol' not in st.session_state: st.session_state.rol = "espectador"
if 'equipo_usuario' not in st.session_state: st.session_state.equipo_usuario = None
if 'datos_temp' not in st.session_state: st.session_state.datos_temp = None

# --- BOTÓN ATRÁS UNIVERSAL ---
if st.session_state.rol != "espectador" or st.session_state.confirmado:
    if st.button("⬅️ Volver a la Tabla Principal"):
        st.session_state.confirmado = False
        st.session_state.rol = "espectador"
        st.session_state.equipo_usuario = None
        st.session_state.datos_temp = None
        st.rerun()

st.title("⚽ Gol-Gana")

# --- LOGIN ---
if st.session_state.rol == "espectador":
    with st.expander("🔑 Acceso para DTs y Admin"):
        with st.form("login_form"):
            pin_input = st.text_input("Introduce tu PIN", type="password")
            if st.form_submit_button("Entrar"):
                if pin_input == ADMIN_PIN:
                    st.session_state.rol = "admin"
                    st.rerun()
                elif pin_input != "":
                    conn = get_connection()
                    cur = conn.cursor()
                    cur.execute("SELECT nombre FROM equipos WHERE pin = ? AND estado = 'aprobado'", (pin_input,))
                    res = cur.fetchone()
                    if res:
                        st.session_state.rol = "dt"
                        st.session_state.equipo_usuario = res[0]
                        st.rerun()
                    else:
                        st.error("PIN incorrecto o equipo no aprobado.")

# --- VISTA: ESPECTADOR ---
if st.session_state.rol == "espectador":
    tab1, tab2 = st.tabs(["📊 Clasificación", "📝 Inscribirse"])

    with tab1:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT nombre, prefijo, celular FROM equipos WHERE estado = 'aprobado'")
        equipos_db = cur.fetchall()
        if not equipos_db:
            st.info("No hay equipos aprobados aún.")
        else:
            for nombre_e, pref, cel in equipos_db:
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    c1.write(f"**{nombre_e}**")
                    c2.markdown(f"[💬 WA](https://wa.me/{pref.replace('+','')}{cel})")

    with tab2:
        if not st.session_state.confirmado:
            with st.form("registro"):
                st.subheader("📩 Inscripción")
                nombre_e = st.text_input("Nombre del Equipo")
                whatsapp = st.text_input("WhatsApp (Sin prefijo)")
                nuevo_pin = st.text_input("PIN (4 dígitos)", max_chars=4, type="password")
                if st.form_submit_button("Revisar Datos"):
                    if not nombre_e or not whatsapp or len(nuevo_pin) < 4:
                        st.error("Completa los campos correctamente.")
                    else:
                        st.session_state.datos_temp = {"nombre": nombre_e, "wa": whatsapp, "pin": nuevo_pin}
                        st.session_state.confirmado = True
                        st.rerun()
        else:
            d = st.session_state.datos_temp
            st.warning("Confirma tus datos:")
            st.write(f"**Equipo:** {d['nombre']} | **WA:** {d['wa']}")
            if st.button("🚀 Confirmar Registro"):
                conn = get_connection()
                try:
                    conn.execute("INSERT INTO equipos (nombre, celular, prefijo, pin, estado) VALUES (?,?,'+57',?,'pendiente')", 
                                 (d['nombre'], d['wa'], d['pin']))
                    conn.commit()
                    st.success("Enviado. Espera aprobación del Admin.")
                    st.session_state.confirmado = False
                    st.rerun()
                except:
                    st.error("Error: El equipo o PIN ya existe.")

# --- VISTA: ADMIN (Corregida para ver pendientes) ---
elif st.session_state.rol == "admin":
    st.header("🛠️ Panel Admin")
    st.subheader("📋 Equipos por Aprobar")
    
    conn = get_connection()
    cur = conn.cursor()
    # Forzamos la consulta para ver qué hay en la DB
    cur.execute("SELECT nombre, celular FROM equipos WHERE estado = 'pendiente'")
    pendientes = cur.fetchall()
    
    if not pendientes:
        st.info("No hay solicitudes pendientes.")
    else:
        for nombre_e, cel in pendientes:
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                c1.write(f"**Equipo:** {nombre_e} | **Tel:** {cel}")
                # Botón verde de Aceptar
                if c2.button("✅ Aceptar", key=f"key_{nombre_e}"):
                    conn = get_connection()
                    conn.execute("UPDATE equipos SET estado = 'aprobado' WHERE nombre = ?", (nombre_e,))
                    conn.commit()
                    st.success(f"{nombre_e} aprobado")
                    st.rerun()

    if st.button("🚨 BORRAR TODO"):
        conn = get_connection()
        conn.execute("DELETE FROM equipos"); conn.execute("DELETE FROM historial"); conn.commit()
        st.rerun()

# --- VISTA: DT ---
elif st.session_state.rol == "dt":
    st.header(f"🎮 DT: {st.session_state.equipo_usuario}")
    st.write("Panel de gestión de resultados (Próximamente)")

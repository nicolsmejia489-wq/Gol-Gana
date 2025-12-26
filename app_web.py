import streamlit as st
import sqlite3
import pandas as pd

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Gol-Gana", layout="centered", page_icon="⚽")
DB_NAME = "gol_gana.db"
ADMIN_PIN = "2025"

# --- ESTILOS ---
st.markdown("""
    <style>
    .stApp { max-width: 600px; margin: 0 auto; }
    .stButton>button { width: 100%; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

def inicializar_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS equipos (
        nombre TEXT PRIMARY KEY, celular TEXT, prefijo TEXT, pin TEXT, estado TEXT DEFAULT 'pendiente'
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS historial (
        id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, local TEXT, goles_l INTEGER, goles_v INTEGER, visitante TEXT
    )''')
    conn.commit()
    return conn

conn = inicializar_db()

# --- GESTIÓN DE SESIÓN (PERSISTENCIA) ---
if 'confirmado' not in st.session_state: st.session_state.confirmado = False
if 'rol' not in st.session_state: st.session_state.rol = "espectador"
if 'equipo_usuario' not in st.session_state: st.session_state.equipo_usuario = None
if 'datos_temp' not in st.session_state: st.session_state.datos_temp = None

# --- BOTÓN ATRÁS / CERRAR SESIÓN ---
if st.button("⬅️ Volver al Inicio / Cerrar Sesión"):
    st.session_state.confirmado = False
    st.session_state.rol = "espectador"
    st.session_state.equipo_usuario = None
    st.session_state.datos_temp = None
    st.rerun()

st.title("⚽ Gol-Gana")

# --- LOGIN SEPARADO (PROTECCIÓN ADMIN) ---
if st.session_state.rol == "espectador":
    with st.expander("🔑 Acceso para DTs y Admin"):
        with st.form("login_form"):
            pin_input = st.text_input("Introduce tu PIN", type="password")
            if st.form_submit_button("Entrar"):
                if pin_input == ADMIN_PIN:
                    st.session_state.rol = "admin"
                    st.rerun()
                elif pin_input != "":
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
        # (Lógica de tabla simplificada para visualización)
        cur = conn.cursor()
        cur.execute("SELECT nombre, prefijo, celular FROM equipos WHERE estado = 'aprobado'")
        equipos_db = cur.fetchall()
        if not equipos_db:
            st.info("Aún no hay equipos aprobados.")
        else:
            # Aquí iría el cálculo de la tabla que ya tenemos
            st.write("Tabla de Posiciones Próximamente...")

    with tab2:
        # DICCIONARIO DE PAÍSES
        paises_data = {
            "Argentina": "+54", "Bolivia": "+591", "Brasil": "+55", "Canadá": "+1",
            "Chile": "+56", "Colombia": "+57", "Costa Rica": "+506", "Cuba": "+53",
            "Ecuador": "+593", "El Salvador": "+503", "España": "+34", "Estados Unidos": "+1",
            "Guatemala": "+502", "Honduras": "+504", "México": "+52", "Nicaragua": "+505",
            "Panamá": "+507", "Paraguay": "+595", "Perú": "+51", "Puerto Rico": "+1",
            "Rep. Dominicana": "+1", "Uruguay": "+598", "Venezuela": "+58"
        }
        opciones_paises = [f"{pais} ({pref})" for pais, pref in paises_data.items()]

        if not st.session_state.confirmado:
            # --- FASE 1: FORMULARIO DE REGISTRO ---
            with st.form("registro_equipo"):
                st.subheader("📩 Nueva Inscripción")
                nombre_e = st.text_input("Nombre del Equipo", value=st.session_state.datos_temp['nombre'] if st.session_state.datos_temp else "")
                seleccion = st.selectbox("País y Prefijo", opciones_paises)
                whatsapp = st.text_input("WhatsApp (Sin prefijo)", value=st.session_state.datos_temp['wa'] if st.session_state.datos_temp else "")
                nuevo_pin = st.text_input("Crea tu PIN (4 dígitos)", max_chars=4, type="password")
                
                if st.form_submit_button("Revisar Datos"):
                    cur = conn.cursor()
                    cur.execute("SELECT nombre FROM equipos WHERE pin = ?", (nuevo_pin,))
                    if nuevo_pin == ADMIN_PIN or cur.fetchone():
                        st.error("❌ Este PIN no está disponible. Elige otro.")
                    elif not nombre_e or not whatsapp or len(nuevo_pin) < 4:
                        st.error("⚠️ Completa todos los campos (PIN de 4 dígitos).")
                    else:
                        st.session_state.datos_temp = {
                            "nombre": nombre_e, 
                            "wa": whatsapp, 
                            "pin": nuevo_pin, 
                            "prefijo": seleccion.split('(')[-1].replace(')', ''),
                            "pais": seleccion.split(' (')[0]
                        }
                        st.session_state.confirmado = True
                        st.rerun()
        else:
            # --- FASE 2: PANTALLA DE CONFIRMACIÓN (RECUPERADA) ---
            d = st.session_state.datos_temp
            st.success("✅ Revisa tus datos antes de enviar")
            
            with st.container(border=True):
                st.write(f"**Equipo:** {d['nombre']}")
                st.write(f"**WhatsApp:** {d['prefijo']} {d['wa']}")
                st.write(f"**PIN Seleccionado:** `{d['pin']}`")
                st.write(f"**País:** {d['pais']}")

            c1, c2 = st.columns(2)
            if c1.button("🚀 Confirmar e Inscribir"):
                try:
                    conn.execute("INSERT INTO equipos (nombre, celular, prefijo, pin) VALUES (?,?,?,?)", 
                                 (d['nombre'], d['wa'], d['prefijo'], d['pin']))
                    conn.commit()
                    st.balloons()
                    st.success("¡Inscripción enviada con éxito!")
                    st.session_state.confirmado = False
                    st.session_state.datos_temp = None
                except:
                    st.error("Error al guardar. El nombre del equipo ya existe.")

            if c2.button("✏️ Editar Datos"):
                st.session_state.confirmado = False
                st.rerun()

# --- VISTAS PROTEGIDAS ---
elif st.session_state.rol == "admin":
    st.header("🛠️ Panel Admin")
    # ... Lógica de aprobación y reset ...

elif st.session_state.rol == "dt":
    st.header(f"🎮 Panel DT: {st.session_state.equipo_usuario}")
    # ... Lógica de subida de imagen ...

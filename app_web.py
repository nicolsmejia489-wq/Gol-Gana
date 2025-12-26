import streamlit as st
import sqlite3
import pandas as pd

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Gol-Gana", layout="centered", page_icon="⚽")

# --- BASE DE DATOS ---
DB_NAME = "gol_gana.db"
ADMIN_PIN = "2025"

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

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .stApp { max-width: 600px; margin: 0 auto; }
    .stButton>button { width: 100%; border-radius: 10px; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- GESTIÓN DE SESIÓN ---
if 'confirmado' not in st.session_state: st.session_state.confirmado = False
if 'rol' not in st.session_state: st.session_state.rol = "espectador"
if 'equipo_usuario' not in st.session_state: st.session_state.equipo_usuario = None
if 'datos_temp' not in st.session_state: st.session_state.datos_temp = None

# --- BOTÓN ATRÁS / CERRAR SESIÓN UNIVERSAL ---
# Solo aparece si no estás en la vista de espectador base
if st.session_state.rol != "espectador" or st.session_state.confirmado:
    if st.button("⬅️ Volver a la Tabla Principal"):
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
                        st.error("PIN incorrecto o equipo aún no aprobado.")

# --- VISTA: ESPECTADOR ---
if st.session_state.rol == "espectador":
    tab1, tab2 = st.tabs(["📊 Clasificación", "📝 Inscribirse"])

    with tab1:
        cur = conn.cursor()
        cur.execute("SELECT nombre, prefijo, celular FROM equipos WHERE estado = 'aprobado'")
        equipos_db = cur.fetchall()
        if not equipos_db:
            st.info("Aún no hay equipos oficiales. ¡Sé el primero en inscribirte!")
        else:
            st.subheader("Tabla de Posiciones")
            # Por ahora mostramos los inscritos, luego sumaremos la lógica de puntos
            for nombre_e, pref, cel in equipos_db:
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    c1.markdown(f"**{nombre_e}**")
                    wa_link = f"https://wa.me/{pref.replace('+','')}{cel}"
                    c2.markdown(f"[💬 WA]({wa_link})")

    with tab2:
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
            # FASE 1: FORMULARIO
            with st.form("registro_equipo"):
                st.subheader("📩 Nueva Inscripción")
                nombre_e = st.text_input("Nombre del Equipo", value=st.session_state.datos_temp['nombre'] if st.session_state.datos_temp else "")
                seleccion = st.selectbox("País y Prefijo", opciones_paises)
                whatsapp = st.text_input("WhatsApp (Sin prefijo)", value=st.session_state.datos_temp['wa'] if st.session_state.datos_temp else "")
                nuevo_pin = st.text_input("Crea tu PIN (4 dígitos)", max_chars=4, type="password")
                
                if st.form_submit_button("Revisar Datos"):
                    cur = conn.cursor()
                    cur.execute("SELECT nombre FROM equipos WHERE pin = ?", (nuevo_pin,))
                    pin_db = cur.fetchone()
                    
                    if nuevo_pin == ADMIN_PIN or pin_db:
                        st.error("❌ Este PIN no está disponible. Elige otro.")
                    elif not nombre_e or not whatsapp or len(nuevo_pin) < 4:
                        st.error("⚠️ Completa todos los campos (PIN de 4 dígitos).")
                    else:
                        st.session_state.datos_temp = {
                            "nombre": nombre_e, "wa": whatsapp, "pin": nuevo_pin,
                            "prefijo": seleccion.split('(')[-1].replace(')', ''),
                            "pais": seleccion.split(' (')[0]
                        }
                        st.session_state.confirmado = True
                        st.rerun()
        else:
            # FASE 2: CONFIRMACIÓN
            d = st.session_state.datos_temp
            st.success("✅ Revisa tus datos")
            with st.container(border=True):
                st.write(f"**Equipo:** {d['nombre']}")
                st.write(f"**WhatsApp:** {d['prefijo']} {d['wa']}")
                st.write(f"**PIN:** `{d['pin']}`")
                st.write(f"**País:** {d['pais']}")

            col_enviar, col_editar = st.columns(2)
            if col_enviar.button("🚀 Confirmar e Inscribir"):
                try:
                    conn.execute("INSERT INTO equipos (nombre, celular, prefijo, pin) VALUES (?,?,?,?)", 
                                 (d['nombre'], d['wa'], d['prefijo'], d['pin']))
                    conn.commit()
                    st.balloons()
                    st.success("¡Inscripción enviada!")
                    st.session_state.confirmado = False
                    st.session_state.datos_temp = None
                    st.rerun()
                except:
                    st.error("El nombre del equipo ya existe.")

            if col_editar.button("✏️ Editar Datos"):
                st.session_state.confirmado = False
                st.rerun()

# --- VISTA: ADMIN ---
elif st.session_state.rol == "admin":
    st.header("🛠️ Panel de Administración")
    st.subheader("📋 Solicitudes Pendientes")
    
    cur = conn.cursor()
    cur.execute("SELECT nombre, prefijo, celular FROM equipos WHERE estado = 'pendiente'")
    pendientes = cur.fetchall()
    
    if not pendientes:
        st.info("No hay solicitudes nuevas.")
    else:
        # Cabecera de tabla manual
        c_h1, c_h2, c_h3 = st.columns([2, 2, 1.2])
        c_h1.write("**Equipo**")
        c_h2.write("**WhatsApp**")
        c_h3.write("**Acción**")
        st.divider()

        for nombre_e, pref, cel in pendientes:
            c1, c2, c3 = st.columns([2, 2, 1.2])
            c1.write(nombre_e)
            c2.write(f"{pref} {cel}")
            if c3.button("✅ Aceptar", key=f"adm_{nombre_e}"):
                conn.execute("UPDATE equipos SET estado = 'aprobado' WHERE nombre = ?", (nombre_e,))
                conn.commit()
                st.rerun()
            st.divider()

    st.subheader("⚙️ Configuración")
    if st.button("🚨 RESET TOTAL TORNEO"):
        conn.execute("DELETE FROM equipos"); conn.execute("DELETE FROM historial"); conn.commit()
        st.rerun()

# --- VISTA: DT ---
elif st.session_state.rol == "dt":
    st.header(f"🎮 Panel DT: {st.session_state.equipo_usuario}")
    st.write("Sube tu marcador:")
    archivo = st.file_uploader("Captura de pantalla", type=['jpg', 'png'])
    if archivo:
        st.image(archivo)
        st.button("Procesar Imagen con IA")

conn.close()

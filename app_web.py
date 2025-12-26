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
    .status-badge { padding: 5px; border-radius: 5px; background-color: #f0f2f6; }
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

# --- GESTIÓN DE SESIÓN ---
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
            # Cálculo de tabla (simplificado por ahora)
            stats = {e[0]: {'PJ':0, 'Pts':0, 'WA': f"https://wa.me/{e[1].replace('+','')}{e[2]}"} for e in equipos_db}
            for e_nombre, info in stats.items():
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    c1.markdown(f"**{e_nombre}**")
                    c2.markdown(f"[💬 WA]({info['WA']})")

    with tab2:
        paises_data = {"Colombia": "+57", "México": "+52", "Venezuela": "+58", "Argentina": "+54", "Perú": "+51", "EEUU": "+1"}
        opciones_paises = [f"{pais} ({pref})" for pais, pref in paises_data.items()]

        if not st.session_state.confirmado:
            with st.form("registro"):
                nombre_e = st.text_input("Nombre del Equipo", value=st.session_state.datos_temp['nombre'] if st.session_state.datos_temp else "")
                seleccion = st.selectbox("País", opciones_paises)
                whatsapp = st.text_input("WhatsApp", value=st.session_state.datos_temp['wa'] if st.session_state.datos_temp else "")
                nuevo_pin = st.text_input("Crea tu PIN (4 dígitos)", max_chars=4, type="password")
                if st.form_submit_button("Revisar Datos"):
                    # Validaciones
                    if len(nuevo_pin) < 4: st.error("El PIN debe ser de 4 dígitos.")
                    else:
                        st.session_state.datos_temp = {"nombre": nombre_e, "wa": whatsapp, "pin": nuevo_pin, "prefijo": seleccion.split('(')[-1].replace(')', ''), "pais": seleccion.split(' (')[0]}
                        st.session_state.confirmado = True
                        st.rerun()
        else:
            d = st.session_state.datos_temp
            st.info("Confirma tus datos:")
            st.write(f"**Equipo:** {d['nombre']} | **WA:** {d['prefijo']} {d['wa']}")
            c1, c2 = st.columns(2)
            if c1.button("✅ Enviar"):
                conn.execute("INSERT INTO equipos (nombre, celular, prefijo, pin) VALUES (?,?,?,?)", (d['nombre'], d['wa'], d['prefijo'], d['pin']))
                conn.commit()
                st.session_state.confirmado = False
                st.success("¡Registrado!")
                st.rerun()
            if c2.button("✏️ Editar"):
                st.session_state.confirmado = False
                st.rerun()

# --- VISTA: ADMIN (¡YA NO ESTÁ EN BLANCO!) ---
elif st.session_state.rol == "admin":
    st.header("🛠️ Panel de Administración")
    
    # 1. Aprobación de Equipos
    st.subheader("📋 Solicitudes Pendientes")
    pendientes = pd.read_sql_query("SELECT nombre, celular, prefijo FROM equipos WHERE estado = 'pendiente'", conn)
    
    if pendientes.empty:
        st.write("No hay solicitudes nuevas.")
    else:
        st.table(pendientes)
        equipo_a_aprobar = st.selectbox("Selecciona equipo para aprobar", [""] + list(pendientes['nombre']))
        if st.button("Aprobar Equipo Seleccionado"):
            if equipo_a_aprobar:
                conn.execute("UPDATE equipos SET estado = 'aprobado' WHERE nombre = ?", (equipo_a_aprobar,))
                conn.commit()
                st.success(f"¡{equipo_a_aprobar} ahora es oficial!")
                st.rerun()

    # 2. Reseteo
    st.divider()
    if st.button("🚨 RESET TOTAL DEL TORNEO"):
        conn.execute("DELETE FROM equipos")
        conn.execute("DELETE FROM historial")
        conn.commit()
        st.warning("Torneo reiniciado por completo.")
        st.rerun()

# --- VISTA: DT ---
elif st.session_state.rol == "dt":
    st.header(f"🎮 Panel DT: {st.session_state.equipo_usuario}")
    st.write("Sube el marcador de tu último partido:")
    archivo = st.file_uploader("Captura de pantalla", type=['jpg', 'png'])
    if archivo:
        st.image(archivo, caption="Imagen cargada")
        st.button("Procesar con IA (Próximamente)")

conn.close()

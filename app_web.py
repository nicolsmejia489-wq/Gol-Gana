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

# --- GESTIÓN DE SESIÓN ---
if 'confirmado' not in st.session_state: st.session_state.confirmado = False
if 'rol' not in st.session_state: st.session_state.rol = "espectador"
if 'equipo_usuario' not in st.session_state: st.session_state.equipo_usuario = None

# --- BOTÓN ATRÁS / CERRAR SESIÓN ---
if st.button("⬅️ Volver al Inicio / Cerrar Sesión"):
    st.session_state.confirmado = False
    st.session_state.rol = "espectador"
    st.session_state.equipo_usuario = None
    st.rerun()

st.title("⚽ Gol-Gana")

# --- LOGIN SEPARADO (Solo se evalúa al presionar el botón) ---
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
        # (Lógica de tabla igual a la anterior)
        cur = conn.cursor()
        cur.execute("SELECT nombre, prefijo, celular FROM equipos WHERE estado = 'aprobado'")
        equipos_db = cur.fetchall()
        if not equipos_db:
            st.info("Aún no hay equipos aprobados.")
        else:
            stats = {e[0]: {'PJ':0, 'Pts':0, 'DG':0, 'GF':0, 'GC':0, 'WA': f"https://wa.me/{e[1].replace('+','')}{e[2]}"} for e in equipos_db}
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
            
            df_final = pd.DataFrame.from_dict(stats, orient='index').reset_index()
            df_final.columns = ['Equipo', 'PJ', 'Pts', 'DG', 'GF', 'GC', 'WA_Link']
            df_final['DG'] = df_final['GF'] - df_final['GC']
            df_final = df_final.sort_values(by=['Pts', 'DG'], ascending=False)
            df_final.insert(0, 'Pos', range(1, len(df_final) + 1))

            for _, row in df_final.iterrows():
                with st.container():
                    c1, c2, c3 = st.columns([1, 4, 2])
                    c1.write(f"#{row['Pos']}")
                    c2.markdown(f"[{row['Equipo']}]({row['WA_Link']})", unsafe_allow_html=True)
                    c3.write(f"**{row['Pts']}** Pts")
                    st.divider()

    with tab2:
        # --- FORMULARIO DE INSCRIPCIÓN (Ahora seguro) ---
        paises_data = {"Colombia": "+57", "México": "+52", "Venezuela": "+58", "Argentina": "+54", "España": "+34"} # Simplificado para el ejemplo
        opciones_paises = [f"{pais} ({pref})" for pais, pref in paises_data.items()]

        if not st.session_state.confirmado:
            with st.form("registro_equipo"):
                nombre_e = st.text_input("Nombre del Equipo")
                seleccion = st.selectbox("País", opciones_paises)
                whatsapp = st.text_input("WhatsApp")
                nuevo_pin = st.text_input("Crea tu PIN (4 dígitos)", max_chars=4, type="password")
                
                if st.form_submit_button("Revisar Datos"):
                    cur = conn.cursor()
                    cur.execute("SELECT nombre FROM equipos WHERE pin = ?", (nuevo_pin,))
                    if nuevo_pin == ADMIN_PIN or cur.fetchone():
                        st.error("Ese PIN no está disponible. Usa otro.")
                    elif not nombre_e or not whatsapp or len(nuevo_pin) < 4:
                        st.error("Datos incompletos.")
                    else:
                        st.session_state.datos_temp = {"nombre": nombre_e, "wa": whatsapp, "pin": nuevo_pin, "prefijo": seleccion.split('(')[-1].replace(')', '')}
                        st.session_state.confirmado = True
                        st.rerun()
        else:
            st.write(f"Confirmar: {st.session_state.datos_temp['nombre']}")
            if st.button("🚀 Enviar"):
                d = st.session_state.datos_temp
                conn.execute("INSERT INTO equipos (nombre, celular, prefijo, pin) VALUES (?,?,?,?)", (d['nombre'], d['wa'], d['prefijo'], d['pin']))
                conn.commit()
                st.session_state.confirmado = False
                st.success("¡Enviado!")
                st.rerun()

# --- VISTAS ADMIN Y DT (Solo se activan si el rol cambia por el botón de login) ---
elif st.session_state.rol == "admin":
    st.header("🛠️ Panel Admin")
    if st.button("🚨 RESET TOTAL"):
        conn.execute("DELETE FROM equipos"); conn.execute("DELETE FROM historial"); conn.commit()
        st.rerun()

elif st.session_state.rol == "dt":
    st.header(f"🎮 Panel DT: {st.session_state.equipo_usuario}")
    st.file_uploader("Sube tu marcador")

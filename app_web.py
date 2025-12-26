import streamlit as st
import sqlite3
import pandas as pd
from PIL import Image

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Gol-Gana", layout="centered", page_icon="⚽")

# --- ESTILOS CSS PARA MÓVIL ---
st.markdown("""
    <style>
    .stApp { max-width: 600px; margin: 0 auto; }
    .stButton>button { width: 100%; border-radius: 10px; }
    .block-container { padding-top: 1rem; }
    </style>
    """, unsafe_allow_html=True)

# --- CONSTANTES Y DB ---
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

# --- GESTIÓN DE ESTADO (STATE) ---
if 'confirmado' not in st.session_state: st.session_state.confirmado = False
if 'datos_temp' not in st.session_state: st.session_state.datos_temp = None

# --- BOTÓN "ATRÁS" UNIVERSAL ---
# Se coloca al principio para que siempre esté arriba
if st.button("⬅️ Volver al Inicio / Atrás"):
    st.session_state.confirmado = False
    st.session_state.datos_temp = None
    # Forzamos limpieza de PIN si quieres que cierre sesión también:
    # st.rerun() 
    st.rerun()

st.title("⚽ Gol-Gana")

# --- LOGIN Y ROLES ---
user_pin = st.text_input("🔑 PIN de Acceso", type="password", placeholder="Ingresa tu PIN")

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

# --- VISTA: ESPECTADOR ---
if rol == "espectador":
    tab1, tab2 = st.tabs(["📊 Clasificación", "📝 Inscribirse"])

    with tab1:
        cur = conn.cursor()
        cur.execute("SELECT nombre, prefijo, celular FROM equipos WHERE estado = 'aprobado'")
        equipos_db = cur.fetchall()
        
        if not equipos_db:
            st.info("Aún no hay equipos aprobados en el torneo.")
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
            with st.form("registro_equipo"):
                st.subheader("📩 Nueva Inscripción")
                nombre_e = st.text_input("Nombre del Equipo")
                seleccion = st.selectbox("País y Prefijo", opciones_paises)
                whatsapp = st.text_input("WhatsApp (Solo números)")
                nuevo_pin = st.text_input("Crea tu PIN (4 dígitos)", max_chars=4, type="password")
                
                if st.form_submit_button("Revisar Datos"):
                    cur = conn.cursor()
                    cur.execute("SELECT nombre FROM equipos WHERE pin = ?", (nuevo_pin,))
                    if not nombre_e or not whatsapp or len(nuevo_pin) < 4:
                        st.error("Completa todos los campos.")
                    elif nuevo_pin == ADMIN_PIN or cur.fetchone():
                        st.error("❌ PIN no disponible. Elige otro.")
                    else:
                        st.session_state.datos_temp = {
                            "nombre": nombre_e, "wa": whatsapp, "pin": nuevo_pin,
                            "prefijo": seleccion.split('(')[-1].replace(')', ''),
                            "pais": seleccion.split(' (')[0]
                        }
                        st.session_state.confirmado = True
                        st.rerun()
        else:
            d = st.session_state.datos_temp
            st.warning("Confirmar datos:")
            st.write(f"**Equipo:** {d['nombre']}")
            st.write(f"**WhatsApp:** {d['prefijo']} {d['wa']}")
            st.write(f"**PIN:** `{d['pin']}`")
            
            if st.button("🚀 Enviar Inscripción"):
                conn.execute("INSERT INTO equipos (nombre, celular, prefijo, pin) VALUES (?,?,?,?)",
                             (d['nombre'], d['wa'], d['prefijo'], d['pin']))
                conn.commit()
                st.success("¡Enviado! Reiniciando...")
                st.session_state.confirmado = False
                st.rerun()

# --- VISTA: ADMIN ---
elif rol == "admin":
    st.header("🛠️ Admin")
    pendientes = pd.read_sql_query("SELECT nombre, celular, prefijo FROM equipos WHERE estado = 'pendiente'", conn)
    if not pendientes.empty:
        st.dataframe(pendientes)
        equipo = st.selectbox("Aprobar:", [""] + list(pendientes['nombre']))
        if st.button("✅ Confirmar Aprobación"):
            conn.execute("UPDATE equipos SET estado = 'aprobado' WHERE nombre = ?", (equipo,))
            conn.commit()
            st.rerun()
    else:
        st.info("No hay equipos pendientes.")
    
    if st.button("🚨 RESET TOTAL TORNEO"):
        conn.execute("DELETE FROM historial"); conn.execute("DELETE FROM equipos")
        conn.commit(); st.rerun()

# --- VISTA: DT ---
elif rol == "dt":
    st.header(f"🎮 Panel DT: {equipo_usuario}")
    st.write("Sube tu marcador:")
    archivo = st.file_uploader("Captura del partido", type=['jpg', 'png'])
    if archivo:
        st.image(archivo)
        st.button("Analizar Imagen")

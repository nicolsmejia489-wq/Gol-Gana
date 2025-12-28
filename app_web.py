import streamlit as st
import sqlite3
import pandas as pd
from PIL import Image

# --- 1. CONFIGURACIÓN Y ESTILOS ---
DB_NAME = "gol_gana.db"
ADMIN_PIN = "2025" 



st.set_page_config(page_title="Gol-Gana", layout="centered")

# CSS para optimización móvil y estética
st.markdown("""
    <style>
    .stApp { max-width: 600px; margin: 0 auto; }
    .whatsapp-link { color: #25D366; text-decoration: none; font-weight: bold; }
    [data-testid="stMetricValue"] { font-size: 1.8rem; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BASE DE DATOS ---
def inicializar_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Tabla de equipos con prefijo para WA internacional
    cursor.execute('''CREATE TABLE IF NOT EXISTS equipos (
        nombre TEXT PRIMARY KEY, celular TEXT, prefijo TEXT, pin TEXT, estado TEXT DEFAULT 'pendiente'
    )''')
    # Tabla de historial de partidos
    cursor.execute('''CREATE TABLE IF NOT EXISTS historial (
        id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, local TEXT, goles_l INTEGER, goles_v INTEGER, visitante TEXT
    )''')
    conn.commit()
    return conn

conn = inicializar_db()

# --- 3. CABECERA Y ACCESO (SIEMPRE VISIBLE) ---
st.title("⚽ Gol-Gana")
user_pin = st.text_input("🔑 PIN de Acceso", type="password", help="DTs y Admin ingresen su PIN aquí")




# Lógica de Roles
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

# --- 4. VISTA: ESPECTADOR ---
if rol == "espectador":
    tab1, tab2 = st.tabs(["📊 Clasificación", "📝 Inscribirse"])

    with tab1:
        cur = conn.cursor()
        cur.execute("SELECT nombre, prefijo, celular FROM equipos WHERE estado = 'aprobado'")
        equipos_db = cur.fetchall()
        
        if not equipos_db:
            st.info("Aún no hay equipos aprobados en el torneo.")
        else:
            # Diccionario de estadísticas inicializado en 0
            stats = {e[0]: {'PJ':0, 'Pts':0, 'DG':0, 'GF':0, 'GC':0, 'WA': f"https://wa.me/{e[1].replace('+','')}{e[2]}"} for e in equipos_db}
            
            # Cargar partidos jugados
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

            # Crear DataFrame y ordenar
            df_final = pd.DataFrame.from_dict(stats, orient='index').reset_index()
            df_final.columns = ['Equipo', 'PJ', 'Pts', 'DG', 'GF', 'GC', 'WA_Link']
            df_final['DG'] = df_final['GF'] - df_final['GC']
            df_final = df_final.sort_values(by=['Pts', 'DG'], ascending=False)
            df_final.insert(0, 'Pos', range(1, len(df_final) + 1))

            # Renderizado de Tabla Mobile-Friendly
            for _, row in df_final.iterrows():
                with st.container():
                    c1, c2, c3 = st.columns([1, 4, 2])
                    c1.subheader(f"#{row['Pos']}")
                    c2.markdown(f"**[{row['Equipo']}]({row['WA_Link']})**", unsafe_allow_html=True)
                    c3.write(f"{row['Pts']} Pts")
                    st.caption(f"PJ: {row['PJ']} | GF: {row['GF']} | GC: {row['GC']} | DG: {row['DG']}")
                    st.divider()

    with tab2:
        st.subheader("📩 Registro de Equipo")
        paises_data = {
            "Argentina": "+54", "Bolivia": "+591", "Brasil": "+55", "Canadá": "+1",
            "Chile": "+56", "Colombia": "+57", "Costa Rica": "+506", "Ecuador": "+593",
            "España": "+34", "Estados Unidos": "+1", "México": "+52", "Panamá": "+507",
            "Perú": "+51", "Uruguay": "+598", "Venezuela": "+58"
        }
        opciones_paises = [f"{p} ({pref})" for p, pref in paises_data.items()]

        if 'confirmado' not in st.session_state:
            st.session_state.confirmado = False

        if not st.session_state.confirmado:
            with st.form("registro_equipo"):
                nom = st.text_input("Nombre del Equipo")
                pais_sel = st.selectbox("País", opciones_paises)
                tel = st.text_input("WhatsApp (Solo números)")
                pin_nuevo = st.text_input("PIN (4 dígitos)", max_chars=4, type="password")
                if st.form_submit_button("Revisar Registro"):
                    if nom and tel and len(pin_nuevo) == 4:
                        st.session_state.datos_temp = {
                            "n": nom, "wa": tel, "pin": pin_nuevo,
                            "pref": pais_sel.split('(')[-1].replace(')', '')
                        }
                        st.session_state.confirmado = True
                        st.rerun()
                    else: st.error("Llene todos los campos correctamente.")
        else:
            d = st.session_state.datos_temp
            st.info(f"**¿Confirmas los datos?**\n\nEquipo: {d['n']}\n\nWhatsApp: {d['pref']} {d['wa']}\n\nPIN: `{d['pin']}`")
            col1, col2 = st.columns(2)
            if col1.button("✅ Confirmar"):
                try:
                    conn.execute("INSERT INTO equipos (nombre, celular, prefijo, pin) VALUES (?,?,?,?)", (d['n'], d['wa'], d['pref'], d['pin']))
                    conn.commit()
                    st.success("¡Enviado! Espera aprobación.")
                    st.session_state.confirmado = False
                    st.rerun()
                except: st.error("El nombre o PIN ya existen.")
            if col2.button("✏️ Editar"):
                st.session_state.confirmado = False
                st.rerun()

# --- 5. VISTA: ADMIN ---
elif rol == "admin":
    st.header("👑 Panel de Administración")
    pendientes = pd.read_sql_query("SELECT nombre, celular, prefijo FROM equipos WHERE estado = 'pendiente'", conn)
    
    if not pendientes.empty:
        st.subheader("Solicitudes Pendientes")
        for _, r in pendientes.iterrows():
            with st.container():
                c1, c2, c3 = st.columns([2, 1, 1])
                c1.write(f"**{r['nombre']}**")
                link_wa = f"https://wa.me/{r['prefijo'].replace('+','')}{r['celular']}"
                c2.markdown(f"[💬 Chat]({link_wa})")
                if c3.button("✅ Ok", key=f"ok_{r['nombre']}"):
                    conn.execute("UPDATE equipos SET estado = 'aprobado' WHERE nombre = ?", (r['nombre'],))
                    conn.commit()
                    st.rerun()
                st.divider()
    else:
        st.info("No hay equipos por aprobar.")

    with st.expander("Zona de Peligro"):
        if st.button("🚨 REINICIAR TODO EL TORNEO"):
            conn.execute("DELETE FROM historial"); conn.execute("DELETE FROM equipos")
            conn.commit(); st.rerun()

# --- 6. VISTA: DT ---
elif rol == "dt":
    st.header(f"🎮 Panel DT: {equipo_usuario}")
    st.write("Sube la foto del resultado de tu partido.")
    archivo = st.file_uploader("Captura de pantalla", type=['jpg', 'png'])
    if archivo:
        st.image(archivo, caption="Imagen cargada")
        if st.button("Procesar Resultado"):
            st.info("Función de IA EasyOCR se activará en el siguiente paso.")




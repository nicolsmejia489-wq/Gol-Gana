import streamlit as st
import sqlite3
import pandas as pd

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Gol-Gana", layout="centered", page_icon="⚽")

def get_connection():
    return sqlite3.connect("gol_gana.db", check_same_thread=False)

# --- INICIALIZACIÓN DE DB ---
conn = get_connection()
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS equipos (
    nombre TEXT PRIMARY KEY, celular TEXT, prefijo TEXT, pin TEXT, estado TEXT DEFAULT 'pendiente'
)''')
conn.commit()

# --- ESTADOS DE SESIÓN ---
if 'rol' not in st.session_state: st.session_state.rol = "espectador"
if 'confirmado' not in st.session_state: st.session_state.confirmado = False
if 'datos_temp' not in st.session_state: st.session_state.datos_temp = None

# --- BOTÓN ATRÁS UNIVERSAL ---
if st.session_state.rol != "espectador" or st.session_state.confirmado:
    if st.button("⬅️ Volver / Cancelar"):
        st.session_state.confirmado = False
        st.session_state.rol = "espectador"
        st.session_state.datos_temp = None
        st.rerun()

st.title("⚽ Gol-Gana")

# --- BLOQUE DE LOGIN ---
if st.session_state.rol == "espectador" and not st.session_state.confirmado:
    with st.expander("🔑 Acceso DT / Admin"):
        with st.form("login"):
            pin_in = st.text_input("PIN", type="password")
            if st.form_submit_button("Entrar"):
                if pin_in == "2025":
                    st.session_state.rol = "admin"
                    st.rerun()
                else:
                    cur = conn.cursor()
                    cur.execute("SELECT nombre FROM equipos WHERE pin=? AND estado='aprobado'", (pin_in,))
                    res = cur.fetchone()
                    if res:
                        st.session_state.rol = "dt"; st.session_state.equipo_usuario = res[0]
                        st.rerun()
                    else:
                        st.error("PIN no válido o equipo pendiente.")

# --- VISTA: ESPECTADOR ---
if st.session_state.rol == "espectador":
    tab1, tab2 = st.tabs(["📊 Tabla de Posiciones", "📝 Inscripción"])

    with tab1:
        st.subheader("Clasificación Oficial")
        
        # 1. Obtener equipos aprobados
        cur = conn.cursor()
        cur.execute("SELECT nombre, prefijo, celular FROM equipos WHERE estado='aprobado'")
        equipos_db = cur.fetchall()
        
        if not equipos_db:
            st.info("Esperando aprobación de equipos para generar la tabla.")
        else:
            # 2. Inicializar estadísticas para cada equipo
            # POS, EQUIPO, PJ, PTS, GF, GC, DG
            stats = []
            for nom, pref, cel in equipos_db:
                # Aquí simulamos los datos. Cuando la IA funcione, leeremos la tabla 'historial'
                # Por ahora, todos empiezan en 0
                stats.append({
                    "Equipo": nom,
                    "PJ": 0, "PTS": 0, "GF": 0, "GC": 0, "DG": 0,
                    "WA": f"https://wa.me/{pref.replace('+','')}{cel}"
                })
            
            # 3. Convertir a DataFrame para manejar los datos fácil
            df = pd.DataFrame(stats)
            
            # Ordenar por Puntos, luego Diferencia de Goles
            df = df.sort_values(by=["PTS", "DG"], ascending=False)
            df.insert(0, "POS", range(1, len(df) + 1)) # Añadir columna de posición

            # 4. Mostrar la Tabla (Formato Profesional)
            # Usamos columnas para que se vea bien en móvil
            cols = st.columns([1, 3, 1, 1, 1, 1, 1])
            headers = ["POS", "EQUIPO", "PJ", "PTS", "GF", "GC", "DG"]
            for i, h in enumerate(headers):
                cols[i].write(f"**{h}**")
            
            st.divider()

            for _, fila in df.iterrows():
                c = st.columns([1, 3, 1, 1, 1, 1, 1])
                c[0].write(str(fila["POS"]))
                c[1].write(fila["Equipo"])
                c[2].write(str(fila["PJ"]))
                c[3].write(f"**{fila['PTS']}**")
                c[4].write(str(fila["GF"]))
                c[5].write(str(fila["GC"]))
                c[6].write(str(fila["DG"]))
                st.divider()

    with tab2:
        # Aquí se mantiene tu código de inscripción que ya funciona perfecto...
        st.write("(El formulario de inscripción sigue aquí)")

# --- VISTA ADMIN ---
elif st.session_state.rol == "admin":
    st.header("🛠️ Panel Admin")
    cur = conn.cursor()
    cur.execute("SELECT nombre, prefijo, celular FROM equipos WHERE estado='pendiente'")
    pendientes = cur.fetchall()
    
    if not pendientes:
        st.info("No hay solicitudes.")
    else:
        for nom, pref, cel in pendientes:
            with st.container(border=True):
                col1, col2 = st.columns([3,1])
                col1.write(f"**{nom}** ({pref} {cel})")
                if col2.button("✅ Aceptar", key=f"ok_{nom}"):
                    conn.execute("UPDATE equipos SET estado='aprobado' WHERE nombre=?", (nom,))
                    conn.commit()
                    st.rerun()

    st.divider()
    if st.button("🚨 RESET TORNEO"):
        conn.execute("DELETE FROM equipos"); conn.commit()
        st.rerun()

# --- VISTA DT ---
elif st.session_state.rol == "dt":
    st.header(f"🎮 Panel DT: {st.session_state.equipo_usuario}")
    st.write("Aquí podrás subir tus fotos de resultados próximamente.")


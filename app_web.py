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
        st.subheader("📩 Registro de Equipo")

        # 1. Diccionario Extendido de Países y Prefijos
        paises_data = {
            "Colombia": "+57", "Bolivia": "+591", "Brasil": "+55", "Canadá": "+1",
            "Chile": "+56", "Argentina": "+54", "Costa Rica": "+506", "Cuba": "+53",
            "Ecuador": "+593", "El Salvador": "+503", "España": "+34", "Estados Unidos": "+1",
            "Guatemala": "+502", "Honduras": "+504", "México": "+52", "Nicaragua": "+505",
            "Panamá": "+507", "Paraguay": "+595", "Perú": "+51", "Puerto Rico": "+1",
            "Rep. Dominicana": "+1", "Uruguay": "+598", "Venezuela": "+58"
        }
        opciones_paises = [f"{pais} ({pref})" for pais, pref in paises_data.items()]

        # Inicializar estado de confirmación si no existe
        if 'confirmado' not in st.session_state:
            st.session_state.confirmado = False

        if not st.session_state.confirmado:
            # --- FASE 1: LLENAR DATOS ---
            with st.form("registro_gol_gana"):
                nombre_e = st.text_input("Nombre del Equipo", placeholder="Ej: Once Caldas")
                seleccion = st.selectbox("País y Prefijo", opciones_paises)
                whatsapp = st.text_input("Número de WhatsApp", placeholder="Sin el prefijo")
                nuevo_pin = st.text_input("Crea tu PIN (4 números)", max_chars=4, type="password")
                
                enviado = st.form_submit_button("Inscribir equipo")
                
                if enviado:
                    if nombre_e and whatsapp and len(nuevo_pin) == 4:
                        # Guardamos temporalmente en la sesión
                        st.session_state.datos_temp = {
                            "nombre": nombre_e,
                            "pais_full": seleccion,
                            "prefijo": seleccion.split('(')[-1].replace(')', ''),
                            "wa": whatsapp,
                            "pin": nuevo_pin
                        }
                        st.session_state.confirmado = True
                        st.rerun()
                    else:
                        st.error("Por favor, llena todos los campos correctamente (El PIN debe ser de 4 dígitos).")
        else:
            # --- FASE 2: CONFIRMACIÓN ---
            d = st.session_state.datos_temp
            st.warning("El PIN elegido lo debes recordar para accceder como DT y subir los resultados de tu equipo⚠️ Revisa que tus datos sean correctos:")
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.write(f"**Equipo:** {d['nombre']}")
                st.write(f"**WhatsApp:** {d['prefijo']} {d['wa']}")
            with col_b:
                st.write(f"**PIN elegido:** `{d['pin']}`")
                st.write(f"**País:** {d['pais_full'].split(' (')[0]}")

            c1, c2 = st.columns(2)
            if c1.button("✅ Confirmar e Inscribir"):
                try:
                    conn.execute(
                        "INSERT INTO equipos (nombre, celular, prefijo, pin) VALUES (?, ?, ?, ?)",
                        (d['nombre'], d['wa'], d['prefijo'], d['pin'])
                    )
                    conn.commit()
                    st.success("¡Solicitud enviada con éxito! El admin te aprobará pronto.")
                    # Limpiamos el estado
                    st.session_state.confirmado = False
                    st.session_state.datos_temp = None
                except Exception as e:
                    st.error(f"Error: El nombre o PIN ya están en uso. {e}")

            if c2.button("✏️ Editar Datos"):
                st.session_state.confirmado = False
                st.rerun()

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



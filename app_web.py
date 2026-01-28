import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import cloudinary
import cloudinary.uploader
import time

# --- CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Copa Fácil", layout="centered", page_icon="🏆")

# URL DEL FONDO
fondo_url = "https://res.cloudinary.com/dlvczeqlp/image/upload/v1769030979/fondo_base_l7i0k6.png"
COLOR_LOBBY = "#FFD700" # Dorado Copa Fácil

# --- BLINDAJE VISUAL V2 (CON FONDO CLOUDINARY INTEGRADO) ---
st.markdown(f"""
    <style>
        /* 1. FONDO GENERAL CON IMAGEN Y CAPA OSCURA */
        .stApp {{
            background: linear-gradient(rgba(14, 17, 23, 0.85), rgba(14, 17, 23, 0.95)), 
                        url("{fondo_url}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
            color: white;
        }}
        
        /* 2. ARREGLO DE INPUTS (PIN, Nombres, Números) */
        div[data-baseweb="input"] {{
            background-color: rgba(38, 39, 48, 0.8) !important; /* Un poco de transparencia */
            border: 1px solid #444 !important;
        }}
        div[data-baseweb="input"] > div {{
            background-color: transparent !important;
            color: white !important;
        }}
        input {{ color: white !important; }}
        
        /* 3. ARREGLO DE BOTONES */
        button[kind="secondary"], div[data-testid="stLinkButton"] a {{
            background-color: rgba(38, 39, 48, 0.9) !important;
            color: white !important;
            border: 1px solid #555 !important;
        }}
        /* Efecto Hover Dorado (Marca Copa Fácil) */
        button[kind="secondary"]:hover, div[data-testid="stLinkButton"] a:hover {{
            border-color: {COLOR_LOBBY} !important;
            color: {COLOR_LOBBY} !important;
        }}
        /* Botones Primarios (Crear Torneo) */
        button[kind="primary"] {{
            background-color: {COLOR_LOBBY} !important;
            color: black !important;
            font-weight: bold !important;
            border: none !important;
        }}

        /* 4. EXPANDERS */
        div[data-testid="stExpander"] details summary {{
            background-color: rgba(38, 39, 48, 0.9) !important;
            color: white !important;
            border-radius: 5px;
        }}
        div[data-testid="stExpander"] details {{
            border-color: #444 !important;
            background-color: rgba(14, 17, 23, 0.9) !important; 
        }}
        div[data-testid="stExpander"] p {{ color: white !important; }}

        /* 5. TEXTOS GENERALES */
        p, label, h1, h2, h3, h4, span {{
            color: white !important;
        }}
        
        /* TARJETAS DE TORNEOS (CSS Específico para el Lobby) */
        .lobby-card {{
            background-color: rgba(255, 255, 255, 0.07);
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 15px;
            border: 1px solid rgba(255,255,255,0.1);
            transition: transform 0.2s;
        }}
        .lobby-card:hover {{
            transform: scale(1.01);
            border-color: {COLOR_LOBBY};
        }}
    </style>
""", unsafe_allow_html=True)


def render_lobby():
    # --- HEADER: BIENVENIDA ---
    # Usamos columnas para centrar y dar aire
    c_izq, c_cen, c_der = st.columns([1, 2, 1])
    with c_cen:
        st.markdown(f"<h1 style='text-align: center; color: {COLOR_LOBBY} !important; font-size: 50px;'>🏆 Copa Fácil</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; font-size: 18px; opacity: 0.8;'>La evolución de los torneos de barrio.</p>", unsafe_allow_html=True)
    
    st.markdown("---")

    # --- SECCIÓN 1: TORNEOS VIGENTES ---
    st.subheader("🔥 Torneos en Juego")
    
    try:
        # Traemos solo lo necesario para el lobby
        # NOTA: Asegúrate de tener 'conn' definido globalmente
        torneos = pd.read_sql_query(text("SELECT id, nombre, organizador, color_primario, fase, formato FROM torneos WHERE fase != 'Terminado' ORDER BY fecha_creacion DESC"), conn)
    except:
        torneos = pd.DataFrame()

    if not torneos.empty:
        for _, t in torneos.iterrows():
            # Usamos un container para agrupar visualmente
            with st.container():
                # Inyectamos HTML con el color específico de ESE torneo para el borde
                st.markdown(f"""
                <div class="lobby-card" style="border-left: 5px solid {t['color_primario']};">
                    <h3 style="margin:0; font-weight:800;">{t['nombre']}</h3>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:5px;">
                        <span style="opacity:0.7; font-size:14px;">👮 {t['organizador']}</span>
                        <span style="background-color:{t['color_primario']}40; padding:2px 8px; border-radius:4px; font-size:12px; border:1px solid {t['color_primario']};">
                            {t['fase'].upper()}
                        </span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Botón de acción (Ocupa todo el ancho debajo de la tarjeta)
                if st.button(f"⚽ Entrar a: {t['nombre']}", key=f"btn_lobby_{t['id']}", use_container_width=True):
                    st.query_params["id"] = str(t['id'])
                    st.rerun()
    else:
        st.info("No hay torneos activos en este momento. ¡Sé el primero en crear uno!")

    st.markdown("<br><br>", unsafe_allow_html=True)

    # --- SECCIÓN 2: ORGANIZAR MI TORNEO ---
    # Usamos el expander estilizado con tu CSS
    with st.expander("✨ ¡Organizar mi propio Torneo!", expanded=False):
        st.write("Configura tu competencia profesional en segundos.")
        
        with st.form("crear_torneo_lobby"):
            st.markdown("##### 1. Datos del Torneo")
            new_nombre = st.text_input("Nombre de la Competencia", placeholder="Ej: Relámpago Nocturno Jueves")
            
            c_f1, c_f2 = st.columns(2)
            new_formato = c_f1.selectbox("Formato", ["Grupos + Eliminatoria", "Todos contra Todos", "Eliminación Directa"])
            new_color = c_f2.color_picker("Color de tu Marca", "#00FF00")
            
            st.markdown("##### 2. Datos del Organizador (Admin)")
            c_adm1, c_adm2 = st.columns(2)
            new_org = c_adm1.text_input("Tu Nombre / Empresa")
            new_wa = c_adm2.text_input("WhatsApp de Contacto")
            
            st.markdown("##### 3. Seguridad")
            new_pin = st.text_input("Crea un PIN de Admin (4 dígitos)", type="password", max_chars=4, help="No lo olvides, es tu llave de acceso.")
            
            st.markdown("---")
            
            if st.form_submit_button("🚀 Lanzar Torneo", use_container_width=True, type="primary"):
                if new_nombre and new_pin and new_org:
                    try:
                        with conn.connect() as db:
                            # Insertar en BD y devolver ID
                            result = db.execute(text("""
                                INSERT INTO torneos (nombre, organizador, whatsapp_admin, pin_admin, color_primario, fase, formato)
                                VALUES (:n, :o, :w, :p, :c, 'inscripcion', :f) RETURNING id
                            """), {
                                "n": new_nombre, "o": new_org, "w": new_wa, 
                                "p": new_pin, "c": new_color, "f": new_formato
                            })
                            nuevo_id = result.fetchone()[0]
                            db.commit()
                        
                        st.success("¡Torneo creado con éxito!")
                        time.sleep(1)
                        # Redirección automática
                        st.query_params["id"] = str(nuevo_id)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error creando torneo: {e}")
                else:
                    st.warning("⚠️ Por favor completa el nombre, tu nombre y el PIN.")

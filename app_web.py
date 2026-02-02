import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import time
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url




# --- CONFIGURACIÓN DE CLOUDINARY CORREGIDA ---
cloudinary.config( 
    # Accedemos primero a la sección ["cloudinary"] y luego a la clave específica
    cloud_name = st.secrets["cloudinary"]["cloud_name"], 
    api_key = st.secrets["cloudinary"]["api_key"], 
    api_secret = st.secrets["cloudinary"]["api_secret"],
    secure = True
)

# ==============================================================================
# 1. CONFIGURACIÓN E IDENTIDAD
# ==============================================================================
st.set_page_config(page_title="Gol Gana", layout="centered", page_icon="⚽")

# --- ASSETS GRÁFICOS ---
URL_FONDO_BASE = "https://res.cloudinary.com/dlvczeqlp/image/upload/v1769030979/fondo_base_l7i0k6.png"
URL_PORTADA = "https://res.cloudinary.com/dlvczeqlp/image/upload/v1769050565/a906a330-8b8c-4b52-b131-8c75322bfc10_hwxmqb.png"
COLOR_MARCA = "#FFD700"  # Dorado Gol Gana

# --- CONEXIÓN A BASE DE DATOS (SEGURA CON SECRETS) ---
@st.cache_resource
def get_db_connection():
    try:
        if "connections" not in st.secrets or "postgresql" not in st.secrets["connections"]:
            return None # Modo diseño si no hay conexión
        db_url = st.secrets["connections"]["postgresql"]["url"]
        return create_engine(db_url, pool_pre_ping=True)
    except Exception as e:
        return None

conn = get_db_connection()

st.markdown(f"""
    <style>
        /* 0. IMPORTACIÓN Y BLINDAJE DE FUENTE OSWALD (Pesos más fuertes) */
        @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;600;700&display=swap');

        /* Forzado universal de la fuente con ajuste de espaciado (Impacto) */
        .stApp, h1, h2, h3, h4, h5, h6, p, div, button, input, label, span, textarea, a {{
            font-family: 'Oswald', sans-serif !important;
            letter-spacing: -0.02em !important; /* Letras más juntas como antes */
        }}

        /* 1. FONDO GENERAL */
        .stApp {{
            background: linear-gradient(rgba(14, 17, 23, 0.92), rgba(14, 17, 23, 0.96)), 
                        url("{URL_FONDO_BASE}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
            color: white;
            -webkit-font-smoothing: antialiased;
        }}

        /* Títulos con negrilla máxima (700) */
        h1, h2, h3, .tournament-title {{
            font-weight: 700 !important;
            text-transform: uppercase;
        }}

        /* 2. AJUSTE DE PESTAÑAS (TABS) - DISTRIBUCIÓN UNIFORME */
        button[data-baseweb="tab"] {{
            flex-grow: 1 !important;
            justify-content: center !important;
            min-width: 150px;
            background-color: rgba(255,255,255,0.05);
            border-radius: 8px 8px 0 0;
            color: #aaa;
            font-weight: 600 !important; /* Más gruesa la letra */
            letter-spacing: 0px !important; /* Sin separación extra */
            transition: all 0.3s ease;
            text-transform: uppercase;
        }}
        
        .stTabs [data-baseweb="tab-list"] {{ gap: 10px; }}
        
        .stTabs [aria-selected="true"] {{
            background-color: rgba(255, 215, 0, 0.1) !important;
            color: {COLOR_MARCA} !important;
            border-top: 3px solid {COLOR_MARCA} !important;
        }}

        /* 3. INPUTS Y BOTONES ESTÁNDAR */
        div[data-testid="stTextInput"] input, div[data-testid="stSelectbox"] > div > div {{
            background-color: #262730 !important;
            border: 1px solid #444 !important;
            color: white !important;
            height: 50px !important;
            font-size: 18px !important;
            border-radius: 8px !important;
        }}
        
        button[kind="secondary"], div[data-testid="stLinkButton"] a {{
            background-color: #262730 !important;
            border: 1px solid #555 !important;
            color: white !important;
            font-weight: 600 !important;
            border-radius: 8px !important;
        }}
        
        button[kind="primary"] {{
            background-color: {COLOR_MARCA} !important;
            color: black !important;
            font-weight: 700 !important; /* Negrilla máxima en botones */
            border: none !important;
            height: 50px !important;
            font-size: 18px !important;
            border-radius: 8px !important;
            text-transform: uppercase;
        }}

        /* 4. TARJETAS DE LOBBY */
        .lobby-card {{
            background-color: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            border: 1px solid rgba(255,255,255,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
            position: relative;
        }}
        
        .lobby-card:hover {{
            transform: scale(1.01);
            border-color: {COLOR_MARCA};
            background-color: rgba(255, 255, 255, 0.08);
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        }}

        /* 5. BURBUJA DEL BOT */
        .bot-bubble {{
            background-color: rgba(30, 30, 40, 0.9);
            border-left: 4px solid {COLOR_MARCA};
            border-radius: 8px;
            padding: 15px 20px;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 15px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.3);
            animation: fadeIn 1s ease-in;
        }}
        
        .bot-text {{ color: #ddd; font-size: 16px; font-weight: 400; line-height: 1.4; }}
        .bot-avatar {{ font-size: 28px; }}
        
        @keyframes fadeIn {{ 
            from {{ opacity:0; transform:translateY(10px); }} 
            to {{ opacity:1; transform:translateY(0); }} 
        }}

        /* 6. MANIFIESTO (FOOTER) */
        .manifesto-container {{
            margin-top: 50px; 
            padding: 30px;
            background: rgba(0,0,0,0.3);
            border-top: 1px solid #333; 
            border-radius: 15px;
        }}
        
        .intro-quote {{ font-size: 20px; font-style: italic; color: {COLOR_MARCA}; text-align: center; margin-bottom: 20px; font-weight: 400; }}
        .intro-text {{ font-size: 15px; text-align: justify; color: #aaa; line-height: 1.6; margin-bottom: 10px; font-weight: 400; }}
    </style>
""", unsafe_allow_html=True)

def mostrar_bot(mensaje):
    """Componente visual del asistente (Solo lectura)"""
    st.markdown(f"""
        <div class="bot-bubble">
            <div class="bot-avatar">🤖</div>
            <div class="bot-text">{mensaje}</div>
        </div>
    """, unsafe_allow_html=True)

# ==============================================================================
# 2. LIMPIEZA DE ESCUDO CLUDINARY
# ==============================================================================
def procesar_y_subir_escudo(archivo_imagen, nombre_equipo, id_torneo):
    """
    Sube la imagen a Cloudinary, aplica eliminación de fondo por IA
    y retorna la URL del PNG transparente.
    """
    try:
        # 'background_removal': 'cloudinary_ai' requiere el add-on activo en Cloudinary
        resultado = cloudinary.uploader.upload(
            archivo_imagen,
            folder=f"gol_gana/torneo_{id_torneo}/escudos",
            public_id=f"escudo_{nombre_equipo.replace(' ', '_').lower()}",
            background_removal="cloudinary_ai", 
            format="png" 
        )
        return resultado['secure_url']
    except Exception as e:
        # Fallback: Si la IA falla o el plan no la incluye, sube la imagen normal
        resultado_fallback = cloudinary.uploader.upload(
            archivo_imagen,
            folder=f"gol_gana/torneo_{id_torneo}/escudos"
        )
        return resultado_fallback['secure_url']

def validar_acceso(id_torneo, pin_ingresado):
    try:
        with conn.connect() as db:
            q_admin = text("SELECT nombre FROM torneos WHERE id = :id AND pin_admin = :pin")
            res_admin = db.execute(q_admin, {"id": id_torneo, "pin": pin_ingresado}).fetchone()
            if res_admin:
                return {"rol": "Admin", "id_equipo": None, "nombre_equipo": None}
            
            q_dt = text("SELECT id, nombre FROM equipos_globales WHERE id_torneo = :id AND pin_equipo = :pin")
            res_dt = db.execute(q_dt, {"id": id_torneo, "pin": pin_ingresado}).fetchone()
            if res_dt:
                return {"rol": "DT", "id_equipo": res_dt[0], "nombre_equipo": res_dt[1]}
        return None
    except: return None




    
# ==============================================================================
# 3. LÓGICA DEL LOBBY
# ==============================================================================

def render_lobby():
    # --- A. PORTADA ---
    st.image(URL_PORTADA, use_container_width=True)
    
    # --- B. SALUDO DEL BOT ---
    mostrar_bot("Hola, Soy <b>Gol Bot</b>. Guardaré las estadísticas de equipo y apoyaré al admin en la organización de cada torneo.")

    # --- C. SECCIÓN: NOVEDADES (TABS) ---
    st.markdown(f"<h3 style='text-align:center; color:{COLOR_MARCA}; margin-top:10px; letter-spacing:2px;'>NOVEDADES</h3>", unsafe_allow_html=True)
    
    tab_eq, tab_dt, tab_adm = st.tabs(["🛡️ Equipos", "🧠 DTs / Capitanes", "👮 Administradores"])
    
    with tab_eq:
        mostrar_bot("Olvídate de los debates subjetivos; aquí hablamos con datos, no opiniones. Te muestro contra quién compites más, a quién has dominado siempre o quién no has podido vencer nunca. Cada partido, título y victoria forma parte de la historia de Clubes Pro.")
    
    with tab_dt:
        mostrar_bot("Sé que gestionar un equipo es difícil. He simplificado todo para que cada competencia sea más fluida. Te facilitaré el Contacto con rivales, la revisión de marcadores y una actualización Instantánea.")
        
    with tab_adm:
        mostrar_bot("Yo te apoyaré con el trabajo sucio: lectura y proceso de marcadores, actualización de tablas, rondas y estadísticas. Tú tomas las decisiones importantes y defines los colores de tu competición para que tu comunidad resalte sobre las demás.")

    # --- LÍNEA DIVISORIA ---
    st.markdown("---")

    # ==============================================================================
    # D. TORNEOS EN CURSO (ESTE ES EL BLOQUE QUE MOVIMOS BAJO NOVEDADES)
    # ==============================================================================
    st.subheader("🔥 Torneos en Curso")

    try:
        if conn:
            query = text("""
                SELECT id, nombre, organizador, color_primario, fase, formato, fecha_creacion 
                FROM torneos 
                WHERE fase != 'Terminado' 
                ORDER BY fecha_creacion DESC
            """)
            df_torneos = pd.read_sql_query(query, conn)
        else:
            df_torneos = pd.DataFrame()
    except:
        st.error("Conectando al servidor...")
        df_torneos = pd.DataFrame()

    if not df_torneos.empty:
        for _, t in df_torneos.iterrows():
            with st.container():
                # 1. Diseño Visual de la Tarjeta (HTML)
                estado_txt = "INSCRIPCIONES ABIERTAS" if t['fase'] == 'inscripcion' else t['fase'].upper()
                
                st.markdown(f"""
                    <div style="border-left: 6px solid {t['color_primario']}; 
                                background: rgba(255,255,255,0.05); 
                                padding: 15px; 
                                border-radius: 0 12px 12px 0; 
                                margin-bottom: -10px;">
                        <h3 style="margin:0; color:white;">🏆 {t['nombre']}</h3>
                        <p style="margin:0; color:{t['color_primario']}; font-weight:bold; font-size:14px;">
                            ● {estado_txt}
                        </p>
                        <p style="margin:5px 0 0 0; opacity:0.7; font-size:14px;">
                            👮 {t['organizador']} | 🎮 {t['formato']}
                        </p>
                    </div>
                """, unsafe_allow_html=True)

                # 2. Botones de Acción (Nativos)
                c1, c2 = st.columns(2)
                with c1:
                    if st.button(f"Ver Torneo", key=f"v_{t['id']}", use_container_width=True):
                        st.query_params["id"] = str(t['id'])
                        st.rerun()
                with c2:
                    if st.button(f"Inscribir mi equipo", key=f"i_{t['id']}", use_container_width=True, type="primary"):
                        st.query_params["id"] = str(t['id'])
                        st.query_params["action"] = "inscribir"
                        st.rerun()
                st.markdown("<br>", unsafe_allow_html=True)
    else:
        st.info("No hay torneos activos actualmente.")

    

    # --- E. CREAR NUEVO TORNEO (Sin cambios) ---
    with st.expander("✨ ¿Eres Organizador? Crea tu Torneo", expanded=False):
        mostrar_bot("Configura tu torneo aquí. <br>Recuerda: <b>El PIN es sagrado</b>.")
        with st.form("form_crear_torneo"):
            st.markdown("##### 1. Identidad")
            new_nombre = st.text_input("Nombre de la Competencia", placeholder="Ej: Relámpago Jueves")
            c_f1, c_f2 = st.columns(2)
            new_formato = c_f1.selectbox("Formato", ["Grupos + Eliminatoria", "Todos contra Todos", "Eliminación Directa"])
            with c_f2: new_color = st.color_picker("Color de Marca", "#00FF00")
            
            st.markdown("##### 2. Admin")
            c_adm1, c_adm2 = st.columns(2)
            new_org = c_adm1.text_input("Tu Nombre / Cancha")
            new_wa = c_adm2.text_input("WhatsApp (Sin +)")
            
            st.markdown("##### 3. Seguridad")
            new_pin = st.text_input("Crea un PIN (4 dígitos)", type="password", max_chars=4)
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.form_submit_button("🚀 Lanzar Torneo", use_container_width=True, type="primary"):
                if new_nombre and new_pin and new_org and conn:
                    try:
                        with conn.connect() as db:
                            result = db.execute(text("""
                                INSERT INTO torneos (nombre, organizador, whatsapp_admin, pin_admin, color_primario, fase, formato)
                                VALUES (:n, :o, :w, :p, :c, 'inscripcion', :f) RETURNING id
                            """), {
                                "n": new_nombre, "o": new_org, "w": new_wa, 
                                "p": new_pin, "c": new_color, "f": new_formato
                            })
                            nuevo_id = result.fetchone()[0]
                            db.commit()
                        st.balloons()
                        time.sleep(1)
                        st.query_params["id"] = str(nuevo_id)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.warning("⚠️ Faltan datos.")

     # --- F. MANIFIESTO (FOOTER) ---
    st.markdown(f"""
        <div class="manifesto-container">
            <div class="intro-quote">
                “Mientras otros solo anotan goles, tú construyes una historia”
            </div>
            <div class="intro-text">
                El mundo ha cambiado. La tecnología y la Inteligencia Artificial han redefinido cada industria, y hoy, 
                ese poder llega finalmente a la comunidad de Clubes Pro. Ya no se trata solo de jugar un partido; 
                se trata del legado que dejas en cada cancha virtual.
            </div>
            <div class="intro-text">
                En la élite, los equipos más grandes no solo se miden por sus títulos, sino por los datos e indicadores 
                que respaldan cada trofeo. Por eso, en <b>Gol-Gana</b>, cada victoria, cada rivalidad y cada estadística 
                forman parte de una historia viva y objetiva. La evolución no se detiene, es momento de dar paso a un 
                ecosistema inteligente donde la historia de cada club puede ser eterna.
            </div>
            <div style="text-align:center; margin-top:15px; font-size:18px; font-weight:600; color:{COLOR_MARCA};">
                ¿Estás listo para transformar tu comunidad? Únete a los clubes que ya compiten en el futuro.
            </div>
        </div>
    """, unsafe_allow_html=True)






# ==============================================================================
# 4.1 LOGICA DE VALIDACIÓN DE ACCESO
# ==============================================================================
def validar_acceso(id_torneo, pin_ingresado):
    """
    4.1: Valida PIN alfanumérico (Admin o DT).
    """
    try:
        with conn.connect() as db:
            # 1. ¿Es Admin del torneo?
            q_admin = text("SELECT nombre FROM torneos WHERE id = :id AND pin_admin = :pin")
            res_admin = db.execute(q_admin, {"id": id_torneo, "pin": pin_ingresado}).fetchone()
            if res_admin:
                return {"rol": "Admin", "id_equipo": None, "nombre_equipo": None}
            
            # 2. ¿Es DT de un equipo en este torneo?
            q_dt = text("""
                SELECT id, nombre FROM equipos_globales 
                WHERE id_torneo = :id AND pin_equipo = :pin
            """)
            res_dt = db.execute(q_dt, {"id": id_torneo, "pin": pin_ingresado}).fetchone()
            if res_dt:
                return {"rol": "DT", "id_equipo": res_dt[0], "nombre_equipo": res_dt[1]}
        return None
    except: return None

        
def render_torneo(id_torneo):
    # ---------------------------------------------------------
    # 1. DATOS MAESTROS Y CONFIGURACIÓN VISUAL
    # ---------------------------------------------------------
    try:
        query = text("SELECT nombre, organizador, color_primario, url_portada, fase FROM torneos WHERE id = :id")
        with conn.connect() as db:
            t = db.execute(query, {"id": id_torneo}).fetchone()
        
        if not t:
            st.error("Torneo no encontrado."); return
        
        t_nombre, t_org, t_color, t_portada, t_fase = t
    
    except Exception as e:
        st.error(f"Error DB: {e}"); return

    # --- CSS Personalizado (Oswald Impact) ---
    st.markdown(f"""
        <style>
            button[kind="primary"] {{ background-color: {t_color} !important; color: black !important; font-weight: 700 !important; }}
            .stTabs [aria-selected="true"] p {{ color: {t_color} !important; font-weight: 700 !important; }}
            [data-baseweb="tab-highlight-renderer"] {{ background-color: {t_color} !important; }}
            .tournament-title {{ color: white; font-size: 32px; font-weight: 700; text-transform: uppercase; margin-top: 10px; margin-bottom: 0px; letter-spacing: -0.02em; }}
            .tournament-subtitle {{ color: {t_color}; font-size: 16px; opacity: 0.9; margin-bottom: 25px; font-weight: 400; }}
            div[data-testid="stExpander"] {{ border: 1px solid {t_color}; }}
        </style>
    """, unsafe_allow_html=True)

    # --- Cabecera y Navegación ---
    st.image(t_portada if t_portada else URL_PORTADA, use_container_width=True)
    
    # Botón Salir al Lobby (Limpia sesión)
    if st.button("⬅ LOBBY", use_container_width=False):
        for k in ["rol", "id_equipo", "nombre_equipo", "login_error", "datos_temp", "reg_estado", "msg_bot_ins"]:
            if k in st.session_state: del st.session_state[k]
        st.query_params.clear(); st.rerun()

    # Títulos
    st.markdown(f'<p class="tournament-title">{t_nombre}</p>', unsafe_allow_html=True)
    
    rol_actual = st.session_state.get("rol", "Espectador")
    label_modo = f"DT: {st.session_state.get('nombre_equipo')}" if rol_actual == "DT" else rol_actual
    st.markdown(f'<p class="tournament-subtitle">Organiza: {t_org} | Modo: {label_modo}</p>', unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 2. GESTOR DE PESTAÑAS POR ROL (Esqueleto)
    # ---------------------------------------------------------
    
    # --- ESCENARIO A: ADMINISTRADOR ---
    if rol_actual == "Admin":
        tabs = st.tabs(["🏆 Torneo", "⚙️ Control de Torneo"])

        # 1. TORNEO (Tabla de Posiciones)
        with tabs[0]:
            st.info("🚧 [PENDIENTE] Aquí irá la Tabla de Posiciones General (Admin View).")

        # 2. CONTROL (Panel de Gestión)
        with tabs[1]:
            st.info("🚧 [PENDIENTE] Aquí irá el Panel de Control del Admin (Partidos, Aprobaciones, Config).")
            st.markdown("---")
            if st.button("🔴 Cerrar Sesión Admin", use_container_width=True):
                st.session_state.clear(); st.rerun()

    # --- ESCENARIO B: DT (Director Técnico) ---
    elif rol_actual == "DT":
        tabs = st.tabs(["🏆 Torneo", "📅 Calendario", "👤 Mi Equipo"])

        # 1. TORNEO (Tabla de Posiciones)
        with tabs[0]:
            st.info("🚧 [PENDIENTE] Aquí irá la Tabla de Posiciones General.")

        # 2. CALENDARIO (Solo sus partidos)
        with tabs[1]:
            st.info(f"🚧 [PENDIENTE] Calendario de juegos para: {st.session_state.get('nombre_equipo')}")

        # 3. MI EQUIPO (Sub-pestañas)
        with tabs[2]:
            sub_tabs = st.tabs(["✏️ Editar Equipo", "📊 Estadísticas"])
            
            with sub_tabs[0]:
                st.info("🚧 [PENDIENTE] Gestión de escudo, nombre y Capitán encargado.")
            
            with sub_tabs[1]:
                st.info("🚧 [PENDIENTE] Gráficas de rendimiento.")
            
            st.markdown("---")
            if st.button("🔴 Cerrar Sesión Club", use_container_width=True):
                st.session_state.clear(); st.rerun()

   # --- ESCENARIO C: ESPECTADOR (Por defecto) ---
    else:
        # El orden solicitado: 1. Inscripciones, 2. Torneo, 3. Ingreso
        tabs = st.tabs(["📝 Inscripciones", "🏆 Torneo", "🔐 Ingreso"])

        # 1. INSCRIPCIONES (Registro nuevo o validar PIN)
        with tabs[0]:
            if t_fase == "inscripcion":
                
                # --- CEREBRO DE GOL BOT (Gestión de Mensajes) ---
                if "msg_bot_ins" not in st.session_state:
                    st.session_state.msg_bot_ins = "👋 Este registro es único. Si ya tienes equipo, ve a la pestaña INGRESO."

                mostrar_bot(st.session_state.msg_bot_ins)

                # --- MÁQUINA DE ESTADOS DEL REGISTRO ---
                if "reg_estado" not in st.session_state: st.session_state.reg_estado = "formulario"
                if "datos_temp" not in st.session_state: st.session_state.datos_temp = {}

                # ==========================================
                # ESTADO 3: ÉXITO (Final del camino)
                # ==========================================
                if st.session_state.reg_estado == "exito":
                    if st.button("📝 Inscribir otro equipo", use_container_width=True):
                        st.session_state.reg_estado = "formulario"
                        st.session_state.datos_temp = {}
                        st.session_state.msg_bot_ins = "¡Venga el siguiente! Lléname los datos del nuevo equipo."
                        st.rerun()

                # ==========================================
                # ESTADO 2: CONFIRMACIÓN (Resumen)
                # ==========================================
                elif st.session_state.reg_estado == "confirmar":
                    d = st.session_state.datos_temp
                    
                    with st.container(border=True):
                        col_t, col_i = st.columns([2, 1], vertical_alignment="center")
                        with col_t:
                            st.markdown(f"**Club:** {d['n']}")
                            st.markdown(f"**Contacto:** {d['pref']} {d['wa']}")
                            st.markdown(f"**PIN:** `{d['pin']}`")
                        with col_i:
                            if d['escudo_obj']: 
                                d['escudo_obj'].seek(0)
                                st.image(d['escudo_obj'], width=80)
                            else:
                                st.markdown("Sin Escudo")

                    c1, c2 = st.columns(2)
                    
                    if c1.button("✅ Enviar Solicitud", use_container_width=True):
                        with st.spinner("Subiendo escudo y guardando..."):
                            url_escudo = None
                            try:
                                if d['escudo_obj']:
                                    d['escudo_obj'].seek(0)
                                    url_escudo = procesar_y_subir_escudo(d['escudo_obj'], d['n'], id_torneo)
                                
                                with conn.connect() as db:
                                    db.execute(text("""
                                        INSERT INTO equipos_globales (id_torneo, nombre, celular_capitan, prefijo, pin_equipo, escudo, estado, celular_dt1, prefijo_dt1)
                                        VALUES (:id_t, :n, :c, :p, :pi, :e, 'pendiente', :c, :p)
                                    """), {
                                        "id_t": int(id_torneo), "n": d['n'], "c": d['wa'], 
                                        "p": d['pref'], "pi": d['pin'], "e": url_escudo
                                    })
                                    db.commit()
                                
                                st.session_state.reg_estado = "exito"
                                st.session_state.msg_bot_ins = f"¡Anotado! He guardado a <b>{d['n']}</b>. Dile al Admin que revise sus pendientes."
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error técnico: {e}")

                    if c2.button("✏️ Corregir", use_container_width=True):
                        st.session_state.reg_estado = "formulario"
                        st.session_state.msg_bot_ins = "Ok, volvamos al formulario."
                        st.rerun()

                # ==========================================
                # ESTADO 1: FORMULARIO (Inicio)
                # ==========================================
                else:
                    st.markdown("#### Registro de Nuevo Club")
                    with st.form("registro_club"):
                        d = st.session_state.get("datos_temp", {})
                        
                        nom_f = st.text_input("Nombre del Equipo", value=d.get('n', '')).strip()
                        
                        paises = {"Colombia": "+57", "México": "+52", "EEUU": "+1", "Argentina": "+54", "Ecuador": "+593", "Perú": "+51", "Chile": "+56", "Venezuela": "+58"}
                        opciones = [f"{p} ({pref})" for p, pref in paises.items()]
                        
                        idx_pref = 0
                        if d.get('pref'):
                            try: idx_pref = [d['pref'] in opt for opt in opciones].index(True)
                            except: pass
                        
                        pais_sel = st.selectbox("País", opciones, index=idx_pref)
                        wa_f = st.text_input("WhatsApp (Sin prefijo)", value=d.get('wa', '')).strip()
                        pin_f = st.text_input("Crea un PIN (4-6 alfanuméricos)", value=d.get('pin', ''), max_chars=6).strip()
                        escudo_f = st.file_uploader("🛡️ Escudo (Opcional)", type=['png', 'jpg', 'jpeg'])
                        
                        if st.form_submit_button("Siguiente ➡️", use_container_width=True):
                            if not nom_f or not wa_f or len(pin_f) < 4:
                                st.error("Faltan datos obligatorios.")
                            else:
                                # VALIDACIÓN INTELIGENTE (GOL BOT)
                                error_detectado = False
                                try:
                                    with conn.connect() as db:
                                        res_dup = db.execute(text("SELECT estado FROM equipos_globales WHERE id_torneo=:id AND LOWER(nombre) = LOWER(:n)"), 
                                                           {"id": int(id_torneo), "n": nom_f}).fetchone()
                                        res_pin = db.execute(text("SELECT 1 FROM equipos_globales WHERE pin_equipo = :p"), 
                                                           {"p": pin_f}).fetchone()

                                        if res_dup:
                                            st.session_state.msg_bot_ins = f"¡Alto ahí! El nombre <b>{nom_f}</b> ya existe en este torneo."
                                            error_detectado = True
                                        elif res_pin:
                                            st.session_state.msg_bot_ins = "Ese <b>PIN ya está ocupado</b>. Por seguridad, inventa uno diferente."
                                            error_detectado = True
                                except: pass

                                if error_detectado:
                                    st.rerun()
                                else:
                                    st.session_state.datos_temp = {
                                        "n": nom_f, "wa": wa_f, "pin": pin_f,
                                        "pref": pais_sel.split('(')[-1].replace(')', ''),
                                        "escudo_obj": escudo_f if escudo_f else d.get('escudo_obj')
                                    }
                                    st.session_state.reg_estado = "confirmar"
                                    st.session_state.msg_bot_ins = "🧐 Casi listo. Revisa los datos aquí abajo."
                                    st.rerun()
            else:
                st.warning("🚫 Las inscripciones están cerradas.")

        # 2. TORNEO (Tabla de Posiciones)
        with tabs[1]:
             # [PENDIENTE: AQUÍ PEGAREMOS LA TABLA DE POSICIONES]
             st.info("🚧 Tabla de Posiciones en construcción.")

        # 3. INGRESO (Login DT/Admin)
        with tabs[2]:
            st.subheader("🔐 Acceso Socios")
            with st.container(border=True):
                c_in, c_btn = st.columns([3, 1])
                pin_login = c_in.text_input("Ingresa tu PIN", type="password", placeholder="Admin o Club", label_visibility="collapsed")
                
                if c_btn.button("Entrar", type="primary", use_container_width=True):
                    acc = validar_acceso(id_torneo, pin_login)
                    if acc:
                        st.session_state.update(acc)
                        st.rerun()
                    else:
                        st.error("PIN incorrecto")

                        

            
# --- 4.3 EJECUCIÓN ---
params = st.query_params
if "id" in params: render_torneo(params["id"])
else: render_lobby()







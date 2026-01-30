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
    # 1. RECUPERAR DATOS DEL TORNEO (Configuración y Fase)
    try:
        with conn.connect() as db:
            t_data = db.execute(text("SELECT nombre, color_primario, fase FROM torneos WHERE id = :id"), {"id": id_torneo}).fetchone()
            if not t_data:
                st.error("Torneo no encontrado.")
                return
            
            t_nombre = t_data[0]
            t_color = t_data[1]
            t_fase = t_data[2]
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return

    # --- TÍTULO Y ESTILOS ---
    st.title(f"{t_nombre}")
    st.markdown(f"""
    <style>
        .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {{
            font-size: 1.1rem; font-weight: bold;
        }}
        div[data-testid="stExpander"] {{ border: 1px solid {t_color}; }}
        button[kind="primary"] {{ background-color: {t_color} !important; border: none; }}
    </style>
    """, unsafe_allow_html=True)

    # ==============================================================================
    # LÓGICA DE NAVEGACIÓN DINÁMICA (EL CEREBRO DE LA APP)
    # ==============================================================================
    rol_actual = st.session_state.get("rol")

    # ------------------------------------------------------------------------------
    # ESCENARIO 1: VISITANTE (Nadie logueado)
    # ------------------------------------------------------------------------------
    if not rol_actual:
        tabs = st.tabs(["🏆 Clasificación", "📝 Inscripción y Acceso"])

        # --- TAB 1: CLASIFICACIÓN (Pública) ---
        with tabs[0]:
            st.header("Tabla de Posiciones")
            st.info("🚧 Aquí se mostrará la tabla calculada automáticamente desde la base de datos.")
            # [AQUÍ PUEDES INSERTAR TU CÓDIGO DE TABLA DE POSICIONES CUANDO LO TENGAS]

        # --- TAB 2: ZONA DE ACCESO Y REGISTRO ---
        with tabs[1]:
            c_izq, c_der = st.columns([1, 1])
            
            # A. LOGIN (Siempre visible)
            with c_izq:
                with st.container(border=True):
                    st.subheader("🔐 Ingreso Socios")
                    pin_ingreso = st.text_input("PIN de Acceso", type="password", placeholder="PIN de equipo o Admin")
                    if st.button("Entrar al Club", type="primary", use_container_width=True):
                        acc = validar_acceso(id_torneo, pin_ingreso)
                        if acc:
                            st.session_state.update(acc)
                            st.rerun()
                        else:
                            st.error("PIN incorrecto.")

            # B. REGISTRO (Solo si fase == inscripcion)
            with c_der:
                if t_fase == "inscripcion":
                    st.subheader("📝 Nuevo Registro")
                    
                    # CEREBRO GOL BOT REGISTRO
                    if "msg_bot_ins" not in st.session_state:
                        st.session_state.msg_bot_ins = "👋 Si eres nuevo, registra tu club aquí. Si ya tienes PIN, usa el login de la izquierda."
                    mostrar_bot(st.session_state.msg_bot_ins)

                    # MÁQUINA DE ESTADOS REGISTRO
                    if "reg_estado" not in st.session_state: st.session_state.reg_estado = "formulario"
                    if "datos_temp" not in st.session_state: st.session_state.datos_temp = {}

                    if st.session_state.reg_estado == "exito":
                         if st.button("📝 Inscribir otro equipo"):
                            st.session_state.reg_estado = "formulario"
                            st.session_state.datos_temp = {}
                            st.session_state.msg_bot_ins = "¡Listo! Lléname los datos del nuevo equipo."
                            st.rerun()

                    elif st.session_state.reg_estado == "confirmar":
                        d = st.session_state.datos_temp
                        with st.container(border=True):
                            st.write(f"**Club:** {d['n']} | **PIN:** `{d['pin']}`")
                            if d['escudo_obj']: 
                                d['escudo_obj'].seek(0)
                                st.image(d['escudo_obj'], width=50)
                        
                        c1, c2 = st.columns(2)
                        if c1.button("✅ Enviar", use_container_width=True):
                            with st.spinner("Guardando..."):
                                try:
                                    url_escudo = None
                                    if d['escudo_obj']:
                                        d['escudo_obj'].seek(0)
                                        url_escudo = procesar_y_subir_escudo(d['escudo_obj'], d['n'], id_torneo)
                                    
                                    with conn.connect() as db:
                                        db.execute(text("INSERT INTO equipos_globales (id_torneo, nombre, celular_capitan, prefijo, pin_equipo, escudo, estado) VALUES (:id, :n, :c, :p, :pi, :e, 'pendiente')"),
                                                   {"id": id_torneo, "n": d['n'], "c": d['wa'], "p": d['pref'], "pi": d['pin'], "e": url_escudo})
                                        db.commit()
                                    st.session_state.reg_estado = "exito"
                                    st.session_state.msg_bot_ins = f"¡Anotado! He guardado a <b>{d['n']}</b>."
                                    st.rerun()
                                except Exception as e: st.error(f"Error: {e}")

                        if c2.button("✏️ Corregir", use_container_width=True):
                            st.session_state.reg_estado = "formulario"
                            st.rerun()

                    else: # Formulario
                        with st.form("reg_form"):
                            d = st.session_state.get("datos_temp", {})
                            nom = st.text_input("Nombre Club", value=d.get('n',''))
                            
                            paises = {"Colombia": "+57", "México": "+52", "EEUU": "+1", "Argentina": "+54"}
                            l_p = [f"{k} ({v})" for k,v in paises.items()]
                            pais = st.selectbox("País", l_p)
                            cel = st.text_input("WhatsApp (Sin prefijo)", value=d.get('wa',''))
                            pin = st.text_input("Crea tu PIN (4-6 letras/num)", value=d.get('pin',''), max_chars=6)
                            esc = st.file_uploader("Escudo", type=['png','jpg'])

                            if st.form_submit_button("Siguiente"):
                                if not nom or not cel or len(pin) < 4:
                                    st.error("Faltan datos.")
                                else:
                                    # Validaciones
                                    err = False
                                    with conn.connect() as db:
                                        if db.execute(text("SELECT 1 FROM equipos_globales WHERE pin_equipo=:p"), {"p":pin}).fetchone():
                                            st.session_state.msg_bot_ins = "PIN ocupado. Elige otro."
                                            err = True
                                    if not err:
                                        st.session_state.datos_temp = {"n": nom, "wa": cel, "pin": pin, "pref": pais.split('(')[-1][:-1], "escudo_obj": esc}
                                        st.session_state.reg_estado = "confirmar"
                                        st.session_state.msg_bot_ins = "Confirma los datos abajo."
                                    st.rerun()
                else:
                    st.info("🚫 Inscripciones cerradas.")

    # ------------------------------------------------------------------------------
    # ESCENARIO 2: DT / CAPITÁN (Logueado)
    # ------------------------------------------------------------------------------
    elif rol_actual == "DT":
        nom_eq = st.session_state.nombre_equipo
        id_eq = st.session_state.id_equipo

        tabs = st.tabs(["🏆 Clasificación", "⚽ Mis Partidos", "👤 Mi Club"])

        # --- TAB 1: CLASIFICACIÓN ---
        with tabs[0]:
            st.header("Tabla de Posiciones")
            st.info("🚧 Tabla de posiciones aquí.")

        # --- TAB 2: PARTIDOS ---
        with tabs[1]:
            st.subheader(f"Calendario: {nom_eq}")
            
            if t_fase == "inscripcion":
                mostrar_bot("⏳ **Paciencia, Profe.** El torneo aún no inicia. Cuando suene el silbato, aquí verás tu calendario.")
                st.image("https://cdn-icons-png.flaticon.com/512/2313/2313437.png", width=100)
            else:
                try:
                    q_mis = text("SELECT * FROM partidos WHERE id_torneo = :id AND (local = :n OR visitante = :n) ORDER BY jornada ASC")
                    with conn.connect() as db:
                        mis = pd.read_sql_query(q_mis, db, params={"id": id_torneo, "n": nom_eq})
                    
                    if mis.empty:
                        st.info("No hay partidos programados.")
                    else:
                        for _, p in mis.iterrows():
                            # Renderizado de Partido
                            es_local = (p['local'] == nom_eq)
                            rival = p['visitante'] if es_local else p['local']
                            
                            with st.container(border=True):
                                c_tit, c_chat = st.columns([3, 1])
                                with c_tit: st.markdown(f"**Vs {rival}** (J{p['jornada']})")
                                with c_chat:
                                    # Link WA Rival
                                    try:
                                        with conn.connect() as db:
                                            r = db.execute(text("SELECT prefijo, celular_capitan FROM equipos_globales WHERE id_torneo=:i AND nombre=:n"), {"i":id_torneo, "n":rival}).fetchone()
                                            if r: st.link_button("Chat", f"https://wa.me/{str(r[0]).replace('+','')}{str(r[1])}", use_container_width=True)
                                    except: pass

                                if p['estado'] == 'Finalizado':
                                    st.success(f"Result: {p['goles_l']} - {p['goles_v']}")
                                elif p['estado'] == 'Revision':
                                    st.warning("En Revisión")
                                else:
                                    # Carga de Foto
                                    up_foto = st.file_uploader(f"Foto J{p['jornada']}", key=f"u_{p['id']}")
                                    if up_foto and st.button("Enviar", key=f"b_{p['id']}"):
                                        # (Aquí iría tu lógica completa de IA y Cloudinary detallada en bloques anteriores)
                                        # Por brevedad en este bloque masivo, simulo el guardado básico
                                        st.toast("Función completa en bloque anterior") 
                except Exception as e: st.error(e)

        # --- TAB 3: MI CLUB (Oficina Virtual) ---
        with tabs[2]:
            c_head, c_btn = st.columns([3, 1])
            with c_head: st.header("Oficina Virtual")
            with c_btn:
                if st.button("🔴 Salir", use_container_width=True):
                    st.session_state.clear(); st.rerun()

            sub_tabs = st.tabs(["✏️ Editar Info", "📊 Estadísticas"])
            
            # SUB-TAB: EDICIÓN (UX MEJORADA)
            with sub_tabs[0]:
                try:
                    with conn.connect() as db:
                        me = db.execute(text("SELECT * FROM equipos_globales WHERE id=:i"), {"i":id_eq}).fetchone()
                    
                    if me:
                        p1, n1 = (me.prefijo_dt1 or "+57"), (me.celular_dt1 or "")
                        p2, n2 = (me.prefijo_dt2 or "+57"), (me.celular_dt2 or "")
                        tiene_dos = (len(n1)>5 and len(n2)>5)

                        # 1. SELECTOR CAPITÁN
                        if tiene_dos:
                            st.markdown(f"#### ©️ Capitán encargado para: {t_nombre}")
                            opt1, opt2 = f"{p1} {n1}", f"{p2} {n2}"
                            idx = 1 if me.celular_capitan == n2 else 0
                            sel = st.radio("Visible para rivales:", [opt1, opt2], index=idx, horizontal=True)
                            mostrar_bot("🤖 Los rivales verán el número seleccionado. Cámbialo cuando quieras.")
                            st.divider()
                        else: sel = None

                        # 2. FORMULARIO
                        with st.form("edit_club"):
                            st.subheader("Datos del Club")
                            c_a, c_b = st.columns(2)
                            nn = c_a.text_input("Nombre", me.nombre)
                            np = c_b.text_input("PIN", me.pin_equipo, type="password")
                            n_esc = st.file_uploader("Escudo")

                            st.subheader("Cuerpo Técnico")
                            paises = ["+57", "+52", "+1", "+54", "+593", "+51", "+56", "+58", "+502", "+506", "+507"]
                            
                            c_d1a, c_d1b = st.columns([1, 2])
                            try: i1 = paises.index(p1) 
                            except: i1=0
                            sp1 = c_d1a.selectbox("Prefijo DT", paises, index=i1)
                            sn1 = c_d1b.text_input("Celular DT", n1)

                            c_d2a, c_d2b = st.columns([1, 2])
                            try: i2 = paises.index(p2) 
                            except: i2=0
                            sp2 = c_d2a.selectbox("Prefijo Co-DT", paises, index=i2)
                            sn2 = c_d2b.text_input("Celular Co-DT", n2)

                            if st.form_submit_button("Guardar"):
                                url = me.escudo
                                if n_esc: url = procesar_y_subir_escudo(n_esc, nn, id_torneo)
                                
                                # Lógica Activo
                                if tiene_dos and sel and (n2 in sel): pub_c, pub_p = sn2, sp2
                                else: pub_c, pub_p = sn1, sp1

                                with conn.connect() as db:
                                    db.execute(text("""
                                        UPDATE equipos_globales SET nombre=:n, pin_equipo=:pi, escudo=:e,
                                        celular_dt1=:c1, prefijo_dt1=:p1, celular_dt2=:c2, prefijo_dt2=:p2,
                                        celular_capitan=:cp, prefijo=:pp WHERE id=:id
                                    """), {"n":nn, "pi":np, "e":url, "c1":sn1, "p1":sp1, "c2":sn2, "p2":sp2, "cp":pub_c, "pp":pub_p, "id":id_eq})
                                    
                                    if nn != me.nombre: # Sincronizar partidos
                                        db.execute(text("UPDATE partidos SET local=:n WHERE local=:o AND id_torneo=:i"), {"n":nn, "o":me.nombre, "i":id_torneo})
                                        db.execute(text("UPDATE partidos SET visitante=:n WHERE visitante=:o AND id_torneo=:i"), {"n":nn, "o":me.nombre, "i":id_torneo})
                                        st.session_state.nombre_equipo = nn
                                    db.commit()
                                st.success("✅ Guardado"); time.sleep(1); st.rerun()

                except Exception as e: st.error(e)

            with sub_tabs[1]:
                mostrar_bot("📊 Recopilando estadísticas...")


    # ------------------------------------------------------------------------------
    # ESCENARIO 3: ADMINISTRADOR (Logueado)
    # ------------------------------------------------------------------------------
    elif rol_actual == "Admin":
        tabs = st.tabs(["🏆 Clasificación", "⚙️ Panel Admin"])

        # --- TAB 1: CLASIFICACIÓN ---
        with tabs[0]:
            st.header("Tabla General")
            st.info("🚧 Tabla de posiciones aquí.")

        # --- TAB 2: PANEL ADMIN ---
        with tabs[1]:
            c_tit, c_out = st.columns([3, 1])
            with c_tit: st.markdown(f"#### Administración de {t_nombre}")
            with c_out: 
                if st.button("🔴 Salir", use_container_width=True):
                    st.session_state.clear(); st.rerun()

            # LÓGICA DE FASES ADMIN
            if t_fase == "inscripcion":
                tabs_ad = st.tabs(["⏳ Pendientes", "📋 Directorio", "⚙️ Config"])
            else:
                tabs_ad = st.tabs(["⚽ Resultados", "📋 Directorio", "⚙️ Config"])

            # A. PENDIENTES / RESULTADOS
            with tabs_ad[0]:
                if t_fase == "inscripcion":
                    # Lista de Espera
                    try:
                        with conn.connect() as db:
                            pend = pd.read_sql_query(text("SELECT * FROM equipos_globales WHERE id_torneo=:i AND estado='pendiente'"), db, params={"i":id_torneo})
                        if pend.empty: mostrar_bot("Todo limpio, Presi. No hay pendientes.")
                        else:
                            mostrar_bot(f"Tienes {len(pend)} solicitudes.")
                            for _, r in pend.iterrows():
                                with st.container(border=True):
                                    c1, c2, c3 = st.columns([0.5, 3, 1])
                                    with c1: 
                                        if r['escudo']: st.image(r['escudo'], width=40)
                                    with c2: st.markdown(f"**{r['nombre']}** | PIN: {r['pin_equipo']}")
                                    with c3:
                                        if st.button("Ok", key=f"ok_{r['id']}"):
                                            with conn.connect() as db:
                                                db.execute(text("UPDATE equipos_globales SET estado='aprobado' WHERE id=:i"), {"i":r['id']})
                                                db.commit()
                                            st.rerun()
                    except: pass
                else:
                    st.info("Gestor de Resultados (Fixture) va aquí.")

            # B. DIRECTORIO
            with tabs_ad[1]:
                # Directorio simple
                with conn.connect() as db:
                    eqs = pd.read_sql_query(text("SELECT nombre, celular_capitan, prefijo FROM equipos_globales WHERE id_torneo=:i AND estado='aprobado'"), db, params={"i":id_torneo})
                for _, r in eqs.iterrows():
                    st.markdown(f"**{r['nombre']}** - {r['prefijo']} {r['celular_capitan']}")
                    st.divider()

            # C. CONFIGURACIÓN
            with tabs_ad[2]:
                st.subheader("Fase del Torneo")
                if t_fase == "inscripcion":
                    if st.button("🔐 Cerrar Inscripciones e Iniciar", type="primary"):
                        st.session_state.conf_ini = True
                    
                    if st.session_state.get("conf_ini"):
                        mostrar_bot("¿Seguro? Pasaremos a competencia.")
                        if st.button("✅ Sí"):
                            with conn.connect() as db:
                                db.execute(text("UPDATE torneos SET fase='competencia' WHERE id=:i"), {"i":id_torneo}); db.commit()
                            del st.session_state.conf_ini; st.rerun()# --- TAB 3: PANEL DE GESTIÓN (LÓGICA UNIFICADA) ---
    with tabs[2]:
        
        # ---------------------------------------------------------
        # A. LOGIN (Si no hay sesión iniciada)
        # ---------------------------------------------------------
        if "rol" not in st.session_state:
            mostrar_bot("Zona restringida. Identifícate para gestionar.")
            
            c_login, c_submit = st.columns([3, 1])
            with c_login:
                pin_input = st.text_input("PIN de Acceso", type="password", 
                                        placeholder="Ingresa tu PIN...", 
                                        label_visibility="collapsed")
            with c_submit:
                if st.button("Entrar", type="primary", use_container_width=True):
                    acc = validar_acceso(id_torneo, pin_input)
                    if acc:
                        st.session_state.update(acc)
                        st.rerun()
                    else:
                        st.error("PIN no reconocido.")

        # ---------------------------------------------------------
        # B. VISTA DE DT (Capitán)
        # ---------------------------------------------------------
       # ---------------------------------------------------------
        # B. VISTA DE DT (Capitán / Cuerpo Técnico)
        # ---------------------------------------------------------
        elif st.session_state.rol == "DT":
            # Datos de la sesión
            id_eq = st.session_state.id_equipo
            nom_eq = st.session_state.nombre_equipo
            
            st.markdown(f"#### 🧢 Panel Técnico: {nom_eq}")
            
            # Pestañas del DT
            if t_fase == "inscripcion":
                # Si estamos en inscripción, no mostramos partidos aún
                tabs_dt = st.tabs(["📋 Mi Equipo", "📊 Estadísticas"])
                idx_partidos = -1 # No existe tab partidos
                idx_mi_equipo = 0
                idx_stats = 1
            else:
                tabs_dt = st.tabs(["⚽ Mis Partidos", "📊 Estadísticas", "📋 Mi Equipo"])
                idx_partidos = 0
                idx_stats = 1
                idx_mi_equipo = 2

            # ==========================================
            # TAB: MIS PARTIDOS (Solo fase Competencia)
            # ==========================================
            if idx_partidos != -1:
                with tabs_dt[idx_partidos]:
                    st.subheader("Calendario y Resultados")
                    
                    try:
                        # Buscamos partidos donde el equipo sea Local O Visitante en ESTE torneo
                        q_mis = text("""
                            SELECT * FROM partidos 
                            WHERE id_torneo = :id_t AND (local = :n OR visitante = :n) 
                            ORDER BY jornada ASC
                        """)
                        with conn.connect() as db:
                            mis = pd.read_sql_query(q_mis, db, params={"id_t": int(id_torneo), "n": nom_eq})
                        
                        if mis.empty:
                            mostrar_bot("Aún no tienes partidos programados. ¡A entrenar mientras tanto!")
                        
                        ultima_jornada = -1
                        for _, p in mis.iterrows():
                            # Separador de Jornada
                            if p['jornada'] != ultima_jornada:
                                st.markdown(f"##### 🗓️ Jornada {p['jornada']}")
                                st.divider()
                                ultima_jornada = p['jornada']

                            # Identificar Rival
                            es_local = (p['local'] == nom_eq)
                            rival = p['visitante'] if es_local else p['local']
                            
                            with st.container(border=True):
                                # 1. ENCABEZADO DEL PARTIDO
                                c_info, c_chat = st.columns([3, 1], vertical_alignment="center")
                                with c_info:
                                    st.caption("Tu Rival")
                                    st.markdown(f"### 🆚 {rival}")
                                with c_chat:
                                    # Lógica para buscar el WhatsApp del Rival
                                    link_wa = None
                                    try:
                                        with conn.connect() as db:
                                            # Buscamos en equipos_globales por nombre y torneo
                                            r = db.execute(text("SELECT prefijo, celular_capitan FROM equipos_globales WHERE id_torneo=:idt AND nombre=:n"), 
                                                         {"idt": id_torneo, "n": rival}).fetchone()
                                            if r and r[1]:
                                                # Limpieza del número
                                                num_clean = str(r[1]).replace(' ', '').replace('+', '')
                                                pref_clean = str(r[0]).replace('+', '')
                                                link_wa = f"https://wa.me/{pref_clean}{num_clean}"
                                    except: pass
                                    
                                    if link_wa: st.link_button("💬 Chat", link_wa, type="secondary", use_container_width=True)
                                    else: st.caption("📵 Sin contacto")

                                # 2. ESTADOS DEL PARTIDO
                                metodo = p['metodo_registro'] if pd.notna(p['metodo_registro']) else "Algoritmo"

                                # CASO A: FINALIZADO
                                if p['estado'] == 'Finalizado':
                                    g_l = int(p['goles_l'])
                                    g_v = int(p['goles_v'])
                                    st.success(f"✅ Finalizado: {p['local']} ({g_l}) - ({g_v}) {p['visitante']}")
                                    
                                    if st.button("❌ Reportar Error", key=f"rep_{p['id']}"):
                                        with conn.connect() as db:
                                            # Pasamos a revisión (Conflicto = 1)
                                            db.execute(text("UPDATE partidos SET estado='Revision', conflicto=1 WHERE id=:id"), {"id": p['id']})
                                            db.commit()
                                        mostrar_bot("Entendido, Profe. He avisado al Admin para que revise el VAR (la foto).")
                                        time.sleep(2); st.rerun()

                                # CASO B: EN REVISIÓN
                                elif p['estado'] == 'Revision':
                                    st.warning("⚠️ Resultado en revisión por el Admin.")
                                
                                # CASO C: PENDIENTE (Subir Foto)
                                else:
                                    st.info("📸 Carga la foto del marcador para actualizar la tabla.")
                                    tipo_carga = st.radio("Método:", ["Cámara", "Galería"], horizontal=True, label_visibility="collapsed", key=f"rad_{p['id']}")
                                    
                                    foto = None
                                    if tipo_carga == "Cámara": foto = st.camera_input("Foto", key=f"cam_{p['id']}")
                                    else: foto = st.file_uploader("Imagen", type=['jpg','png','jpeg'], key=f"up_{p['id']}")
                                    
                                    if foto:
                                        if st.button("Enviar Resultado", key=f"env_{p['id']}", type="primary"):
                                            with st.spinner("🤖 Gol Bot analizando marcador..."):
                                                # 1. Análisis IA (Tu función existente)
                                                res_ia, msg_ia = leer_marcador_ia(foto, p['local'], p['visitante'])
                                                
                                                # 2. Subir Evidencia
                                                foto.seek(0)
                                                url_evidencia = None
                                                try:
                                                    c_res = cloudinary.uploader.upload(foto, folder=f"gol_gana/torneo_{id_torneo}/evidencias")
                                                    url_evidencia = c_res['secure_url']
                                                except: pass

                                                col_bd = "url_foto_l" if es_local else "url_foto_v"
                                                
                                                # 3. Lógica de Guardado
                                                with conn.connect() as db:
                                                    if res_ia:
                                                        gl, gv = res_ia
                                                        # Verificar si ya había datos del otro equipo
                                                        g_ex_l = p['goles_l']
                                                        
                                                        # Si es el primero en subir o coincide => Finalizar
                                                        # (Simplificamos: Si la IA lee, guardamos como Finalizado directo por ahora)
                                                        db.execute(text(f"""
                                                            UPDATE partidos SET 
                                                                goles_l=:gl, goles_v=:gv, {col_bd}=:u, 
                                                                estado='Finalizado', metodo_registro='IA-Bot' 
                                                            WHERE id=:id
                                                        """), {"gl": gl, "gv": gv, "u": url_evidencia, "id": p['id']})
                                                        st.balloons()
                                                        mostrar_bot(f"¡Leído! {gl} - {gv}. Tabla actualizada.")
                                                    else:
                                                        # Si la IA falla, marcamos Revisión
                                                        db.execute(text(f"""
                                                            UPDATE partidos SET 
                                                                {col_bd}=:u, estado='Revision', conflicto=1 
                                                            WHERE id=:id
                                                        """), {"u": url_evidencia, "id": p['id']})
                                                        st.warning("No pude leer los números claros, pero guardé la foto para el Admin.")
                                                    db.commit()
                                                time.sleep(2); st.rerun()

                    except Exception as e:
                        st.error(f"Error cargando partidos: {e}")

            # ==========================================
            # TAB: ESTADÍSTICAS
            # ==========================================
            with tabs_dt[idx_stats]:
                st.subheader("📊 Historia del Club")
                mostrar_bot("Estoy recopilando los datos de la temporada. Pronto verás aquí tu rendimiento, goles a favor y racha de victorias.")
                st.image("https://cdn-icons-png.flaticon.com/512/3094/3094845.png", width=100)

           # ==========================================
            # TAB: MI EQUIPO (Diseño Modular y Limpio)
            # ==========================================
            with tabs_dt[idx_mi_equipo]:
                try:
                    with conn.connect() as db:
                        q_me = text("SELECT * FROM equipos_globales WHERE id = :id")
                        me = db.execute(q_me, {"id": id_eq}).fetchone()

                    if me:
                        # Recuperamos datos de DTs para validaciones previas
                        p1 = me.prefijo_dt1 if me.prefijo_dt1 else "+57"
                        n1 = me.celular_dt1 if me.celular_dt1 else ""
                        p2 = me.prefijo_dt2 if me.prefijo_dt2 else "+57"
                        n2 = me.celular_dt2 if me.celular_dt2 else ""
                        
                        tiene_dos = (len(n1) > 5 and len(n2) > 5)

                        with st.form("form_mi_equipo"):
                            
                            # ==========================================
                            # 1. ZONA DE CAPITÁN ENCARGADO (Top Priority)
                            # ==========================================
                            if tiene_dos:
                                st.markdown(f"#### ©️ Capitán encargado para: {t_nombre}")
                                
                                # Opciones directas: Prefijo + Número
                                opt_1 = f"{p1} {n1}"
                                opt_2 = f"{p2} {n2}"
                                
                                # Detectar activo
                                idx_activo = 0
                                if me.celular_capitan == n2: idx_activo = 1
                                
                                sel_capitan = st.radio("Selecciona el número visible para los rivales:", 
                                                     [opt_1, opt_2], 
                                                     index=idx_activo, 
                                                     horizontal=True,
                                                     label_visibility="collapsed")
                                
                                mostrar_bot("🤖 Los rivales verán el número seleccionado al pulsar 'Chat'. Cámbialo aquí cuando lo necesites.")
                                st.write("") # Espacio
                            else:
                                sel_capitan = "Unico" # Valor dummy

                            # ==========================================
                            # 2. ZONA DE EDICIÓN (Separada en Tarjetas)
                            # ==========================================
                            st.subheader("✏️ Editar información de club")

                            # --- TARJETA 1: IDENTIDAD ---
                            with st.container(border=True):
                                st.markdown("**🪪 Identidad del Club**")
                                c_id1, c_id2 = st.columns([2, 1])
                                with c_id1:
                                    new_nom = st.text_input("Nombre del Equipo", value=me.nombre)
                                with c_id2:
                                    new_pin = st.text_input("PIN", value=me.pin_equipo, type="password")
                                
                                c_esc1, c_esc2 = st.columns([1, 4], vertical_alignment="center")
                                with c_esc1:
                                    if me.escudo: st.image(me.escudo, width=50)
                                    else: st.write("🛡️")
                                with c_esc2:
                                    new_escudo = st.file_uploader("Actualizar Escudo", type=['png', 'jpg'], label_visibility="collapsed")

                            # Lista de Países (Incluyendo Centroamérica)
                            paises = {
                                "Colombia": "+57", "México": "+52", "EEUU": "+1", "Argentina": "+54", 
                                "Ecuador": "+593", "Perú": "+51", "Chile": "+56", "Venezuela": "+58", "Brasil": "+55",
                                "Guatemala": "+502", "Costa Rica": "+506", "Panamá": "+507", 
                                "Honduras": "+504", "El Salvador": "+503", "Nicaragua": "+505"
                            }
                            l_paises = [f"{k} ({v})" for k, v in paises.items()]

                            # --- TARJETA 2: DT PRINCIPAL ---
                            with st.container(border=True):
                                st.markdown("**👤 DT Principal** (Quien inscribió al club)")
                                c_dt1_p, c_dt1_n = st.columns([1.5, 2])
                                
                                try: idx_p1 = list(paises.values()).index(p1)
                                except: idx_p1 = 0
                                
                                sel_p1 = c_dt1_p.selectbox("País", l_paises, index=idx_p1, key="s_p1", label_visibility="collapsed")
                                val_p1 = sel_p1.split('(')[-1].replace(')', '')
                                val_n1 = c_dt1_n.text_input("Celular", value=n1, key="i_n1", label_visibility="collapsed", placeholder="Número Principal")

                            # --- TARJETA 3: CO-DT ---
                            with st.container(border=True):
                                st.markdown("**👥 Co-DT** (Segundo contacto)")
                                c_dt2_p, c_dt2_n = st.columns([1.5, 2])
                                
                                try: idx_p2 = list(paises.values()).index(p2)
                                except: idx_p2 = 0
                                
                                sel_p2 = c_dt2_p.selectbox("País", l_paises, index=idx_p2, key="s_p2", label_visibility="collapsed")
                                val_p2 = sel_p2.split('(')[-1].replace(')', '')
                                val_n2 = c_dt2_n.text_input("Celular", value=n2, key="i_n2", label_visibility="collapsed", placeholder="Número Opcional")

                            st.write("")
                            
                            # BOTÓN DE GUARDADO
                            if st.form_submit_button("💾 Guardar Cambios", use_container_width=True):
                                # 1. Procesar Escudo
                                url_final = me.escudo
                                if new_escudo:
                                    url_final = procesar_y_subir_escudo(new_escudo, new_nom, id_torneo)
                                
                                # 2. Lógica del "Capitán Activo"
                                # Si el usuario eligió el segundo número en el radio button...
                                # Y verificamos que el número 2 no esté vacío
                                if tiene_dos and sel_capitan and (val_n2 in sel_capitan) and len(val_n2) > 5:
                                    pub_cel = val_n2
                                    pub_pref = val_p2
                                else:
                                    # Default: DT 1
                                    pub_cel = val_n1
                                    pub_pref = val_p1

                                with conn.connect() as db:
                                    # Actualizamos Fijos + Público
                                    db.execute(text("""
                                        UPDATE equipos_globales 
                                        SET nombre=:n, pin_equipo=:p, escudo=:e, 
                                            celular_dt1=:c1, prefijo_dt1=:p1,
                                            celular_dt2=:c2, prefijo_dt2=:p2,
                                            celular_capitan=:cp, prefijo=:pp
                                        WHERE id=:id
                                    """), {
                                        "n": new_nom, "p": new_pin, "e": url_final,
                                        "c1": val_n1, "p1": val_p1,
                                        "c2": val_n2, "p2": val_p2,
                                        "cp": pub_cel, "pp": pub_pref,
                                        "id": id_eq
                                    })
                                    
                                    # Sincronizar nombre en Partidos
                                    if new_nom != me.nombre:
                                        db.execute(text("UPDATE partidos SET local=:n WHERE local=:old AND id_torneo=:idt"), {"n": new_nom, "old": me.nombre, "idt": id_torneo})
                                        db.execute(text("UPDATE partidos SET visitante=:n WHERE visitante=:old AND id_torneo=:idt"), {"n": new_nom, "old": me.nombre, "idt": id_torneo})
                                        st.session_state.nombre_equipo = new_nom
                                        
                                    db.commit()
                                
                                st.success(f"✅ Información actualizada. Contacto activo: {pub_pref} {pub_cel}")
                                time.sleep(1.5); st.rerun()

                except Exception as e:
                    st.error(f"Error cargando perfil: {e}")
                    
        # ---------------------------------------------------------
        # C. VISTA DE ADMIN (Orquestador)
        # ---------------------------------------------------------
        elif st.session_state.rol == "Admin":
            # 1. Título Ajustado (Más pequeño)
            st.markdown(f"#### ⚙️ Administración de {t_nombre}")
            
            # --- CSS Exclusivo Admin ---
            st.markdown(f"""<style>div[data-testid="stExpander"] {{ border: 1px solid {t_color}; border-radius: 5px; }}</style>""", unsafe_allow_html=True)

            # Lógica de Pestañas Dinámicas
            if t_fase == "inscripcion":
                tabs_admin = st.tabs(["⏳ Lista de Espera", "📋 Directorio", "⚙️ Configuración"])
            else:
                tabs_admin = st.tabs(["⚽ Gestión Partidos", "📋 Directorio", "⚙️ Configuración"])

            # ==========================================
            # TAB 1: DINÁMICA (LISTA DE ESPERA / PARTIDOS)
            # ==========================================
            with tabs_admin[0]:
                if t_fase == "inscripcion":
                    try:
                        with conn.connect() as db:
                            q_pend = text("SELECT * FROM equipos_globales WHERE id_torneo = :id AND estado = 'pendiente'")
                            df_pend = pd.read_sql_query(q_pend, db, params={"id": id_torneo})
                        
                        if df_pend.empty:
                            # 2. Gol Bot avisa que todo está limpio
                            mostrar_bot("Todo tranquilo por aquí, Presi. <b>No hay solicitudes pendientes</b> en la bandeja.")
                        else:
                            # 2. Gol Bot alerta de trabajo
                            mostrar_bot(f"¡Atención! Tienes <b>{len(df_pend)} equipos</b> esperando tu visto bueno en la puerta.")
                            
                            for _, r in df_pend.iterrows():
                                with st.container(border=True):
                                    c1, c2, c3 = st.columns([0.5, 3, 1], vertical_alignment="center")
                                    with c1:
                                        if r['escudo']: st.image(r['escudo'], width=50)
                                        else: st.write("🛡️")
                                    with c2:
                                        st.markdown(f"**{r['nombre']}**")
                                        cel_clean = str(r['celular_capitan']).replace(' ', '')
                                        st.markdown(f"📞 [{r['prefijo']} {r['celular_capitan']}](https://wa.me/{r['prefijo'].replace('+','')}{cel_clean}) | PIN: `{r['pin_equipo']}`")
                                    with c3:
                                        if st.button("Aprobar ✅", key=f"apr_{r['id']}", use_container_width=True):
                                            with conn.connect() as db:
                                                db.execute(text("UPDATE equipos_globales SET estado='aprobado' WHERE id=:id"), {"id": r['id']})
                                                db.commit()
                                            st.toast(f"{r['nombre']} Aprobado"); time.sleep(1); st.rerun()
                    except Exception as e:
                        st.error(f"Error cargando lista: {e}")

                else:
                    # Lógica Fase Competencia
                    mostrar_bot("El balón está rodando. Aquí podrás cargar los marcadores cuando configuremos el fixture.")

            # ==========================================
            # TAB 2: DIRECTORIO (Solo Lectura)
            # ==========================================
            with tabs_admin[1]:
                st.subheader("Equipos Aprobados")
                try:
                    with conn.connect() as db:
                        q_aprob = text("SELECT nombre, celular_capitan, prefijo, escudo FROM equipos_globales WHERE id_torneo = :id AND estado = 'aprobado' ORDER BY nombre ASC")
                        df_aprob = pd.read_sql_query(q_aprob, db, params={"id": id_torneo})
                    
                    if df_aprob.empty:
                        st.warning("Aún no has aprobado equipos.")
                    else:
                        st.markdown(f"**Total:** {len(df_aprob)} equipos listos.")
                        for _, row in df_aprob.iterrows():
                            with st.container():
                                c_img, c_info = st.columns([0.5, 4], vertical_alignment="center")
                                with c_img:
                                    if row['escudo']: st.image(row['escudo'], width=35)
                                    else: st.write("🛡️")
                                with c_info:
                                    # 1. Construcción de la URL limpia para la API de WhatsApp
                                    pref_url = str(row['prefijo']).replace('+', '')
                                    cel_url = str(row['celular_capitan']).replace(' ', '')
                                    link_wa = f"https://wa.me/{pref_url}{cel_url}"
                                    
                                    # 2. Renderizado: Nombre • [Número con Link]
                                    # Usamos sintaxis Markdown: [Texto Visible](URL)
                                    st.markdown(f"**{row['nombre']}** • [`{row['prefijo']} {row['celular_capitan']}`]({link_wa})")
                                st.divider()
                except Exception as e:
                    st.error(f"Error listando equipos: {e}")

            # ==========================================
            # TAB 3: CONFIGURACIÓN (Con Confirmación de Gol Bot)
            # ==========================================
            with tabs_admin[2]:
                st.subheader("Ajustes del Torneo")
                
                # Color
                st.markdown("##### 🎨 Identidad")
                c_col1, c_col2 = st.columns([1, 2])
                new_color = c_col1.color_picker("Color Principal", value=t_color)
                if c_col2.button("Aplicar Color"):
                    with conn.connect() as db:
                        db.execute(text("UPDATE torneos SET color_primario = :c WHERE id = :id"), {"c": new_color, "id": id_torneo})
                        db.commit(); st.rerun()
                
                st.divider()

                # 3. CONTROL DE FASES CON CONFIRMACIÓN
                st.markdown(f"##### 🚀 Fase Actual: `{t_fase.upper()}`")
                
                if t_fase == "inscripcion":
                    # Botón inicial
                    if st.button("🔐 Cerrar Inscripciones e Iniciar Competencia", type="primary", use_container_width=True):
                        st.session_state.confirmar_inicio = True
                    
                    # Bloque de Confirmación de Gol Bot
                    if st.session_state.get("confirmar_inicio"):
                        st.markdown("---")
                        mostrar_bot("¿Estás seguro, Presi? Al iniciar la competencia **se cerrará el formulario de registro** y pasaremos al modo de grupos/partidos.")
                        
                        col_si, col_no = st.columns(2)
                        if col_si.button("✅ Sí, ¡A rodar el balón!", use_container_width=True):
                            with conn.connect() as db:
                                db.execute(text("UPDATE torneos SET fase='competencia' WHERE id=:id"), {"id": id_torneo})
                                db.commit()
                            del st.session_state.confirmar_inicio
                            st.balloons()
                            time.sleep(1.5)
                            st.rerun()
                            
                        if col_no.button("❌ Cancelar", use_container_width=True):
                            del st.session_state.confirmar_inicio
                            st.rerun()
                
                else:
                    st.info("El torneo está en curso. Para reiniciar o cambiar ajustes avanzados, contacta soporte técnico.")

            st.markdown("---")
            if st.button("Cerrar Sesión Admin", type="secondary"):
                for key in ["rol", "id_equipo", "nombre_equipo"]: del st.session_state[key]
                st.rerun()
                        
# --- 4.3 EJECUCIÓN ---
params = st.query_params
if "id" in params: render_torneo(params["id"])
else: render_lobby()



import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import time
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url

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
    # --- 4.2.1 Datos Maestros ---
    try:
        query = text("SELECT nombre, organizador, color_primario, url_portada, fase FROM torneos WHERE id = :id")
        with conn.connect() as db:
            t = db.execute(query, {"id": id_torneo}).fetchone()
        if not t:
            st.error("Torneo no encontrado."); return
        t_nombre, t_org, t_color, t_portada, t_fase = t
    except Exception as e:
        st.error(f"Error DB: {e}"); return

    # --- 4.2.2 CSS Oswald Impact ---
    st.markdown(f"""
        <style>
            button[kind="primary"] {{ background-color: {t_color} !important; color: black !important; font-weight: 700 !important; }}
            .stTabs [aria-selected="true"] p {{ color: {t_color} !important; font-weight: 700 !important; }}
            [data-baseweb="tab-highlight-renderer"] {{ background-color: {t_color} !important; }}
            .tournament-title {{ color: white; font-size: 32px; font-weight: 700; text-transform: uppercase; margin-top: 10px; margin-bottom: 0px; letter-spacing: -0.02em; }}
            .tournament-subtitle {{ color: {t_color}; font-size: 16px; opacity: 0.9; margin-bottom: 25px; font-weight: 400; }}
        </style>
    """, unsafe_allow_html=True)

    # --- 4.2.3 Cabecera ---
    st.image(t_portada if t_portada else URL_PORTADA, use_container_width=True)
    if st.button("⬅ LOBBY", use_container_width=False):
        for k in ["rol", "id_equipo", "nombre_equipo", "login_error", "datos_temp", "reg_estado", "msg_bot_ins"]:
            if k in st.session_state: del st.session_state[k]
        st.query_params.clear(); st.rerun()

    st.markdown(f'<p class="tournament-title">{t_nombre}</p>', unsafe_allow_html=True)
    
    rol_actual = st.session_state.get("rol", "Espectador")
    label_modo = f"DT: {st.session_state.get('nombre_equipo')}" if rol_actual == "DT" else rol_actual
    st.markdown(f'<p class="tournament-subtitle">Organiza: {t_org} | Modo: {label_modo}</p>', unsafe_allow_html=True)

    # --- 4.2.4 Pestañas Dinámicas ---
    tabs_nombres = ["📊 POSICIONES", "⚽ RESULTADOS", "⚙️ PANEL"]
    if t_fase == "inscripcion": tabs_nombres[1] = "📝 INSCRIPCIONES"
    tabs = st.tabs(tabs_nombres)

    with tabs[0]:
        st.subheader("Clasificación General")

# --- TAB 2: INSCRIPCIONES (Vía Rápida + Formulario con IA) ---
    with tabs[1]:
        if t_fase == "inscripcion":
            # 1. Mensaje inicial del Bot
            if "msg_bot_ins" not in st.session_state:
                st.session_state.msg_bot_ins = "Este registro es necesario una sola vez, si ya estás registrado recuérdame el PIN y presiona BUSCAR."

            mostrar_bot(st.session_state.msg_bot_ins)

            # --- A. BÚSQUEDA RÁPIDA ---
            c_pin, c_btn = st.columns([3, 1])
            with c_pin:
                pin_bus = st.text_input("Verificar mi PIN", max_chars=6, key="bus_pin", label_visibility="collapsed", placeholder="Ingresa PIN (alfanumérico)...")
            with c_btn:
                if st.button("BUSCAR", use_container_width=True):
                    if pin_bus:
                        try:
                            with conn.connect() as db:
                                q_bus = text("SELECT nombre FROM equipos_globales WHERE id_torneo=:id AND pin_equipo=:p")
                                res = db.execute(q_bus, {"id": int(id_torneo), "p": pin_bus}).fetchone()
                                if res:
                                    st.session_state.msg_bot_ins = f"El club <b>{res[0]}</b> ya está en lista de espera."
                                else:
                                    st.session_state.msg_bot_ins = "No te conozco aún, <b>no tengo ese PIN registrado</b> en este torneo."
                            st.rerun()
                        except Exception as e:
                            st.session_state.msg_bot_ins = "No te conozco aún, no tengo ese PIN registrado."
                            st.rerun()

            st.markdown("---")

            # --- B. LÓGICA DE REGISTRO POR ESTADOS ---
            if "reg_estado" not in st.session_state:
                st.session_state.reg_estado = "formulario"
            if "datos_temp" not in st.session_state:
                st.session_state.datos_temp = {"n": "", "wa": "", "pin": "", "pref": "+57", "escudo_obj": None}

            # ESTADO: ÉXITO
            if st.session_state.reg_estado == "exito":
                st.success("⚽ ¡Inscripción enviada con éxito! Revisa el panel pronto.")
                if st.button("Hacer otro registro"):
                    st.session_state.reg_estado = "formulario"
                    st.session_state.datos_temp = {"n": "", "wa": "", "pin": "", "pref": "+57", "escudo_obj": None}
                    st.rerun()

            # ESTADO: CONFIRMACIÓN (Procesamiento IA y Guardado)
            elif st.session_state.reg_estado == "confirmar":
                d = st.session_state.datos_temp
                st.warning("⚠️ **Confirma los datos del Club antes de enviar:**")
                
                col_t, col_i = st.columns([2, 1])
                with col_t:
                    st.write(f"**Club:** {d['n']}")
                    st.write(f"**Contacto:** ({d['pref']}) {d['wa']}")
                    st.write(f"**PIN:** {d['pin']}")
                with col_i:
                    if d['escudo_obj']: st.image(d['escudo_obj'], width=100)
                
                c1, c2 = st.columns(2)
                if c1.button("✅ Confirmar y Guardar", use_container_width=True):
                    with st.spinner("Procesando escudo con IA y guardando..."):
                        url_escudo = None
                        if d['escudo_obj']:
                            url_escudo = procesar_y_subir_escudo(d['escudo_obj'], d['n'], id_torneo)
                        
                        try:
                            with conn.connect() as db:
                                query_insert = text("""
                                    INSERT INTO equipos_globales (id_torneo, nombre, celular_capitan, prefijo, pin_equipo, escudo, estado)
                                    VALUES (:id_t, :n, :c, :p, :pi, :e, 'pendiente')
                                """)
                                db.execute(query_insert, {
                                    "id_t": int(id_torneo), "n": d['n'], "c": d['wa'], 
                                    "p": d['pref'], "pi": d['pin'], "e": url_escudo
                                })
                                db.commit()
                            st.session_state.reg_estado = "exito"
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al guardar: {e}")

                if c2.button("✏️ Corregir datos", use_container_width=True):
                    st.session_state.reg_estado = "formulario"; st.rerun()

            # ESTADO: FORMULARIO (Primera vez)
            else:
                st.markdown("#### ¿Eres nuevo? Regístrate aquí")
                with st.form("registro_club"):
                    d = st.session_state.datos_temp
                    nom_f = st.text_input("Nombre del Equipo", value=d['n']).strip()
                    
                    paises = {"Colombia": "+57", "EEUU": "+1", "México": "+52", "Ecuador": "+593", "Panamá": "+507", "Perú": "+51", "Argentina": "+54"}
                    opciones = [f"{p} ({pref})" for p, pref in paises.items()]
                    # Intentar pre-seleccionar el país guardado
                    try:
                        idx_pref = [d['pref'] in opt for opt in opciones].index(True)
                    except:
                        idx_pref = 0

                    pais_sel = st.selectbox("País", opciones, index=idx_pref)
                    wa_f = st.text_input("WhatsApp (Sin prefijo)", value=d['wa']).strip()
                    pin_f = st.text_input("Crea un PIN (4-6 caracteres alfanuméricos)", value=d['pin'], max_chars=6).strip()
                    escudo_f = st.file_uploader("🛡️ Sube tu escudo", type=['png', 'jpg', 'jpeg'])
                    
                    if st.form_submit_button("Siguiente", use_container_width=True):
                        if not nom_f or not wa_f or len(pin_f) < 4:
                            st.error("Datos incompletos o PIN muy corto (mínimo 4).")
                        else:
                            st.session_state.datos_temp = {
                                "n": nom_f, "wa": wa_f, "pin": pin_f,
                                "pref": pais_sel.split('(')[-1].replace(')', ''),
                                "escudo_obj": escudo_f if escudo_f else d['escudo_obj']
                            }
                            st.session_state.reg_estado = "confirmar"
                            st.rerun()
        
        else:
            # Si fase != inscripcion, mostramos resultados
            st.subheader("Resultados de la Jornada")
            st.info("No hay partidos registrados aún.")

            

# --- TAB 3: PANEL DE GESTIÓN (LÓGICA UNIFICADA) ---
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
        elif st.session_state.rol == "DT":
            st.header(f"Hola, Profe de {st.session_state.nombre_equipo}")
            mostrar_bot("🚧 Estoy construyendo tu vestuario digital. Pronto podrás editar tu escudo y ver tus estadísticas aquí.")
            
            if st.button("Cerrar Sesión", type="secondary"):
                for key in ["rol", "id_equipo", "nombre_equipo"]: del st.session_state[key]
                st.rerun()

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
                                        cel_clean = str(r['celular']).replace(' ', '')
                                        st.markdown(f"📞 [{r['prefijo']} {r['celular']}](https://wa.me/{r['prefijo'].replace('+','')}{cel_clean}) | PIN: `{r['pin_equipo']}`")
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
                        df_aprob = pd.read_sql_query(text("SELECT nombre, celular, prefijo, escudo FROM equipos_globales WHERE id_torneo = :id AND estado = 'aprobado' ORDER BY nombre ASC"), db, params={"id": id_torneo})
                    
                    if df_aprob.empty:
                        st.warning("Aún no has aprobado equipos.")
                    else:
                        st.markdown(f"**Total:** {len(df_aprob)} equipos listos.")
                        for _, row in df_aprob.iterrows():
                            with st.container():
                                c_img, c_info = st.columns([0.5, 4])
                                with c_img:
                                    if row['escudo']: st.image(row['escudo'], width=35)
                                    else: st.write("🛡️")
                                with c_info:
                                    st.markdown(f"**{row['nombre']}** • {row['prefijo']} {row['celular']}")
                                st.divider()
                except Exception as e: st.error(f"Error: {e}")

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











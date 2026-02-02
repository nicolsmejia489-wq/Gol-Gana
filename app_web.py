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
            letter-spacing: -0.02em !important;
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

        /* ============================================================ */
        /* 2. AJUSTE DE PESTAÑAS (TABS) - VERSIÓN COMPACTA (MÓVIL)      */
        /* ============================================================ */
        
        button[data-baseweb="tab"] {{
            flex-grow: 1 !important;
            justify-content: center !important;
            /* min-width: 150px;  <-- ELIMINADO para evitar scroll en móviles */
            min-width: 50px !important; /* Mínimo pequeño para permitir encogerse */
            
            background-color: rgba(255,255,255,0.05);
            border-radius: 8px 8px 0 0;
            color: #aaa;
            font-weight: 600 !important;
            letter-spacing: 0px !important;
            transition: all 0.3s ease;
            text-transform: uppercase;
            
            /* --- AJUSTES DE REDUCCIÓN DE TAMAÑO (~20%) --- */
            padding-left: 8px !important;   /* Antes era mayor */
            padding-right: 8px !important;  /* Antes era mayor */
            gap: 5px !important;            /* Menos espacio entre icono y texto */
            height: 45px !important;        /* Altura controlada */
        }}

        /* Reducción específica del tamaño de letra dentro de la pestaña */
        .stTabs [data-baseweb="tab"] p {{
            font-size: 14px !important; /* Reducido para que quepa todo */
        }}
        
        .stTabs [data-baseweb="tab-list"] {{ gap: 5px; }} /* Menos hueco entre pestañas */
        
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
            font-weight: 700 !important;
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
            # 1. VERIFICAR ADMIN
            q_admin = text("SELECT nombre FROM torneos WHERE id = :id AND pin_admin = :pin")
            res_admin = db.execute(q_admin, {"id": id_torneo, "pin": pin_ingresado}).fetchone()
            if res_admin:
                return {"rol": "Admin", "id_equipo": None, "nombre_equipo": "Organizador"}
            
            # 2. VERIFICAR DT (Con Estado)
            q_dt = text("SELECT id, nombre, estado FROM equipos_globales WHERE id_torneo = :id AND pin_equipo = :pin")
            res_dt = db.execute(q_dt, {"id": id_torneo, "pin": pin_ingresado}).fetchone()
            
            if res_dt:
                # El PIN existe, ahora miramos el estado
                if res_dt.estado == 'aprobado':
                    return {"rol": "DT", "id_equipo": res_dt.id, "nombre_equipo": res_dt.nombre}
                elif res_dt.estado == 'pendiente':
                    return "PENDIENTE" # Señal especial para la UI
                else:
                    return None # Baja u otro estado (No entra)

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
    try:
        with conn.connect() as db:
            # 1. VERIFICAR ADMIN (Prioridad absoluta)
            q_admin = text("SELECT nombre FROM torneos WHERE id = :id AND pin_admin = :pin")
            res_admin = db.execute(q_admin, {"id": id_torneo, "pin": pin_ingresado}).fetchone()
            if res_admin:
                return {"rol": "Admin", "id_equipo": None, "nombre_equipo": "Organizador"}
            
            # 2. VERIFICAR DT APROBADO (Solo entran los 'aprobado')
            # Nota: Agregamos explícitamente AND estado = 'aprobado' en el SQL
            q_ok = text("""
                SELECT id, nombre 
                FROM equipos_globales 
                WHERE id_torneo = :id AND pin_equipo = :pin AND estado = 'aprobado'
            """)
            res_ok = db.execute(q_ok, {"id": id_torneo, "pin": pin_ingresado}).fetchone()
            
            if res_ok:
                return {"rol": "DT", "id_equipo": res_ok.id, "nombre_equipo": res_ok.nombre}
            
            # 3. VERIFICAR SI ESTÁ PENDIENTE (Para dar el aviso correcto)
            q_pend = text("""
                SELECT 1 
                FROM equipos_globales 
                WHERE id_torneo = :id AND pin_equipo = :pin AND estado = 'pendiente'
            """)
            # Si existe un pendiente, devolvemos la señal de alerta
            if db.execute(q_pend, {"id": id_torneo, "pin": pin_ingresado}).fetchone():
                return "PENDIENTE"

        # Si llegamos aquí, es porque no es Admin, ni DT aprobado, ni pendiente.
        # (Puede ser estado NULL, 'baja' o PIN incorrecto)
        return None

    except Exception as e:
        print(f"Error login: {e}")
        return None

        


######DESARROLLO DE TORNEO
def contenido_pestana_torneo(id_torneo, t_color):
    """
    Función auxiliar para renderizar la tabla de posiciones o cruces.
    Se puede llamar desde cualquier rol (Admin, DT, Espectador).
    """
    # 1. Validar el formato del torneo
    try:
        with conn.connect() as db:
            res_fmt = db.execute(text("SELECT formato FROM torneos WHERE id=:id"), {"id": id_torneo}).fetchone()
            t_formato = res_fmt[0] if res_fmt else "Liga"
    except:
        t_formato = "Liga" # Fallback

    # ------------------------------------------
    # CASO A: FORMATOS CON TABLA (Liga / Grupos)
    # ------------------------------------------
    if t_formato in ["Liga", "Grupos y Cruces"]:
        try:
            color_maestro = t_color 

            # 1. Obtener datos FILTRADOS POR TORNEO
            with conn.connect() as db:
                df_eq = pd.read_sql_query(
                    text("SELECT nombre, escudo FROM equipos_globales WHERE id_torneo = :id AND estado = 'aprobado'"), 
                    db, 
                    params={"id": id_torneo}
                )
            
            if df_eq.empty:
                mostrar_bot("Aún no hay equipos oficiales en la tabla. El balón está detenido.")
            else:
                mapa_escudos = dict(zip(df_eq['nombre'], df_eq['escudo']))
                stats = {e: {'PJ':0, 'PTS':0, 'GF':0, 'GC':0} for e in df_eq['nombre']}
                
                with conn.connect() as db:
                    df_p = pd.read_sql_query(
                        text("SELECT * FROM partidos WHERE id_torneo = :id AND estado = 'Finalizado'"), 
                        db, 
                        params={"id": id_torneo}
                    )
                
                # Cálculo de Estadísticas
                for _, f in df_p.iterrows():
                    l, v = f['local'], f['visitante']
                    if l in stats and v in stats:
                        gl, gv = int(f['goles_l']), int(f['goles_v'])
                        stats[l]['PJ'] += 1; stats[v]['PJ'] += 1
                        stats[l]['GF'] += gl; stats[l]['GC'] += gv
                        stats[v]['GF'] += gv; stats[v]['GC'] += gl
                        if gl > gv: stats[l]['PTS'] += 3
                        elif gv > gl: stats[v]['PTS'] += 3
                        else: stats[l]['PTS'] += 1; stats[v]['PTS'] += 1
                
                df_f = pd.DataFrame.from_dict(stats, orient='index').reset_index()
                df_f.columns = ['EQ', 'PJ', 'PTS', 'GF', 'GC']
                df_f['DG'] = df_f['GF'] - df_f['GC']
                df_f = df_f.sort_values(by=['PTS', 'DG', 'GF'], ascending=False).reset_index(drop=True)
                df_f.insert(0, 'POS', range(1, len(df_f) + 1))

                # =========================================================================
                # 2. DISEÑO Y ESTILOS (AQUÍ ESTÁ TODO LO EDITABLE)
                # =========================================================================
                plantilla_tabla = f"""
                <style>
                    /* --- CONTENEDOR PRINCIPAL DE LA TABLA --- */
                    .tabla-pro {{ 
                        width: 100%;                        /* Ancho de la tabla */
                        border-collapse: collapse;          /* Bordes colapsados (estilo limpio) */
                        table-layout: fixed;                /* Fija el ancho de columnas */
                        background-color: rgba(0,0,0,0.5);  /* Color de Fondo (Negro semitransparente) */
                        font-family: 'Oswald', sans-serif;  /* TIPO DE FUENTE PRINCIPAL */
                        border: 1px solid {color_maestro} !important; /* Borde externo del color del torneo */
                    }}

                    /* --- ENCABEZADOS (POS, EQUIPO, PTS...) --- */
                    .tabla-pro th {{ 
                        background-color: #111;             /* Fondo del encabezado (Casi negro) */
                        color: #ffffff !important;          /* Color del texto del encabezado */
                        font-size: 11px;                    /* TAMAÑO FUENTE ENCABEZADO */
                        height: 35px !important;            /* ALTURA de la fila de encabezado */
                        text-align: center;                 /* Alineación texto (centrado) */
                        border-bottom: 2px solid {color_maestro} !important; /* Línea separadora de color */
                        padding: 1px 1px;                   /* Relleno interno */
                    }}

                    /* --- CELDAS DEL CUERPO (DATOS) --- */
                    .tabla-pro td {{ 
                        color: white;                       /* Color texto general */
                        font-size: 13px;                    /* TAMAÑO FUENTE DATOS */
                        height: 30px !important;            /* ALTURA FILA EQUIPOS (Aumentado para escudo grande) */
                        border-bottom: 1px solid #222;      /* Línea gris suave entre filas */
                        vertical-align: middle !important;  /* Centrado vertical */
                        padding: 2px 1px !important;        /* Espacio lateral mínimo */
                        text-align: center;                 /* Por defecto todo centrado */
                    }}

                    /* --- CONTENEDOR DEL ESCUDO (Caja invisible) --- */
                    .escudo-wrapper {{
                        display: inline-block;
                        width: 35px;                        /* ANCHO RESERVADO PARA ESCUDO */
                        text-align: center;
                        margin-right: 2px;                 /* ESPACIO ENTRE ESCUDO Y NOMBRE DEL EQUIPO */
                        vertical-align: middle;
                    }}
                    
                    /* --- IMAGEN DEL ESCUDO --- */
                    .img-escudo {{
                        height: 35px;                       /* ALTO DEL ESCUDO (Aumentado) */
                        width: 35px;                        /* ANCHO DEL ESCUDO (Aumentado) */
                        object-fit: contain;                /* Para que no se deforme */
                    }}
                </style>
                """

                # Construcción del HTML
                tabla_html = '<table class="tabla-pro"><thead><tr>'
                
                # --- ANCHOS DE COLUMNAS (La suma debe dar 100%) ---
                tabla_html += '<th style="width:10%">POS</th>'
                tabla_html += '<th style="width:45%; text-align:left; padding-left:10px">EQUIPO</th>' # Columna ancha alineada a izq
                tabla_html += '<th style="width:10%">PTS</th>'
                tabla_html += '<th style="width:9%">PJ</th>'
                tabla_html += '<th style="width:9%">GF</th>'
                tabla_html += '<th style="width:9%">GC</th>'
                tabla_html += '<th style="width:8%">DG</th>'
                tabla_html += '</tr></thead><tbody>'

                for _, r in df_f.iterrows():
                    url = mapa_escudos.get(r['EQ'])
                    # Renderizado de imagen
                    img_html = f'<img src="{url}" class="img-escudo">' if url else ''
                    escudo_final = f'<div class="escudo-wrapper">{img_html}</div>'
                    
                    tabla_html += "<tr>"
                    tabla_html += f"<td>{r['POS']}</td>"
                    
                    # Estilos específicos de la celda de Nombre (Negrita, corte de texto si es muy largo)
                    tabla_html += f"<td style='text-align:left; padding-left:10px; font-weight:bold; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;'>"
                    tabla_html += f"{escudo_final}{r['EQ']}</td>"
                    
                    # Estilo columna Puntos (Color del torneo y negrita)
                    tabla_html += f"<td style='color:{color_maestro}; font-weight:bold; font-size:14px;'>{r['PTS']}</td>"
                    
                    tabla_html += f"<td>{r['PJ']}</td>"
                    tabla_html += f"<td>{r['GF']}</td>"
                    tabla_html += f"<td>{r['GC']}</td>"
                    tabla_html += f"<td style='font-size:11px; color:#888;'>{r['DG']}</td>"
                    tabla_html += "</tr>"

                tabla_html += "</tbody></table>"
                st.markdown(plantilla_tabla + tabla_html, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Error al cargar la clasificación: {e}")
    
    # ------------------------------------------
    # CASO B: OTROS FORMATOS (Cruces)
    # ------------------------------------------
    else:
        mostrar_bot("Este torneo se juega por llaves de eliminación directa.")
        st.info("🚧 Visualizador de Cuadro de Honor / Bracket en construcción.")

        




        
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

        # 1. TORNEO
        with tabs[0]:
            # ¡AQUÍ ESTÁ LA MAGIA! LLAMAMOS A LA FUNCIÓN
            contenido_pestana_torneo(id_torneo, t_color)

        # 2. CONTROL (Panel de Gestión)
        with tabs[1]:
            st.markdown(f"#### ⚙️ Administración de {t_nombre}")
            
            # --- CSS Exclusivo Admin ---
            st.markdown(f"""<style>div[data-testid="stExpander"] {{ border: 1px solid {t_color}; border-radius: 5px; }}</style>""", unsafe_allow_html=True)

            # Lógica de Sub-Pestañas Dinámicas
            if t_fase == "inscripcion":
                sub_tabs = st.tabs(["⏳ Lista de Espera", "📋 Directorio", "⚙️ Configuración"])
            else:
                sub_tabs = st.tabs(["⚽ Gestión Partidos", "📋 Directorio", "⚙️ Configuración"])

            # ==========================================
            # SUB-TAB 1: DINÁMICA (LISTA DE ESPERA / PARTIDOS)
            # ==========================================
            with sub_tabs[0]:
                if t_fase == "inscripcion":
                    try:
                        with conn.connect() as db:
                            q_pend = text("SELECT * FROM equipos_globales WHERE id_torneo = :id AND estado = 'pendiente'")
                            df_pend = pd.read_sql_query(q_pend, db, params={"id": id_torneo})
                        
                        if df_pend.empty:
                            mostrar_bot("Todo tranquilo por aquí, Presi. <b>No hay solicitudes pendientes</b>.")
                        else:
                            mostrar_bot(f"¡Atención! Tienes <b>{len(df_pend)} equipos</b> esperando tu visto bueno.")
                            
                            for _, r in df_pend.iterrows():
                                with st.container(border=True):
                                    c1, c2, c3 = st.columns([0.5, 3, 1], vertical_alignment="center")
                                    with c1:
                                        if r['escudo']: st.image(r['escudo'], width=50)
                                        else: st.write("🛡️")
                                    with c2:
                                        st.markdown(f"**{r['nombre']}**")
                                        cel_clean = str(r['celular_capitan']).replace(' ', '')
                                        # Privacidad: Sin PIN
                                        st.markdown(f"📞 [{r['prefijo']} {r['celular_capitan']}](https://wa.me/{r['prefijo'].replace('+','')}{cel_clean})")
                                    with c3:
                                        if st.button("Aprobar ✅", key=f"apr_{r['id']}", use_container_width=True):
                                            with conn.connect() as db:
                                                db.execute(text("UPDATE equipos_globales SET estado='aprobado' WHERE id=:id"), {"id": r['id']})
                                                db.commit()
                                            st.toast(f"{r['nombre']} Aprobado"); time.sleep(1); st.rerun()
                    except Exception as e:
                        st.error(f"Error cargando lista: {e}")

                else:
                    mostrar_bot("El balón está rodando. Aquí podrás cargar los marcadores cuando configuremos el fixture.")

            # ==========================================
            # SUB-TAB 2: DIRECTORIO (Con Baja Lógica)
            # ==========================================
            with sub_tabs[1]:
                st.subheader("Equipos Aprobados")
                
                # --- LÓGICA DE CONFIRMACIÓN DE BAJA ---
                if "baja_equipo_id" in st.session_state:
                    with st.container(border=True):
                        st.warning(f"⚠️ **CONFIRMACIÓN REQUERIDA**")
                        st.write(f"¿Seguro que quieres dar de baja al equipo **{st.session_state.baja_equipo_nombre}** del torneo **{t_nombre}**?")
                        st.caption("El equipo saldrá del torneo pero sus datos permanecerán guardados.")
                        
                        col_si, col_no = st.columns(2)
                        if col_si.button("✅ Sí, dar de baja", type="primary", use_container_width=True):
                            with conn.connect() as db:
                                # CAMBIO CLAVE: UPDATE en vez de DELETE
                                db.execute(text("UPDATE equipos_globales SET estado='baja' WHERE id=:id"), {"id": st.session_state.baja_equipo_id})
                                db.commit()
                            del st.session_state.baja_equipo_id
                            del st.session_state.baja_equipo_nombre
                            st.success("Equipo dado de baja del torneo."); time.sleep(1); st.rerun()
                            
                        if col_no.button("❌ Cancelar", use_container_width=True):
                            del st.session_state.baja_equipo_id
                            del st.session_state.baja_equipo_nombre
                            st.rerun()
                    st.divider()

                # --- LISTADO ---
                try:
                    with conn.connect() as db:
                        q_aprob = text("SELECT id, nombre, celular_capitan, prefijo, escudo FROM equipos_globales WHERE id_torneo = :id AND estado = 'aprobado' ORDER BY nombre ASC")
                        df_aprob = pd.read_sql_query(q_aprob, db, params={"id": id_torneo})
                    
                    if df_aprob.empty:
                        st.warning("Aún no has aprobado equipos.")
                    else:
                        st.markdown(f"**Total:** {len(df_aprob)} equipos listos.")
                        for _, row in df_aprob.iterrows():
                            with st.container():
                                c_img, c_info, c_del = st.columns([0.5, 3.5, 1], vertical_alignment="center")
                                with c_img:
                                    if row['escudo']: st.image(row['escudo'], width=35)
                                    else: st.write("🛡️")
                                with c_info:
                                    pref_url = str(row['prefijo']).replace('+', '')
                                    cel_url = str(row['celular_capitan']).replace(' ', '')
                                    link_wa = f"https://wa.me/{pref_url}{cel_url}"
                                    st.markdown(f"**{row['nombre']}** • [`Chat`]({link_wa})")
                                with c_del:
                                    if st.button("⛔ Bajar", key=f"del_{row['id']}", help="Dar de baja del torneo"):
                                        st.session_state.baja_equipo_id = row['id']
                                        st.session_state.baja_equipo_nombre = row['nombre']
                                        st.rerun()
                            st.divider()
                except Exception as e:
                    st.error(f"Error listando equipos: {e}")

            # ==========================================
            # SUB-TAB 3: CONFIGURACIÓN
            # ==========================================
            with sub_tabs[2]:
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

                # Control de Fases
                st.markdown(f"##### 🚀 Fase Actual: `{t_fase.upper()}`")
                
                if t_fase == "inscripcion":
                    if st.button("🔐 Cerrar Inscripciones e Iniciar Competencia", type="primary", use_container_width=True):
                        st.session_state.confirmar_inicio = True
                    
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
            if st.button("🔴 Cerrar Sesión Admin", use_container_width=True):
                st.session_state.clear(); st.rerun()



                

 # --- ESCENARIO B: DT (Director Técnico) ---
    elif rol_actual == "DT":
        
        # 0. BOTÓN SALIR
        c_vacio, c_salir = st.columns([6, 1])
        if c_salir.button("🔴 Cerrar sesión de Club", key="btn_salir_dt", use_container_width=True):
            st.session_state.clear()
            st.rerun()

        # Pestañas
        tabs = st.tabs(["🏆 Torneo", "📅 Calendario", "👤 Mi Equipo"])

        # 1. TORNEO
        with tabs[0]:
             contenido_pestana_torneo(id_torneo, t_color)

        # 2. CALENDARIO (Solo sus partidos)
        with tabs[1]:
            if t_fase == "inscripcion":
                mostrar_bot("El balón aún no rueda, Profe. Cuando inicie el torneo, aquí verás tu calendario.")
              
            else:
                st.subheader(f"📅 Calendario de {st.session_state.nombre_equipo}")
                
                try:
                    with conn.connect() as db:
                        # Buscamos partidos donde el equipo sea Local O Visitante
                        q_cal = text("""
                            SELECT * FROM partidos 
                            WHERE id_torneo = :id 
                            AND (local = :n OR visitante = :n)
                            ORDER BY jornada ASC, id ASC
                        """)
                        df_cal = pd.read_sql_query(q_cal, db, params={"id": id_torneo, "n": st.session_state.nombre_equipo})
                    
                    if df_cal.empty:
                        st.info("Aún no se han programado tus partidos.")
                    else:
                        # Agrupamos por Jornada para que se vea ordenado
                        jornadas = df_cal['jornada'].unique()
                        
                        for j in jornadas:
                            # Título de la Jornada o Fase
                            lbl_jornada = f"Jornada {j}" if str(j).isdigit() else j
                            st.markdown(f"##### 📍 {lbl_jornada}")
                            
                            # Filtramos los partidos de esta jornada
                            df_j = df_cal[df_cal['jornada'] == j]
                            
                            for _, p in df_j.iterrows():
                                with st.container(border=True):
                                    # Diseño de Tarjeta de Partido
                                    c_loc, c_vs, c_vis = st.columns([2, 0.5, 2], vertical_alignment="center")
                                    
                                    # Equipo Local
                                    with c_loc:
                                        st.markdown(f"<div style='text-align:right; font-weight:bold;'>{p['local']}</div>", unsafe_allow_html=True)
                                        if p['goles_l'] is not None:
                                            st.markdown(f"<div style='text-align:right; font-size:20px; color:{t_color};'>{int(p['goles_l'])}</div>", unsafe_allow_html=True)
                                    
                                    # VS
                                    with c_vs:
                                        st.markdown("<div style='text-align:center; color:#888;'>vs</div>", unsafe_allow_html=True)
                                    
                                    # Equipo Visitante
                                    with c_vis:
                                        st.markdown(f"<div style='text-align:left; font-weight:bold;'>{p['visitante']}</div>", unsafe_allow_html=True)
                                        if p['goles_v'] is not None:
                                            st.markdown(f"<div style='text-align:left; font-size:20px; color:{t_color};'>{int(p['goles_v'])}</div>", unsafe_allow_html=True)
                                    
                                    st.divider()
                                    
                                    # ESTADO Y ACCIONES
                                    c_status, c_action = st.columns([2, 1], vertical_alignment="center")
                                    
                                    with c_status:
                                        if p['estado'] == 'Finalizado':
                                            st.caption("✅ Finalizado")
                                        else:
                                            st.caption("⏳ Pendiente / En Juego")
                                    
                                    with c_action:
                                        # Solo permitimos subir foto si NO está finalizado aún (o para corregir)
                                        # Usamos un key único por partido
                                        key_up = f"evidencia_{p['id']}"
                                        
                                        # Popover para subir la evidencia sin salir de la pantalla
                                        with st.popover("📸 Reportar"):
                                            st.markdown("Subir foto del marcador final:")
                                            foto_ev = st.file_uploader("Evidencia", type=['jpg', 'png'], key=f"u_{p['id']}", label_visibility="collapsed")
                                            
                                            if foto_ev:
                                                if st.button("Enviar Resultado", key=f"b_{p['id']}"):
                                                    # Aquí iría la lógica de OCR o guardado de la imagen para revisión del Admin
                                                    # Por ahora, simulamos el envío al admin
                                                    st.success("Evidencia enviada al Admin.")
                                                    time.sleep(1)
                                                    # (Opcional) Aquí podrías actualizar un campo 'evidencia_url' en la tabla partidos
                            
                            st.write("") # Espacio entre jornadas

                except Exception as e:
                    st.error(f"Error cargando calendario: {e}")


                    

        # 3. MI EQUIPO
        with tabs[2]:
            sub_tabs = st.tabs(["📊 Estadísticas", "✏️ Editar Equipo"])
            
            with sub_tabs[0]:
                st.subheader("📊 Historia del Club")
                mostrar_bot("Estoy recopilando los datos. Pronto verás aquí tu rendimiento.")
                st.image("https://cdn-icons-png.flaticon.com/512/3094/3094845.png", width=100)
            
            # --- LÓGICA DE EDICIÓN ROBUSTA ---
            with sub_tabs[1]:
                id_eq = st.session_state.id_equipo
                
                try:
                    with conn.connect() as db:
                        # Traemos el registro específico de ESTE torneo
                        q_me = text("SELECT * FROM equipos_globales WHERE id = :id")
                        me = db.execute(q_me, {"id": id_eq}).fetchone()

                    if me:
                        # 1. Recuperar datos actuales de la DB
                        p1 = me.prefijo_dt1 if me.prefijo_dt1 else "+57"
                        n1 = me.celular_dt1 if me.celular_dt1 else ""
                        p2 = me.prefijo_dt2 if me.prefijo_dt2 else "+57"
                        n2 = me.celular_dt2 if me.celular_dt2 else ""
                        
                        # ¿Tiene dos números registrados válidos?
                        tiene_dos = (len(str(n1)) > 5 and len(str(n2)) > 5)

                        with st.form("form_mi_equipo"):
                            
                            # ==========================================
                            # A. SELECTOR DE CAPITÁN (Lógica Torneo)
                            # ==========================================
                            if tiene_dos:
                                st.markdown(f"#### ©️ Contacto Visible (Capitán del Torneo)")
                                st.caption("¿A quién deben llamar los rivales y el Admin **en este torneo**?")
                                
                                # Opciones claras
                                lbl_opt1 = f"👑 DT Principal ({p1} {n1})"
                                lbl_opt2 = f"🤝 Co-DT ({p2} {n2})"
                                
                                # Pre-selección inteligente:
                                # Si el número guardado como 'capitán' coincide con el DT2, marcamos el 2.
                                # Si no, marcamos el 1 (Principal).
                                idx_activo = 1 if me.celular_capitan == n2 else 0
                                
                                sel_capitan = st.radio("Selecciona el responsable activo:", 
                                                     [lbl_opt1, lbl_opt2], 
                                                     index=idx_activo, 
                                                     horizontal=True)
                                st.divider()
                            else:
                                sel_capitan = "Unico" # Marcador interno

                            # ==========================================
                            # B. EDICIÓN DE DATOS GLOBALES
                            # ==========================================
                            st.subheader("✏️ Datos del Club")
                            
                            # IDENTIDAD
                            with st.container(border=True):
                                st.markdown("**🪪 Identidad**")
                                c_id1, c_id2 = st.columns([2, 1])
                                with c_id1:
                                    new_nom = st.text_input("Nombre", value=me.nombre).strip().upper()
                                with c_id2:
                                    new_pin = st.text_input("PIN", value=me.pin_equipo, type="password", max_chars=6).strip().upper()
                                
                                c_esc1, c_esc2 = st.columns([1, 4], vertical_alignment="center")
                                with c_esc1:
                                    if me.escudo: st.image(me.escudo, width=50)
                                    else: st.write("🛡️")
                                with c_esc2:
                                    new_escudo = st.file_uploader("Nuevo Escudo", type=['png', 'jpg'], label_visibility="collapsed")

                            # Lista Países
                            paises = {
                                "Argentina": "+54", "Belice": "+501", "Bolivia": "+591", "Brasil": "+55",
                                "Chile": "+56", "Colombia": "+57", "Costa Rica": "+506", "Ecuador": "+593",
                                "EEUU/CANADA": "+1", "El Salvador": "+503", "Guatemala": "+502", 
                                "Guayana Fran": "+594", "Guyana": "+592", "Honduras": "+504", "México": "+52",
                                "Nicaragua": "+505", "Panamá": "+507", "Paraguay": "+595", "Perú": "+51",
                                "Surinam": "+597", "Uruguay": "+598", "Venezuela": "+58"
                            }
                            l_paises = [f"{k} ({paises[k]})" for k in sorted(paises.keys())]

                            # DT 1
                            with st.container(border=True):
                                st.markdown("**👤 DT Principal**")
                                c_dt1_p, c_dt1_n = st.columns([1.5, 2])
                                try: 
                                    current_val = next((k for k, v in paises.items() if v == p1), "Colombia")
                                    idx_p1 = sorted(paises.keys()).index(current_val)
                                except: idx_p1 = 0
                                
                                s_p1 = c_dt1_p.selectbox("P-DT1", l_paises, index=idx_p1, label_visibility="collapsed")
                                val_p1 = s_p1.split('(')[-1].replace(')', '')
                                val_n1 = c_dt1_n.text_input("N-DT1", value=n1, label_visibility="collapsed")

                            # DT 2
                            with st.container(border=True):
                                st.markdown("**👥 Co-DT (Opcional)**")
                                c_dt2_p, c_dt2_n = st.columns([1.5, 2])
                                try: 
                                    current_val2 = next((k for k, v in paises.items() if v == p2), "Colombia")
                                    idx_p2 = sorted(paises.keys()).index(current_val2)
                                except: idx_p2 = 0
                                
                                s_p2 = c_dt2_p.selectbox("P-DT2", l_paises, index=idx_p2, label_visibility="collapsed")
                                val_p2 = s_p2.split('(')[-1].replace(')', '')
                                val_n2 = c_dt2_n.text_input("N-DT2", value=n2, label_visibility="collapsed")

                            st.write("")
                            
                            # ==========================================
                            # C. PROCESADO Y GUARDADO
                            # ==========================================
                            if st.form_submit_button("💾 Guardar Cambios", use_container_width=True):
                                
                                # 1. Escudo
                                url_final = me.escudo
                                if new_escudo:
                                    url_final = procesar_y_subir_escudo(new_escudo, new_nom, id_torneo)
                                
                                # 2. Lógica: ¿Quién es el capitán HOY?
                                # Si tiene 2 números Y seleccionó la opción que contiene "Co-DT"
                                if tiene_dos and sel_capitan and ("Co-DT" in sel_capitan) and len(val_n2) > 5:
                                    pub_cel = val_n2
                                    pub_pref = val_p2
                                else:
                                    # Por defecto (o si seleccionó DT Principal)
                                    pub_cel = val_n1
                                    pub_pref = val_p1

                                try:
                                    with conn.connect() as db:
                                        # 3. UPDATE GLOBAL (Identidad y Contactos Base)
                                        # Actualizamos los datos "fuente" (DT1 y DT2) en TODAS las inscripciones de este PIN
                                        db.execute(text("""
                                            UPDATE equipos_globales 
                                            SET nombre=:n, pin_equipo=:new_pin, escudo=:e, 
                                                celular_dt1=:c1, prefijo_dt1=:p1,
                                                celular_dt2=:c2, prefijo_dt2=:p2
                                            WHERE pin_equipo=:old_pin
                                        """), {
                                            "n": new_nom, "new_pin": new_pin, "e": url_final,
                                            "c1": val_n1, "p1": val_p1,
                                            "c2": val_n2, "p2": val_p2,
                                            "old_pin": me.pin_equipo
                                        })
                                        
                                        # 4. UPDATE LOCAL (Capitán del Torneo)
                                        # Aquí guardamos QUIÉN es el visible PARA ESTE TORNEO (id)
                                        db.execute(text("""
                                            UPDATE equipos_globales 
                                            SET celular_capitan=:cp, prefijo=:pp
                                            WHERE id=:id
                                        """), {
                                            "cp": pub_cel, "pp": pub_pref, "id": id_eq
                                        })

                                        # 5. SINCRONIZACIÓN PARTIDOS (Protegida)
                                        if new_nom != me.nombre:
                                            try:
                                                db.execute(text("UPDATE partidos SET local=:n WHERE local=:old AND id_torneo=:idt"), {"n": new_nom, "old": me.nombre, "idt": id_torneo})
                                                db.execute(text("UPDATE partidos SET visitante=:n WHERE visitante=:old AND id_torneo=:idt"), {"n": new_nom, "old": me.nombre, "idt": id_torneo})
                                            except Exception as e_match:
                                                print(f"Warning partidos: {e_match}")
                                        
                                        st.session_state.nombre_equipo = new_nom
                                        db.commit()
                                    
                                    st.toast("✅ Datos actualizados correctamente")
                                    time.sleep(1.5); st.rerun()
                                
                                except Exception as e_main:
                                    st.error(f"Error guardando datos: {e_main}")

                except Exception as e_load:
                    st.error(f"Error cargando perfil: {e_load}")
                    


                


# --- ESCENARIO C: ESPECTADOR (Por defecto) ---
    else:
        # Pestañas ordenadas
        tabs = st.tabs(["📝 Inscripciones", "🏆 Torneo", "🔐 Ingreso"])

        # ==========================================
        # 1. INSCRIPCIONES (Lógica Doble Vía con Flujo de Estados Correcto)
        # ==========================================
 
        with tabs[0]:
            if t_fase == "inscripcion":
                
                # CEREBRO GOL BOT
                if "msg_bot_ins" not in st.session_state:
                    st.session_state.msg_bot_ins = "👋 ¡Hola! Si tu club ya esta registrado, recuerdame el PIN para inscribirte. Si eres nuevo, registra tu club en el formulario de abajo."
                mostrar_bot(st.session_state.msg_bot_ins)

                # --- OPCIÓN A: VÍA RÁPIDA (YA TENGO PIN) ---
                with st.container(border=True):
                    st.markdown("#### ⚡ ¿Ya tienes un Club registrado?")
                    st.caption("Usa tu PIN existente para inscribirte o reactivar tu solicitud.")
                    
                    c_pin_fast, c_btn_fast = st.columns([3, 1])
                    # AJUSTE: .upper() aquí también para facilitar la búsqueda
                    pin_fast = c_pin_fast.text_input("Tu PIN", max_chars=6, key="pin_fast", label_visibility="collapsed", placeholder="Ej: A1B2").strip().upper()
                    
                    if c_btn_fast.button("Inscribirme", use_container_width=True):
                        if not pin_fast:
                            st.warning("Escribe un PIN.")
                        else:
                            with conn.connect() as db:
                                # PASO 1: BÚSQUEDA LOCAL
                                q_local = text("SELECT id, nombre, estado FROM equipos_globales WHERE id_torneo=:idt AND pin_equipo=:p")
                                local = db.execute(q_local, {"idt": id_torneo, "p": pin_fast}).fetchone()
                                
                                if local:
                                    if local.estado == 'pendiente':
                                        st.info(f"🤖 **Gol Bot:** Tranquilo, tu solicitud con **{local.nombre}** ya está enviada.")
                                    elif local.estado == 'aprobado':
                                        st.success(f"🤖 **Gol Bot:** ¡Pero si ya estás adentro! **{local.nombre}** es oficial.")
                                        st.session_state.rol = "DT"
                                        st.session_state.id_equipo = local.id
                                        st.session_state.nombre_equipo = local.nombre
                                        time.sleep(1.5); st.rerun()
                                    else: # Reactivar baja
                                        db.execute(text("UPDATE equipos_globales SET estado='pendiente' WHERE id=:id"), {"id": local.id})
                                        db.commit()
                                        st.balloons()
                                        st.success(f"✅ ¡Solicitud Reactivada! He vuelto a poner a **{local.nombre}** en la lista de espera.")
                                else:
                                    # PASO 2: BÚSQUEDA GLOBAL
                                    q_global = text("SELECT * FROM equipos_globales WHERE pin_equipo=:p ORDER BY id DESC LIMIT 1")
                                    origen = db.execute(q_global, {"p": pin_fast}).fetchone()
                                    
                                    if origen:
                                        try:
                                            db.execute(text("""
                                                INSERT INTO equipos_globales 
                                                (id_torneo, nombre, pin_equipo, escudo, prefijo, celular_capitan, 
                                                 celular_dt1, prefijo_dt1, celular_dt2, prefijo_dt2, estado)
                                                VALUES 
                                                (:idt, :n, :pi, :e, :pr, :cc, :c1, :p1, :c2, :p2, 'pendiente')
                                            """), {
                                                "idt": id_torneo, "n": origen.nombre, "pi": origen.pin_equipo, 
                                                "e": origen.escudo, "pr": origen.prefijo, "cc": origen.celular_capitan,
                                                "c1": origen.celular_dt1, "p1": origen.prefijo_dt1,
                                                "c2": origen.celular_dt2, "p2": origen.prefijo_dt2
                                            })
                                            db.commit()
                                            nuevo = db.execute(text("SELECT id FROM equipos_globales WHERE id_torneo=:idt AND pin_equipo=:p"),
                                                             {"idt": id_torneo, "p": pin_fast}).fetchone()
                                            st.balloons()
                                            st.success(f"✅ ¡Te encontré! He traído los datos de **{origen.nombre}**.")
                                        except Exception as e:
                                            st.error(f"Error técnico: {e}")
                                    else:
                                        st.error("❌ No reconozco ese PIN. Regístrate como club nuevo abajo.")

                st.markdown("---")

                # --- OPCIÓN B: REGISTRO NUEVO ---
                st.markdown("#### 🌱 ¿Club Nuevo? Registra tu club")
                
                if "reg_estado" not in st.session_state: st.session_state.reg_estado = "formulario"
                if "datos_temp" not in st.session_state: st.session_state.datos_temp = {}

                # ESTADO: CONFIRMACIÓN
                if st.session_state.reg_estado == "confirmar":
                    d = st.session_state.datos_temp
                    with st.container(border=True):
                        c_img, c_txt = st.columns([1, 3], vertical_alignment="center")
                        with c_img:
                             if d['escudo_obj']: 
                                 d['escudo_obj'].seek(0)
                                 st.image(d['escudo_obj'])
                             else: st.write("🛡️")
                        with c_txt:
                            st.markdown(f"**{d['n']}**") # Aquí ya se verá en MAYÚSCULAS
                            st.markdown(f"📞 {d['pref']} {d['wa']}")
                            st.markdown(f"🔐 PIN: `{d['pin']}`")
                    
                    c1, c2 = st.columns(2)
                    if c1.button("✅ Confirmar Inscripción", use_container_width=True):
                         with st.spinner("Creando ficha..."):
                            url_escudo = None
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
                                new_id = db.execute(text("SELECT id FROM equipos_globales WHERE id_torneo=:idt AND pin_equipo=:p AND estado='pendiente'"), 
                                                  {"idt": id_torneo, "p": d['pin']}).fetchone()
                                
                                st.session_state.rol = "DT"
                                st.session_state.id_equipo = new_id.id
                                st.session_state.nombre_equipo = d['n']
                                st.rerun()

                    if c2.button("✏️ Editar", use_container_width=True):
                        st.session_state.reg_estado = "formulario"; st.rerun()

                # ESTADO: FORMULARIO
                else:
                    with st.form("registro_nuevo"):
                        d = st.session_state.get("datos_temp", {})
                        
                        # =========================================================
                        # AJUSTE CLAVE: .upper() AL FINAL DEL INPUT DE NOMBRE
                        # =========================================================
                        nom_f = st.text_input("Nombre del Equipo", value=d.get('n', '')).strip().upper()
                        
                        c_p, c_w = st.columns([1, 2])
                        paises = {
                            "Argentina": "+54", "Belice": "+501", "Bolivia": "+591", "Brasil": "+55",
                            "Chile": "+56", "Colombia": "+57", "Costa Rica": "+506", "Ecuador": "+593",
                            "EEUU/CANADA": "+1", "El Salvador": "+503", "Guatemala": "+502", 
                            "Guayana Fran": "+594", "Guyana": "+592", "Honduras": "+504", "México": "+52",
                            "Nicaragua": "+505", "Panamá": "+507", "Paraguay": "+595", "Perú": "+51",
                            "Surinam": "+597", "Uruguay": "+598", "Venezuela": "+58"
                        }
                        claves_ordenadas = sorted(paises.keys())
                        l_paises = [f"{k} ({paises[k]})" for k in claves_ordenadas]
                        
                        pais_sel = c_p.selectbox("País", l_paises)
                        wa_f = c_w.text_input("WhatsApp DT", value=d.get('wa', ''))
                        
                        # =========================================================
                        # AJUSTE CLAVE: .upper() AL FINAL DEL INPUT DE PIN
                        # =========================================================
                        pin_f = st.text_input("Crea un PIN (Evita una contraseña generica)", value=d.get('pin', ''), max_chars=6).strip().upper()
                        escudo_f = st.file_uploader("Escudo (Opcional)", type=['png', 'jpg'])

                        if st.form_submit_button("Siguiente", use_container_width=True):
                            err = False
                            with conn.connect() as db:
                                # Validación Nombre (Ya llega en Mayúsculas, la comparación funciona igual)
                                q_nom = text("SELECT 1 FROM equipos_globales WHERE id_torneo=:i AND nombre=:n AND (estado='aprobado' OR estado='pendiente')")
                                if db.execute(q_nom, {"i": id_torneo, "n": nom_f}).fetchone():
                                    st.error("Ese nombre ya existe activo en este torneo."); err = True
                                
                                q_pin = text("SELECT nombre FROM equipos_globales WHERE pin_equipo=:p LIMIT 1")
                                res_global = db.execute(q_pin, {"p": pin_f}).fetchone()
                                if res_global:
                                    st.warning(f"🤖 **Gol Bot:** El PIN **{pin_f}** ya existe (Club: {res_global.nombre}). Usa la opción de arriba.")
                                    err = True
                            
                            if not err and nom_f and wa_f and len(pin_f) > 3:
                                st.session_state.datos_temp = {
                                    "n": nom_f, "wa": wa_f, "pin": pin_f, 
                                    "pref": pais_sel.split('(')[-1][:-1], "escudo_obj": escudo_f
                                }
                                st.session_state.reg_estado = "confirmar"
                                st.rerun()
            else:
                st.warning("🚫 Inscripciones Cerradas.")


                

        # 2. TORNEO
        with tabs[1]:
             # LLAMADA A LA FUNCIÓN
             contenido_pestana_torneo(id_torneo, t_color)
             
        # 3. INGRESO (Login Clásico Actualizado)
        with tabs[2]:
            st.subheader("🔐 Acceso DT / Admin")
            with st.container(border=True):
                c_in, c_btn = st.columns([3, 1])
                pin_log = c_in.text_input("PIN", type="password", label_visibility="collapsed", placeholder="Ingresa PIN")
                
                if c_btn.button("Entrar", type="primary", use_container_width=True):
                    acc = validar_acceso(id_torneo, pin_log)
                    
                    # CASO 1: Login Exitoso (Devuelve Diccionario)
                    if isinstance(acc, dict):
                        st.session_state.update(acc)
                        st.rerun()
                    
                    # CASO 2: En Lista de Espera (Devuelve String "PENDIENTE")
                    elif acc == "PENDIENTE":
                        st.warning("⏳ Tu equipo está en **Lista de Espera**. El Admin debe aprobarte antes de que puedas gestionar tu plantilla.")
                    
                    # CASO 3: PIN Incorrecto o Baja
                    else:
                        st.error("PIN no válido en este torneo.")


                        

            st.markdown("---")
            if st.button("🔴 Cerrar Sesión Admin", use_container_width=True):
                st.session_state.clear(); st.rerun()


                        
# --- 4.3 EJECUCIÓN ---
params = st.query_params
if "id" in params: render_torneo(params["id"])
else: render_lobby()











































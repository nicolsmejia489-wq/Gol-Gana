from PIL import Image, ImageOps, ImageChops
import requests
from io import BytesIO
import config

# --- DIMENSIONES MÓVILES (Vertical HD) ---
ANCHO_CANVAS = 1080
ALTO_CANVAS = 1920

# --- CONFIGURACIÓN DE ZONAS (Ajusta estos valores si quieres mover cosas) ---
MARGEN_SUPERIOR = 120   # Espacio desde el techo (para la barra de estado del cel)
MARGEN_LATERAL = 50     # Espacio a los lados
TAMAÑO_ESCUDO_FONDO = 0.85 # El escudo ocupará el 85% del ancho de la pantalla

def descargar_imagen(url):
    """Descarga imagen y la convierte a RGBA para manejar transparencias."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content)).convert("RGBA")
        return img
    except Exception as e:
        print(f"Error descargando {url}: {e}")
        # Retorna una imagen vacía transparente para no romper el script
        return Image.new("RGBA", (100, 100), (0, 0, 0, 0))

def teñir_plantilla(imagen_plantilla, color_hex):
    """
    Aplica el 'Efecto Multiplicar':
    Lo blanco se vuelve del color elegido.
    Lo negro/gris oscuro se mantiene (sombras).
    """
    # Separamos el canal Alfa (la transparencia)
    r, g, b, alpha = imagen_plantilla.split()
    imagen_gris = Image.merge("RGB", (r, g, b))
    
    # Creamos un bloque sólido del color del campeón
    lienzo_color = Image.new("RGB", imagen_gris.size, color_hex)
    
    # Fusión Matemática (Multiplicar)
    imagen_teñida = ImageChops.multiply(imagen_gris, lienzo_color)
    
    # Le devolvemos su transparencia original
    imagen_teñida.putalpha(alpha)
    return imagen_teñida

def procesar_escudo_fantasma(img_escudo):
    """Convierte el escudo en una textura de fondo oscura y sutil."""
    # 1. Convertir a Escala de Grises
    escudo = img_escudo.convert("L").convert("RGBA")
    
    # 2. Redimensionar (Gigante)
    ancho_objetivo = int(ANCHO_CANVAS * TAMAÑO_ESCUDO_FONDO)
    factor = ancho_objetivo / escudo.width
    nuevo_alto = int(escudo.height * factor)
    escudo = escudo.resize((ancho_objetivo, nuevo_alto), Image.Resampling.LANCZOS)
    
    # 3. Aplicar Transparencia (Fantasma)
    # Hacemos que sea muy sutil (Opacidad baja)
    datos = escudo.getdata()
    nuevos_datos = []
    for item in datos:
        # Mantenemos RGB, bajamos Alpha al 15% (38 de 255)
        nuevo_alpha = int(item[3] * 0.15) 
        nuevos_datos.append((item[0], item[1], item[2], nuevo_alpha))
    
    escudo.putdata(nuevos_datos)
    return escudo

def construir_portada(color_campeon, url_escudo_campeon):
    print(f"📱 Diseñando interfaz móvil con color: {color_campeon}...")

    # --- PASO 1: CARGA DE INGREDIENTES ---
    fondo = descargar_imagen(config.ASSETS["fondo_base"])
    jugador = descargar_imagen(config.ASSETS["plantilla_jugador"])
    logo = descargar_imagen(config.ASSETS["plantilla_logo"])
    
    # Intentar cargar escudo campeón, si falla usar backup
    if url_escudo_campeon:
        escudo = descargar_imagen(url_escudo_campeon)
    else:
        escudo = descargar_imagen(config.DEFAULTS["escudo_backup"])

    # --- PASO 2: PROCESAMIENTO ---
    
    # A. Fondo: Recorte vertical inteligente
    fondo_vertical = ImageOps.fit(fondo, (ANCHO_CANVAS, ALTO_CANVAS), centering=(0.5, 0.5))
    
    # B. Escudo Fantasma (Fondo)
    escudo_fantasma = procesar_escudo_fantasma(escudo)
    
    # C. Jugador (Teñido)
    jugador_coloreado = teñir_plantilla(jugador, color_campeon)
    
    # D. Logo (Teñido)
    logo_coloreado = teñir_plantilla(logo, color_campeon)

    # --- PASO 3: MONTAJE (LAYERS) ---
    lienzo = fondo_vertical.copy()

    # --- CAPA 1: EL ESCUDO FANTASMA (ZONA INFERIOR/CENTRAL) ---
    # Lo colocamos centrado horizontalmente
    x_escudo = (ANCHO_CANVAS - escudo_fantasma.width) // 2
    # Lo colocamos en la mitad inferior para llenar el vacío
    y_escudo = ALTO_CANVAS - escudo_fantasma.height - 300 
    lienzo.alpha_composite(escudo_fantasma, (x_escudo, y_escudo))

    # --- CAPA 2: EL LOGO (SUPERIOR IZQUIERDA) ---
    # Definimos que el logo ocupe el 40% del ancho
    ancho_logo = int(ANCHO_CANVAS * 0.40)
    ratio_logo = ancho_logo / logo_coloreado.width
    alto_logo = int(logo_coloreado.height * ratio_logo)
    logo_final = logo_coloreado.resize((ancho_logo, alto_logo), Image.Resampling.LANCZOS)
    
    # Posición: Arriba a la Izquierda
    lienzo.alpha_composite(logo_final, (MARGEN_LATERAL, MARGEN_SUPERIOR))

    # --- CAPA 3: EL JUGADOR (SUPERIOR DERECHA) ---
    # Definimos que el jugador ocupe el 45% del ancho (para equilibrar con el logo)
    ancho_jug = int(ANCHO_CANVAS * 0.45)
    ratio_jug = ancho_jug / jugador_coloreado.width
    alto_jug = int(jugador_coloreado.height * ratio_jug)
    jugador_final = jugador_coloreado.resize((ancho_jug, alto_jug), Image.Resampling.LANCZOS)
    
    # Posición: Arriba a la Derecha
    # X = Ancho Total - Ancho Jugador - Margen
    x_jug = ANCHO_CANVAS - ancho_jug - MARGEN_LATERAL
    # Y = Alineado con el logo (un poco más arriba para que la copa destaque)
    y_jug = MARGEN_SUPERIOR - 20 
    lienzo.alpha_composite(jugador_final, (x_jug, y_jug))

    return lienzo

# --- BLOQUE DE PRUEBA LOCAL ---
if __name__ == "__main__":
    # URL de prueba (Escudo Fifinhos)
    url_test = "https://res.cloudinary.com/dlvczeqlp/image/upload/v1768951368/escudos_limpios/h0brcsuihwiznexlcaz0.png"
    # Color rojo de prueba
    img = construir_portada("#D11D28", url_test)
    img.show()

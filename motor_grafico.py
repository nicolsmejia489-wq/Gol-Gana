from PIL import Image, ImageOps, ImageChops
import requests
from io import BytesIO
import config

# --- DIMENSIONES PARA MÓVIL (Vertical 9:16) ---
ANCHO_CANVAS = 1080
ALTO_CANVAS = 1920

def descargar_imagen(url):
    """Descarga imagen y la convierte a RGBA."""
    response = requests.get(url)
    response.raise_for_status()
    img = Image.open(BytesIO(response.content)).convert("RGBA")
    return img

def teñir_plantilla(imagen_plantilla, color_hex):
    """
    Tiñe usando multiplicación.
    NOTA: Requiere que la imagen de entrada sea BLANCA/GRIS con Transparencia real.
    """
    r, g, b, alpha = imagen_plantilla.split()
    imagen_gris = Image.merge("RGB", (r, g, b))
    lienzo_color = Image.new("RGB", imagen_gris.size, color_hex)
    imagen_teñida = ImageChops.multiply(imagen_gris, lienzo_color)
    imagen_teñida.putalpha(alpha)
    return imagen_teñida

def procesar_escudo_fantasma(img_escudo):
    """Crea la marca de agua central."""
    escudo = img_escudo.convert("L").convert("RGBA")
    
    # Hacemos que ocupe el 60% del ancho del celular
    ancho_objetivo = int(ANCHO_CANVAS * 0.75)
    factor = ancho_objetivo / escudo.width
    nuevo_alto = int(escudo.height * factor)
    escudo = escudo.resize((ancho_objetivo, nuevo_alto), Image.Resampling.LANCZOS)
    
    # Opacidad baja (10%) para que no compita con el texto
    datos = escudo.getdata()
    nuevos_datos = []
    for item in datos:
        nuevo_alpha = int(item[3] * 0.12) # 12% de opacidad
        nuevos_datos.append((item[0], item[1], item[2], nuevo_alpha))
    
    escudo.putdata(nuevos_datos)
    return escudo

def construir_portada(color_campeon, url_escudo_campeon):
    print(f"📱 Construyendo fondo vertical móvil: {color_campeon}...")

    # --- 1. CARGA DE RECURSOS ---
    fondo = descargar_imagen(config.ASSETS["fondo_base"])
    jugador = descargar_imagen(config.ASSETS["plantilla_jugador"])
    logo = descargar_imagen(config.ASSETS["plantilla_logo"])
    
    try:
        escudo = descargar_imagen(url_escudo_campeon)
    except:
        escudo = descargar_imagen(config.DEFAULTS["escudo_backup"])

    # --- 2. PROCESAMIENTO ---
    
    # A. FONDO: Ajuste Inteligente (Crop) para llenar el vertical
    # Esto toma el centro de la imagen horizontal y la recorta a 1080x1920
    fondo_vertical = ImageOps.fit(fondo, (ANCHO_CANVAS, ALTO_CANVAS), centering=(0.5, 0.5))

    # B. ESCUDO FANTASMA
    escudo_fantasma = procesar_escudo_fantasma(escudo)

    # C. JUGADOR (Teñido)
    jugador_coloreado = teñir_plantilla(jugador, color_campeon)

    # D. LOGO (Teñido)
    logo_coloreado = teñir_plantilla(logo, color_campeon)

    # --- 3. ENSAMBLAJE (LAYERS) ---
    lienzo = fondo_vertical.copy()

    # CAPA 1: Escudo Fantasma (Centro absoluto)
    x_escudo = (ANCHO_CANVAS - escudo_fantasma.width) // 2
    y_escudo = (ALTO_CANVAS - escudo_fantasma.height) // 2
    lienzo.alpha_composite(escudo_fantasma, (x_escudo, y_escudo))

    # CAPA 2: Jugador (Abajo Centrado - Estilo Portada FIFA)
    # Queremos que el jugador sea GRANDE, ocupando el 60% de la altura
    alto_jug_obj = int(ALTO_CANVAS * 0.65)
    ratio_jug = alto_jug_obj / jugador_coloreado.height
    ancho_jug_obj = int(jugador_coloreado.width * ratio_jug)
    jugador_final = jugador_coloreado.resize((ancho_jug_obj, alto_jug_obj), Image.Resampling.LANCZOS)
    
    x_jug = (ANCHO_CANVAS - ancho_jug_obj) // 2
    y_jug = ALTO_CANVAS - alto_jug_obj # Pegado al piso (borde inferior)
    lienzo.alpha_composite(jugador_final, (x_jug, y_jug))

    # CAPA 3: Logo (Arriba Centrado)
    ancho_logo_obj = int(ANCHO_CANVAS * 0.6) # 60% del ancho de pantalla
    ratio_logo = ancho_logo_obj / logo_coloreado.width
    alto_logo_obj = int(logo_coloreado.height * ratio_logo)
    logo_final = logo_coloreado.resize((ancho_logo_obj, alto_logo_obj), Image.Resampling.LANCZOS)
    
    x_logo = (ANCHO_CANVAS - ancho_logo_obj) // 2
    y_logo = 150 # Margen superior de 150px (para librar la barra de estado del celular)
    lienzo.alpha_composite(logo_final, (x_logo, y_logo))

    return lienzo

# --- PRUEBA RÁPIDA ---
if __name__ == "__main__":
    # URL de prueba (Tu escudo Fifinhos)
    url = "https://res.cloudinary.com/dlvczeqlp/image/upload/v1768951368/escudos_limpios/h0brcsuihwiznexlcaz0.png"
    # Color de prueba (Rojo Fuego)
    res = construir_portada("#D11D28", url)
    res.show()

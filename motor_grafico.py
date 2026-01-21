from PIL import Image, ImageOps, ImageChops, ImageEnhance
import requests
from io import BytesIO
import config  # Importamos tus URLs de config.py

# Dimensiones del Lienzo (Full HD)
ANCHO_CANVAS = 1920
ALTO_CANVAS = 1080

def descargar_imagen(url):
    """Descarga una imagen de Internet y la convierte a objeto PIL RGBA."""
    response = requests.get(url)
    response.raise_for_status()
    img = Image.open(BytesIO(response.content)).convert("RGBA")
    return img

def teñir_plantilla(imagen_plantilla, color_hex):
    """
    Toma una imagen en escala de grises con transparencia (camiseta/logo)
    y la tiñe del color deseado usando 'Multiplicación' para cuidar las sombras.
    """
    # 1. Separar el canal Alpha (Transparencia) para no perderlo
    r, g, b, alpha = imagen_plantilla.split()
    imagen_gris = Image.merge("RGB", (r, g, b))

    # 2. Crear un lienzo sólido del color del campeón
    lienzo_color = Image.new("RGB", imagen_gris.size, color_hex)

    # 3. FUSIÓN: Multiplicar (Gris * Color). 
    # Esto mantiene las sombras negras y tiñe lo blanco.
    imagen_teñida = ImageChops.multiply(imagen_gris, lienzo_color)

    # 4. Recuperar la transparencia original
    imagen_teñida.putalpha(alpha)
    
    return imagen_teñida

def procesar_escudo_fantasma(img_escudo):
    """Convierte el escudo en una marca de agua gris y gigante."""
    # 1. Escala de Grises
    escudo = img_escudo.convert("L").convert("RGBA")
    
    # 2. Redimensionar (Hacerlo gigante, ej: 80% de la altura de la pantalla)
    alto_objetivo = int(ALTO_CANVAS * 0.8)
    factor = alto_objetivo / escudo.height
    nuevo_ancho = int(escudo.width * factor)
    escudo = escudo.resize((nuevo_ancho, alto_objetivo), Image.Resampling.LANCZOS)
    
    # 3. Bajar Opacidad (Hacerlo casi transparente - 10%)
    # Creamos una máscara alfa con valor 25 (de 255)
    datos = escudo.getdata()
    nuevos_datos = []
    for item in datos:
        # item[0-2] es RGB, item[3] es Alpha actual
        # Reducimos el alpha actual drásticamente
        nuevo_alpha = int(item[3] * 0.10) 
        nuevos_datos.append((item[0], item[1], item[2], nuevo_alpha))
    
    escudo.putdata(nuevos_datos)
    return escudo

def construir_portada(color_campeon, url_escudo_campeon):
    """
    Función Principal: Orquesta todo el ensamblaje.
    Retorna: Objeto de imagen final listo para guardar o subir.
    """
    print(f"🏗️ Construyendo portada con color: {color_campeon}...")

    # --- PASO 1: CARGAR INGREDIENTES ---
    fondo = descargar_imagen(config.ASSETS["fondo_base"])
    # Asegurar tamaño del fondo
    fondo = fondo.resize((ANCHO_CANVAS, ALTO_CANVAS))
    
    jugador = descargar_imagen(config.ASSETS["plantilla_jugador"])
    logo = descargar_imagen(config.ASSETS["plantilla_logo"])
    
    # Cargar escudo del campeón (si falla, usa backup)
    try:
        escudo = descargar_imagen(url_escudo_campeon)
    except:
        escudo = descargar_imagen(config.DEFAULTS["escudo_backup"])

    # --- PASO 2: PROCESAMIENTO (LA COCINA) ---
    
    # A. Escudo Fantasma (Marca de Agua)
    escudo_fantasma = procesar_escudo_fantasma(escudo)
    
    # B. Teñir Jugador
    jugador_coloreado = teñir_plantilla(jugador, color_campeon)
    
    # C. Teñir Logo (Opcional: Si el fondo es oscuro, a veces el logo blanco destaca más. 
    # Pero aquí lo teñiremos para probar la personalización)
    logo_coloreado = teñir_plantilla(logo, color_campeon)

    # --- PASO 3: ENSAMBLAJE (EL EMPLATADO) ---
    
    # Lienzo final (Copia del fondo)
    lienzo = fondo.copy()

    # CAPA 1: Escudo Fantasma (Centrado en el fondo)
    pos_x_escudo = (ANCHO_CANVAS - escudo_fantasma.width) // 2
    pos_y_escudo = (ALTO_CANVAS - escudo_fantasma.height) // 2
    lienzo.alpha_composite(escudo_fantasma, (pos_x_escudo, pos_y_escudo))

    # CAPA 2: Jugador (Alineado abajo a la derecha, o centro según tu imagen)
    # Ajustamos al jugador para que quepa bien (ej: 90% de altura)
    alto_jug = int(ALTO_CANVAS * 0.95)
    ratio_jug = alto_jug / jugador_coloreado.height
    ancho_jug = int(jugador_coloreado.width * ratio_jug)
    jugador_final = jugador_coloreado.resize((ancho_jug, alto_jug), Image.Resampling.LANCZOS)
    
    # Posición: Derecha con un margen
    pos_x_jug = ANCHO_CANVAS - ancho_jug - 100 
    pos_y_jug = ALTO_CANVAS - alto_jug # Pegado al piso
    lienzo.alpha_composite(jugador_final, (pos_x_jug, pos_y_jug))

    # CAPA 3: Logo (Esquina superior izquierda)
    # Redimensionar logo si es muy grande
    ancho_logo = 500
    ratio_logo = ancho_logo / logo_coloreado.width
    alto_logo = int(logo_coloreado.height * ratio_logo)
    logo_final = logo_coloreado.resize((ancho_logo, alto_logo), Image.Resampling.LANCZOS)
    
    lienzo.alpha_composite(logo_final, (50, 50)) # Margen de 50px

    return lienzo

# --- PRUEBA LOCAL ---
if __name__ == "__main__":
    # URL de prueba (Escudo Fifinhos)
    url_test = "https://res.cloudinary.com/dlvczeqlp/image/upload/v1768951368/escudos_limpios/h0brcsuihwiznexlcaz0.png"
    color_test = "#d11d28" # Rojo Fifinhos detectado antes
    
    imagen_final = construir_portada(color_test, url_test)
    imagen_final.show() # Abre la imagen en tu visor de fotos local
    # imagen_final.save("prueba_generada.png")

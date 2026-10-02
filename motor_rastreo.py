import time
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from playwright.sync_api import sync_playwright

# ==========================================
# 1. CONFIGURACIÓN DE CONEXIÓN
# ==========================================
SHEET_ID = "10jrOsS054n0atMk8GxQilkXqm6LjsnrwPOZnSx8iDek"
ARCHIVO_CREDENCIALES = "credentials.json" # Asegúrate de que este archivo esté en la misma carpeta

def conectar_sheets():
    print("Conectando a Google Sheets...")
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    credenciales = Credentials.from_service_account_file(ARCHIVO_CREDENCIALES, scopes=scopes)
    cliente = gspread.authorize(credenciales)
    return cliente.open_by_key(SHEET_ID)

# ==========================================
# 2. MOTOR DE RASTREO (PLAYWRIGHT)
# ==========================================
def rastrear_paquetexpress(guia, page):
    """
    Navega a la URL directa de la guía y extrae el último estatus activo basado en el código fuente.
    """
    print(f"  🔍 Buscando guía: {guia}...")
    try:
        # 1. Inyección directa a la URL (mucho más rápido y sin clicks)
        page.goto(f"https://www.paquetexpress.com.mx/rastreo/{guia}", timeout=20000)
        
        # 2. Esperamos a que la línea de tiempo cargue la clase activa que vimos en el DOM
        page.wait_for_selector(".TrackingStatusActive", timeout=10000)
        
        # 3. Extraemos el texto de TODOS los spans que estén dentro de un paso activo
        textos_activos = page.locator(".TrackingStatusActive span").all_inner_texts()
        
        if textos_activos:
            # 4. Limpiamos espacios basura y tomamos el ÚLTIMO elemento de la lista [-1]
            estatus_actual = textos_activos[-1].strip()
            return estatus_actual
        else:
            return "Estatus no encontrado en la línea de tiempo"

    except Exception as e:
        print(f"  ⚠️ Timeout o error de red con la guía {guia}: {e}")
        return "Pendiente de actualización"

# ==========================================
# 3. LÓGICA PRINCIPAL (CONTROLADOR)
# ==========================================
def ejecutar_laboratorio():
    print("Iniciando Motor de Rastreo Independiente...")
    doc = conectar_sheets()
    ws = doc.worksheet("BD_UNIFICADA")
    datos = ws.get_all_values()
    
    headers = [str(h).strip().upper() for h in datos[0]]
    
    # Identificar columnas
    try:
        idx_id = headers.index(next(h for h in headers if "SINIESTRO" in h))
        idx_desc = headers.index(next(h for h in headers if "DESCRIPCI" in h or "REFACCI" in h))
        idx_paq = headers.index(next(h for h in headers if "PAQUETERIA" in h or "PAQUETERÍA" in h))
        idx_guia = headers.index(next(h for h in headers if "GUIA" in h or "GUÍA" in h))
        idx_estatus = headers.index(next(h for h in headers if "ESTATUS" in h and "ENV" not in h))
        idx_estatus_envio = headers.index(next(h for h in headers if "ESTATUS ENV" in h or "RASTREO" in h))
    except StopIteration:
        print("❌ Error: No se encontraron todas las columnas necesarias en BD_UNIFICADA.")
        return

    celdas_a_actualizar = []
    
    # Iniciamos el navegador una sola vez para procesar todas las guías rápido
    with sync_playwright() as p:
        # headless=True significa que no verás el navegador abrirse, corre en segundo plano.
        # Cambia a headless=False si quieres ver visualmente cómo abre la página para depurar.
        browser = p.chromium.launch(headless=True) 
        page = browser.new_page()
        
        # Recorremos la base de datos (saltando el encabezado)
        for i, fila in enumerate(datos[1:]):
            
            # Seguro por si hay filas vacías al final del archivo de Excel
            if len(fila) <= max(idx_paq, idx_guia, idx_estatus, idx_estatus_envio):
                continue
                
            # Normalizamos los valores para evitar errores por espacios o mayúsculas
            fila_estatus = str(fila[idx_estatus]).strip().upper()
            fila_paqueteria = str(fila[idx_paq]).strip().upper()
            fila_guia = str(fila[idx_guia]).strip()
            
            # FILTRO: Solo EN TRANSITO + PAQUETEXPRESS + Que tenga una Guía escrita
            if fila_estatus == "EN TRANSITO" and fila_paqueteria == "PAQUETEXPRESS" and fila_guia:
                siniestro_actual = fila[idx_id]
                desc_actual = fila[idx_desc]
                
                # Ejecutamos el rastreo real
                nuevo_estatus_envio = rastrear_paquetexpress(fila_guia, page)
                print(f"  ✅ Resultado para {siniestro_actual} ({fila_guia}): {nuevo_estatus_envio}")
                
                # Preparamos la celda para actualizar (i + 2 porque 'i' empieza en 0 y hay 1 fila de encabezado)
                celda = gspread.Cell(row=i+2, col=idx_estatus_envio+1, value=nuevo_estatus_envio)
                celdas_a_actualizar.append(celda)
                
                # Pequeña pausa para no saturar los servidores de Paquetexpress
                time.sleep(1.5)
        
        browser.close()

    # Guardado en bloque directo a Sheets
    if celdas_a_actualizar:
        print(f"\nSubiendo {len(celdas_a_actualizar)} actualizaciones a Google Sheets...")
        ws.update_cells(celdas_a_actualizar, value_input_option='USER_ENTERED')
        print("🎉 ¡Sincronización exitosa!")
    else:
        print("\nNo se encontraron guías de Paquetexpress en tránsito para rastrear.")

if __name__ == "__main__":
    ejecutar_laboratorio()
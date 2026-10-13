import time
import re
import datetime
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from playwright.sync_api import sync_playwright

# ==========================================
# 1. CONFIGURACIÓN DE CONEXIÓN
# ==========================================
SHEET_ID = "10jrOsS054n0atMk8GxQilkXqm6LjsnrwPOZnSx8iDek"
ARCHIVO_CREDENCIALES = "credentials.json"

meses_map = {'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6, 
             'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12,
             'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6, 
             'jul': 7, 'ago': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dic': 12}

def convertir_a_formato_mx(fecha_raw):
    if not fecha_raw: return ""
    f_str = str(fecha_raw).strip().lower()
    # Limpiamos palabras de relleno comunes en Paquetexpress (ej. "07 De Octubre Del 2026")
    for palabra in [' de ', ' del ']:
        f_str = f_str.replace(palabra, ' ')
    
    match = re.search(r"(\d{1,2})\s+([a-záéíóú]+)\s+(\d{2,4})", f_str)
    if match:
        try:
            dia = int(match.group(1))
            mes_str = match.group(2)[:3]
            anio = int(match.group(3))
            if anio < 100: anio += 2000
            mes = meses_map.get(mes_str, 1)
            dt = datetime.datetime(anio, mes, dia)
            meses_cortos = {1:'ene', 2:'feb', 3:'mar', 4:'abr', 5:'may', 6:'jun', 7:'jul', 8:'ago', 9:'sep', 10:'oct', 11:'nov', 12:'dic'}
            return f"{dt.day:02d}/{meses_cortos[dt.month]}/{dt.strftime('%y')}"
        except: pass
    return str(fecha_raw)

def conectar_sheets():
    print("Conectando a Google Sheets...")
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    credenciales = Credentials.from_service_account_file(ARCHIVO_CREDENCIALES, scopes=scopes)
    cliente = gspread.authorize(credenciales)
    return cliente.open_by_key(SHEET_ID)

# ==========================================
# 2. MOTOR DE RASTREO CON EXTRACCIÓN DE FECHA Y FIRMA
# ==========================================
def rastrear_paquetexpress(guia, page):
    """
    Navega a la URL de la guía, extrae el estatus, y si está entregado, 
    recupera la fecha de entrega y la persona que recibió.
    """
    print(f"  🔍 Buscando guía: {guia}...")
    try:
        page.goto(f"https://www.paquetexpress.com.mx/rastreo/{guia}", timeout=20000)
        page.wait_for_selector(".TrackingStatusActive", timeout=10000)
        
        textos_activos = page.locator(".TrackingStatusActive span").all_inner_texts()
        estatus_actual = textos_activos[-1].strip() if textos_activos else "Estatus no encontrado"

        # Valores predeterminados por si no ha sido entregado
        fecha_entrega_formateada = ""
        estatus_final_api = estatus_actual

        # Si el paquete ya fue entregado, escaneamos las notificaciones detalladas del DOM
        if "ENTREGADO" in estatus_actual.upper() or "DELIVERED" in estatus_actual.upper():
            try:
                # Extraemos todos los bloques de historial de la línea de tiempo
                items_historial = page.locator("ul li").all_inner_texts()
                for item in items_historial:
                    if "recibió" in item.lower() or "entregada" in item.lower():
                        # 1. Extraer la persona que recibió (lo que está después de "recibió")
                        match_recibe = re.search(r"recibi[oó]\s+([^\n\r]+)", item, re.IGNORECASE)
                        if match_recibe:
                            persona = match_recibe.group(1).strip()
                            estatus_final_api = f"Entregado ({persona})"
                        
                        # 2. Extraer la fecha (ej. "12 De Octubre Del 2026")
                        match_fecha = re.search(r"(\d{1,2}\s+(?:de\s+)?[a-záéíóú]+\s+(?:de\s+|del\s+)?\d{2,4})", item, re.IGNORECASE)
                        if match_fecha:
                            fecha_cruda = match_fecha.group(1)
                            fecha_entrega_formateada = convertir_a_formato_mx(fecha_cruda)
                        break
            except Exception as ex:
                print(f"  ⚠️ Detalle menor extrayendo firma/fecha de {guia}: {ex}")

        return estatus_final_api, fecha_entrega_formateada

    except Exception as e:
        print(f"  ⚠️ Timeout o error de red con la guía {guia}: {e}")
        return "Pendiente de actualización", ""

# ==========================================
# 3. LÓGICA PRINCIPAL (CONTROLADOR Y ACTUALIZACIÓN EN BLOQUE)
# ==========================================
def ejecutar_laboratorio():
    print("Iniciando Motor de Rastreo Inteligente (Con Fecha y Receptor)...")
    doc = conectar_sheets()
    
    # Procesamos tanto la base viva como el histórico por si hay guías activas ahí
    hojas_a_procesar = [doc.worksheet("BD_UNIFICADA")]
    try:
        hojas_a_procesar.append(doc.worksheet("BD_HISTORICO"))
    except:
        pass

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True) 
        page = browser.new_page()
        
        for ws in hojas_a_procesar:
            print(f"\nRevisando hoja: {ws.title}...")
            datos = ws.get_all_values()
            if not datos: continue
            
            headers = [str(h).strip().upper() for h in datos[0]]
            
            try:
                idx_guia = headers.index(next(h for h in headers if "GUIA" in h or "GUÍA" in h))
                idx_paq = headers.index(next(h for h in headers if "PAQUETERIA" in h or "PAQUETERÍA" in h))
                idx_estatus = headers.index(next(h for h in headers if "ESTATUS" in h and "ENV" not in h))
                idx_estatus_envio = headers.index(next(h for h in headers if "ESTATUS ENV" in h or "RASTREO" in h))
                
                # Buscamos de forma segura la columna de Fecha Recibido (o Fecha Entrega)
                idx_fecha_recibido = next((i for i, h in enumerate(headers) if "FECHA REC" in h or "FECHA ENT" in h), None)
            except StopIteration:
                print(f"  [!] Faltan columnas clave en {ws.title}, saltando...")
                continue

            celdas_a_actualizar = []
            
            for i, fila in enumerate(datos[1:]):
                if len(fila) <= max(idx_paq, idx_guia, idx_estatus, idx_estatus_envio):
                    continue
                    
                fila_estatus = str(fila[idx_estatus]).strip().upper()
                fila_paqueteria = str(fila[idx_paq]).strip().upper()
                fila_guia = str(fila[idx_guia]).strip()
                
                # Rastreamos únicamente lo que esté EN TRANSITO y sea Paquetexpress con guía válida
                if fila_estatus == "EN TRANSITO" and fila_paqueteria == "PAQUETEXPRESS" and fila_guia:
                    siniestro_actual = fila[0] if len(fila) > 0 else "N/A"
                    
                    # Llamada al motor mejorado
                    nuevo_estatus_envio, fecha_recibido_extraida = rastrear_paquetexpress(fila_guia, page)
                    print(f"  ✅ [{siniestro_actual}] Guía {fila_guia} ➔ {nuevo_estatus_envio} | Fecha: {fecha_recibido_extraida}")
                    
                    # Columna de Estatus Envío / Rastreo API
                    celdas_a_actualizar.append(gspread.Cell(row=i+2, col=idx_estatus_envio+1, value=nuevo_estatus_envio))
                    
                    # Si el bot encontró fecha de recibido y la columna existe en el sheet, la agregamos al paquete
                    if idx_fecha_recibido is not None and fecha_recibido_extraida:
                        # Solo escribimos si la celda estaba vacía para no pisar datos manuales previos
                        valor_actual_celda = fila[idx_fecha_recibido] if len(fila) > idx_fecha_recibido else ""
                        if not valor_actual_celda.strip():
                            celdas_a_actualizar.append(gspread.Cell(row=i+2, col=idx_fecha_recibido+1, value=fecha_recibido_extraida))
                    
                    time.sleep(1.5)

            if celdas_a_actualizar:
                print(f"\nSubiendo {len(celdas_a_actualizar)} actualizaciones a {ws.title}...")
                ws.update_cells(celdas_a_actualizar, value_input_option='USER_ENTERED')
            else:
                print(f"  -> No hubo guías nuevas para actualizar en {ws.title}.")

        browser.close()
    print("\n🎉 ¡Sincronización de rastreo, fechas y firmas finalizada con éxito!")

if __name__ == "__main__":
    ejecutar_laboratorio()
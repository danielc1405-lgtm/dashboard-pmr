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

meses_map = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6, 
    'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12,
    'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6, 
    'jul': 7, 'ago': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dic': 12
}

PATRON_MESES = r"(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)"

def convertir_a_formato_mx(fecha_raw):
    if not fecha_raw: return ""
    f_str = str(fecha_raw).strip().lower()
    
    # Busca estrictamente: Día + Nombre de Mes Real + Año de 4 dígitos (Ej. "12 De Octubre Del 2026")
    match = re.search(rf"(\d{{1,2}})\s+(?:de\s+)?({PATRON_MESES})\s+(?:de\s+|del\s+)?(\d{{4}})", f_str, re.IGNORECASE)
    if match:
        try:
            dia = int(match.group(1))
            mes_str = match.group(2)[:3].lower()
            anio = int(match.group(3))
            mes = meses_map.get(mes_str)
            if mes:
                dt = datetime.datetime(anio, mes, dia)
                meses_cortos = {1:'ene', 2:'feb', 3:'mar', 4:'abr', 5:'may', 6:'jun', 7:'jul', 8:'ago', 9:'sep', 10:'oct', 11:'nov', 12:'dic'}
                return f"{dt.day:02d}/{meses_cortos[dt.month]}/{dt.strftime('%y')}"
        except: pass
    return ""

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
    print(f"  🔍 Buscando guía: {guia}...")
    try:
        page.goto(f"https://www.paquetexpress.com.mx/rastreo/{guia}", timeout=25000)
        page.wait_for_selector(".TrackingStatusActive", timeout=12000)
        
        textos_activos = page.locator(".TrackingStatusActive span").all_inner_texts()
        estatus_actual = textos_activos[-1].strip() if textos_activos else "Estatus no encontrado"

        fecha_entrega_formateada = ""
        estatus_final_api = estatus_actual

        if "ENTREGADO" in estatus_actual.upper() or "DELIVERED" in estatus_actual.upper():
            try:
                items_historial = page.locator("ul li").all_inner_texts()
                for item in items_historial:
                    if "recibió" in item.lower() or "entregada" in item.lower():
                        # 1. Extraer quién recibió
                        match_recibe = re.search(r"recibi[oó]\s+([^\n\r]+)", item, re.IGNORECASE)
                        if match_recibe:
                            persona = match_recibe.group(1).strip()
                            estatus_final_api = f"Entregado ({persona})"
                        else:
                            estatus_final_api = "Entregado"
                        
                        # 2. Extraer la fecha validando que contenga un mes real (ignora "11:52 Horas")
                        fecha_entrega_formateada = convertir_a_formato_mx(item)
                        break
            except Exception as ex:
                print(f"  ⚠️ Detalle menor extrayendo firma/fecha de {guia}: {ex}")

        return estatus_final_api, fecha_entrega_formateada

    except Exception as e:
        print(f"  ⚠️ Timeout o error de red con la guía {guia}: {e}")
        return "Pendiente de actualización", ""

# ==========================================
# 3. LÓGICA PRINCIPAL
# ==========================================
def ejecutar_laboratorio():
    print("Iniciando Motor de Rastreo Inteligente (Con Fecha Exacta y Receptor)...")
    doc = conectar_sheets()
    hojas_a_procesar = [doc.worksheet("BD_UNIFICADA")]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True) 
        page = browser.new_page()
        cache_guias = {}
        
        for ws in hojas_a_procesar:
            print(f"\nRevisando hoja: {ws.title}...")
            datos = ws.get_all_values()
            if not datos: continue
            
            headers = [str(h).strip().upper() for h in datos[0]]
            
            try:
                idx_guia = headers.index(next(h for h in headers if "GUIA" in h or "GUÍA" in h))
                idx_paq = headers.index(next(h for h in headers if "PAQUETERIA" in h or "PAQUETERÍA" in h))
                idx_estatus = headers.index(next(h for h in headers if "ESTATUS" in h and "ENV" not in h and "PAGO" not in h))
                idx_estatus_envio = headers.index(next(h for h in headers if "ESTATUS ENV" in h or "RASTREO" in h))
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
                valor_fecha_actual = str(fila[idx_fecha_recibido]).strip() if (idx_fecha_recibido is not None and len(fila) > idx_fecha_recibido) else ""
                
                # Detecta si la fecha está vacía o si tiene el error anterior ("Horas", "/09", "/10", "/12")
                fecha_invalida = (not valor_fecha_actual) or ("HORAS" in valor_fecha_actual.upper()) or any(valor_fecha_actual.endswith(x) for x in ["/09", "/10", "/12"])
                
                requiere_rastreo = (fila_estatus == "EN TRANSITO") or (fila_estatus == "ENTREGADO" and fecha_invalida)
                
                if requiere_rastreo and fila_paqueteria == "PAQUETEXPRESS" and fila_guia:
                    if fila_guia in cache_guias:
                        nuevo_estatus_envio, fecha_recibido_extraida = cache_guias[fila_guia]
                    else:
                        nuevo_estatus_envio, fecha_recibido_extraida = rastrear_paquetexpress(fila_guia, page)
                        cache_guias[fila_guia] = (nuevo_estatus_envio, fecha_recibido_extraida)
                        time.sleep(1.5)
                        
                    print(f"  ✅ Fila {i+2} | Guía {fila_guia} ➔ {nuevo_estatus_envio} | Fecha Entrega: {fecha_recibido_extraida}")
                    
                    if nuevo_estatus_envio != "Pendiente de actualización":
                        celdas_a_actualizar.append(gspread.Cell(row=i+2, col=idx_estatus_envio+1, value=nuevo_estatus_envio))
                        
                        if "ENTREGADO" in nuevo_estatus_envio.upper() and fila_estatus == "EN TRANSITO":
                            celdas_a_actualizar.append(gspread.Cell(row=i+2, col=idx_estatus+1, value="ENTREGADO"))
                        
                        if idx_fecha_recibido is not None and fecha_recibido_extraida and fecha_invalida:
                            celdas_a_actualizar.append(gspread.Cell(row=i+2, col=idx_fecha_recibido+1, value=fecha_recibido_extraida))

            if celdas_a_actualizar:
                print(f"\nSubiendo {len(celdas_a_actualizar)} actualizaciones a {ws.title}...")
                ws.update_cells(celdas_a_actualizar, value_input_option='USER_ENTERED')
            else:
                print(f"  -> No hubo guías pendientes por actualizar en {ws.title}.")

        browser.close()
    print("\n🎉 ¡Sincronización de rastreo, fechas y firmas finalizada con éxito!")

if __name__ == "__main__":
    ejecutar_laboratorio()
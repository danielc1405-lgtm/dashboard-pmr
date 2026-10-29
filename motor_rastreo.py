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
    # Mantenemos esta frase para que el contador del Cuartel General cuente las guías únicas
    print(f"🔍 Buscando guía: {guia}...")
    try:
        page.goto(f"https://www.paquetexpress.com.mx/rastreo/{guia}", timeout=25000, wait_until="domcontentloaded")
        page.wait_for_selector(".TrackingStatusActive", timeout=15000)
        
        textos_activos = page.locator(".TrackingStatusActive span").all_inner_texts()
        estatus_actual = textos_activos[-1].strip() if textos_activos else "Estatus no encontrado"

        fecha_entrega_formateada = ""
        estatus_final_api = estatus_actual

        if "ENTREGADO" in estatus_actual.upper() or "DELIVERED" in estatus_actual.upper():
            try:
                items_historial = page.locator("ul li").all_inner_texts()
                for item in items_historial:
                    if "recibió" in item.lower() or "entregada" in item.lower():
                        match_recibe = re.search(r"recibi[oó]\s+([^\n\r]+)", item, re.IGNORECASE)
                        if match_recibe:
                            persona = match_recibe.group(1).strip()
                            estatus_final_api = f"Entregado ({persona})"
                        else:
                            estatus_final_api = "Entregado"
                        
                        fecha_entrega_formateada = convertir_a_formato_mx(item)
                        break
            except Exception:
                pass

        return estatus_final_api, fecha_entrega_formateada

    except Exception:
        # Sin imprimir el Call log gigante de Playwright
        return "Pendiente de actualización", ""

# ==========================================
# 3. LÓGICA PRINCIPAL
# ==========================================
def ejecutar_laboratorio():
    print("==================================================")
    print("   RADAR PAQUETEXPRESS -> BASE MAESTRA EN VIVO    ")
    print("==================================================")
    doc = conectar_sheets()
    hojas_a_procesar = [doc.worksheet("BD_UNIFICADA")]

    agente_humano = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        context = browser.new_context(user_agent=agente_humano, viewport={"width": 1366, "height": 768}, locale="es-MX")
        page = context.new_page()
        cache_guias = {}
        
        for ws in hojas_a_procesar:
            print(f"\nEscaneando hoja: {ws.title}...")
            datos = ws.get_all_values()
            if not datos: continue
            
            headers = [str(h).strip().upper() for h in datos[0]]
            
            try:
                # Buscamos columnas de manera estricta y segura
                idx_guia = next(i for i, h in enumerate(headers) if h in ["GUIA", "GUÍA", "NO. GUIA", "PAQUETERIA GUIA"])
                idx_guia_dev = next((i for i, h in enumerate(headers) if h in ["GUIA DEVOLUCION", "GUÍA DEVOLUCIÓN", "GUIA RETORNO", "GUÍA RETORNO"]), None)
                idx_paq = next(i for i, h in enumerate(headers) if "PAQUETER" in h and "GUIA" not in h)
                idx_estatus = next(i for i, h in enumerate(headers) if h in ["ESTATUS", "STATUS"])
                idx_estatus_envio = next(i for i, h in enumerate(headers) if h in ["ESTATUS ENVIO", "ESTATUS ENVÍO", "RASTREO"])
                idx_taller = next((i for i, h in enumerate(headers) if "TALLER" in h or "CDR" in h), None)
                idx_fecha_recibido = next((i for i, h in enumerate(headers) if "FECHA REC" in h or "FECHA ENT" in h), None)
            except StopIteration:
                print(f"  [!] Faltan columnas clave en {ws.title}, saltando...")
                continue

            filas_pendientes = []
            for i, fila in enumerate(datos[1:]):
                # Asegurar que la fila tenga suficientes datos
                fila_estatus = str(fila[idx_estatus]).strip().upper() if len(fila) > idx_estatus else ""
                fila_paqueteria = str(fila[idx_paq]).strip().upper() if len(fila) > idx_paq else ""
                
                guia_normal = str(fila[idx_guia]).strip() if len(fila) > idx_guia else ""
                guia_devolucion = str(fila[idx_guia_dev]).strip() if (idx_guia_dev is not None and len(fila) > idx_guia_dev) else ""
                
                valor_fecha_actual = str(fila[idx_fecha_recibido]).strip() if (idx_fecha_recibido is not None and len(fila) > idx_fecha_recibido) else ""
                fecha_invalida = (not valor_fecha_actual) or ("HORAS" in valor_fecha_actual.upper()) or any(valor_fecha_actual.endswith(x) for x in ["/09", "/10", "/12"])
                
                # --- LÓGICA DE DECISIÓN DE GUÍA ---
                guia_a_rastrear = ""
                es_devolucion = False
                requiere_rastreo = False
                
                # Limpiamos las guías detectadas para evitar vacíos o nulos cruzados
                guia_normal = guia_normal if guia_normal not in ["", "nan", "None", "NAN"] else ""
                guia_devolucion = guia_devolucion if guia_devolucion not in ["", "nan", "None", "NAN"] else ""
                
                # 1. Si es un retorno, tomamos EXCLUSIVAMENTE la guía de devolución
                if "RECOLECCI" in fila_estatus or "RETORNO" in fila_estatus:
                    if guia_devolucion:
                        guia_a_rastrear = guia_devolucion
                        es_devolucion = True
                        requiere_rastreo = True
                
                # 2. Si es envío normal de ida
                elif (fila_estatus in ["EN TRANSITO", "EN PROCESAMIENTO"]) or (fila_estatus == "ENTREGADO" and fecha_invalida):
                    if guia_normal:
                        guia_a_rastrear = guia_normal
                        es_devolucion = False
                        requiere_rastreo = True
                
                # Validación a prueba de espacios en el nombre de la paquetería
                paqueteria_limpia = fila_paqueteria.replace(" ", "")
                if requiere_rastreo and "PAQUETEXPRESS" in paqueteria_limpia and guia_a_rastrear:
                    taller_str = str(fila[idx_taller]).strip() if (idx_taller is not None and len(fila) > idx_taller) else "CDR"
                    filas_pendientes.append((i + 2, guia_a_rastrear, fila_estatus, fecha_invalida, taller_str, es_devolucion))

            total_f = len(filas_pendientes)
            print(f"-> Se detectaron {total_f} partida(s) activas con guía Paquetexpress.\n")

            celdas_a_actualizar = []
            
            for idx_item, (num_fila, fila_guia, fila_estatus, fecha_invalida, taller_str, es_devolucion) in enumerate(filas_pendientes, start=1):
                if fila_guia in cache_guias:
                    nuevo_estatus_envio, fecha_recibido_extraida = cache_guias[fila_guia]
                else:
                    nuevo_estatus_envio, fecha_recibido_extraida = rastrear_paquetexpress(fila_guia, page)
                    cache_guias[fila_guia] = (nuevo_estatus_envio, fecha_recibido_extraida)
                    time.sleep(1.2)
                
                if nuevo_estatus_envio == "Pendiente de actualización":
                    print(f"  ⏳ [{idx_item:02d}/{total_f:02d}] Fila {num_fila:<4} | {taller_str} | Guía {fila_guia} ➔ Sin avance (En sitio)")
                else:
                    icono = "📦" if "ENTREGADO" in nuevo_estatus_envio.upper() else "🚚"
                    tipo_viaje = "(Retorno)" if es_devolucion else "(Ida)"
                    txt_fecha = f" | Fecha: {fecha_recibido_extraida}" if fecha_recibido_extraida else ""
                    print(f"  {icono} [{idx_item:02d}/{total_f:02d}] Fila {num_fila:<4} | {taller_str} | Guía {tipo_viaje} {fila_guia} ➔ {nuevo_estatus_envio}{txt_fecha}")
                    
                    # Actualiza la columna de "Rastreo API"
                    celdas_a_actualizar.append(gspread.Cell(row=num_fila, col=idx_estatus_envio+1, value=nuevo_estatus_envio))
                    
                    # --- LÓGICA DE ESTATUS FINAL ---
                    if "ENTREGADO" in nuevo_estatus_envio.upper():
                        if es_devolucion:
                            # Si era una recolección y ya se entregó, se marca como devuelto a la base
                            celdas_a_actualizar.append(gspread.Cell(row=num_fila, col=idx_estatus+1, value="RECIBIDO EN BASE"))
                        elif fila_estatus in ["EN TRANSITO", "EN PROCESAMIENTO"]:
                            # Si era un envío de ida y ya se entregó al taller
                            celdas_a_actualizar.append(gspread.Cell(row=num_fila, col=idx_estatus+1, value="ENTREGADO"))
                    
                    if idx_fecha_recibido is not None and fecha_recibido_extraida and fecha_invalida:
                        celdas_a_actualizar.append(gspread.Cell(row=num_fila, col=idx_fecha_recibido+1, value=fecha_recibido_extraida))

            if celdas_a_actualizar:
                print(f"\n☁️ Sincronizando {len(celdas_a_actualizar)} cambio(s) en {ws.title}...")
                ws.update_cells(celdas_a_actualizar, value_input_option='USER_ENTERED')
            else:
                print(f"\n-> Sin cambios nuevos que reportar en {ws.title}.")

        browser.close()
    print("\n🎉 ¡Rastreo de guías, fechas y firmas finalizado con éxito!")

if __name__ == "__main__":
    ejecutar_laboratorio()
import time
import re
import datetime
from playwright.sync_api import sync_playwright
import gspread
from google.oauth2.service_account import Credentials

SHEET_ID = "10jrOsS054n0atMk8GxQilkXqm6LjsnrwPOZnSx8iDek"

def formato_fecha_mex(fecha_obj):
    if not fecha_obj: return ""
    dt_obj = None
    if isinstance(fecha_obj, datetime.datetime): dt_obj = fecha_obj
    else:
        fecha_str = str(fecha_obj).strip()
        for fmt in ("%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y", "%d-%m-%y", "%Y-%m-%d"):
            try: 
                dt_obj = datetime.datetime.strptime(fecha_str, fmt)
                break
            except ValueError: continue
    if dt_obj:
        meses = {1:'ene', 2:'feb', 3:'mar', 4:'abr', 5:'may', 6:'jun', 7:'jul', 8:'ago', 9:'sep', 10:'oct', 11:'nov', 12:'dic'}
        return f"{dt_obj.day:02d}/{meses[dt_obj.month]}/{dt_obj.strftime('%y')}"
    return str(fecha_obj)

def limpiar_y_dividir_descripcion(desc):
    desc_limpia = re.sub(r'\(([^)]+)\)', lambda m: m.group(0).replace('/', ' '), desc)
    partes = [p.strip() for p in desc_limpia.split('/')]
    marca = partes[0] if len(partes) > 0 else ""
    modelo = partes[1] if len(partes) > 1 else ""
    version = partes[2] if len(partes) > 2 else ""
    return marca, modelo, version

def convertir_a_fecha_excel(fecha_raw):
    if not fecha_raw: return None
    f_str = str(fecha_raw).strip()
    match_num = re.search(r"(\d{1,2})[\s\-/](\d{1,2})[\s\-/](\d{2,4})", f_str)
    if match_num:
        try:
            dia, mes, anio = int(match_num.group(1)), int(match_num.group(2)), int(match_num.group(3))
            if anio < 100: anio += 2000
            return datetime.datetime(anio, mes, dia)
        except: pass
    meses_map = {'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6, 'jul': 7, 'ago': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dic': 12}
    match = re.search(r"(\d{1,2})[\s\-/]?([a-zA-ZáéíóúÁÉÍÓÚ]{3,4})[\s\-/]?(\d{2,4})", f_str)
    if match:
        try:
            dia, mes_str, anio = int(match.group(1)), match.group(2)[:3].lower(), int(match.group(3))
            mes = meses_map.get(mes_str, 8)
            if anio < 100: anio += 2000
            return datetime.datetime(anio, mes, dia)
        except: pass
    return f_str

def obtener_rango_fechas():
    hoy = datetime.datetime.now()
    print("\n--- CONFIGURACIÓN DE BÚSQUEDA (FECHAS) ---")
    print("  [1] Mes actual (Del día 1 al día de hoy)")
    print("  [2] Rango personalizado (Manual)")
    
    opcion = input("Elige una opción (1 o 2) [Por defecto 1]: ").strip()
    if opcion == '2':
        f_inicio_raw = input("Ingresa la fecha de inicio (Ej. 01/08/2026): ").strip()
        f_fin_raw = input("Ingresa la fecha de fin (Ej. 23/08/2026): ").strip()
        inicio = datetime.datetime.strptime(f_inicio_raw, "%d/%m/%Y").strftime("%d/%m/%Y") if f_inicio_raw else hoy.strftime("%d/%m/%Y")
        fin = datetime.datetime.strptime(f_fin_raw, "%d/%m/%Y").strftime("%d/%m/%Y") if f_fin_raw else hoy.strftime("%d/%m/%Y")
        return inicio, fin
    else: return datetime.datetime(hoy.year, hoy.month, 1).strftime("%d/%m/%Y"), hoy.strftime("%d/%m/%Y")

def obtener_mapa_columnas_lista(encabezados):
    mapa = {}
    for i, val in enumerate(encabezados):
        txt = str(val).strip().upper()
        if not txt: continue
        if txt == "ASEGURADORA": mapa['Aseguradora'] = i
        elif txt == "PEDIDO / SINIESTRO": mapa['ID_Principal'] = i
        elif txt == "SINIESTRO RELACIONADO": mapa['Siniestro_Relacionado'] = i
        elif txt == "TALLER": mapa['Taller'] = i
        elif txt == "MARCA": mapa['Marca'] = i
        elif txt in ["MODELO / VEHÍCULO", "MODELO / VEHICULO"]: mapa['Modelo'] = i
        elif txt in ["AÑO", "ANO"]: mapa['Año'] = i
        elif txt == "VIN / SERIE": mapa['VIN'] = i
        elif txt == "ORIGEN": mapa['Origen'] = i
        elif txt == "CANTIDAD": mapa['Cantidad'] = i
        elif txt in ["DESCRIPCIÓN", "DESCRIPCION"]: mapa['Descripcion'] = i
        elif txt == "PRECIO": mapa['Precio'] = i
        elif txt in ["FECHA ASIGNACIÓN", "FECHA ASIGNACION"]: mapa['Fecha_Asignacion'] = i
        elif txt == "FECHA VENCIMIENTO": mapa['Fecha_Vencimiento'] = i
        elif txt == "ESTATUS": mapa['Estatus'] = i
    return mapa

def automatizar_inpart():
    import sys
    print("==================================================")
    print("   EXTRACTOR INPART (GNP) -> NUBE (G. SHEETS)     ")
    print("==================================================")
    
    print("Conectando a Google Sheets para leer historial...")
    try:
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        credenciales = Credentials.from_service_account_file('credentials.json', scopes=scopes)
        cliente = gspread.authorize(credenciales)
        doc = cliente.open_by_key(SHEET_ID)
        
        ws_uni = doc.worksheet("BD_UNIFICADA")
        try: ws_hist = doc.worksheet("BD_HISTORICO")
        except: ws_hist = None

        datos_uni = ws_uni.get_all_values()
        datos_hist = ws_hist.get_all_values() if ws_hist else []

        encabezados_uni = datos_uni[0] if datos_uni else []
        mapa_uni = obtener_mapa_columnas_lista(encabezados_uni)
        encabezados_hist = datos_hist[0] if datos_hist else []
        mapa_hist = obtener_mapa_columnas_lista(encabezados_hist)

        existentes = {} 
        pedidos_existentes_set = set() 

        def registrar_existentes(datos_hoja, nombre_hoja, mapa_c):
            c_id = mapa_c.get('ID_Principal')
            c_desc = mapa_c.get('Descripcion')
            c_aseg = mapa_c.get('Aseguradora')
            if c_id is None or c_desc is None: return
            for i, row in enumerate(datos_hoja):
                if i == 0: continue
                if len(row) > c_id and len(row) > c_desc:
                    aseg = str(row[c_aseg]).upper() if c_aseg is not None and len(row) > c_aseg else ""
                    if aseg == "GNP":
                        pedido_id = str(row[c_id]).strip()
                        if pedido_id: pedidos_existentes_set.add(pedido_id)
                        llave = f"{pedido_id}_{str(row[c_desc]).strip()}"
                        if llave not in existentes:
                            existentes[llave] = (nombre_hoja, i + 1, row, mapa_c)

        registrar_existentes(datos_uni, 'UNI', mapa_uni)
        registrar_existentes(datos_hist, 'HIST', mapa_hist)

    except Exception as e:
        print(f"\n❌ Error al conectar a Google Sheets: {e}")
        return

    # MODO DE EJECUCIÓN (Por consola o desde Streamlit)
    if "--visual" in sys.argv:
        modo_oculto = False
        fecha_inicio, fecha_fin = obtener_rango_fechas() if not ("--visual" in sys.argv or "--oculto" in sys.argv) else (datetime.datetime(datetime.datetime.now().year, datetime.datetime.now().month, 1).strftime("%d/%m/%Y"), datetime.datetime.now().strftime("%d/%m/%Y"))
    elif "--oculto" in sys.argv:
        modo_oculto = True
        hoy = datetime.datetime.now()
        fecha_inicio, fecha_fin = datetime.datetime(hoy.year, hoy.month, 1).strftime("%d/%m/%Y"), hoy.strftime("%d/%m/%Y")
    else:
        fecha_inicio, fecha_fin = obtener_rango_fechas()
        print("¿Deseas ver el proceso de extracción en la ventana de Chrome? (s/n)")
        respuesta = input("-> ").strip().lower()
        modo_oculto = False if respuesta == 's' else True

    todos_los_pedidos_web = []
    agente_falso = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=modo_oculto, args=["--disable-blink-features=AutomationControlled"])
        context = browser.new_context(viewport={"width": 1920, "height": 1080}, user_agent=agente_falso, locale="es-MX", timezone_id="America/Monterrey")
        page = context.new_page()

        print("\nAbriendo portal Inpart...")
        page.goto("https://inpart.audatex.com.mx/AudaPartsSite/")
        page.wait_for_load_state("networkidle")
        print("Iniciando sesión...")
        page.fill("input[type='text'], input#username", "MX290679_1")
        try: page.click("input[type='checkbox']", timeout=2000)
        except: pass
        page.fill("input[type='password']", "inpart*79")
        page.keyboard.press("Enter")
        page.wait_for_load_state("networkidle")
        time.sleep(4)
        try: 
            if page.locator("#ctl00_cphBody_ucLogin_ucNeoMessageRemoveConcurrentLogin_btnYes").is_visible():
                page.click("#ctl00_cphBody_ucLogin_ucNeoMessageRemoveConcurrentLogin_btnYes")
                time.sleep(3)
        except: pass

        print("\n[Fase 1] Escaneando tabla general de pedidos por IDs estáticos...")
        try:
            page.wait_for_selector("text=PEDIDO", timeout=10000)
            page.locator("text=PEDIDO").first.hover(timeout=5000)
            time.sleep(1)
            page.locator("a[href*='frmOrderSupplierSearch']").first.click(timeout=5000)
        except:
            page.evaluate("window.location.href = 'frmOrderSupplierSearch.aspx'")
            
        page.wait_for_load_state("networkidle")
        time.sleep(4)

        try:
            page.wait_for_selector("input#cphBody_txtStartDate", timeout=10000)
            page.fill("input#cphBody_txtStartDate", ""); page.type("input#cphBody_txtStartDate", fecha_inicio)
            page.fill("input#cphBody_txtEndDate", ""); page.type("input#cphBody_txtEndDate", fecha_fin)
            page.click("input#cphBody_btnSearch")
            page.wait_for_load_state("networkidle")
            time.sleep(3)
        except Exception as ex: 
            print(f"Error técnico al buscar fechas: {ex}")
            return

        while True:
            try: page.wait_for_selector("table#cphBody_gdvResult", timeout=10000)
            except: break
            time.sleep(2)
            cantidad_filas = page.locator("table#cphBody_gdvResult tr").count()
            for i in range(1, int(cantidad_filas)):
                try:
                    fila = page.locator("table#cphBody_gdvResult tr").nth(i)
                    pedido_elem = fila.locator("span[id*='lblOrder_']")
                    taller_elem = fila.locator("span[id*='lblCompanyType_BodyShop_']")
                    fprev_elem = fila.locator("span[id*='lblScheduledDelivery_']")
                    fasig_elem = fila.locator("span[id*='lblDateTimeOrder_']")
                    estatus_elem = fila.locator("span[id*='lblStatus_']")

                    if pedido_elem.count() > 0:
                        pedido_txt = pedido_elem.first.inner_text().strip()
                        if not pedido_txt: continue
                        todos_los_pedidos_web.append({
                            'pedido': pedido_txt,
                            'taller': taller_elem.first.inner_text().strip() if taller_elem.count() > 0 else "",
                            'fecha_prevision': fprev_elem.first.inner_text().strip() if fprev_elem.count() > 0 else "",
                            'fecha_asignacion': fasig_elem.first.inner_text().strip() if fasig_elem.count() > 0 else "",
                            'estatus': estatus_elem.first.inner_text().strip() if estatus_elem.count() > 0 else ""
                        })
                except: pass

            btn_siguiente = page.locator("#cphBody_ucNeoPager_ibtNext")
            if btn_siguiente.count() > 0 and btn_siguiente.is_visible():
                if "disabled" in (btn_siguiente.get_attribute("class") or ""): break
                btn_siguiente.click()
                time.sleep(3)
            else: break
        browser.close()

    nuevos_pedidos_gnp = []
    for datos_dict in todos_los_pedidos_web:
        num_pedido = str(datos_dict['pedido']).strip()
        if num_pedido and num_pedido not in pedidos_existentes_set:
            nuevos_pedidos_gnp.append(datos_dict)
            pedidos_existentes_set.add(num_pedido)

    print(f"Total leídos en este periodo: {len(todos_los_pedidos_web)}")
    print(f"Pedidos NUEVOS detectados: {len(nuevos_pedidos_gnp)}")

    partidas_extraidas = []
    ya_procesados = set() 
    intentos_globales = 0

    if len(nuevos_pedidos_gnp) > 0:
        print("\n[Fase 2] Extrayendo detalle de partidas uno a uno...")
        while intentos_globales < 5:
            intentos_globales += 1
            hubo_timeout = False
            pendientes = [p for p in nuevos_pedidos_gnp if p['pedido'] not in ya_procesados]
            if not pendientes: break

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=modo_oculto, args=["--disable-blink-features=AutomationControlled"])
                context = browser.new_context(viewport={"width": 1920, "height": 1080}, user_agent=agente_falso, locale="es-MX", timezone_id="America/Monterrey")
                page = context.new_page()

                try:
                    print(f"\n[Intento {intentos_globales}/5] Iniciando sesión para extraer detalles...")
                    page.goto("https://inpart.audatex.com.mx/AudaPartsSite/")
                    page.wait_for_load_state("networkidle")
                    page.fill("input[type='text'], input#username", "MX290679_1")
                    try: page.click("input[type='checkbox']", timeout=2000)
                    except: pass
                    page.fill("input[type='password']", "inpart*79")
                    page.keyboard.press("Enter")
                    page.wait_for_load_state("networkidle")
                    time.sleep(4)
                    
                    try: 
                        if page.locator("#ctl00_cphBody_ucLogin_ucNeoMessageRemoveConcurrentLogin_btnYes").is_visible():
                            page.click("#ctl00_cphBody_ucLogin_ucNeoMessageRemoveConcurrentLogin_btnYes")
                            time.sleep(3)
                    except: pass
                    
                    total_pendientes = len(pendientes)
                    for idx, pedido_data in enumerate(pendientes):
                        num_pedido = pedido_data['pedido']
                        taller = pedido_data['taller']
                        fecha_prevision = pedido_data['fecha_prevision']
                        fecha_asignacion = pedido_data['fecha_asignacion'].split(" ")[0] if pedido_data['fecha_asignacion'] else ""
                        
                        estatus_raw = str(pedido_data['estatus']).strip()
                        if "Aguardando" in estatus_raw: estatus_pedido = "POR CONFIRMAR"
                        elif "Procesamiento" in estatus_raw: estatus_pedido = "EN PROCESAMIENTO"
                        elif not estatus_raw: estatus_pedido = "POR CONFIRMAR" 
                        else: estatus_pedido = estatus_raw.upper()
                        
                        print(f"[{idx+1}/{total_pendientes}] | Siniestro {num_pedido} procesado.")
                        try:
                            try:
                                page.wait_for_selector("text=PEDIDO", timeout=10000)
                                page.locator("text=PEDIDO").first.hover(timeout=5000)
                                time.sleep(1)
                                page.locator("a[href*='frmOrderSupplierSearch']").first.click(timeout=5000)
                            except: page.evaluate("window.location.href = 'frmOrderSupplierSearch.aspx'")
                                
                            page.wait_for_load_state("networkidle")
                            time.sleep(2)
                            
                            try:
                                page.wait_for_selector("input#cphBody_txtStartDate", timeout=10000)
                                page.fill("input#cphBody_txtStartDate", ""); page.type("input#cphBody_txtStartDate", fecha_inicio)
                                page.fill("input#cphBody_txtEndDate", ""); page.type("input#cphBody_txtEndDate", fecha_fin)
                            except: raise Exception(f"No se cargó el buscador en Fase 2.")
                            
                            page.fill("input[id*='OrderNumber'], input[id*='txtOrder']", num_pedido)
                            page.click("input#cphBody_btnSearch")
                            page.wait_for_load_state("networkidle")
                            time.sleep(2)
                            
                            fila_pedido = page.locator(f"table#cphBody_gdvResult tr:has-text('{num_pedido}')")
                            if fila_pedido.count() > 0:
                                enlace = fila_pedido.first.locator("a")
                                if enlace.count() > 0: enlace.first.click()
                                else: fila_pedido.first.click()
                                time.sleep(3)
                                
                                try:
                                    page.click("text=Datos Siniestro e Entrega", timeout=3000)
                                    time.sleep(1)
                                except: pass
                                
                                desc_elem = page.locator("span[id*='lblVehicleDescription']")
                                desc_veh_texto = desc_elem.first.inner_text().strip() if desc_elem.count() > 0 else ""
                                if '/' in desc_veh_texto: marca_veh, modelo_veh, _ = limpiar_y_dividir_descripcion(desc_veh_texto)
                                else:
                                    partes = desc_veh_texto.split(' ', 1)
                                    marca_veh = partes[0] if len(partes) > 0 else desc_veh_texto
                                    modelo_veh = partes[1] if len(partes) > 1 else ""

                                vin_elem = page.locator("span[id*='lblVIN']")
                                vin_texto_raw = vin_elem.first.inner_text().strip() if vin_elem.count() > 0 else ""
                                if '/' in vin_texto_raw:
                                    vin_texto = vin_texto_raw.split('/')[0].strip()
                                    origen_texto = vin_texto_raw.split('/')[1].strip()
                                else:
                                    vin_texto = vin_texto_raw
                                    origen_texto = "Original"

                                anio_elem = page.locator("span[id*='lblYearModel']")
                                anio_texto = anio_elem.first.inner_text().strip() if anio_elem.count() > 0 else ""
                                
                                sin_elem = page.locator("span[id*='lblClaimNumber']")
                                siniestro_relacionado = sin_elem.first.inner_text().strip() if sin_elem.count() > 0 else ""

                                try:
                                    page.click("text=Items del Pedido", timeout=3000)
                                    time.sleep(1)
                                    page.wait_for_selector("table[id*='gdvItemSupplier']", timeout=5000)
                                    filas_items = page.locator("table[id*='gdvItemSupplier'] tr").all()
                                    
                                    for item_fila in filas_items:
                                        desc_elem_pieza = item_fila.locator("span[id*='lblPartDescription_']")
                                        precio_elem_pieza = item_fila.locator("span[id*='lblItemPrice_']")
                                        
                                        if desc_elem_pieza.count() > 0:
                                            desc_pieza = desc_elem_pieza.first.inner_text().strip()
                                            precio_pieza = precio_elem_pieza.first.inner_text().strip() if precio_elem_pieza.count() > 0 else "0"
                                            if not desc_pieza or desc_pieza == "0": continue
                                            
                                            partidas_extraidas.append({
                                                'pedido': num_pedido, 'siniestro_relacionado': siniestro_relacionado, 
                                                'taller': taller, 'marca': marca_veh, 'modelo': modelo_veh,
                                                'vin': vin_texto, 'anio': anio_texto, 'origen': origen_texto, 
                                                'descripcion': desc_pieza, 'cantidad': "1", 'precio': precio_pieza, 
                                                'vencimiento': fecha_prevision, 'fecha_asignacion': fecha_asignacion, 'estatus': estatus_pedido
                                            })
                                except Exception as e: print(f"    Error al extraer piezas del pedido {num_pedido}: {e}")
                            ya_procesados.add(num_pedido)
                        except Exception as e_siniestro:
                            if "Timeout" in str(e_siniestro) or "ERR_ABORTED" in str(e_siniestro):
                                print(f"  [!] 🚨 Atasco/Aborto en pedido {num_pedido}. Reiniciando navegador...")
                                hubo_timeout = True
                                break 
                            else:
                                ya_procesados.add(num_pedido)
                                continue
                except Exception as e_global:
                    if "Timeout" in str(e_global): hubo_timeout = True
                finally:
                    try: browser.close()
                    except: pass
            if not hubo_timeout: break 

    # --- FASE 3: INYECCIÓN Y REPORTE HOMOLOGADO (ESTILO MULTI) ---
    if len(partidas_extraidas) > 0:
        print("\n[3/3] Conectando a Google Sheets para inyección y validación...")
        try:
            filas_a_insertar = []
            celdas_a_actualizar_uni = []
            celdas_a_actualizar_hist = []
            cambios_precio = []
            alertas_precio_1 = []
            piezas_reactivadas = [] 
            reporte_whatsapp = {}
            hoy = datetime.datetime.now()

            for p in partidas_extraidas:
                llave = f"{p['pedido']}_{p['descripcion']}"
                
                precio_flotante = 0.0
                try: precio_flotante = float(str(p['precio']).replace('$', '').replace(',', '').strip())
                except: pass

                if precio_flotante == 1.0:
                    alertas_precio_1.append(f"⚠️ {p['pedido']} | {p['taller'][:20]:<20} | 1x {p['descripcion']}")

                if llave in existentes:
                    hoja_ext, fila_existente, row_datos, map_cols = existentes[llave]
                    c_estatus = map_cols.get('Estatus')
                    c_vin = map_cols.get('VIN')
                    c_modelo = map_cols.get('Modelo')
                    c_origen = map_cols.get('Origen')
                    c_precio = map_cols.get('Precio')

                    def agregar_celda(col_idx, valor):
                        celda = gspread.Cell(row=fila_existente, col=col_idx + 1, value=valor)
                        if hoja_ext == 'UNI': celdas_a_actualizar_uni.append(celda)
                        else: celdas_a_actualizar_hist.append(celda)
                    
                    if c_estatus is not None:
                        estatus_actual = str(row_datos[c_estatus]).strip().upper() if len(row_datos) > c_estatus else ""
                        if "CANCELADO" in estatus_actual or "REEMBOLSADO" in estatus_actual:
                            agregar_celda(c_estatus, "POR CONFIRMAR")
                            if len(row_datos) > c_estatus: row_datos[c_estatus] = "POR CONFIRMAR"
                            piezas_reactivadas.append(f"🔄 REACTIVADO: {p['pedido']:<10} | {p['taller'][:20]:<20} | 1x {p['descripcion']}")
                    
                    if c_vin is not None and p['vin'] and "..." not in p['vin']:
                        vin_actual = str(row_datos[c_vin]).strip() if len(row_datos) > c_vin else ""
                        if "..." in vin_actual or not vin_actual:
                            agregar_celda(c_vin, p['vin'])
                            if len(row_datos) > c_vin: row_datos[c_vin] = p['vin']
                    
                    precio_excel_raw = row_datos[c_precio] if c_precio is not None and len(row_datos) > c_precio else 0
                    try: precio_actual_excel = float(str(precio_excel_raw).replace('$', '').replace(',', '').strip())
                    except: precio_actual_excel = 0.0
                    
                    if precio_flotante != precio_actual_excel and precio_flotante > 0:
                        cambios_precio.append(f"⚠ {p['pedido']:<10} | {p['descripcion'][:25]:<25} | De ${precio_actual_excel:,.2f} a ${precio_flotante:,.2f}")
                        if c_precio is not None: agregar_celda(c_precio, precio_flotante)
                else:
                    nueva_fila = [""] * len(encabezados_uni) 
                    if 'Aseguradora' in mapa_uni: nueva_fila[mapa_uni['Aseguradora']] = 'GNP'
                    if 'ID_Principal' in mapa_uni: nueva_fila[mapa_uni['ID_Principal']] = p['pedido']
                    if 'Siniestro_Relacionado' in mapa_uni: nueva_fila[mapa_uni['Siniestro_Relacionado']] = p['siniestro_relacionado']
                    if 'Taller' in mapa_uni: nueva_fila[mapa_uni['Taller']] = p['taller']
                    if 'Marca' in mapa_uni: nueva_fila[mapa_uni['Marca']] = p['marca']
                    if 'Modelo' in mapa_uni: nueva_fila[mapa_uni['Modelo']] = p['modelo']
                    if 'Año' in mapa_uni: nueva_fila[mapa_uni['Año']] = p['anio']
                    if 'VIN' in mapa_uni: nueva_fila[mapa_uni['VIN']] = p['vin']
                    if 'Origen' in mapa_uni: nueva_fila[mapa_uni['Origen']] = p['origen']
                    if 'Descripcion' in mapa_uni: nueva_fila[mapa_uni['Descripcion']] = p['descripcion']
                    if 'Precio' in mapa_uni: nueva_fila[mapa_uni['Precio']] = precio_flotante
                    if 'Fecha_Asignacion' in mapa_uni: nueva_fila[mapa_uni['Fecha_Asignacion']] = formato_fecha_mex(p.get('fecha_asignacion') or hoy)
                    if 'Fecha_Vencimiento' in mapa_uni: nueva_fila[mapa_uni['Fecha_Vencimiento']] = formato_fecha_mex(p['vencimiento'])
                    if 'Estatus' in mapa_uni: nueva_fila[mapa_uni['Estatus']] = p['estatus']
                    
                    filas_a_insertar.append(nueva_fila)

                    sin_key = f"{p['pedido']} (Siniestro: {p['siniestro_relacionado']})" if p['siniestro_relacionado'] else p['pedido']
                    if sin_key not in reporte_whatsapp:
                        reporte_whatsapp[sin_key] = {'taller': str(p['taller']).upper() if p['taller'] else 'N/A', 'vehiculo': f"{p['marca']} {p['modelo']} {p['anio']}".upper().strip(), 'piezas': {}}
                    
                    desc_key = str(p['descripcion']).upper()
                    if desc_key in reporte_whatsapp[sin_key]['piezas']: reporte_whatsapp[sin_key]['piezas'][desc_key] += 1
                    else: reporte_whatsapp[sin_key]['piezas'][desc_key] = 1

            if celdas_a_actualizar_uni:
                ws_uni.update_cells(celdas_a_actualizar_uni, value_input_option='USER_ENTERED')
                print(f"✅ Se aplicaron {len(celdas_a_actualizar_uni)} auto-correcciones en BD_UNIFICADA.")
            if celdas_a_actualizar_hist:
                ws_hist.update_cells(celdas_a_actualizar_hist, value_input_option='USER_ENTERED')
                print(f"✅ Se aplicaron {len(celdas_a_actualizar_hist)} auto-correcciones en BD_HISTORICO.")
            if filas_a_insertar:
                ws_uni.append_rows(filas_a_insertar, value_input_option='USER_ENTERED', table_range="A1:B")
                print(f"✅ Se inyectaron {len(filas_a_insertar)} piezas NUEVAS a la nube.")
            else: print("✅ No hubo piezas nuevas para inyectar.")

            if reporte_whatsapp:
                print("\n" + "="*50)
                print(" 📱 REPORTES LISTOS PARA COPIAR A WHATSAPP ")
                print("="*50 + "\n")
                for sin, datos_wa in reporte_whatsapp.items():
                    mensaje = "🚨 *NUEVA ASIGNACIÓN* 🚨\n"
                    mensaje += f"🏢 *Taller:* {datos_wa['taller'].strip()}\n"
                    mensaje += f"📄 *Siniestro:* {sin.strip()}\n"
                    mensaje += f"🚗 *Vehículo:* {datos_wa['vehiculo'].strip()}\n\n"
                    mensaje += "*📦 Piezas:*\n"
                    for desc, cant in datos_wa['piezas'].items():
                        mensaje += f"🔹 {cant}x {desc.strip()}\n"
                
                    print(mensaje)
                    print(" " + "_"*40 + "\n")
                
            if piezas_reactivadas:
                print("\n🔄 PIEZAS REACTIVADAS (Estaban canceladas y regresaron al portal):")
                for r in sorted(set(piezas_reactivadas)): print(r)
            if cambios_precio:
                print("\n🟠 CAMBIOS DE PRECIO DETECTADOS Y ACTUALIZADOS:")
                for c in sorted(set(cambios_precio)): print(c)
            if alertas_precio_1:
                print("\n🟡 ALERTAS DE PRECIO $1.00 (Revisar posible error de cotización):")
                for a in sorted(set(alertas_precio_1)): print(a)
                
            print("\n" + "!"*80)
            print(" 🚨 REVISIÓN DE ESTATUS CRÍTICO EN BASE MAESTRA (HOY Y VENCIDOS) 🚨")
            print("!"*80)

            partidas_vencidas_db = []
            partidas_hoy_db = []
            def revisar_criticos(hoja_ws, mapa):
                c_venc = mapa.get('Fecha_Vencimiento')
                c_sin = mapa.get('ID_Principal')
                c_taller = mapa.get('Taller')
                c_est = mapa.get('Estatus')
                c_desc = mapa.get('Descripcion')
                if c_est is not None and c_venc is not None and c_sin is not None:
                    datos_act = hoja_ws.get_all_values()
                    for j, r in enumerate(datos_act):
                        if j == 0: continue
                        def g_val(row_array, index): return str(row_array[index]).strip() if index is not None and index < len(row_array) else ""
                        estatus = g_val(r, c_est).upper()
                        if estatus in ["POR CONFIRMAR", "EN PROCESAMIENTO", "EN TRANSITO"]:
                            fecha_venc_raw = g_val(r, c_venc)
                            fecha_venc_date = None
                            if fecha_venc_raw:
                                fecha_parsed = convertir_a_fecha_excel(fecha_venc_raw)
                                if isinstance(fecha_parsed, datetime.datetime): fecha_venc_date = fecha_parsed.date()
                            if fecha_venc_date:
                                dias_restantes = (fecha_venc_date - hoy.date()).days
                                if dias_restantes <= 0:
                                    sin_val = g_val(r, c_sin).replace('.0','')
                                    taller_val = g_val(r, c_taller)[:20] if g_val(r, c_taller) else 'N/A'
                                    desc_val = g_val(r, c_desc)
                                    if dias_restantes < 0: partidas_vencidas_db.append(f"❌ VENCIDO hace {abs(dias_restantes):02d} día(s): {sin_val:<10} | {taller_val:<20} | 1x {desc_val} ({estatus})")
                                    elif dias_restantes == 0: partidas_hoy_db.append(f"⚠️ VENCE HOY: {sin_val:<10} | {taller_val:<20} | 1x {desc_val} ({estatus})")

            revisar_criticos(ws_uni, mapa_uni)
            if ws_hist: revisar_criticos(ws_hist, mapa_hist)

            if partidas_vencidas_db:
                print("\n🔴 PARTIDAS VENCIDAS (Riesgo de reasignación o cancelación):")
                for v in sorted(set(partidas_vencidas_db), key=lambda x: x.split(': ')[1] if ': ' in x else x): print(v)
                print("-" * 80)
            else: print("\n🔴 PARTIDAS VENCIDAS:\n  ✅ No hay partidas vencidas de días anteriores.")
                
            if partidas_hoy_db:
                print("\n⚠️ PARTIDAS POR VENCER (El día de hoy):")
                for h in sorted(set(partidas_hoy_db), key=lambda x: x.split(': ')[1] if ': ' in x else x): print(h)
                print("-" * 80)

        except Exception as e: print(f"\n❌ Error al guardar en Base Maestra: {e}")
    else: print("\nNo se encontraron registros NUEVOS para agregar.")

if __name__ == "__main__": automatizar_inpart()
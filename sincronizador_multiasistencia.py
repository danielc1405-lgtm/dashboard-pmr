import os
import re
import time
import datetime
import sys
from playwright.sync_api import sync_playwright
import gspread
from google.oauth2.service_account import Credentials

# --- CREDENCIALES Y PORTAL ---
SHEET_ID = "10jrOsS054n0atMk8GxQilkXqm6LjsnrwPOZnSx8iDek"
PORTAL_URL = "https://siniestros.bbva.mx/refaccionarias/"
USUARIO_PORTAL = "PMA5816"
PASSWORD_PORTAL = "Pmroct1."

meses_map = {'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6, 'jul': 7, 'ago': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dic': 12}

def formato_fecha_mex(fecha_obj):
    if not fecha_obj: return ""
    dt_obj = None
    if isinstance(fecha_obj, datetime.datetime):
        dt_obj = fecha_obj
    else:
        fecha_str = str(fecha_obj).strip()
        for fmt in ("%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y", "%d-%m-%y", "%Y-%m-%d"):
            try: 
                dt_obj = datetime.datetime.strptime(fecha_str, fmt)
                break
            except ValueError: 
                continue
    if dt_obj:
        meses = {1:'ene', 2:'feb', 3:'mar', 4:'abr', 5:'may', 6:'jun', 7:'jul', 8:'ago', 9:'sep', 10:'oct', 11:'nov', 12:'dic'}
        return f"{dt_obj.day:02d}/{meses[dt_obj.month]}/{dt_obj.strftime('%y')}"
    return str(fecha_obj)

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

    match = re.search(r"(\d{1,2})[\s\-/]?([a-zA-ZáéíóúÁÉÍÓÚ]{3,4})[\s\-/]?(\d{2,4})", f_str)
    if match:
        try:
            dia, mes_str, anio = int(match.group(1)), match.group(2)[:3].lower(), int(match.group(3))
            mes = meses_map.get(mes_str, 8)
            if anio < 100: anio += 2000
            return datetime.datetime(anio, mes, dia)
        except: pass

    return f_str

def obtener_frame_derecho(page):
    frame = page.frame(name="middleFrameRight")
    if not frame: frame = page.frame_locator("iframe[name='middleFrameRight']")
    return frame

def limpiar_precio(precio_raw):
    if not precio_raw: return ""
    p = str(precio_raw).replace(" ", "").replace("\xa0", "").strip()
    if not p.startswith("$") and p != "": p = "$" + p
    return p

def obtener_mapa_columnas_lista(encabezados):
    mapa = {}
    for i, val in enumerate(encabezados):
        txt = str(val).strip().upper()
        if not txt: continue
        
        if txt == "ASEGURADORA": mapa['Aseguradora'] = i
        elif txt == "PEDIDO / SINIESTRO": mapa['ID_Principal'] = i
        elif txt == "TALLER": mapa['Taller'] = i
        elif txt == "MARCA": mapa['Marca'] = i
        elif txt in ["MODELO / VEHÍCULO", "MODELO / VEHICULO"]: mapa['Modelo'] = i
        elif txt == "AÑO": mapa['Año'] = i
        elif txt == "VIN / SERIE": mapa['VIN'] = i
        elif txt == "ORIGEN": mapa['Origen'] = i
        elif txt == "CANTIDAD": mapa['Cantidad'] = i
        elif txt in ["DESCRIPCIÓN", "DESCRIPCION"]: mapa['Descripcion'] = i
        elif txt == "PRECIO": mapa['Precio'] = i
        elif txt in ["FECHA ASIGNACIÓN", "FECHA ASIGNACION"]: mapa['Fecha_Asignacion'] = i
        elif txt == "FECHA VENCIMIENTO": mapa['Fecha_Vencimiento'] = i
        elif txt == "ESTATUS": mapa['Estatus'] = i
            
    return mapa

def extraer_datos_multi():
    if "--visual" in sys.argv:
        modo_headless = False
    elif "--oculto" in sys.argv:
        modo_headless = True
    else:
        print("¿Deseas ver el proceso de extracción en Chrome? (s/n)")
        respuesta = input("-> ").strip().lower()
        modo_headless = False if respuesta == 's' else True

    print("==================================================")
    print(" AUTOMATIZACIÓN MULTIASISTENCIA -> NUBE (G. SHEETS) ")
    print("==================================================")

    partidas_extraidas = []
    ya_procesados = set() 
    intentos_globales = 0

    while intentos_globales < 5:
        intentos_globales += 1
        hubo_timeout = False

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=modo_headless)
            context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            page = context.new_page()
            page.on("dialog", lambda dialog: dialog.accept())

            try:
                print(f"\n[Intento {intentos_globales}/5] Accediendo al portal de Multiasistencia...")
                page.goto(PORTAL_URL, timeout=60000)
                page.wait_for_load_state("domcontentloaded")

                page.fill("input[type='text']", USUARIO_PORTAL)
                page.fill("input[type='password']", PASSWORD_PORTAL)
                page.click("input[value='Aceptar'], button:has-text('Aceptar')")
                time.sleep(2.5)

                print("-> Entrando a 'Piezas Pendientes de Entregar al Taller'...")
                page.click("text=Piezas Pendientes de Entregar al Taller", timeout=25000)
                time.sleep(3)

                frame_derecho = obtener_frame_derecho(page)
                enlaces = frame_derecho.locator("a").all_inner_texts()
                lista_siniestros = []
                
                for txt in enlaces:
                    t = txt.strip()
                    if re.match(r"^[A-Z0-9\-]{6,20}$", t.upper()) and not t.isalpha():
                        if t not in lista_siniestros: lista_siniestros.append(t)
                            
                if not lista_siniestros:
                    print("      [!] No se encontraron siniestros en la lista.")
                    browser.close()
                    return []

                siniestros_pendientes = [s for s in lista_siniestros if s not in ya_procesados]
                
                if not siniestros_pendientes:
                    print("✅ Todos los siniestros han sido procesados exitosamente.")
                    break

                total_s = len(siniestros_pendientes)
                print(f"-> Quedan {total_s} siniestros por procesar en esta ronda.")

                for idx, num_siniestro in enumerate(siniestros_pendientes):
                    try:
                        time.sleep(1)
                        frame_derecho = obtener_frame_derecho(page)
                        
                        if not frame_derecho.locator(f"a:has-text('{num_siniestro}')").is_visible(timeout=5000):
                            page.click("text=Piezas Pendientes de Entregar al Taller", timeout=15000)
                            time.sleep(2.5)
                            frame_derecho = obtener_frame_derecho(page)

                        frame_derecho.click(f"a:has-text('{num_siniestro}')", timeout=15000)
                        
                        time.sleep(1)
                        frame_derecho = obtener_frame_derecho(page)
                        try:
                            frame_derecho.locator("td:has-text('Cantidad')").first.wait_for(timeout=10000)
                        except:
                            time.sleep(2)

                        datos_raw = frame_derecho.evaluate(r"""
                            () => {
                                function getFullText(el) { 
                                    if (!el) return '';
                                    let text = el.textContent.replace(/[\s\xA0]+/g, ' ').trim();
                                    
                                    let title = el.getAttribute('title');
                                    if (title && title.trim().length > text.length && !title.includes('...')) return title.trim();
                                    
                                    let onmouse = el.getAttribute('onmouseover');
                                    if (onmouse) {
                                        let m = onmouse.match(/['"]([^'"]+)['"]/);
                                        if (m && m[1].trim().length > text.length && !m[1].includes('...')) return m[1].trim();
                                    }
                                    return text;
                                }

                                let taller = '', modelo = '', vin = '', marca = '', ano = '', fecha_asig = '';
                                let celdasTD = Array.from(document.querySelectorAll('td'));
                                
                                for (let i = 0; i < celdasTD.length; i++) {
                                    let t = celdasTD[i].textContent.trim();
                                    if (t === "Nombre:" && celdasTD[i + 1]) taller = getFullText(celdasTD[i + 1]);
                                    if (t.includes("Veh") && t.includes("culo") && celdasTD[i + 1]) modelo = getFullText(celdasTD[i + 1]);
                                    if (t.includes("No. Serie") && celdasTD[i + 1]) vin = getFullText(celdasTD[i + 1]);
                                    if (t === "Marca:" && celdasTD[i + 1]) marca = getFullText(celdasTD[i + 1]).replace(/\./g, "").trim();
                                    if (t === "Modelo:" && celdasTD[i + 1] && !ano) {
                                        let c = getFullText(celdasTD[i + 1]);
                                        if (/^\d{4}$/.test(c)) ano = c;
                                    }
                                }
                                
                                let regexAsig = /Fecha Asignaci[oó]n\s*[:]?\s*([0-9]{1,2}[-\/][a-zA-Z0-9]{2,4}[-\/][0-9]{2,4})/i;
                                let matchTxt = document.body.innerText.match(regexAsig);
                                if(matchTxt) fecha_asig = matchTxt[1];

                                let partidas = [];
                                let trs = Array.from(document.querySelectorAll('tr'));
                                for (let tr of trs) {
                                    let tds = Array.from(tr.querySelectorAll('td'));
                                    if (tds.length >= 8) {
                                        let txt0 = tds[0].textContent.trim();
                                        if (txt0.length > 0 && !isNaN(txt0) && Number(txt0) > 0) {
                                            partidas.push({
                                                cantidad: txt0,
                                                descripcion: getFullText(tds[3]), 
                                                origen: tds[4] ? getFullText(tds[4]) : '',
                                                precio: tds[5] ? tds[5].textContent.trim() : '', 
                                                fecha_promesa: tds[8] ? tds[8].textContent.trim() : ''
                                            });
                                        }
                                    }
                                }
                                return { taller, marca, modelo, ano, vin, fecha_asig, partidas };
                            }
                        """)

                        partidas_siniestro = 0
                        for p_item in datos_raw.get('partidas', []):
                            desc_limpia = str(p_item['descripcion']).replace("...", "").strip()
                            if not desc_limpia or len(desc_limpia) < 3 or desc_limpia.upper() in ["CÓDIGO", "DESCRIPCION", "CANTIDAD"]: continue

                            partidas_extraidas.append({
                                'siniestro': num_siniestro, 'taller': datos_raw.get('taller', '').strip(),
                                'marca': datos_raw.get('marca', '').strip(), 'modelo': datos_raw.get('modelo', '').strip(),
                                'ano': datos_raw.get('ano', '').strip(), 'vin': datos_raw.get('vin', '').strip(),
                                'cantidad': str(p_item.get('cantidad', '1')).strip(),
                                'origen': p_item['origen'], 'descripcion': desc_limpia,
                                'precio': limpiar_precio(p_item['precio']),
                                'fecha_promesa': convertir_a_fecha_excel(p_item['fecha_promesa']),
                                'fecha_asignacion': convertir_a_fecha_excel(datos_raw.get('fecha_asig', ''))
                            })
                            partidas_siniestro += 1
                        
                        ya_procesados.add(num_siniestro) 
                        
                        if partidas_siniestro == 0:
                            print(f"[{idx+1}/{total_s}] | Siniestro {num_siniestro} procesado. ⚠️ [!] No devolvió partidas.")
                        else:
                            print(f"[{idx+1}/{total_s}] | Siniestro {num_siniestro} procesado.")

                        try:
                            btn_regresar = frame_derecho.locator("input[value='Regresar'], button:has-text('Regresar')")
                            if btn_regresar.count() > 0: 
                                btn_regresar.first.click(timeout=10000)
                                time.sleep(2) 
                            else: 
                                page.click("text=Piezas Pendientes de Entregar al Taller", timeout=10000)
                                time.sleep(2)
                        except:
                            page.goto(PORTAL_URL)
                            time.sleep(3)
                            page.click("text=Piezas Pendientes de Entregar al Taller")
                            time.sleep(3)

                    except Exception as e_siniestro:
                        if "Timeout" in str(e_siniestro):
                            print(f"  [!] 🚨 Atasco detectado (Timeout) en siniestro {num_siniestro}. Reiniciando navegador...")
                            hubo_timeout = True
                            break 
                        else:
                            print(f"  [!] Error en siniestro {num_siniestro}: {e_siniestro}")
                            ya_procesados.add(num_siniestro) 
                            continue

            except Exception as e_global: 
                print(f"[!] Error global: {e_global}")
                if "Timeout" in str(e_global): hubo_timeout = True
            finally:
                try: browser.close()
                except: pass
        
        if not hubo_timeout:
            break 

    return partidas_extraidas

def vaciar_a_base_maestra(partidas_web):
    if not partidas_web: return
    
    print("\n[3/3] Conectando a Google Sheets para inyección y validación...")
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

        def registrar_existentes(datos_hoja, nombre_hoja, mapa_c):
            c_id = mapa_c.get('ID_Principal')
            c_desc = mapa_c.get('Descripcion')
            c_aseg = mapa_c.get('Aseguradora')
            if c_id is None or c_desc is None: return
            for i, row in enumerate(datos_hoja):
                if i == 0: continue
                if len(row) > c_id and len(row) > c_desc:
                    aseg = str(row[c_aseg]).upper() if c_aseg is not None and len(row) > c_aseg else ""
                    if aseg == "MULTI":
                        llave = f"{str(row[c_id]).strip()}_{str(row[c_desc]).strip()}"
                        if llave not in existentes:
                            existentes[llave] = (nombre_hoja, i + 1, row, mapa_c)

        registrar_existentes(datos_uni, 'UNI', mapa_uni)
        registrar_existentes(datos_hist, 'HIST', mapa_hist)

        filas_a_insertar = []
        cambios_precio = []
        alertas_precio_1 = []
        piezas_reactivadas = [] 
        reporte_whatsapp = {}
        
        celdas_a_actualizar_uni = []
        celdas_a_actualizar_hist = []

        hoy = datetime.datetime.now()

        for p in partidas_web:
            llave = f"{p['siniestro']}_{p['descripcion']}"
            
            precio_flotante = 0.0
            try: precio_flotante = float(str(p['precio']).replace('$', '').replace(',', '').strip())
            except: pass

            if precio_flotante == 1.0:
                alertas_precio_1.append(f"⚠️ {p['siniestro']} | {p['taller'][:20]:<20} | 1x {p['descripcion']}")

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
                        piezas_reactivadas.append(f"🔄 REACTIVADO: {p['siniestro']:<10} | {p['taller'][:20]:<20} | 1x {p['descripcion']}")
                
                if c_vin is not None and p['vin'] and "..." not in p['vin']:
                    vin_actual = str(row_datos[c_vin]).strip() if len(row_datos) > c_vin else ""
                    if "..." in vin_actual or not vin_actual:
                        agregar_celda(c_vin, p['vin'])
                        if len(row_datos) > c_vin: row_datos[c_vin] = p['vin']

                if c_modelo is not None and p['modelo'] and "..." not in p['modelo']:
                    mod_actual = str(row_datos[c_modelo]).strip() if len(row_datos) > c_modelo else ""
                    if "..." in mod_actual or not mod_actual:
                        agregar_celda(c_modelo, p['modelo'])
                        if len(row_datos) > c_modelo: row_datos[c_modelo] = p['modelo']

                if c_origen is not None and p['origen'] and "..." not in p['origen']:
                    ori_actual = str(row_datos[c_origen]).strip() if len(row_datos) > c_origen else ""
                    if "..." in ori_actual or not ori_actual:
                        agregar_celda(c_origen, p['origen'])
                        if len(row_datos) > c_origen: row_datos[c_origen] = p['origen']

                precio_excel_raw = row_datos[c_precio] if c_precio is not None and len(row_datos) > c_precio else 0
                try: precio_actual_excel = float(str(precio_excel_raw).replace('$', '').replace(',', '').strip())
                except: precio_actual_excel = 0.0
                
                if precio_flotante != precio_actual_excel and precio_flotante > 0:
                    cambios_precio.append(f"⚠ {p['siniestro']:<10} | {p['descripcion'][:25]:<25} | De ${precio_actual_excel:,.2f} a ${precio_flotante:,.2f}")
                    if c_precio is not None:
                        agregar_celda(c_precio, precio_flotante)
            else:
                nueva_fila = [""] * len(encabezados_uni) 
                
                if 'Aseguradora' in mapa_uni: nueva_fila[mapa_uni['Aseguradora']] = 'MULTI'
                if 'ID_Principal' in mapa_uni: nueva_fila[mapa_uni['ID_Principal']] = p['siniestro']
                if 'Taller' in mapa_uni: nueva_fila[mapa_uni['Taller']] = p['taller']
                if 'Marca' in mapa_uni: nueva_fila[mapa_uni['Marca']] = p['marca']
                if 'Modelo' in mapa_uni: nueva_fila[mapa_uni['Modelo']] = p['modelo']
                if 'Año' in mapa_uni: nueva_fila[mapa_uni['Año']] = p['ano']
                if 'VIN' in mapa_uni: nueva_fila[mapa_uni['VIN']] = p['vin']
                if 'Origen' in mapa_uni: nueva_fila[mapa_uni['Origen']] = p['origen']
                if 'Cantidad' in mapa_uni: nueva_fila[mapa_uni['Cantidad']] = p.get('cantidad', '1')
                if 'Descripcion' in mapa_uni: nueva_fila[mapa_uni['Descripcion']] = p['descripcion']
                if 'Precio' in mapa_uni: nueva_fila[mapa_uni['Precio']] = precio_flotante
                if 'Fecha_Asignacion' in mapa_uni: nueva_fila[mapa_uni['Fecha_Asignacion']] = formato_fecha_mex(p.get('fecha_asignacion') or hoy)
                if 'Fecha_Vencimiento' in mapa_uni: nueva_fila[mapa_uni['Fecha_Vencimiento']] = formato_fecha_mex(p['fecha_promesa'])
                if 'Estatus' in mapa_uni: nueva_fila[mapa_uni['Estatus']] = 'POR CONFIRMAR'
                
                filas_a_insertar.append(nueva_fila)

                sin_key = p['siniestro']
                if sin_key not in reporte_whatsapp:
                    reporte_whatsapp[sin_key] = {'taller': str(p['taller']).upper() if p['taller'] else 'N/A', 'vehiculo': f"{p['marca']} {p['modelo']} {p['ano']}".upper().strip(), 'piezas': {}}
                
                desc_key = str(p['descripcion']).upper()
                if desc_key in reporte_whatsapp[sin_key]['piezas']: reporte_whatsapp[sin_key]['piezas'][desc_key] += int(p.get('cantidad', '1'))
                else: reporte_whatsapp[sin_key]['piezas'][desc_key] = int(p.get('cantidad', '1'))

        if celdas_a_actualizar_uni:
            ws_uni.update_cells(celdas_a_actualizar_uni, value_input_option='USER_ENTERED')
            print(f"✅ Se aplicaron {len(celdas_a_actualizar_uni)} auto-correcciones en BD_UNIFICADA.")
            
        if celdas_a_actualizar_hist:
            ws_hist.update_cells(celdas_a_actualizar_hist, value_input_option='USER_ENTERED')
            print(f"✅ Se aplicaron {len(celdas_a_actualizar_hist)} auto-correcciones en BD_HISTORICO.")

        if filas_a_insertar:
            ws_uni.append_rows(filas_a_insertar, value_input_option='USER_ENTERED', table_range="A1:B")
            print(f"✅ Se inyectaron {len(filas_a_insertar)} piezas NUEVAS a la nube.")
        else:
            print("✅ No hubo piezas nuevas para inyectar.")

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
                            if isinstance(fecha_parsed, datetime.datetime):
                                fecha_venc_date = fecha_parsed.date()
                        
                        if fecha_venc_date:
                            dias_restantes = (fecha_venc_date - hoy.date()).days
                            if dias_restantes <= 0:
                                sin_val = g_val(r, c_sin).replace('.0','')
                                taller_val = g_val(r, c_taller)[:20] if g_val(r, c_taller) else 'N/A'
                                desc_val = g_val(r, c_desc)
                                
                                if dias_restantes < 0:
                                    partidas_vencidas_db.append(f"❌ {abs(dias_restantes):02d} día(s): {sin_val:<10} | {taller_val:<20} | 1x {desc_val} ({estatus})")
                                elif dias_restantes == 0:
                                    partidas_hoy_db.append(f"⚠️ {sin_val:<10} | {taller_val:<20} | 1x {desc_val} ({estatus})")

        revisar_criticos(ws_uni, mapa_uni)
        if ws_hist: revisar_criticos(ws_hist, mapa_hist)

        if partidas_vencidas_db:
            print("\n🔴 PARTIDAS VENCIDAS (Riesgo de reasignación o cancelación):")
            for v in sorted(set(partidas_vencidas_db), key=lambda x: x.split(': ')[1] if ': ' in x else x): 
                print(v)
            print("-" * 80)
        else:
            print("\n🔴 PARTIDAS VENCIDAS:\n  ✅ No hay partidas vencidas de días anteriores.")
            
        if partidas_hoy_db:
            print("\n⚠️ PARTIDAS POR VENCER (El día de hoy):")
            for h in sorted(set(partidas_hoy_db), key=lambda x: x.split(': ')[1] if ': ' in x else x): 
                print(h)
            print("-" * 80)

    except Exception as e:
        print(f"\n❌ Error al conectar/procesar en Google Sheets: {e}")

if __name__ == "__main__":
    datos = extraer_datos_multi()
    vaciar_a_base_maestra(datos)
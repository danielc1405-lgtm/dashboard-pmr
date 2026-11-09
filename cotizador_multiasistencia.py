import os
import re
import sys
import time
import random
import datetime
import urllib.parse
import requests
from playwright.sync_api import sync_playwright
import gspread
from google.oauth2.service_account import Credentials

SHEET_ID = "10jrOsS054n0atMk8GxQilkXqm6LjsnrwPOZnSx8iDek"
PORTAL_URL = "https://siniestros.bbva.mx/refaccionarias/"

ENCABEZADOS_COT = [
    "ID_Cotizacion", "Fecha_Extraccion", "Siniestro", "Cotizacion_No",
    "Marca", "Vehiculo", "Modelo_Ano", "VIN", "Taller", "Ciudad", "Estado", "Fecha_Fin",
    "Partida_Idx", "Cantidad", "Descripcion_Portal", "Busqueda_Sugerida",
    "Precio_Original", "Precio_No_Original", "Precio_Generica", "Precio_Historial",
    "Flete_Estimado", "Fuente_Seleccionada", "Origen_Portal", "Costo_Base",
    "Margen_Pct", "Precio_Sugerido", "Precio_Libre", "Precio_Final_Enviar",
    "Codigo_Hub", "Link_ML", "Link_eBay", "Validar_Envio", "Estatus_Cotizacion"
]

DICCIONARIO_BASE = {
    "FACIA": "FASCIA", "DEL.": "DELANTERA", "DEL": "DELANTERA",
    "TRA.": "TRASERA", "TRA": "TRASERA", "TRAS.": "TRASERA", "TRAS": "TRASERA",
    "IZQ.": "IZQUIERDA", "IZQ": "IZQUIERDA", "DER.": "DERECHA", "DER": "DERECHA", "D.": "DERECHA",
    "SOP.": "SOPORTE", "SOP": "SOPORTE", "CEN.": "CENTRAL", "CEN": "CENTRAL",
    "SUP.": "SUPERIOR", "SUP": "SUPERIOR", "INF.": "INFERIOR", "INF": "INFERIOR",
    "EXT.": "EXTERIOR", "INT.": "INTERIOR", "PTA.": "PUERTA", "PTA": "PUERTA",
    "SALP.": "SALPICADERA", "SALP": "SALPICADERA", "MOLD.": "MOLDURA", "MOLD": "MOLDURA",
    "ANTIN.": "ANTINIEBLA", "ANITIN.": "ANTINIEBLA", "INTEG.": "INTEGRADO", "INTEG": "INTEGRADO"
}

def conectar_sheets():
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    credenciales = Credentials.from_service_account_file('credentials.json', scopes=scopes)
    cliente = gspread.authorize(credenciales)
    return cliente.open_by_key(SHEET_ID)

def cargar_configuracion_dinamica(doc):
    config = {
        "MULTI_USER": "PMA5816",
        "MULTI_PASS": "Pmroct1.",
        "TC_USD": 20.50,
        "DICCIONARIO_EXTRA": {}
    }
    try:
        ws_cfg = doc.worksheet("BD_CONFIG_BOTS")
        filas = ws_cfg.get_all_values()
        for f in filas[1:]:
            if len(f) >= 2:
                k, v = str(f[0]).strip().upper(), str(f[1]).strip()
                if k == "MULTI_USER" and v: config["MULTI_USER"] = v
                elif k == "MULTI_PASS" and v: config["MULTI_PASS"] = v
                elif k == "TC_USD" and v:
                    try: config["TC_USD"] = float(v)
                    except: pass
                elif k.startswith("ABREV_") and v:
                    config["DICCIONARIO_EXTRA"][k.replace("ABREV_", "").strip()] = v.upper()
    except Exception:
        pass
    return config

def expandir_descripcion(desc_raw, marca, vehiculo, ano, dicc_extra=None):
    texto_orig = str(desc_raw).upper().strip()
    dicc = DICCIONARIO_BASE.copy()
    if dicc_extra: dicc.update(dicc_extra)

    texto = re.sub(r'\.(?=[A-Z])', '. ', texto_orig)
    piezas_centrales = ["PARRILLA", "REJILLA", "RADIADOR", "CONDENSADOR", "SPOILER", "DEFENSA", "ALMA", "TOLVA", "COFRE", "CAJUELA"]
    tiene_lado = any(x in texto for x in ["DER", " D.", "IZQ"])
    tiene_altura = any(x in texto for x in ["SUP", "INF"])
    es_central = any(p in texto for p in piezas_centrales) and not any(l in texto for l in ["SOP", "GUIA", "FARO", "CALAVERA", "PUERTA", "ESPEJO", "SALP"])

    if tiene_altura: sig_i = "IZQUIERDA"
    elif tiene_lado or es_central: sig_i = "INFERIOR"
    else: sig_i = "IZQUIERDA"

    palabras = texto.split()
    traducidas = []
    for pal in palabras:
        p_s = pal.rstrip('.')
        if pal in ["I.", "I"]: traducidas.append(sig_i)
        elif pal in ["D.", "D"]: traducidas.append("DERECHA")
        elif pal in dicc: traducidas.append(dicc[pal])
        elif p_s in dicc: traducidas.append(dicc[p_s])
        else: traducidas.append(p_s)

    frase = re.sub(r'\s+', ' ', " ".join(traducidas)).strip()
    veh_limpio = str(vehiculo).upper().replace(str(marca).upper(), '').strip()
    return f"{frase} {marca} {veh_limpio} {ano}".strip()

def calcular_fecha_habiles(dias_habiles=7):
    meses_p = {1:'ENE', 2:'FEB', 3:'MAR', 4:'ABR', 5:'MAY', 6:'JUN', 7:'JUL', 8:'AGO', 9:'SEP', 10:'OCT', 11:'NOV', 12:'DIC'}
    tz_mx = datetime.timezone(datetime.timedelta(hours=-6))
    fecha = datetime.datetime.now(tz_mx).date()
    agregados = 0
    while agregados < dias_habiles:
        fecha += datetime.timedelta(days=1)
        if fecha.weekday() < 5: agregados += 1
    while fecha.weekday() >= 5: fecha += datetime.timedelta(days=1)
    return f"{fecha.day:02d} {meses_p[fecha.month]} {fecha.year}"

def estimar_flete(descripcion, ciudad, estado):
    loc_str = f"{ciudad} {estado}".upper()
    if any(k in loc_str for k in ["MONTERREY", "APODACA", "SAN NICOLAS", "GUADALUPE", "SANTA CATARINA", "ESCOBEDO", "SAN PEDRO", "NUEVO LEON"]):
        return 0.0
    es_reg = any(k in loc_str for k in ["SALTILLO", "REYNOSA", "MATAMOROS", "NUEVO LAREDO", "TORREON", "TAMPICO", "COAHUILA", "TAMAULIPAS"])
    d = str(descripcion).upper()
    if any(k in d for k in ["COFRE", "PUERTA", "QUINTA", "CAJUELA", "COSTADO", "PUENTE"]):
        return 750.0 if es_reg else 1200.0
    elif any(k in d for k in ["FACIA", "FASCIA", "SALPICADERA", "FARO", "RADIADOR", "CONDENSADOR", "PARRILLA"]):
        return 450.0 if es_reg else 650.0
    else:
        return 300.0 if es_reg else 380.0

def buscar_precios_mercado(query, tc_usd=20.50):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    precios_orig, precios_noorig, precios_gen = [], [], []
    link_ml = f"https://listado.mercadolibre.com.mx/{urllib.parse.quote(query.replace(' ', '-'))}"
    link_ebay = f"https://www.ebay.com/sch/i.html?_nkw={urllib.parse.quote(query)}"

    try:
        resp = requests.get(f"https://api.mercadolibre.com/sites/MLM/search?q={urllib.parse.quote(query)}&limit=15", headers=headers, timeout=5)
        if resp.status_code == 200:
            for it in resp.json().get("results", []):
                p = float(it.get("price", 0))
                if p < 200: continue
                tit = str(it.get("title", "")).upper()
                cond = str(it.get("condition", "")).lower()
                if it.get("permalink"): link_ml = it["permalink"]
                if cond == "used" or any(k in tit for k in ["USADO", "SEMINUEVO", "YONKE"]): precios_noorig.append(p)
                elif any(k in tit for k in ["ORIGINAL", "OEM", "AGENCIA"]): precios_orig.append(p)
                else: precios_gen.append(p)
    except: pass

    try:
        resp_eb = requests.get(link_ebay, headers=headers, timeout=5)
        if resp_eb.status_code == 200:
            for b in resp_eb.text.split('s-item__info')[1:8]:
                m = re.search(r'\$([0-9]{1,4}(?:,[0-9]{3})*\.[0-9]{2})', b)
                if m:
                    val = float(m.group(1).replace(',', ''))
                    mxn = val if "MXN" in b else round(val * tc_usd)
                    if mxn < 250: continue
                    b_up = b.upper()
                    if any(k in b_up for k in ["PRE-OWNED", "USED", "USADO"]): precios_noorig.append(mxn)
                    elif any(k in b_up for k in ["OEM", "GENUINE", "ORIGINAL"]): precios_orig.append(mxn)
                    else: precios_gen.append(mxn)
    except: pass

    p_orig = round(sum(sorted(precios_orig)[:3]) / len(precios_orig[:3])) if precios_orig else 0
    p_noorig = round(sum(sorted(precios_noorig)[:3]) / len(precios_noorig[:3])) if precios_noorig else 0
    p_gen = round(sum(sorted(precios_gen)[:3]) / len(precios_gen[:3])) if precios_gen else 0
    return p_orig, p_noorig, p_gen, link_ml, link_ebay

def obtener_ws_cotizaciones(doc):
    try:
        ws = doc.worksheet("BD_COTIZACIONES")
        if not ws.row_values(1): ws.append_row(ENCABEZADOS_COT, value_input_option='USER_ENTERED')
    except:
        ws = doc.add_worksheet(title="BD_COTIZACIONES", rows=1000, cols=len(ENCABEZADOS_COT))
        ws.append_row(ENCABEZADOS_COT, value_input_option='USER_ENTERED')
    return ws

def cargar_mapa_historial(doc):
    mapa = {}
    try:
        for r in doc.worksheet("BD_COMPRAS").get_all_values()[1:]:
            if len(r) > 5:
                try:
                    c = float(str(r[5]).replace('$', '').replace(',', '').strip())
                    if c > 0: mapa[f"{str(r[3]).upper()[:12]}_{str(r[2]).upper()[:10]}"] = c
                except: pass
    except: pass
    return mapa

def ejecutar_extraccion_cotizaciones(modo_headless=True):
    print("=== INICIANDO EXTRACCIÓN DE COTIZACIONES ===")
    doc = conectar_sheets()
    cfg = cargar_configuracion_dinamica(doc)
    ws_cot = obtener_ws_cotizaciones(doc)
    mapa_hist = cargar_mapa_historial(doc)

    existentes = {f"{r[2]}_{r[12]}_{r[14]}" for r in ws_cot.get_all_values()[1:] if len(r) > 14}
    nuevas = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=modo_headless)
        page = browser.new_context().new_page()
        page.on("dialog", lambda d: d.accept())

        try:
            print(f"-> Conectando a {PORTAL_URL} con usuario {cfg['MULTI_USER']}...")
            page.goto(PORTAL_URL, timeout=45000)
            page.fill("input[type='text']", cfg["MULTI_USER"])
            page.fill("input[type='password']", cfg["MULTI_PASS"])
            page.click("input[value='Aceptar'], button:has-text('Aceptar')")
            time.sleep(2)

            print("-> Abriendo menú de Cotizaciones...")
            page.evaluate("submitForm('main_action.do','quotation_list_action.do')")
            time.sleep(3)

            frame = page.frame(name="middleFrameRight") or page.frame_locator("iframe[name='middleFrameRight']")
            
            siniestros = frame.evaluate("""
                () => Array.from(document.querySelectorAll('a.cvi'))
                    .filter(a => (a.getAttribute('href')||'').includes('showDetail') && a.textContent.trim().length >= 6)
                    .map(a => ({ siniestro: a.textContent.trim(), js: a.getAttribute('href') }))
            """)
            print(f"-> Siniestros detectados: {len(siniestros)}")

            for idx, item in enumerate(siniestros):
                num_sin = item['siniestro']
                print(f"[{idx+1}/{len(siniestros)}] Procesando Siniestro {num_sin}...")
                try:
                    frame = page.frame(name="middleFrameRight")
                    frame.evaluate(item['js'].replace("javascript:", ""))
                    time.sleep(2)

                    frame = page.frame(name="middleFrameRight")
                    sub_js = frame.evaluate("() => { let a = document.querySelector('a.cvi'); return a ? a.getAttribute('href') : ''; }")
                    if not sub_js: continue
                    frame.evaluate(sub_js.replace("javascript:", ""))
                    time.sleep(2.5)

                    frame = page.frame(name="middleFrameRight")
                    detalle = frame.evaluate(r"""
                        () => {
                            function fullTxt(el) {
                                if (!el) return '';
                                let onm = el.getAttribute('onmouseover') || '';
                                let m = onm.match(/displayTool\s*\(\s*event\s*,\s*['"]([^'"]+)['"]\s*\)/i);
                                if (m && m[1]) return m[1].trim();
                                return el.textContent.replace(/[\s\xA0]+/g, ' ').trim();
                            }
                            let marca = '', vehiculo = '', modelo = '', vin = '', taller = '', ciudad = '', estado = '', fecha_fin = '';
                            Array.from(document.querySelectorAll('td')).forEach((td, i, arr) => {
                                let l = td.textContent.replace(/[\s\xA0]+/g, ' ').trim();
                                if (l === 'Marca:' && arr[i+1]) marca = fullTxt(arr[i+1]);
                                if ((l === 'Vehículo:' || l === 'Vehiculo:') && arr[i+1]) vehiculo = fullTxt(arr[i+1]);
                                if (l.startsWith('Modelo') && arr[i+1]) modelo = fullTxt(arr[i+1]);
                                if (l.startsWith('Serie') && arr[i+1]) vin = fullTxt(arr[i+1]);
                                if (l.startsWith('Nombre') && arr[i+1]) taller = fullTxt(arr[i+1]);
                                if (l.startsWith('Ciudad:') && arr[i+1]) ciudad = fullTxt(arr[i+1]);
                                if (l.startsWith('Estado:') && arr[i+1] && !estado) estado = fullTxt(arr[i+1]);
                                if (l.startsWith('Fecha Fin') && arr[i+1]) fecha_fin = fullTxt(arr[i+1]);
                            });
                            let piezas = [];
                            document.querySelectorAll("select[name='statusPart']").forEach((sel, idx) => {
                                let tr = sel.closest('tr');
                                if (tr) {
                                    let tds = tr.querySelectorAll('td');
                                    piezas.push({ idx: idx, cantidad: tds[0]?tds[0].textContent.trim():'1', descripcion: tds[1]?fullTxt(tds[1]):'' });
                                }
                            });
                            return { marca, vehiculo, modelo, vin, taller, ciudad, estado, fecha_fin, piezas };
                        }
                    """)

                    ahora = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-6))).strftime("%Y-%m-%d %H:%M")
                    for pza in detalle.get('piezas', []):
                        if f"{num_sin}_{pza['idx']}_{pza['descripcion']}" in existentes: continue
                        q = expandir_descripcion(pza['descripcion'], detalle.get('marca',''), detalle.get('vehiculo',''), detalle.get('modelo',''), cfg.get("DICCIONARIO_EXTRA", {}))
                        p_orig, p_noorig, p_gen, l_ml, l_eb = buscar_precios_mercado(q, cfg.get("TC_USD", 20.50))
                        p_hist = mapa_hist.get(f"{pza['descripcion'][:12].upper()}_{detalle.get('vehiculo','')[:10].upper()}", 0.0)
                        flete = estimar_flete(pza['descripcion'], detalle.get('ciudad',''), detalle.get('estado',''))

                        costo = p_gen or p_noorig or p_orig or p_hist or 0
                        origen = "NO ORIGINAL" if p_gen or p_noorig else ("ORIGINAL" if p_orig else "NO ORIGINAL")
                        fuente = "ML" if costo > 0 else "MAN"
                        sug = round((costo + flete) * 1.35) if costo > 0 else 0

                        nuevas.append([
                            f"COT-{num_sin}-{pza['idx']+1}", ahora, num_sin, "1",
                            detalle.get('marca',''), detalle.get('vehiculo',''), detalle.get('modelo',''), detalle.get('vin',''),
                            detalle.get('taller',''), detalle.get('ciudad',''), detalle.get('estado',''), detalle.get('fecha_fin',''),
                            pza['idx'], pza['cantidad'], pza['descripcion'], q,
                            p_orig, p_noorig, p_gen, p_hist, flete, fuente, origen, costo, 35, sug, 0, sug,
                            f"HUB{fuente}{random.randint(100,999)}", l_ml, l_eb, "FALSE", "PENDIENTE"
                        ])

                    page.evaluate("submitForm('main_action.do','quotation_list_action.do')")
                    time.sleep(2)
                except Exception as e:
                    print(f"  [!] Error en siniestro {num_sin}: {e}")
                    try: page.evaluate("submitForm('main_action.do','quotation_list_action.do')")
                    except: pass
        finally:
            browser.close()

    if nuevas:
        ws_cot.append_rows(nuevas, value_input_option='USER_ENTERED')
        print(f"\n✅ {len(nuevas)} partidas extraídas y guardadas exitosamente en BD_COTIZACIONES.")
    else:
        print("\n✅ Sin partidas nuevas.")

def ejecutar_envio_cotizaciones(modo_headless=True):
    print("=== INICIANDO ENVÍO DE COTIZACIONES AL PORTAL ===")
    doc = conectar_sheets()
    cfg = cargar_configuracion_dinamica(doc)
    ws_cot = obtener_ws_cotizaciones(doc)
    datos = ws_cot.get_all_values()
    if len(datos) <= 1: return

    headers = [str(h).strip() for h in datos[0]]
    idx_sin = headers.index("Siniestro")
    idx_pza = headers.index("Partida_Idx")
    idx_ori = headers.index("Origen_Portal")
    idx_fin = headers.index("Precio_Final_Enviar")
    idx_cod = headers.index("Codigo_Hub")
    idx_val = headers.index("Validar_Envio")
    idx_est = headers.index("Estatus_Cotizacion")

    por_enviar = {}
    for r_num, r in enumerate(datos[1:], start=2):
        if len(r) <= idx_est: continue
        if str(r[idx_val]).strip().upper() in ["TRUE", "SI", "1", "VERDADERO"] and str(r[idx_est]).strip().upper() == "PENDIENTE":
            try: p_int = int(round(float(str(r[idx_fin]).replace('$', '').replace(',', '').strip())))
            except: p_int = 0
            if p_int > 0:
                por_enviar.setdefault(str(r[idx_sin]).strip(), []).append({
                    'gs_row': r_num, 'partida_idx': int(r[idx_pza]),
                    'origen_txt': str(r[idx_ori]).strip().upper(), 'precio_int': str(p_int),
                    'codigo_hub': re.sub(r'[^A-Za-z0-9]', '', str(r[idx_cod]).strip().upper())[:20]
                })

    if not por_enviar:
        print("⚠️ No hay partidas validadas para enviar.")
        return

    fecha_7d = calcular_fecha_habiles(7)
    mapa_orig = {"ORIGINAL": "42007", "NO ORIGINAL": "42008", "GENERICA": "42008", "SEMINUEVA": "42009"}
    actualizar = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=modo_headless)
        page = browser.new_context().new_page()
        page.on("dialog", lambda d: d.accept())

        try:
            page.goto(PORTAL_URL, timeout=45000)
            page.fill("input[type='text']", cfg["MULTI_USER"])
            page.fill("input[type='password']", cfg["MULTI_PASS"])
            page.click("input[value='Aceptar'], button:has-text('Aceptar')")
            time.sleep(2)
            page.evaluate("submitForm('main_action.do','quotation_list_action.do')")
            time.sleep(3)

            for sin, items in por_enviar.items():
                try:
                    frame = page.frame(name="middleFrameRight")
                    link = frame.locator(f"a.cvi:has-text('{sin}')")
                    if link.count() == 0: continue
                    frame.evaluate(link.first.get_attribute("href").replace("javascript:", ""))
                    time.sleep(2)

                    frame = page.frame(name="middleFrameRight")
                    frame.evaluate(frame.locator("a.cvi").first.get_attribute("href").replace("javascript:", ""))
                    time.sleep(2.5)

                    frame = page.frame(name="middleFrameRight")
                    for it in items:
                        frame.evaluate("""
                            (args) => {
                                const i = args.idx;
                                const s = document.querySelectorAll("select[name='statusPart']");
                                const c = document.querySelectorAll("input[name='codePart']");
                                const pr = document.querySelectorAll("input[name='price']");
                                const o = document.querySelectorAll("select[name='origin']");
                                if(s[i]) { s[i].value = '133002'; if(typeof s[i].onchange==='function') s[i].onchange(); }
                                let fV = document.getElementById('promiseDatePart'+i), fH = document.getElementById('promiseDateValue'+i);
                                if(fV) fV.value = args.fecha; if(fH) fH.value = args.fecha;
                                if(c[i]) c[i].value = args.codigo;
                                if(pr[i]) pr[i].value = args.precio;
                                if(o[i]) { o[i].value = args.origen; if(typeof o[i].onchange==='function') o[i].onchange(); }
                            }
                        """, {"idx": it['partida_idx'], "fecha": fecha_7d, "codigo": it['codigo_hub'], "precio": it['precio_int'], "origen": mapa_orig.get(it['origen_txt'], "42008")})
                        time.sleep(0.2)

                    btn = frame.locator("input[name='btnSubmit'][value='Grabar']")
                    if btn.count() > 0:
                        btn.first.click()
                        time.sleep(3)
                        for it in items: actualizar.append(gspread.Cell(row=it['gs_row'], col=idx_est + 1, value="ENVIADA PORTAL"))

                    page.evaluate("submitForm('main_action.do','quotation_list_action.do')")
                    time.sleep(2)
                except Exception as e:
                    print(f"[!] Error enviando {sin}: {e}")
        finally:
            browser.close()

    if actualizar:
        ws_cot.update_cells(actualizar, value_input_option='USER_ENTERED')
        print(f"\n✅ {len(actualizar)} partidas marcadas como 'ENVIADA PORTAL'.")

if __name__ == "__main__":
    oculto = False if "--visual" in sys.argv else True
    if "--enviar" in sys.argv: ejecutar_envio_cotizaciones(modo_headless=oculto)
    else: ejecutar_extraccion_cotizaciones(modo_headless=oculto)
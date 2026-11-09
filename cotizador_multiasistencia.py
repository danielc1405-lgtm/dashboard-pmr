import os
import re
import sys
import json
import time
import random
import datetime
import urllib.parse
import requests
from playwright.sync_api import sync_playwright
import gspread
from google.oauth2.service_account import Credentials

# --- CREDENCIALES BASE POR DEFECTO ---
SHEET_ID = "10jrOsS054n0atMk8GxQilkXqm6LjsnrwPOZnSx8iDek"
PORTAL_URL = "https://siniestros.bbva.mx/refaccionarias/"
DEFAULT_USER = "PMA5816"
DEFAULT_PASS = "Pmroct1."
DEFAULT_TC_USD = 20.50

ENCABEZADOS_COT = [
    "ID_Cotizacion", "Fecha_Extraccion", "Siniestro", "Cotizacion_No",
    "Marca", "Vehiculo", "Modelo_Ano", "VIN", "Taller", "Ciudad", "Estado", "Fecha_Fin",
    "Partida_Idx", "Cantidad", "Descripcion_Portal", "Busqueda_Sugerida",
    "Precio_Original", "Precio_No_Original", "Precio_Generica", "Precio_Historial",
    "Flete_Estimado", "Fuente_Seleccionada", "Origen_Portal", "Costo_Base",
    "Margen_Pct", "Precio_Sugerido", "Precio_Libre", "Precio_Final_Enviar",
    "Codigo_Hub", "Link_ML", "Link_eBay", "Validar_Envio", "Estatus_Cotizacion"
]

# --- DICCIONARIO BASE DE ABREVIATURAS ---
DICCIONARIO_BASE = {
    "FACIA": "FASCIA",
    "DEL.": "DELANTERA",
    "DEL": "DELANTERA",
    "TRA.": "TRASERA",
    "TRA": "TRASERA",
    "TRAS.": "TRASERA",
    "TRAS": "TRASERA",
    "IZQ.": "IZQUIERDA",
    "IZQ": "IZQUIERDA",
    "DER.": "DERECHA",
    "DER": "DERECHA",
    "D.": "DERECHA",
    "SOP.": "SOPORTE",
    "SOP": "SOPORTE",
    "CEN.": "CENTRAL",
    "CEN": "CENTRAL",
    "SUP.": "SUPERIOR",
    "SUP": "SUPERIOR",
    "INF.": "INFERIOR",
    "INF": "INFERIOR",
    "EXT.": "EXTERIOR",
    "INT.": "INTERIOR",
    "PTA.": "PUERTA",
    "PTA": "PUERTA",
    "SALP.": "SALPICADERA",
    "SALP": "SALPICADERA",
    "MOLD.": "MOLDURA",
    "MOLD": "MOLDURA",
    "ANTIN.": "ANTINIEBLA",
    "ANITIN.": "ANTINIEBLA",
    "INTEG.": "INTEGRADO",
    "INTEG": "INTEGRADO",
    "C/HOYO": "CON HOYO",
    "S/HOYO": "SIN HOYO"
}

def conectar_sheets():
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    credenciales = Credentials.from_service_account_file('credentials.json', scopes=scopes)
    cliente = gspread.authorize(credenciales)
    return cliente.open_by_key(SHEET_ID)

def cargar_configuracion_dinamica(doc):
    """Lee Usuario, Password, Tipo de Cambio y Diccionario personalizado desde BD_CONFIG_BOTS."""
    config = {
        "MULTI_USER": DEFAULT_USER,
        "MULTI_PASS": DEFAULT_PASS,
        "TC_USD": DEFAULT_TC_USD,
        "DICCIONARIO_EXTRA": {}
    }
    try:
        ws_cfg = doc.worksheet("BD_CONFIG_BOTS")
        filas = ws_cfg.get_all_values()
        for f in filas[1:]:
            if len(f) >= 2:
                k, v = str(f[0]).strip().upper(), str(f[1]).strip()
                if k == "MULTI_USER" and v:
                    config["MULTI_USER"] = v
                elif k == "MULTI_PASS" and v:
                    config["MULTI_PASS"] = v
                elif k == "TC_USD" and v:
                    try:
                        config["TC_USD"] = float(v)
                    except Exception:
                        pass
                elif k.startswith("ABREV_") and v:
                    abrev_key = k.replace("ABREV_", "").strip()
                    config["DICCIONARIO_EXTRA"][abrev_key] = v.upper()
    except Exception:
        pass
    return config

def expandir_descripcion(desc_raw, marca, vehiculo, ano, dicc_extra=None):
    """Traduce abreviaturas del portal y resuelve 'I.' (Izquierda vs Inferior) por contexto."""
    texto_orig = str(desc_raw).upper().strip()
    dicc = DICCIONARIO_BASE.copy()
    if dicc_extra:
        dicc.update(dicc_extra)

    # Separar puntos pegados a letras (ej. SOP.FACIA.D. -> SOP. FACIA. D.)
    texto = re.sub(r'\.(?=[A-Z])', '. ', texto_orig)

    # Regla contextual para resolver "I." o "I" suelta (Izquierda vs Inferior)
    piezas_centrales = ["PARRILLA", "REJILLA", "RADIADOR", "CONDENSADOR", "SPOILER", "DEFENSA", "ALMA", "TOLVA", "COFRE", "CAJUELA"]
    tiene_lado_explicito = any(x in texto for x in ["DER", " D.", "IZQ"])
    tiene_altura_explicita = any(x in texto for x in ["SUP", "INF"])
    es_pieza_central = any(p in texto for p in piezas_centrales) and not any(l in texto for l in ["SOP", "GUIA", "FARO", "CALAVERA", "PUERTA", "ESPEJO", "SALP"])

    if tiene_altura_explicita:
        significado_i = "IZQUIERDA"
    elif tiene_lado_explicito or es_pieza_central:
        significado_i = "INFERIOR"
    else:
        significado_i = "IZQUIERDA"

    palabras = texto.split()
    palabras_traducidas = []
    for pal in palabras:
        pal_sin_punto = pal.rstrip('.')
        if pal in ["I.", "I"]:
            palabras_traducidas.append(significado_i)
        elif pal in ["D.", "D"]:
            palabras_traducidas.append("DERECHA")
        elif pal in dicc:
            palabras_traducidas.append(dicc[pal])
        elif pal_sin_punto in dicc:
            palabras_traducidas.append(dicc[pal_sin_punto])
        else:
            palabras_traducidas.append(pal_sin_punto)

    frase_pieza = " ".join(palabras_traducidas)
    frase_pieza = re.sub(r'\s+', ' ', frase_pieza).strip()
    veh_limpio = str(vehiculo).upper().replace(str(marca).upper(), '').strip()
    return f"{frase_pieza} {marca} {veh_limpio} {ano}".strip()

def calcular_fecha_habiles(dias_habiles=7):
    """Suma 7 días hábiles (L-V). Si cae en sábado o domingo, empuja al lunes siguiente."""
    meses_portal = {
        1: 'ENE', 2: 'FEB', 3: 'MAR', 4: 'ABR', 5: 'MAY', 6: 'JUN',
        7: 'JUL', 8: 'AGO', 9: 'SEP', 10: 'OCT', 11: 'NOV', 12: 'DIC'
    }
    tz_mx = datetime.timezone(datetime.timedelta(hours=-6))
    fecha = datetime.datetime.now(tz_mx).date()
    agregados = 0
    while agregados < dias_habiles:
        fecha += datetime.timedelta(days=1)
        if fecha.weekday() < 5:  # 0=Lunes ... 4=Viernes
            agregados += 1
    while fecha.weekday() >= 5:
        fecha += datetime.timedelta(days=1)
    return f"{fecha.day:02d} {meses_portal[fecha.month]} {fecha.year}"

def estimar_flete(descripcion, ciudad, estado):
    """Calcula envío considerando distancia y volumen. Piso mínimo de mensajería: $300 MXN."""
    loc_str = f"{ciudad} {estado}".upper()
    if any(k in loc_str for k in ["MONTERREY", "APODACA", "SAN NICOLAS", "GUADALUPE", "SANTA CATARINA", "ESCOBEDO", "SAN PEDRO", "NUEVO LEON"]):
        return 0.0
    
    es_regional = any(k in loc_str for k in ["SALTILLO", "RAMOS ARIZPE", "REYNOSA", "MATAMOROS", "NUEVO LAREDO", "TORREON", "MONCLOVA", "TAMPICO", "CIUDAD VICTORIA", "COAHUILA", "TAMAULIPAS"])
    
    d = str(descripcion).upper()
    if any(k in d for k in ["COFRE", "PUERTA", "PTA", "QUINTA", "CAJUELA", "COSTADO", "CAPACETE", "PUENTE", "EJE"]):
        return 750.0 if es_regional else 1200.0
    elif any(k in d for k in ["FACIA", "FASCIA", "SALPICADERA", "FARO", "RADIADOR", "CONDENSADOR", "PARRILLA", "DEFENSA", "ALMA", "REFUERZO"]):
        return 450.0 if es_regional else 650.0
    else:
        return 300.0 if es_regional else 380.0

def buscar_precios_mercado(query, tc_usd=20.50):
    """Consulta Mercado Libre México y eBay Motors EE.UU. devolviendo las 3 columnas y links."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "es-MX,es;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    precios_orig, precios_noorig, precios_gen = [], [], []
    link_ml = f"https://listado.mercadolibre.com.mx/{urllib.parse.quote(query.replace(' ', '-'))}"
    link_ebay = f"https://www.ebay.com/sch/i.html?_nkw={urllib.parse.quote(query)}"

    # 1. MERCADO LIBRE MÉXICO (API Pública)
    try:
        url_api = f"https://api.mercadolibre.com/sites/MLM/search?q={urllib.parse.quote(query)}&limit=15"
        resp = requests.get(url_api, headers=headers, timeout=6)
        if resp.status_code == 200:
            items = resp.json().get("results", [])
            for it in items:
                p = float(it.get("price", 0))
                if p < 200:
                    continue
                titulo = str(it.get("title", "")).upper()
                condicion = str(it.get("condition", "")).lower()
                permalink = it.get("permalink", "")
                if permalink and "listado.mercadolibre" in link_ml:
                    link_ml = permalink

                if condicion == "used" or any(k in titulo for k in ["USADO", "USADA", "SEMINUEVO", "SEMINUEVA", "YONKE", "DESHUESO"]):
                    precios_noorig.append(p)
                elif any(k in titulo for k in ["ORIGINAL", "OEM", "GENUINO", "GENUINA", "AGENCIA"]):
                    precios_orig.append(p)
                else:
                    precios_gen.append(p)
    except Exception:
        pass

    # 2. EBAY EE.UU. (Extracción ligera y conversión de USD a MXN)
    try:
        resp_eb = requests.get(link_ebay, headers=headers, timeout=6)
        if resp_eb.status_code == 200:
            html_eb = resp_eb.text
            bloques = html_eb.split('s-item__info')
            for b in bloques[1:10]:
                m_price = re.search(r'\$([0-9]{1,4}(?:,[0-9]{3})*\.[0-9]{2})', b)
                if not m_price:
                    continue
                val_num = float(m_price.group(1).replace(',', ''))
                # Si la página respondió en USD (valores típicos < 600 USD), multiplicamos por tipo de cambio
                es_mxn_directo = ("MXN" in b or "Mex$" in b)
                precio_mxn = val_num if es_mxn_directo else round(val_num * tc_usd)
                if precio_mxn < 250:
                    continue

                b_up = b.upper()
                if any(k in b_up for k in ["PRE-OWNED", "USED", "USADO", "SEMINUEVO"]):
                    precios_noorig.append(precio_mxn)
                elif any(k in b_up for k in ["OEM", "GENUINE", "FACTORY", "ORIGINAL"]):
                    precios_orig.append(precio_mxn)
                else:
                    precios_gen.append(precio_mxn)
    except Exception:
        pass

    p_orig = round(sum(sorted(precios_orig)[:3]) / len(precios_orig[:3])) if precios_orig else 0
    p_noorig = round(sum(sorted(precios_noorig)[:3]) / len(precios_noorig[:3])) if precios_noorig else 0
    p_gen = round(sum(sorted(precios_gen)[:3]) / len(precios_gen[:3])) if precios_gen else 0

    return p_orig, p_noorig, p_gen, link_ml, link_ebay

def obtener_ws_cotizaciones(doc):
    try:
        ws = doc.worksheet("BD_COTIZACIONES")
        primera_fila = ws.row_values(1)
        if not primera_fila:
            ws.append_row(ENCABEZADOS_COT, value_input_option='USER_ENTERED')
    except Exception:
        ws = doc.add_worksheet(title="BD_COTIZACIONES", rows=1000, cols=len(ENCABEZADOS_COT))
        ws.append_row(ENCABEZADOS_COT, value_input_option='USER_ENTERED')
    return ws

def cargar_mapa_historial(doc):
    mapa_hist = {}
    try:
        ws_c = doc.worksheet("BD_COMPRAS")
        for r in ws_c.get_all_values()[1:]:
            if len(r) > 5:
                veh = str(r[2]).upper()
                pza = str(r[3]).upper()
                try:
                    costo = float(str(r[5]).replace('$', '').replace(',', '').strip())
                    if costo > 0:
                        mapa_hist[f"{pza[:12]}_{veh[:10]}"] = costo
                except Exception:
                    pass
    except Exception:
        pass
    return mapa_hist

def obtener_frame_derecho(page):
    frame = page.frame(name="middleFrameRight")
    if not frame:
        frame = page.frame_locator("iframe[name='middleFrameRight']")
    return frame

# ==============================================================================
# MODO 1: EXTRAER COTIZACIONES E INVESTIGAR PRECIOS (ML + EBAY + HISTORIAL)
# ==============================================================================
def ejecutar_extraccion_cotizaciones(modo_headless=True):
    print("==========================================================")
    print(" 🤖 COTIZADOR AI MULTIASISTENCIA: EXTRACCIÓN Y MERCADO ")
    print("==========================================================")

    doc = conectar_sheets()
    cfg = cargar_configuracion_dinamica(doc)
    ws_cot = obtener_ws_cotizaciones(doc)
    mapa_hist = cargar_mapa_historial(doc)

    datos_existentes = ws_cot.get_all_values()
    llaves_existentes = set()
    if len(datos_existentes) > 1:
        for r in datos_existentes[1:]:
            if len(r) > 14:
                llaves_existentes.add(f"{r[2]}_{r[12]}_{r[14]}")

    nuevas_filas_cot = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=modo_headless)
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = context.new_page()
        page.on("dialog", lambda dialog: dialog.accept())

        try:
            print(f"-> Iniciando sesión en Multiasistencia con usuario {cfg['MULTI_USER']}...")
            page.goto(PORTAL_URL, timeout=60000)
            page.fill("input[type='text']", cfg["MULTI_USER"])
            page.fill("input[type='password']", cfg["MULTI_PASS"])
            page.click("input[value='Aceptar'], button:has-text('Aceptar')")
            time.sleep(2.5)

            print("-> Entrando a la bandeja de 'Cotizaciones'...")
            try:
                page.evaluate("submitForm('main_action.do','quotation_list_action.do')")
            except Exception:
                page.click("text=Cotizaciones", timeout=15000)
            time.sleep(3)

            frame = obtener_frame_derecho(page)

            siniestros_cot = frame.evaluate("""
                () => {
                    let lista = [];
                    let links = Array.from(document.querySelectorAll('a.cvi'));
                    for (let a of links) {
                        let href = a.getAttribute('href') || '';
                        let txt = a.textContent.trim();
                        if (href.includes('showDetail') && txt.length >= 6) {
                            lista.push({ siniestro: txt, js: href });
                        }
                    }
                    return lista;
                }
            """)

            print(f"-> Se detectaron {len(siniestros_cot)} siniestros pendientes por cotizar.")

            for idx_s, item_s in enumerate(siniestros_cot):
                num_sin = item_s['siniestro']
                print(f"\n[{idx_s+1}/{len(siniestros_cot)}] Abriendo Siniestro {num_sin}...")

                try:
                    frame = obtener_frame_derecho(page)
                    frame.evaluate(item_s['js'].replace("javascript:", ""))
                    time.sleep(2.2)

                    frame = obtener_frame_derecho(page)
                    sub_links = frame.evaluate("""
                        () => {
                            let links = Array.from(document.querySelectorAll('a.cvi'));
                            return links.map(a => ({ num: a.textContent.trim(), js: a.getAttribute('href') || '' }));
                        }
                    """)

                    if not sub_links:
                        print(f"  [!] No se encontró liga de detalle en {num_sin}.")
                        continue

                    cot_no = sub_links[0]['num']
                    frame.evaluate(sub_links[0]['js'].replace("javascript:", ""))
                    time.sleep(2.5)

                    frame = obtener_frame_derecho(page)
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
                            let tds = Array.from(document.querySelectorAll('td'));
                            for (let i = 0; i < tds.length; i++) {
                                let label = tds[i].textContent.replace(/[\s\xA0]+/g, ' ').trim();
                                if (label === 'Marca:' && tds[i+1]) marca = fullTxt(tds[i+1]);
                                if ((label === 'Vehículo:' || label === 'Vehiculo:') && tds[i+1]) vehiculo = fullTxt(tds[i+1]);
                                if (label.startsWith('Modelo') && tds[i+1]) modelo = fullTxt(tds[i+1]);
                                if (label.startsWith('Serie') && tds[i+1]) vin = fullTxt(tds[i+1]);
                                if (label.startsWith('Nombre') && tds[i+1]) taller = fullTxt(tds[i+1]);
                                if (label.startsWith('Ciudad:') && tds[i+1]) ciudad = fullTxt(tds[i+1]);
                                if (label.startsWith('Estado:') && tds[i+1] && !estado) estado = fullTxt(tds[i+1]);
                                if (label.startsWith('Fecha Fin') && tds[i+1]) fecha_fin = fullTxt(tds[i+1]);
                            }

                            let piezas = [];
                            let selects = Array.from(document.querySelectorAll("select[name='statusPart']"));
                            selects.forEach((sel, idx) => {
                                let tr = sel.closest('tr');
                                if (tr) {
                                    let celdas = Array.from(tr.querySelectorAll('td'));
                                    let cant = celdas[0] ? celdas[0].textContent.trim() : '1';
                                    let desc = celdas[1] ? fullTxt(celdas[1]) : '';
                                    piezas.push({ idx: idx, cantidad: cant, descripcion: desc });
                                }
                            });

                            return { marca, vehiculo, modelo, vin, taller, ciudad, estado, fecha_fin, piezas };
                        }
                    """)

                    piezas_sin = detalle.get('piezas', [])
                    print(f"  -> Auto: {detalle.get('marca')} {detalle.get('vehiculo')} {detalle.get('modelo')} | Destino: {detalle.get('ciudad')} | {len(piezas_sin)} pieza(s)")

                    tz_mx = datetime.timezone(datetime.timedelta(hours=-6))
                    ahora_str = datetime.datetime.now(tz_mx).strftime("%Y-%m-%d %H:%M")

                    for pza in piezas_sin:
                        llave_p = f"{num_sin}_{pza['idx']}_{pza['descripcion']}"
                        if llave_p in llaves_existentes:
                            continue

                        busqueda_q = expandir_descripcion(
                            pza['descripcion'],
                            detalle.get('marca', ''),
                            detalle.get('vehiculo', ''),
                            detalle.get('modelo', ''),
                            cfg.get("DICCIONARIO_EXTRA", {})
                        )
                        print(f"     🔎 Buscando ML + eBay Partida {pza['idx']+1}: {busqueda_q}...")
                        p_orig, p_noorig, p_gen, link_ml, link_ebay = buscar_precios_mercado(busqueda_q, cfg.get("TC_USD", 20.50))

                        k_hist = f"{pza['descripcion'][:12].upper()}_{detalle.get('vehiculo', '')[:10].upper()}"
                        p_hist = mapa_hist.get(k_hist, 0.0)

                        flete_est = estimar_flete(pza['descripcion'], detalle.get('ciudad', ''), detalle.get('estado', ''))

                        if p_gen > 0:
                            costo_base = p_gen
                            origen_sug = "NO ORIGINAL"
                            fuente_sug = "ML"
                        elif p_noorig > 0:
                            costo_base = p_noorig
                            origen_sug = "SEMINUEVA"
                            fuente_sug = "ML"
                        elif p_orig > 0:
                            costo_base = p_orig
                            origen_sug = "ORIGINAL"
                            fuente_sug = "ML"
                        else:
                            costo_base = p_hist
                            origen_sug = "NO ORIGINAL"
                            fuente_sug = "HIST" if p_hist > 0 else "MAN"

                        margen_default = 35
                        precio_sugerido = round((costo_base + flete_est) * (1 + margen_default / 100.0)) if costo_base > 0 else 0
                        codigo_hub = f"HUB{fuente_sug}{random.randint(100, 999)}"
                        id_cot = f"COT-{num_sin}-{pza['idx']+1}"

                        nuevas_filas_cot.append([
                            id_cot, ahora_str, num_sin, cot_no,
                            detalle.get('marca', ''), detalle.get('vehiculo', ''), detalle.get('modelo', ''), detalle.get('vin', ''),
                            detalle.get('taller', ''), detalle.get('ciudad', ''), detalle.get('estado', ''), detalle.get('fecha_fin', ''),
                            pza['idx'], pza['cantidad'], pza['descripcion'], busqueda_q,
                            p_orig, p_noorig, p_gen, p_hist,
                            flete_est, fuente_sug, origen_sug, costo_base,
                            margen_default, precio_sugerido, 0, precio_sugerido,
                            codigo_hub, link_ml, link_ebay, "FALSE", "PENDIENTE"
                        ])

                    page.evaluate("submitForm('main_action.do','quotation_list_action.do')")
                    time.sleep(2.2)

                except Exception as e_sin:
                    print(f"  [!] Error procesando siniestro {num_sin}: {e_sin}")
                    try:
                        page.evaluate("submitForm('main_action.do','quotation_list_action.do')")
                        time.sleep(2)
                    except Exception:
                        pass

        finally:
            browser.close()

    if nuevas_filas_cot:
        ws_cot.append_rows(nuevas_filas_cot, value_input_option='USER_ENTERED')
        print(f"\n✅ Se registraron {len(nuevas_filas_cot)} partidas listas para revisión en BD_COTIZACIONES.")
    else:
        print("\n✅ No hubo partidas nuevas por agregar (todas las activas ya están en tu bandeja).")


# ==============================================================================
# MODO 2: INYECTAR Y GRABAR EN EL PORTAL LAS PARTIDAS VALIDADAS
# ==============================================================================
def ejecutar_envio_cotizaciones(modo_headless=True):
    print("==========================================================")
    print(" 🚀 COTIZADOR AI MULTIASISTENCIA: ENVÍO AL PORTAL (7 DÍAS) ")
    print("==========================================================")

    doc = conectar_sheets()
    cfg = cargar_configuracion_dinamica(doc)
    ws_cot = obtener_ws_cotizaciones(doc)
    datos = ws_cot.get_all_values()
    if len(datos) <= 1:
        print("[!] No hay datos en BD_COTIZACIONES.")
        return

    headers = [str(h).strip() for h in datos[0]]
    idx_sin = headers.index("Siniestro")
    idx_pza = headers.index("Partida_Idx")
    idx_ori = headers.index("Origen_Portal")
    idx_fin = headers.index("Precio_Final_Enviar")
    idx_cod = headers.index("Codigo_Hub")
    idx_val = headers.index("Validar_Envio")
    idx_est = headers.index("Estatus_Cotizacion")

    por_enviar = {}
    for row_num, r in enumerate(datos[1:], start=2):
        if len(r) <= idx_est:
            continue
        val_flag = str(r[idx_val]).strip().upper() in ["TRUE", "SI", "1", "VERDADERO"]
        est_actual = str(r[idx_est]).strip().upper()
        try:
            precio_entero = int(round(float(str(r[idx_fin]).replace('$', '').replace(',', '').strip())))
        except Exception:
            precio_entero = 0

        if val_flag and est_actual == "PENDIENTE" and precio_entero > 0:
            sin_k = str(r[idx_sin]).strip()
            por_enviar.setdefault(sin_k, []).append({
                'gs_row': row_num,
                'partida_idx': int(r[idx_pza]),
                'origen_txt': str(r[idx_ori]).strip().upper(),
                'precio_int': str(precio_entero),
                'codigo_hub': re.sub(r'[^A-Za-z0-9]', '', str(r[idx_cod]).strip().upper())[:20]
            })

    if not por_enviar:
        print("⚠️ No hay partidas validadas con precio > $0 y estatus PENDIENTE para enviar.")
        return

    fecha_promesa_7d = calcular_fecha_habiles(7)
    print(f"-> Fecha Promesa calculada (7 días hábiles L-V): {fecha_promesa_7d}")
    print(f"-> Siniestros a cotizar en el portal: {list(por_enviar.keys())}")

    mapa_origen_valor = {
        "ORIGINAL": "42007",
        "NO ORIGINAL": "42008",
        "GENERICA": "42008",
        "SEMINUEVA": "42009"
    }

    celdas_actualizar = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=modo_headless)
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = context.new_page()
        page.on("dialog", lambda dialog: dialog.accept())

        try:
            page.goto(PORTAL_URL, timeout=60000)
            page.fill("input[type='text']", cfg["MULTI_USER"])
            page.fill("input[type='password']", cfg["MULTI_PASS"])
            page.click("input[value='Aceptar'], button:has-text('Aceptar')")
            time.sleep(2.5)

            page.evaluate("submitForm('main_action.do','quotation_list_action.do')")
            time.sleep(3)

            for sin_target, lista_partidas in por_enviar.items():
                print(f"\n-> Entrando al Siniestro {sin_target} para grabar {len(lista_partidas)} partida(s)...")
                try:
                    frame = obtener_frame_derecho(page)
                    link_sin = frame.locator(f"a.cvi:has-text('{sin_target}')")
                    if link_sin.count() == 0:
                        print(f"  [!] El siniestro {sin_target} ya no aparece en la bandeja activa.")
                        continue

                    href_sin = link_sin.first.get_attribute("href")
                    frame.evaluate(href_sin.replace("javascript:", ""))
                    time.sleep(2)

                    frame = obtener_frame_derecho(page)
                    href_cot = frame.locator("a.cvi").first.get_attribute("href")
                    frame.evaluate(href_cot.replace("javascript:", ""))
                    time.sleep(2.5)

                    frame = obtener_frame_derecho(page)

                    for item_p in lista_partidas:
                        idx_p = item_p['partida_idx']
                        cod_origen = mapa_origen_valor.get(item_p['origen_txt'], "42008")
                        precio_str = item_p['precio_int']
                        codigo_str = item_p['codigo_hub']

                        print(f"   ✔️ Partida #{idx_p+1} | Precio: ${precio_str} | Origen: {item_p['origen_txt']} ({cod_origen}) | Código: {codigo_str}")

                        frame.evaluate(
                            """
                            (args) => {
                                const i = args.idx;
                                const selectsStatus = document.querySelectorAll("select[name='statusPart']");
                                const inputsCode = document.querySelectorAll("input[name='codePart']");
                                const inputsPrice = document.querySelectorAll("input[name='price']");
                                const selectsOrigin = document.querySelectorAll("select[name='origin']");

                                if (selectsStatus[i]) {
                                    selectsStatus[i].value = '133002'; // Aceptar
                                    if (typeof selectsStatus[i].onchange === 'function') {
                                        selectsStatus[i].onchange();
                                    }
                                }

                                const fVisible = document.getElementById('promiseDatePart' + i);
                                const fHidden = document.getElementById('promiseDateValue' + i);
                                if (fVisible) fVisible.value = args.fecha;
                                if (fHidden) fHidden.value = args.fecha;

                                if (inputsCode[i]) {
                                    inputsCode[i].value = args.codigo;
                                }
                                if (inputsPrice[i]) {
                                    inputsPrice[i].value = args.precio;
                                }
                                if (selectsOrigin[i]) {
                                    selectsOrigin[i].value = args.origen;
                                    if (typeof selectsOrigin[i].onchange === 'function') {
                                        selectsOrigin[i].onchange();
                                    }
                                }
                            }
                            """,
                            {
                                "idx": idx_p,
                                "fecha": fecha_promesa_7d,
                                "codigo": codigo_str,
                                "precio": precio_str,
                                "origen": cod_origen
                            }
                        )
                        time.sleep(0.3)

                    btn_grabar = frame.locator("input[name='btnSubmit'][value='Grabar']")
                    if btn_grabar.count() > 0:
                        btn_grabar.first.click()
                        time.sleep(3)
                        print(f"  🎉 Siniestro {sin_target} GRABADO exitosamente en Multiasistencia.")
                        for item_p in lista_partidas:
                            celdas_actualizar.append(gspread.Cell(row=item_p['gs_row'], col=idx_est + 1, value="ENVIADA PORTAL"))
                    else:
                        print(f"  [!] No se encontró el botón Grabar en {sin_target}.")

                    page.evaluate("submitForm('main_action.do','quotation_list_action.do')")
                    time.sleep(2.2)

                except Exception as e_env:
                    print(f"  [!] Error enviando siniestro {sin_target}: {e_env}")

        finally:
            browser.close()

    if celdas_actualizar:
        ws_cot.update_cells(celdas_actualizar, value_input_option='USER_ENTERED')
        print(f"\n✅ Se actualizaron {len(celdas_actualizar)} partidas a 'ENVIADA PORTAL' en BD_COTIZACIONES.")


if __name__ == "__main__":
    modo_oculto = False if "--visual" in sys.argv else True
    if "--enviar" in sys.argv:
        ejecutar_envio_cotizaciones(modo_headless=modo_oculto)
    else:
        ejecutar_extraccion_cotizaciones(modo_headless=modo_oculto)
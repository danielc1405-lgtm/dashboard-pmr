import os
import re
import sys
import json
import time
import random
import datetime
import traceback
import urllib.parse
import requests
from playwright.sync_api import sync_playwright
import gspread
from google.oauth2.service_account import Credentials

SHEET_ID = "10jrOsS054n0atMk8GxQilkXqm6LjsnrwPOZnSx8iDek"
PORTAL_URL = "https://siniestros.bbva.mx/refaccionarias/"

# Exactamente las 32 columnas de tu hoja BD_COTIZACIONES (1 sola columna Link_Referencia)
ENCABEZADOS_COT = [
    "ID_Cotizacion", "Fecha_Extraccion", "Siniestro", "Cotizacion_No",
    "Marca", "Vehiculo", "Modelo_Ano", "VIN", "Taller", "Ciudad", "Estado", "Fecha_Fin",
    "Partida_Idx", "Cantidad", "Descripcion_Portal", "Busqueda_Sugerida",
    "Precio_Original", "Precio_No_Original", "Precio_Generica", "Precio_Historial",
    "Flete_Estimado", "Fuente_Seleccionada", "Origen_Portal", "Costo_Base",
    "Margen_Pct", "Precio_Sugerido", "Precio_Libre", "Precio_Final_Enviar",
    "Codigo_Hub", "Link_Referencia", "Validar_Envio", "Estatus_Cotizacion"
]

# Diccionario ampliado con todas las abreviaturas reales detectadas en el portal
DICCIONARIO_BASE = {
    "FACIA": "FASCIA",
    "DEL.": "DELANTERA", "DEL": "DELANTERA", "DL.": "DELANTERA", "DL": "DELANTERA",
    "TRA.": "TRASERA", "TRA": "TRASERA", "TRAS.": "TRASERA", "TRAS": "TRASERA",
    "IZQ.": "IZQUIERDA", "IZQ": "IZQUIERDA",
    "DER.": "DERECHA", "DER": "DERECHA", "D.": "DERECHA",
    "SOP.": "SOPORTE", "SOP": "SOPORTE",
    "CEN.": "CENTRAL", "CEN": "CENTRAL",
    "SUP.": "SUPERIOR", "SUP": "SUPERIOR", "SP.": "SUPERIOR", "SP": "SUPERIOR",
    "INF.": "INFERIOR", "INF": "INFERIOR",
    "EXT.": "EXTERIOR", "EXT": "EXTERIOR",
    "INT.": "INTERIOR", "INT": "INTERIOR",
    "PTA.": "PUERTA", "PTA": "PUERTA", "PUER.": "PUERTA", "PUER": "PUERTA",
    "SALP.": "SALPICADERA", "SALP": "SALPICADERA",
    "MOLD.": "MOLDURA", "MOLD": "MOLDURA",
    "ANTIN.": "ANTINIEBLA", "ANITIN.": "ANTINIEBLA", "ANTIN": "ANTINIEBLA", "ANITIN": "ANTINIEBLA",
    "INTEG.": "", "INTEG": "", "CPL.": "", "CPL": "",
    "BISAG.": "BISAGRA", "BISAG": "BISAGRA",
    "REC.": "RECUBRIMIENTO", "REC": "RECUBRIMIENTO",
    "BRAZ.": "BRAZO", "BRAZ": "BRAZO",
    "SUSP.": "SUSPENSION", "SUSP": "SUSPENSION",
    "ABSORBED.": "ABSORBEDOR", "ABSORBED": "ABSORBEDOR", "ABSORB.": "ABSORBEDOR", "ABSORB": "ABSORBEDOR",
    "DIRECC.": "DIRECCIONAL", "DIRECC": "DIRECCIONAL",
    "LIMPIAPARAB.": "LIMPIAPARABRISAS", "LIMPIAPARAB": "LIMPIAPARABRISAS",
    "TRAVES.": "TRAVESANO", "TRAVES": "TRAVESANO",
    "FRONT.": "FRONTAL", "FRONT": "FRONTAL"
}

def conectar_sheets():
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    credenciales = Credentials.from_service_account_file('credentials.json', scopes=scopes)
    cliente = gspread.authorize(credenciales)
    return cliente.open_by_key(SHEET_ID)

def cargar_configuracion_y_exclusiones(doc):
    """Carga credenciales, diccionario extra, estados excluidos (DURANGO) y talleres AUTO SURTIDO."""
    config = {
        "MULTI_USER": "PMA5816",
        "MULTI_PASS": "Pmroct1.",
        "TC_USD": 20.50,
        "GEMINI_API_KEY": "",
        "ESTADOS_EXCLUIDOS": ["DURANGO", "DGO"],
        "TALLERES_AUTOSURTIDO": set(),
        "DICCIONARIO_EXTRA": {}
    }
    # 1. Leer BD_CONFIG_BOTS
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
                elif k == "GEMINI_API_KEY" and v:
                    config["GEMINI_API_KEY"] = v
                elif k == "ESTADOS_EXCLUIDOS" and v:
                    config["ESTADOS_EXCLUIDOS"] = [x.strip().upper() for x in v.split(",") if x.strip()]
                elif k.startswith("ABREV_") and v:
                    config["DICCIONARIO_EXTRA"][k.replace("ABREV_", "").strip()] = v.upper()
    except Exception:
        pass

    # 2. Leer BD_TALLERES para detectar talleres marcados como AUTO SURTIDO
    try:
        ws_t = doc.worksheet("BD_TALLERES")
        datos_t = ws_t.get_all_values()
        if len(datos_t) > 1:
            for r_t in datos_t[1:]:
                fila_str = " ".join([str(c).upper() for c in r_t])
                nombre_t = str(r_t[0]).strip().upper() if r_t else ""
                if nombre_t and ("AUTO SURTIDO" in fila_str or "AUTOSURTIDO" in fila_str or "(DGO)" in nombre_t):
                    config["TALLERES_AUTOSURTIDO"].add(nombre_t)
    except Exception:
        pass

    return config

def es_siniestro_excluido(ciudad, estado, regional, taller, cfg):
    """Devuelve (True, motivo) si pertenece a Durango o a un taller Auto Surtido."""
    t_up = str(taller).strip().upper()
    loc_up = f"{ciudad} {estado} {regional} {t_up}".upper()

    for est_ex in cfg.get("ESTADOS_EXCLUIDOS", ["DURANGO", "DGO"]):
        if est_ex and (est_ex in loc_up or f"({est_ex})" in t_up):
            return True, f"Plaza excluida ({est_ex})"

    for t_auto in cfg.get("TALLERES_AUTOSURTIDO", set()):
        if t_auto and (t_auto in t_up or t_up in t_auto):
            return True, f"Taller Auto Surtido ({taller})"

    return False, ""

def limpiar_modelo_comercial(marca, vehiculo_raw, ano):
    """Elimina códigos de equipamiento de aseguradora (2.0L, ZEN, AA, EE, STD, 4P, etc.)."""
    v = str(vehiculo_raw).upper()
    m = str(marca).upper().strip()
    if "NUEVO J" in v or "JETTA" in v:
        return "JETTA"
    if "SEDAN" in v and "VOLKSWAGEN" in v:
        try:
            if int(ano) >= 2014: return "VENTO"
        except:
            pass
        return "SEDAN"

    v = re.sub(r'\b\d+\.\d+\s*[LT]?\b', ' ', v)
    v = re.sub(r'["\'\.]', ' ', v)
    v = v.replace(m, ' ')
    basura = [
        r'\b\d+\s*CIL\b', r'\bAA\b', r'\bEE\b', r'\bSTD\b', r'\bESTANDAR\b',
        r'\bAUT\b', r'\bAUTOMATICO\b', r'\b\d+P\b', r'\b\d+PTS\b', r'\bCA\b', r'\bMP3\b',
        r'\bCD\b', r'\bBA\b', r'\bABS\b', r'\bPICKUP\b', r'\bPACK\b', r'\bEX\b', r'\bLX\b',
        r'\bZEN\b', r'\bADVANCE\b', r'\bHB\b', r'\bSEDAN\b', r'\bEL\b', r'\bNUEVO\b',
        r'\bC\b', r'\b4\b', r'\b5\b'
    ]
    for b in basura:
        v = re.sub(b, ' ', v)
    v = re.sub(r'\s+', ' ', v).strip()
    palabras = v.split()
    return " ".join(palabras[:2]) if palabras else ""

def expandir_descripcion(desc_raw, marca, vehiculo, ano, dicc_extra=None):
    """Traduce las abreviaturas del portal y une con el modelo comercial limpio."""
    texto_orig = str(desc_raw).upper().strip()
    dicc = DICCIONARIO_BASE.copy()
    if dicc_extra:
        dicc.update(dicc_extra)

    texto = re.sub(r'\.(?=[A-Z])', '. ', texto_orig)
    palabras = texto.split()
    traducidas = []
    for pal in palabras:
        p_s = pal.rstrip('.')
        # En Multiasistencia "I." o "I" siempre es IZQUIERDA (inferior siempre viene como "INF.")
        if pal in ["I.", "I"]:
            traducidas.append("IZQUIERDA")
        elif pal in ["D.", "D"]:
            traducidas.append("DERECHA")
        elif pal in dicc:
            if dicc[pal]: traducidas.append(dicc[pal])
        elif p_s in dicc:
            if dicc[p_s]: traducidas.append(dicc[p_s])
        else:
            traducidas.append(p_s)

    frase_pieza = re.sub(r'\s+', ' ', " ".join(traducidas)).strip()
    marca_clean = str(marca).upper().strip()
    mod_clean = limpiar_modelo_comercial(marca_clean, vehiculo, ano)
    return f"{frase_pieza} {marca_clean} {mod_clean} {ano}".strip()

def calcular_fecha_habiles(dias_habiles=7):
    meses_p = {1:'ENE', 2:'FEB', 3:'MAR', 4:'ABR', 5:'MAY', 6:'JUN', 7:'JUL', 8:'AGO', 9:'SEP', 10:'OCT', 11:'NOV', 12:'DIC'}
    tz_mx = datetime.timezone(datetime.timedelta(hours=-6))
    fecha = datetime.datetime.now(tz_mx).date()
    agregados = 0
    while agregados < dias_habiles:
        fecha += datetime.timedelta(days=1)
        if fecha.weekday() < 5:
            agregados += 1
    while fecha.weekday() >= 5:
        fecha += datetime.timedelta(days=1)
    return f"{fecha.day:02d} {meses_p[fecha.month]} {fecha.year}"

def estimar_flete(descripcion, ciudad, estado):
    loc_str = f"{ciudad} {estado}".upper()
    if any(k in loc_str for k in ["MONTERREY", "APODACA", "SAN NICOLAS", "GUADALUPE", "SANTA CATARINA", "ESCOBEDO", "SAN PEDRO", "NUEVO LEON"]):
        return 0.0
    es_reg = any(k in loc_str for k in ["SALTILLO", "REYNOSA", "MATAMOROS", "NUEVO LAREDO", "TORREON", "TAMPICO", "CIUDAD VICTORIA", "CD VICTORIA", "COAHUILA", "TAMAULIPAS"])
    d = str(descripcion).upper()
    if any(k in d for k in ["COFRE", "PUERTA", "QUINTA", "CAJUELA", "COSTADO", "PUENTE", "PARABRISAS", "MEDALLON"]):
        return 750.0 if es_reg else 1200.0
    elif any(k in d for k in ["FACIA", "FASCIA", "SALPICADERA", "FARO", "RADIADOR", "CONDENSADOR", "PARRILLA", "ALMA", "MARCO"]):
        return 450.0 if es_reg else 650.0
    else:
        return 300.0 if es_reg else 380.0

def buscar_precios_playwright(page_buscador, query, desc_raw, vin, tc_usd=20.50, gemini_key=""):
    """
    Usa el navegador real de Playwright para buscar en Mercado Libre MX y eBay Motors,
    extrayendo precios reales y el LINK DIRECTO al anuncio del producto.
    """
    precios_orig, precios_noorig, precios_gen = [], [], []
    mejor_link = ""
    fuente_ganadora = "MAN"

    # Palabras que indican que un resultado es un accesorio menor cuando buscamos una pieza grande
    d_up = str(desc_raw).upper()
    palabras_excluir = []
    if ("PUERTA" in d_up or "PTA" in d_up) and not any(x in d_up for x in ["MOLD", "BISAG", "MANIJA"]):
        palabras_excluir = ["MANIJA", "MOLDURA", "EMPAQUE", "HULE", "BISAGRA", "CERRADURA", "CHAPA", "ELEVADOR", "BOCINA"]
    elif "FACIA" in d_up and not any(x in d_up for x in ["SOP", "GUIA", "REJILLA", "MOLD", "TAPA", "ALMA", "ABSORB"]):
        palabras_excluir = ["SOPORTE", "GUIA", "GRAPA", "TAPA", "MOLDURA", "REFLEJANTE", "CUARTO"]
    elif "COFRE" in d_up and not any(x in d_up for x in ["BISAG", "CERRADURA", "JUNTA"]):
        palabras_excluir = ["BISAGRA", "CHAPA", "CERRADURA", "AMORTIGUADOR", "VARILLA", "EMBLEMA"]
    elif "FARO" in d_up and "NIEBLA" not in query:
        palabras_excluir = ["FOCO", "BULBO", "BALASTRA", "CONECTOR", "ARNES", "SOPORTE"]

    # 1. CONSULTA EN MERCADO LIBRE CON NAVEGADOR REAL CHROMIUM
    try:
        url_ml = f"https://listado.mercadolibre.com.mx/{urllib.parse.quote(query.replace(' ', '-'))}"
        page_buscador.goto(url_ml, timeout=15000, wait_until="domcontentloaded")
        time.sleep(1.2)

        items_ml = page_buscador.evaluate("""
            () => {
                let resultados = [];
                let cards = Array.from(document.querySelectorAll('li.ui-search-layout__item, div.poly-card, div.ui-search-result__wrapper'));
                for (let c of cards.slice(0, 14)) {
                    let a = c.querySelector('a.poly-component__title, a.ui-search-item__group__element, a.ui-search-link, a');
                    let titEl = c.querySelector('.poly-component__title, .ui-search-item__title, h2, h3');
                    let priceEl = c.querySelector('.andes-money-amount__fraction');
                    if (a && priceEl) {
                        let href = a.getAttribute('href') || '';
                        let titulo = (titEl ? titEl.textContent : a.textContent).trim();
                        let precioTxt = priceEl.textContent.replace(/[^0-9]/g, '');
                        let textoCompleto = c.innerText || '';
                        if (precioTxt && Number(precioTxt) > 180) {
                            resultados.push({
                                titulo: titulo.toUpperCase(),
                                precio: Number(precioTxt),
                                link: href.split('#')[0].split('?')[0],
                                usado: textoCompleto.toUpperCase().includes('USADO') || titulo.toUpperCase().includes('USADO') || titulo.toUpperCase().includes('SEMINUEV') || titulo.toUpperCase().includes('YONKE')
                            });
                        }
                    }
                }
                return resultados;
            }
        """)

        for it in items_ml:
            tit = it['titulo']
            if any(ex in tit for ex in palabras_excluir):
                continue
            p = float(it['precio'])
            es_orig = any(k in tit for k in ["ORIGINAL", "OEM", "GENUINO", "GENUINA", "AGENCIA"])
            if it['usado']:
                precios_noorig.append((p, it['link'], "ML"))
            elif es_orig:
                precios_orig.append((p, it['link'], "ML"))
            else:
                precios_gen.append((p, it['link'], "ML"))
    except Exception:
        pass

    # 2. CONSULTA EN EBAY MOTORS (EE.UU.) CON NAVEGADOR REAL CHROMIUM
    try:
        url_eb = f"https://www.ebay.com/sch/i.html?_nkw={urllib.parse.quote(query)}&_sacat=6030"
        page_buscador.goto(url_eb, timeout=15000, wait_until="domcontentloaded")
        time.sleep(1.2)

        items_eb = page_buscador.evaluate("""
            () => {
                let resultados = [];
                let items = Array.from(document.querySelectorAll('li.s-item'));
                for (let it of items.slice(0, 12)) {
                    let titEl = it.querySelector('.s-item__title');
                    let priceEl = it.querySelector('.s-item__price');
                    let linkEl = it.querySelector('a.s-item__link');
                    if (titEl && priceEl && linkEl) {
                        let titulo = titEl.textContent.trim();
                        if (titulo.toLowerCase().includes('shop on ebay')) continue;
                        let rawPrice = priceEl.textContent.trim();
                        let href = linkEl.getAttribute('href') || '';
                        let infoTxt = it.innerText || '';
                        resultados.push({
                            titulo: titulo.toUpperCase(),
                            rawPrice: rawPrice,
                            link: href.split('?')[0],
                            info: infoTxt.toUpperCase()
                        });
                    }
                }
                return resultados;
            }
        """)

        for it in items_eb:
            tit = it['titulo']
            if any(ex in tit for ex in palabras_excluir):
                continue
            m_num = re.search(r'([0-9]{1,4}(?:,[0-9]{3})*(?:\.[0-9]{2})?)', it['rawPrice'])
            if not m_num:
                continue
            val = float(m_num.group(1).replace(',', ''))
            es_mxn = ("MXN" in it['rawPrice'].upper() or "MEX" in it['rawPrice'].upper() or val > 900)
            p_mxn = round(val) if es_mxn else round(val * tc_usd)
            if p_mxn < 250:
                continue

            info_up = it['info']
            es_usado = any(k in info_up for k in ["PRE-OWNED", "USED", "USADO", "SEMINUEVO"])
            es_orig = any(k in tit for k in ["OEM", "GENUINE", "FACTORY", "ORIGINAL"])
            if es_usado:
                precios_noorig.append((p_mxn, it['link'], "EB"))
            elif es_orig:
                precios_orig.append((p_mxn, it['link'], "EB"))
            else:
                precios_gen.append((p_mxn, it['link'], "EB"))
    except Exception:
        pass

    # 3. RESPALDO CON GEMINI SEARCH GROUNDING SI NO HUBO RESULTADOS Y HAY API KEY
    if not (precios_orig or precios_noorig or precios_gen) and gemini_key:
        try:
            url_gem = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
            prompt_g = (
                f"Cotiza en México/EEUU la refacción automotriz '{query}' (VIN: {vin}). "
                f"Devuelve SOLO un JSON exacto con claves: "
                f'{{"orig": precio_mxn_original_entero, "semi": precio_mxn_usada_entero, "gen": precio_mxn_generica_entero, "link": "url_directa_compra"}}'
            )
            payload = {
                "contents": [{"parts": [{"text": prompt_g}]}],
                "tools": [{"google_search": {}}]
            }
            r_g = requests.post(url_gem, json=payload, timeout=12)
            if r_g.status_code == 200:
                txt_g = r_g.json()["candidates"][0]["content"]["parts"][0]["text"]
                m_j = re.search(r'\{.*\}', txt_g, re.DOTALL)
                if m_j:
                    d_j = json.loads(m_j.group(0))
                    if d_j.get("orig", 0) > 0: precios_orig.append((float(d_j["orig"]), d_j.get("link", ""), "ML"))
                    if d_j.get("semi", 0) > 0: precios_noorig.append((float(d_j["semi"]), d_j.get("link", ""), "ML"))
                    if d_j.get("gen", 0) > 0: precios_gen.append((float(d_j["gen"]), d_j.get("link", ""), "ML"))
        except Exception:
            pass

    def procesar_bucket(lista_tuplas):
        if not lista_tuplas:
            return 0, "", ""
        ordenadas = sorted(lista_tuplas, key=lambda x: x[0])
        top = ordenadas[:3]
        prom = round(sum(x[0] for x in top) / len(top))
        mejor_url = ordenadas[0][1]
        mejor_src = ordenadas[0][2]
        return prom, mejor_url, mejor_src

    p_orig, url_orig, src_orig = procesar_bucket(precios_orig)
    p_noorig, url_noorig, src_noorig = procesar_bucket(precios_noorig)
    p_gen, url_gen, src_gen = procesar_bucket(precios_gen)

    # Elegir el link directo real al producto correspondiente a la mejor opción encontrada
    if p_gen > 0:
        mejor_link = url_gen
        fuente_ganadora = src_gen
    elif p_noorig > 0:
        mejor_link = url_noorig
        fuente_ganadora = src_noorig
    elif p_orig > 0:
        mejor_link = url_orig
        fuente_ganadora = src_orig
    else:
        mejor_link = f"https://listado.mercadolibre.com.mx/{urllib.parse.quote(query.replace(' ', '-'))}"
        fuente_ganadora = "MAN"

    return p_orig, p_noorig, p_gen, mejor_link, fuente_ganadora

def obtener_ws_cotizaciones(doc):
    try:
        ws = doc.worksheet("BD_COTIZACIONES")
        enc_actuales = ws.row_values(1)
        if not enc_actuales or len(enc_actuales) != len(ENCABEZADOS_COT):
            ws.update(range_name='A1', values=[ENCABEZADOS_COT], value_input_option='USER_ENTERED')
    except Exception:
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
                    if c > 0:
                        mapa[f"{str(r[3]).upper()[:12]}_{str(r[2]).upper()[:10]}"] = c
                except Exception:
                    pass
    except Exception:
        pass
    return mapa

def abrir_menu_cotizaciones(page):
    for f in [page.main_frame] + page.frames:
        try:
            if f.evaluate("() => typeof submitForm === 'function'"):
                f.evaluate("submitForm('main_action.do','quotation_list_action.do')")
                return True
        except Exception:
            pass
    for f in [page.main_frame] + page.frames:
        try:
            loc = f.locator("a:has-text('Cotizaciones'), td:has-text('Cotizaciones'), [onclick*='quotation_list_action']")
            if loc.count() > 0:
                loc.first.click(timeout=5000)
                return True
        except Exception:
            pass
    raise RuntimeError("No se encontró el menú 'Cotizaciones'.")

def obtener_frame_derecho(page, espera_seg=10):
    fin = time.time() + espera_seg
    while time.time() < fin:
        f = page.frame(name="middleFrameRight")
        if f:
            return f
        for cand in page.frames:
            try:
                if "middleFrameRight" in (cand.name or "") or cand.locator("a.cvi, select[name='statusPart']").count() > 0:
                    return cand
            except Exception:
                pass
        time.sleep(0.5)
    return page.main_frame

def verificar_headless_seguro(modo_headless):
    if not modo_headless and sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
        print("⚠️ [AVISO] Servidor Cloud sin monitor físico. Usando modo Oculto (Headless)...")
        return True
    return modo_headless

def ejecutar_extraccion_cotizaciones(modo_headless=True):
    print("=== INICIANDO EXTRACCIÓN INTELIGENTE DE COTIZACIONES ===")
    modo_headless = verificar_headless_seguro(modo_headless)

    try:
        doc = conectar_sheets()
        cfg = cargar_configuracion_y_exclusiones(doc)
        ws_cot = obtener_ws_cotizaciones(doc)
        mapa_hist = cargar_mapa_historial(doc)

        # Limpiar automáticamente filas corruptas previas (desfasadas o de Durango)
        filas_todas = ws_cot.get_all_values()
        filas_sanas = [ENCABEZADOS_COT]
        existentes = set()
        if len(filas_todas) > 1:
            for r in filas_todas[1:]:
                if len(r) >= 32:
                    est_cot = str(r[31]).strip().upper()
                    ciu_r, edo_r, tal_r = str(r[9]), str(r[10]), str(r[8])
                    excluido, _ = es_siniestro_excluido(ciu_r, edo_r, "", tal_r, cfg)
                    # Conservar solo filas válidas que no sean de Durango ni tengan "FALSE" en Estatus
                    if not excluido and est_cot in ["PENDIENTE", "ENVIADA PORTAL"] and (float(r[16] or 0) > 0 or float(r[17] or 0) > 0 or float(r[18] or 0) > 0 or est_cot == "ENVIADA PORTAL"):
                        filas_sanas.append(r[:32])
                        existentes.add(f"{r[2]}_{r[12]}_{r[14]}")
            if len(filas_sanas) != len(filas_todas):
                ws_cot.clear()
                ws_cot.update(range_name='A1', values=filas_sanas, value_input_option='USER_ENTERED')
                print(f"🧹 Se depuraron {len(filas_todas) - len(filas_sanas)} filas antiguas (Durango / sin precio / desfasadas).")

        print(f"-> Estados excluidos configurados: {cfg['ESTADOS_EXCLUIDOS']}")
        print(f"-> Talleres Auto Surtido detectados en BD_TALLERES: {len(cfg['TALLERES_AUTOSURTIDO'])}")
    except Exception as e_sh:
        print(f"❌ [ERROR GOOGLE SHEETS]: {e_sh}")
        traceback.print_exc()
        return

    nuevas = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=modo_headless)
        ctx = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        page = ctx.new_page()
        page_buscador = ctx.new_page()  # Segunda pestaña real para buscar en Mercado Libre y eBay sin bloqueo 403
        page.on("dialog", lambda d: d.accept())

        try:
            print(f"-> Conectando a Multiasistencia con usuario {cfg['MULTI_USER']}...")
            page.goto(PORTAL_URL, timeout=45000)
            page.fill("input[type='text']", cfg["MULTI_USER"])
            page.fill("input[type='password']", cfg["MULTI_PASS"])
            page.click("input[value='Aceptar'], button:has-text('Aceptar'), input[type='submit']")
            time.sleep(3)

            abrir_menu_cotizaciones(page)
            time.sleep(3.5)

            frame = obtener_frame_derecho(page, espera_seg=12)

            # Extraer siniestros junto con su columna Regional desde la tabla inicial
            siniestros = frame.evaluate("""
                () => {
                    let lista = [];
                    let links = Array.from(document.querySelectorAll('a.cvi, a[href*="showDetail"]'));
                    for (let a of links) {
                        let href = a.getAttribute('href') || '';
                        let txt = a.textContent.trim();
                        if (href.includes('showDetail') && txt.length >= 5) {
                            let tr = a.closest('tr');
                            let tds = tr ? Array.from(tr.querySelectorAll('td')) : [];
                            let regional = tds[5] ? tds[5].textContent.trim() : '';
                            lista.push({ siniestro: txt, js: href, regional: regional });
                        }
                    }
                    return lista;
                }
            """)
            print(f"-> Siniestros en bandeja: {len(siniestros)}")

            for idx, item in enumerate(siniestros):
                num_sin = item['siniestro']
                reg_sin = item.get('regional', '')

                # FILTRO NIVEL 1: Saltar Durango desde la lista principal sin siquiera abrirlo
                ex_pre, motivo_pre = es_siniestro_excluido("", "", reg_sin, "", cfg)
                if ex_pre:
                    print(f"[{idx+1}/{len(siniestros)}] ⏭️ Saltando Siniestro {num_sin} ({motivo_pre}).")
                    continue

                print(f"\n[{idx+1}/{len(siniestros)}] Abriendo Siniestro {num_sin} (Regional: {reg_sin})...")
                try:
                    frame = obtener_frame_derecho(page)
                    frame.evaluate(item['js'].replace("javascript:", ""))
                    time.sleep(2.2)

                    frame = obtener_frame_derecho(page)
                    sub_js = frame.evaluate("""
                        () => {
                            let a = document.querySelector('a.cvi, a[href*="showDetail"]');
                            return a ? a.getAttribute('href') : '';
                        }
                    """)
                    if not sub_js:
                        continue

                    frame.evaluate(sub_js.replace("javascript:", ""))
                    time.sleep(2.5)

                    frame = obtener_frame_derecho(page)
                    # Regex corregido para soportar comillas dobles dentro de displayTool(event, 'VOLKSWAGEN "EL NUEVO JETTA"')
                    detalle = frame.evaluate(r"""
                        () => {
                            function fullTxt(el) {
                                if (!el) return '';
                                let onm = el.getAttribute('onmouseover') || '';
                                let m = onm.match(/displayTool\s*\(\s*event\s*,\s*'([^']*)'\s*\)/i) ||
                                        onm.match(/displayTool\s*\(\s*event\s*,\s*"([^"]*)"\s*\)/i);
                                if (m && m[1]) return m[1].replace(/[\s\xA0]+/g, ' ').trim();
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

                    # FILTRO NIVEL 2: Verificar si el Taller es Auto Surtido o Ciudad/Estado es Durango
                    ex_det, motivo_det = es_siniestro_excluido(
                        detalle.get('ciudad', ''), detalle.get('estado', ''), reg_sin, detalle.get('taller', ''), cfg
                    )
                    if ex_det:
                        print(f"  ⏭️ Ignorando Siniestro {num_sin}: {motivo_det}.")
                        abrir_menu_cotizaciones(page)
                        time.sleep(2)
                        continue

                    piezas_lista = detalle.get('piezas', [])
                    print(f"  -> Auto: {detalle.get('marca','')} {detalle.get('vehiculo','')} ({detalle.get('modelo','')}) | Taller: {detalle.get('taller','')} ({detalle.get('ciudad','')}) | Piezas: {len(piezas_lista)}")

                    ahora = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-6))).strftime("%Y-%m-%d %H:%M")
                    for pza in piezas_lista:
                        llave_u = f"{num_sin}_{pza['idx']}_{pza['descripcion']}"
                        if llave_u in existentes:
                            print(f"     [Ya en bandeja] Partida #{pza['idx']+1}: {pza['descripcion']}")
                            continue

                        q = expandir_descripcion(
                            pza['descripcion'], detalle.get('marca', ''), detalle.get('vehiculo', ''), detalle.get('modelo', ''), cfg.get("DICCIONARIO_EXTRA", {})
                        )
                        print(f"     🔎 Buscando: '{q}'...")
                        p_orig, p_noorig, p_gen, link_directo, fuente_det = buscar_precios_playwright(
                            page_buscador, q, pza['descripcion'], detalle.get('vin', ''), cfg.get("TC_USD", 20.50), cfg.get("GEMINI_API_KEY", "")
                        )
                        p_hist = mapa_hist.get(f"{pza['descripcion'][:12].upper()}_{detalle.get('vehiculo','')[:10].upper()}", 0.0)
                        flete = estimar_flete(pza['descripcion'], detalle.get('ciudad', ''), detalle.get('estado', ''))

                        if p_gen > 0:
                            costo = p_gen
                            origen = "NO ORIGINAL"
                        elif p_noorig > 0:
                            costo = p_noorig
                            origen = "SEMINUEVA"
                        elif p_orig > 0:
                            costo = p_orig
                            origen = "ORIGINAL"
                        else:
                            costo = p_hist
                            origen = "NO ORIGINAL"
                            if p_hist > 0:
                                fuente_det = "LOC"

                        sug = round((costo + flete) * 1.35) if costo > 0 else 0
                        print(f"        💰 Orig: ${p_orig} | Semi: ${p_noorig} | Gen: ${p_gen} | Sugerido: ${sug} ({fuente_det})")

                        # Exactamente 32 valores alineados con ENCABEZADOS_COT
                        nuevas.append([
                            f"COT-{num_sin}-{pza['idx']+1}", ahora, num_sin, "1",
                            detalle.get('marca', '').upper(), detalle.get('vehiculo', '').upper(), detalle.get('modelo', ''), detalle.get('vin', ''),
                            detalle.get('taller', ''), detalle.get('ciudad', ''), detalle.get('estado', ''), detalle.get('fecha_fin', ''),
                            pza['idx'], pza['cantidad'], pza['descripcion'], q,
                            p_orig, p_noorig, p_gen, p_hist,
                            flete, fuente_det, origen, costo,
                            35, sug, 0, sug,
                            f"HUB{fuente_det}{random.randint(100,999)}", link_directo, "FALSE", "PENDIENTE"
                        ])

                    abrir_menu_cotizaciones(page)
                    time.sleep(2.2)
                except Exception as e_sin:
                    print(f"  ❌ [ERROR en Siniestro {num_sin}]: {e_sin}")
                    try:
                        abrir_menu_cotizaciones(page)
                        time.sleep(2)
                    except Exception:
                        pass
        finally:
            browser.close()

    if nuevas:
        ws_cot.append_rows(nuevas, value_input_option='USER_ENTERED')
        print(f"\n✅ {len(nuevas)} partidas cotizadas y guardadas en BD_COTIZACIONES (sin Durango ni Auto Surtido).")
    else:
        print("\nℹ️ Proceso finalizado sin partidas nuevas por agregar.")

def ejecutar_envio_cotizaciones(modo_headless=True):
    print("=== INICIANDO ENVÍO DE COTIZACIONES AL PORTAL ===")
    modo_headless = verificar_headless_seguro(modo_headless)

    try:
        doc = conectar_sheets()
        cfg = cargar_configuracion_y_exclusiones(doc)
        ws_cot = obtener_ws_cotizaciones(doc)
        datos = ws_cot.get_all_values()
        if len(datos) <= 1:
            print("⚠️ BD_COTIZACIONES está vacía.")
            return
    except Exception as e_sh:
        print(f"❌ [ERROR GOOGLE SHEETS]: {e_sh}")
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
    for r_num, r in enumerate(datos[1:], start=2):
        if len(r) <= idx_est:
            continue
        if str(r[idx_val]).strip().upper() in ["TRUE", "SI", "1", "VERDADERO"] and str(r[idx_est]).strip().upper() == "PENDIENTE":
            try:
                p_int = int(round(float(str(r[idx_fin]).replace('$', '').replace(',', '').strip())))
            except Exception:
                p_int = 0
            if p_int > 0:
                por_enviar.setdefault(str(r[idx_sin]).strip(), []).append({
                    'gs_row': r_num,
                    'partida_idx': int(r[idx_pza]),
                    'origen_txt': str(r[idx_ori]).strip().upper(),
                    'precio_int': str(p_int),
                    'codigo_hub': re.sub(r'[^A-Za-z0-9]', '', str(r[idx_cod]).strip().upper())[:20]
                })

    if not por_enviar:
        print("⚠️ No hay partidas validadas con precio mayor a $0 para enviar.")
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
            page.click("input[value='Aceptar'], button:has-text('Aceptar'), input[type='submit']")
            time.sleep(3)

            abrir_menu_cotizaciones(page)
            time.sleep(3.5)

            for sin, items in por_enviar.items():
                try:
                    print(f"-> Abriendo Siniestro {sin} para inyectar {len(items)} partida(s)...")
                    frame = obtener_frame_derecho(page)
                    link = frame.locator(f"a.cvi:has-text('{sin}'), a[href*='showDetail']:has-text('{sin}')")
                    if link.count() == 0:
                        continue
                    frame.evaluate(link.first.get_attribute("href").replace("javascript:", ""))
                    time.sleep(2.5)

                    frame = obtener_frame_derecho(page)
                    frame.evaluate(frame.locator("a.cvi, a[href*='showDetail']").first.get_attribute("href").replace("javascript:", ""))
                    time.sleep(2.8)

                    frame = obtener_frame_derecho(page)
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
                        print(f"   ✔ Partida #{it['partida_idx']+1} inyectada (${it['precio_int']} - {it['codigo_hub']})")
                        time.sleep(0.2)

                    btn = frame.locator("input[name='btnSubmit'][value='Grabar']")
                    if btn.count() > 0:
                        btn.first.click()
                        time.sleep(3)
                        print(f"   💾 Siniestro {sin} grabado en el portal.")
                        for it in items:
                            actualizar.append(gspread.Cell(row=it['gs_row'], col=idx_est + 1, value="ENVIADA PORTAL"))

                    abrir_menu_cotizaciones(page)
                    time.sleep(2.5)
                except Exception as e:
                    print(f"❌ [!] Error enviando {sin}: {e}")
        finally:
            browser.close()

    if actualizar:
        ws_cot.update_cells(actualizar, value_input_option='USER_ENTERED')
        print(f"\n✅ {len(actualizar)} partidas marcadas como 'ENVIADA PORTAL'.")

if __name__ == "__main__":
    oculto = False if "--visual" in sys.argv else True
    if "--enviar" in sys.argv:
        ejecutar_envio_cotizaciones(modo_headless=oculto)
    else:
        ejecutar_extraccion_cotizaciones(modo_headless=oculto)
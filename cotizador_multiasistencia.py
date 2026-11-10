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

ENCABEZADOS_COT = [
    "ID_Cotizacion", "Fecha_Extraccion", "Siniestro", "Cotizacion_No",
    "Marca", "Vehiculo", "Modelo_Ano", "VIN", "Taller", "Ciudad", "Estado", "Fecha_Fin",
    "Partida_Idx", "Cantidad", "Descripcion_Portal", "Busqueda_Sugerida",
    "Precio_Original", "Precio_No_Original", "Precio_Generica", "Precio_Historial",
    "Flete_Estimado", "Fuente_Seleccionada", "Origen_Portal", "Costo_Base",
    "Margen_Pct", "Precio_Sugerido", "Precio_Libre", "Precio_Final_Enviar",
    "Codigo_Hub", "Link_Referencia", "Validar_Envio", "Estatus_Cotizacion"
]

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

TRADUCTOR_EBAY_EN = {
    "FASCIA": "BUMPER COVER", "FACIA": "BUMPER COVER",
    "DELANTERA": "FRONT", "TRASERA": "REAR",
    "IZQUIERDA": "LEFT DRIVER SIDE", "DERECHA": "RIGHT PASSENGER SIDE",
    "SUPERIOR": "UPPER", "INFERIOR": "LOWER", "CENTRAL": "CENTER",
    "EXTERIOR": "OUTER", "INTERIOR": "INNER",
    "SALPICADERA": "FENDER", "GUARDAFANGO": "FENDER LINER",
    "COFRE": "HOOD PANEL", "PUERTA": "DOOR SHELL",
    "PARRILLA": "GRILLE", "REJILLA": "LOWER GRILLE BEZEL",
    "FARO": "HEADLIGHT LAMP", "ANTINIEBLA": "FOG LIGHT", "NIEBLA": "FOG LIGHT",
    "CALAVERA": "TAIL LIGHT LAMP", "RADIADOR": "RADIATOR", "CONDENSADOR": "AC CONDENSER",
    "MARCO": "RADIATOR SUPPORT", "ALMA": "BUMPER REINFORCEMENT",
    "ABSORBEDOR": "BUMPER ABSORBER", "SOPORTE": "BRACKET RETAINER",
    "MOLDURA": "MOLDING TRIM", "COSTADO": "QUARTER PANEL",
    "BISAGRA": "HINGE", "CERRADURA": "LATCH LOCK", "ESPEJO": "SIDE MIRROR",
    "CAJUELA": "TRUNK LID", "PARABRISAS": "WINDSHIELD", "MEDALLON": "REAR GLASS",
    "AMORTIGUADOR": "SHOCK STRUT", "BRAZO": "CONTROL ARM", "SUSPENSION": "SUSPENSION",
    "MANGUETA": "STEERING KNUCKLE", "RODAMIENTO": "WHEEL HUB BEARING",
    "BUJE": "BUSHING", "RIN": "WHEEL RIM", "LLANTA": "TIRE",
    "TAPON": "WHEEL CAP", "ESTRIBO": "ROCKER PANEL", "SPOILER": "SPOILER VALANCE",
    "TOLVA": "SPLASH SHIELD"
}

# Cadena de catálogos OEM americanos (PartsGiant / PartsNow / PartsDeal)
CATALOGOS_OEM_USA = {
    "KIA": "kiapartsnow.com",
    "HYUNDAI": "hyundaipartsdeal.com",
    "FORD": "fordpartsgiant.com",
    "CHEVROLET": "gmpartsgiant.com",
    "GMC": "gmpartsgiant.com",
    "BUICK": "gmpartsgiant.com",
    "CADILLAC": "gmpartsgiant.com",
    "NISSAN": "nissanpartsdeal.com",
    "HONDA": "hondapartsnow.com",
    "TOYOTA": "toyotapartsdeal.com",
    "MAZDA": "mazdaswag.com",
    "VOLKSWAGEN": "vw.oempartsonline.com",
    "DODGE": "moparpartsgiant.com",
    "JEEP": "moparpartsgiant.com",
    "RAM": "moparpartsgiant.com",
    "CHRYSLER": "moparpartsgiant.com",
    "SUBARU": "subarupartsdeal.com",
    "MITSUBISHI": "mitsubishipartsnow.com"
}

def conectar_sheets():
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    credenciales = Credentials.from_service_account_file('credentials.json', scopes=scopes)
    cliente = gspread.authorize(credenciales)
    return cliente.open_by_key(SHEET_ID)

def cargar_configuracion_y_exclusiones(doc):
    config = {
        "MULTI_USER": "PMA5816",
        "MULTI_PASS": "Pmroct1.",
        "TC_USD": 20.50,
        "GEMINI_API_KEY": "",
        "ESTADOS_EXCLUIDOS": ["DURANGO", "DGO"],
        "TALLERES_AUTOSURTIDO": {"MAZDA LAS TORRES"},
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
                elif k == "GEMINI_API_KEY" and v:
                    config["GEMINI_API_KEY"] = v
                elif k == "ESTADOS_EXCLUIDOS" and v:
                    config["ESTADOS_EXCLUIDOS"] = [x.strip().upper() for x in v.split(",") if x.strip()]
                elif k.startswith("ABREV_") and v:
                    config["DICCIONARIO_EXTRA"][k.replace("ABREV_", "").strip()] = v.upper()
    except Exception:
        pass

    try:
        ws_t = doc.worksheet("BD_TALLERES")
        datos_t = ws_t.get_all_values()
        if len(datos_t) > 1:
            for r_t in datos_t[1:]:
                fila_str = " ".join([str(c).upper() for c in r_t])
                nombre_t = str(r_t[0]).strip().upper() if r_t else ""
                if len(nombre_t) >= 4 and any(k in fila_str for k in ["AUTO SURTIDO", "AUTOSURTIDO", "AUTO SERVICIO", "AUTOSERVICIO"]):
                    config["TALLERES_AUTOSURTIDO"].add(nombre_t)
    except Exception:
        pass

    return config

def es_siniestro_excluido(ciudad, estado, taller, cfg):
    t_up = str(taller).strip().upper()
    c_up = str(ciudad).strip().upper()
    e_up = str(estado).strip().upper()
    loc_up = f"{c_up} {e_up}"

    for est_ex in cfg.get("ESTADOS_EXCLUIDOS", ["DURANGO", "DGO"]):
        if est_ex and (re.search(rf'\b{re.escape(est_ex)}\b', loc_up) or f"({est_ex})" in t_up):
            return True, f"Plaza excluida ({c_up or e_up})"

    if len(t_up) >= 4:
        for t_auto in cfg.get("TALLERES_AUTOSURTIDO", set()):
            if len(t_auto) >= 4 and (t_up == t_auto or t_auto in t_up or (len(t_up) >= 8 and t_up in t_auto)):
                return True, f"Taller Auto Surtido ({t_up})"

    return False, ""

def limpiar_modelo_comercial(marca, vehiculo_raw, ano):
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

    # Eliminar códigos entre paréntesis como (H) LUJO
    v = re.sub(r'\([^\)]*\)', ' ', v)
    v = re.sub(r'\b\d+\.\d+\s*[LT]?\b', ' ', v)
    v = re.sub(r'["\'\.\(\)]', ' ', v)
    v = v.replace(m, ' ')
    basura = [
        r'\b\d+\s*CIL\b', r'\bAA\b', r'\bEE\b', r'\bSTD\b', r'\bESTANDAR\b',
        r'\bAUT\b', r'\bAUTOMATICO\b', r'\b\d+P\b', r'\b\d+PTS\b', r'\bCA\b', r'\bMP3\b',
        r'\bCD\b', r'\bBA\b', r'\bABS\b', r'\bPICKUP\b', r'\bPACK\b', r'\bEX\b', r'\bLX\b',
        r'\bZEN\b', r'\bADVANCE\b', r'\bHB\b', r'\bSEDAN\b', r'\bEL\b', r'\bNUEVO\b', r'\bLUJO\b',
        r'\bCHEVROLET\b', r'\bVOLKSWAGEN\b', r'\bNISSAN\b', r'\bKIA\b', r'\bMAZDA\b', r'\bRENAULT\b', r'\bHYUNDAI\b'
    ]
    for b in basura:
        v = re.sub(b, ' ', v)

    modelos_cortos_validos = {"2", "3", "5", "6", "K3", "K4", "K5", "A1", "A3", "A4", "Q3", "Q5", "X1", "X3", "X5", "MG", "GT"}
    palabras_limpias = [w for w in v.split() if len(w) >= 3 or w in modelos_cortos_validos]
    return palabras_limpias[0] if palabras_limpias else ""

def expandir_descripcion(desc_raw, marca, vehiculo, ano, dicc_extra=None):
    texto_orig = str(desc_raw).upper().strip()
    dicc = DICCIONARIO_BASE.copy()
    if dicc_extra:
        dicc.update(dicc_extra)

    texto = re.sub(r'\.(?=[A-Z])', '. ', texto_orig)
    palabras = texto.split()
    traducidas = []
    for pal in palabras:
        p_s = pal.rstrip('.')
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

def construir_query_ebay_ingles(frase_es, marca, modelo, ano):
    palabras_en = []
    for w in frase_es.upper().split():
        if w in [marca.upper(), modelo.upper(), str(ano)]:
            continue
        if w in TRADUCTOR_EBAY_EN:
            palabras_en.append(TRADUCTOR_EBAY_EN[w])
    pieza_en = " ".join(palabras_en[:4]).strip()
    if not pieza_en:
        pieza_en = frase_es
    return f"{ano} {marca} {modelo} {pieza_en}".strip()

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

def cargar_mapa_historial_completo(doc):
    registros = []
    for nombre_h in ["BD_COMPRAS", "BD_UNIFICADA", "BD_HISTORICO"]:
        try:
            ws = doc.worksheet(nombre_h)
            datos = ws.get_all_values()
            if len(datos) <= 1:
                continue
            headers = [str(h).strip().upper() for h in datos[0]]
            i_pza = next((i for i, h in enumerate(headers) if "DESCRIP" in h or "PIEZA" in h or "REFAC" in h), -1)
            i_mod = next((i for i, h in enumerate(headers) if "MODELO" in h or "VEH" in h), -1)
            i_pre = next((i for i, h in enumerate(headers) if "COSTO" in h or "PRECIO" in h), -1)
            if i_pza >= 0 and i_pre >= 0:
                for r in datos[1:]:
                    if len(r) > max(i_pza, i_pre):
                        try:
                            val = float(str(r[i_pre]).replace('$', '').replace(',', '').strip())
                            if val > 150:
                                p_txt = str(r[i_pza]).upper().strip()
                                m_txt = str(r[i_mod]).upper().strip() if (i_mod >= 0 and len(r) > i_mod) else ""
                                registros.append((p_txt, m_txt, val))
                        except Exception:
                            pass
        except Exception:
            pass
    return registros

def buscar_en_historial(registros_hist, desc_raw, query_limpia, modelo_limpio):
    if not registros_hist:
        return 0.0
    pal_clave = query_limpia.split()[0].upper() if query_limpia else ""
    d_raw_up = str(desc_raw).upper().strip()
    precios_exactos, precios_modelo = [], []
    for p_txt, m_txt, val in registros_hist:
        if modelo_limpio and modelo_limpio in m_txt:
            if d_raw_up[:8] in p_txt or (pal_clave and pal_clave in p_txt):
                precios_exactos.append(val)
        elif d_raw_up == p_txt:
            precios_modelo.append(val)
    if precios_exactos:
        return round(sum(precios_exactos[:5]) / len(precios_exactos[:5]))
    if precios_modelo:
        return round(sum(precios_modelo[:5]) / len(precios_modelo[:5]))
    return 0.0

def buscar_precios_multimotor(page_buscador, query, query_ebay_en, marca, desc_raw, vin, tc_usd=20.50, gemini_key=""):
    """
    Busca precios en:
    1) Gemini Search Grounding (si hay API Key configurada)
    2) Catálogos OEM USA (PartsGiant / PartsNow / PartsDeal)
    3) Mercado Libre México (Directo + Metabuscador Web anti-bloqueo Cloud)
    4) eBay Motors EE.UU. (en inglés)
    """
    precios_orig, precios_noorig, precios_gen = [], [], []

    d_up = str(desc_raw).upper()
    palabras_excluir = []
    if ("PUERTA" in d_up or "PTA" in d_up) and not any(x in d_up for x in ["MOLD", "BISAG", "MANIJA"]):
        palabras_excluir = ["MANIJA", "MOLDURA", "EMPAQUE", "HULE", "BISAGRA", "CERRADURA", "CHAPA", "ELEVADOR", "BOCINA"]
    elif "FACIA" in d_up and not any(x in d_up for x in ["SOP", "GUIA", "REJILLA", "MOLD", "TAPA", "ALMA", "ABSORB"]):
        palabras_excluir = ["SOPORTE", "GUIA", "GRAPA", "TAPA", "MOLDURA", "REFLEJANTE", "CUARTO", "CHISGUETERO"]
    elif "COFRE" in d_up and not any(x in d_up for x in ["BISAG", "CERRADURA", "JUNTA"]):
        palabras_excluir = ["BISAGRA", "CHAPA", "CERRADURA", "AMORTIGUADOR", "VARILLA", "EMBLEMA"]
    elif "FARO" in d_up and "NIEBLA" not in query:
        palabras_excluir = ["FOCO", "BULBO", "BALASTRA", "CONECTOR", "ARNES", "SOPORTE"]

    def clasificar_item(titulo_up, precio_val, url_item, fuente_tag, forzar_origen=None):
        if precio_val < 220 or precio_val > 85000:
            return
        if any(ex in titulo_up for ex in palabras_excluir):
            return
        if forzar_origen == "ORIGINAL":
            precios_orig.append((precio_val, url_item, fuente_tag))
            return
        es_usado = any(k in titulo_up for k in ["USADO", "USADA", "SEMINUEV", "YONKE", "DESHUESO", "PRE-OWNED", "USED"])
        es_orig = any(k in titulo_up for k in ["ORIGINAL", "OEM", "GENUIN", "AGENCIA", "FACTORY", "PARTSGIANT", "PARTSNOW", "PARTSDEAL"])
        if es_usado:
            precios_noorig.append((precio_val, url_item, fuente_tag))
        elif es_orig:
            precios_orig.append((precio_val, url_item, fuente_tag))
        else:
            precios_gen.append((precio_val, url_item, fuente_tag))

    # --- CAPA 1: GEMINI AI SEARCH GROUNDING (SI HAY API KEY) ---
    if gemini_key:
        try:
            sitio_oem = CATALOGOS_OEM_USA.get(marca.upper(), "partsgiant.com")
            url_gem = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
            prompt_g = (
                f"Busca precios reales actuales para la refacción automotriz: '{query}' / '{query_ebay_en}' (VIN: {vin}). "
                f"Revisa Mercado Libre México, eBay Motors y catálogos OEM como {sitio_oem} (convierte USD a MXN usando {tc_usd}). "
                f"Devuelve ÚNICAMENTE un objeto JSON válido con este formato exacto: "
                f'{{"orig": precio_mxn_original_entero, "semi": precio_mxn_usada_entero, "gen": precio_mxn_generica_entero, "link": "url_directa_del_producto"}}'
            )
            payload = {
                "contents": [{"parts": [{"text": prompt_g}]}],
                "tools": [{"google_search": {}}]
            }
            r_g = requests.post(url_gem, json=payload, timeout=14)
            if r_g.status_code == 200:
                txt_g = r_g.json()["candidates"][0]["content"]["parts"][0]["text"]
                m_j = re.search(r'\{.*\}', txt_g, re.DOTALL)
                if m_j:
                    d_j = json.loads(m_j.group(0))
                    lnk_g = d_j.get("link", "")
                    if float(d_j.get("orig", 0) or 0) > 0:
                        precios_orig.append((float(d_j["orig"]), lnk_g, "AGENCIA"))
                    if float(d_j.get("semi", 0) or 0) > 0:
                        precios_noorig.append((float(d_j["semi"]), lnk_g, "ML"))
                    if float(d_j.get("gen", 0) or 0) > 0:
                        precios_gen.append((float(d_j["gen"]), lnk_g, "ML"))
        except Exception:
            pass

    # --- CAPA 2: CATÁLOGOS OEM USA (PARTSGIANT / PARTSNOW / PARTSDEAL) ---
    sitio_oem_marca = CATALOGOS_OEM_USA.get(marca.upper(), "")
    if sitio_oem_marca and len(precios_orig) == 0:
        try:
            q_oem = f"site:{sitio_oem_marca} {query_ebay_en}"
            url_oem_search = f"https://search.yahoo.com/search?p={urllib.parse.quote(q_oem)}"
            page_buscador.goto(url_oem_search, timeout=10000, wait_until="domcontentloaded")
            time.sleep(0.8)
            bloques_oem = page_buscador.evaluate("""
                () => Array.from(document.querySelectorAll('div.algo, li'))
                    .map(b => ({ txt: (b.innerText || '').toUpperCase(), href: (b.querySelector('a') ? b.querySelector('a').href : '') }))
                    .filter(x => x.txt.includes('$'))
                    .slice(0, 8)
            """)
            for bo in bloques_oem:
                lnk_o = bo['href']
                m_ru = re.search(r'/RU=([^/]+)/', lnk_o)
                if m_ru:
                    lnk_o = urllib.parse.unquote(m_ru.group(1))
                for m_usd in re.findall(r'\$\s*([0-9]{1,4}\.[0-9]{2})', bo['txt']):
                    val_usd = float(m_usd)
                    if 15 <= val_usd <= 2500:
                        clasificar_item(bo['txt'], round(val_usd * tc_usd), lnk_o, "AGENCIA", forzar_origen="ORIGINAL")
        except Exception:
            pass

    # --- CAPA 3: MERCADO LIBRE MÉXICO (DIRECTO + METABUSCADOR WEB) ---
    try:
        q_ml_web = f"site:mercadolibre.com.mx {query}"
        url_yahoo_ml = f"https://mx.search.yahoo.com/search?p={urllib.parse.quote(q_ml_web)}"
        page_buscador.goto(url_yahoo_ml, timeout=11000, wait_until="domcontentloaded")
        time.sleep(0.9)
        resultados_ml = page_buscador.evaluate("""
            () => Array.from(document.querySelectorAll('div.algo, li'))
                .map(b => {
                    let a = b.querySelector('a');
                    return { txt: (b.innerText || '').replace(/\\s+/g, ' ').toUpperCase(), href: a ? a.href : '' };
                })
                .filter(x => x.href.includes('mercadolibre.com.mx') || x.txt.includes('$'))
                .slice(0, 12)
        """)
        for rw in resultados_ml:
            link_real = rw['href']
            m_ru = re.search(r'/RU=([^/]+)/', link_real)
            if m_ru:
                link_real = urllib.parse.unquote(m_ru.group(1))
            for ph in re.findall(r'\$\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{3,5})', rw['txt']):
                clasificar_item(rw['txt'], float(ph.replace(',', '')), link_real, "ML")
    except Exception:
        pass

    # --- CAPA 4: EBAY MOTORS EE.UU. (EN INGLÉS) ---
    try:
        url_eb = f"https://www.ebay.com/sch/i.html?_nkw={urllib.parse.quote(query_ebay_en)}&_sacat=6030"
        page_buscador.goto(url_eb, timeout=11000, wait_until="domcontentloaded")
        time.sleep(0.9)
        items_eb = page_buscador.evaluate("""
            () => {
                let res = [];
                let cards = Array.from(document.querySelectorAll('li.s-item, div.s-item__wrapper'));
                for (let it of cards.slice(0, 10)) {
                    let titEl = it.querySelector('.s-item__title');
                    let priceEl = it.querySelector('.s-item__price');
                    let linkEl = it.querySelector('a.s-item__link, a');
                    if (titEl && priceEl && linkEl) {
                        let tit = titEl.textContent.trim();
                        if (tit.toLowerCase().includes('shop on ebay')) continue;
                        res.push({
                            tit: (it.innerText || '').toUpperCase(),
                            rawPrice: priceEl.textContent.trim(),
                            link: (linkEl.getAttribute('href') || '').split('?')[0]
                        });
                    }
                }
                return res;
            }
        """)
        for it in items_eb:
            m_num = re.search(r'([0-9]{1,4}(?:,[0-9]{3})*(?:\.[0-9]{2})?)', it['rawPrice'])
            if m_num:
                val = float(m_num.group(1).replace(',', ''))
                es_mxn = ("MXN" in it['rawPrice'].upper() or "MEX" in it['rawPrice'].upper() or val > 950)
                p_mxn = round(val) if es_mxn else round(val * tc_usd)
                clasificar_item(it['tit'], p_mxn, it['link'], "EB")
    except Exception:
        pass

    def procesar_bucket(lista_tuplas):
        if not lista_tuplas:
            return 0, "", ""
        ordenadas = sorted(lista_tuplas, key=lambda x: x[0])
        top = ordenadas[:3]
        prom = round(sum(x[0] for x in top) / len(top))
        return prom, ordenadas[0][1], ordenadas[0][2]

    p_orig, url_orig, src_orig = procesar_bucket(precios_orig)
    p_noorig, url_noorig, src_noorig = procesar_bucket(precios_noorig)
    p_gen, url_gen, src_gen = procesar_bucket(precios_gen)

    if p_gen > 0:
        mejor_link, fuente_ganadora = url_gen, src_gen
    elif p_noorig > 0:
        mejor_link, fuente_ganadora = url_noorig, src_noorig
    elif p_orig > 0:
        mejor_link, fuente_ganadora = url_orig, src_orig
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
        print("⚠️ [AVISO] Servidor Cloud sin monitor físico. Usando modo Oculto y activando Cámara de Evidencia...")
        return True
    return modo_headless

def ejecutar_extraccion_cotizaciones(modo_headless=True):
    print("=== INICIANDO EXTRACCIÓN INTELIGENTE DE COTIZACIONES ===")
    modo_headless = verificar_headless_seguro(modo_headless)

    try:
        doc = conectar_sheets()
        cfg = cargar_configuracion_y_exclusiones(doc)
        ws_cot = obtener_ws_cotizaciones(doc)
        registros_hist = cargar_mapa_historial_completo(doc)

        # Limpiar duplicados y filas de talleres excluidos
        filas_todas = ws_cot.get_all_values()
        filas_sanas = [ENCABEZADOS_COT]
        existentes = set()
        if len(filas_todas) > 1:
            for r in filas_todas[1:]:
                if len(r) >= 32:
                    est_cot = str(r[31]).strip().upper()
                    ciu_r, edo_r, tal_r = str(r[9]), str(r[10]), str(r[8])
                    excluido, _ = es_siniestro_excluido(ciu_r, edo_r, tal_r, cfg)
                    llave_unica = f"{str(r[2]).strip()}_{str(r[12]).strip()}"
                    if not excluido and est_cot in ["PENDIENTE", "ENVIADA PORTAL"] and llave_unica not in existentes:
                        filas_sanas.append(r[:32])
                        existentes.add(llave_unica)
            if len(filas_sanas) != len(filas_todas):
                ws_cot.clear()
                ws_cot.update(range_name='A1', values=filas_sanas, value_input_option='USER_ENTERED')
                print(f"🧹 Se eliminaron {len(filas_todas) - len(filas_sanas)} filas duplicadas o de talleres excluidos.")
    except Exception as e_sh:
        print(f"❌ [ERROR GOOGLE SHEETS]: {e_sh}")
        traceback.print_exc()
        return

    nuevas = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=modo_headless,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            locale="es-MX",
            viewport={"width": 1366, "height": 900}
        )
        page = ctx.new_page()
        page_buscador = ctx.new_page()
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

            siniestros = frame.evaluate("""
                () => {
                    let lista = [];
                    let links = Array.from(document.querySelectorAll('a.cvi, a[href*="showDetail"]'));
                    for (let a of links) {
                        let href = a.getAttribute('href') || '';
                        let txt = a.textContent.trim();
                        if (href.includes('showDetail') && txt.length >= 5) {
                            lista.push({ siniestro: txt, js: href });
                        }
                    }
                    return lista;
                }
            """)
            print(f"-> Siniestros en bandeja: {len(siniestros)}")

            for idx, item in enumerate(siniestros):
                num_sin = item['siniestro']
                print(f"\n[{idx+1}/{len(siniestros)}] Revisando interior del Siniestro {num_sin}...")
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
                        abrir_menu_cotizaciones(page)
                        time.sleep(2)
                        continue

                    frame.evaluate(sub_js.replace("javascript:", ""))
                    time.sleep(2.5)

                    frame = obtener_frame_derecho(page)
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

                    taller_real = detalle.get('taller', '')
                    ciudad_real = detalle.get('ciudad', '')
                    estado_real = detalle.get('estado', '')

                    ex_det, motivo_det = es_siniestro_excluido(ciudad_real, estado_real, taller_real, cfg)
                    if ex_det:
                        print(f"  ⏭️ Saltando {num_sin} | Taller: {taller_real} ({ciudad_real}, {estado_real}) -> {motivo_det}.")
                        abrir_menu_cotizaciones(page)
                        time.sleep(2.2)
                        continue

                    piezas_lista = detalle.get('piezas', [])
                    marca_clean = detalle.get('marca', '').upper().strip()
                    mod_comercial = limpiar_modelo_comercial(marca_clean, detalle.get('vehiculo', ''), detalle.get('modelo', ''))
                    ano_clean = detalle.get('modelo', '').strip()

                    print(f"  ✅ Cotizable | Auto: {marca_clean} {mod_comercial} ({ano_clean}) | Taller: {taller_real} ({ciudad_real}, {estado_real}) | {len(piezas_lista)} pieza(s)")

                    ahora = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-6))).strftime("%Y-%m-%d %H:%M")
                    for pza in piezas_lista:
                        llave_u = f"{num_sin}_{pza['idx']}"
                        if llave_u in existentes:
                            print(f"     [Ya en bandeja] Partida #{pza['idx']+1}: {pza['descripcion']}")
                            continue

                        q = expandir_descripcion(
                            pza['descripcion'], marca_clean, detalle.get('vehiculo', ''), ano_clean, cfg.get("DICCIONARIO_EXTRA", {})
                        )
                        q_ebay = construir_query_ebay_ingles(q, marca_clean, mod_comercial, ano_clean)
                        print(f"     🔎 [{pza['idx']+1}/{len(piezas_lista)}] MX: '{q}' | US: '{q_ebay}'...")

                        p_orig, p_noorig, p_gen, link_directo, fuente_det = buscar_precios_multimotor(
                            page_buscador, q, q_ebay, marca_clean, pza['descripcion'], detalle.get('vin', ''), cfg.get("TC_USD", 20.50), cfg.get("GEMINI_API_KEY", "")
                        )
                        p_hist = buscar_en_historial(registros_hist, pza['descripcion'], q, mod_comercial)
                        flete = estimar_flete(pza['descripcion'], ciudad_real, estado_real)

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
                        print(f"        💰 Orig: ${p_orig} | Semi: ${p_noorig} | Gen: ${p_gen} | Hist: ${p_hist} ➔ Sugerido: ${sug} ({fuente_det})")

                        nuevas.append([
                            f"COT-{num_sin}-{pza['idx']+1}", ahora, num_sin, "1",
                            marca_clean, f"{marca_clean} {mod_comercial}".strip(), ano_clean, detalle.get('vin', ''),
                            taller_real, ciudad_real, estado_real, detalle.get('fecha_fin', ''),
                            pza['idx'], pza['cantidad'], pza['descripcion'], q,
                            p_orig, p_noorig, p_gen, p_hist,
                            flete, fuente_det, origen, costo,
                            35, sug, 0, sug,
                            f"HUB{fuente_det}{random.randint(100,999)}", link_directo, "FALSE", "PENDIENTE"
                        ])
                        existentes.add(llave_u)

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
        print(f"\n✅ {len(nuevas)} partidas cotizadas con éxito en BD_COTIZACIONES.")
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
    idx_lib = headers.index("Precio_Libre") if "Precio_Libre" in headers else -1
    idx_sug = headers.index("Precio_Sugerido") if "Precio_Sugerido" in headers else -1
    idx_cod = headers.index("Codigo_Hub")
    idx_val = headers.index("Validar_Envio")
    idx_est = headers.index("Estatus_Cotizacion")

    por_enviar = {}
    for r_num, r in enumerate(datos[1:], start=2):
        if len(r) <= idx_est:
            continue
        if str(r[idx_val]).strip().upper() in ["TRUE", "SI", "1", "VERDADERO"] and str(r[idx_est]).strip().upper() == "PENDIENTE":
            def parse_m(col_i):
                if col_i < 0 or col_i >= len(r): return 0
                try: return int(round(float(str(r[col_i]).replace('$', '').replace(',', '').strip())))
                except: return 0
            # Si Precio_Libre > 0 manda sobre cualquier otro campo
            p_libre = parse_m(idx_lib)
            p_final = parse_m(idx_fin)
            p_suger = parse_m(idx_sug)
            p_int = p_libre if p_libre > 0 else (p_final if p_final > 0 else p_suger)

            if p_int > 0:
                por_enviar.setdefault(str(r[idx_sin]).strip(), {})[int(r[idx_pza])] = {
                    'gs_row': r_num,
                    'partida_idx': int(r[idx_pza]),
                    'origen_txt': str(r[idx_ori]).strip().upper(),
                    'precio_int': str(p_int),
                    'codigo_hub': re.sub(r'[^A-Za-z0-9]', '', str(r[idx_cod]).strip().upper())[:20]
                }

    if not por_enviar:
        print("⚠️ No hay partidas validadas con precio mayor a $0 para enviar.")
        return

    fecha_7d = calcular_fecha_habiles(7)
    mapa_orig = {"ORIGINAL": "42007", "NO ORIGINAL": "42008", "GENERICA": "42008", "SEMINUEVA": "42009"}
    actualizar = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=modo_headless)
        ctx = browser.new_context(viewport={"width": 1366, "height": 950})
        page = ctx.new_page()
        page.on("dialog", lambda d: (print(f"   🔔 [ALERTA PORTAL]: {d.message}"), d.accept()))

        try:
            page.goto(PORTAL_URL, timeout=45000)
            page.fill("input[type='text']", cfg["MULTI_USER"])
            page.fill("input[type='password']", cfg["MULTI_PASS"])
            page.click("input[value='Aceptar'], button:has-text('Aceptar'), input[type='submit']")
            time.sleep(3)

            abrir_menu_cotizaciones(page)
            time.sleep(3.5)

            for sin, dict_partidas in por_enviar.items():
                try:
                    print(f"-> Abriendo Siniestro {sin} para inyectar {len(dict_partidas)} partida(s)...")
                    frame = obtener_frame_derecho(page)
                    link = frame.locator(f"a.cvi:has-text('{sin}'), a[href*='showDetail']:has-text('{sin}')")
                    if link.count() == 0:
                        print(f"  ⚠️ El siniestro {sin} ya no está disponible en la bandeja de Cotizaciones.")
                        continue
                    frame.evaluate(link.first.get_attribute("href").replace("javascript:", ""))
                    time.sleep(2.5)

                    frame = obtener_frame_derecho(page)
                    frame.evaluate(frame.locator("a.cvi, a[href*='showDetail']").first.get_attribute("href").replace("javascript:", ""))
                    time.sleep(2.8)

                    frame = obtener_frame_derecho(page)
                    total_filas_portal = frame.locator("select[name='statusPart']").count()
                    print(f"   📋 Total de partidas en el pliego del portal: {total_filas_portal}")

                    # Recorrer TODAS las filas del pliego: las validadas se Aceptan ('133002') y las no validadas se Rechazan ('133003')
                    # para que validateStatus() del portal permita grabar sin bloquear el formulario.
                    for idx_fila in range(total_filas_portal):
                        sel_status = frame.locator("select[name='statusPart']").nth(idx_fila)
                        if idx_fila in dict_partidas:
                            it = dict_partidas[idx_fila]
                            cod_origen = mapa_orig.get(it['origen_txt'], "42008")
                            sel_status.select_option("133002")  # Aceptar (dispara reviewSelect nativo)
                            time.sleep(0.25)

                            # Inyectar fecha en campo visible (readonly) y oculto
                            frame.evaluate(
                                """(args) => {
                                    let fv = document.getElementById('promiseDatePart' + args.i);
                                    let fh = document.getElementById('promiseDateValue' + args.i);
                                    if (fv) { fv.removeAttribute('readonly'); fv.value = args.f; }
                                    if (fh) { fh.value = args.f; }
                                }""",
                                {"i": idx_fila, "f": fecha_7d}
                            )

                            inp_code = frame.locator("input[name='codePart']").nth(idx_fila)
                            inp_price = frame.locator("input[name='price']").nth(idx_fila)
                            sel_orig = frame.locator("select[name='origin']").nth(idx_fila)

                            inp_code.fill(it['codigo_hub'])
                            inp_price.fill(it['precio_int'])
                            sel_orig.select_option(cod_origen)  # Dispara getValueSelected nativo
                            print(f"   ✔ Partida #{idx_fila+1} ACEPTADA (${it['precio_int']} | {it['codigo_hub']} | Fecha: {fecha_7d})")
                        else:
                            sel_status.select_option("133003")  # Rechazar partida no seleccionada
                            print(f"   ⏭️ Partida #{idx_fila+1} marcada como RECHAZAR (no validada en mesa).")
                        time.sleep(0.15)

                    # Tomar foto de evidencia ANTES de presionar Grabar
                    page.screenshot(path="evidencia_antes_grabar.png", full_page=True)

                    btn = frame.locator("input[name='btnSubmit'][value='Grabar']")
                    if btn.count() > 0:
                        btn.first.click()
                        time.sleep(3.5)
                        # Tomar foto de evidencia DESPUÉS de presionar Grabar
                        page.screenshot(path="evidencia_despues_grabar.png", full_page=True)
                        print(f"   💾 Siniestro {sin} enviado y grabado en el portal (Revisa las capturas de evidencia abajo).")
                        for it in dict_partidas.values():
                            actualizar.append(gspread.Cell(row=it['gs_row'], col=idx_est + 1, value="ENVIADA PORTAL"))

                    abrir_menu_cotizaciones(page)
                    time.sleep(2.5)
                except Exception as e:
                    print(f"❌ [!] Error enviando {sin}: {e}")
                    traceback.print_exc()
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
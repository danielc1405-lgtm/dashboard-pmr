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
    "FRONT.": "FRONTAL", "FRONT": "FRONTAL",
    "EMBL.": "EMBLEMA", "CERRAD.": "CERRADURA", "REVEST.": "REVESTIMIENTO"
}

PORTALES_DEFAULT = [
    {"nombre": "RADEC", "url": "radec.com.mx", "categoria": "GENERICA"},
    {"nombre": "MERCADO LIBRE", "url": "mercadolibre.com.mx", "categoria": "TODAS"},
    {"nombre": "EBAY MOTORS", "url": "ebay.com", "categoria": "SEMINUEVA"},
    {"nombre": "PARTSOUQ", "url": "partsouq.com", "categoria": "ORIGINAL"},
    {"nombre": "PARTSLINK24", "url": "partslink24.com", "categoria": "ORIGINAL"}
]

def conectar_sheets():
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    credenciales = Credentials.from_service_account_file('credentials.json', scopes=scopes)
    cliente = gspread.authorize(credenciales)
    return cliente.open_by_key(SHEET_ID)

def cargar_configuracion_y_exclusiones(doc):
    config = {
        "MULTI_USER": "PMA5816",
        "MULTI_PASS": "PmrNov1.",
        "TC_USD": 20.50,
        "GEMINI_API_KEY": "",
        "ESTADOS_EXCLUIDOS": ["DURANGO", "DGO"],
        "TALLERES_AUTOSURTIDO": {"MAZDA LAS TORRES"},
        "DICCIONARIO_EXTRA": {},
        "PORTALES_BUSQUEDA": []
    }
    try:
        ws_cfg = doc.worksheet("BD_CONFIG_BOTS")
        filas = ws_cfg.get_all_values()
        for f in filas[1:]:
            if len(f) >= 2:
                k, v = str(f[0]).strip().upper(), str(f[1]).strip()
                nota = str(f[2]).strip().upper() if len(f) >= 3 else "TODAS"
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
                elif k.startswith("PORTAL_") and v:
                    config["PORTALES_BUSQUEDA"].append({
                        "nombre": k.replace("PORTAL_", "").strip(),
                        "url": v.lower().strip(),
                        "categoria": nota
                    })
    except Exception:
        pass

    if not config["PORTALES_BUSQUEDA"]:
        config["PORTALES_BUSQUEDA"] = PORTALES_DEFAULT

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

def es_pieza_convenio_excluida(desc_raw):
    d = str(desc_raw).upper().strip()
    if "PARABRISAS" in d and "LIMPIA" not in d and "TOLVA" not in d and "DEPOSITO" not in d:
        return True
    if re.search(r'\bLLANTA\b|\bLLANTAS\b|\bNEUMATICO\b', d):
        return True
    return False

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

    # Unificar modelos compuestos separados por espacio (ej. CX 30 -> CX-30, CR V -> CR-V, F 150 -> F-150, S 10 -> S-10)
    v = re.sub(r'\b(CX|CR|HR|BR|MX|RX|NX|UX|GX|LX|FX|QX|XT|CT|ES|IS|LS|GS|RC|LC|GLC|GLE|GLA|GLB|GLS|CLA|CLS)\s*[\-\s]?\s*([0-9A-Z]{1,3})\b', r'\1-\2', v)
    v = re.sub(r'\b([FS])\s*[\-\s]?\s*(10|150|250|350|450|550)\b', r'\1-\2', v)

    v = re.sub(r'\([^\)]*\)', ' ', v)
    v = re.sub(r'\b\d+\.\d+\s*[LT]?\b', ' ', v)
    v = re.sub(r'["\'\.\(\)]', ' ', v)
    v = v.replace(m, ' ')
    basura = [
        r'\b\d+\s*CIL\b', r'\bAA\b', r'\bEE\b', r'\bSTD\b', r'\bESTANDAR\b',
        r'\bAUT\b', r'\bAUTOMATICO\b', r'\b\d+P\b', r'\b\d+PTS\b', r'\bCA\b', r'\bMP3\b',
        r'\bCD\b', r'\bBA\b', r'\bABS\b', r'\bPICKUP\b', r'\bPACK\b', r'\bEX\b', r'\bLX\b',
        r'\bZEN\b', r'\bADVANCE\b', r'\bHB\b', r'\bSEDAN\b', r'\bEL\b', r'\bNUEVO\b', r'\bLUJO\b',
        r'\bCHEVROLET\b', r'\bVOLKSWAGEN\b', r'\bNISSAN\b', r'\bKIA\b', r'\bMAZDA\b', r'\bRENAULT\b', r'\bHYUNDAI\b', r'\bHONDA\b'
    ]
    for b in basura:
        v = re.sub(b, ' ', v)

    modelos_cortos_validos = {"2", "3", "5", "6", "K3", "K4", "K5", "A1", "A3", "A4", "Q2", "Q3", "Q5", "Q7", "X1", "X3", "X4", "X5", "MG", "GT", "J7", "T6", "T8"}
    palabras_limpias = [w for w in v.split() if len(w) >= 3 or w in modelos_cortos_validos]
    return palabras_limpias[0] if palabras_limpias else ""

def expandir_descripcion(desc_raw, marca, vehiculo, ano, dicc_extra=None):
    texto_orig = str(desc_raw).upper().strip()
    dicc = DICCIONARIO_BASE.copy()
    dicc.update({
        "REFLECTOR": "CUARTO REFLEJANTE",
        "REFLEJANTE": "CUARTO REFLEJANTE",
        "REFLEC.": "CUARTO REFLEJANTE",
        "REFLEC": "CUARTO REFLEJANTE",
        "GUARDAFANGO": "TOLVA LODERA"
    })
    if dicc_extra:
        dicc.update(dicc_extra)

    texto = re.sub(r'\.(?=[A-Z])', '. ', texto_orig)

    # 1. Reemplazar primero frases compuestas para desambiguar (ej. TOLVA SALPICADERA vs SALPICADERA)
    frases_compuestas = {
        "TOLVA SALP.": "TOLVA LODERA",
        "TOLVA SALPICADERA": "TOLVA LODERA",
        "FORRO SALPICADERA": "TOLVA LODERA",
        "LUZ DIRECC.": "CUARTO DIRECCIONAL",
        "FARO NIEBLA": "FARO ANTINIEBLA"
    }
    for k_f, v_f in sorted({**frases_compuestas, **(dicc_extra or {})}.items(), key=lambda x: -len(x[0])):
        if " " in k_f and k_f in texto:
            texto = texto.replace(k_f, v_f)

    # 2. Traducir palabra por palabra y resolver sinónimos regionales
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
    if "COSTADO" in frase_pieza and not any(x in frase_pieza for x in ["MOLDURA", "CRISTAL", "VIDRIO", "CALAVERA"]):
        frase_pieza = frase_pieza.replace("COSTADO", "COSTADO LIENZO", 1)

    marca_clean = str(marca).upper().strip()
    mod_clean = limpiar_modelo_comercial(marca_clean, vehiculo, ano)
    return f"{frase_pieza} {marca_clean} {mod_clean} {ano}".strip()

def calcular_fecha_habiles(dias_habiles=6):
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
    for nombre_h in ["BD_UNIFICADA", "BD_HISTORICO"]:
        try:
            ws = doc.worksheet(nombre_h)
            datos = ws.get_all_values()
            if len(datos) <= 1:
                continue
            headers = [str(h).strip().upper() for h in datos[0]]
            i_pza = next((i for i, h in enumerate(headers) if "DESCRIP" in h or "REFAC" in h), -1)
            i_mod = next((i for i, h in enumerate(headers) if "MODELO" in h or "VEH" in h), -1)
            i_pre = next((i for i, h in enumerate(headers) if "PRECIO" in h or "COSTO" in h), -1)
            if i_pza >= 0 and i_pre >= 0 and i_mod >= 0:
                for r in datos[1:]:
                    if len(r) > max(i_pza, i_pre, i_mod):
                        try:
                            val = float(str(r[i_pre]).replace('$', '').replace(',', '').strip())
                            if val > 100:
                                p_txt = str(r[i_pza]).upper().strip()
                                m_txt = str(r[i_mod]).upper().strip()
                                registros.append((p_txt, m_txt, val))
                        except Exception:
                            pass
        except Exception:
            pass
    return registros

def buscar_en_historial(registros_hist, desc_raw, modelo_limpio):
    if not registros_hist or not modelo_limpio:
        return 0.0
    mod_up = str(modelo_limpio).upper().strip()
    mod_sin_guion = mod_up.replace("-", "")
    d_raw_up = str(desc_raw).upper().strip()
    precios_exactos = []
    for p_txt, m_txt, val in registros_hist:
        m_clean = m_txt.replace("-", "")
        if (mod_up in m_txt or mod_sin_guion in m_clean) and d_raw_up == p_txt:
            precios_exactos.append(val)
    if precios_exactos:
        return round(sum(precios_exactos) / len(precios_exactos))
    return 0.0

def descubrir_modelos_gemini(gemini_key):
    """Prioriza los modelos estables con cuota activa y excluye los dados de baja (2.5-flash-lite) o de voz."""
    preferidos = [
        "gemini-flash-latest",
        "gemini-flash-lite-latest",
        "gemma-3-27b-it",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite"
    ]
    if not gemini_key:
        return []
    try:
        r = requests.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={gemini_key}", timeout=10)
        if r.status_code == 200:
            modelos_api = []
            palabras_excluir = ["tts", "audio", "image", "imagen", "veo", "embedding", "aqa", "robotics", "computer", "learnlm", "thinking", "2.5-flash", "2.5-pro", "3-flash", "3.1-pro"]
            for m in r.json().get("models", []):
                metodos = m.get("supportedGenerationMethods", [])
                if "generateContent" in metodos:
                    nom = m.get("name", "").replace("models/", "")
                    if ("gemini" in nom or "gemma-3-27b" in nom) and not any(ex in nom.lower() for ex in palabras_excluir):
                        modelos_api.append(nom)

            ordenados = [p for p in preferidos if p in modelos_api]
            for m_rest in modelos_api:
                if m_rest not in ordenados:
                    ordenados.append(m_rest)
            return ordenados[:4]
    except Exception:
        pass
    return preferidos[:3]

def cotizar_lote_con_gemini_ai(marca, modelo, ano, vin, lista_partidas_query, tc_usd, gemini_key, portales_cfg):
    """
    Capa 1: Prueba los modelos de texto válidos en tu cuenta (con y sin Google Search)
    hasta obtener los precios en MXN.
    """
    resultados_ia = {}
    if not gemini_key:
        print("   ⚠️ [Capa 1 - IA]: No hay GEMINI_API_KEY guardada en BD_CONFIG_BOTS. Saltando a Capa 2...")
        return resultados_ia

    modelos_disponibles = descubrir_modelos_gemini(gemini_key)
    print(f"   🤖 [Capa 1 - IA]: Modelos de texto listos para probar: {modelos_disponibles}")

    lista_portales_txt = ", ".join([f"{p['nombre']} ({p['url']})" for p in portales_cfg])

    for i in range(0, len(lista_partidas_query), 8):
        lote = lista_partidas_query[i:i+8]
        lineas_prompt = "\n".join([f"- ID {item['idx']}: {item['q']} (Descripción portal: {item['desc']})" for item in lote])
        prompt = (
            f"Actúa como cotizador senior de refacciones de colisión en México y EE.UU.\n"
            f"Vehículo: {marca} {modelo} (Año {ano}) | VIN: {vin}\n"
            f"Tipo de cambio USD a MXN: {tc_usd}\n"
            f"Portales de referencia: Radec (radec.com.mx), Mercado Libre México, eBay Motors, PartSouq, PartsLink24 ({lista_portales_txt}).\n\n"
            f"Para cada una de las siguientes piezas, entrega precios reales de mercado en pesos mexicanos (MXN, enteros mayores a 0):\n"
            f"- 'orig': Precio pieza ORIGINAL / OEM nueva.\n"
            f"- 'semi': Precio pieza USADA / SEMINUEVA en Mercado Libre o eBay.\n"
            f"- 'gen': Precio pieza GENÉRICA nueva (Radec / TYC / Depo / Tong Yang).\n\n"
            f"Piezas a cotizar:\n{lineas_prompt}\n\n"
            f"Responde ÚNICAMENTE con un arreglo JSON válido con este formato exacto:\n"
            f'[{{"idx": numero_id, "orig": entero_mxn, "semi": entero_mxn, "gen": entero_mxn, "fuente": "RAD o ML o EB o AGEN", "link": "url_directa_o_vacio"}}]'
        )

        exito_lote = False
        for mod_name in modelos_disponibles:
            if exito_lote:
                break
            # Los modelos gemma no usan la herramienta google_search; los gemini prueban con search y luego directo
            modos_search = [False] if "gemma" in mod_name else [True, False]
            for usar_search in modos_search:
                if exito_lote:
                    break
                try:
                    url_gem = f"https://generativelanguage.googleapis.com/v1beta/models/{mod_name}:generateContent?key={gemini_key}"
                    payload = {"contents": [{"parts": [{"text": prompt}]}]}
                    if usar_search:
                        payload["tools"] = [{"google_search": {}}]

                    resp = requests.post(url_gem, json=payload, timeout=25)
                    if resp.status_code == 200:
                        cand = resp.json().get("candidates", [])
                        if cand:
                            partes_txt = cand[0].get("content", {}).get("parts", [])
                            texto_completo = "".join([p.get("text", "") for p in partes_txt])
                            m_arr = re.search(r'\[.*\]', texto_completo, re.DOTALL)
                            if m_arr:
                                arr_json = json.loads(m_arr.group(0))
                                encontrados_cnt = 0
                                for obj in arr_json:
                                    idx_k = int(obj.get("idx", -1))
                                    o_v = round(float(obj.get("orig", 0) or 0))
                                    s_v = round(float(obj.get("semi", 0) or 0))
                                    g_v = round(float(obj.get("gen", 0) or 0))
                                    if o_v > 0 or s_v > 0 or g_v > 0:
                                        encontrados_cnt += 1
                                    resultados_ia[idx_k] = {
                                        "orig": o_v,
                                        "semi": s_v,
                                        "gen": g_v,
                                        "fuente": str(obj.get("fuente", "ML")).upper(),
                                        "link": str(obj.get("link", ""))
                                    }
                                if encontrados_cnt > 0:
                                    modo_lbl = "con Google Search" if usar_search else "modo Estimación Experta"
                                    print(f"   ✅ [Capa 1 - IA]: {mod_name} ({modo_lbl}) cotizó {encontrados_cnt}/{len(lote)} piezas.")
                                    exito_lote = True
                    else:
                        err_short = resp.text[:160].replace("\n", " ")
                        print(f"   ℹ️ [Capa 1 - {mod_name} search={usar_search}]: HTTP {resp.status_code} ({err_short})")
                except Exception as e_g:
                    print(f"   ℹ️ [Capa 1 - {mod_name}]: {e_g}")

    return resultados_ia

def buscar_web_playwright_respaldo(page_buscador, query, marca, modelo):
    """Devuelve los 3 precios y los 3 enlaces exactos (Original, Seminueva y Genérica)."""
    precios_orig, precios_semi, precios_gen = [], [], []
    mejor_link_orig, mejor_link_semi, mejor_link_gen = "", "", ""

    q_clean = query.replace(modelo, modelo.replace("-", "")) if "-" in modelo else query
    url_fallback_ml = f"https://listado.mercadolibre.com.mx/{urllib.parse.quote(q_clean.replace(' ', '-'))}"
    consultas_web = [
        f"{q_clean} radec OR mercadolibre precio",
        f"site:mercadolibre.com.mx {q_clean}"
    ]

    for q_w in consultas_web:
        try:
            url_yh = f"https://mx.search.yahoo.com/search?p={urllib.parse.quote(q_w)}"
            page_buscador.goto(url_yh, timeout=12000, wait_until="domcontentloaded")
            time.sleep(0.9)
            bloques = page_buscador.evaluate("""
                () => Array.from(document.querySelectorAll('div.algo, li'))
                    .map(el => {
                        let a = el.querySelector('a');
                        let t = el.querySelector('h3') ? el.querySelector('h3').innerText : '';
                        return {
                            titulo: t.replace(/\\s+/g, ' ').trim(),
                            txt: (el.innerText || '').replace(/\\s+/g, ' ').toUpperCase(),
                            href: a ? a.href : ''
                        };
                    })
                    .filter(x => x.txt.includes('$') && x.href.startsWith('http'))
                    .slice(0, 12)
            """)
            for b in bloques:
                link_real = b['href']
                m_ru = re.search(r'/RU=([^/]+)/', link_real)
                if m_ru:
                    link_real = urllib.parse.unquote(m_ru.group(1))
                if "yahoo.com" in link_real:
                    continue

                montos = re.findall(r'\$\s*([0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]{2})?|[0-9]{3,5}\.[0-9]{2}|[0-9]{4,5})', b['txt'])
                for m in montos:
                    val = float(m.replace(',', ''))
                    if 250 <= val <= 65000:
                        if any(k in b['txt'] for k in ["USADO", "USADA", "SEMINUEV", "YONKE"]):
                            precios_semi.append(val)
                            if not mejor_link_semi:
                                mejor_link_semi = link_real
                                print(f"        🔗 [Semi ${val:,.0f}]: {b['titulo'][:50]} -> {link_real[:60]}")
                        elif any(k in b['txt'] for k in ["ORIGINAL", "OEM", "GENUIN", "AGENCIA"]) and "RADEC" not in b['txt'] and "TONG YANG" not in b['txt']:
                            precios_orig.append(val)
                            if not mejor_link_orig:
                                mejor_link_orig = link_real
                                print(f"        🔗 [Orig ${val:,.0f}]: {b['titulo'][:50]} -> {link_real[:60]}")
                        else:
                            precios_gen.append(val)
                            if not mejor_link_gen:
                                mejor_link_gen = link_real
                                print(f"        🔗 [Gen ${val:,.0f}]: {b['titulo'][:50]} -> {link_real[:60]}")
            if precios_orig or precios_semi or precios_gen:
                break
        except Exception:
            pass

    p_o = round(sum(sorted(precios_orig)[:3]) / len(precios_orig[:3])) if precios_orig else 0
    p_s = round(sum(sorted(precios_semi)[:3]) / len(precios_semi[:3])) if precios_semi else 0
    p_g = round(sum(sorted(precios_gen)[:3]) / len(precios_gen[:3])) if precios_gen else 0

    l_o = mejor_link_orig or f"https://www.google.com/search?q={urllib.parse.quote(q_clean + ' OEM original precio')}"
    l_s = mejor_link_semi or url_fallback_ml
    l_g = mejor_link_gen or f"https://www.google.com/search?q={urllib.parse.quote('site:radec.com.mx OR site:mercadolibre.com.mx ' + q_clean)}"
    links_empaquetados = f"{l_o} || {l_s} || {l_g}"

    return p_o, p_s, p_g, links_empaquetados

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
    for f in page.frames:
        try:
            loc = f.locator("a:text-is('Cotizaciones'), a:has-text('Cotizaciones')").first
            if loc.count() > 0:
                loc.click(timeout=6000)
                return True
        except Exception:
            pass
    for f in [page.main_frame] + page.frames:
        try:
            if f.evaluate("() => typeof submitForm === 'function'"):
                f.evaluate("submitForm('main_action.do','quotation_list_action.do')")
                return True
        except Exception:
            pass
    return False

def regresar_a_lista_siniestros(page, frame):
    try:
        for _ in range(2):
            f_der = obtener_frame_derecho(page, espera_seg=5)
            btn_reg = f_der.locator("input[value='Regresar'], button:has-text('Regresar')")
            if btn_reg.count() > 0:
                btn_reg.first.click(timeout=6000)
                time.sleep(1.8)
    except Exception:
        pass
    f_der = obtener_frame_derecho(page, espera_seg=5)
    if f_der.locator("td:has-text('Listado de Cotizaciones')").count() == 0:
        abrir_menu_cotizaciones(page)
        time.sleep(2.5)

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
        time.sleep(0.4)
    return page.main_frame

def verificar_headless_seguro(modo_headless):
    if not modo_headless and sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
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

        key_len = len(cfg.get("GEMINI_API_KEY", ""))
        print(f"🔑 Estado Gemini API Key en BD_CONFIG_BOTS: {'CONFIGURADA (' + str(key_len) + ' caracteres)' if key_len > 10 else 'VACÍA / NO CONFIGURADA'}")

        filas_todas = ws_cot.get_all_values()
        filas_sanas = [ENCABEZADOS_COT]
        existentes = set()
        if len(filas_todas) > 1:
            for r in filas_todas[1:]:
                if len(r) >= 32:
                    ciu_r, edo_r, tal_r = str(r[9]), str(r[10]), str(r[8])
                    excluido, _ = es_siniestro_excluido(ciu_r, edo_r, tal_r, cfg)
                    es_llanta_parab = es_pieza_convenio_excluida(r[14])
                    llave_unica = f"{str(r[2]).strip()}_{str(r[12]).strip()}"
                    if not excluido and not es_llanta_parab and llave_unica not in existentes:
                        filas_sanas.append(r[:32])
                        existentes.add(llave_unica)
    except Exception as e_sh:
        print(f"❌ [ERROR GOOGLE SHEETS]: {e_sh}")
        traceback.print_exc()
        return

    nuevas = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=modo_headless, args=["--no-sandbox"])
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
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
            enlaces_txt = frame.locator("a.cvi").all_inner_texts()
            lista_siniestros = [t.strip() for t in enlaces_txt if len(t.strip()) >= 5]
            print(f"-> Siniestros activos en bandeja del portal: {len(lista_siniestros)}")

            # Mover automáticamente al Historial los siniestros que estaban PENDIENTE pero ya cerraron en el portal
            activos_set = set(lista_siniestros)
            archivadas_cnt = 0
            for r_sana in filas_sanas[1:]:
                if str(r_sana[31]).strip().upper() == "PENDIENTE" and str(r_sana[2]).strip() not in activos_set:
                    r_sana[31] = "HISTORIAL / CERRADA"
                    archivadas_cnt += 1

            if archivadas_cnt > 0 or len(filas_sanas) != len(filas_todas):
                ws_cot.clear()
                ws_cot.update(range_name='A1', values=filas_sanas, value_input_option='USER_ENTERED')
                if archivadas_cnt > 0:
                    print(f"📁 Se movieron {archivadas_cnt} partida(s) que ya no están por cotizar al Historial como respaldo.")

            for idx, num_sin in enumerate(lista_siniestros):
                print(f"\n[{idx+1}/{len(lista_siniestros)}] Revisando interior del Siniestro {num_sin}...")
                try:
                    frame = obtener_frame_derecho(page, espera_seg=8)
                    loc_sin = frame.locator(f"a.cvi:has-text('{num_sin}')")
                    if loc_sin.count() == 0:
                        abrir_menu_cotizaciones(page)
                        time.sleep(2.5)
                        frame = obtener_frame_derecho(page, espera_seg=8)
                        loc_sin = frame.locator(f"a.cvi:has-text('{num_sin}')")
                        if loc_sin.count() == 0:
                            continue

                    loc_sin.first.click(timeout=10000)
                    time.sleep(2.2)

                    frame = obtener_frame_derecho(page, espera_seg=8)
                    loc_cot1 = frame.locator("a.cvi")
                    if loc_cot1.count() == 0:
                        regresar_a_lista_siniestros(page, frame)
                        continue

                    loc_cot1.first.click(timeout=10000)
                    time.sleep(2.5)

                    frame = obtener_frame_derecho(page, espera_seg=8)
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
                        regresar_a_lista_siniestros(page, frame)
                        continue

                    piezas_lista = detalle.get('piezas', [])
                    marca_clean = detalle.get('marca', '').upper().strip()
                    mod_comercial = limpiar_modelo_comercial(marca_clean, detalle.get('vehiculo', ''), detalle.get('modelo', ''))
                    ano_clean = detalle.get('modelo', '').strip()

                    partidas_a_cotizar = []
                    for pza in piezas_lista:
                        if es_pieza_convenio_excluida(pza['descripcion']):
                            print(f"     ⏭️ Omitiendo por convenio (Llanta/Parabrisas): {pza['descripcion']}")
                            continue
                        if f"{num_sin}_{pza['idx']}" in existentes:
                            continue
                        q = expandir_descripcion(pza['descripcion'], marca_clean, detalle.get('vehiculo', ''), ano_clean, cfg.get("DICCIONARIO_EXTRA", {}))
                        partidas_a_cotizar.append({
                            "idx": pza['idx'],
                            "cantidad": pza['cantidad'],
                            "desc": pza['descripcion'],
                            "q": q
                        })

                    if not partidas_a_cotizar:
                        regresar_a_lista_siniestros(page, frame)
                        continue

                    print(f"  ✅ Cotizando {len(partidas_a_cotizar)} pieza(s) | Auto: {marca_clean} {mod_comercial} ({ano_clean}) | Taller: {taller_real}")

                    # CAPA 1: Gemini AI
                    precios_ia_lote = cotizar_lote_con_gemini_ai(
                        marca_clean, mod_comercial, ano_clean, detalle.get('vin', ''),
                        partidas_a_cotizar, cfg.get("TC_USD", 20.50), cfg.get("GEMINI_API_KEY", ""),
                        cfg.get("PORTALES_BUSQUEDA", PORTALES_DEFAULT)
                    )

                    ahora = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-6))).strftime("%Y-%m-%d %H:%M")
                    for item_p in partidas_a_cotizar:
                        idx_p = item_p['idx']
                        desc_p = item_p['desc']
                        q = item_p['q']

                        datos_ia = precios_ia_lote.get(idx_p, {})
                        p_orig = datos_ia.get("orig", 0)
                        p_noorig = datos_ia.get("semi", 0)
                        p_gen = datos_ia.get("gen", 0)
                        link_directo = datos_ia.get("link", "")
                        fuente_ia = datos_ia.get("fuente", "ML").upper()

                        # CAPA 2: Si Capa 1 devolvió $0, buscar con navegador Chromium en DuckDuckGo
                        if p_orig == 0 and p_noorig == 0 and p_gen == 0:
                            print(f"     🌐 [Capa 2 - Web] Buscando '{q}' en portales...")
                            p_orig, p_noorig, p_gen, link_web = buscar_web_playwright_respaldo(page_buscador, q, marca_clean, mod_comercial)
                            if link_web:
                                link_directo = link_web

                        # Construir los 3 enlaces dedicados por columna (sin URLs inventadas por IA que den 404)
                        q_sin_guion = q.replace(mod_comercial, mod_comercial.replace("-", ""))
                        # Para Radec quitamos el nombre largo de la marca (ej. CHEVROLET) porque Radec usa abreviaturas (CV SONIC 17-19)
                        q_radec = q_sin_guion.replace(f" {marca_clean} ", " ")
                        vin_clean = str(detalle.get('vin', '')).strip()
                        l_orig_def = f"https://partsouq.com/en/search/all?q={urllib.parse.quote(vin_clean)}" if len(vin_clean) >= 11 else f"https://www.google.com/search?q={urllib.parse.quote(q_sin_guion + ' OEM original partsouq')}"
                        l_base_ml = f"https://listado.mercadolibre.com.mx/{urllib.parse.quote(q_sin_guion.replace(' ', '-'))}"
                        l_gen_def = f"https://www.google.com/search?q={urllib.parse.quote('site:radec.com.mx ' + q_radec)}"
                        if "||" not in str(link_directo) or "radec.com.mx/catalogo/" in str(link_directo):
                            link_directo = f"{l_orig_def} || {l_base_ml} || {l_gen_def}"

                        # CAPA 3: Historial exacto en tu base
                        p_hist = buscar_en_historial(registros_hist, desc_p, mod_comercial)
                        flete = estimar_flete(desc_p, ciudad_real, estado_real)

                        if p_gen > 0:
                            costo, origen, fuente_cod = p_gen, "NO ORIGINAL", ("RAD" if "RAD" in fuente_ia else "ML")
                        elif p_noorig > 0:
                            costo, origen, fuente_cod = p_noorig, "SEMINUEVA", ("EB" if "EB" in fuente_ia else "ML")
                        elif p_orig > 0:
                            costo, origen, fuente_cod = p_orig, "ORIGINAL", "AGEN"
                        elif p_hist > 0:
                            costo, origen, fuente_cod = p_hist, "NO ORIGINAL", "LOC"
                        else:
                            costo, origen, fuente_cod = 0, "NO ORIGINAL", "MAN"

                        margen_def = 65
                        sug = max(1000, round((costo + flete) * (1.0 + margen_def / 100.0))) if costo > 0 else 0
                        tag_prov = re.sub(r'[^A-Z]', '', fuente_cod)[:4] or "RAD"
                        codigo_hub_gen = f"HUB{tag_prov}{random.randint(100, 999)}"

                        print(f"     💰 #{idx_p+1} {desc_p} ({q}) ➔ Orig: ${p_orig} | Semi: ${p_noorig} | Gen: ${p_gen} | Hist: ${p_hist} ➔ Sug: ${sug} ({codigo_hub_gen})")

                        nuevas.append([
                            f"COT-{num_sin}-{idx_p+1}", ahora, num_sin, "1",
                            marca_clean, f"{marca_clean} {mod_comercial}".strip(), ano_clean, detalle.get('vin', ''),
                            taller_real, ciudad_real, estado_real, detalle.get('fecha_fin', ''),
                            idx_p, item_p['cantidad'], desc_p, q,
                            p_orig, p_noorig, p_gen, p_hist,
                            flete, fuente_cod, origen, costo,
                            margen_def, sug, 0, sug,
                            codigo_hub_gen, link_directo, "FALSE", "PENDIENTE"
                        ])
                        existentes.add(f"{num_sin}_{idx_p}")

                    regresar_a_lista_siniestros(page, frame)
                except Exception as e_sin:
                    print(f"  ❌ [ERROR en Siniestro {num_sin}]: {e_sin}")
                    regresar_a_lista_siniestros(page, frame)
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

    fecha_7d = calcular_fecha_habiles(6)
    mapa_orig = {"ORIGINAL": "42007", "NO ORIGINAL": "42008", "GENERICA": "42008", "SEMINUEVA": "42009"}
    actualizar = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=modo_headless)
        ctx = browser.new_context(viewport={"width": 1366, "height": 950})
        page = ctx.new_page()

        ultimo_dialogo = {"error": ""}
        def manejar_dialogo(d):
            msg_d = d.message.strip()
            if "seguro de guardar" in msg_d.lower() or "exito" in msg_d.lower() or "guardaron" in msg_d.lower():
                print(f"   ✅ [CONFIRMACIÓN PORTAL ACEPTADA]: {msg_d}")
            else:
                ultimo_dialogo["error"] = msg_d
                print(f"   🔔 [ALERTA PORTAL]: {msg_d}")
            d.accept()

        page.on("dialog", manejar_dialogo)

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
                    ultimo_dialogo["error"] = ""
                    print(f"-> Abriendo Siniestro {sin} para inyectar {len(dict_partidas)} partida(s) validadas...")
                    frame = obtener_frame_derecho(page, espera_seg=8)
                    link = frame.locator(f"a.cvi:has-text('{sin}')")
                    if link.count() == 0:
                        print(f"   ℹ️ El Siniestro {sin} ya no está en bandeja (ya fue cotizado o cerró subasta). Moviendo a Historial...")
                        for it in dict_partidas.values():
                            actualizar.append(gspread.Cell(row=it['gs_row'], col=idx_est + 1, value="HISTORIAL / CERRADA"))
                        continue
                    link.first.click(timeout=10000)
                    time.sleep(2.2)

                    frame = obtener_frame_derecho(page, espera_seg=8)
                    frame.locator("a.cvi").first.click(timeout=10000)
                    time.sleep(2.5)

                    frame = obtener_frame_derecho(page, espera_seg=8)

                    for idx_fila, it in sorted(dict_partidas.items()):
                        cod_origen = mapa_orig.get(it['origen_txt'], "42008")
                        sel_status = frame.locator("select[name='statusPart']").nth(idx_fila)
                        sel_status.select_option("133002")
                        time.sleep(0.3)

                        fecha_usada = frame.evaluate(
                            """(args) => {
                                let fv = document.getElementById('promiseDatePart' + args.i);
                                let fh = document.getElementById('promiseDateValue' + args.i);
                                let actual = (fv && fv.value ? fv.value.trim() : '');
                                let finalDate = actual.length >= 9 ? actual.toUpperCase() : args.f;
                                if (fv) { fv.removeAttribute('readonly'); fv.value = finalDate; }
                                if (fh) { fh.value = finalDate; }
                                return finalDate;
                            }""",
                            {"i": idx_fila, "f": fecha_7d}
                        )

                        frame.locator("input[name='codePart']").nth(idx_fila).fill(it['codigo_hub'])
                        frame.locator("input[name='price']").nth(idx_fila).fill(it['precio_int'])
                        frame.locator("select[name='origin']").nth(idx_fila).select_option(cod_origen)
                        print(f"   ✔ Partida #{idx_fila+1} llenada: ${it['precio_int']} | {it['origen_txt']} | {it['codigo_hub']} | Fecha: {fecha_usada}")
                        time.sleep(0.15)

                    page.screenshot(path="evidencia_antes_grabar.png", full_page=True)

                    btn = frame.locator("input[name='btnSubmit'][value='Grabar']")
                    if btn.count() > 0:
                        btn.first.click()
                        time.sleep(3.0)

                        if "Fecha Promesa" in ultimo_dialogo["error"]:
                            m_fec = re.search(r'\(\s*([0-9]{1,2}\s+[a-zA-Z]{3}\s+[0-9]{4})\s*\)', ultimo_dialogo["error"])
                            if m_fec:
                                fecha_corregida = m_fec.group(1).strip().upper()
                                ultimo_dialogo["error"] = ""
                                for idx_fila in dict_partidas.keys():
                                    frame.evaluate(
                                        """(args) => {
                                            let fv = document.getElementById('promiseDatePart' + args.i);
                                            let fh = document.getElementById('promiseDateValue' + args.i);
                                            if (fv) fv.value = args.f;
                                            if (fh) fh.value = args.f;
                                        }""",
                                        {"i": idx_fila, "f": fecha_corregida}
                                    )
                                btn.first.click()
                                time.sleep(3.5)

                        page.screenshot(path="evidencia_despues_grabar.png", full_page=True)

                        if not ultimo_dialogo["error"]:
                            print(f"   💾 Siniestro {sin} GRABADO exitosamente en el portal.")
                            for it in dict_partidas.values():
                                actualizar.append(gspread.Cell(row=it['gs_row'], col=idx_est + 1, value="ENVIADA PORTAL"))
                        else:
                            print(f"   ❌ El portal rechazó el guardado con la alerta: {ultimo_dialogo['error']}")

                    regresar_a_lista_siniestros(page, frame)
                except Exception as e:
                    print(f"❌ [!] Error enviando {sin}: {e}")
                    regresar_a_lista_siniestros(page, frame)
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
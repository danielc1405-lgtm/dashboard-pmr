# ==============================================================================
# === CHAT PMR MÓVIL (PWA) — MENSAJERÍA, GRUPOS Y STICKERS ===
# ==============================================================================
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import gspread
import json
import os
import re
import io
import uuid
import time
import html
import base64
import datetime
import unicodedata
from PIL import Image
from google.oauth2.service_account import Credentials

# Configuración optimizada para teléfono (PWA)
st.set_page_config(
    page_title="Chat PMR",
    page_icon="💬",
    layout="centered",
    initial_sidebar_state="collapsed"
)

SHEET_ID = "10jrOsS054n0atMk8GxQilkXqm6LjsnrwPOZnSx8iDek"
CARPETA_STICKERS = "stickers"
TZ_MX = datetime.timezone(datetime.timedelta(hours=-6))

# ==============================================================================
# === 1. ESTILOS CSS MÓVIL (TEMA OSCURO ESTILO WHATSAPP) ===
# ==============================================================================
st.markdown("""
    <style>
    header[data-testid="stHeader"], footer {
        visibility: hidden !important;
        display: none !important;
    }
    .stApp, div[data-testid="stAppViewContainer"], .main {
        background-color: #05070A !important;
    }
    .block-container,
    div[data-testid="stMainBlockContainer"] {
        padding-top: 0.7rem !important;
        padding-bottom: 1.5rem !important;
        padding-left: 0.7rem !important;
        padding-right: 0.7rem !important;
        max-width: 680px !important;
    }
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div,
    div[data-baseweb="textarea"],
    textarea {
        background-color: #111B21 !important;
        border-color: #222E35 !important;
        color: #E9EDEF !important;
    }
    div.stButton > button {
        min-height: 2.75rem !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
    }
    div.stButton > button[kind="primary"],
    div[data-testid="stFormSubmitButton"] > button[kind="primary"],
    div[data-testid="stFormSubmitButton"] > button {
        background-color: #E50914 !important;
        border-color: #E50914 !important;
        color: #FFFFFF !important;
    }
    /* Tarjetas de conversación en la bandeja (2 líneas alineadas a la izquierda) */
    .st-key-pmr_mob_bandeja div.stButton > button {
        height: auto !important;
        min-height: 3.6rem !important;
        padding: 9px 13px !important;
        background-color: #111B21 !important;
        border: 1px solid #222E35 !important;
        display: flex !important;
        justify-content: flex-start !important;
        align-items: flex-start !important;
        text-align: left !important;
    }
    .st-key-pmr_mob_bandeja div.stButton > button:hover {
        border-color: #00A884 !important;
        background-color: #18252D !important;
    }
    .st-key-pmr_mob_bandeja div.stButton > button > div,
    .st-key-pmr_mob_bandeja div.stButton > button [data-testid="stMarkdownContainer"] {
        width: 100% !important;
        text-align: left !important;
        margin-right: auto !important;
    }
    .st-key-pmr_mob_bandeja div.stButton > button p {
        white-space: pre-line !important;
        line-height: 1.35 !important;
        font-size: 0.9rem !important;
        text-align: left !important;
        width: 100% !important;
        margin: 0 !important;
        color: #E9EDEF !important;
    }
    /* File uploader compacto para móvil */
    .st-key-pmr_mob_composer [data-testid="stFileUploaderDropzoneInstructions"],
    .st-key-pmr_mob_composer [data-testid="stFileUploaderFile"],
    .st-key-pmr_mob_composer [data-testid="stFileUploader"] small {
        display: none !important;
    }
    .st-key-pmr_mob_composer [data-testid="stFileUploaderDropzone"] {
        padding: 0px !important;
        min-height: 2.75rem !important;
        border: none !important;
        background: transparent !important;
    }
    .st-key-pmr_mob_composer [data-testid="stFileUploaderDropzone"] button {
        width: 100% !important;
        min-height: 2.75rem !important;
        border-radius: 10px !important;
        margin: 0 !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# === 2. CONEXIÓN CON REINTENTO AUTOMÁTICO (502/503/429) ===
# ==============================================================================
@st.cache_resource
def init_connection():
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    cred_dict = json.loads(st.secrets["google_credentials"])
    credenciales = Credentials.from_service_account_info(cred_dict, scopes=scopes)
    cliente = gspread.authorize(credenciales)
    return cliente.open_by_key(SHEET_ID)

def leer_hoja_con_reintento(nombre_hoja, max_intentos=3):
    ultimo_err = None
    for intento in range(max_intentos):
        try:
            doc = init_connection()
            ws = doc.worksheet(nombre_hoja)
            return ws.get_all_values()
        except Exception as e:
            ultimo_err = e
            err_txt = str(e).upper()
            es_temp = any(c in err_txt for c in ["502", "503", "500", "429", "SERVER ERROR", "TEMPORARY"])
            if es_temp and intento < max_intentos - 1:
                init_connection.clear()
                time.sleep(1.2 * (intento + 1))
                continue
            raise ultimo_err

# ==============================================================================
# === 3. SISTEMA DE LOGIN Y AUTO-SESIÓN (?usr=...) ===
# ==============================================================================
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

if not st.session_state['autenticado'] and 'usr' in st.query_params:
    try:
        usr_url = str(st.query_params['usr']).strip()
        if usr_url:
            datos_u_a = leer_hoja_con_reintento("Usuarios")
            if len(datos_u_a) > 1:
                df_u_a = pd.DataFrame(datos_u_a[1:], columns=[str(h).strip() for h in datos_u_a[0]])
                match_a = df_u_a[df_u_a['Nombre Completo'].astype(str).str.strip().str.upper() == usr_url.upper()]
                if not match_a.empty:
                    st.session_state['autenticado'] = True
                    st.session_state['usuario_actual'] = str(match_a.iloc[0]['Nombre Completo']).strip()
                    st.session_state['rol_actual'] = str(match_a.iloc[0].get('Rol', '')).strip()
    except Exception:
        pass

if not st.session_state['autenticado']:
    _, c_mid, _ = st.columns([1, 1.4, 1])
    with c_mid:
        if os.path.exists("logo.png"):
            st.image("logo.png", width=150)
    st.markdown("<h2 style='text-align:center; color:#E9EDEF; margin-bottom:0.2rem;'>💬 Chat PMR</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#8696A0; font-size:0.9rem;'>Mensajería interna del equipo</p>", unsafe_allow_html=True)

    with st.form("login_chat_movil"):
        usuario_in = st.text_input("👤 Usuario").strip().lower()
        password_in = st.text_input("🔑 Contraseña", type="password")
        if st.form_submit_button("Entrar al Chat", type="primary", use_container_width=True):
            try:
                datos_u = leer_hoja_con_reintento("Usuarios")
                df_u = pd.DataFrame(datos_u[1:], columns=[str(h).strip() for h in datos_u[0]])
                df_u['Usuario'] = df_u['Usuario'].astype(str).str.strip().str.lower()
                df_u['Password'] = df_u['Password'].astype(str).str.strip()
                match = df_u[(df_u['Usuario'] == usuario_in) & (df_u['Password'] == password_in)]
                if not match.empty:
                    nom_u = str(match.iloc[0]['Nombre Completo']).strip()
                    st.session_state['autenticado'] = True
                    st.session_state['usuario_actual'] = nom_u
                    st.session_state['rol_actual'] = str(match.iloc[0].get('Rol', '')).strip()
                    st.query_params['usr'] = nom_u
                    st.rerun()
                else:
                    st.error("❌ Usuario o contraseña incorrectos.")
            except Exception as e:
                st.error(f"Error al validar acceso: {e}")
    st.stop()

usuario_activo_real = str(st.session_state.get('usuario_actual', 'Usuario')).strip()

# ==============================================================================
# === 4. MOTORES DE USUARIOS, TAREAS, SINIESTROS, ADJUNTOS Y STICKERS ===
# ==============================================================================
@st.cache_data(ttl=600)
def obtener_mapa_usuarios():
    usuarios_dropdown = []
    grupos_identidad = []
    try:
        datos_u = leer_hoja_con_reintento("Usuarios")
        if len(datos_u) > 1:
            headers_u = [str(h).strip().upper() for h in datos_u[0]]
            idx_usr = next((i for i, h in enumerate(headers_u) if "USUARIO" in h), 0)
            idx_nom = next((i for i, h in enumerate(headers_u) if "NOMBRE" in h), -1)
            for fila in datos_u[1:]:
                u_val = str(fila[idx_usr]).strip() if len(fila) > idx_usr else ""
                n_val = str(fila[idx_nom]).strip() if (idx_nom >= 0 and len(fila) > idx_nom) else ""
                mostrar = n_val if n_val else u_val
                if mostrar and mostrar.lower() != "nan" and mostrar not in usuarios_dropdown:
                    usuarios_dropdown.append(mostrar)
                alias = {x.lower() for x in [u_val, n_val] if x and x.lower() != "nan"}
                if alias:
                    grupos_identidad.append(alias)
    except Exception:
        pass
    if not usuarios_dropdown:
        usuarios_dropdown = ["Daniel Cantú", "Diana Cantú", "Marco A. Mendoza", "Israel Escamilla", "Cristian Gaona", "Juan Garza", "Dionicio Cantú"]
    return usuarios_dropdown, grupos_identidad

def es_mismo_usuario(u1, u2, grupos_identidad=None):
    def limpiar_txt(t):
        s = unicodedata.normalize('NFKD', str(t)).encode('ASCII', 'ignore').decode('utf-8').lower().strip()
        return re.sub(r'[^a-z0-9]', '', s)
    s1, s2 = str(u1).strip().lower(), str(u2).strip().lower()
    if not s1 or not s2:
        return False
    if s1 == s2:
        return True
    if grupos_identidad:
        for grp in grupos_identidad:
            grp_clean = {limpiar_txt(x) for x in grp}
            if (s1 in grp or limpiar_txt(s1) in grp_clean) and (s2 in grp or limpiar_txt(s2) in grp_clean):
                return True
    c1, c2 = limpiar_txt(s1), limpiar_txt(s2)
    if not c1 or not c2:
        return False
    if c1 in c2 or c2 in c1:
        return True
    for i in range(len(c2) - 4):
        if c2[i:i+5] in c1:
            return True
    return False

def usuario_en_lista(usuario, campo_usuarios, grupos_identidad=None):
    partes = [p.strip() for p in re.split(r'[,;]', str(campo_usuarios or '')) if p.strip()]
    return any(es_mismo_usuario(usuario, p, grupos_identidad) for p in partes)

def extraer_ultimo_evento_chat(row):
    hoy_d = datetime.datetime.now(TZ_MX).date()
    def _parse_dt(txt):
        s = str(txt or "").strip()
        if not s:
            return None
        for fmt in ("%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M", "%d/%m/%y %H:%M", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.datetime.strptime(s, fmt)
            except Exception:
                continue
        return None

    hist_raw = str(row.get('Respuesta', '')).strip()
    dt_ult = None
    autor_ult = ""
    if hist_raw and hist_raw.lower() not in ["none", "nan"]:
        lineas = [l.strip() for l in hist_raw.replace('\\n', '\n').split('\n') if l.strip()]
        for linea in reversed(lineas):
            m = re.match(r'^\[(.*?)\]\s*([^:]+):\s*(.*)$', linea)
            if m:
                dt_p = _parse_dt(m.group(1))
                autor_ult = m.group(2).strip()
                if dt_p:
                    dt_ult = dt_p
                break
    if dt_ult is None:
        dt_ult = _parse_dt(row.get('Fecha_Creacion', ''))
    if not autor_ult:
        autor_ult = str(row.get('Emisor', '')).strip()

    if dt_ult is None:
        gs_r = int(row.get('GS_Row', 0) or 0)
        dt_ult = datetime.datetime(2000, 1, 1) + datetime.timedelta(seconds=gs_r)
        hora_corta = ""
    else:
        hora_corta = dt_ult.strftime("%H:%M") if dt_ult.date() == hoy_d else dt_ult.strftime("%d/%m %H:%M")
    return dt_ult, hora_corta, autor_ult

def requiere_atencion_chat(row, usuario, grupos_identidad=None):
    st_v = str(row.get('Status', '')).strip().lower()
    if st_v not in ['pendiente', 'resuelto']:
        return False
    soy_emi = es_mismo_usuario(usuario, row.get('Emisor', ''), grupos_identidad)
    soy_rec = usuario_en_lista(usuario, row.get('Receptor', ''), grupos_identidad)
    if not (soy_emi or soy_rec):
        return False
    _, _, ult_autor = extraer_ultimo_evento_chat(row)
    if ult_autor:
        return not es_mismo_usuario(usuario, ult_autor, grupos_identidad)
    return (soy_rec and st_v == 'pendiente') or (soy_emi and st_v == 'resuelto')

def acortar_auto_chat(marca_raw, modelo_raw, fallback_ref=""):
    marcas_com = {
        "NISSAN", "TOYOTA", "CHEVROLET", "FORD", "VOLKSWAGEN", "VW", "HONDA", "HYUNDAI",
        "KIA", "MAZDA", "CHERY", "CHIREY", "MG", "BYD", "JAC", "GEELY", "SUZUKI", "MITSUBISHI",
        "DODGE", "JEEP", "RAM", "CHRYSLER", "GMC", "CADILLAC", "BUICK", "BMW", "AUDI", "MERCEDES",
        "MERCEDES-BENZ", "VOLVO", "SEAT", "CUPRA", "PEUGEOT", "RENAULT", "FIAT", "SUBARU",
        "INFINITI", "ACURA", "LEXUS", "LINCOLN", "TESLA", "OMODA", "JAECOO", "CHANGAN", "BAIC", "JETOUR"
    }
    trims_noise = {
        "AUT", "STD", "TM", "TA", "CVT", "4P", "5P", "SEDAN", "HB", "HATCHBACK", "PICKUP",
        "4X4", "4X2", "L4", "V6", "V8", "TURBO", "ADVANCE", "SENSE", "EXCLUSIVE", "XLE",
        "LE", "SE", "LIMITED", "QUANTUM", "PRO", "PLUS", "BASE", "GL", "GLS", "LT", "LTZ", "T"
    }
    siglas_up = {"BMW", "VW", "JAC", "BYD", "MG", "RAM", "GMC", "KIA", "CR-V", "HR-V", "CX-5", "CX-30"}
    marca = str(marca_raw or "").strip().upper()
    modelo = str(modelo_raw or "").strip().upper()
    texto = modelo if modelo else str(fallback_ref or "").strip().upper()
    texto = re.sub(r'\b(19|20)\d{2}\b', '', texto)
    texto = re.sub(r'\(.*?\)', '', texto)
    texto = re.sub(r'\b\d\.\d\b', '', texto)
    palabras = [w for w in texto.split() if w and w not in trims_noise]
    if not palabras:
        return ""
    if (marca and palabras[0] == marca) or (palabras[0] in marcas_com):
        resto = palabras[1:]
        if resto:
            if len(resto[0]) >= 4:
                palabras = resto[:2] if (len(resto) >= 2 and resto[1].isdigit()) else resto[:1]
            else:
                palabras = palabras[:2]
        else:
            palabras = palabras[:1]
    else:
        palabras = palabras[:2] if (len(palabras) >= 2 and palabras[1].isdigit()) else palabras[:1]
        if marca and len(palabras) == 1 and len(palabras[0]) <= 3:
            palabras = [marca] + palabras
    return " ".join(w if (w in siglas_up or len(w) <= 2 or any(c.isdigit() for c in w)) else w.title() for w in palabras)

def acortar_taller_chat(taller_raw, max_len=20):
    siglas_t = {"GG", "GNP", "AMP", "PAMI", "CDR", "BMW", "VW", "SLP", "MTY", "NL", "PMR"}
    t = str(taller_raw or "").strip().upper()
    if not t or t in ["NAN", "NONE"]:
        return ""
    t = re.sub(r'\bS\.?A\.?\s*DE\s*C\.?V\.?\b', '', t).strip()
    t = re.sub(r'\s+', ' ', t)
    if len(t) > max_len:
        t = re.sub(r'^(RECONSTRUCTORA\s+AUTOMOTRIZ|SERVICIOS?\s+AUTOMOTRICES?|TALLER\s+DE\s+HOJALATERIA\s+Y\s+PINTURA|AUTOMOTRIZ|TALLER)\s+', '', t).strip()
    bonito = " ".join(w if w in siglas_t else w.title() for w in t.split())
    return bonito if len(bonito) <= max_len else bonito[:max_len-1].rstrip() + "…"

def formatear_participantes_corto(emisor, receptor, usuario_actual, grupos_identidad=None):
    todos = [str(emisor or '').strip()] + [p.strip() for p in re.split(r'[,;]', str(receptor or '')) if p.strip()]
    otros = []
    vistos = set()
    for p in todos:
        if not p or es_mismo_usuario(usuario_actual, p, grupos_identidad):
            continue
        prim = p.split()[0]
        if prim.lower() not in vistos:
            vistos.add(prim.lower())
            otros.append(prim)
    if not otros:
        return "👤 Yo"
    if len(otros) == 1:
        return f"👤 {otros[0]}"
    if len(otros) == 2:
        return f"👥 {otros[0]}, {otros[1]}"
    return f"👥 {otros[0]}, {otros[1]} +{len(otros) - 2}"

@st.cache_data(ttl=300)
def cargar_contexto_siniestros():
    """Carga catálogo ligero de BD_UNIFICADA para mostrar Auto + Taller y crear nuevos chats."""
    mapa_info = {}
    mapa_piezas = {}
    lista_activos = []
    try:
        datos = leer_hoja_con_reintento("BD_UNIFICADA")
        if len(datos) > 1:
            df = pd.DataFrame(datos[1:], columns=[str(h).strip() for h in datos[0]])
            c_sin = next((c for c in df.columns if "SINIESTRO" in str(c).upper() or "PEDIDO" in str(c).upper()), None)
            c_tal = next((c for c in df.columns if "TALLER" in str(c).upper() or "CDR" in str(c).upper()), None)
            c_mar = next((c for c in df.columns if "MARCA" in str(c).upper()), None)
            c_mod = next((c for c in df.columns if "MODELO" in str(c).upper() or "VEH" in str(c).upper()), None)
            c_des = next((c for c in df.columns if "DESCRIPCI" in str(c).upper() or "REFACCI" in str(c).upper()), None)
            c_est = next((c for c in df.columns if "ESTATUS" in str(c).upper() and "ENV" not in str(c).upper() and "PAGO" not in str(c).upper()), None)

            if c_sin:
                for _, r in df.drop_duplicates(subset=[c_sin]).iterrows():
                    s_k = str(r.get(c_sin, '')).strip().upper().removesuffix('.0')
                    if not s_k or s_k == "NAN":
                        continue
                    mapa_info[s_k] = {
                        "taller": str(r.get(c_tal, '')).strip() if c_tal else "",
                        "marca": str(r.get(c_mar, '')).strip() if c_mar else "",
                        "modelo": str(r.get(c_mod, '')).strip() if c_mod else ""
                    }

                inactivos = {"CANCELADO", "RECIBIDO", "FACTURADO", "REEMBOLSADO", "PÉRDIDA TOTAL", "PERDIDA TOTAL", "PAGO DE DAÑOS", "PAGO DE DANOS"}
                df_act = df[~df[c_est].astype(str).str.strip().str.upper().isin(inactivos)].copy() if c_est else df.copy()
                for sid_val, grp in df_act.groupby(c_sin):
                    sid = str(sid_val).strip().removesuffix('.0')
                    if not sid or sid.upper() == "NAN":
                        continue
                    r0 = grp.iloc[0]
                    m_v = str(r0.get(c_mar, '')).strip() if c_mar else ""
                    mod_v = str(r0.get(c_mod, '')).strip() if c_mod else ""
                    veh_s = mod_v if mod_v.upper().startswith(m_v.upper()) else f"{m_v} {mod_v}".strip()
                    lista_activos.append(f"{sid} | {veh_s}" if veh_s else sid)
                    if c_des:
                        pzas = sorted(list({str(x).strip() for x in grp[c_des].dropna().tolist() if str(x).strip()}))
                        mapa_piezas[sid] = pzas
                lista_activos = sorted(list(set(lista_activos)))
    except Exception:
        pass
    return mapa_info, mapa_piezas, lista_activos

@st.cache_data(ttl=25)
def leer_tareas_normalizadas():
    try:
        datos = leer_hoja_con_reintento("Gestor_Tareas")
        if len(datos) <= 1:
            return pd.DataFrame(), []
        headers = [str(h).strip() for h in datos[0]]
        headers_up = [h.upper().rstrip(':') for h in headers]

        def idx_col(nombres):
            for n in nombres:
                if n.upper() in headers_up:
                    return headers_up.index(n.upper())
            return -1

        c_id = idx_col(["ID_TAREA", "ID"])
        c_fec = idx_col(["FECHA_CREACION", "CREATED_AT"])
        c_emi = idx_col(["EMISOR"])
        c_rec = idx_col(["RECEPTOR"])
        c_ref = idx_col(["SINIESTRO / TALLER / PIEZAS", "REFERENCIA"])
        c_ins = idx_col(["INSTRUCCION", "MENSAJE"])
        c_sta = idx_col(["STATUS", "ESTATUS"])
        c_res = idx_col(["RESPUESTA"])

        filas_limpias = []
        for idx_f, f in enumerate(datos[1:], start=2):
            if not any(str(x).strip() for x in f):
                continue
            f_ext = list(f) + [""] * max(0, len(headers) - len(f))
            st_normal = str(f_ext[c_sta]).strip() if c_sta >= 0 else ""
            filas_limpias.append({
                'GS_Row': idx_f,
                'ID_Tarea': str(f_ext[c_id]).strip() if c_id >= 0 else "",
                'Fecha_Creacion': str(f_ext[c_fec]).strip() if c_fec >= 0 else "",
                'Emisor': str(f_ext[c_emi]).strip() if c_emi >= 0 else "",
                'Receptor': str(f_ext[c_rec]).strip() if c_rec >= 0 else "",
                'Siniestro / Taller / Piezas': str(f_ext[c_ref]).strip() if c_ref >= 0 else "",
                'Instruccion': str(f_ext[c_ins]).strip() if c_ins >= 0 else "",
                'Status': st_normal,
                'Respuesta': str(f_ext[c_res]).strip() if c_res >= 0 else ""
            })
        return pd.DataFrame(filas_limpias), headers
    except Exception:
        return pd.DataFrame(), []

def actualizar_tarea_en_sheet(headers, row_data, nuevo_status, nuevo_historial):
    doc = init_connection()
    ws_tareas = doc.worksheet("Gestor_Tareas")
    headers_up = [str(h).strip().upper().rstrip(':') for h in headers]
    gs_row = int(row_data['GS_Row'])

    c_id = next((i for i, h in enumerate(headers_up) if h == "ID_TAREA"), 0)
    c_fec = next((i for i, h in enumerate(headers_up) if h == "FECHA_CREACION"), 1)
    c_emi = next((i for i, h in enumerate(headers_up) if h == "EMISOR"), 2)
    c_rec = next((i for i, h in enumerate(headers_up) if h == "RECEPTOR"), 3)
    c_ref = next((i for i, h in enumerate(headers_up) if "SINIESTRO" in h), 4)
    c_ins = next((i for i, h in enumerate(headers_up) if "INSTRUCCION" in h), 5)
    c_sta = next((i for i, h in enumerate(headers_up) if h in ["STATUS", "ESTATUS"]), 6)
    c_res = next((i for i, h in enumerate(headers_up) if "RESPUESTA" in h), 7)

    nueva_fila = [""] * len(headers)
    nueva_fila[c_id] = row_data.get('ID_Tarea', '')
    nueva_fila[c_fec] = row_data.get('Fecha_Creacion', '')
    nueva_fila[c_emi] = row_data.get('Emisor', '')
    nueva_fila[c_rec] = row_data.get('Receptor', '')
    nueva_fila[c_ref] = row_data.get('Siniestro / Taller / Piezas', '')
    nueva_fila[c_ins] = row_data.get('Instruccion', '')
    nueva_fila[c_sta] = nuevo_status
    nueva_fila[c_res] = nuevo_historial

    celdas = [gspread.Cell(row=gs_row, col=col_i + 1, value=val) for col_i, val in enumerate(nueva_fila)]
    ws_tareas.update_cells(celdas, value_input_option='USER_ENTERED')

@st.cache_data(ttl=300)
def cargar_fotos_chat_sheets():
    mapa_adjuntos = {}
    try:
        filas = leer_hoja_con_reintento("BD_CHAT_IMAGENES")
        if len(filas) > 1:
            for r in filas[1:]:
                if len(r) >= 4 and str(r[0]).strip():
                    id_f = str(r[0]).strip().upper()
                    b64_full = "".join([str(c).strip() for c in r[3:] if str(c).strip()])
                    if b64_full:
                        if not b64_full.startswith("data:"):
                            b64_full = f"data:image/jpeg;base64,{b64_full}"
                        mapa_adjuntos[id_f] = b64_full
    except Exception:
        pass
    return mapa_adjuntos

def depurar_adjuntos_antiguos_chat(ws_img, dias_vigencia=5):
    try:
        filas = ws_img.get_all_values()
        if len(filas) <= 1:
            return
        ahora_d = datetime.datetime.now(TZ_MX).replace(tzinfo=None)
        vigentes = [filas[0]]
        hubo_borrados = False
        for r in filas[1:]:
            if not any(str(x).strip() for x in r):
                continue
            f_str = str(r[1]).strip() if len(r) > 1 else ""
            conservar = True
            if f_str:
                try:
                    dt_f = datetime.datetime.strptime(f_str[:16], "%d/%m/%Y %H:%M")
                    if (ahora_d - dt_f).days >= dias_vigencia:
                        conservar = False
                        hubo_borrados = True
                except Exception:
                    pass
            if conservar:
                vigentes.append(r)
        if hubo_borrados:
            ws_img.clear()
            ws_img.update(range_name="A1", values=vigentes, value_input_option="RAW")
    except Exception:
        pass

def guardar_adjunto_chat_en_sheet(archivo_bytes, nombre_archivo, autor, depurar=True):
    ext = os.path.splitext(str(nombre_archivo or "").lower())[1]
    es_imagen = ext in [".png", ".jpg", ".jpeg", ".webp"]

    if es_imagen:
        img = Image.open(io.BytesIO(archivo_bytes))
        if img.mode in ("RGBA", "P"):
            fondo = Image.new("RGB", img.size, (11, 20, 26))
            if img.mode == "P":
                img = img.convert("RGBA")
            fondo.paste(img, mask=img.split()[3] if len(img.split()) > 3 else None)
            img = fondo
        else:
            img = img.convert("RGB")
        img.thumbnail((950, 950), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=74, optimize=True)
        data_uri = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")
    else:
        if len(archivo_bytes) > 460 * 1024:
            raise ValueError("El documento supera el límite de 450 KB.")
        mimes = {
            ".pdf": "application/pdf",
            ".csv": "text/csv",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".xls": "application/vnd.ms-excel",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".doc": "application/msword"
        }
        mime_type = mimes.get(ext, "application/octet-stream")
        data_uri = f"data:{mime_type};base64," + base64.b64encode(archivo_bytes).decode("utf-8")

    partes = [data_uri[i:i+42000] for i in range(0, len(data_uri), 42000)]
    while len(partes) < 3:
        partes.append("")

    id_adj = str(uuid.uuid4().hex)[:6].upper()
    fecha_f = datetime.datetime.now(TZ_MX).strftime("%d/%m/%Y %H:%M")

    doc = init_connection()
    try:
        ws_img = doc.worksheet("BD_CHAT_IMAGENES")
    except Exception:
        ws_img = doc.add_worksheet(title="BD_CHAT_IMAGENES", rows=1000, cols=20)

    if depurar:
        depurar_adjuntos_antiguos_chat(ws_img, dias_vigencia=5)

    if not ws_img.row_values(1):
        ws_img.append_row(["ID_FOTO", "FECHA", "AUTOR", "PARTE_1", "PARTE_2", "PARTE_3"], value_input_option="USER_ENTERED")

    cols_necesarias = 3 + len(partes)
    if ws_img.col_count < cols_necesarias:
        ws_img.resize(cols=cols_necesarias)

    ws_img.append_row([id_adj, fecha_f, str(autor).strip()] + partes, value_input_option="RAW")
    st.session_state.setdefault("cache_fotos_chat_local", {})[id_adj] = data_uri
    cargar_fotos_chat_sheets.clear()

    nom_seguro = re.sub(r'[\[\]\|]', '', str(nombre_archivo or f"archivo{ext}")).strip()
    return f"[FOTO:{id_adj}]" if es_imagen else f"[DOC:{id_adj}|{nom_seguro}]"

@st.cache_data(ttl=600)
def cargar_stickers_locales():
    """Carga automáticamente todos los stickers (.webp, .png, .gif, .jpg) de la carpeta stickers/."""
    stickers = {}
    if not os.path.isdir(CARPETA_STICKERS):
        return stickers
    mimes_st = {
        ".webp": "image/webp",
        ".png": "image/png",
        ".gif": "image/gif",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg"
    }
    for fname in sorted(os.listdir(CARPETA_STICKERS)):
        ext = os.path.splitext(fname)[1].lower()
        if ext not in mimes_st:
            continue
        ruta = os.path.join(CARPETA_STICKERS, fname)
        if not os.path.isfile(ruta):
            continue
        stem = os.path.splitext(fname)[0].strip()
        clave = re.sub(r'[^A-Za-z0-9_-]', '_', stem).upper()
        try:
            with open(ruta, "rb") as f_s:
                b64_s = base64.b64encode(f_s.read()).decode("utf-8")
            stickers[clave] = {
                "clave": clave,
                "etiqueta": stem.replace("_", " ").replace("-", " ").title(),
                "path": ruta,
                "data_uri": f"data:{mimes_st[ext]};base64,{b64_s}"
            }
        except Exception:
            continue
    return stickers

def reproducir_tono_nuevo_msg():
    components.html("""
        <script>
        try {
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.type = 'sine';
            osc.frequency.setValueAtTime(880, ctx.currentTime);
            osc.frequency.exponentialRampToValueAtTime(1320, ctx.currentTime + 0.14);
            gain.gain.setValueAtTime(0.18, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.42);
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.start();
            osc.stop(ctx.currentTime + 0.42);
        } catch (e) {}
        </script>
    """, height=0)

# ==============================================================================
# === 5. RENDER DEL HILO DE MENSAJES (CON STICKERS SIN BURBUJA Y ZOOM) ===
# ==============================================================================
def renderizar_hilo_chat_movil(row, usuario_real, grupos_identidad, stickers_map):
    texto_completo = f"{row.get('Instruccion', '')} {row.get('Respuesta', '')}"
    mapa_fotos = {}
    if "[FOTO:" in texto_completo or "[DOC:" in texto_completo:
        mapa_fotos.update(cargar_fotos_chat_sheets())
        mapa_fotos.update(st.session_state.get("cache_fotos_chat_local", {}))

    def formatear_cuerpo(
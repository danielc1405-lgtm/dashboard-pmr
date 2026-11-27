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

    def formatear_cuerpo(txt_crudo):
        txt_str = str(txt_crudo or "").strip()
        m_solo_st = re.fullmatch(r'\[STICKER:([A-Za-z0-9_-]+)\]', txt_str, flags=re.IGNORECASE)
        if m_solo_st:
            k_st = m_solo_st.group(1).strip().upper()
            info_st = stickers_map.get(k_st)
            if info_st:
                return f'<img src="{info_st["data_uri"]}" class="chat-sticker-solo" alt="{html.escape(k_st)}" />', True
            return f'<span style="color:#8696A0; font-style:italic;">[🏷️ Sticker: {html.escape(k_st)}]</span>', False

        txt_esc = html.escape(txt_str).replace('\n', '<br>')

        def _rep_foto(m):
            id_f = m.group(1).strip().upper()
            src_f = mapa_fotos.get(id_f, "")
            if src_f:
                return f'<div class="img-wrap"><img src="{src_f}" class="chat-img" onclick="abrirZoom(this.src)" /></div>'
            return f'<span style="color:#8696A0; font-style:italic;">[📷 Imagen {id_f} expirada (>5 días)]</span>'

        def _rep_doc(m):
            id_d = m.group(1).strip().upper()
            nom_d = m.group(2).strip()
            src_d = mapa_fotos.get(id_d, "")
            ic = "📊" if any(x in nom_d.lower() for x in [".xls", ".csv"]) else ("📝" if ".doc" in nom_d.lower() else "📄")
            if src_d:
                return f'<div class="doc-card"><a href="{src_d}" download="{nom_d}" class="doc-link">{ic} <span>{nom_d}</span> <b>⬇️</b></a></div>'
            return f'<span style="color:#8696A0; font-style:italic;">[{ic} {nom_d} expirado]</span>'

        def _rep_sticker(m):
            k_st = m.group(1).strip().upper()
            info_st = stickers_map.get(k_st)
            if info_st:
                return f'<div class="img-wrap"><img src="{info_st["data_uri"]}" class="chat-sticker-inline" /></div>'
            return f'<span style="color:#8696A0;">[🏷️ {html.escape(k_st)}]</span>'

        txt_out = re.sub(r'\[FOTO:([A-Za-z0-9]+)\]', _rep_foto, txt_esc)
        txt_out = re.sub(r'\[DOC:([A-Za-z0-9]+)\|([^\]]+)\]', _rep_doc, txt_out)
        txt_out = re.sub(r'\[STICKER:([A-Za-z0-9_-]+)\]', _rep_sticker, txt_out, flags=re.IGNORECASE)
        return txt_out, False

    def armar_burbuja(autor, fecha, cuerpo_raw, es_mio):
        cuerpo_html, es_solo_sticker = formatear_cuerpo(cuerpo_raw)
        align = "flex-end" if es_mio else "flex-start"
        color_autor = "#53BDEB" if es_mio else "#00A884"
        header_h = f'<div class="author" style="color:{color_autor};">{html.escape(autor)} <span class="time">• {html.escape(fecha)}</span></div>' if autor else ""
        if es_solo_sticker:
            return (
                f'<div class="msg-row" style="justify-content:{align};">'
                f'<div class="sticker-wrap" style="align-items:{align};">'
                f'{header_h}{cuerpo_html}'
                f'</div></div>'
            )
        bg = "#005C4B" if es_mio else "#1F2C34"
        rad = "12px 2px 12px 12px" if es_mio else "2px 12px 12px 12px"
        return (
            f'<div class="msg-row" style="justify-content:{align};">'
            f'<div class="bubble" style="background-color:{bg}; border-radius:{rad};">'
            f'{header_h}<div class="txt">{cuerpo_html}</div>'
            f'</div></div>'
        )

    burbujas = []
    emisor_0 = str(row.get('Emisor', 'Usuario')).strip()
    fecha_0 = str(row.get('Fecha_Creacion', '')).strip()
    burbujas.append(armar_burbuja(emisor_0, fecha_0, row.get('Instruccion', ''), es_mismo_usuario(usuario_real, emisor_0, grupos_identidad)))

    historial_raw = str(row.get('Respuesta', '')).strip()
    if historial_raw and historial_raw.lower() not in ["none", "nan"]:
        for linea in historial_raw.replace('\\n', '\n').split('\n'):
            ll = linea.strip()
            if not ll:
                continue
            m = re.match(r'^\[(.*?)\]\s*([^:]+):\s*(.*)$', ll)
            if m:
                f_m, a_m, t_m = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
                es_m = es_mismo_usuario(usuario_real, a_m, grupos_identidad)
            else:
                f_m, a_m, t_m = "", "", ll
                es_m = es_mismo_usuario(usuario_real, ll, grupos_identidad)
            burbujas.append(armar_burbuja(a_m, f_m, t_m, es_m))

    iframe_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            html, body {{
                height: 100%; width: 100%;
                background: transparent;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                overflow: hidden;
            }}
            #chat-vp {{
                height: 100%; width: 100%;
                overflow-y: auto; overflow-x: hidden;
                background-color: #0B141A;
                background-image: radial-gradient(#1F2C34 1px, transparent 1px);
                background-size: 20px 20px;
                border: 1px solid #222E35;
                border-radius: 12px;
                padding: 12px 10px;
            }}
            .msg-row {{ display: flex; margin-bottom: 10px; width: 100%; }}
            .bubble {{
                color: #E9EDEF;
                padding: 8px 12px;
                max-width: 86%;
                box-shadow: 0 1px 2px rgba(0,0,0,0.45);
                word-wrap: break-word;
            }}
            .sticker-wrap {{ display: flex; flex-direction: column; max-width: 75%; }}
            .chat-sticker-solo {{
                width: 132px; max-width: 100%; height: auto;
                object-fit: contain;
                filter: drop-shadow(0 2px 6px rgba(0,0,0,0.55));
            }}
            .chat-sticker-inline {{
                width: 110px; height: auto; object-fit: contain;
            }}
            .author {{ font-size: 0.74rem; font-weight: 700; margin-bottom: 3px; }}
            .time {{ color: #8696A0; font-weight: normal; font-size: 0.68rem; }}
            .txt {{ font-size: 0.93rem; line-height: 1.4; }}
            .img-wrap {{ margin-top: 5px; margin-bottom: 3px; }}
            .chat-img {{
                max-width: 220px; max-height: 200px;
                border-radius: 8px;
                border: 1px solid rgba(255,255,255,0.18);
                cursor: zoom-in; display: block;
            }}
            .doc-card {{
                margin-top: 5px; background: rgba(0,0,0,0.3);
                border: 1px solid rgba(255,255,255,0.18);
                border-radius: 7px; padding: 7px 10px;
            }}
            .doc-link {{
                color: #E9EDEF; text-decoration: none; font-size: 0.85rem;
                display: flex; align-items: center; gap: 6px;
            }}
            #zoom-ov {{
                display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
                background: rgba(0,0,0,0.94); z-index: 9999;
                align-items: center; justify-content: center; flex-direction: column;
            }}
            #zoom-ov img {{ max-width: 95%; max-height: 80%; border-radius: 8px; }}
            #zoom-bar {{ margin-top: 10px; display: flex; gap: 12px; }}
            .zbtn {{
                background: #00A884; color: #fff; text-decoration: none;
                padding: 7px 16px; border-radius: 8px; font-size: 0.85rem; font-weight: 600;
            }}
        </style>
    </head>
    <body>
        <div id="chat-vp">{''.join(burbujas)}</div>
        <div id="zoom-ov" onclick="cerrarZoom()">
            <img id="zoom-img" src="" />
            <div id="zoom-bar">
                <a id="zoom-dl" class="zbtn" href="" download="foto_chat_pmr.jpg" onclick="event.stopPropagation();">⬇️ Descargar</a>
                <span class="zbtn" style="background:#374045;">✖ Cerrar</span>
            </div>
        </div>
        <script>
            const vp = document.getElementById('chat-vp');
            function bajar() {{ if (vp) {{ vp.scrollTop = vp.scrollHeight; }} }}
            bajar();
            window.addEventListener('load', bajar);
            setTimeout(bajar, 250);
            function abrirZoom(src) {{
                document.getElementById('zoom-img').src = src;
                document.getElementById('zoom-dl').href = src;
                document.getElementById('zoom-ov').style.display = 'flex';
            }}
            function cerrarZoom() {{
                document.getElementById('zoom-ov').style.display = 'none';
            }}
        </script>
    </body>
    </html>
    """
    components.html(iframe_html, height=430, scrolling=False)

# ==============================================================================
# === 6. CARGA DE DATOS COMUNES Y CONTROL DE PANTALLAS ===
# ==============================================================================
usuarios_reales, grupos_identidad = obtener_mapa_usuarios()
mapa_info_sin, mapa_piezas_sin, lista_siniestros = cargar_contexto_siniestros()
stickers_map = cargar_stickers_locales()

if 'pmr_vista_movil' not in st.session_state:
    st.session_state['pmr_vista_movil'] = 'bandeja'

def enviar_mensaje_movil(row_act, headers_t, texto_msg="", archivo_up=None, sticker_clave=None):
    tag_extra = ""
    if sticker_clave:
        tag_extra = f"[STICKER:{sticker_clave}]"
    elif archivo_up is not None:
        tag_extra = guardar_adjunto_chat_en_sheet(archivo_up.getvalue(), archivo_up.name, usuario_activo_real)

    texto_limpio = str(texto_msg or "").strip()
    cuerpo_msg = f"{tag_extra} {texto_limpio}".strip() if (tag_extra and texto_limpio) else (tag_extra or texto_limpio)
    if not cuerpo_msg:
        return False

    ahora_str = datetime.datetime.now(TZ_MX).strftime("%d/%m/%Y %H:%M")
    hist_prev = str(row_act.get('Respuesta', '')).strip()
    linea_nueva = f"[{ahora_str}] {usuario_activo_real}: {cuerpo_msg}"
    hist_final = f"{hist_prev}\n{linea_nueva}".strip() if hist_prev else linea_nueva

    soy_emi = es_mismo_usuario(usuario_activo_real, row_act.get('Emisor', ''), grupos_identidad)
    prox_status = "Pendiente" if soy_emi else "Resuelto"
    actualizar_tarea_en_sheet(headers_t, row_act, prox_status, hist_final)
    leer_tareas_normalizadas.clear()
    return True

# ==============================================================================
# === PANTALLA A: BANDEJA DE CONVERSACIONES ===
# ==============================================================================
if st.session_state['pmr_vista_movil'] == 'bandeja':
    c_h1, c_h2, c_h3 = st.columns([2.6, 0.7, 0.9], vertical_alignment="center")
    with c_h1:
        st.markdown(f"<div style='font-size:1.35rem; font-weight:800; color:#E9EDEF;'>💬 Chat PMR</div><div style='font-size:0.78rem; color:#8696A0;'>👤 {html.escape(usuario_activo_real)}</div>", unsafe_allow_html=True)
    with c_h2:
        if st.button("🔄", key="mob_btn_ref", help="Actualizar", use_container_width=True):
            leer_tareas_normalizadas.clear()
            cargar_fotos_chat_sheets.clear()
            cargar_stickers_locales.clear()
            st.rerun()
    with c_h3:
        if st.button("➕ Nuevo", key="mob_btn_nuevo", type="primary", use_container_width=True):
            st.session_state['pmr_vista_movil'] = 'nuevo'
            st.rerun()

    @st.fragment(run_every=30)
    def render_bandeja_viva():
        leer_tareas_normalizadas.clear()
        df_tareas, _ = leer_tareas_normalizadas()
        if df_tareas.empty:
            st.info("🎉 No tienes conversaciones activas por ahora.")
            return

        mask_mios = df_tareas.apply(
            lambda r: usuario_en_lista(usuario_activo_real, r.get('Receptor', ''), grupos_identidad)
            or es_mismo_usuario(usuario_activo_real, r.get('Emisor', ''), grupos_identidad),
            axis=1
        )
        df_mios = df_tareas[mask_mios].copy()
        chats_activos = df_mios[df_mios['Status'].astype(str).str.strip().str.lower().isin(['pendiente', 'resuelto'])].copy()
        chats_fin = df_mios[df_mios['Status'].astype(str).str.strip().str.lower() == 'finalizado'].copy()

        n_nuevos = 0
        if not chats_activos.empty:
            evs = chats_activos.apply(extraer_ultimo_evento_chat, axis=1)
            chats_activos['_dt_ult'] = [e[0] for e in evs]
            chats_activos['_hora'] = [e[1] for e in evs]
            chats_activos['_prio'] = chats_activos.apply(lambda r: 0 if requiere_atencion_chat(r, usuario_activo_real, grupos_identidad) else 1, axis=1)
            n_nuevos = int((chats_activos['_prio'] == 0).sum())

        prev_n = st.session_state.get('_mob_prev_pend', n_nuevos)
        if n_nuevos > prev_n:
            st.toast(f"🔔 ¡Tienes {n_nuevos} chat(s) con mensajes nuevos!", icon="💬")
            reproducir_tono_nuevo_msg()
        st.session_state['_mob_prev_pend'] = n_nuevos

        lbl_act = f"💬 Activos ({n_nuevos} nuevos)" if n_nuevos > 0 else f"💬 Activos ({len(chats_activos)})"
        t_act, t_fin = st.tabs([lbl_act, f"📁 Finalizados ({len(chats_fin)})"])

        with t_act:
            if chats_activos.empty:
                st.info("🎉 Todo al día. Toca **➕ Nuevo** para abrir una conversación.")
            else:
                cb1, cb2 = st.columns([1.6, 1.15], vertical_alignment="center")
                with cb1:
                    busq = st.text_input("Buscar:", placeholder="🔍 Siniestro, auto, taller...", label_visibility="collapsed", key="mob_busq").strip().lower()
                with cb2:
                    orden = st.selectbox("Orden:", ["🕐 Recientes", "🔴 Sin responder", "📅 Antiguos"], label_visibility="collapsed", key="mob_orden")

                if orden == "🕐 Recientes":
                    df_ord = chats_activos.sort_values(by=['_dt_ult', 'GS_Row'], ascending=[False, False])
                elif orden == "📅 Antiguos":
                    df_ord = chats_activos.sort_values(by=['_dt_ult', 'GS_Row'], ascending=[True, True])
                else:
                    df_ord = chats_activos.sort_values(by=['_prio', '_dt_ult', 'GS_Row'], ascending=[True, False, False])

                if busq:
                    def _match(r):
                        ref_t = str(r.get('Siniestro / Taller / Piezas', '')).lower()
                        sid_t = ref_t.split('|')[0].strip().upper().removesuffix('.0')
                        tall_t = str(mapa_info_sin.get(sid_t, {}).get('taller', '')).lower()
                        todo = f"{ref_t} {tall_t} {r.get('Emisor','')} {r.get('Receptor','')} {r.get('Instruccion','')} {r.get('Respuesta','')}".lower()
                        return all(p in todo for p in busq.split())
                    df_ord = df_ord[df_ord.apply(_match, axis=1)]

                with st.container(border=False, key="pmr_mob_bandeja"):
                    if df_ord.empty:
                        st.caption("Sin coincidencias para tu búsqueda.")
                    for _, fila_c in df_ord.iterrows():
                        gs_r = int(fila_c['GS_Row'])
                        ref_c = str(fila_c.get('Siniestro / Taller / Piezas', 'General')).strip()
                        icono = "🔴" if fila_c.get('_prio', 1) == 0 else "🟢"

                        if ref_c.lower().startswith("general"):
                            tit = ref_c.replace("General:", "").replace("GENERAL:", "").strip() or "Tema General"
                            if len(tit) > 34:
                                tit = tit[:33].rstrip() + "…"
                            l1 = f"{icono} 📌 {tit}"
                        else:
                            partes = [p.strip() for p in ref_c.split("|")]
                            sid = partes[0].removesuffix('.0')
                            info_s = mapa_info_sin.get(sid.upper(), {})
                            fb_auto = partes[1] if (len(partes) > 1 and not partes[1].startswith("⚙️")) else ""
                            auto_c = acortar_auto_chat(info_s.get("marca", ""), info_s.get("modelo", ""), fb_auto)
                            tall_c = acortar_taller_chat(info_s.get("taller", ""))
                            l1 = f"{icono} " + " · ".join([b for b in [sid, auto_c, tall_c] if b])

                        quienes = formatear_participantes_corto(fila_c.get('Emisor', ''), fila_c.get('Receptor', ''), usuario_activo_real, grupos_identidad)
                        hora_t = str(fila_c.get('_hora', '')).strip()
                        l2 = f"{quienes} · {hora_t}" if hora_t else quienes

                        if st.button(f"{l1}\n{l2}", key=f"mob_open_{gs_r}", use_container_width=True):
                            st.session_state['mob_chat_gs_row'] = gs_r
                            st.session_state['pmr_vista_movil'] = 'chat'
                            st.rerun(scope="app")

        with t_fin:
            if chats_fin.empty:
                st.caption("No hay conversaciones finalizadas.")
            else:
                cols_f = [c for c in ['Fecha_Creacion', 'Emisor', 'Receptor', 'Siniestro / Taller / Piezas'] if c in chats_fin.columns]
                st.dataframe(chats_fin[cols_f], hide_index=True, use_container_width=True)

    render_bandeja_viva()

# ==============================================================================
# === PANTALLA B: CONVERSACIÓN ACTIVA (PANTALLA COMPLETA) ===
# ==============================================================================
elif st.session_state['pmr_vista_movil'] == 'chat':
    df_tareas_c, headers_t = leer_tareas_normalizadas()
    gs_activo = st.session_state.get('mob_chat_gs_row')
    match_row = df_tareas_c[df_tareas_c['GS_Row'] == gs_activo] if (not df_tareas_c.empty and gs_activo is not None) else pd.DataFrame()

    if match_row.empty:
        st.warning("Esta conversación ya no está disponible.")
        if st.button("⬅️ Volver a Bandeja", use_container_width=True):
            st.session_state['pmr_vista_movil'] = 'bandeja'
            st.rerun()
        st.stop()

    row_activa = match_row.iloc[0]

    # Barra superior de navegación del chat
    ct1, ct2, ct3 = st.columns([1.2, 0.8, 1.2], vertical_alignment="center")
    with ct1:
        if st.button("⬅️ Chats", key="mob_back_bandeja", use_container_width=True):
            leer_tareas_normalizadas.clear()
            st.session_state['pmr_vista_movil'] = 'bandeja'
            st.rerun()
    with ct2:
        if st.button("🔄", key="mob_ref_chat", use_container_width=True):
            leer_tareas_normalizadas.clear()
            cargar_fotos_chat_sheets.clear()
            st.rerun()
    with ct3:
        with st.popover("🏁 Finalizar", use_container_width=True):
            st.caption("¿Cerrar y archivar este chat?")
            if st.button("✅ Sí, finalizar", key=f"mob_conf_fin_{gs_activo}", type="primary", use_container_width=True):
                actualizar_tarea_en_sheet(headers_t, row_activa, "Finalizado", str(row_activa.get('Respuesta', '')).strip())
                leer_tareas_normalizadas.clear()
                st.session_state['pmr_vista_movil'] = 'bandeja'
                st.toast("Chat archivado", icon="🏁")
                st.rerun()

    # Tarjeta de encabezado del siniestro/grupo
    ref_full = str(row_activa.get("Siniestro / Taller / Piezas", "General")).strip()
    sid_h = ref_full.split("|")[0].strip().upper().removesuffix('.0')
    taller_h = mapa_info_sin.get(sid_h, {}).get("taller", "")
    rec_h = str(row_activa.get("Receptor", "N/A")).strip()
    lbl_rec = "👥 <b>Grupo:</b>" if "," in rec_h else "🎯 <b>Para:</b>"
    html_tall = f"<br>🏢 <b>Taller:</b> {html.escape(taller_h)}" if taller_h else ""
    st.markdown(
        f'<div style="background:#1F2C34; padding:9px 12px; border-radius:10px; margin-bottom:6px; border-left:4px solid #00A884;">'
        f'<div style="font-size:0.92rem; font-weight:700; color:#E9EDEF;">🚗 {html.escape(ref_full)}</div>'
        f'<div style="font-size:0.76rem; color:#9BAAB3; margin-top:2px;">'
        f'👤 <b>De:</b> {html.escape(str(row_activa.get("Emisor", "")))}  |  {lbl_rec} {html.escape(rec_h)}{html_tall}'
        f'</div></div>',
        unsafe_allow_html=True
    )

    # Hilo en vivo con auto-refresco cada 25s sin interrumpir la escritura
    @st.fragment(run_every=25)
    def render_hilo_vivo_movil(gs_id):
        leer_tareas_normalizadas.clear()
        df_live, _ = leer_tareas_normalizadas()
        m_live = df_live[df_live['GS_Row'] == gs_id] if not df_live.empty else pd.DataFrame()
        if m_live.empty:
            st.caption("Conversación cerrada o eliminada.")
            return
        r_live = m_live.iloc[0]
        resp_txt = str(r_live.get('Respuesta', '')).strip()
        k_len = f"_mob_len_{gs_id}"
        prev_len = st.session_state.get(k_len, len(resp_txt))
        if len(resp_txt) > prev_len:
            _, _, ult_a = extraer_ultimo_evento_chat(r_live)
            if ult_a and not es_mismo_usuario(usuario_activo_real, ult_a, grupos_identidad):
                st.toast(f"💬 Nuevo mensaje de {ult_a}", icon="🔔")
                reproducir_tono_nuevo_msg()
        st.session_state[k_len] = len(resp_txt)
        renderizar_hilo_chat_movil(r_live, usuario_activo_real, grupos_identidad, stickers_map)

    render_hilo_vivo_movil(gs_activo)

    # Barra de escritura, adjuntos (cámara/galería/docs) y stickers
    ver_up_k = f"mob_ver_up_{gs_activo}"
    if ver_up_k not in st.session_state:
        st.session_state[ver_up_k] = 0
    k_inp = f"mob_inp_{gs_activo}"
    k_up = f"mob_up_{gs_activo}_{st.session_state[ver_up_k]}"

    def enviar_mob_cb():
        txt = st.session_state.get(k_inp, "").strip()
        arch = st.session_state.get(k_up, None)
        if not txt and arch is None:
            return
        try:
            df_cur, h_cur = leer_tareas_normalizadas()
            m_cur = df_cur[df_cur['GS_Row'] == gs_activo]
            if not m_cur.empty:
                enviar_mensaje_movil(m_cur.iloc[0], h_cur, texto_msg=txt, archivo_up=arch)
                st.session_state[k_inp] = ""
                st.session_state[ver_up_k] = st.session_state.get(ver_up_k, 0) + 1
        except Exception as e_s:
            st.toast(f"No se pudo enviar: {e_s}", icon="⚠️")

    with st.container(border=True, key="pmr_mob_composer"):
        cm1, cm2 = st.columns([3.4, 1.0], vertical_alignment="bottom")
        with cm1:
            st.text_input("Mensaje:", key=k_inp, placeholder="Escribe un mensaje...", label_visibility="collapsed")
        with cm2:
            st.button("📤", key=f"mob_send_{gs_activo}", type="primary", use_container_width=True, on_click=enviar_mob_cb)

        ca1, ca2 = st.columns([1.4, 1.0], vertical_alignment="center")
        with ca1:
            arch_sel = st.file_uploader(
                "Adjuntar:",
                type=["png", "jpg", "jpeg", "webp", "pdf", "docx", "doc", "xlsx", "xls", "csv"],
                key=k_up,
                label_visibility="collapsed"
            )
        with ca2:
            with st.popover("😀 Stickers", use_container_width=True):
                if not stickers_map:
                    st.caption("Aún no hay stickers cargados. Sube imágenes `.webp`, `.png` o `.gif` a la carpeta `stickers/` en GitHub.")
                else:
                    claves_st = list(stickers_map.keys())
                    cols_st = st.columns(3)
                    for idx_s, k_st in enumerate(claves_st):
                        info_s = stickers_map[k_st]
                        with cols_st[idx_s % 3]:
                            st.image(info_s["path"], use_container_width=True)
                            if st.button(info_s["etiqueta"][:11], key=f"mob_st_{gs_activo}_{k_st}", use_container_width=True):
                                df_cur, h_cur = leer_tareas_normalizadas()
                                m_cur = df_cur[df_cur['GS_Row'] == gs_activo]
                                if not m_cur.empty:
                                    enviar_mensaje_movil(m_cur.iloc[0], h_cur, sticker_clave=k_st)
                                    st.rerun()

    if arch_sel is not None:
        ext_a = os.path.splitext(arch_sel.name.lower())[1]
        if ext_a in [".png", ".jpg", ".jpeg", ".webp"]:
            st.image(arch_sel, caption=f"✅ {arch_sel.name} — Pulsa 📤 para enviar", width=150)
        else:
            st.info(f"📎 Listo ({round(len(arch_sel.getvalue())/1024, 1)} KB): **{arch_sel.name}** — Pulsa **📤**")

    # Expander discreto para borrar mensaje enviado por error
    hist_del = str(row_activa.get('Respuesta', '')).strip()
    lineas_del = [l.strip() for l in hist_del.replace('\\n', '\n').split('\n') if l.strip() and l.strip().lower() not in ["none", "nan"]]
    opc_del = [f"0. [Inicial] {row_activa.get('Emisor', '')}: {row_activa.get('Instruccion', '')}"]
    for i_l, lt in enumerate(lineas_del, start=1):
        opc_del.append(f"{i_l}. {lt}")

    with st.expander("🗑️ Borrar mensaje enviado por error", expanded=False):
        sel_del = st.selectbox("Mensaje a eliminar:", options=opc_del, index=len(opc_del)-1, key=f"mob_sel_del_{gs_activo}")
        if st.button("🗑️ Eliminar Línea", key=f"mob_btn_del_{gs_activo}", use_container_width=True):
            idx_b = int(sel_del.split(".")[0].strip())
            row_mod = row_activa.to_dict()
            if idx_b == 0:
                if lineas_del:
                    m_p = re.match(r'^\[(.*?)\]\s*([^:]+):\s*(.*)$', lineas_del[0])
                    row_mod['Instruccion'] = m_p.group(3).strip() if m_p else lineas_del[0]
                    actualizar_tarea_en_sheet(headers_t, row_mod, row_mod.get('Status', 'Pendiente'), "\n".join(lineas_del[1:]))
                else:
                    actualizar_tarea_en_sheet(headers_t, row_mod, "Eliminado", "")
                    st.session_state['pmr_vista_movil'] = 'bandeja'
            else:
                pos_l = idx_b - 1
                if 0 <= pos_l < len(lineas_del):
                    nuevas_l = [l for i, l in enumerate(lineas_del) if i != pos_l]
                    actualizar_tarea_en_sheet(headers_t, row_mod, row_mod.get('Status', 'Pendiente'), "\n".join(nuevas_l))
            leer_tareas_normalizadas.clear()
            st.rerun()

# ==============================================================================
# === PANTALLA C: CREAR NUEVO CHAT / GRUPO ===
# ==============================================================================
else:
    cn1, cn2 = st.columns([1.2, 2.8], vertical_alignment="center")
    with cn1:
        if st.button("⬅️ Volver", key="mob_back_new", use_container_width=True):
            st.session_state['pmr_vista_movil'] = 'bandeja'
            st.rerun()
    with cn2:
        st.markdown("<div style='font-size:1.15rem; font-weight:700; color:#E9EDEF;'>➕ Nuevo Chat / Grupo</div>", unsafe_allow_html=True)

    destinatarios = st.multiselect(
        "Participante(s) — 1 privado, varios para grupo:",
        options=usuarios_reales,
        placeholder="Selecciona uno o varios...",
        key="mob_nc_dest"
    )
    sin_sel = st.selectbox(
        "Tema / Siniestro (Activos):",
        ["Seleccionar...", "General (Tema Libre)"] + lista_siniestros,
        key="mob_nc_sin"
    )

    tema_libre = ""
    piezas_sel = []
    if sin_sel == "General (Tema Libre)":
        tema_libre = st.text_input("Asunto:", placeholder="Ej. Cotización urgente / Duda facturación", key="mob_nc_tema")
    elif sin_sel != "Seleccionar...":
        id_puro = sin_sel.split(" | ")[0].strip()
        pzas_disp = mapa_piezas_sin.get(id_puro, [])
        if pzas_disp:
            piezas_sel = st.multiselect("Pieza(s) implicada(s):", pzas_disp, key="mob_nc_pzas")

    msg_ini = st.text_area("Mensaje inicial:", key="mob_nc_msg", height=95)
    adj_ini = st.file_uploader(
        "📎 Adjuntar foto o documento (Opcional):",
        type=["png", "jpg", "jpeg", "webp", "pdf", "docx", "doc", "xlsx", "xls", "csv"],
        key="mob_nc_adj"
    )

    if st.button("📤 Iniciar Conversación", type="primary", use_container_width=True, key="mob_nc_send"):
        if destinatarios and sin_sel != "Seleccionar..." and (msg_ini.strip() or adj_ini is not None):
            try:
                id_t = str(uuid.uuid4().hex)[:6].upper()
                fecha_h = datetime.datetime.now(TZ_MX).strftime("%Y-%m-%d %H:%M")
                receptor_str = ", ".join(destinatarios)
                if sin_sel == "General (Tema Libre)":
                    ref_f = f"General: {tema_libre.strip()}" if tema_libre.strip() else "General"
                else:
                    ref_f = f"{sin_sel} | ⚙️ Piezas: {', '.join(piezas_sel)}" if piezas_sel else sin_sel

                tag_i = guardar_adjunto_chat_en_sheet(adj_ini.getvalue(), adj_ini.name, usuario_activo_real) if adj_ini is not None else ""
                cuerpo_i = f"{tag_i} {msg_ini.strip()}".strip() if (tag_i and msg_ini.strip()) else (tag_i or msg_ini.strip())

                doc = init_connection()
                ws_t = doc.worksheet("Gestor_Tareas")
                headers_t = [str(h).strip() for h in ws_t.row_values(1)]
                if not headers_t:
                    headers_t = ["ID_Tarea", "Fecha_Creacion", "Emisor", "Receptor", "Siniestro / Taller / Piezas", "Instruccion", "Status", "Respuesta"]
                h_up = [h.upper().rstrip(':') for h in headers_t]
                fila_n = [""] * len(headers_t)

                def _pos(posibles, dft):
                    for p in posibles:
                        if p in h_up:
                            return h_up.index(p)
                    return dft if dft < len(headers_t) else -1

                for idx_c, val_c in [
                    (_pos(["ID_TAREA"], 0), id_t),
                    (_pos(["FECHA_CREACION"], 1), fecha_h),
                    (_pos(["EMISOR"], 2), usuario_activo_real),
                    (_pos(["RECEPTOR"], 3), receptor_str),
                    (_pos(["SINIESTRO / TALLER / PIEZAS", "REFERENCIA"], 4), ref_f),
                    (_pos(["INSTRUCCION"], 5), cuerpo_i),
                    (_pos(["STATUS", "ESTATUS"], 6), "Pendiente"),
                    (_pos(["RESPUESTA"], 7), ""),
                ]:
                    if idx_c >= 0:
                        fila_n[idx_c] = val_c

                ws_t.append_row(fila_n, value_input_option='USER_ENTERED')
                leer_tareas_normalizadas.clear()
                df_post, _ = leer_tareas_normalizadas()
                m_new = df_post[df_post['ID_Tarea'] == id_t] if not df_post.empty else pd.DataFrame()
                if not m_new.empty:
                    st.session_state['mob_chat_gs_row'] = int(m_new.iloc[-1]['GS_Row'])
                    st.session_state['pmr_vista_movil'] = 'chat'
                else:
                    st.session_state['pmr_vista_movil'] = 'bandeja'
                st.toast(f"✅ Chat iniciado con {receptor_str}", icon="💬")
                st.rerun()
            except Exception as e_nc:
                st.error(f"❌ Error al crear chat: {e_nc}")
        else:
            st.warning("⚠️ Selecciona al menos un participante, el tema/siniestro y escribe un mensaje o adjunta un archivo.")
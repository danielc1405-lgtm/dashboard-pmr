# ==============================================================================
# === [BLOQUE 1: IMPORTS, CONFIGURACIÓN VISUAL Y CSS] ===
# ==============================================================================
import streamlit as st
import pandas as pd
import warnings
import time
import os
import datetime
import tempfile
import base64
from fpdf import FPDF
import plotly.express as px
import gspread
import json
import re
from google.oauth2.service_account import Credentials

warnings.filterwarnings("ignore")

# ESTA LÍNEA DEBE SER SIEMPRE LA NÚMERO 1 DE STREAMLIT
st.set_page_config(page_title="Dashboard PMR - Operación", page_icon="📦", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
        [data-testid="stDataFrame"] { zoom: 0.95; }
        
        /* 1. Aniquilar por completo el padding fantasma superior de Streamlit */
        .main .block-container, div[data-testid="stAppViewBlockContainer"] { 
            padding-top: 0rem !important; 
            padding-bottom: 40px !important; 
            padding-left: 1rem !important; 
            padding-right: 1rem !important; 
            max-width: 100% !important; 
            overflow: visible !important; 
        }
        
        div[data-testid="stVerticalBlock"] {
            overflow: visible !important;
        }
        
        /* 2. Destruir el espacio reservado del header nativo */
        header[data-testid="stHeader"] { 
            display: none !important;
        }
        
        /* --- 3. CINTURÓN DE SEGURIDAD PARA EL MENÚ SUPERIOR (STICKY) --- */
        div[data-testid="stVerticalBlock"] > div:has([data-testid="stRadio"]) {
            position: -webkit-sticky !important;
            position: sticky !important; 
            top: 0px !important; 
            z-index: 99999 !important; 
            background-color: #0E1117 !important; 
            padding-top: 10px !important; 
            padding-bottom: 10px !important; 
            border-bottom: 1px solid #333 !important;
            box-shadow: 0px 6px 15px rgba(0,0,0,0.6) !important;
            margin-top: -15px !important; 
        }
        
        div.row-widget.stRadio > div { flex-direction: row; gap: 8px; flex-wrap: wrap; }
        div.row-widget.stRadio > div > label { background-color: #1E1E24; padding: 6px 14px; border-radius: 6px; cursor: pointer; border: 1px solid #333; font-size: 0.95rem; transition: all 0.3s ease; }
        div.row-widget.stRadio > div > label:hover { border-color: #F63366; background-color: #2A2A35;}
        div.row-widget.stRadio > div > label[data-checked="true"] { background-color: #F63366; color: white; border-color: #F63366; }
        div.row-widget.stRadio > div > label > div:first-child { display: none; }
        
        /* ELIMINAR EL PARPADEO GRIS AL EDITAR CELDAS */
        [data-testid="stDataGrid"] { opacity: 1 !important; }
        .st-emotion-cache-1kyxreq { display: none !important; }
        div[data-testid="stAppViewContainer"] { transition: none !important; }
    </style>
""", unsafe_allow_html=True)


# ==============================================================================
# === [BLOQUE 2: CONEXIÓN TEMPRANA Y SISTEMA DE LOGIN] ===
# ==============================================================================
SHEET_ID = "10jrOsS054n0atMk8GxQilkXqm6LjsnrwPOZnSx8iDek"

@st.cache_resource
def init_connection():
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    cred_dict = json.loads(st.secrets["google_credentials"])
    credenciales = Credentials.from_service_account_info(cred_dict, scopes=scopes)
    cliente = gspread.authorize(credenciales)
    return cliente.open_by_key(SHEET_ID)

if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

if not st.session_state['autenticado']:
    st.markdown("<h1 style='text-align: center; color: #FF4B4B;'>🛡️ Acceso al Sistema PMR</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        with st.form("login_form"):
            usuario_input = st.text_input("👤 Usuario").strip().lower()
            password_input = st.text_input("🔑 Contraseña", type="password")
            btn_login = st.form_submit_button("Entrar al Dashboard", use_container_width=True)
            
            if btn_login:
                try:
                    doc = init_connection()
                    ws_usuarios = doc.worksheet("Usuarios") 
                    df_usuarios = pd.DataFrame(ws_usuarios.get_all_records())
                    df_usuarios['Usuario'] = df_usuarios['Usuario'].astype(str).str.strip().str.lower()
                    df_usuarios['Password'] = df_usuarios['Password'].astype(str).str.strip()
                    
                    match = df_usuarios[(df_usuarios['Usuario'] == usuario_input) & (df_usuarios['Password'] == password_input)]
                    if not match.empty:
                        st.session_state['autenticado'] = True
                        st.session_state['usuario_actual'] = match.iloc[0]['Nombre Completo']
                        st.session_state['rol_actual'] = match.iloc[0]['Rol']
                        st.rerun()
                    else:
                        st.error("❌ Usuario o contraseña incorrectos.")
                except Exception as e:
                    st.error(f"Error al conectar con la base de usuarios: {e}")
    st.stop() 

usuario_activo = str(st.session_state.get('usuario_actual', '')).strip().upper()
rol_activo = str(st.session_state.get('rol_actual', '')).strip().upper()
permiso_edicion = st.session_state.get('permiso_edicion', True)

# ==============================================================================
# === [BLOQUE 3: MENÚ SUPERIOR Y NAVEGACIÓN] ===
# ==============================================================================
modo_consulta = False

opciones_menu = [
    "📊 Analítico", "⚙️ Panel Operativo", "🛒 Compras", "🏢 Directorio", 
    "📦 Inventario", "📝 Remisiones", "🧾 Facturación", "🚚 Rutas", "Precios Promedio", "🔍 Consultas", "🛠️ Cuartel General"
]

# El parámetro vertical_alignment="center" alinea todo a la misma altura
col_logo, col_menu, col_aseg, col_btn_ref, col_btn = st.columns([1.2, 5.5, 1.5, 0.4, 1.2], vertical_alignment="center")

with col_logo:
    try: 
        st.image("logo.png", use_column_width=True)
    except: 
        st.markdown("**PREMIER**")

with col_menu:
    vista_actual = st.radio("Navegación", opciones_menu, horizontal=True, label_visibility="collapsed")

with col_aseg:
    # Quitamos "📝 Remisiones" de esta lista para que el selector desaparezca en esa pestaña
    # y nos permita ver todas las aseguradoras a la vez.
    vistas_con_aseguradora = ["📊 Analítico", "⚙️ Panel Operativo", "🛒 Compras", "🧾 Facturación", "🔍 Consultas"]
    if vista_actual in vistas_con_aseguradora:
        aseguradora_sel = st.selectbox("Aseguradora", ["Multiasistencias", "GNP"], label_visibility="collapsed")
    else:
        aseguradora_sel = "MULTI" 

with col_btn_ref:
    if st.button("🔄", help="Forzar recarga de datos desde Google Sheets"):
        st.cache_data.clear()
        st.rerun()

with col_btn:
    btn_guardar = st.button("💾 Guardar", type="primary", use_container_width=True)
    espacio_spinner = st.empty()

# ==============================================================================
# === [BLOQUE 4: CARGA Y PROCESAMIENTO DE DATOS] ===
# ==============================================================================
def obtener_dataframe(nombre_hoja, silent=False):
    try:
        doc = init_connection()
        ws = doc.worksheet(nombre_hoja)
        datos = ws.get_all_values()
        if not datos: return pd.DataFrame()
        headers = [str(h).strip() for h in datos[0]]
        df = pd.DataFrame(datos[1:], columns=headers)
        return df
    except Exception as e:
        if not silent: st.error(f"Error cargando hoja {nombre_hoja}: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=600)  
def cargar_datos():
    df_uni = obtener_dataframe("BD_UNIFICADA")
    df_hist = obtener_dataframe("BD_HISTORICO", silent=True)
    
    if not df_hist.empty:
        df_uni = pd.concat([df_uni, df_hist], ignore_index=True)
        
    df_comp = obtener_dataframe("BD_COMPRAS", silent=True)
    df_cat = obtener_dataframe("BD_TALLERES", silent=True)
    if df_cat.empty: df_cat = obtener_dataframe("Catálogo", silent=True)
    try: 
        df_inv = obtener_dataframe("BD_INVENTARIO", silent=True)
        if not df_inv.empty and 'Sin Existencia' in df_inv.columns:
            df_inv['Sin Existencia'] = df_inv['Sin Existencia'].astype(str).str.strip().str.upper().isin(['TRUE', 'SI', '1', 'X', 'V', 'VERDADERO'])
    except: df_inv = pd.DataFrame()
    df_prov = obtener_dataframe("BD_PROVEEDORES", silent=True)
    
    if not df_uni.empty and 'Siniestro Relacionado' in df_uni.columns: 
        df_uni.rename(columns={'Siniestro Relacionado': 'Siniestro'}, inplace=True)
        
    return df_uni, df_comp, df_cat, df_inv, df_prov

df_completo, df_compras, df_catalogo, df_inventario, df_proveedores = cargar_datos()

aseguradora_filtro = aseguradora_sel.strip().upper()
palabra_clave_aseg = "MULTI" if "MULTI" in aseguradora_filtro else "GNP"

if not df_completo.empty:
    col_aseg_val = next((c for c in df_completo.columns if "ASEGURADORA" in str(c).upper()), None)
    if col_aseg_val:
        df_trabajo_completo = df_completo[df_completo[col_aseg_val].astype(str).str.upper().str.contains(palabra_clave_aseg, na=False)].copy()
        if df_trabajo_completo.empty: df_trabajo_completo = df_completo.copy()
    else: df_trabajo_completo = df_completo.copy()
else: df_trabajo_completo = pd.DataFrame()

if not df_trabajo_completo.empty:
    col_id = next((c for c in df_trabajo_completo.columns if "SINIESTRO" in str(c).upper()), None)
    col_taller = next((c for c in df_trabajo_completo.columns if "TALLER" in str(c).upper()), None)
    if col_id and col_taller:
        df_trabajo_completo = df_trabajo_completo[df_trabajo_completo[col_id].astype(str).str.strip() != '']
        df_trabajo_completo = df_trabajo_completo[~df_trabajo_completo[col_id].astype(str).str.contains(r'[-_]{2,}')]
        df_trabajo_completo = df_trabajo_completo[~df_trabajo_completo[col_taller].astype(str).str.contains(r'[-_]{2,}')]
        
    col_marca = next((c for c in df_trabajo_completo.columns if "MARCA" in str(c).upper()), None)
    col_modelo = next((c for c in df_trabajo_completo.columns if "MODELO" in str(c).upper()), None)
    col_ano = next((c for c in df_trabajo_completo.columns if "AÑO" in str(c).upper() or "ANO" in str(c).upper()), None)
    col_vin = next((c for c in df_trabajo_completo.columns if "VIN" in str(c).upper() or "SERIE" in str(c).upper()), None)
    col_desc = next((c for c in df_trabajo_completo.columns if "DESCRIPCI" in str(c).upper() or "REFACCI" in str(c).upper()), None)
    col_origen = next((c for c in df_trabajo_completo.columns if "ORIGEN" in str(c).upper()), None)
    col_cant = next((c for c in df_trabajo_completo.columns if "CANTIDAD" in str(c).upper() or "CANT" == str(c).upper()), None)
    col_precio = next((c for c in df_trabajo_completo.columns if "PRECIO" in str(c).upper() or "COSTO" in str(c).upper()), None)
    col_estatus = next((c for c in df_trabajo_completo.columns if "ESTATUS" in str(c).upper() or "STATUS" in str(c).upper()), None)
    col_vencimiento = next((c for c in df_trabajo_completo.columns if "VENCIMIENTO" in str(c).upper() or "PROMESA" in str(c).upper()), None)
    col_asignacion = next((c for c in df_trabajo_completo.columns if "ASIGNACI" in str(c).upper()), None)
    col_fecha_confi = next((c for c in df_trabajo_completo.columns if "FECHA CONFI" in str(c).upper()), None)
    col_paqueteria = next((c for c in df_trabajo_completo.columns if "PAQUETERIA" in str(c).upper() or "PAQUETERÍA" in str(c).upper()), None)
    col_guia = next((c for c in df_trabajo_completo.columns if "GUIA" in str(c).upper() or "GUÍA" in str(c).upper()), None)
    col_estatus_envio = next((c for c in df_trabajo_completo.columns if "ESTATUS ENV" in str(c).upper() or "RASTREO" in str(c).upper()), None)
    col_remision = next((c for c in df_trabajo_completo.columns if "REMISION" in str(c).upper() or "REMISIÓN" in str(c).upper()), None)
    col_comentarios = next((c for c in df_trabajo_completo.columns if "COMENTARIO" in str(c).upper() or "OBSERVACION" in str(c).upper()), None)
    col_aseg = col_aseg_val

    def estandarizar_fechas_mx(fecha_val):
        if pd.isna(fecha_val) or str(fecha_val).strip() in ['', 'None', 'nan', 'NaT']: return ""
        d_str = str(fecha_val).strip().lower().replace('-', '/')
        if re.match(r'^\d{2}/[a-z]{3}/\d{2}$', d_str): return d_str 
        if d_str.replace('.','',1).isdigit():
            val = float(d_str)
            if val > 30000:
                dt = pd.to_datetime('1899-12-30') + pd.to_timedelta(val, unit='D')
                meses = {1:'ene', 2:'feb', 3:'mar', 4:'abr', 5:'may', 6:'jun', 7:'jul', 8:'ago', 9:'sep', 10:'oct', 11:'nov', 12:'dic'}
                return f"{dt.day:02d}/{meses[dt.month]}/{dt.strftime('%y')}"
        meses_map = {'ene':'01', 'feb':'02', 'mar':'03', 'abr':'04', 'may':'05', 'jun':'06', 'jul':'07', 'ago':'08', 'sep':'09', 'oct':'10', 'nov':'11', 'dic':'12'}
        for text, num in meses_map.items():
            if text in d_str: 
                d_str = d_str.replace(text, num); break
        try:
            dt = pd.to_datetime(d_str, dayfirst=True)
            meses = {1:'ene', 2:'feb', 3:'mar', 4:'abr', 5:'may', 6:'jun', 7:'jul', 8:'ago', 9:'sep', 10:'oct', 11:'nov', 12:'dic'}
            return f"{dt.day:02d}/{meses[dt.month]}/{dt.strftime('%y')}"
        except: return str(fecha_val) 

    for c in [col_asignacion, col_vencimiento, col_fecha_confi]:
        if c and c in df_trabajo_completo.columns: df_trabajo_completo[c] = df_trabajo_completo[c].apply(estandarizar_fechas_mx)

    def armar_vehiculo(row):
        m = str(row.get(col_marca, '')).strip().upper()
        mod = str(row.get(col_modelo, '')).strip().upper()
        if mod.startswith(m) and m != "": vehiculo = mod
        else: vehiculo = f"{m} {mod}".strip()
        if col_ano:
            ano = str(row.get(col_ano, '')).strip()
            if ano.endswith('.0'): ano = ano[:-2]
            if ano not in ['', 'NAN', 'NONE']: vehiculo += f" | {ano}"
        if col_vin:
            vin = str(row.get(col_vin, '')).strip().upper()
            if vin not in ['', 'NAN', 'NONE']: vehiculo += f" | {vin}"
        return vehiculo

    df_trabajo_completo['Vehiculo_Info'] = df_trabajo_completo.apply(armar_vehiculo, axis=1)
    df_trabajo_completo['Filtro_Siniestro'] = df_trabajo_completo[col_id].astype(str).str.strip() + " | " + df_trabajo_completo['Vehiculo_Info']
    df_trabajo = df_trabajo_completo.copy()
    
    if modo_consulta: df_proceso = df_trabajo.copy()
    else: df_proceso = df_trabajo[~df_trabajo[col_estatus].astype(str).str.upper().str.contains("CANCELADO|RECIBIDO|FACTURADO|RECOLEC")].copy() if col_estatus else df_trabajo.copy()
        
    df_recoleccion_total = df_trabajo[df_trabajo[col_estatus].astype(str).str.upper().str.contains("RECOLEC")].copy() if col_estatus else pd.DataFrame()
else:
    col_id = col_taller = col_marca = col_modelo = col_desc = col_origen = col_cant = col_precio = col_estatus = col_vencimiento = col_asignacion = col_fecha_confi = col_paqueteria = col_guia = col_estatus_envio = col_remision = col_comentarios = col_aseg = None
    df_trabajo = df_proceso = df_recoleccion_total = pd.DataFrame()

# ==============================================================================
# === [BLOQUE 5: NOTIFICACIONES Y BANDEJA PDF] ===
# ==============================================================================
if 'pdfs_list' in st.session_state and st.session_state['pdfs_list']:
    st.success("🎉 ¡Remisión(es) generada(s) exitosamente!")
    if 'avisos_remision' in st.session_state and st.session_state['avisos_remision']:
        for aviso in st.session_state['avisos_remision']:
            st.warning(aviso)
        st.session_state['avisos_remision'] = [] 
    c_pdfs = st.columns(len(st.session_state['pdfs_list']) + 1)
    for i, pdf_data in enumerate(st.session_state['pdfs_list']):
        with c_pdfs[i]:
            st.download_button(label=f"📄 Descargar {pdf_data['folio']}", data=pdf_data['bytes'], file_name=pdf_data['nombre'], mime="application/pdf", type="primary", use_container_width=True)
    with c_pdfs[-1]:
        if st.button("🧹 Limpiar Bandeja", use_container_width=True):
            st.session_state['pdfs_list'] = []
            st.rerun()
    st.markdown("---")

df_editado_conf = pd.DataFrame(); df_editado_venc = pd.DataFrame(); df_editado_atrasadas = pd.DataFrame()
df_editado_cobro = pd.DataFrame(); df_editado_fact = pd.DataFrame(); df_editado = pd.DataFrame(); df_editado_reemb = pd.DataFrame()

lista_proveedores = [""]
if not df_proveedores.empty:
    for _, row_p in df_proveedores.iterrows():
        p_str = str(row_p.get('Proveedor', '')).strip().upper()
        s_str = str(row_p.get('Sucursal', '')).strip().upper()
        if p_str: lista_proveedores.append(f"{p_str} - {s_str}" if s_str else p_str)
    lista_proveedores = sorted(list(set(lista_proveedores)))

st.markdown("""
    <style>
    @keyframes destello_alerta { 0% { opacity: 1; transform: scale(1); } 50% { opacity: 0.3; transform: scale(0.99); } 100% { opacity: 1; transform: scale(1); } }
    .alerta-flash { animation: destello_alerta 0.7s ease-in-out 3; padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem; color: white; font-size: 1rem; }
    .alerta-warning { background-color: rgba(255, 170, 0, 0.2); border-left: 5px solid #ffaa00; }
    .alerta-info { background-color: rgba(0, 174, 239, 0.2); border-left: 5px solid #00AEEF; }
    </style>
""", unsafe_allow_html=True)

if not modo_consulta:
    if vista_actual == "⚙️ Panel Operativo":
        if col_estatus and not df_trabajo_completo.empty:
            pendientes_bot = len(df_trabajo_completo[df_trabajo_completo[col_estatus].astype(str).str.upper().str.contains("CONFIRMAR")])
            if pendientes_bot > 0: st.markdown(f'<div class="alerta-flash alerta-warning">🚨 <strong>¡ATENCIÓN!</strong> Han ingresado <strong>{pendientes_bot}</strong> partida(s) nueva(s) por confirmar.</div>', unsafe_allow_html=True)

    if vista_actual in ["⚙️ Panel Operativo", "🛒 Compras"]:
        if col_estatus and not df_trabajo_completo.empty:
            df_en_proceso_notif = df_trabajo_completo[df_trabajo_completo[col_estatus].astype(str).str.upper() == "EN PROCESAMIENTO"].copy()
            if not df_en_proceso_notif.empty:
                keys_compras = set()
                if not df_compras.empty:
                    c_sin = next((c for c in df_compras.columns if "SINIESTRO" in str(c).upper()), None)
                    c_desc = next((c for c in df_compras.columns if "DESCRIPCI" in str(c).upper()), None)
                    if c_sin and c_desc:
                        def clean_key(s, d):
                            sv = str(s).strip().upper()
                            if sv.endswith('.0'): sv = sv[:-2]
                            return f"{sv}_{' '.join(str(d).strip().upper().split())}"
                        keys_compras = set(df_compras.apply(lambda r: clean_key(r[c_sin], r[c_desc]), axis=1))
                
                def gen_key_notif(r):
                    sv = str(r.get(col_id, '')).strip().upper()
                    if sv.endswith('.0'): sv = sv[:-2]
                    return f"{sv}_{' '.join(str(r.get(col_desc, '')).strip().upper().split())}"
                    
                df_en_proceso_notif['tmp_key'] = df_en_proceso_notif.apply(gen_key_notif, axis=1)
                comprados_mask = df_en_proceso_notif['tmp_key'].isin(keys_compras)
                
                df_por_comprar = df_en_proceso_notif[~comprados_mask]
                pendientes_surtido = len(df_por_comprar)
                en_espera_prov = len(df_en_proceso_notif[comprados_mask])
                
                primer_nombre = str(usuario_activo).split()[0] if usuario_activo else "Usuario"
                texto_alertas = []
                if pendientes_surtido > 0: texto_alertas.append(f"<strong>{pendientes_surtido}</strong> pedido(s) por comprar")
                if en_espera_prov > 0: texto_alertas.append(f"<strong>{en_espera_prov}</strong> en espera de que lleguen al proveedor")
                
                if texto_alertas:
                    mensaje_final = f"🎯 <strong>¡Hola {primer_nombre}!</strong> Tienes " + " y ".join(texto_alertas) + "."
                    st.markdown(f'<div class="alerta-flash alerta-info">{mensaje_final}</div>', unsafe_allow_html=True)
                    
                    if pendientes_surtido > 0:
                        with st.expander(f"👀 Ver detalle de los {pendientes_surtido} pedidos pendientes de compra", expanded=False):
                            cols_to_show = [c for c in [col_id, 'Vehiculo_Info', col_taller, col_desc] if c in df_por_comprar.columns]
                            df_muestra = df_por_comprar[cols_to_show].copy()
                            df_muestra.rename(columns={col_id: 'Siniestro', 'Vehiculo_Info': 'Vehículo', col_taller: 'Taller', col_desc: 'Pieza'}, inplace=True)
                            st.dataframe(df_muestra, hide_index=True, use_container_width=True)

# ==============================================================================
# === [BLOQUE 6: VISTAS - ANALÍTICO Y OPERATIVO] ===
# ==============================================================================
import plotly.graph_objects as go

# Variables de tiempo globales para este bloque
tz_mx = datetime.timezone(datetime.timedelta(hours=-6))
hoy_dt_full = datetime.datetime.now(tz_mx)
meses_es = {1:'ene', 2:'feb', 3:'mar', 4:'abr', 5:'may', 6:'jun', 7:'jul', 8:'ago', 9:'sep', 10:'oct', 11:'nov', 12:'dic'}
hoy_str = f"{hoy_dt_full.day:02d}/{meses_es[hoy_dt_full.month]}/{hoy_dt_full.strftime('%y')}"
hoy_dt = pd.to_datetime(hoy_dt_full.date())

def parse_dt_safe_op(val):
    if pd.isna(val) or str(val).strip() == '': return pd.NaT
    val_str = str(val).lower().replace('-', '/')
    if val_str.replace('.', '', 1).isdigit():
        v_num = float(val_str)
        if v_num > 30000: return pd.to_datetime('1899-12-30') + pd.to_timedelta(v_num, unit='D')
    meses_map = {'ene':'01', 'feb':'02', 'mar':'03', 'abr':'04', 'may':'05', 'jun':'06', 'jul':'07', 'ago':'08', 'sep':'09', 'oct':'10', 'nov':'11', 'dic':'12'}
    for m_es, m_num in meses_map.items():
        if m_es in val_str: val_str = val_str.replace(m_es, m_num); break
    try: return pd.to_datetime(val_str, dayfirst=True, errors='coerce')
    except: return pd.NaT

# --- INTERCEPTOR DE PAQUETERÍA (AUTOMATIZACIÓN "ENTREGADOS EN CDR") ---
# Se ejecuta antes de renderizar cualquier vista para afectar Analítico y Operativo
if not df_proceso.empty and col_estatus_envio and col_estatus:
    def verificar_entrega_paqueteria(row):
        rastreo = str(row.get(col_estatus_envio, '')).strip().lower()
        estatus_actual = str(row.get(col_estatus, '')).strip().upper()
        if "delivery" in rastreo or "entregado" in rastreo:
            if estatus_actual not in ["RECIBIDO", "FACTURADO", "CANCELADO", "REEMBOLSADO", "EN PROCESO DE REEMBOLSO", "EN PROCESO DE CAMBIO", "EN PROCESO DE RECOLECCIÓN", "PÉRDIDA TOTAL"]:
                return "ENTREGADO"
        return row[col_estatus]
        
    df_proceso[col_estatus] = df_proceso.apply(verificar_entrega_paqueteria, axis=1)
    df_trabajo[col_estatus] = df_trabajo.apply(verificar_entrega_paqueteria, axis=1)

# ------------------------------------------------------------------------------
# --- VISTA 1: ANALÍTICO ---
# ------------------------------------------------------------------------------
if vista_actual == "📊 Analítico":
    st.markdown("## 📊 Rendimiento de Operación")
    
    # --- PREPARACIÓN DE DATOS CRUZADOS (Proveedor, Costo) ---
    dict_prov_ana = {}; dict_costo_ana = {}
    if not df_compras.empty:
        c_sin_a = next((c for c in df_compras.columns if "SINIESTRO" in str(c).upper()), None)
        c_desc_a = next((c for c in df_compras.columns if "DESCRIPCI" in str(c).upper()), None)
        if c_sin_a and c_desc_a:
            def gen_llave_ana(s, d):
                sv = str(s).strip().upper()
                if sv.endswith('.0'): sv = sv[:-2]
                return f"{sv}_{' '.join(str(d).strip().upper().split())}"
            df_c_ana = df_compras.copy()
            df_c_ana['LLAVE'] = df_c_ana.apply(lambda r: gen_llave_ana(r.get(c_sin_a,''), r.get(c_desc_a,'')), axis=1)
            dict_prov_ana = dict(zip(df_c_ana['LLAVE'], df_c_ana['Proveedor']))
            def sf(x):
                try: return float(str(x).replace('$','').replace(',','').strip())
                except: return 0.0
            dict_costo_ana = dict(zip(df_c_ana['LLAVE'], df_c_ana['Costo Compra'].apply(sf)))

    # --- 1. VELOCIDAD LOGÍSTICA (INICIO: 4 DE SEPTIEMBRE 2026) ---
    st.markdown("#### ⏱️ 1. Velocidad Logística (Desde el 04/Sep/2026)")
    st.caption("Promedios de tiempo calculados con datos reales desde el inicio del uso del sistema.")
    if col_asignacion and col_fecha_confi and not df_completo.empty:
        df_vel = df_completo.copy()
        
        def buscar_col_ana(keywords):
            for c in df_vel.columns:
                c_up = str(c).upper().replace('Í','I').replace('Ó','O')
                if all(k in c_up for k in keywords): return c
            return None
            
        c_envio_a = buscar_col_ana(["FECHA", "ENVIO"])
        c_rec_a = buscar_col_ana(["FECHA", "RECIB"])
        c_fac_a = buscar_col_ana(["FECHA", "FACTUR"])
        
        df_vel['F_Asig_D'] = df_vel[col_asignacion].apply(parse_dt_safe_op)
        
        # Filtro: A partir del 4 de septiembre de 2026
        fecha_inicio_sistema = pd.to_datetime('2026-09-04')
        df_vel_mes = df_vel[df_vel['F_Asig_D'] >= fecha_inicio_sistema].copy()
        
        # Excluimos PT y Cancelados de la velocidad
        if col_estatus:
            df_vel_mes = df_vel_mes[~df_vel_mes[col_estatus].astype(str).str.upper().isin(["CANCELADO", "PÉRDIDA TOTAL"])]
        
        if not df_vel_mes.empty:
            df_vel_mes['F_Conf_D'] = df_vel_mes[col_fecha_confi].apply(parse_dt_safe_op)
            df_vel_mes['F_Env_D'] = df_vel_mes[c_envio_a].apply(parse_dt_safe_op) if c_envio_a else pd.NaT
            df_vel_mes['F_Rec_D'] = df_vel_mes[c_rec_a].apply(parse_dt_safe_op) if c_rec_a else pd.NaT
            df_vel_mes['F_Fac_D'] = df_vel_mes[c_fac_a].apply(parse_dt_safe_op) if c_fac_a else pd.NaT
            
            df_vel_mes['D_Asig_Conf'] = (df_vel_mes['F_Conf_D'] - df_vel_mes['F_Asig_D']).dt.days
            df_vel_mes['D_Conf_Env'] = (df_vel_mes['F_Env_D'] - df_vel_mes['F_Conf_D']).dt.days if c_envio_a else pd.Series(dtype=float)
            df_vel_mes['D_Env_Rec'] = (df_vel_mes['F_Rec_D'] - df_vel_mes['F_Env_D']).dt.days if c_envio_a and c_rec_a else pd.Series(dtype=float)
            df_vel_mes['D_Rec_Fac'] = (df_vel_mes['F_Fac_D'] - df_vel_mes['F_Rec_D']).dt.days if c_rec_a and c_fac_a else pd.Series(dtype=float)
            
            def prm(serie):
                v = serie[(serie >= 0) & (serie <= 100)]
                return round(v.mean(), 1) if not v.empty and pd.notna(v.mean()) else 0
                
            p1 = prm(df_vel_mes['D_Asig_Conf']); p2 = prm(df_vel_mes['D_Conf_Env'])
            p3 = prm(df_vel_mes['D_Env_Rec']); p4 = prm(df_vel_mes['D_Rec_Fac'])
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Asignación ➔ Confirmación", f"{p1} días", delta="- Óptimo" if p1 <= 3 else "+ Demorado", delta_color="inverse")
            m2.metric("Confirmación ➔ Envío", f"{p2} días", delta="- Óptimo" if p2 <= 5 else "+ Demorado", delta_color="inverse")
            m3.metric("Envío ➔ Recibido (CDR)", f"{p3} días", delta="- Óptimo" if p3 <= 3 else "+ Demorado", delta_color="inverse")
            m4.metric("Recibido ➔ Facturación", f"{p4} días", delta="- Óptimo" if p4 <= 5 else "+ Demorado", delta_color="inverse")
        else: st.info("No hay pedidos asignados desde el inicio del sistema para calcular la velocidad.")

    st.markdown("---")

    # --- 2. EMBUDO Y TOP MARCAS ---
    c_graf1, c_graf2 = st.columns([1, 1.2])
    with c_graf1:
        st.markdown("#### 🌪️ 2. Embudo de Operación (Activos)")
        if not df_proceso.empty:
            f_conf = len(df_proceso[df_proceso[col_estatus].astype(str).str.upper().str.contains("CONFIRMAR")])
            f_proc = len(df_proceso[df_proceso[col_estatus].astype(str).str.upper() == "EN PROCESAMIENTO"])
            f_tran = len(df_proceso[df_proceso[col_estatus].astype(str).str.upper() == "EN TRANSITO"])
            f_ent = len(df_proceso[df_proceso[col_estatus].astype(str).str.upper() == "ENTREGADO"])
            
            etapas_fun = ["Por Confirmar", "En Procesamiento", "En Tránsito", "Entregados a Taller"]
            valores_fun = [f_conf, f_proc, f_tran, f_ent]
            
            fig_funnel = go.Figure(go.Funnel(
                y=etapas_fun, x=valores_fun, textinfo="value+percent initial",
                marker={"color": ["#FF4B4B", "#FF9800", "#FFEB3B", "#4CAF50"]}
            ))
            fig_funnel.update_layout(margin=dict(t=20, b=20, l=0, r=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_funnel, use_container_width=True)
            
    with c_graf2:
        st.markdown("#### 🏆 3. Análisis Histórico por Marca (Top 4)")
        if col_marca and col_modelo and not df_completo.empty:
            df_m = df_completo.copy()
            c_asig_h = buscar_col_ana(["ASIGNACION"])
            c_env_h = buscar_col_ana(["FECHA", "ENVIO"])
            
            if c_asig_h and c_env_h:
                df_m['FA'] = df_m[c_asig_h].apply(parse_dt_safe_op); df_m['FE'] = df_m[c_env_h].apply(parse_dt_safe_op)
                df_m['D_AE'] = (df_m['FE'] - df_m['FA']).dt.days
            else: df_m['D_AE'] = pd.Series(dtype=float)
            
            df_m['M_Lim'] = df_m[col_marca].astype(str).str.strip().str.upper()
            df_m['Mod_Lim'] = df_m[col_modelo].astype(str).str.strip().str.upper()
            
            # Filtro para evitar marcas y modelos vacíos o "S/D"
            df_m = df_m[(df_m['M_Lim'] != '') & (df_m['M_Lim'] != 'NAN') & (df_m['M_Lim'] != 'S/D')]
            df_m = df_m[(df_m['Mod_Lim'] != '') & (df_m['Mod_Lim'] != 'NAN') & (df_m['Mod_Lim'] != 'S/D')]
            
            top_brands = df_m.groupby('M_Lim').agg(
                Siniestros=('M_Lim', 'count'),
                Prom_Dias=('D_AE', lambda x: x[(x>=0) & (x<=365)].mean())
            ).reset_index().sort_values('Siniestros', ascending=False).head(4)
            
            for _, b_row in top_brands.iterrows():
                b_name = b_row['M_Lim']
                b_tot = b_row['Siniestros']
                b_prom = round(b_row['Prom_Dias'], 1) if pd.notna(b_row['Prom_Dias']) else "N/A"
                
                df_mod = df_m[df_m['M_Lim'] == b_name]
                top_models = df_mod['Mod_Lim'].value_counts().head(3)
                modelos_str = ", ".join([f"{mod} ({cnt})" for mod, cnt in top_models.items()])
                
                with st.expander(f"🚗 **{b_name}** | {b_tot} Siniestros Históricos", expanded=True):
                    st.caption(f"**Modelos más movidos:** {modelos_str}")
                    st.markdown(f"**⏱️ Tiempo de Respuesta (Asignación ➔ Envío):** `{b_prom} días`")

    st.markdown("---")

    # --- 3. MONITOR LOGÍSTICO (AGRUPADO CON FECHAS Y RASTREO) ---
    st.markdown(f"#### 📋 4. Monitor Logístico en Curso ({aseguradora_sel.upper()})")
    st.caption("Visión depurada de refacciones activas, agrupadas por su estatus logístico actual.")
    
    if not df_proceso.empty:
        estatus_validos = ["ENTREGADO", "EN TRANSITO", "EN PROCESAMIENTO", "EN PROCESO DE REEMBOLSO", "EN PROCESO DE CAMBIO", "EN PROCESO DE RECOLECCIÓN"]
        df_mon = df_proceso[df_proceso[col_estatus].astype(str).str.upper().isin(estatus_validos)].copy()
        
        if not df_mon.empty:
            df_mon['LLAVE'] = df_mon.apply(lambda r: gen_llave_ana(r.get(col_id,''), r.get(col_desc,'')), axis=1)
            df_mon['Proveedor'] = df_mon['LLAVE'].map(dict_prov_ana).fillna("-")
            
            # Formateo de fechas para que no se vean feas
            c_env_disp = buscar_col_ana(["FECHA", "ENVIO"])
            c_rec_disp = buscar_col_ana(["FECHA", "RECIB"])
            
            for est in estatus_validos:
                df_est = df_mon[df_mon[col_estatus].astype(str).str.upper() == est]
                if not df_est.empty:
                    if est == "ENTREGADO":
                        titulo = f"📥 Entregados a Taller (Pedir Recepción) | {len(df_est)} Partidas"
                    elif est == "EN TRANSITO":
                        titulo = f"🚚 En Tránsito | {len(df_est)} Partidas"
                    else:
                        titulo = f"⚙️ {est.title()} | {len(df_est)} Partidas"
                        
                    with st.expander(titulo, expanded=(est in ["ENTREGADO", "EN TRANSITO"])):
                        cols_ver = [col_id, 'Vehiculo_Info', col_taller, col_desc, 'Proveedor']
                        
                        # Inyección de Guía, Paquetería, Rastreo y Fechas
                        if col_paqueteria and col_paqueteria in df_est.columns: cols_ver.append(col_paqueteria)
                        if col_guia and col_guia in df_est.columns: cols_ver.append(col_guia)
                        if col_estatus_envio and col_estatus_envio in df_est.columns: cols_ver.append(col_estatus_envio)
                        if c_env_disp and c_env_disp in df_est.columns: cols_ver.append(c_env_disp)
                        if c_rec_disp and c_rec_disp in df_est.columns: cols_ver.append(c_rec_disp)
                        
                        df_vista = df_est[cols_ver].copy()
                        
                        rename_dict = {
                            col_id: 'Siniestro', 'Vehiculo_Info': 'Auto', col_taller: 'Taller', 
                            col_desc: 'Pieza', col_paqueteria: 'Paquetería', col_guia: 'Guía', 
                            col_estatus_envio: 'Rastreo API'
                        }
                        if c_env_disp: rename_dict[c_env_disp] = 'F. Envío'
                        if c_rec_disp: rename_dict[c_rec_disp] = 'F. Entrega'
                        
                        df_vista.rename(columns=rename_dict, inplace=True)
                        st.dataframe(df_vista, use_container_width=True, hide_index=True)
        else: st.info("No hay pedidos activos en las etapas de flujo (Todos por confirmar o en PT).")
    else: st.info(f"No hay pedidos activos para {aseguradora_sel}.")

    st.markdown("---")
    
    # --- 4. PEDIDOS POR LLEGAR REDISEÑADO ---
    st.markdown("#### 📦 5. Próximos Arribos (Compras a Proveedores)")
    if not df_compras.empty:
        df_compras['Recibido_Bool'] = df_compras['Recibido'].astype(str).str.strip().str.upper().isin(['TRUE', 'SI', '1', 'YES', 'V', 'X'])
        df_c_llegar = df_compras[df_compras['Recibido_Bool'] == False].copy()
        if not df_c_llegar.empty:
            def parse_spanish_date_comp(d_str):
                if not isinstance(d_str, str): return pd.NaT
                d_str = d_str.lower().replace('-', '/') 
                meses = {'ene':'01', 'feb':'02', 'mar':'03', 'abr':'04', 'may':'05', 'jun':'06', 'jul':'07', 'ago':'08', 'sep':'09', 'oct':'10', 'nov':'11', 'dic':'12'}
                for text, num in meses.items():
                    if text in d_str: d_str = d_str.replace(text, num); break
                try: return pd.to_datetime(d_str, format='%d/%m/%y', errors='coerce')
                except: return pd.NaT

            df_c_llegar['Fecha_Compra_Dt'] = df_c_llegar['Fecha Compra'].apply(parse_spanish_date_comp)
            df_c_llegar['ETA'] = pd.to_numeric(df_c_llegar['Tiempo Entrega (Días)'], errors='coerce').fillna(0)
            df_c_llegar['Llegada_Calculada'] = df_c_llegar['Fecha_Compra_Dt'] + pd.to_timedelta(df_c_llegar['ETA'], unit='d')
            
            hoy_c = pd.to_datetime(datetime.datetime.now().date())
            df_c_llegar['Estatus'] = df_c_llegar['Llegada_Calculada'].apply(lambda x: "🔴 Atrasado" if pd.notna(x) and x < hoy_c else ("🟡 Vence Hoy" if pd.notna(x) and x == hoy_c else "🟢 En tiempo"))
            df_c_llegar['Llegada'] = df_c_llegar['Llegada_Calculada'].dt.strftime('%d/%b/%y').fillna('-')
            
            df_c_llegar['Orden'] = df_c_llegar['Llegada_Calculada'].apply(lambda x: (x - hoy_c).days if pd.notna(x) else 9999)
            df_c_llegar = df_c_llegar.sort_values(by=['Orden', 'Siniestro'], ascending=True)
            
            cols_llegar = [c for c in ['Siniestro', 'Taller', 'Descripción Pieza', 'Proveedor', 'ETA', 'Llegada', 'Estatus'] if c in df_c_llegar.columns or c in ['ETA', 'Llegada', 'Estatus']]
            st.dataframe(df_c_llegar[cols_llegar], use_container_width=True, hide_index=True)
        else: st.success("✅ Todos los pedidos a proveedores han sido recibidos en base.")

# ------------------------------------------------------------------------------
# --- VISTA 2: PANEL OPERATIVO ---
# ------------------------------------------------------------------------------
elif vista_actual == "⚙️ Panel Operativo":
    st.markdown("### 📈 Indicadores Diarios")
    
    col_sin_rel = next((c for c in df_proceso.columns if str(c).strip().upper() in ["SINIESTRO RELACIONADO", "SINIESTRO"]), None)
    
    def get_agrupador(row):
        rel = str(row.get(col_sin_rel, '')).strip() if col_sin_rel else ''
        if rel and rel.upper() not in ['NAN', 'NONE', '']: return rel
        return str(row.get(col_id, '')).strip()
        
    if not df_proceso.empty: df_proceso['Agrupador_Visual'] = df_proceso.apply(get_agrupador, axis=1)
    if not df_recoleccion_total.empty: df_recoleccion_total['Agrupador_Visual'] = df_recoleccion_total.apply(get_agrupador, axis=1)

    if col_vencimiento:
        fechas_venc_dt = df_proceso[col_vencimiento].apply(parse_dt_safe_op)
        vencidas_pasadas_kpi = len(df_proceso[(fechas_venc_dt < hoy_dt) & (df_proceso[col_vencimiento] != '') & (~df_proceso[col_estatus].astype(str).str.upper().str.contains("CONFIRMAR"))])
    else: vencidas_pasadas_kpi = 0
        
    vencen_hoy = len(df_proceso[df_proceso[col_vencimiento] == hoy_str]) if col_vencimiento else 0
    recolecciones = len(df_recoleccion_total)
    
    # Filtramos visualmente "PÉRDIDA TOTAL" de los KPI
    por_confirmar_kpi = len(df_proceso[(df_proceso[col_estatus].astype(str).str.upper().str.contains("CONFIRMAR") | (df_proceso[col_estatus].astype(str).str.strip() == "")) & (~df_proceso[col_estatus].astype(str).str.upper().isin(["PÉRDIDA TOTAL"]))]) if col_estatus else 0
    en_proceso = len(df_proceso[~df_proceso[col_estatus].astype(str).str.upper().str.contains("CONFIRMAR") & (~df_proceso[col_estatus].astype(str).str.upper().isin(["PÉRDIDA TOTAL"])) & (df_proceso[col_estatus].astype(str).str.strip() != "")]) if col_estatus else len(df_proceso)
    partidas_por_facturar = len(df_trabajo[df_trabajo[col_estatus].astype(str).str.strip().str.upper() == "RECIBIDO"]) if col_estatus else 0
    
    kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)
    kpi1.metric("📦 En Proceso (Piezas)", en_proceso); kpi2.metric("⏳ Por Confirmar", por_confirmar_kpi); kpi3.metric("⚠️ Vencen Hoy", vencen_hoy)
    kpi4.metric("❌ Vencidos", vencidas_pasadas_kpi); kpi5.metric("↩️ En Recolección", recolecciones); kpi6.metric("🧾 Por Facturar", partidas_por_facturar)

    st.markdown("### 🎛️ Filtros de Búsqueda")
    
    dict_estados = {}
    if not df_catalogo.empty and col_taller:
        col_cat_tall = next((c for c in df_catalogo.columns if "TALLER" in str(c).upper()), None)
        col_cat_est = next((c for c in df_catalogo.columns if "ESTADO" in str(c).upper()), None)
        if col_cat_tall and col_cat_est:
            dict_estados = dict(zip(df_catalogo[col_cat_tall].astype(str).str.strip().str.upper(), df_catalogo[col_cat_est].astype(str).str.strip().str.upper()))
    
    df_proceso['Estado_CDR'] = df_proceso[col_taller].astype(str).str.strip().str.upper().map(dict_estados).fillna("S/D") if col_taller else "S/D"
    if not df_recoleccion_total.empty:
        df_recoleccion_total['Estado_CDR'] = df_recoleccion_total[col_taller].astype(str).str.strip().str.upper().map(dict_estados).fillna("S/D") if col_taller else "S/D"

    # Retiramos los PT del flujo normal visual
    if col_estatus:
        df_proceso = df_proceso[~df_proceso[col_estatus].astype(str).str.upper().isin(["PÉRDIDA TOTAL"])]

    filtro_col0, filtro_col1, filtro_col2, filtro_col3, filtro_col4 = st.columns([1, 1.2, 1, 1.5, 1.5])
    
    with filtro_col0: estado_sel = st.multiselect("🌎 Estado:", sorted([str(e) for e in df_proceso['Estado_CDR'].dropna().unique() if str(e).strip() != '']), placeholder="Todos...")
    with filtro_col1: 
        df_t1 = df_proceso.copy()
        if estado_sel: df_t1 = df_t1[df_t1['Estado_CDR'].astype(str).isin(estado_sel)]
        taller_sel = st.multiselect("🏢 Taller:", sorted([str(t) for t in df_t1[col_taller].dropna().unique() if str(t).strip() != '']) if col_taller else [], placeholder="Todos...")
    with filtro_col2: 
        df_t2 = df_t1.copy()
        if taller_sel: df_t2 = df_t2[df_t2[col_taller].astype(str).isin(taller_sel)]
        estatus_sel = st.multiselect("📊 Estatus:", sorted([str(e) for e in df_t2[col_estatus].dropna().unique() if str(e).strip() != '']) if col_estatus else [], placeholder="Todos...")
    with filtro_col3:
        df_t3 = df_t2.copy()
        if estatus_sel: df_t3 = df_t3[df_t3[col_estatus].astype(str).isin(estatus_sel)]
        siniestro_sel = st.multiselect(f"🚗 Siniestro - Vehículo:", sorted(list(df_t3['Filtro_Siniestro'].dropna().unique())) if 'Filtro_Siniestro' in df_t3.columns else [], placeholder="Todos...")
    with filtro_col4:
        df_t4 = df_t3.copy()
        if siniestro_sel: df_t4 = df_t4[df_t4['Filtro_Siniestro'].isin(siniestro_sel)]
        desc_sel = st.multiselect(f"⚙️ Refacción:", sorted(list(df_t4[col_desc].dropna().astype(str).unique())) if col_desc in df_t4.columns else [], placeholder="Todas...")

    df_filtrado = df_proceso.copy()
    if estado_sel: df_filtrado = df_filtrado[df_filtrado['Estado_CDR'].astype(str).isin(estado_sel)]
    if taller_sel: df_filtrado = df_filtrado[df_filtrado[col_taller].astype(str).isin(taller_sel)]
    if estatus_sel: df_filtrado = df_filtrado[df_filtrado[col_estatus].astype(str).isin(estatus_sel)]
    if siniestro_sel: df_filtrado = df_filtrado[df_filtrado['Filtro_Siniestro'].isin(siniestro_sel)]
    if desc_sel: df_filtrado = df_filtrado[df_filtrado[col_desc].astype(str).isin(desc_sel)]

    def generar_llave_temp(id_val, desc_val):
        id_str = str(id_val).strip().upper()
        if id_str.endswith('.0'): id_str = id_str[:-2]
        desc_str = ' '.join(str(desc_val).strip().upper().split())
        return f"{id_str}_{desc_str}"

    if not df_compras.empty:
        def parse_spanish_date_comp(d_str):
            if pd.isna(d_str) or str(d_str).strip() == '': return pd.NaT
            d_str = str(d_str).lower().replace('-', '/') 
            meses = {'ene':'01', 'feb':'02', 'mar':'03', 'abr':'04', 'may':'05', 'jun':'06', 'jul':'07', 'ago':'08', 'sep':'09', 'oct':'10', 'nov':'11', 'dic':'12'}
            for text, num in meses.items():
                if text in d_str: d_str = d_str.replace(text, num); break
            try: return pd.to_datetime(d_str, format='%d/%m/%y', errors='coerce')
            except: return pd.NaT

        df_compras_temp = df_compras.copy()
        df_compras_temp['LLAVE_COMP'] = df_compras_temp.apply(lambda r: generar_llave_temp(r.get('Siniestro',''), r.get('Descripción Pieza','')), axis=1)
        
        df_compras_temp['F_Compra_Dt'] = df_compras_temp['Fecha Compra'].apply(parse_spanish_date_comp)
        df_compras_temp['ETA_Num'] = pd.to_numeric(df_compras_temp['Tiempo Entrega (Días)'], errors='coerce').fillna(0)
        df_compras_temp['Llegada_Calc'] = df_compras_temp['F_Compra_Dt'] + pd.to_timedelta(df_compras_temp['ETA_Num'], unit='d')
        df_compras_temp['Fecha Llegada'] = df_compras_temp['Llegada_Calc'].dt.strftime('%d/%b/%y').fillna('-')
        
        dict_prov = dict(zip(df_compras_temp['LLAVE_COMP'], df_compras_temp['Proveedor']))
        dict_costo = dict(zip(df_compras_temp['LLAVE_COMP'], df_compras_temp['Costo Compra']))
        dict_llegada = dict(zip(df_compras_temp['LLAVE_COMP'], df_compras_temp['Fecha Llegada']))
        
        df_filtrado['LLAVE_TEMP'] = df_filtrado.apply(lambda r: generar_llave_temp(r.get(col_id,''), r.get(col_desc,'')), axis=1)
        df_filtrado['Proveedor'] = df_filtrado['LLAVE_TEMP'].map(dict_prov).fillna("")
        
        def safe_float(v):
            try: return float(str(v).replace('\$', '').replace(',', '').strip())
            except: return 0.0
        df_filtrado['Costo Compra'] = df_filtrado['LLAVE_TEMP'].map(dict_costo).apply(safe_float)
        df_filtrado['Llegada Est.'] = df_filtrado['LLAVE_TEMP'].map(dict_llegada).fillna("-")
    else:
        df_filtrado['Proveedor'] = ""; df_filtrado['Costo Compra'] = 0.0; df_filtrado['Llegada Est.'] = "-"

    base_config = {}
    if col_id and col_id in df_filtrado.columns: base_config[col_id] = st.column_config.TextColumn("Pedido / Siniestro", disabled=True)
    if 'Vehiculo_Info' in df_filtrado.columns: base_config['Vehiculo_Info'] = st.column_config.TextColumn("Vehículo")
    if col_taller: base_config[col_taller] = st.column_config.TextColumn("Taller")
    if col_cant: base_config[col_cant] = st.column_config.TextColumn("Cant")
    if col_desc: base_config[col_desc] = st.column_config.TextColumn("Descrip.") 
    if col_precio: base_config[col_precio] = st.column_config.TextColumn("Precio")
    if col_estatus: base_config[col_estatus] = st.column_config.TextColumn("Estatus", disabled=True)
    if col_vencimiento: base_config[col_vencimiento] = st.column_config.TextColumn("Venc.")
    if col_paqueteria: base_config[col_paqueteria] = st.column_config.SelectboxColumn("Paquetería", options=["", "PAQUETEXPRESS", "FEDEX", "DHL", "ESTAFETA", "AFIMEX"])
    if col_guia: base_config[col_guia] = st.column_config.TextColumn("Guía")
    if col_estatus_envio: base_config[col_estatus_envio] = st.column_config.TextColumn("📍 Rastreo", disabled=True)
    if col_remision: base_config[col_remision] = st.column_config.TextColumn("Folio Remis")
    if col_comentarios: base_config[col_comentarios] = st.column_config.TextColumn("Obs.") 

    cond_confirmar = df_filtrado[col_estatus].astype(str).str.upper().str.contains("CONFIRMAR") | (df_filtrado[col_estatus].fillna('').astype(str).str.strip() == "")
    df_por_confirmar = df_filtrado[cond_confirmar].copy() if col_estatus else pd.DataFrame()
    
    with st.expander(f"⏳ Piezas por Confirmar | {len(df_por_confirmar)} Partida(s)", expanded=False):
        dfs_editados_conf = []
        if not df_por_confirmar.empty:
            for taller, df_taller in df_por_confirmar.groupby(col_taller):
                with st.expander(f"🏢 {taller}", expanded=False):
                    for siniestro_auto, df_grupo in df_taller.groupby('Agrupador_Visual'):
                        st.markdown(f"**🚗 {siniestro_auto} | {df_grupo['Vehiculo_Info'].iloc[0]}**")
                        if permiso_edicion: 
                            df_grupo['Confirmar Surtido'] = False; df_grupo['Cancelar'] = False; df_grupo['Pérdida Total'] = False
                            cols_visibles = [c for c in [col_id, col_cant, col_desc, col_origen, col_precio, col_vencimiento] if c in df_grupo.columns] + ['Proveedor', 'Costo Compra', 'Confirmar Surtido', 'Cancelar', 'Pérdida Total'] + [c for c in [col_comentarios] if c in df_grupo.columns]
                            config_conf = base_config.copy()
                            config_conf.update({"Confirmar Surtido": st.column_config.CheckboxColumn("✅ Confirmar", default=False), "Cancelar": st.column_config.CheckboxColumn("🚫 Can", default=False), "Pérdida Total": st.column_config.CheckboxColumn("💥 PT", default=False), "Proveedor": st.column_config.SelectboxColumn("🏢 Proveedor", options=lista_proveedores), "Costo Compra": st.column_config.NumberColumn("💲 Costo", format="\$ %.2f")})
                            columnas_editables = ['Proveedor', 'Costo Compra', 'Confirmar Surtido', 'Cancelar', 'Pérdida Total', col_comentarios]
                            df_editado_parcial = st.data_editor(df_grupo[cols_visibles], column_config=config_conf, disabled=[c for c in cols_visibles if c not in columnas_editables], hide_index=True, use_container_width=True, key=f"ed_conf_{taller}_{siniestro_auto}")
                            for col in df_grupo.columns:
                                if col not in df_editado_parcial.columns: df_editado_parcial[col] = df_grupo[col].values
                            dfs_editados_conf.append(df_editado_parcial)
                        else:
                            cols_visibles = [c for c in [col_id, col_cant, col_desc, col_origen, col_precio, col_vencimiento, col_comentarios] if c in df_grupo.columns]
                            st.dataframe(df_grupo[cols_visibles], column_config=base_config, hide_index=True, use_container_width=True)
        if dfs_editados_conf: df_editado_conf = pd.concat(dfs_editados_conf, ignore_index=True)

    df_vencimientos = df_filtrado[(df_filtrado[col_vencimiento] == hoy_str) & (~df_filtrado[col_estatus].astype(str).str.upper().str.contains("CONFIRMAR|ENTREGADO|RECIBIDO|FACTURADO|CANCELADO|RECOLEC|REEMBOLSO")) & (df_filtrado[col_estatus].fillna('').astype(str).str.strip() != "")].copy() if col_vencimiento else pd.DataFrame()
    with st.expander(f"🚨 Vencimientos de Hoy | {len(df_vencimientos)} Partida(s)", expanded=False):
        if not df_vencimientos.empty:
            if permiso_edicion:
                df_vencimientos['Cancelar'] = False; df_vencimientos['Nueva Fecha'] = pd.NaT
                cols_visibles = [c for c in [col_id, 'Vehiculo_Info', col_taller, col_cant, col_desc, col_precio, col_vencimiento] if c in df_vencimientos.columns] + ['Cancelar', 'Nueva Fecha'] + [c for c in [col_paqueteria, col_guia, col_comentarios] if c in df_vencimientos.columns]
                config_venc = base_config.copy()
                config_venc.update({"Cancelar": st.column_config.CheckboxColumn("🚫 Can", default=False), "Nueva Fecha": st.column_config.DateColumn("📅 Nueva Fecha", format="DD/MMM/YYYY")})
                df_editado_venc = st.data_editor(df_vencimientos[cols_visibles], column_config=config_venc, disabled=[c for c in cols_visibles if c not in ['Cancelar', 'Nueva Fecha', col_comentarios, col_paqueteria, col_guia]], hide_index=True, use_container_width=True, key="ed_venc")
                for col in df_vencimientos.columns:
                    if col not in df_editado_venc.columns: df_editado_venc[col] = df_vencimientos[col].values
            else:
                cols_visibles = [c for c in [col_id, 'Vehiculo_Info', col_taller, col_cant, col_desc, col_precio, col_vencimiento, col_paqueteria, col_guia, col_comentarios] if c in df_vencimientos.columns]
                st.dataframe(df_vencimientos[cols_visibles], column_config=base_config, hide_index=True, use_container_width=True)
                
    if col_vencimiento and not df_filtrado.empty:
        fechas_venc_filtro = df_filtrado[col_vencimiento].apply(parse_dt_safe_op)
        df_atrasadas = df_filtrado[(fechas_venc_filtro < hoy_dt) & (df_filtrado[col_vencimiento] != '') & (~df_filtrado[col_estatus].astype(str).str.upper().str.contains("CONFIRMAR|ENTREGADO|RECIBIDO|FACTURADO|CANCELADO|RECOLEC|REEMBOLSO")) & (df_filtrado[col_estatus].fillna('').astype(str).str.strip() != "")].copy()
    else: df_atrasadas = pd.DataFrame()
    with st.expander(f"❌ Vencimientos Atrasados | {len(df_atrasadas)} Partida(s)", expanded=False):
        if not df_atrasadas.empty:
            if permiso_edicion:
                df_atrasadas['Cancelar'] = False; df_atrasadas['Nueva Fecha'] = pd.NaT
                cols_visibles = [c for c in [col_id, 'Vehiculo_Info', col_taller, col_cant, col_desc, col_precio, col_vencimiento] if c in df_atrasadas.columns] + ['Cancelar', 'Nueva Fecha'] + [c for c in [col_paqueteria, col_guia, col_comentarios] if c in df_atrasadas.columns]
                config_atr = base_config.copy()
                config_atr.update({"Cancelar": st.column_config.CheckboxColumn("🚫 Can", default=False), "Nueva Fecha": st.column_config.DateColumn("📅 Nueva Fecha", format="DD/MMM/YYYY")})
                df_editado_atrasadas = st.data_editor(df_atrasadas[cols_visibles], column_config=config_atr, disabled=[c for c in cols_visibles if c not in ['Cancelar', 'Nueva Fecha', col_comentarios, col_paqueteria, col_guia]], hide_index=True, use_container_width=True, key="ed_atr")
                for col in df_atrasadas.columns:
                    if col not in df_editado_atrasadas.columns: df_editado_atrasadas[col] = df_atrasadas[col].values
            else:
                cols_visibles = [c for c in [col_id, 'Vehiculo_Info', col_taller, col_cant, col_desc, col_precio, col_vencimiento, col_paqueteria, col_guia, col_comentarios] if c in df_atrasadas.columns]
                st.dataframe(df_atrasadas[cols_visibles], column_config=base_config, hide_index=True, use_container_width=True)

    df_por_recibir = df_filtrado[df_filtrado[col_estatus].astype(str).str.upper() == "ENTREGADO"].copy() if col_estatus else pd.DataFrame()
    with st.expander(f"📥 Por Recibir (Entregados en CDR) | {len(df_por_recibir)} Partida(s)", expanded=False):
        if not df_por_recibir.empty:
            if permiso_edicion:
                df_por_recibir['Marcar Recibido'] = False
                cols_visibles = [c for c in [col_id, 'Vehiculo_Info', col_taller, col_cant, col_desc, col_origen, col_precio] if c in df_por_recibir.columns] + ['Marcar Recibido'] + [c for c in [col_paqueteria, col_guia, col_comentarios] if c in df_por_recibir.columns]
                config_cobro = base_config.copy()
                config_cobro.update({"Marcar Recibido": st.column_config.CheckboxColumn("🏁 Marcar Recibido", default=False)})
                df_editado_cobro = st.data_editor(df_por_recibir[cols_visibles], column_config=config_cobro, disabled=[c for c in cols_visibles if c not in ['Marcar Recibido', col_comentarios]], hide_index=True, use_container_width=True, key="ed_cobro")
                for col in df_por_recibir.columns: 
                    if col not in df_editado_cobro.columns: df_editado_cobro[col] = df_por_recibir[col].values
            else:
                cols_visibles = [c for c in [col_id, 'Vehiculo_Info', col_taller, col_cant, col_desc, col_origen, col_precio, col_paqueteria, col_guia, col_comentarios] if c in df_por_recibir.columns]
                st.dataframe(df_por_recibir[cols_visibles], column_config=base_config, hide_index=True, use_container_width=True)

    if col_estatus and col_estatus in df_filtrado.columns:
        mask_asignados = (~df_filtrado[col_estatus].fillna('').astype(str).str.upper().str.contains("CONFIRMAR|ENTREGADO|RECIBIDO|FACTURADO|CANCELADO|REEMBOLSO")) & (df_filtrado[col_estatus].fillna('').astype(str).str.strip() != "")
        df_asignados = df_filtrado[mask_asignados].copy()
    else: df_asignados = df_filtrado.copy()
    
    with st.expander(f"📋 Pedidos Asignados (General) | {len(df_asignados)} Partida(s)", expanded=False):
        dfs_editados = []
        if not df_asignados.empty:
            if col_estatus:
                estatus_upper = df_asignados[col_estatus].astype(str).str.upper()
                df_asignados['Entregado'] = estatus_upper.str.contains("ENTREGADO")
                df_asignados['Recibido'] = estatus_upper.str.contains("RECIBIDO")
                df_asignados['Cancelar'] = estatus_upper.str.contains("CANCELADO")
            
            for taller, df_taller in df_asignados.groupby(col_taller):
                with st.expander(f"🏢 {taller}", expanded=False):
                    for siniestro_auto, df_grupo in df_taller.groupby('Agrupador_Visual'):
                        st.markdown(f"**🚗 {siniestro_auto} | {df_grupo['Vehiculo_Info'].iloc[0]}**")
                        if permiso_edicion:
                            cols_visibles = [c for c in [col_id, col_cant, col_desc, col_origen, col_precio, col_vencimiento] if c in df_grupo.columns] + ['Proveedor', 'Costo Compra', 'Llegada Est.'] + [c for c in [col_paqueteria, col_guia, col_estatus_envio, col_remision] if c in df_grupo.columns] + ['Entregado', 'Recibido', 'Cancelar'] + [c for c in [col_comentarios] if c in df_grupo.columns]
                            config_pedidos = base_config.copy()
                            config_pedidos.update({ "Proveedor": st.column_config.SelectboxColumn("🏢 Proveedor", options=lista_proveedores), "Costo Compra": st.column_config.NumberColumn("💲 Costo", format="\$ %.2f"), "Llegada Est.": st.column_config.TextColumn("📅 Llegada", disabled=True), col_estatus_envio: st.column_config.TextColumn("📍 Rastreo", disabled=True), "Entregado": st.column_config.CheckboxColumn("🚚 Ent", default=False), "Recibido": st.column_config.CheckboxColumn("🏁 Rec", default=False), "Cancelar": st.column_config.CheckboxColumn("🚫 Can", default=False) })
                            columnas_editables = ['Proveedor', 'Costo Compra', col_paqueteria, col_guia, col_remision, 'Entregado', 'Recibido', 'Cancelar', col_comentarios, col_vencimiento]
                            df_editado_parcial = st.data_editor(df_grupo[cols_visibles], column_config=config_pedidos, disabled=[c for c in cols_visibles if c not in columnas_editables], hide_index=True, use_container_width=True, key=f"ed_{taller}_{siniestro_auto}")
                            for col in df_grupo.columns:
                                if col not in df_editado_parcial.columns: df_editado_parcial[col] = df_grupo[col].values
                            dfs_editados.append(df_editado_parcial)
                        else:
                            cols_visibles = [c for c in [col_id, col_cant, col_desc, col_origen, col_precio, col_vencimiento, col_paqueteria, col_guia, col_estatus_envio, col_remision, col_comentarios] if c in df_grupo.columns]
                            st.dataframe(df_grupo[cols_visibles], column_config=base_config, hide_index=True, use_container_width=True)
        if dfs_editados: df_editado = pd.concat(dfs_editados, ignore_index=True)

    df_reembolsos = df_filtrado[df_filtrado[col_estatus].astype(str).str.upper().str.contains("REEMBOLSO")].copy() if col_estatus else pd.DataFrame()
    with st.expander(f"💸 Reembolsos | {len(df_reembolsos)} Partida(s)", expanded=False):
        if not df_reembolsos.empty:
            if permiso_edicion:
                df_reembolsos['Marcar Reembolsado'] = False
                cols_visibles = [c for c in [col_id, col_cant, col_desc, col_origen, col_precio, col_estatus] if c in df_reembolsos.columns] + ['Marcar Reembolsado'] + [c for c in ['Proveedor', 'Costo Compra', col_paqueteria, col_guia, col_comentarios] if c in df_reembolsos.columns]
                config_reemb = base_config.copy()
                config_reemb.update({"Marcar Reembolsado": st.column_config.CheckboxColumn("✅ Reembolsado", default=False)})
                df_editado_reemb = st.data_editor(df_reembolsos[cols_visibles], column_config=config_reemb, disabled=[c for c in cols_visibles if c not in ['Marcar Reembolsado', col_comentarios]], hide_index=True, use_container_width=True, key="ed_reemb")
                for col in df_reembolsos.columns: 
                    if col not in df_editado_reemb.columns: df_editado_reemb[col] = df_reembolsos[col].values
            else:
                cols_visibles = [c for c in [col_id, col_cant, col_desc, col_origen, col_precio, col_estatus, 'Proveedor', 'Costo Compra', col_paqueteria, col_guia, col_comentarios] if c in df_reembolsos.columns]
                st.dataframe(df_reembolsos[cols_visibles], column_config=base_config, hide_index=True, use_container_width=True)

    df_recoleccion = df_recoleccion_total.copy()
    if 'Estado_CDR' in df_proceso.columns: 
        df_recoleccion['Estado_CDR'] = df_recoleccion[col_taller].astype(str).str.strip().str.upper().map(dict_estados).fillna("S/D") if col_taller else "S/D"
    if estado_sel: df_recoleccion = df_recoleccion[df_recoleccion['Estado_CDR'].astype(str).isin(estado_sel)]
    if taller_sel: df_recoleccion = df_recoleccion[df_recoleccion[col_taller].astype(str).isin(taller_sel)]
    if siniestro_sel:
        ids_sel = [s.split(" - ")[0] for s in siniestro_sel]
        df_recoleccion = df_recoleccion[df_recoleccion[col_id].isin(ids_sel)]
    if desc_sel: df_recoleccion = df_recoleccion[df_recoleccion[col_desc].astype(str).isin(desc_sel)]

    df_editado_rec = pd.DataFrame()
    with st.expander(f"↩️ Piezas para Recolección | {len(df_recoleccion)} Partida(s)", expanded=False):
        if not df_recoleccion.empty:
            if permiso_edicion:
                cols_rec = [c for c in [col_id, col_cant, col_desc, col_precio, col_estatus] if c in df_recoleccion.columns] + [c for c in [col_paqueteria, col_guia, col_comentarios] if c in df_recoleccion.columns]
                df_editado_rec = st.data_editor(df_recoleccion[cols_rec], column_config=base_config, disabled=[c for c in cols_rec if c not in [col_paqueteria, col_guia, col_comentarios]], hide_index=True, use_container_width=True, key="ed_rec_panel")
                for col in df_recoleccion.columns: 
                    if col not in df_editado_rec.columns: df_editado_rec[col] = df_recoleccion[col].values
            else:
                cols_rec = [c for c in [col_id, col_cant, col_desc, col_precio, col_estatus, col_paqueteria, col_guia, col_comentarios] if c in df_recoleccion.columns]
                st.dataframe(df_recoleccion[cols_rec], column_config=base_config, hide_index=True, use_container_width=True)

# ==============================================================================
# === [BLOQUE 7: VISTAS - COMPRAS, TALLERES E INVENTARIO] ===
# ==============================================================================
elif vista_actual == "🛒 Compras":
    st.markdown("### 🛒 Panel de Compras (Gestión y Pagos)")
    if not df_proveedores.empty:
        def normalizar_pago(val):
            v = str(val).strip().upper()
            if 'PREV' in v: return 'Previo'
            if 'ANTIC' in v: return 'Anticipo'
            if 'CONTRA' in v: return 'Contra Entrega'
            if 'CRED' in v or 'CRÉD' in v: return 'Crédito'
            if 'PLAT' in v: return 'Plataforma'
            return str(val).strip()
        if 'Condición Pago' in df_proveedores.columns: df_proveedores['Condición Pago'] = df_proveedores['Condición Pago'].apply(normalizar_pago)

    if not df_compras.empty:
        df_c = df_compras.copy()
        c1, c2, c3 = st.columns(3)
        with c1: f_sin = st.multiselect("🔍 Buscar Siniestro/Pieza:", options=sorted(list(set(df_c['Siniestro'].astype(str).tolist() + df_c['Descripción Pieza'].astype(str).tolist()))))
        with c2: f_tall = st.multiselect("🏢 Filtrar por Taller (CDR):", options=sorted(list(df_c['Taller'].dropna().astype(str).unique())))
        with c3: f_prov = st.multiselect("🏢 Filtrar por Proveedor:", options=sorted(list(df_c['Proveedor'].dropna().astype(str).unique())))
        
        if f_sin: df_c = df_c[df_c['Siniestro'].astype(str).isin(f_sin) | df_c['Descripción Pieza'].astype(str).isin(f_sin)]
        if f_tall: df_c = df_c[df_c['Taller'].astype(str).isin(f_tall)]
        if f_prov: df_c = df_c[df_c['Proveedor'].astype(str).isin(f_prov)]
        
        st.markdown("#### 📦 Próximas Llegadas (Línea de Tiempo)")
        if not df_c.empty:
            df_c['Recibido_Bool'] = df_c['Recibido'].astype(str).str.strip().str.upper().isin(['TRUE', 'SI', '1', 'YES', 'V', 'X'])
            if not modo_consulta: df_c = df_c[df_c['Recibido_Bool'] == False].copy()
            if df_c.empty: st.success("✅ Todo está al día. No hay pedidos pendientes de recepción con estos filtros.")
            else:
                df_c['Cancelar Compra'] = False
                if not df_proveedores.empty:
                    dict_provs = {}
                    for _, rp in df_proveedores.iterrows():
                        p_n = str(rp.get('Proveedor', '')).strip().upper(); s_n = str(rp.get('Sucursal', '')).strip().upper()
                        llave_full = f"{p_n} - {s_n}" if s_n else p_n
                        t_str = str(rp.get('Tiempo de Entrega', '')).upper()
                        nums = re.findall(r'\d+', t_str)
                        eta_v = nums[-1] if nums else "0"
                        cond_v = str(rp.get('Condición Pago', '')).strip().title()
                        dias_v = str(rp.get('Días Crédito', '0')).strip()
                        dict_provs[llave_full] = {'eta': eta_v, 'cond': cond_v, 'dias': dias_v}
                        dict_provs[p_n] = {'eta': eta_v, 'cond': cond_v, 'dias': dias_v}

                    for idx, r_c in df_c.iterrows():
                        prov_actual = str(r_c.get('Proveedor', '')).strip().upper()
                        if prov_actual in dict_provs:
                            datos_p = dict_provs[prov_actual]
                            eta_actual = pd.to_numeric(r_c.get('Tiempo Entrega (Días)', 0), errors='coerce')
                            if pd.isna(eta_actual) or eta_actual == 0: df_c.at[idx, 'Tiempo Entrega (Días)'] = datos_p['eta']
                            cond_actual = str(r_c.get('Condición Pago', '')).strip().title()
                            if cond_actual in ['', 'None', 'Nan']: df_c.at[idx, 'Condición Pago'] = datos_p['cond']
                            dias_actual = pd.to_numeric(r_c.get('Días Crédito', 0), errors='coerce')
                            if pd.isna(dias_actual) or dias_actual == 0: df_c.at[idx, 'Días Crédito'] = datos_p['dias']

                def parse_spanish_date_c2(d_str):
                    if pd.isna(d_str) or str(d_str).strip() == '': return pd.NaT
                    d_str = str(d_str).lower().replace('-', '/') 
                    meses = {'ene':'01', 'feb':'02', 'mar':'03', 'abr':'04', 'may':'05', 'jun':'06', 'jul':'07', 'ago':'08', 'sep':'09', 'oct':'10', 'nov':'11', 'dic':'12'}
                    for text, num in meses.items():
                        if text in d_str: d_str = d_str.replace(text, num); break
                    try: return pd.to_datetime(d_str, format='%d/%m/%y', errors='coerce')
                    except: return pd.NaT

                df_c['Fecha_Compra_Dt'] = df_c['Fecha Compra'].apply(parse_spanish_date_c2)
                df_c['ETA (Días)'] = pd.to_numeric(df_c['Tiempo Entrega (Días)'], errors='coerce').fillna(0)
                df_c['Llegada_Calculada'] = df_c['Fecha_Compra_Dt'] + pd.to_timedelta(df_c['ETA (Días)'], unit='d')
                df_c['Llegada Est.'] = df_c['Llegada_Calculada'].dt.strftime('%d/%b/%y').fillna('-')
                tz_mx = datetime.timezone(datetime.timedelta(hours=-6))
                hoy_dt_alert = pd.to_datetime(datetime.datetime.now(tz_mx).date())
                
                def calc_alerta(row):
                    cond = str(row.get('Condición Pago', '')).strip().title()
                    dias_cr = pd.to_numeric(row.get('Días Crédito', 0), errors='coerce')
                    if pd.isna(dias_cr): dias_cr = 0
                    if cond in ['Previo', 'Anticipo', 'Contra Entrega']: return '🔴 Pago Inmediato'
                    elif cond in ['Crédito', 'Credito']:
                        if pd.notna(row['Fecha_Compra_Dt']):
                            vencimiento = row['Fecha_Compra_Dt'] + pd.to_timedelta(dias_cr, unit='d')
                            dias_restantes = (vencimiento - hoy_dt_alert).days
                            f_venc = vencimiento.strftime('%d/%b')
                            if dias_restantes < 0: return f"❌ VENCIDO ({f_venc})"
                            elif dias_restantes <= 3: return f"🟠 Vence pronto: {f_venc}"
                            else: return f"🟢 En tiempo: {f_venc}"
                        else: return f"🟡 Crédito {dias_cr} días"
                    elif cond == 'Plataforma': return '🔵 Pago en Plataforma'
                    return '⚪ Configurar Pago'
                    
                df_c['Alerta Financiera'] = df_c.apply(calc_alerta, axis=1)

                def formato_auto_corto(v):
                    if pd.isna(v) or not str(v).strip() or str(v).lower() == 'nan': return ""
                    v_str = str(v).strip()
                    if ' - ' in v_str: v_str = v_str.split(' - ')[0].strip()
                    elif ' | ' in v_str:
                        partes = v_str.split(' | ')
                        if len(partes) >= 2: v_str = f"{partes[0]} {partes[1]}".strip()
                        else: v_str = partes[0].strip()
                    return v_str
                
                df_c['Vehículo_Corto'] = df_c.get('Vehículo', pd.Series([""]*len(df_c))).apply(formato_auto_corto)
                cols_mostrar = ['Siniestro', 'Vehículo_Corto', 'Taller', 'Descripción Pieza', 'Proveedor', 'Costo Compra', 'ETA (Días)', 'Llegada Est.', 'Condición Pago', 'Días Crédito', 'Estatus Pago', 'Recibido_Bool', 'Cancelar Compra', 'Alerta Financiera']
                df_disp = df_c[[c for c in cols_mostrar if c in df_c.columns]].copy()
                df_disp.rename(columns={'Vehículo_Corto': 'Auto', 'Taller': 'CDR', 'Descripción Pieza': 'Pieza', 'Costo Compra': 'Costo', 'ETA (Días)': 'ETA', 'Recibido_Bool': 'Recibido', 'Estatus Pago': 'Pago', 'Condición Pago': 'Cond. Pago', 'Días Crédito': 'Días Cr.'}, inplace=True)
                
                if not modo_consulta and permiso_edicion:
                    opciones_pago = ["", "Previo", "Anticipo", "Contra Entrega", "Crédito", "Plataforma"]
                    config_c = {
                        'Siniestro': st.column_config.TextColumn("Siniestro", disabled=True, width="small"), 
                        'Auto': st.column_config.TextColumn("Auto", disabled=True, width="medium"),
                        'CDR': st.column_config.TextColumn("CDR", disabled=True, width="medium"), 
                        'Pieza': st.column_config.TextColumn("Pieza", disabled=True, width="medium"),
                        'Proveedor': st.column_config.TextColumn("Proveedor", width="medium"), 
                        'Costo': st.column_config.NumberColumn("Costo", format="$ %.2f", width="small"),
                        'ETA': st.column_config.NumberColumn("ETA", step=1, width="small"), 
                        'Llegada Est.': st.column_config.TextColumn("Llegada Est.", disabled=True, width="small"),
                        'Cond. Pago': st.column_config.SelectboxColumn("Cond. Pago", options=opciones_pago, width="small"), 
                        'Días Cr.': st.column_config.NumberColumn("Días Cr.", step=1, width="small"),
                        'Pago': st.column_config.SelectboxColumn("Pago", options=["", "Pendiente", "Pagado", "En Aclaración"], width="small"),
                        'Recibido': st.column_config.CheckboxColumn("🏁 Recibido", width="small"), 
                        'Cancelar Compra': st.column_config.CheckboxColumn("🚫 Cancelar", width="small"),
                        'Alerta Financiera': st.column_config.TextColumn("Alerta Financiera", disabled=True, width="medium")
                    }
                    df_editado_compras = st.data_editor(df_disp, column_config=config_c, hide_index=True, use_container_width=True, key="ed_compras_main")
                    df_editado_compras.rename(columns={'Auto': 'Vehículo_Corto', 'CDR': 'Taller', 'Pieza': 'Descripción Pieza', 'Costo': 'Costo Compra', 'ETA': 'Tiempo Entrega (Días)', 'Cond. Pago': 'Condición Pago', 'Días Cr.': 'Días Crédito', 'Pago': 'Estatus Pago'}, inplace=True)
                    st.session_state['df_editado_compras_temp'] = df_editado_compras
                else: 
                    st.dataframe(df_disp, hide_index=True, use_container_width=True)
        else: st.info("No hay pedidos en curso.")
    else: st.warning("No hay datos en la base de compras.")

elif vista_actual == "🏢 Directorio":
    st.markdown("### 🏢 Directorio Principal")
    tab_talleres, tab_proveedores = st.tabs(["🔧 Talleres / CDR", "📦 Proveedores"])

    # ==========================
    # PESTAÑA 1: TALLERES (CDR) - FUSIONADO
    # ==========================
    with tab_talleres:
        col_taller_cat = next((c for c in df_catalogo.columns if "TALLER" in str(c).upper()), None)
        col_dir_cat = next((c for c in df_catalogo.columns if "DIRECCI" in str(c).upper()), None)
        col_tel_cat = next((c for c in df_catalogo.columns if "TELEFONO" in str(c).upper() or "TEL" in str(c).upper()), None)
        col_ciudad_cat = next((c for c in df_catalogo.columns if "CIUDAD" in str(c).upper()), None)
        col_estado_cat = next((c for c in df_catalogo.columns if "ESTADO" in str(c).upper()), None)
        
        busqueda_taller = st.text_input("🔍 Buscar Taller por nombre, ciudad o estado...")
        df_cat_filtrado = df_catalogo.copy()
        
        if busqueda_taller:
            mask = df_cat_filtrado.apply(lambda row: row.astype(str).str.contains(busqueda_taller, case=False, na=False).any(), axis=1)
            df_cat_filtrado = df_cat_filtrado[mask]

        cols_vista_cat = [c for c in df_cat_filtrado.columns if "Unnamed" not in str(c)]
        if cols_vista_cat: st.dataframe(df_cat_filtrado[cols_vista_cat], hide_index=True, use_container_width=True)

        if permiso_edicion:
            with st.expander("➕ Agregar / Registrar Nuevo Taller (CDR)", expanded=False):
                st.info("Registra un nuevo taller integrando todos los datos operativos y de contacto.")
                with st.form("form_nuevo_taller", clear_on_submit=True):
                    mapa_asesores = {"Monterrey": "Oscar Landeros Martinez", "CDMX": "Yessica Vianney Martinez Olivar", "Guadalajara": "Estefany Dayanna Ochoa Aranda"}
                    
                    c1, c2, c3 = st.columns([2, 2, 1])
                    nuevo_taller = c1.text_input("Nombre del Taller / CDR * (Obligatorio)")
                    
                    ciudades_bd = [str(c).strip().title() for c in df_catalogo[col_ciudad_cat].dropna().unique() if str(c).strip() != ''] if col_ciudad_cat else []
                    lista_ciudades = sorted(list(set(list(mapa_asesores.keys()) + ciudades_bd)))
                    
                    ciudad_sel = c2.selectbox("Ciudad *", [""] + lista_ciudades + ["➕ OTRA CIUDAD (Escribir manual)"])
                    if ciudad_sel == "➕ OTRA CIUDAD (Escribir manual)": 
                        nueva_ciudad = c2.text_input("✍️ Escribe el nombre de la nueva Ciudad *").title()
                        asesor_asignado = c3.text_input("Asesor Asignado (Manual)").upper()
                    elif ciudad_sel != "": 
                        nueva_ciudad = ciudad_sel
                        asesor_asignado = mapa_asesores.get(ciudad_sel, "")
                        c3.text_input("Asesor Asignado", value=asesor_asignado, disabled=True)
                    else: 
                        nueva_ciudad = ""; asesor_asignado = ""
                        c3.text_input("Asesor Asignado", disabled=True)
                    
                    c4, c5, c6, c7 = st.columns(4)
                    lista_estados_mexico = [
                        "Aguascalientes", "Baja California", "Baja California Sur", "Campeche", "Chiapas", 
                        "Chihuahua", "Ciudad de México", "Coahuila", "Colima", "Durango", "Estado de México", 
                        "Guanajuato", "Guerrero", "Hidalgo", "Jalisco", "Michoacán", "Morelos", "Nayarit", 
                        "Nuevo León", "Oaxaca", "Puebla", "Querétaro", "Quintana Roo", "San Luis Potosí", 
                        "Sinaloa", "Sonora", "Tabasco", "Tamaulipas", "Tlaxcala", "Veracruz", "Yucatán", "Zacatecas"
                    ]
                    nuevo_estado = c4.selectbox("Estado *", [""] + lista_estados_mexico)
                    nuevo_seguro = c5.selectbox("Seguro", ["MULTI", "GNP", "AMBOS", "OTRO"])
                    nuevo_contacto = c6.text_input("Contacto Taller")
                    nuevo_tel = c7.text_input("Teléfono Principal / Contacto")
                    
                    c8, c9 = st.columns(2)
                    nuevo_wa = c8.text_input("Whatsapp")
                    nuevo_correo = c9.text_input("Correo")
                    
                    c10, c11, c12 = st.columns([2, 2, 1])
                    nueva_calle = c10.text_input("Calle y Número")
                    nueva_colonia = c11.text_input("Colonia")
                    nuevo_cp = c12.text_input("C.P.")

                    if st.form_submit_button("💾 Guardar Taller en Catálogo", type="primary"):
                        if nuevo_taller.strip() and nueva_ciudad.strip() and nuevo_estado.strip():
                            partes_dir = [p.strip() for p in [nueva_calle, nueva_colonia, nuevo_cp] if p.strip() != ""]
                            nueva_dir = ", ".join(partes_dir)
                            with st.spinner("Guardando en la base de datos..."):
                                try:
                                    doc = init_connection()
                                    try: ws_cat = doc.worksheet("BD_TALLERES")
                                    except:
                                        try: ws_cat = doc.worksheet("Catálogo")
                                        except:
                                            st.error("⚠️ No se encontró la pestaña BD_TALLERES. Verifica el nombre en Google Sheets.")
                                            st.stop()
                                            
                                    headers = [str(h).strip().upper() for h in ws_cat.row_values(1)]
                                    fila_nueva = [""] * len(headers)
                                    
                                    def s_idx(n): return headers.index(n) if n in headers else -1
                                    
                                    idx_tall = s_idx(col_taller_cat.upper()) if col_taller_cat else s_idx('TALLER')
                                    idx_cont = s_idx('CONTACTO')
                                    idx_tel = s_idx(col_tel_cat.upper()) if col_tel_cat else s_idx('TELEFONO')
                                    idx_wa = s_idx('WHATSAPP')
                                    idx_corr = s_idx('CORREO')
                                    idx_dir = s_idx(col_dir_cat.upper()) if col_dir_cat else s_idx('DIRECCION')
                                    idx_ciu = s_idx(col_ciudad_cat.upper()) if col_ciudad_cat else s_idx('CIUDAD')
                                    idx_est = s_idx(col_estado_cat.upper()) if col_estado_cat else s_idx('ESTADO')
                                    idx_ase = s_idx('ASESOR')
                                    idx_seg = s_idx('SEGURO')
                                    
                                    if idx_tall >= 0: fila_nueva[idx_tall] = nuevo_taller.upper()
                                    if idx_cont >= 0: fila_nueva[idx_cont] = nuevo_contacto.upper()
                                    if idx_tel >= 0: fila_nueva[idx_tel] = str(nuevo_tel)
                                    if idx_wa >= 0: fila_nueva[idx_wa] = str(nuevo_wa)
                                    if idx_corr >= 0: fila_nueva[idx_corr] = nuevo_correo
                                    if idx_dir >= 0: fila_nueva[idx_dir] = nueva_dir.upper()
                                    if idx_ciu >= 0: fila_nueva[idx_ciu] = nueva_ciudad.upper()
                                    if idx_est >= 0: fila_nueva[idx_est] = nuevo_estado.upper()
                                    if idx_ase >= 0: fila_nueva[idx_ase] = asesor_asignado.upper()
                                    if idx_seg >= 0: fila_nueva[idx_seg] = nuevo_seguro.upper()
                                    
                                    # Fallback si el archivo maestro no tiene cabeceras o no detecta el Taller
                                    if len(headers) == 0 or idx_tall == -1:
                                        fila_nueva = [nuevo_taller.upper(), nuevo_contacto.upper(), str(nuevo_tel), str(nuevo_wa), nuevo_correo, nueva_dir.upper(), nueva_ciudad.upper(), nuevo_estado.upper(), asesor_asignado.upper(), nuevo_seguro.upper()]
                                    
                                    ws_cat.append_row(fila_nueva, value_input_option='USER_ENTERED')
                                    st.success(f"✅ ¡Taller '{nuevo_taller}' guardado exitosamente!")
                                    st.cache_data.clear()
                                    time.sleep(1.5)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error guardando taller: {e}")
                        else:
                            st.error("❌ Por favor completa los campos obligatorios: Taller, Ciudad y Estado.")

    # ==========================
    # PESTAÑA 2: PROVEEDORES
    # ==========================
    with tab_proveedores:
        if not df_proveedores.empty:
            busqueda_prov = st.text_input("🔍 Buscar Proveedor por nombre, marca o especialidad...")
            df_prov_filtrado = df_proveedores.copy()
            
            if busqueda_prov:
                mask = df_prov_filtrado.apply(lambda row: row.astype(str).str.contains(busqueda_prov, case=False, na=False).any(), axis=1)
                df_prov_filtrado = df_prov_filtrado[mask]

            cols_prov = ['Proveedor', 'Sucursal', 'Marcas Especialidad', 'Días Crédito', 'Condición Pago', 'Teléfono', 'Dirección']
            cols_vista_prov = [c for c in cols_prov if c in df_prov_filtrado.columns]
            st.dataframe(df_prov_filtrado[cols_vista_prov], hide_index=True, use_container_width=True)

            if permiso_edicion:
                with st.expander("➕ Agregar Nuevo Proveedor", expanded=False):
                    with st.form("form_nuevo_proveedor", clear_on_submit=True):
                        col1, col2 = st.columns(2)
                        nuevo_prov = col1.text_input("Nombre del Proveedor *")
                        nueva_sucursal = col2.text_input("Sucursal / Referencia")
                        
                        col3, col4 = st.columns(2)
                        nuevas_marcas = col3.text_input("Marcas de Especialidad", placeholder="Ej. Nissan, Honda, Colisión")
                        nuevo_tel_p = col4.text_input("Teléfono o Contacto")
                        
                        nueva_dir_p = st.text_input("Dirección Completa")
                        
                        col5, col6, col7 = st.columns(3)
                        nuevo_tiempo = col5.selectbox("Tiempo Promedio de Entrega", ["Inmediata", "1 a 2 días", "3 a 5 días", "Más de 5 días", "Bajo Pedido"])
                        nueva_cond_pago = col6.selectbox("Condición de Pago", ["CONTADO", "CREDITO", "CONTRA ENTREGA"])
                        nuevos_dias_c = col7.number_input("Días Crédito", min_value=0, value=0, step=1)
                        
                        if st.form_submit_button("Guardar Proveedor", type="primary"):
                            if nuevo_prov.strip():
                                with st.spinner("Guardando proveedor en la base de datos..."):
                                    try:
                                        doc = init_connection()
                                        ws_prov = doc.worksheet("BD_PROVEEDORES")
                                        
                                        fila_nueva = [""] * 10
                                        headers = [str(h).strip() for h in ws_prov.row_values(1)]
                                        
                                        def safe_idx(name): return headers.index(name) if name in headers else -1
                                        
                                        i_prv = safe_idx('Proveedor')
                                        i_suc = safe_idx('Sucursal')
                                        i_mar = safe_idx('Marcas Especialidad')
                                        i_tel = safe_idx('Teléfono')
                                        i_dir = safe_idx('Dirección')
                                        i_tie = safe_idx('Tiempo de Entrega')
                                        i_con = safe_idx('Condición Pago')
                                        i_dia = safe_idx('Días Crédito')
                                        
                                        if i_prv >= 0: fila_nueva[i_prv] = nuevo_prov.upper()
                                        if i_suc >= 0: fila_nueva[i_suc] = nueva_sucursal.upper()
                                        if i_mar >= 0: fila_nueva[i_mar] = nuevas_marcas.upper()
                                        if i_tel >= 0: fila_nueva[i_tel] = str(nuevo_tel_p)
                                        if i_dir >= 0: fila_nueva[i_dir] = nueva_dir_p.upper()
                                        if i_tie >= 0: fila_nueva[i_tie] = nuevo_tiempo
                                        if i_con >= 0: fila_nueva[i_con] = nueva_cond_pago
                                        if i_dia >= 0: fila_nueva[i_dia] = str(nuevos_dias_c)
                                        
                                        ws_prov.append_row(fila_nueva, value_input_option='USER_ENTERED')
                                        st.success("✅ ¡Proveedor guardado exitosamente!")
                                        st.cache_data.clear()
                                        time.sleep(1.5)
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error guardando proveedor: {e}")
                            else:
                                st.error("❌ El Nombre del Proveedor es obligatorio.")
        else:
            st.warning("⚠️ No se encontró la pestaña 'BD_PROVEEDORES' en el archivo maestro.")

elif vista_actual == "📦 Inventario":
    if permiso_edicion:
        with st.expander("➕ Registrar Nueva Pieza", expanded=False):
            with st.form("form_alta_inv", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                ubicacion_n = c1.text_input("Ubicación Física"); oem_n = c2.text_input("No. Parte (OEM)"); alt_n = c3.text_input("No. Parte Alterno")
                desc_n = st.text_input("Descripción de la Pieza * (Obligatorio)")
                c4, c5, c6 = st.columns(3)
                marca_n = c4.text_input("Marca"); mod_n = c5.text_input("Modelo"); ver_n = c6.text_input("Versión")
                c7, c8, c9 = st.columns(3)
                ano_n = c7.text_input("Años Compatibilidad"); pos_n = c8.text_input("Posición / Lado"); cant_n = c9.number_input("Cantidad", min_value=1, step=1)
                c10, c11, c12 = st.columns(3)
                est_n = c10.selectbox("Estado de la Pieza", ["NUEVA", "REPARADA", "USADA", "GENÉRICA"]); costo_n = c11.number_input("Costo Adquisición", min_value=0.0, step=10.0); precio_n = c12.number_input("Precio Venta", min_value=0.0, step=10.0)
                c13, c14 = st.columns(2)
                sin_n = c13.text_input("No. Siniestro / Lote"); ml_n = c14.text_input("SKU Mercado Libre")
                if st.form_submit_button("💾 Guardar en Inventario"):
                    if desc_n.strip() == "": st.error("❌ La 'Descripción de la Pieza' es obligatoria.")
                    else:
                        try:
                            doc = init_connection(); ws_i = doc.worksheet("BD_INVENTARIO")
                            ws_i.append_row([str(v).upper() if isinstance(v, str) else v for v in [ubicacion_n, oem_n, alt_n, desc_n, marca_n, mod_n, ver_n, ano_n, pos_n, cant_n, est_n, costo_n, precio_n, sin_n, ml_n, "NO"]], value_input_option='USER_ENTERED')
                            st.success("✅ Pieza agregada exitosamente en la nube."); st.cache_data.clear(); time.sleep(1); st.rerun()
                        except Exception as e: st.error(f"❌ Error al guardar en la nube: {e}")

        st.markdown("---")
        with st.expander("📉 Registrar Salida / Venta", expanded=False):
            if not df_inventario.empty:
                col_skuint = next((c for c in df_inventario.columns if "SKU INT" in str(c).upper()), None)
                df_inv_act = df_inventario[df_inventario[col_skuint].astype(str).str.strip().str.upper() != 'PRE-001'].copy() if col_skuint else df_inventario.copy()
                df_inv_act['Cantidad_Num'] = pd.to_numeric(df_inv_act['Cantidad'], errors='coerce').fillna(0)
                df_stock = df_inv_act[(~df_inv_act['Sin Existencia']) & (df_inv_act['Cantidad_Num'] > 0)].copy()
                if not df_stock.empty:
                    df_stock['GS_Row'] = df_stock.index + 2
                    df_stock['Filtro_Venta'] = df_stock.apply(lambda r: f"ID:{r['GS_Row']} - " + " | ".join([e.upper() for e in [str(r.get('Número de Parte (OEM)', '')), str(r.get('Marca', '')), str(r.get('Modelo', '')), str(r.get('Descripción de la Pieza', ''))] if str(e).strip() not in ['nan','none','']]), axis=1)
                    with st.form("form_salida_inv", clear_on_submit=True):
                        st.info("Selecciona una pieza para descontar del inventario. Si la cantidad llega a 0, se ocultará automáticamente.")
                        pieza_sel = st.selectbox("Pieza a descontar:", options=[""] + sorted(list(df_stock['Filtro_Venta'].unique())))
                        c_cant, c_dest = st.columns([1, 3])
                        cant_descontar = c_cant.number_input("Cantidad a sacar", min_value=1, step=1); destino_salida = c_dest.text_input("Destino / Comentario (Ej. Venta Mostrador, Siniestro MULTI-123)")
                        if st.form_submit_button("📉 Confirmar Salida"):
                            if not pieza_sel: st.error("❌ Por favor selecciona una pieza.")
                            else:
                                try:
                                    fila_encontrada = int(pieza_sel.split(' - ')[0].replace('ID:', '').strip())
                                    doc = init_connection(); ws_i = doc.worksheet("BD_INVENTARIO")
                                    datos_i = ws_i.get_all_values()
                                    headers = [str(h).strip().upper() for h in datos_i[0]]
                                    idx_cant = headers.index('CANTIDAD') if 'CANTIDAD' in headers else 9; idx_sin = headers.index('NO. SINIESTRO / LOTE') if 'NO. SINIESTRO / LOTE' in headers else 13; idx_sinexist = headers.index('SIN EXISTENCIA') if 'SIN EXISTENCIA' in headers else 15
                                    cant_actual_str = str(datos_i[fila_encontrada-1][idx_cant]).strip()
                                    cant_actual = int(float(cant_actual_str)) if cant_actual_str.replace('.','',1).isdigit() else 0
                                    nueva_cant = cant_actual - cant_descontar
                                    if nueva_cant <= 0: nueva_cant = 0; ws_i.update_cell(fila_encontrada, idx_sinexist + 1, "SI")
                                    ws_i.update_cell(fila_encontrada, idx_cant + 1, nueva_cant)
                                    if destino_salida.strip():
                                        val_previo = str(datos_i[fila_encontrada-1][idx_sin]) if len(datos_i[fila_encontrada-1]) > idx_sin else ""
                                        nuevo_dest = f"{val_previo} [Salida: {destino_salida.upper()}]".strip()
                                        ws_i.update_cell(fila_encontrada, idx_sin + 1, nuevo_dest)
                                    st.success(f"✅ Salida registrada. Nuevo stock: {nueva_cant}"); st.cache_data.clear(); time.sleep(1); st.rerun()
                                except Exception as e: st.error(f"❌ Error al conectar con la nube: {e}")
                else: st.warning("No hay piezas disponibles en stock (Cantidades agotadas).")

        st.markdown("---")
        if not df_inventario.empty:
            col_skuint = next((c for c in df_inventario.columns if "SKU INT" in str(c).upper()), None)
            df_inv_filtrado = df_inventario[df_inventario[col_skuint].astype(str).str.strip().str.upper() != 'PRE-001'].copy() if col_skuint else df_inventario.copy()
            df_inv_filtrado['Cantidad_Num_Vista'] = pd.to_numeric(df_inv_filtrado['Cantidad'], errors='coerce').fillna(0)
            df_inv_filtrado = df_inv_filtrado[(~df_inv_filtrado['Sin Existencia']) & (df_inv_filtrado['Cantidad_Num_Vista'] > 0)].copy()
            if not df_inv_filtrado.empty:
                df_inv_filtrado['Filtro_Busqueda'] = df_inv_filtrado.apply(lambda r: " | ".join([e.upper() for e in [str(r.get('Número de Parte (OEM)', '')), str(r.get('Marca', '')), str(r.get('Modelo', '')), str(r.get('Descripción de la Pieza', ''))] if str(e).strip() not in ['nan','none','']]), axis=1)
                busqueda_inv = st.multiselect("🔍 Buscar Pieza:", options=sorted(list(df_inv_filtrado['Filtro_Busqueda'].dropna().unique())))
                df_inv_disp = df_inv_filtrado[df_inv_filtrado['Filtro_Busqueda'].isin(busqueda_inv)].copy() if busqueda_inv else df_inv_filtrado.copy()
                if 'Filtro_Busqueda' in df_inv_disp.columns: df_inv_disp = df_inv_disp.drop(columns=['Filtro_Busqueda'])
                if 'Cantidad_Num_Vista' in df_inv_disp.columns: df_inv_disp = df_inv_disp.drop(columns=['Cantidad_Num_Vista'])
                for c in df_inv_disp.columns:
                    if c != 'Sin Existencia': df_inv_disp[c] = df_inv_disp[c].fillna("").astype(str).replace(['nan', 'None', '0.0'], '').str.upper()
                df_inv_disp.insert(0, 'Nº', range(1, len(df_inv_disp) + 1)); st.markdown(f"**🔢 Total de piezas listadas:** {len(df_inv_disp)}")
                if permiso_edicion:
                    config_inv = {'Nº': st.column_config.NumberColumn("Nº", disabled=True), 'Sin Existencia': st.column_config.CheckboxColumn("Sin Existencia", default=False)}
                    st.data_editor(df_inv_disp, num_rows="dynamic", column_config=config_inv, use_container_width=True, hide_index=True, key="ed_inv")
                else: st.dataframe(df_inv_disp, use_container_width=True, hide_index=True)
            else: st.info("El inventario está vacío o todas las piezas están agotadas.")

# ==============================================================================
# === [BLOQUE 8: VISTAS - REMISIONES Y FACTURACIÓN] ===
# ==============================================================================
elif vista_actual == "📝 Remisiones":
    st.markdown("### 📝 Generación de Remisiones (Envío a Taller)")
    
    # Motor de búsqueda estricto local para evitar trampas en nombres de columnas
    def buscar_col_local(df_obj, exactos, parciales, excluidos=["USUARIO", "ENV"]):
        cols = df_obj.columns if hasattr(df_obj, 'columns') else df_obj
        cols_up = [str(c).strip().upper() for c in cols]
        for ex in exactos:
            if ex in cols_up: return cols[cols_up.index(ex)]
        for i, c_up in enumerate(cols_up):
            for p in parciales:
                if p in c_up and not any(exc in c_up for exc in excluidos): return cols[i]
        return None

    # --- CORRECCIÓN LÓGICA: Leemos df_completo para traer TODAS las aseguradoras ---
    col_estatus_univ = buscar_col_local(df_completo, ["ESTATUS", "STATUS"], ["ESTATUS", "STATUS"])
    col_remision_univ = buscar_col_local(df_completo, ["REMISION", "REMISIÓN", "FOLIO REMISION"], ["REMISION", "REMISIÓN"])
    col_aseguradora = buscar_col_local(df_completo, ["ASEGURADORA"], ["ASEGURADORA"])

    if col_estatus_univ and col_remision_univ and not df_completo.empty:
        estatus_permitidos = ["EN PROCESAMIENTO", "RECIBIDO"]
        cond_proceso = df_completo[col_estatus_univ].astype(str).str.upper().isin(estatus_permitidos)
        cond_sin_folio = df_completo[col_remision_univ].astype(str).str.strip() == ""
        df_listos = df_completo[cond_proceso & cond_sin_folio].copy()
    else: 
        df_listos = pd.DataFrame()

    if not df_listos.empty:
        col_id_r = buscar_col_local(df_listos, ["PEDIDO / SINIESTRO", "SINIESTRO"], ["SINIESTRO"])
        col_taller_r = buscar_col_local(df_listos, ["TALLER", "CDR"], ["TALLER"])
        col_marca_r = buscar_col_local(df_listos, ["MARCA"], ["MARCA"])
        col_modelo_r = buscar_col_local(df_listos, ["MODELO"], ["MODELO"])
        col_ano_r = buscar_col_local(df_listos, ["AÑO", "ANO"], ["AÑO", "ANO"])
        col_desc_r = buscar_col_local(df_listos, ["DESCRIPCIÓN", "DESCRIPCION"], ["DESCRIPCI", "REFACCI"])
        
        # Formatear el vehículo y la aseguradora
        def armar_vehiculo_r(r):
            m = str(r.get(col_marca_r, '')).strip().upper() if col_marca_r else ''
            mod = str(r.get(col_modelo_r, '')).strip().upper() if col_modelo_r else ''
            veh = mod if mod.startswith(m) and m != "" else f"{m} {mod}".strip()
            if col_ano_r:
                ano = str(r.get(col_ano_r, '')).strip()
                if ano.endswith('.0'): ano = ano[:-2]
                if ano not in ['', 'NAN', 'NONE']: veh += f" | {ano}"
            return veh
        
        df_listos['Vehiculo_Info'] = df_listos.apply(armar_vehiculo_r, axis=1)
        df_listos['Filtro_Siniestro'] = df_listos[col_id_r].astype(str).str.strip() + " | " + df_listos['Vehiculo_Info']
        
        if col_aseguradora:
            df_listos['Aseg_Grupo'] = df_listos[col_aseguradora].astype(str).str.upper().apply(lambda x: "MULTI" if "MULTI" in x else ("GNP" if "GNP" in x else "OTRA"))
        else:
            df_listos['Aseg_Grupo'] = "MULTI"
        
        st.markdown("#### 🎛️ Filtros de Búsqueda para Envío")
        filtro_r1, filtro_r2, filtro_r3 = st.columns([1.5, 1.5, 1.5])

        with filtro_r1:
            taller_sel_r = st.multiselect("🏢 Filtrar por Taller:", sorted([str(t) for t in df_listos[col_taller_r].dropna().unique() if str(t).strip() != '']) if col_taller_r else [], placeholder="Todos...")
        with filtro_r2:
            df_t_r = df_listos.copy()
            if taller_sel_r: df_t_r = df_t_r[df_t_r[col_taller_r].astype(str).isin(taller_sel_r)]
            siniestro_sel_r = st.multiselect("🚗 Siniestro - Vehículo:", sorted(list(df_t_r['Filtro_Siniestro'].dropna().unique())), placeholder="Todos...")
        with filtro_r3:
            df_t_desc_r = df_t_r.copy()
            if siniestro_sel_r: df_t_desc_r = df_t_desc_r[df_t_desc_r['Filtro_Siniestro'].isin(siniestro_sel_r)]
            desc_sel_r = st.multiselect("⚙️ Refacción:", sorted(list(df_t_desc_r[col_desc_r].dropna().astype(str).unique())) if col_desc_r else [], placeholder="Todas...")

        df_filtrado_rem = df_listos.copy()
        if taller_sel_r: df_filtrado_rem = df_filtrado_rem[df_filtrado_rem[col_taller_r].astype(str).isin(taller_sel_r)]
        if siniestro_sel_r: df_filtrado_rem = df_filtrado_rem[df_filtrado_rem['Filtro_Siniestro'].isin(siniestro_sel_r)]
        if desc_sel_r: df_filtrado_rem = df_filtrado_rem[df_filtrado_rem[col_desc_r].astype(str).isin(desc_sel_r)]
        
        st.markdown("---")

        if not df_filtrado_rem.empty:
            st.info("Selecciona las refacciones que deseas incluir en la nueva remisión.")
            
            # --- AGRUPACIÓN PRINCIPAL POR ASEGURADORA ---
            for aseguradora in ["MULTI", "GNP", "OTRA"]:
                df_aseg = df_filtrado_rem[df_filtrado_rem['Aseg_Grupo'] == aseguradora]
                if not df_aseg.empty:
                    icono = "🔵" if aseguradora == "MULTI" else ("🟠" if aseguradora == "GNP" else "⚪")
                    nombre_aseg = "MULTIASISTENCIAS" if aseguradora == "MULTI" else aseguradora
                    
                    with st.expander(f"{icono} {nombre_aseg} | {len(df_aseg)} Partida(s) lista(s) para remisionar", expanded=False):
                        
                        # --- AGRUPACIÓN SECUNDARIA POR TALLER (ACORDEÓN) ---
                        for taller, df_taller_rem in df_aseg.groupby(col_taller_r):
                            with st.expander(f"🏢 {taller} | {len(df_taller_rem)} Pieza(s) lista(s)", expanded=False):
                                agrupadores = [c for c in [col_id_r, col_marca_r, col_modelo_r] if c in df_taller_rem.columns]
                                
                                for keys, df_sin_rem in df_taller_rem.groupby(agrupadores):
                                    siniestro_v = keys[agrupadores.index(col_id_r)] if col_id_r in agrupadores else "S/N"
                                    marca_v = keys[agrupadores.index(col_marca_r)] if col_marca_r in agrupadores else ""
                                    modelo_v = keys[agrupadores.index(col_modelo_r)] if col_modelo_r in agrupadores else ""
                                    
                                    vehiculo_str = modelo_v if modelo_v.startswith(marca_v) and marca_v != "" else f"{marca_v} {modelo_v}".strip()
                                    
                                    with st.form(f"form_rem_{aseguradora}_{taller}_{siniestro_v}"):
                                        st.markdown(f"**🚗 Siniestro: {siniestro_v} | {vehiculo_str}**")
                                        piezas_a_remisionar = []
                                        for _, row_p in df_sin_rem.iterrows():
                                            desc_val = str(row_p.get(col_desc_r, ''))
                                            if st.checkbox(desc_val, value=True, key=f"chk_{aseguradora}_{siniestro_v}_{desc_val}"):
                                                piezas_a_remisionar.append(desc_val)
                                                
                                        if st.form_submit_button("📄 Generar Remisión PDF"):
                                            if piezas_a_remisionar:
                                                st.session_state['trigger_remision_manual'] = {'siniestro': siniestro_v, 'taller': taller, 'descripciones': piezas_a_remisionar}
                                                st.rerun()
                                            else: st.warning("Debes seleccionar al menos una pieza para generar la remisión.")
        else:
            st.warning("No hay refacciones que coincidan con los filtros actuales.")
    else:
        st.success("✅ No hay piezas marcadas listas para remisionar (EN PROCESAMIENTO o RECIBIDO sin folio asignado).")

    # -------------------------------------------------------------------------
    # --- BÓVEDA DE REIMPRESIÓN (REDISEÑADA) ---
    # -------------------------------------------------------------------------
    st.markdown("---")
    st.markdown("### 🖨️ Bóveda de Reimpresión")
    st.info("Busca por Número de Siniestro para ver y reimprimir todas las remisiones asociadas a él.")
    
    if col_remision_univ and not df_completo.empty:
        # Extraemos solo filas que sí contengan la cadena PMR
        df_con_folio = df_completo[df_completo[col_remision_univ].astype(str).str.upper().str.contains("PMR", na=False)].copy()
        
        if not df_con_folio.empty:
            col_id_reimp = buscar_col_local(df_con_folio, ["PEDIDO / SINIESTRO", "SINIESTRO"], ["SINIESTRO"])
            col_taller_reimp = buscar_col_local(df_con_folio, ["TALLER", "CDR"], ["TALLER"])
            col_desc_reimp = buscar_col_local(df_con_folio, ["DESCRIPCIÓN", "DESCRIPCION"], ["DESCRIPCI", "REFACCI"])
            col_cant_reimp = buscar_col_local(df_con_folio, ["CANTIDAD", "CANT"], ["CANTIDAD", "CANT"])
            col_marca_reimp = buscar_col_local(df_con_folio, ["MARCA"], ["MARCA"])
            col_modelo_reimp = buscar_col_local(df_con_folio, ["MODELO"], ["MODELO"])
            
            # Buscador Directo y Blindado por Siniestro
            col_search, _ = st.columns([1, 1])
            with col_search:
                lista_siniestros_con_folio = sorted(list(df_con_folio[col_id_reimp].dropna().astype(str).unique()))
                siniestro_a_reimprimir = st.selectbox("🔍 Buscar por Número de Siniestro:", [""] + lista_siniestros_con_folio, help="Selecciona el siniestro para ver sus remisiones guardadas.")
                
            if siniestro_a_reimprimir:
                # Filtramos el DF exclusivamente por el siniestro seleccionado
                df_sin_reimp = df_con_folio[df_con_folio[col_id_reimp].astype(str).str.strip() == siniestro_a_reimprimir].copy()
                
                if not df_sin_reimp.empty:
                    # Agrupamos por los folios exactos que existan para este siniestro
                    folios_crudos = df_sin_reimp[col_remision_univ].dropna().astype(str).unique()
                    
                    st.markdown(f"**Remisiones encontradas para el Siniestro {siniestro_a_reimprimir}:**")
                    
                    for folio_bruto in sorted(folios_crudos):
                        folio_limpio = str(folio_bruto).strip()
                        df_folio = df_sin_reimp[df_sin_reimp[col_remision_univ].astype(str) == folio_bruto].copy()
                        
                        with st.expander(f"📄 Folio: {folio_limpio} | {len(df_folio)} pieza(s)", expanded=True):
                            cols_mostrar_reimp = [c for c in [col_id_reimp, col_taller_reimp, col_desc_reimp, col_cant_reimp, col_marca_reimp, col_modelo_reimp] if c in df_folio.columns]
                            st.dataframe(df_folio[cols_mostrar_reimp], hide_index=True, use_container_width=True)
                            
                            if st.button(f"🖨️ Generar PDF para {folio_limpio}", key=f"btn_reimp_{siniestro_a_reimprimir}_{folio_limpio}"):
                                with st.spinner("Construyendo documento histórico..."):
                                    fila_0 = df_folio.iloc[0]
                                    taller_v = str(fila_0.get(col_taller_reimp, '')).strip()
                                    marca_v = str(fila_0.get(col_marca_reimp, '')).strip()
                                    modelo_v = str(fila_0.get(col_modelo_reimp, '')).strip()
                                    
                                    # Fecha de envio
                                    col_envio = buscar_col_local(df_folio, ["FECHA ENVIO", "FECHA ENVÍO"], ["FECHA ENV"])
                                    fecha_header = str(fila_0.get(col_envio, '')).strip() if col_envio else ''
                                    if not fecha_header or fecha_header in ['nan', 'None']: 
                                        tz_mx = datetime.timezone(datetime.timedelta(hours=-6))
                                        fecha_header = datetime.datetime.now(tz_mx).strftime('%d/%b/%Y').upper()
                                    else:
                                        fecha_header = fecha_header.upper()
                                        
                                    firma_digital = f"Reimpresión solicitada por: {st.session_state.get('usuario_actual', 'Sistema')}"
                                    
                                    # Dirección Taller
                                    dir_v = ""
                                    col_cat_taller = buscar_col_local(df_catalogo, ["TALLER", "CDR"], ["TALLER"])
                                    if not df_catalogo.empty and col_cat_taller:
                                        match_taller = df_catalogo[df_catalogo[col_cat_taller].astype(str).str.strip().str.upper() == taller_v.upper()]
                                        if not match_taller.empty:
                                            col_dir = buscar_col_local(df_catalogo, ["DIRECCION", "DIRECCIÓN"], ["DIRECCI"])
                                            if col_dir: dir_v = str(match_taller.iloc[0].get(col_dir, '')).strip()
                                    
                                    def limpiar_texto(txt): return str(txt).encode('latin-1', 'replace').decode('latin-1')

                                    pdf = FPDF(orientation='L', unit='mm', format='A4')
                                    pdf.set_auto_page_break(auto=False, margin=0); pdf.add_page()
                                    
                                    def dibujar_bloque_reimpresion(x_offset):
                                        import os
                                        y_offset = 15
                                        if os.path.exists("logo.png"):
                                            try: pdf.image("logo.png", x_offset, y_offset - 3, 30)
                                            except: pass
                                        
                                        pdf.set_font("Arial", 'B', 10); pdf.set_text_color(0, 51, 102); pdf.set_xy(x_offset + 32, y_offset)
                                        pdf.cell(70, 5, limpiar_texto("PREMIER SERVICIOS Y REFACCIONES"))
                                        pdf.set_font("Arial", 'B', 8); pdf.set_xy(x_offset + 32, y_offset + 5); pdf.cell(70, 4, limpiar_texto("PMR SERVICIOS AUTOMOTRIZ"))
                                        pdf.set_font("Arial", '', 7); pdf.set_text_color(100, 100, 100); pdf.set_xy(x_offset + 32, y_offset + 9); pdf.cell(70, 3, limpiar_texto("ALLENDE 228, AÑO DE JUAREZ"))
                                        pdf.set_xy(x_offset + 32, y_offset + 12); pdf.cell(70, 3, limpiar_texto("SAN NICOLAS DE LOS GARZA, N.L. | PSA 211015 B30"))

                                        pdf.set_text_color(0, 0, 0); pdf.set_xy(x_offset + 105, y_offset); pdf.set_font("Arial", 'B', 9); pdf.cell(30, 5, "REMISION", border=1, align='C')
                                        pdf.set_text_color(200, 0, 0); pdf.set_font("Arial", 'B', 10); pdf.set_xy(x_offset + 105, y_offset + 5); pdf.cell(30, 6, limpiar_texto(folio_limpio), border=1, align='C')
                                        pdf.set_text_color(100, 100, 100); pdf.set_font("Arial", '', 7); pdf.set_xy(x_offset + 105, y_offset + 12); pdf.cell(30, 4, f"FECHA: {fecha_header}", align='C')
                                        
                                        y_datos = y_offset + 22; pdf.set_fill_color(220, 220, 220); pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", 'B', 7)
                                        pdf.set_xy(x_offset, y_datos); pdf.cell(20, 5, "TALLER", border=1, fill=True); pdf.set_font("Arial", '', 7); pdf.cell(115, 5, limpiar_texto(f" {taller_v}")[:75], border=1)
                                        y_datos += 5; pdf.set_xy(x_offset, y_datos); pdf.set_font("Arial", 'B', 7); pdf.cell(20, 5, "DIRECCION", border=1, fill=True); pdf.set_font("Arial", '', 7); pdf.cell(115, 5, limpiar_texto(f" {dir_v}")[:85], border=1)
                                        y_datos += 5; pdf.set_xy(x_offset, y_datos); pdf.set_font("Arial", 'B', 7); pdf.cell(20, 5, "SINIESTRO", border=1, fill=True); pdf.set_font("Arial", 'B', 8); pdf.cell(45, 5, limpiar_texto(f" {siniestro_a_reimprimir}"), border=1)
                                        pdf.set_font("Arial", 'B', 7); pdf.cell(20, 5, "VEHICULO", border=1, fill=True); pdf.set_font("Arial", '', 7); pdf.cell(50, 5, limpiar_texto(f" {marca_v} {modelo_v}")[:35], border=1)

                                        y_tabla = y_datos + 10; pdf.set_xy(x_offset, y_tabla); pdf.set_fill_color(0, 0, 0); pdf.set_text_color(255, 255, 255); pdf.set_font("Arial", 'B', 7)
                                        pdf.cell(15, 6, "CANT", border=1, fill=True, align='C'); pdf.cell(120, 6, "DESCRIPCION", border=1, fill=True, align='C')

                                        y_item = y_tabla + 6; pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", '', 7)
                                        for _, row_rem in df_folio.iterrows():
                                            cant_v = str(row_rem.get(col_cant_reimp, 1))
                                            if not cant_v.strip() or cant_v == 'nan': cant_v = '1'
                                            pdf.set_xy(x_offset, y_item); pdf.cell(15, 5, limpiar_texto(cant_v), border=1, align='C'); pdf.cell(120, 5, limpiar_texto(str(row_rem.get(col_desc_reimp, '')))[:80], border=1)
                                            y_item += 5
                                            
                                        pdf.set_xy(x_offset, 192); pdf.set_font("Arial", 'I', 6); pdf.set_text_color(120, 120, 120); pdf.cell(135, 4, limpiar_texto(firma_digital), align='R')

                                    dibujar_bloque_reimpresion(10)
                                    pdf.set_draw_color(180, 180, 180); pdf.line(148.5, 10, 148.5, 200); pdf.set_draw_color(0, 0, 0)
                                    dibujar_bloque_reimpresion(152)

                                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                                        pdf.output(tmp.name)
                                        nombre_archivo = f"Reimpresion_{folio_limpio.replace(' ', '_')}_{siniestro_a_reimprimir}.pdf"
                                        with open(tmp.name, "rb") as f: pdf_bytes = f.read()
                                        
                                    st.session_state['pdfs_list'] = [{'folio': folio_limpio, 'siniestro': siniestro_a_reimprimir, 'bytes': pdf_bytes, 'nombre': nombre_archivo}]
                                    st.rerun()

elif vista_actual == "🧾 Facturación":
    st.markdown("### 🧾 Control de Facturación a Aseguradoras")
    
    # Motor de búsqueda estricto local
    def buscar_col_local_fac(df_obj, exactos, parciales, excluidos=["USUARIO", "ENV"]):
        cols = df_obj.columns if hasattr(df_obj, 'columns') else df_obj
        cols_up = [str(c).strip().upper() for c in cols]
        for ex in exactos:
            if ex in cols_up: return cols[cols_up.index(ex)]
        for i, c_up in enumerate(cols_up):
            for p in parciales:
                if p in c_up and not any(exc in c_up for exc in excluidos): return cols[i]
        return None
        
    col_estatus_fac = buscar_col_local_fac(df_trabajo, ["ESTATUS", "STATUS"], ["ESTATUS", "STATUS"])
    
    if col_estatus_fac and not df_trabajo.empty:
        df_por_facturar = df_trabajo[df_trabajo[col_estatus_fac].astype(str).str.upper() == "RECIBIDO"].copy()
    else: df_por_facturar = pd.DataFrame()

    st.markdown(f"**📦 Total de partidas esperando facturación:** {len(df_por_facturar)}")
    
    if not df_por_facturar.empty:
        col_id_fac = buscar_col_local_fac(df_por_facturar, ["PEDIDO / SINIESTRO", "SINIESTRO"], ["SINIESTRO"])
        col_taller_fac = buscar_col_local_fac(df_por_facturar, ["TALLER", "CDR"], ["TALLER"])
        col_cant_fac = buscar_col_local_fac(df_por_facturar, ["CANTIDAD", "CANT"], ["CANTIDAD", "CANT"])
        col_desc_fac = buscar_col_local_fac(df_por_facturar, ["DESCRIPCIÓN", "DESCRIPCION"], ["DESCRIPCI", "REFACCI"])
        col_origen_fac = buscar_col_local_fac(df_por_facturar, ["ORIGEN"], ["ORIGEN"])
        col_precio_fac = buscar_col_local_fac(df_por_facturar, ["PRECIO", "COSTO VENTA"], ["PRECIO", "COSTO"])
        
        if permiso_edicion:
            df_por_facturar['Facturado'] = False
            cols_visibles = [c for c in [col_id_fac, 'Vehiculo_Info', col_taller_fac, col_cant_fac, col_desc_fac, col_origen_fac, col_precio_fac] if c in df_por_facturar.columns] + ['Facturado']
            config_fact = {}
            if col_id_fac in df_por_facturar.columns: config_fact[col_id_fac] = st.column_config.TextColumn("Siniestro", disabled=True)
            if 'Vehiculo_Info' in df_por_facturar.columns: config_fact['Vehiculo_Info'] = st.column_config.TextColumn("Vehículo", disabled=True)
            config_fact["Facturado"] = st.column_config.CheckboxColumn("🧾 Facturar", default=False)
            
            df_editado_fact = st.data_editor(df_por_facturar[cols_visibles], column_config=config_fact, hide_index=True, use_container_width=True, disabled=[c for c in cols_visibles if c != 'Facturado'], key="ed_facturacion")
            
            for col in df_por_facturar.columns:
                if col not in df_editado_fact.columns: df_editado_fact[col] = df_por_facturar[col].values
        else:
            cols_visibles = [c for c in [col_id_fac, 'Vehiculo_Info', col_taller_fac, col_cant_fac, col_desc_fac, col_origen_fac, col_precio_fac] if c in df_por_facturar.columns]
            st.dataframe(df_por_facturar[cols_visibles], hide_index=True, use_container_width=True)
    else:
        st.success("✅ Todo está al día. No hay partidas pendientes de facturación.")

# ==============================================================================
# === [BLOQUE 9: VISTAS - RUTAS, PRECIOS, CONSULTAS GLOBALES Y CUARTEL GENERAL] ===
# ==============================================================================
elif vista_actual == "🚚 Rutas":
    st.markdown("### 🚚 Despachador de Rutas (Logística Local - Nuevo León)")
    st.info("Selecciona los destinos que visitará el operador hoy. Desmarca las piezas que NO deseas enviar en este viaje.")
    
    tab_entregas, tab_recolecciones, tab_compras, tab_cotizacion = st.tabs(["📦 Entregas (CDR)", "↩ Recolecciones (CDR)", "🛒 Compras", "🔎 Cotizaciones"])
    
    dict_dir_talleres = {}
    dict_estado_talleres = {}
    if not df_catalogo.empty:
        col_cat_tall = next((c for c in df_catalogo.columns if "TALLER" in str(c).upper()), None)
        col_cat_dir = next((c for c in df_catalogo.columns if "DIRECCI" in str(c).upper()), None)
        col_cat_est = next((c for c in df_catalogo.columns if "ESTADO" in str(c).upper()), None)
        if col_cat_tall:
            if col_cat_dir: dict_dir_talleres = dict(zip(df_catalogo[col_cat_tall].astype(str).str.strip().str.upper(), df_catalogo[col_cat_dir].astype(str).str.strip().str.upper()))
            if col_cat_est: dict_estado_talleres = dict(zip(df_catalogo[col_cat_tall].astype(str).str.strip().str.upper(), df_catalogo[col_cat_est].astype(str).str.strip().str.upper()))
            
    dict_dir_provs = {}
    if not df_proveedores.empty:
        dict_dir_provs = dict(zip(df_proveedores['Proveedor'].astype(str).str.strip().str.upper(), df_proveedores['Dirección'].astype(str).str.strip().str.upper()))

    def enviar_a_bd_rutas(tipo, lugar, direccion, df_partidas, col_vehiculo, col_vin, col_pieza, col_siniestro, notas_op=""):
        try:
            doc = init_connection()
            ws_rutas = doc.worksheet("BD_RUTAS")
            tz_mx = datetime.timezone(datetime.timedelta(hours=-6))
            ahora = datetime.datetime.now(tz_mx)
            id_ruta = "R-" + ahora.strftime("%Y%m%d%H%M%S")
            fecha_hoy = ahora.strftime("%d/%b/%Y").upper()
            
            filas_a_insertar = []
            for _, row in df_partidas.iterrows():
                v_veh = str(row.get(col_vehiculo, 'S/D')).strip() if col_vehiculo and pd.notna(row.get(col_vehiculo)) else "S/D"
                v_vin = str(row.get(col_vin, '')).strip() if col_vin and pd.notna(row.get(col_vin)) else ""
                v_sin = str(row.get(col_siniestro, 'S/D')).strip() if col_siniestro and pd.notna(row.get(col_siniestro)) else "S/D"
                v_pza = str(row.get(col_pieza, 'S/D')).strip() if col_pieza and pd.notna(row.get(col_pieza)) else "S/D"
                fila = [id_ruta, fecha_hoy, tipo, lugar.upper(), direccion.upper(), v_veh, v_vin, v_pza, v_sin, "Pendiente", "", "", notas_op]
                filas_a_insertar.append(fila)
                
            if filas_a_insertar: ws_rutas.append_rows(filas_a_insertar, value_input_option='USER_ENTERED')
            return True
        except Exception as e: st.error(f"Error al enviar a BD_RUTAS: {e}"); return False

    with tab_entregas:
        if col_estatus and not df_trabajo.empty:
            df_para_entrega = df_trabajo[df_trabajo[col_estatus].astype(str).str.upper().isin(["EN TRANSITO", "RECIBIDO"])].copy()
            if not df_para_entrega.empty:
                df_para_entrega['Estado_CDR'] = df_para_entrega[col_taller].astype(str).str.strip().str.upper().map(dict_estado_talleres).fillna("")
                df_para_entrega = df_para_entrega[df_para_entrega['Estado_CDR'].str.contains("NUEVO LEÓN|NUEVO LEON|NL", case=False, na=False)]
                
            if not df_para_entrega.empty:
                for taller, df_taller in df_para_entrega.groupby(col_taller):
                    with st.expander(f"🏢 {taller} | {len(df_taller)} piezas en sistema", expanded=False):
                        cols_ver = [c for c in [col_id, 'Vehiculo_Info', col_desc, col_estatus, col_remision] if c in df_taller.columns]
                        df_interactivo = df_taller[cols_ver].copy()
                        df_interactivo.insert(0, 'Enviar Hoy', True)
                        config_ent = {'Enviar Hoy': st.column_config.CheckboxColumn("Enviar Hoy", default=True)}
                        for c in cols_ver: config_ent[c] = st.column_config.TextColumn(disabled=True)
                        editado = st.data_editor(df_interactivo, column_config=config_ent, hide_index=True, use_container_width=True, key=f"ed_ent_{taller}")
                        direccion_taller = dict_dir_talleres.get(str(taller).strip().upper(), "Dirección no registrada en catálogo")
                        nota_op_ent = st.text_input("📝 Instrucciones / Notas:", key=f"nota_ent_{taller}", placeholder="Ej. Dejar con el jefe de taller")
                        
                        if st.button(f"➕ Enviar Selección a {taller}", key=f"btn_ent_{taller}"):
                            seleccionadas = editado[editado['Enviar Hoy'] == True]
                            if not seleccionadas.empty:
                                with st.spinner(f"Inyectando parada..."):
                                    col_vin = next((c for c in df_taller.columns if "VIN" in str(c).upper() or "SERIE" in str(c).upper()), None)
                                    exito = enviar_a_bd_rutas('entrega', taller, direccion_taller, df_taller.loc[seleccionadas.index], 'Vehiculo_Info', col_vin, col_desc, col_id, notas_op=nota_op_ent)
                                    if exito: st.success(f"✅ ¡Enviado con {len(seleccionadas)} pieza(s)!"); time.sleep(1.5); st.rerun()
                            else: st.warning("Selecciona al menos una pieza.")
            else: st.success("✅ No hay entregas locales pendientes.")

    with tab_recolecciones:
        if col_estatus and not df_trabajo.empty:
            df_para_recoleccion = df_trabajo[df_trabajo[col_estatus].astype(str).str.upper().str.contains("RECOLEC")].copy()
            if not df_para_recoleccion.empty:
                df_para_recoleccion['Estado_CDR'] = df_para_recoleccion[col_taller].astype(str).str.strip().str.upper().map(dict_estado_talleres).fillna("")
                df_para_recoleccion = df_para_recoleccion[df_para_recoleccion['Estado_CDR'].str.contains("NUEVO LEÓN|NUEVO LEON|NL", case=False, na=False)]
                
            if not df_para_recoleccion.empty:
                for taller, df_taller in df_para_recoleccion.groupby(col_taller):
                    with st.expander(f"🏢 {taller} | {len(df_taller)} piezas a recolectar", expanded=False):
                        cols_ver = [c for c in [col_id, 'Vehiculo_Info', col_desc, col_estatus] if c in df_taller.columns]
                        df_interactivo = df_taller[cols_ver].copy()
                        df_interactivo.insert(0, 'Recoger Hoy', True)
                        config_rec = {'Recoger Hoy': st.column_config.CheckboxColumn("Recoger Hoy", default=True)}
                        for c in cols_ver: config_rec[c] = st.column_config.TextColumn(disabled=True)
                        editado = st.data_editor(df_interactivo, column_config=config_rec, hide_index=True, use_container_width=True, key=f"ed_rec_{taller}")
                        direccion_taller = dict_dir_talleres.get(str(taller).strip().upper(), "Dirección no registrada en catálogo")
                        nota_op_rec = st.text_input("📝 Instrucciones / Notas:", key=f"nota_rec_{taller}", placeholder="Ej. Validar que venga completa")
                        
                        if st.button(f"➕ Enviar Selección a {taller}", key=f"btn_rec_{taller}"):
                            seleccionadas = editado[editado['Recoger Hoy'] == True]
                            if not seleccionadas.empty:
                                with st.spinner("Enviando..."):
                                    col_vin = next((c for c in df_taller.columns if "VIN" in str(c).upper() or "SERIE" in str(c).upper()), None)
                                    exito = enviar_a_bd_rutas('recoleccion', taller, direccion_taller, df_taller.loc[seleccionadas.index], 'Vehiculo_Info', col_vin, col_desc, col_id, notas_op=nota_op_rec)
                                    if exito: st.success(f"✅ ¡Recolección asignada!"); time.sleep(1.5); st.rerun()
                            else: st.warning("Selecciona al menos una pieza.")
            else: st.success("✅ No hay recolecciones locales pendientes.")
                
    with tab_compras:
        if not df_compras.empty:
            df_c_pend = df_compras[df_compras['Recibido'].astype(str).str.strip().str.upper().isin(['FALSE', 'NO', '0', 'FALSO', ''])].copy()
            if not df_c_pend.empty:
                for prov, df_prov in df_c_pend.groupby('Proveedor'):
                    prov_limpio = str(prov).strip()
                    if prov_limpio and prov_limpio.lower() != 'nan':
                        with st.expander(f"🚚 {prov_limpio} | {len(df_prov)} compras pendientes", expanded=False):
                            cols_ver = ['Siniestro', 'Vehículo', 'Descripción Pieza', 'Condición Pago']
                            df_interactivo = df_prov[cols_ver].copy()
                            df_interactivo.insert(0, 'Recolectar Hoy', True)
                            config_comp = {'Recolectar Hoy': st.column_config.CheckboxColumn("Recolectar Hoy", default=True)}
                            for c in cols_ver: config_comp[c] = st.column_config.TextColumn(disabled=True)
                            editado = st.data_editor(df_interactivo, column_config=config_comp, hide_index=True, use_container_width=True, key=f"ed_comp_{prov_limpio}")
                            direccion_prov = dict_dir_provs.get(prov_limpio.upper(), "Dirección no registrada")
                            nota_op_comp = st.text_input("📝 Instrucciones / Notas:", key=f"nota_comp_{prov_limpio}", placeholder="Ej. Llevar cheque")
                            
                            if st.button(f"➕ Enviar Selección a {prov_limpio}", key=f"btn_comp_{prov_limpio}"):
                                seleccionadas = editado[editado['Recolectar Hoy'] == True]
                                if not seleccionadas.empty:
                                    with st.spinner(f"Asignando visita..."):
                                        exito = enviar_a_bd_rutas('compra', prov_limpio, direccion_prov, df_prov.loc[seleccionadas.index], 'Vehículo', None, 'Descripción Pieza', 'Siniestro', notas_op=nota_op_comp)
                                        if exito: st.success(f"✅ ¡Visita enviada al celular!"); time.sleep(1.5); st.rerun()
                                else: st.warning("Selecciona al menos una pieza.")
            else: st.success("✅ Todas las compras han sido marcadas como recibidas.")
        else: st.warning("La base de datos de compras está vacía.")
        
    with tab_cotizacion:
        st.markdown("#### 🔎 Asignar Cotización / Visita Especial")
        st.caption("Usa esta pestaña para enviar al operador a revisar piezas sin una orden de compra formal.")
        
        col_cot1, col_cot2 = st.columns(2)
        with col_cot1:
            sel_lugar = st.selectbox("Lugar (Yonke / Agencia / Proveedor) *", lista_proveedores + ["➕ [ ESCRIBIR OTRO NUEVO... ]"])
            lugar_cot = st.text_input("Escribe el nombre del nuevo lugar *") if sel_lugar == "➕ [ ESCRIBIR OTRO NUEVO... ]" else sel_lugar
        with col_cot2:
            lugar_base = lugar_cot.split(' - ')[0].strip() if ' - ' in lugar_cot else lugar_cot
            dir_sugerida = dict_dir_provs.get(lugar_base.upper(), "") if lugar_base else ""
            dir_cot = st.text_input("Dirección o Zona", value=dir_sugerida)
            
        col_cot3, col_cot4 = st.columns(2)
        vehiculo_cot = col_cot3.text_input("Vehículo *")
        vin_cot = col_cot4.text_input("VIN / Número de Serie")
        
        st.markdown("**Piezas a buscar ***")
        df_p_vacia = pd.DataFrame([{"Número de Parte": "", "Descripción": ""}])
        config_columnas_cot = {"Número de Parte": st.column_config.TextColumn("No. de Parte (Opcional)", width="medium"), "Descripción": st.column_config.TextColumn("Descripción de la Pieza", width="large")}
        df_piezas_cot = st.data_editor(df_p_vacia, num_rows="dynamic", use_container_width=True, key="tabla_cotizaciones", hide_index=True, column_config=config_columnas_cot)
        nota_cot = st.text_input("📝 Instrucciones / Notas para el operador:", placeholder="Ej. Solo tomar fotos", key="nota_cot_manual")
        
        if st.button("➕ Enviar Cotización a la Ruta", type="primary", use_container_width=True):
            piezas_validas = df_piezas_cot[(df_piezas_cot["Descripción"].str.strip() != "") | (df_piezas_cot["Número de Parte"].str.strip() != "")]
            if lugar_cot.strip() and vehiculo_cot.strip() and not piezas_validas.empty:
                df_cot_list = []
                for _, row_p in piezas_validas.iterrows():
                    np = str(row_p['Número de Parte']).strip(); desc = str(row_p['Descripción']).strip()
                    texto_pieza = f"{np} - {desc}".strip(" - ") if np and desc else (np if np else desc)
                    df_cot_list.append({'Vehiculo_C': vehiculo_cot.upper(), 'VIN_C': vin_cot.upper(), 'Pieza_C': texto_pieza.upper(), 'Sin_C': 'COTIZACIÓN'})
                exito = enviar_a_bd_rutas('cotizacion', lugar_cot, dir_cot, pd.DataFrame(df_cot_list), 'Vehiculo_C', 'VIN_C', 'Pieza_C', 'Sin_C', notas_op=nota_cot)
                if exito: st.success(f"✅ ¡Cotización en {lugar_cot} enviada!"); time.sleep(1.5); st.rerun()
            else: st.error("❌ Completa Lugar, Vehículo y agrega al menos la descripción o número de parte.")

elif vista_actual == "Precios Promedio":
    st.markdown("## 💲 Precios Promedio Históricos")
    st.info("Filtra el historial de la base unificada para obtener referencias de precios (Promedio, Máximo y Mínimo) para nuevas cotizaciones.")

    if not df_completo.empty:
        df_cot = df_completo.copy()
        col_marca_cot = next((c for c in df_cot.columns if "MARCA" in str(c).upper()), None)
        col_modelo_cot = next((c for c in df_cot.columns if "MODELO" in str(c).upper()), None)
        col_ano_cot = next((c for c in df_cot.columns if "AÑO" in str(c).upper() or "ANO" in str(c).upper()), None)
        col_desc_cot = next((c for c in df_cot.columns if "DESCRIPCI" in str(c).upper() or "REFACCI" in str(c).upper()), None)
        col_origen_cot = next((c for c in df_cot.columns if "ORIGEN" in str(c).upper()), None)
        col_precio_cot = next((c for c in df_cot.columns if "PRECIO" in str(c).upper() or "COSTO" in str(c).upper()), None)

        if col_marca_cot and col_precio_cot and col_desc_cot:
            df_cot['Precio_Num'] = df_cot[col_precio_cot].astype(str).replace({r'\$': '', r',': '', r' ': ''}, regex=True)
            df_cot['Precio_Num'] = pd.to_numeric(df_cot['Precio_Num'], errors='coerce')
            df_cot = df_cot.dropna(subset=['Precio_Num']) 
            df_cot = df_cot[df_cot['Precio_Num'] > 0] 

            col_m, col_mo, col_a, col_p = st.columns(4)
            with col_m:
                lista_marcas = ["Todas"] + sorted(df_cot[col_marca_cot].dropna().astype(str).unique().tolist())
                filtro_marca = st.selectbox("Marca", options=lista_marcas)
            with col_mo:
                if filtro_marca != "Todas": lista_modelos = ["Todos"] + sorted(df_cot[df_cot[col_marca_cot] == filtro_marca][col_modelo_cot].dropna().astype(str).unique().tolist())
                else: lista_modelos = ["Todos"] + sorted(df_cot[col_modelo_cot].dropna().astype(str).unique().tolist())
                filtro_modelo = st.selectbox("Modelo", options=lista_modelos)
            with col_a:
                lista_anios = ["Todos"] + sorted(df_cot[col_ano_cot].dropna().astype(str).unique().tolist(), reverse=True)
                filtro_anio = st.selectbox("Año", options=lista_anios)
            with col_p:
                filtro_pieza = st.text_input("Buscar Pieza (Ej. Salpicadera)", value="")

            if filtro_marca != "Todas": df_cot = df_cot[df_cot[col_marca_cot] == filtro_marca]
            if filtro_modelo != "Todos": df_cot = df_cot[df_cot[col_modelo_cot] == filtro_modelo]
            if filtro_anio != "Todos": df_cot = df_cot[df_cot[col_ano_cot].astype(str) == filtro_anio]
            if filtro_pieza.strip() != "": df_cot = df_cot[df_cot[col_desc_cot].astype(str).str.contains(filtro_pieza.strip(), case=False, na=False)]

            st.divider()

            if not df_cot.empty:
                precio_promedio = df_cot['Precio_Num'].mean(); precio_max = df_cot['Precio_Num'].max(); precio_min = df_cot['Precio_Num'].min()
                kpi1, kpi2, kpi3 = st.columns(3)
                kpi1.metric("⚖️ Precio Promedio", f"${precio_promedio:,.2f}" if pd.notnull(precio_promedio) else "$0.00")
                kpi2.metric("📈 Precio Máximo", f"${precio_max:,.2f}" if pd.notnull(precio_max) else "$0.00")
                kpi3.metric("📉 Precio Mínimo", f"${precio_min:,.2f}" if pd.notnull(precio_min) else "$0.00")

                st.caption(f"**Resultados encontrados:** {len(df_cot)} piezas históricas")
                columnas_vista = [c for c in [col_marca_cot, col_modelo_cot, col_ano_cot, col_desc_cot, col_origen_cot, col_precio_cot] if c]
                st.dataframe(df_cot[columnas_vista].sort_values(by=col_precio_cot, ascending=False), use_container_width=True, hide_index=True)
            else: st.info("No hay registros históricos que coincidan con estos filtros.")
        else: st.warning("Faltan columnas clave (Marca, Modelo, Descripción o Precio) en la base maestra.")
    else: st.warning("La base de datos está vacía.")

elif vista_actual == "🔍 Consultas":
    st.markdown("## 🔍 Consulta Global y Filtros de Búsqueda")
    st.info("Utiliza los filtros desplegables para encontrar refacciones y siniestros específicos en el histórico.")
    
    if not modo_consulta and permiso_edicion and "Daniel" in st.session_state.get("usuario_actual", ""):
        with st.expander("👑 Editor Maestro (Modo Dios)", expanded=False):
            st.info("Control total: Edita cualquier dato histórico o activo. Para logística inversa y reemplazo, selecciona 'EN PROCESO DE CAMBIO' en la columna de Estatus.")
            
            if not df_trabajo.empty and col_id in df_trabajo.columns:
                siniestros_unicos = sorted(list(df_trabajo[col_id].dropna().astype(str).unique()))
                sin_sel = st.selectbox("🔍 Escribe y selecciona el Siniestro a intervenir:", [""] + siniestros_unicos)
                
                if sin_sel:
                    df_edit = df_trabajo[df_trabajo[col_id].astype(str) == sin_sel].copy()
                    cols_dios = [c for c in [col_id, 'Vehiculo_Info', col_taller, col_desc, col_cant, col_precio, col_estatus, col_vencimiento, col_comentarios] if c in df_edit.columns]
                    
                    estatus_bd = list(df_trabajo[col_estatus].dropna().astype(str).unique()) if col_estatus else []
                    estatus_base = ["EN PROCESO DE REEMBOLSO", "REEMBOLSADO", "POR CONFIRMAR", "EN PROCESAMIENTO", "EN TRANSITO", "ENTREGADO", "RECIBIDO", "FACTURADO", "CANCELADO", "EN PROCESO DE CAMBIO"]
                    opciones_estatus = sorted(list(set(estatus_bd + estatus_base)))
                    
                    config_dios = {}
                    if col_estatus: config_dios[col_estatus] = st.column_config.SelectboxColumn("Estatus", options=opciones_estatus)
                    if 'Vehiculo_Info' in df_edit.columns: config_dios['Vehiculo_Info'] = st.column_config.TextColumn("Vehículo", disabled=True)
                    if col_id: config_dios[col_id] = st.column_config.TextColumn("Siniestro", disabled=True)
                    
                    st.caption("Modifica directamente en la tabla y presiona Guardar. Si seleccionas 'EN PROCESO DE CAMBIO', la original pasará a recolección y se creará una nueva partida clonada en estado 'POR CONFIRMAR'.")
                    df_modificado = st.data_editor(df_edit[cols_dios], column_config=config_dios, key="editor_dios", use_container_width=True, hide_index=True)
                    
                    if st.button("💾 Ejecutar Cambios (Modo Dios)", type="primary"):
                        with st.spinner("Inyectando cambios en la base de datos..."):
                            try:
                                doc = init_connection()
                                ws_uni = doc.worksheet("BD_UNIFICADA"); ws_hist = doc.worksheet("BD_HISTORICO")
                                datos_uni = ws_uni.get_all_values(); datos_hist = ws_hist.get_all_values()
                                
                                def construir_mapa(datos_hoja):
                                    mapa = {}
                                    if len(datos_hoja) > 1:
                                        encabezados = [str(x).strip().upper() for x in datos_hoja[0]]
                                        idx_sin = encabezados.index("PEDIDO / SINIESTRO") if "PEDIDO / SINIESTRO" in encabezados else -1
                                        idx_desc = encabezados.index("DESCRIPCIÓN") if "DESCRIPCIÓN" in encabezados else (encabezados.index("DESCRIPCION") if "DESCRIPCION" in encabezados else -1)
                                        if idx_sin != -1 and idx_desc != -1:
                                            for i, row in enumerate(datos_hoja[1:]):
                                                if len(row) > max(idx_sin, idx_desc):
                                                    llave = f"{str(row[idx_sin]).strip()}_{str(row[idx_desc]).strip()}".upper()
                                                    mapa[llave] = i + 2 
                                    return mapa
                                
                                mapa_uni = construir_mapa(datos_uni); mapa_hist = construir_mapa(datos_hist)
                                celdas_a_actualizar_uni = []; celdas_a_actualizar_hist = []
                                filas_nuevas_uni = []; filas_nuevas_hist = []
                                encabezados_uni = [str(x).strip() for x in datos_uni[0]]; encabezados_hist = [str(x).strip() for x in datos_hist[0]]
                                
                                def crear_fila_clon(encabezados, index_en_bd, datos_matriz):
                                    if not index_en_bd or index_en_bd > len(datos_matriz): return [""] * len(encabezados)
                                    fila_original = datos_matriz[index_en_bd - 1].copy()
                                    while len(fila_original) < len(encabezados): fila_original.append("")
                                    for idx, h in enumerate(encabezados):
                                        h_up = str(h).strip().upper()
                                        if "ESTATUS" in h_up or "STATUS" in h_up: fila_original[idx] = "POR CONFIRMAR"
                                        elif "DESCRIPCIÓN" in h_up or "DESCRIPCION" in h_up or "REFACCI" in h_up: fila_original[idx] = f"{str(fila_original[idx]).strip()} (CAMBIO)"
                                        elif any(x in h_up for x in ["FECHA", "VENCIMIENTO", "PROMESA", "GUIA", "PAQUETERIA", "REMISION", "ASIGNAC"]): fila_original[idx] = ""
                                    return fila_original

                                for index, row_orig in df_edit.iterrows():
                                    row_mod = df_modificado.loc[index]
                                    cambios_detectados = any(str(row_orig[c]) != str(row_mod[c]) for c in cols_dios)
                                    if cambios_detectados:
                                        llave_busqueda = f"{str(row_mod[col_id]).strip()}_{str(row_mod[col_desc]).strip()}".upper()
                                        fila_en_uni = mapa_uni.get(llave_busqueda); fila_en_hist = mapa_hist.get(llave_busqueda)
                                        estatus_sel_dios = str(row_mod[col_estatus]).strip()
                                        
                                        if estatus_sel_dios == "EN PROCESO DE CAMBIO":
                                            if fila_en_uni and col_estatus in encabezados_uni: celdas_a_actualizar_uni.append(gspread.Cell(row=fila_en_uni, col=encabezados_uni.index(col_estatus) + 1, value="EN PROCESO DE RECOLECCIÓN"))
                                            if fila_en_hist and col_estatus in encabezados_hist: celdas_a_actualizar_hist.append(gspread.Cell(row=fila_en_hist, col=encabezados_hist.index(col_estatus) + 1, value="EN PROCESO DE RECOLECCIÓN"))
                                            if fila_en_uni: filas_nuevas_uni.append(crear_fila_clon(encabezados_uni, fila_en_uni, datos_uni))
                                            if fila_en_hist: filas_nuevas_hist.append(crear_fila_clon(encabezados_hist, fila_en_hist, datos_hist))
                                        else:
                                            for c in cols_dios:
                                                if str(row_orig[c]) != str(row_mod[c]):
                                                    nuevo_valor = row_mod[c]
                                                    if fila_en_uni and c in encabezados_uni: celdas_a_actualizar_uni.append(gspread.Cell(row=fila_en_uni, col=encabezados_uni.index(c) + 1, value=nuevo_valor))
                                                    if fila_en_hist and c in encabezados_hist: celdas_a_actualizar_hist.append(gspread.Cell(row=fila_en_hist, col=encabezados_hist.index(c) + 1, value=nuevo_valor))
                                                    
                                if celdas_a_actualizar_uni: ws_uni.update_cells(celdas_a_actualizar_uni, value_input_option='USER_ENTERED')
                                if celdas_a_actualizar_hist: ws_hist.update_cells(celdas_a_actualizar_hist, value_input_option='USER_ENTERED')
                                if filas_nuevas_uni: ws_uni.append_rows(filas_nuevas_uni, value_input_option='USER_ENTERED')
                                if filas_nuevas_hist: ws_hist.append_rows(filas_nuevas_hist, value_input_option='USER_ENTERED')
                                
                                st.cache_data.clear(); st.success("⚡ ¡Cambios y clonaciones aplicados con éxito en la matriz!"); time.sleep(1.5); st.rerun()
                            except Exception as e: st.error(f"Error al guardar: {e}")
    st.markdown("---")
    
    if not df_completo.empty:
        col_id_univ = next((c for c in df_completo.columns if "SINIESTRO" in str(c).upper()), None)
        col_taller_univ = next((c for c in df_completo.columns if "TALLER" in str(c).upper()), None)
        col_estatus_univ = next((c for c in df_completo.columns if "ESTATUS" in str(c).upper() or "STATUS" in str(c).upper()), None)
        col_desc_univ = next((c for c in df_completo.columns if "DESCRIPCI" in str(c).upper() or "REFACCI" in str(c).upper()), None)
        col_marca_univ = next((c for c in df_completo.columns if "MARCA" in str(c).upper()), None)
        col_modelo_univ = next((c for c in df_completo.columns if "MODELO" in str(c).upper()), None)
        col_ano_univ = next((c for c in df_completo.columns if "AÑO" in str(c).upper() or "ANO" in str(c).upper()), None)
        
        df_busqueda = df_completo.copy()
        
        if col_marca_univ and col_modelo_univ and col_id_univ:
            def armar_vehiculo_filtro(row):
                m = str(row.get(col_marca_univ, '')).strip().upper()
                mod = str(row.get(col_modelo_univ, '')).strip().upper()
                vehiculo = mod if mod.startswith(m) and m != "" else f"{m} {mod}".strip()
                if col_ano_univ:
                    ano = str(row.get(col_ano_univ, '')).strip()
                    if ano.endswith('.0'): ano = ano[:-2]
                    if ano not in ['', 'NAN', 'NONE']: vehiculo += f" | {ano}"
                return vehiculo
            
            df_busqueda['Vehiculo_Temp'] = df_busqueda.apply(armar_vehiculo_filtro, axis=1)
            df_busqueda['Filtro_Siniestro'] = df_busqueda[col_id_univ].astype(str).str.strip() + " | " + df_busqueda['Vehiculo_Temp']
        else: df_busqueda['Filtro_Siniestro'] = df_busqueda[col_id_univ] if col_id_univ else "S/N"
            
        filtro_col1, filtro_col2, filtro_col3, filtro_col4 = st.columns(4)
        with filtro_col1: taller_sel = st.multiselect("🏢 Taller:", sorted([str(t) for t in df_busqueda[col_taller_univ].dropna().unique() if str(t).strip() != '']) if col_taller_univ else [], placeholder="Todos...")
        with filtro_col2: estatus_sel = st.multiselect("📊 Estatus:", sorted([str(e) for e in df_busqueda[col_estatus_univ].dropna().unique() if str(e).strip() != '']) if col_estatus_univ else [], placeholder="Todos...")
        with filtro_col3:
            df_temp = df_busqueda.copy()
            if taller_sel: df_temp = df_temp[df_temp[col_taller_univ].astype(str).isin(taller_sel)]
            if estatus_sel: df_temp = df_temp[df_temp[col_estatus_univ].astype(str).isin(estatus_sel)]
            siniestro_sel = st.multiselect("🚗 Siniestro - Vehículo:", sorted(list(df_temp['Filtro_Siniestro'].dropna().unique())), placeholder="Todos...")
        with filtro_col4:
            df_temp_desc = df_temp.copy()
            if siniestro_sel: df_temp_desc = df_temp_desc[df_temp_desc['Filtro_Siniestro'].isin(siniestro_sel)]
            desc_sel = st.multiselect("⚙️ Refacción:", sorted(list(df_temp_desc[col_desc_univ].dropna().astype(str).unique())) if col_desc_univ else [], placeholder="Todas...")

        df_filtrado_global = df_busqueda.copy()
        filtros_activos = False
        
        if taller_sel: df_filtrado_global = df_filtrado_global[df_filtrado_global[col_taller_univ].astype(str).isin(taller_sel)]; filtros_activos = True
        if estatus_sel: df_filtrado_global = df_filtrado_global[df_filtrado_global[col_estatus_univ].astype(str).isin(estatus_sel)]; filtros_activos = True
        if siniestro_sel: df_filtrado_global = df_filtrado_global[df_filtrado_global['Filtro_Siniestro'].isin(siniestro_sel)]; filtros_activos = True
        if desc_sel: df_filtrado_global = df_filtrado_global[df_filtrado_global[col_desc_univ].astype(str).isin(desc_sel)]; filtros_activos = True

        st.markdown("---")
        
        if filtros_activos:
            st.markdown(f"**✅ {len(df_filtrado_global)} registro(s) encontrado(s)** con los filtros seleccionados.")
            col_aseg_exp = next((c for c in df_filtrado_global.columns if "ASEGURADORA" in str(c).upper()), None)
            col_vin_exp = next((c for c in df_filtrado_global.columns if "VIN" in str(c).upper() or "SERIE" in str(c).upper()), None)
            col_cant_exp = next((c for c in df_filtrado_global.columns if "CANT" in str(c).upper()), None)
            
            if not col_cant_exp: df_filtrado_global['Cant.'] = "1"; col_cant_exp = 'Cant.'

            col_precio_exp = next((c for c in df_filtrado_global.columns if "PRECIO" in str(c).upper() or "COSTO" in str(c).upper()), None)
            col_asig_exp = next((c for c in df_filtrado_global.columns if "ASIGNACI" in str(c).upper()), None)
            col_conf_exp = next((c for c in df_filtrado_global.columns if "FECHA CONFI" in str(c).upper()), None)
            col_venc_exp = next((c for c in df_filtrado_global.columns if "VENCIMIENTO" in str(c).upper() or "PROMESA" in str(c).upper()), None)
            col_guia_exp = next((c for c in df_filtrado_global.columns if "GUIA" in str(c).upper() or "GUÍA" in str(c).upper()), None)
            col_rem_exp = next((c for c in df_filtrado_global.columns if "REMISION" in str(c).upper() or "REMISIÓN" in str(c).upper()), None)
            col_obs_exp = next((c for c in df_filtrado_global.columns if "COMENTARIO" in str(c).upper() or "OBSERVACION" in str(c).upper()), None)
            col_origen_exp = next((c for c in df_filtrado_global.columns if "ORIGEN" in str(c).upper()), None)

            cols_a_mostrar = [c for c in [col_aseg_exp, col_id_univ, col_taller_univ, 'Vehiculo_Temp', col_vin_exp, col_cant_exp, col_desc_univ, col_origen_exp, col_precio_exp, col_estatus_univ, col_asig_exp, col_conf_exp, col_venc_exp, col_guia_exp, col_rem_exp, col_obs_exp] if c is not None and c in df_filtrado_global.columns]
            
            df_log = df_filtrado_global[cols_a_mostrar].copy()
            if 'Vehiculo_Temp' in df_log.columns: df_log.rename(columns={'Vehiculo_Temp': 'Vehículo'}, inplace=True)
            
            st.markdown("#### 🛠️ Expedientes y Remisiones")
            st.dataframe(df_log, hide_index=True, use_container_width=True)
            
            siniestros_filtrados = df_filtrado_global[col_id_univ].dropna().unique() if col_id_univ else []
            if len(siniestros_filtrados) > 0 and len(siniestros_filtrados) <= 10: 
                st.markdown("#### 💰 Histórico Financiero y Compras Relacionadas")
                if not df_compras.empty:
                    col_sin_comp = next((c for c in df_compras.columns if "SINIESTRO" in str(c).upper()), None)
                    if col_sin_comp:
                        df_comp_exp = df_compras[df_compras[col_sin_comp].astype(str).isin([str(s) for s in siniestros_filtrados])].copy()
                        if not df_comp_exp.empty:
                            cols_comp = ['Siniestro', 'Taller', 'Descripción Pieza', 'Proveedor', 'Costo Compra', 'Fecha Compra', 'Tiempo Entrega (Días)', 'Estatus Pago', 'Recibido']
                            df_comp_disp = df_comp_exp[[c for c in cols_comp if c in df_comp_exp.columns]].copy()
                            df_comp_disp.rename(columns={'Descripción Pieza': 'Pieza', 'Costo Compra': 'Costo', 'Tiempo Entrega (Días)': 'ETA (Días)'}, inplace=True)
                            st.dataframe(df_comp_disp, hide_index=True, use_container_width=True)
                        else: st.info("No existen registros de compras o pagos capturados para estos siniestros.")
                else: st.warning("La base de datos de compras no está disponible.")
        else: st.info("👆 Selecciona al menos un filtro en la parte superior para mostrar resultados.")
    else: st.warning("La base de datos está vacía.")

elif vista_actual == "🛠️ Cuartel General":
    st.markdown("### 🛠️ Cuartel General PMR (Solo Administración)")
    st.info("Bienvenido a la sala de máquinas. Desde aquí controlaremos respaldos, reimpresiones y rutas locales.")
    
    st.markdown("#### 🐛 Reporte de Bugs e Ideas (Checklist Activo):")
    try:
        doc = init_connection(); ws_notas = doc.worksheet("BD_NOTAS")
        datos_notas = ws_notas.get_all_values()
        if not datos_notas: ws_notas.append_row(["Fecha", "Nota", "Estatus"]); datos_notas = [["Fecha", "Nota", "Estatus"]]
        df_notas = pd.DataFrame(datos_notas[1:], columns=datos_notas[0])
        with st.form("form_nueva_nota", clear_on_submit=True):
            nueva_nota = st.text_input("Añadir nuevo pendiente, bug o idea:")
            if st.form_submit_button("➕ Agregar a la lista"):
                if nueva_nota.strip():
                    fecha_str = datetime.datetime.now().strftime("%d/%b/%y %H:%M")
                    ws_notas.append_row([fecha_str, nueva_nota.strip(), "PENDIENTE"], value_input_option='USER_ENTERED')
                    st.success("✅ Nota registrada en la base de datos."); time.sleep(1); st.rerun()

        st.markdown("**Tareas por resolver:**")
        if not df_notas.empty:
            df_notas['GS_Row'] = df_notas.index + 2
            df_pendientes = df_notas[df_notas['Estatus'].astype(str).str.upper() != 'COMPLETADO']
            if df_pendientes.empty: st.success("¡Todo al día! No hay tareas pendientes en el radar.")
            else:
                for _, row in df_pendientes.iterrows():
                    marcado = st.checkbox(f"{row['Nota']} *(Reportado: {row['Fecha']})*", key=f"nota_{row['GS_Row']}")
                    if marcado:
                        ws_notas.update_cell(row['GS_Row'], 3, "COMPLETADO")
                        st.toast(f"Tarea completada: {row['Nota']}", icon="✅"); time.sleep(0.5); st.rerun()
        else: st.success("¡Todo al día! No hay tareas pendientes en el radar.")
    except gspread.exceptions.WorksheetNotFound: st.error("⚠️ Error de conexión: Para usar esta función, debes crear una nueva pestaña llamada **BD_NOTAS** en tu Google Sheets.")
    except Exception as e: st.error(f"⚠️ Ha ocurrido un error al cargar las notas: {e}")

# ==============================================================================
# === [BLOQUE 10: MOTOR DE GUARDADO Y SINCRONIZACIÓN] ===
# ==============================================================================
trigger_rem = st.session_state.pop('trigger_remision_manual', None)

if (btn_guardar or trigger_rem) and permiso_edicion:
    st.session_state['pdfs_list'] = []
    st.session_state['avisos_remision'] = []
    
    def generar_llave(id_val, desc_val):
        id_str = str(id_val).strip().upper()
        if id_str.endswith('.0'): id_str = id_str[:-2]
        desc_str = ' '.join(str(desc_val).strip().upper().split())
        return (id_str if id_str not in ['NAN', 'NONE'] else '', desc_str if desc_str not in ['NAN', 'NONE'] else '')

    def buscar_columna(df_o_lista, exactos, parciales, excluidos=["ENV", "PAGO"]):
        cols = df_o_lista.columns if hasattr(df_o_lista, 'columns') else df_o_lista
        cols_up = [str(c).strip().upper() for c in cols]
        for ex in exactos:
            if ex in cols_up: return cols[cols_up.index(ex)]
        for i, c_up in enumerate(cols_up):
            for p in parciales:
                if p in c_up and not any(exc in c_up for exc in excluidos): return cols[i]
        return None

    col_id_univ = buscar_columna(df_completo, ["PEDIDO / SINIESTRO", "SINIESTRO"], ["SINIESTRO"])
    col_desc_univ = buscar_columna(df_completo, ["DESCRIPCIÓN", "DESCRIPCION"], ["DESCRIPCI", "REFACCI"])
    col_estatus_univ = buscar_columna(df_completo, ["ESTATUS", "STATUS"], ["ESTATUS", "STATUS"])
    col_taller_univ = buscar_columna(df_completo, ["TALLER", "CDR"], ["TALLER"])
    col_marca_univ = buscar_columna(df_completo, ["MARCA"], ["MARCA"])
    col_modelo_univ = buscar_columna(df_completo, ["MODELO"], ["MODELO"])
    col_cant_univ = buscar_columna(df_completo, ["CANTIDAD", "CANT"], ["CANTIDAD", "CANT"])
    col_paqueteria_univ = buscar_columna(df_completo, ["PAQUETERIA", "PAQUETERÍA"], ["PAQUETER"])
    col_guia_univ = buscar_columna(df_completo, ["GUIA", "GUÍA", "NO. GUIA"], ["GUIA", "GUÍA"])
    col_rem_univ = buscar_columna(df_completo, ["REMISION", "REMISIÓN", "FOLIO REMISION"], ["REMISION", "REMISIÓN"])
    col_coment_univ = buscar_columna(df_completo, ["COMENTARIOS", "OBSERVACIONES", "COMENTARIO", "OBSERVACION"], ["COMENTARIO", "OBSERVACION"])
    col_venc_univ = buscar_columna(df_completo, ["VENCIMIENTO", "FECHA VENCIMIENTO", "PROMESA"], ["VENCIMIENTO", "PROMESA"])
    col_asig_univ = buscar_columna(df_completo, ["ASIGNACION", "FECHA ASIGNACION"], ["ASIGNACI"])
    
    originales = {}
    for _, r in df_completo.iterrows():
        k = generar_llave(r.get(col_id_univ, ''), r.get(col_desc_univ, ''))
        raw_venc = str(r.get(col_venc_univ, '')).strip() if col_venc_univ else ""
        venc_formateada = estandarizar_fechas_mx(raw_venc) if raw_venc else ""

        originales[k] = {
            'comentario': str(r.get(col_coment_univ, '')).strip() if col_coment_univ else '',
            'paqueteria': str(r.get(col_paqueteria_univ, '')).strip() if col_paqueteria_univ else '',
            'guia': str(r.get(col_guia_univ, '')).strip() if col_guia_univ else '',
            'estatus_db': str(r.get(col_estatus_univ, '')).strip().upper() if col_estatus_univ else '',
            'remision_bool': str(r.get(col_rem_univ, '')).strip() != '' if col_rem_univ else False,
            'vencimiento_db': venc_formateada,
            'asignacion_db': str(r.get(col_asig_univ, '')).strip() if col_asig_univ else ''
        }
        
    cambios_a_guardar = {}
    cambios_bd_compras = {}
    tz_mx = datetime.timezone(datetime.timedelta(hours=-6))
    fecha_hoy_sistema = datetime.datetime.now(tz_mx).strftime('%d/%b/%y')

    if trigger_rem:
        for desc in trigger_rem['descripciones']:
            k = generar_llave(trigger_rem['siniestro'], desc)
            orig = originales.get(k, {'remision_bool': False})
            cambios_a_guardar.setdefault(k, {}).update({'estatus': 'EN TRANSITO', 'imprimir_remision': True, 'usuario_rem': st.session_state.get('usuario_actual', 'Sistema'), 'fecha_envio': fecha_hoy_sistema})
            if not orig['remision_bool']: cambios_a_guardar[k]['generar_nuevo_folio'] = True
            cambios_bd_compras.setdefault(k, {})['recibido'] = 'SI'

    if btn_guardar:
        if not df_editado_conf.empty:
            for _, row in df_editado_conf.iterrows():
                k = generar_llave(row.get(col_id, ''), row.get(col_desc, ''))
                orig = originales.get(k, {'comentario': '', 'estatus_db': ''})
                
                nuevo_estatus = None
                if row.get('Pérdida Total'): nuevo_estatus = "PÉRDIDA TOTAL"
                elif row.get('Cancelar'): nuevo_estatus = "CANCELADO"
                elif row.get('Confirmar Surtido'): nuevo_estatus = "EN PROCESAMIENTO"
                
                comentario_actual = str(row.get(col_comentarios, '')).strip()
                if nuevo_estatus and nuevo_estatus != orig['estatus_db']: 
                    cambios_a_guardar.setdefault(k, {})['estatus'] = nuevo_estatus
                    if nuevo_estatus == "EN PROCESAMIENTO": cambios_a_guardar[k]['fecha_confi'] = fecha_hoy_sistema
                if comentario_actual != orig['comentario']: cambios_a_guardar.setdefault(k, {})['comentario'] = comentario_actual

        for df_venc in [df_editado_venc, df_editado_atrasadas]:
            if not df_venc.empty:
                for _, row in df_venc.iterrows():
                    k = generar_llave(row.get(col_id, ''), row.get(col_desc, ''))
                    orig = originales.get(k, {'comentario': '', 'paqueteria': '', 'guia': '', 'estatus_db': ''})
                    
                    nuevo_estatus = "CANCELADO" if row.get('Cancelar') else None
                    comentario_actual = str(row.get(col_comentarios, '')).strip()
                    paq_actual = str(row.get(col_paqueteria, '')).strip()
                    guia_actual = str(row.get(col_guia, '')).strip()
                    nueva_fecha = row.get('Nueva Fecha')
                    
                    if pd.notnull(nueva_fecha) and str(nueva_fecha).strip() not in ['', 'NaT', 'None']:
                        try: fecha_str = pd.to_datetime(nueva_fecha).strftime('%d/%b/%y')
                        except: fecha_str = str(nueva_fecha)
                        cambios_a_guardar.setdefault(k, {})['vencimiento'] = fecha_str
                        if not nuevo_estatus: nuevo_estatus = "EN PROCESAMIENTO"
                    
                    if nuevo_estatus and nuevo_estatus != orig['estatus_db']: cambios_a_guardar.setdefault(k, {})['estatus'] = nuevo_estatus
                    if comentario_actual != orig['comentario']: cambios_a_guardar.setdefault(k, {})['comentario'] = comentario_actual
                    if paq_actual != orig['paqueteria']: cambios_a_guardar.setdefault(k, {})['paqueteria'] = paq_actual
                    if guia_actual != orig['guia']: cambios_a_guardar.setdefault(k, {})['guia'] = guia_actual

        if 'df_editado_rec' in locals() and not df_editado_rec.empty:
            for _, row in df_editado_rec.iterrows():
                k = generar_llave(row.get(col_id, ''), row.get(col_desc, ''))
                orig = originales.get(k, {'comentario': '', 'paqueteria': '', 'guia': ''})
                
                comentario_actual = str(row.get(col_comentarios, '')).strip()
                paq_actual = str(row.get(col_paqueteria, '')).strip()
                guia_actual = str(row.get(col_guia, '')).strip()
                
                if comentario_actual != orig['comentario']: cambios_a_guardar.setdefault(k, {})['comentario'] = comentario_actual
                if paq_actual != orig['paqueteria']: cambios_a_guardar.setdefault(k, {})['paqueteria'] = paq_actual
                if guia_actual != orig['guia']: cambios_a_guardar.setdefault(k, {})['guia'] = guia_actual

        if not df_editado_cobro.empty:
            for _, row in df_editado_cobro.iterrows():
                k = generar_llave(row.get(col_id, ''), row.get(col_desc, ''))
                orig = originales.get(k, {'comentario': '', 'estatus_db': ''})
                if row.get('Marcar Recibido') and cambios_a_guardar.get(k, {}).get('estatus') != "CANCELADO": 
                    cambios_a_guardar.setdefault(k, {})['estatus'] = "RECIBIDO"
                    cambios_a_guardar[k]['fecha_recibido'] = fecha_hoy_sistema
                comentario_actual = str(row.get(col_comentarios, '')).strip()
                if comentario_actual != orig['comentario']: cambios_a_guardar.setdefault(k, {})['comentario'] = comentario_actual

        if not df_editado_fact.empty:
            for _, row in df_editado_fact.iterrows():
                k = generar_llave(row.get(col_id, ''), row.get(col_desc, ''))
                if row.get('Facturado') and cambios_a_guardar.get(k, {}).get('estatus') != "CANCELADO": 
                    cambios_a_guardar.setdefault(k, {})['estatus'] = "FACTURADO"
                    cambios_a_guardar[k]['fecha_facturacion'] = fecha_hoy_sistema

        if not df_editado_reemb.empty:
            for _, row in df_editado_reemb.iterrows():
                k = generar_llave(row.get(col_id, ''), row.get(col_desc, ''))
                orig = originales.get(k, {'comentario': '', 'estatus_db': ''})
                if row.get('Marcar Reembolsado'): 
                    cambios_a_guardar.setdefault(k, {})['estatus'] = "REEMBOLSADO"
                comentario_actual = str(row.get(col_comentarios, '')).strip()
                if comentario_actual != orig['comentario']: cambios_a_guardar.setdefault(k, {})['comentario'] = comentario_actual

        if not df_editado.empty:
            for _, row in df_editado.iterrows():
                k = generar_llave(row.get(col_id, ''), row.get(col_desc, ''))
                orig = originales.get(k, {'comentario': '', 'paqueteria': '', 'guia': '', 'estatus_db': '', 'remision_bool': False, 'vencimiento_db': '', 'asignacion_db': ''})
                
                if row.get('Cancelar') and 'estatus' not in cambios_a_guardar.get(k, {}): 
                    cambios_a_guardar.setdefault(k, {})['estatus'] = "CANCELADO"
                elif row.get('Recibido') and 'estatus' not in cambios_a_guardar.get(k, {}): 
                    cambios_a_guardar.setdefault(k, {})['estatus'] = "RECIBIDO"
                    cambios_a_guardar[k]['fecha_recibido'] = fecha_hoy_sistema
                elif row.get('Entregado') and 'estatus' not in cambios_a_guardar.get(k, {}): 
                    cambios_a_guardar.setdefault(k, {})['estatus'] = "ENTREGADO"
                
                comentario_actual = str(row.get(col_comentarios, '')).strip()
                paq_actual = str(row.get(col_paqueteria, '')).strip()
                guia_actual = str(row.get(col_guia, '')).strip()
                venc_actual = str(row.get(col_vencimiento, '')).strip()
                asig_actual = str(row.get(col_asignacion, '')).strip()
                
                if comentario_actual != orig['comentario']: cambios_a_guardar.setdefault(k, {})['comentario'] = comentario_actual
                if paq_actual != orig['paqueteria']: cambios_a_guardar.setdefault(k, {})['paqueteria'] = paq_actual
                if guia_actual != orig['guia']: cambios_a_guardar.setdefault(k, {})['guia'] = guia_actual
                if venc_actual and venc_actual != orig['vencimiento_db'] and 'vencimiento' not in cambios_a_guardar.get(k, {}): cambios_a_guardar.setdefault(k, {})['vencimiento'] = venc_actual
                if asig_actual and asig_actual != orig['asignacion_db']: cambios_a_guardar.setdefault(k, {})['asignacion'] = asig_actual
                
                prov_asignado = str(row.get('Proveedor', '')).strip()
                if prov_asignado != '' and cambios_a_guardar.get(k, {}).get('estatus', orig['estatus_db']) != "CANCELADO":
                    cambios_a_guardar.setdefault(k, {})['crear_compra'] = True
                    cambios_a_guardar[k]['compra_prov'] = prov_asignado
                    cambios_a_guardar[k]['compra_costo'] = str(row.get('Costo Compra', '0')).strip()
                    cambios_a_guardar[k]['compra_taller'] = str(row.get(col_taller, '')).strip()
                    cambios_a_guardar[k]['compra_vehiculo'] = str(row.get('Vehiculo_Info', '')).strip()

        if vista_actual == "🛒 Compras":
            df_editado_compras = st.session_state.get('df_editado_compras_temp', pd.DataFrame())
            if not df_editado_compras.empty:
                for _, row in df_editado_compras.iterrows():
                    k = generar_llave(row.get('Siniestro', ''), row.get('Descripción Pieza', ''))
                    cambios_bd_compras.setdefault(k, {})
                    if row.get('Cancelar Compra'):
                        cambios_bd_compras[k]['cancelar_compra'] = True
                        cambios_a_guardar.setdefault(k, {})['estatus'] = "POR CONFIRMAR"
                    else:
                        cambios_bd_compras[k]['costo'] = str(row.get('Costo Compra', '')).replace('$', '').strip()
                        cambios_bd_compras[k]['tiempo'] = row.get('Tiempo Entrega (Días)', '')
                        cambios_bd_compras[k]['cond_pago'] = row.get('Condición Pago', '')
                        cambios_bd_compras[k]['dias_credito'] = row.get('Días Crédito', '')
                        cambios_bd_compras[k]['estatus_pago'] = row.get('Estatus Pago', '')
                        cambios_bd_compras[k]['prov'] = row.get('Proveedor', '')
                        cambios_bd_compras[k]['recibido'] = 'SI' if row.get('Recibido') else 'NO'
                        if row.get('Recibido'): cambios_a_guardar.setdefault(k, {})['estatus'] = "EN PROCESAMIENTO" 

    if cambios_a_guardar or cambios_bd_compras:
        with espacio_spinner:
            with st.spinner("Sincronizando con BD_UNIFICADA y BD_HISTORICO..."):
                try:
                    doc = init_connection()
                    
                    if cambios_a_guardar:
                        ws_uni = doc.worksheet("BD_UNIFICADA")
                        datos_uni = ws_uni.get_all_values()
                        headers_uni = [str(h).strip() for h in datos_uni[0]]
                        
                        try:
                            ws_hist = doc.worksheet("BD_HISTORICO")
                            datos_hist = ws_hist.get_all_values()
                            headers_hist = [str(h).strip() for h in datos_hist[0]] if datos_hist else []
                        except:
                            datos_hist = []; headers_hist = []

                        def mapear_columnas(headers):
                            if not headers: return {}
                            return {
                                'id': headers.index(buscar_columna(headers, ["PEDIDO / SINIESTRO", "SINIESTRO"], ["SINIESTRO"])) if buscar_columna(headers, ["PEDIDO / SINIESTRO", "SINIESTRO"], ["SINIESTRO"]) else -1,
                                'desc': headers.index(buscar_columna(headers, ["DESCRIPCIÓN", "DESCRIPCION"], ["DESCRIPCI", "REFACCI"])) if buscar_columna(headers, ["DESCRIPCIÓN", "DESCRIPCION"], ["DESCRIPCI", "REFACCI"]) else -1,
                                'estatus': headers.index(buscar_columna(headers, ["ESTATUS", "STATUS"], ["ESTATUS", "STATUS"])) if buscar_columna(headers, ["ESTATUS", "STATUS"], ["ESTATUS", "STATUS"]) else -1,
                                'rem': headers.index(buscar_columna(headers, ["REMISION", "REMISIÓN", "FOLIO REMISION"], ["REMISION", "REMISIÓN"])) if buscar_columna(headers, ["REMISION", "REMISIÓN", "FOLIO REMISION"], ["REMISION", "REMISIÓN"]) else -1,
                                'usr_rem': headers.index(buscar_columna(headers, ["USUARIO REMISION", "USUARIO REMISIÓN"], ["USUARIO REM"])) if buscar_columna(headers, ["USUARIO REMISION", "USUARIO REMISIÓN"], ["USUARIO REM"]) else -1,
                                'coment': headers.index(buscar_columna(headers, ["COMENTARIOS", "COMENTARIO", "OBSERVACION"], ["COMENTARIO", "OBSERVACION"])) if buscar_columna(headers, ["COMENTARIOS", "COMENTARIO", "OBSERVACION"], ["COMENTARIO", "OBSERVACION"]) else -1,
                                'paq': headers.index(buscar_columna(headers, ["PAQUETERIA", "PAQUETERÍA"], ["PAQUETER"])) if buscar_columna(headers, ["PAQUETERIA", "PAQUETERÍA"], ["PAQUETER"]) else -1,
                                'guia': headers.index(buscar_columna(headers, ["GUIA", "GUÍA", "NO. GUIA"], ["GUIA", "GUÍA"])) if buscar_columna(headers, ["GUIA", "GUÍA", "NO. GUIA"], ["GUIA", "GUÍA"]) else -1,
                                'venc': headers.index(buscar_columna(headers, ["VENCIMIENTO", "FECHA VENCIMIENTO", "PROMESA"], ["VENCIMIENTO", "PROMESA"])) if buscar_columna(headers, ["VENCIMIENTO", "FECHA VENCIMIENTO", "PROMESA"], ["VENCIMIENTO", "PROMESA"]) else -1,
                                'asig': headers.index(buscar_columna(headers, ["ASIGNACION", "FECHA ASIGNACION"], ["ASIGNACI"])) if buscar_columna(headers, ["ASIGNACION", "FECHA ASIGNACION"], ["ASIGNACI"]) else -1,
                                'confi': headers.index(buscar_columna(headers, ["CONFIRMACION", "FECHA CONFIRMACION"], ["FECHA CONFI"])) if buscar_columna(headers, ["CONFIRMACION", "FECHA CONFIRMACION"], ["FECHA CONFI"]) else -1,
                                'envio': headers.index(buscar_columna(headers, ["FECHA ENVIO", "FECHA ENVÍO"], ["FECHA ENV"])) if buscar_columna(headers, ["FECHA ENVIO", "FECHA ENVÍO"], ["FECHA ENV"]) else -1,
                                'recibido': headers.index(buscar_columna(headers, ["FECHA RECIBIDO"], ["FECHA REC"])) if buscar_columna(headers, ["FECHA RECIBIDO"], ["FECHA REC"]) else -1,
                                'fact': headers.index(buscar_columna(headers, ["FECHA FACTURACION", "FECHA FACTURACIÓN"], ["FECHA FAC"])) if buscar_columna(headers, ["FECHA FACTURACION", "FECHA FACTURACIÓN"], ["FECHA FAC"]) else -1
                            }

                        mapa_uni = mapear_columnas(headers_uni)
                        mapa_hist = mapear_columnas(headers_hist)

                        max_folio_pmr = 0
                        numeros = df_completo[col_rem_univ].astype(str).str.extract(r'(?i)PMR\s*-\s*0*(\d+)', expand=False) if col_rem_univ else pd.Series()
                        if not numeros.empty: max_folio_pmr = int(pd.to_numeric(numeros, errors='coerce').max() if pd.notna(pd.to_numeric(numeros, errors='coerce').max()) else 0)

                        folios_asignados_en_sesion = {}
                        for k, v in cambios_a_guardar.items():
                            if v.get('generar_nuevo_folio'):
                                siniestro_id = k[0] 
                                if siniestro_id not in folios_asignados_en_sesion:
                                    max_folio_pmr += 1
                                    folios_asignados_en_sesion[siniestro_id] = f"PMR - {max_folio_pmr:03d}"
                                v['remision_num'] = folios_asignados_en_sesion[siniestro_id]

                        def actualizar_datos_hoja(datos_hoja, mapa_hoja):
                            if not datos_hoja or not mapa_hoja or mapa_hoja['id'] == -1 or mapa_hoja['desc'] == -1: return False
                            cambio_realizado = False
                            for i in range(1, len(datos_hoja)):
                                k = generar_llave(datos_hoja[i][mapa_hoja['id']], datos_hoja[i][mapa_hoja['desc']])
                                if k in cambios_a_guardar:
                                    c = cambios_a_guardar[k]
                                    cambio_realizado = True
                                    if 'estatus' in c and mapa_hoja['estatus'] >= 0: datos_hoja[i][mapa_hoja['estatus']] = c['estatus']
                                    if 'remision_num' in c and mapa_hoja['rem'] >= 0: datos_hoja[i][mapa_hoja['rem']] = c['remision_num']
                                    if 'usuario_rem' in c and mapa_hoja['usr_rem'] >= 0: datos_hoja[i][mapa_hoja['usr_rem']] = c['usuario_rem']
                                    if 'comentario' in c and mapa_hoja['coment'] >= 0: datos_hoja[i][mapa_hoja['coment']] = c['comentario']
                                    if 'paqueteria' in c and mapa_hoja['paq'] >= 0: datos_hoja[i][mapa_hoja['paq']] = c['paqueteria']
                                    if 'guia' in c and mapa_hoja['guia'] >= 0: datos_hoja[i][mapa_hoja['guia']] = c['guia']
                                    if 'vencimiento' in c and mapa_hoja['venc'] >= 0: datos_hoja[i][mapa_hoja['venc']] = c['vencimiento']
                                    if 'asignacion' in c and mapa_hoja['asig'] >= 0: datos_hoja[i][mapa_hoja['asig']] = c['asignacion']
                                    if 'fecha_confi' in c and mapa_hoja['confi'] >= 0: datos_hoja[i][mapa_hoja['confi']] = c['fecha_confi']
                                    if 'fecha_envio' in c and mapa_hoja['envio'] >= 0: datos_hoja[i][mapa_hoja['envio']] = c['fecha_envio']
                                    if 'fecha_recibido' in c and mapa_hoja['recibido'] >= 0: datos_hoja[i][mapa_hoja['recibido']] = c['fecha_recibido']
                                    if 'fecha_facturacion' in c and mapa_hoja['fact'] >= 0: datos_hoja[i][mapa_hoja['fact']] = c['fecha_facturacion']
                            return cambio_realizado

                        hay_cambios_uni = actualizar_datos_hoja(datos_uni, mapa_uni)
                        hay_cambios_hist = actualizar_datos_hoja(datos_hist, mapa_hist)

                        if hay_cambios_uni: ws_uni.update(range_name='A1', values=datos_uni, value_input_option='USER_ENTERED')
                        if hay_cambios_hist and datos_hist: ws_hist.update(range_name='A1', values=datos_hist, value_input_option='USER_ENTERED')

                    if any(v.get('crear_compra') for v in cambios_a_guardar.values()) or cambios_bd_compras:
                        try:
                            ws_comp = doc.worksheet("BD_COMPRAS")
                            datos_comp_crudos = ws_comp.get_all_values()
                            if not datos_comp_crudos:
                                headers_comp = ['Siniestro', 'Taller', 'Vehículo', 'Descripción Pieza', 'Proveedor', 'Costo Compra', 'Fecha Compra', 'Tiempo Entrega (Días)', 'Recibido', 'Condición Pago', 'Días Crédito', 'Estatus Pago']
                                datos_comp = [headers_comp]
                            else:
                                headers_comp = [str(h).strip() for h in datos_comp_crudos[0]]
                                datos_comp = [headers_comp]
                                for fila in datos_comp_crudos[1:]:
                                    if any(str(celda).strip() for celda in fila): datos_comp.append(fila)
                                
                            def get_col_idx(name):
                                if name in headers_comp: return headers_comp.index(name)
                                headers_comp.append(name); datos_comp[0] = headers_comp
                                for r in datos_comp[1:]: r.append("")
                                return len(headers_comp) - 1
                                
                            idx_c_sin = get_col_idx('Siniestro'); idx_c_desc = get_col_idx('Descripción Pieza'); i_tall = get_col_idx('Taller'); i_veh = get_col_idx('Vehículo')
                            i_prov = get_col_idx('Proveedor'); i_costo = get_col_idx('Costo Compra'); i_fcomp = get_col_idx('Fecha Compra'); i_tiempo = get_col_idx('Tiempo Entrega (Días)')
                            i_rec = get_col_idx('Recibido'); i_cond_pago = get_col_idx('Condición Pago'); i_dias_cred = get_col_idx('Días Crédito'); i_est_pago = get_col_idx('Estatus Pago')
                            
                            llaves_en_compras = set()
                            nuevos_datos_comp = [headers_comp]
                            for i in range(1, len(datos_comp)):
                                while len(datos_comp[i]) < len(headers_comp): datos_comp[i].append("")
                                k_c = generar_llave(datos_comp[i][idx_c_sin], datos_comp[i][idx_c_desc])
                                llaves_en_compras.add(k_c)
                                eliminar_fila = False
                                
                                if k_c in cambios_bd_compras:
                                    cb = cambios_bd_compras[k_c]
                                    if cb.get('cancelar_compra'): eliminar_fila = True
                                    else:
                                        if str(cb.get('costo','')).strip(): datos_comp[i][i_costo] = cb['costo']
                                        if str(cb.get('tiempo','')).strip(): datos_comp[i][i_tiempo] = cb['tiempo']
                                        if 'cond_pago' in cb and str(cb['cond_pago']).strip() != 'nan': datos_comp[i][i_cond_pago] = cb['cond_pago']
                                        if 'dias_credito' in cb and str(cb['dias_credito']).strip() != 'nan': datos_comp[i][i_dias_cred] = cb['dias_credito']
                                        if 'estatus_pago' in cb and str(cb['estatus_pago']).strip() != 'nan': datos_comp[i][i_est_pago] = cb['estatus_pago']
                                        if 'prov' in cb and str(cb['prov']).strip() and str(cb['prov']).strip() != 'nan': datos_comp[i][i_prov] = cb['prov']
                                        if 'recibido' in cb: datos_comp[i][i_rec] = cb['recibido']
                                
                                if k_c in cambios_a_guardar and cambios_a_guardar[k_c].get('crear_compra'):
                                    v_po = cambios_a_guardar[k_c]
                                    po_prov = str(v_po.get('compra_prov', '')).strip()
                                    po_costo = str(v_po.get('compra_costo', '')).strip()
                                    
                                    if po_prov and po_prov not in ['None', 'nan', '']:
                                        datos_comp[i][i_prov] = po_prov
                                        if not df_proveedores.empty:
                                            for _, row_p in df_proveedores.iterrows():
                                                p_val = str(row_p.get('Proveedor', '')).strip().upper(); s_val = str(row_p.get('Sucursal', '')).strip().upper()
                                                llave_p = f"{p_val} - {s_val}" if s_val else p_val
                                                if llave_p == po_prov:
                                                    t_str = str(row_p.get('Tiempo de Entrega', '')).upper()
                                                    nums = re.findall(r'\d+', t_str)
                                                    if nums: datos_comp[i][i_tiempo] = nums[-1]
                                                    cond_p = str(row_p.get('Condición Pago', '')).strip().title()
                                                    if cond_p: datos_comp[i][i_cond_pago] = cond_p
                                                    dias_c = str(row_p.get('Días Crédito', '0')).strip()
                                                    if dias_c: datos_comp[i][i_dias_cred] = dias_c
                                                    break
                                    if po_costo and po_costo not in ['0', '0.0', 'None', 'nan', '']:
                                        datos_comp[i][i_costo] = po_costo

                                if not eliminar_fila: nuevos_datos_comp.append(datos_comp[i])
                                        
                            fecha_hoy_comp = datetime.datetime.now(tz_mx).strftime('%d/%b/%y')
                            nuevas_filas = []
                            for k, v in cambios_a_guardar.items():
                                if v.get('crear_compra') and k not in llaves_en_compras:
                                    n_row = [""] * len(headers_comp)
                                    n_row[idx_c_sin] = k[0]; n_row[idx_c_desc] = k[1]; n_row[i_tall] = v.get('compra_taller', ''); n_row[i_veh] = v.get('compra_vehiculo', '')
                                    n_row[i_fcomp] = fecha_hoy_comp; n_row[i_rec] = 'NO'; n_row[i_costo] = v.get('compra_costo', '0')
                                    
                                    nombre_prov_completo = str(v.get('compra_prov', '')).strip()
                                    eta_calc = "0"; cond_pago_calc = ""; dias_cred_calc = "0"
                                    if nombre_prov_completo and not df_proveedores.empty:
                                        for _, row_p in df_proveedores.iterrows():
                                            p_val = str(row_p.get('Proveedor', '')).strip().upper(); s_val = str(row_p.get('Sucursal', '')).strip().upper()
                                            llave_p = f"{p_val} - {s_val}" if s_val else p_val
                                            if llave_p == nombre_prov_completo:
                                                tiempo_str = str(row_p.get('Tiempo de Entrega', '')).upper()
                                                numeros = re.findall(r'\d+', tiempo_str)
                                                if numeros: eta_calc = numeros[-1]
                                                cond_pago_calc = str(row_p.get('Condición Pago', '')).strip().title()
                                                dias_cred_calc = str(row_p.get('Días Crédito', '0')).strip()
                                                break
                                    n_row[i_prov] = nombre_prov_completo; n_row[i_tiempo] = eta_calc if eta_calc else '0'
                                    n_row[i_cond_pago] = cond_pago_calc; n_row[i_dias_cred] = dias_cred_calc
                                    nuevas_filas.append(n_row)
                            
                            filas_a_escribir = nuevos_datos_comp + nuevas_filas
                            while len(filas_a_escribir) < len(datos_comp_crudos): filas_a_escribir.append([""] * len(headers_comp))
                            ws_comp.update(range_name='A1', values=filas_a_escribir, value_input_option='USER_ENTERED')
                        except Exception as e_comp: st.warning(f"Nota: Hubo un problema sincronizando BD_COMPRAS: {e_comp}")

                    llaves_a_imprimir = [k for k, v in cambios_a_guardar.items() if v.get('imprimir_remision') == True]
                    if llaves_a_imprimir:
                        marcados_remision = df_completo[df_completo.apply(lambda r: generar_llave(r.get(col_id_univ, ''), r.get(col_desc_univ, '')) in llaves_a_imprimir, axis=1)]
                        cols_agrup_univ = [col_id_univ, col_taller_univ, col_marca_univ, col_modelo_univ]
                        agrupadores = [c for c in cols_agrup_univ if c in marcados_remision.columns]
                        
                        avisos_unicos = set()
                        pdfs_list = []
                        usuario_print = st.session_state.get('usuario_actual', 'Sistema')
                        
                        for keys, df_g in marcados_remision.groupby(agrupadores):
                            siniestro_v = keys[agrupadores.index(col_id_univ)] if col_id_univ in agrupadores else ""
                            taller_v = keys[agrupadores.index(col_taller_univ)] if col_taller_univ in agrupadores else ""
                            marca_v = keys[agrupadores.index(col_marca_univ)] if col_marca_univ in agrupadores else ""
                            modelo_v = keys[agrupadores.index(col_modelo_univ)] if col_modelo_univ in agrupadores else ""
                            
                            folio_str_print = "S/N"
                            for _, row_rem in df_g.iterrows():
                                key_rem = generar_llave(row_rem.get(col_id_univ, ''), row_rem.get(col_desc_univ, ''))
                                if key_rem in cambios_a_guardar and 'remision_num' in cambios_a_guardar[key_rem]:
                                    folio_str_print = cambios_a_guardar[key_rem]['remision_num']; break
                            
                            fecha_actual = datetime.datetime.now(tz_mx)
                            fecha_header = fecha_actual.strftime('%d/%b/%Y').upper()
                            firma_digital = f"Generado por: {usuario_print}"
                            
                            dir_v = ""
                            col_cat_taller = next((c for c in df_catalogo.columns if "TALLER" in str(c).upper()), None)
                            if not df_catalogo.empty and col_cat_taller:
                                match_taller = df_catalogo[df_catalogo[col_cat_taller].astype(str).str.strip().str.upper() == str(taller_v).strip().upper()]
                                if not match_taller.empty:
                                    col_dir = next((c for c in df_catalogo.columns if "DIRECCI" in str(c).upper()), None)
                                    if col_dir: dir_v = str(match_taller.iloc[0].get(col_dir, '')).strip()
                                else: avisos_unicos.add(f"⚠️ AVISO: El CDR '{taller_v}' no está registrado.")
                            else: avisos_unicos.add(f"⚠️ AVISO: El CDR '{taller_v}' no está registrado.")

                            def limpiar_texto(txt): return str(txt).encode('latin-1', 'replace').decode('latin-1')

                            pdf = FPDF(orientation='L', unit='mm', format='A4')
                            pdf.set_auto_page_break(auto=False, margin=0); pdf.add_page()
                            
                            def dibujar_bloque_remision(x_offset):
                                import os
                                y_offset = 15
                                if os.path.exists("logo.png"):
                                    try: pdf.image("logo.png", x_offset, y_offset - 3, 30)
                                    except: pass
                                
                                pdf.set_font("Arial", 'B', 10); pdf.set_text_color(0, 51, 102); pdf.set_xy(x_offset + 32, y_offset)
                                pdf.cell(70, 5, limpiar_texto("PREMIER SERVICIOS Y REFACCIONES"))
                                pdf.set_font("Arial", 'B', 8); pdf.set_xy(x_offset + 32, y_offset + 5); pdf.cell(70, 4, limpiar_texto("PMR SERVICIOS AUTOMOTRIZ"))
                                pdf.set_font("Arial", '', 7); pdf.set_text_color(100, 100, 100); pdf.set_xy(x_offset + 32, y_offset + 9); pdf.cell(70, 3, limpiar_texto("ALLENDE 228, AÑO DE JUAREZ"))
                                pdf.set_xy(x_offset + 32, y_offset + 12); pdf.cell(70, 3, limpiar_texto("SAN NICOLAS DE LOS GARZA, N.L. | PSA 211015 B30"))

                                pdf.set_text_color(0, 0, 0); pdf.set_xy(x_offset + 105, y_offset); pdf.set_font("Arial", 'B', 9); pdf.cell(30, 5, "REMISION", border=1, align='C')
                                pdf.set_text_color(200, 0, 0); pdf.set_font("Arial", 'B', 10); pdf.set_xy(x_offset + 105, y_offset + 5); pdf.cell(30, 6, folio_str_print, border=1, align='C')
                                pdf.set_text_color(100, 100, 100); pdf.set_font("Arial", '', 7); pdf.set_xy(x_offset + 105, y_offset + 12); pdf.cell(30, 4, f"FECHA: {fecha_header}", align='C')
                                
                                y_datos = y_offset + 22; pdf.set_fill_color(220, 220, 220); pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", 'B', 7)
                                pdf.set_xy(x_offset, y_datos); pdf.cell(20, 5, "TALLER", border=1, fill=True); pdf.set_font("Arial", '', 7); pdf.cell(115, 5, limpiar_texto(f" {taller_v}")[:75], border=1)
                                y_datos += 5; pdf.set_xy(x_offset, y_datos); pdf.set_font("Arial", 'B', 7); pdf.cell(20, 5, "DIRECCION", border=1, fill=True); pdf.set_font("Arial", '', 7); pdf.cell(115, 5, limpiar_texto(f" {dir_v}")[:85], border=1)
                                y_datos += 5; pdf.set_xy(x_offset, y_datos); pdf.set_font("Arial", 'B', 7); pdf.cell(20, 5, "SINIESTRO", border=1, fill=True); pdf.set_font("Arial", 'B', 8); pdf.cell(45, 5, limpiar_texto(f" {siniestro_v}"), border=1)
                                pdf.set_font("Arial", 'B', 7); pdf.cell(20, 5, "VEHICULO", border=1, fill=True); pdf.set_font("Arial", '', 7); pdf.cell(50, 5, limpiar_texto(f" {marca_v} {modelo_v}")[:35], border=1)

                                y_tabla = y_datos + 10; pdf.set_xy(x_offset, y_tabla); pdf.set_fill_color(0, 0, 0); pdf.set_text_color(255, 255, 255); pdf.set_font("Arial", 'B', 7)
                                pdf.cell(15, 6, "CANT", border=1, fill=True, align='C'); pdf.cell(120, 6, "DESCRIPCION", border=1, fill=True, align='C')

                                y_item = y_tabla + 6; pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", '', 7)
                                for _, row_rem in df_g.iterrows():
                                    cant_v = str(row_rem.get(col_cant_univ, 1))
                                    if not cant_v.strip() or cant_v == 'nan': cant_v = '1'
                                    pdf.set_xy(x_offset, y_item); pdf.cell(15, 5, limpiar_texto(cant_v), border=1, align='C'); pdf.cell(120, 5, limpiar_texto(str(row_rem.get(col_desc_univ, '')))[:80], border=1)
                                    y_item += 5
                                    
                                pdf.set_xy(x_offset, 192); pdf.set_font("Arial", 'I', 6); pdf.set_text_color(120, 120, 120); pdf.cell(135, 4, limpiar_texto(firma_digital), align='R')

                            dibujar_bloque_remision(10)
                            pdf.set_draw_color(180, 180, 180); pdf.line(148.5, 10, 148.5, 200); pdf.set_draw_color(0, 0, 0)
                            dibujar_bloque_remision(152)

                            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                                pdf.output(tmp.name)
                                nombre_archivo = f"Remision_{folio_str_print.replace(' - ', '_')}_{siniestro_v}.pdf"
                                with open(tmp.name, "rb") as f: pdf_bytes = f.read()
                                pdfs_list.append({'folio': folio_str_print, 'siniestro': siniestro_v, 'bytes': pdf_bytes, 'nombre': nombre_archivo})

                        st.session_state['pdfs_list'] = pdfs_list
                        if avisos_unicos: st.session_state['avisos_remision'] = list(avisos_unicos)
                    
                    st.toast("✅ ¡Bases actualizadas exitosamente en la nube!", icon="✅"); st.cache_data.clear(); st.rerun()
                except Exception as e: st.error(f"❌ Error guardando: {e}")
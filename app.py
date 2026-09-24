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

# ESTA LÍNEA DEBE SER SIEMPRE LA NÚMERO 1 DE STREAMLIT (Ahora con layout="wide")
st.set_page_config(page_title="Dashboard PMR - Operación", page_icon="📦", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
        [data-testid="stDataFrame"] { zoom: 0.95; }
        
        /* 1. Matar el padding fantasma del contenedor principal de Streamlit */
        .main .block-container { 
            padding-top: 0rem !important; 
            padding-bottom: 40px; 
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
            visibility: hidden !important; 
            height: 0px !important; 
            padding: 0px !important; 
            min-height: 0px !important; 
        }
        
        /* --- 3. CINTURÓN DE SEGURIDAD PARA EL MENÚ SUPERIOR (STICKY) --- */
        div[data-testid="stVerticalBlock"] > div:has([data-testid="stRadio"]) {
            position: -webkit-sticky !important;
            position: sticky !important; 
            top: -15px !important; /* Sube la barra para tragar el espacio vacío */
            z-index: 99999 !important; 
            background-color: #0E1117 !important; 
            padding-top: 30px !important; /* Rellena el color oscuro hacia arriba */
            padding-bottom: 15px !important; 
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
    "📊 Analítico", "⚙️ Panel Operativo", "🛒 Compras", "🏢 Talleres", 
    "📦 Inventario", "📝 Remisiones", "🧾 Facturación", "Precios Promedio", "🔍 Consultas", "🛠️ Cuartel General"
]

col_logo, col_menu, col_aseg, col_btn = st.columns([1.5, 6.0, 1.5, 1])

with col_logo:
    try: st.image("logo.png", width=120)
    except: st.markdown("**PREMIER**")

with col_menu:
    vista_actual = st.radio("Navegación", opciones_menu, horizontal=True, label_visibility="collapsed")

with col_aseg:
    if vista_actual in ["📊 Analítico", "⚙️ Panel Operativo"]:
        aseguradora_sel = st.selectbox("Aseguradora", ["Multiasistencias", "GNP"], label_visibility="collapsed")
    else:
        aseguradora_sel = "MULTI" 

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

@st.cache_data(ttl=10)
def cargar_datos():
    df_uni = obtener_dataframe("BD_UNIFICADA")
    df_comp = obtener_dataframe("BD_COMPRAS", silent=True)
    df_cat = obtener_dataframe("BD_TALLERES", silent=True)
    if df_cat.empty: df_cat = obtener_dataframe("Catálogo", silent=True)
    try: 
        df_inv = obtener_dataframe("BD_INVENTARIO", silent=True)
        if not df_inv.empty and 'Sin Existencia' in df_inv.columns:
            df_inv['Sin Existencia'] = df_inv['Sin Existencia'].astype(str).str.strip().str.upper().isin(['TRUE', 'SI', '1', 'X', 'V', 'VERDADERO'])
    except: df_inv = pd.DataFrame()
    df_prov = obtener_dataframe("BD_PROVEEDORES", silent=True)
    if not df_uni.empty and 'Siniestro Relacionado' in df_uni.columns: df_uni.rename(columns={'Siniestro Relacionado': 'Siniestro'}, inplace=True)
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
    
    # CORRECCIÓN: AGREGAMOS LA BÚSQUEDA DE LA COLUMNA ORIGEN
    col_origen = next((c for c in df_trabajo_completo.columns if "ORIGEN" in str(c).upper()), None)
    
    col_cant = next((c for c in df_trabajo_completo.columns if "CANTIDAD" in str(c).upper() or "CANT" == str(c).upper()), None)
    col_precio = next((c for c in df_trabajo_completo.columns if "PRECIO" in str(c).upper() or "COSTO" in str(c).upper()), None)
    col_estatus = next((c for c in df_trabajo_completo.columns if "ESTATUS" in str(c).upper() or "STATUS" in str(c).upper()), None)
    col_vencimiento = next((c for c in df_trabajo_completo.columns if "VENCIMIENTO" in str(c).upper() or "PROMESA" in str(c).upper()), None)
    col_asignacion = next((c for c in df_trabajo_completo.columns if "ASIGNACI" in str(c).upper()), None)
    col_fecha_confi = next((c for c in df_trabajo_completo.columns if "FECHA CONFI" in str(c).upper()), None)
    col_guia = next((c for c in df_trabajo_completo.columns if "GUIA" in str(c).upper() or "GUÍA" in str(c).upper()), None)
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
    # CORRECCIÓN: AGREGAMOS col_origen A LA LISTA DE INICIALIZACIÓN
    col_id = col_taller = col_marca = col_modelo = col_desc = col_origen = col_cant = col_precio = col_estatus = col_vencimiento = col_asignacion = col_fecha_confi = col_guia = col_remision = col_comentarios = col_aseg = None
    df_trabajo = df_proceso = df_recoleccion_total = pd.DataFrame()

# ==============================================================================
# === [BLOQUE 5: NOTIFICACIONES Y BANDEJA PDF] ===
# ==============================================================================
if 'pdfs_list' in st.session_state and st.session_state['pdfs_list']:
    st.success("🎉 ¡Remisión(es) generada(s) exitosamente!")
    c_pdfs = st.columns(len(st.session_state['pdfs_list']) + 1)
    for i, pdf_data in enumerate(st.session_state['pdfs_list']):
        with c_pdfs[i]:
            st.download_button(label=f"📄 Descargar {pdf_data['folio']}", data=pdf_data['bytes'], file_name=pdf_data['nombre'], mime="application/pdf", type="primary", use_container_width=True)
    with c_pdfs[-1]:
        if st.button("🧹 Limpiar Bandeja", use_container_width=True):
            st.session_state['pdfs_list'] = []
            st.rerun()
    st.markdown("---")

df_editado_conf = pd.DataFrame()
df_editado_venc = pd.DataFrame()
df_editado_atrasadas = pd.DataFrame()
df_editado_cobro = pd.DataFrame()
df_editado_fact = pd.DataFrame()
df_editado = pd.DataFrame()

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
            if pendientes_bot > 0: st.markdown(f'<div class="alerta-flash alerta-warning">🚨 <strong>¡ATENCIÓN!</strong> Han ingresado <strong>{pendientes_bot}</strong> pedido(s) nuevo(s) por confirmar.</div>', unsafe_allow_html=True)

    if vista_actual in ["⚙️ Panel Operativo", "🛒 Compras"]:
        if col_estatus and not df_trabajo_completo.empty:
            pendientes_surtido = len(df_trabajo_completo[df_trabajo_completo[col_estatus].astype(str).str.upper() == "EN PROCESAMIENTO"])
            if pendientes_surtido > 0:
                primer_nombre = str(usuario_activo).split()[0] if usuario_activo else "Usuario"
                st.markdown(f'<div class="alerta-flash alerta-info">🎯 <strong>¡Hola {primer_nombre}!</strong> Hay <strong>{pendientes_surtido}</strong> pedido(s) confirmado(s) esperando a ser comprados/surtidos.</div>', unsafe_allow_html=True)

# ==============================================================================
# === [BLOQUE 6: VISTAS - ANALÍTICO & OPERATIVO] ===
# ==============================================================================
if vista_actual == "📊 Analítico":
    st.markdown("## 📊 Rendimiento de Operación")
    st.markdown("#### 1. Estado General de Partidas en Proceso")
    if col_estatus and col_vencimiento and not df_proceso.empty:
        df_grafico = df_proceso.copy()
        df_agrupado = df_grafico.groupby([col_vencimiento, col_estatus]).size().reset_index(name='Cantidad')
        fig = px.bar(df_agrupado, x=col_vencimiento, y='Cantidad', color=col_estatus, barmode='stack', color_discrete_sequence=["#1E88E5", "#64B5F6", "#0D47A1", "#1976D2", "#90CAF9"])
        col_graf, col_det = st.columns([2, 1])
        with col_graf: graf_sel = st.plotly_chart(fig, use_container_width=True, on_select="rerun")
        with col_det:
            st.markdown("📄 **Detalle de Partidas**")
            if graf_sel and len(graf_sel.selection.points) > 0:
                fecha_sel = graf_sel.selection.points[0]["x"]
                df_detalle = df_grafico[df_grafico[col_vencimiento] == fecha_sel]
                cols_mostrar = [c for c in [col_id, col_taller, col_estatus] if c in df_detalle.columns]
                st.dataframe(df_detalle[cols_mostrar], use_container_width=True, hide_index=True)
            else: st.info("👆 Haz clic en una barra para filtrar la tabla.")
    else: st.warning("No hay partidas en proceso para graficar.")

    st.markdown("---")
    st.markdown("#### 2. Pedidos por Llegar (Compras a Proveedores)")
    if not df_compras.empty:
        df_compras['Recibido_Bool'] = df_compras['Recibido'].astype(str).str.strip().str.upper().isin(['TRUE', 'SI', '1', 'YES', 'V', 'X'])
        df_compras_llegar = df_compras[df_compras['Recibido_Bool'] == False].copy()
        if not df_compras_llegar.empty:
            def parse_spanish_date_comp(d_str):
                if not isinstance(d_str, str): return pd.NaT
                d_str = d_str.lower().replace('-', '/') 
                meses = {'ene':'01', 'feb':'02', 'mar':'03', 'abr':'04', 'may':'05', 'jun':'06', 'jul':'07', 'ago':'08', 'sep':'09', 'oct':'10', 'nov':'11', 'dic':'12'}
                for text, num in meses.items():
                    if text in d_str: d_str = d_str.replace(text, num); break
                try: return pd.to_datetime(d_str, format='%d/%m/%y', errors='coerce')
                except: return pd.NaT

            df_compras_llegar['Fecha_Compra_Dt'] = df_compras_llegar['Fecha Compra'].apply(parse_spanish_date_comp)
            df_compras_llegar['ETA_Dias'] = pd.to_numeric(df_compras_llegar['Tiempo Entrega (Días)'], errors='coerce').fillna(0)
            df_compras_llegar['Llegada_Calculada'] = df_compras_llegar['Fecha_Compra_Dt'] + pd.to_timedelta(df_compras_llegar['ETA_Dias'], unit='d')
            df_compras_llegar = df_compras_llegar.sort_values(by='Llegada_Calculada', ascending=True)
            hoy_comparacion = pd.to_datetime(datetime.datetime.now().date())
            df_compras_llegar['Estatus'] = df_compras_llegar['Llegada_Calculada'].apply(lambda x: "🔴 Atrasado" if pd.notna(x) and x < hoy_comparacion else "🟢 En tiempo")
            df_compras_llegar['Fecha Llegada'] = df_compras_llegar['Llegada_Calculada'].dt.strftime('%d/%b/%y').fillna('-')
            cols_llegar = [c for c in ['Siniestro', 'Taller', 'Vehículo', 'Descripción Pieza', 'Proveedor', 'Fecha Compra', 'Tiempo Entrega (Días)', 'Fecha Llegada', 'Estatus'] if c in df_compras_llegar.columns]
            st.dataframe(df_compras_llegar[cols_llegar], use_container_width=True, hide_index=True)
        else: st.info("✅ Todos los pedidos han sido recibidos.")
    
    st.markdown("---")
    st.markdown("#### 3. Pedidos Activos por CDR (Taller)")
    if col_taller and not df_proceso.empty:
        df_talleres = df_proceso[col_taller].value_counts().reset_index()
        df_talleres.columns = ['Taller', 'Cantidad']
        fig_bar = px.bar(df_talleres, x='Cantidad', y='Taller', orientation='h')
        fig_bar.update_layout(yaxis={'categoryorder':'total ascending'}, margin=dict(t=10, b=0, l=0, r=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")
    st.markdown("#### 4. ⏱️ Análisis de Tiempos Operativos (Días Promedio)")
    if col_asignacion and col_fecha_confi and not df_completo.empty:
        df_t = df_completo.copy()
        
        def parse_fecha_segura(d_str):
            if pd.isna(d_str) or str(d_str).strip() in ['', 'NaT', 'None']: return pd.NaT
            d_str_clean = str(d_str).lower().replace('-', '/').strip()
            if d_str_clean.replace('.','',1).isdigit():
                val = float(d_str_clean)
                if val > 30000: return pd.to_datetime('1899-12-30') + pd.to_timedelta(val, unit='D')
            meses = {'ene':'01', 'feb':'02', 'mar':'03', 'abr':'04', 'may':'05', 'jun':'06', 'jul':'07', 'ago':'08', 'sep':'09', 'oct':'10', 'nov':'11', 'dic':'12'}
            for text, num in meses.items():
                if text in d_str_clean: d_str_clean = d_str_clean.replace(text, num)
            try: return pd.to_datetime(d_str_clean, dayfirst=True, errors='coerce')
            except: return pd.NaT

        df_t['F_Asig'] = df_t[col_asignacion].apply(parse_fecha_segura)
        df_t['F_Conf'] = df_t[col_fecha_confi].apply(parse_fecha_segura)
        def find_col(df, keywords):
            for c in df.columns:
                c_up = str(c).upper().replace('Í','I').replace('Ó','O')
                if all(k in c_up for k in keywords): return c
            return None
        col_envio = find_col(df_t, ["FECHA", "ENVIO"]); col_recibido = find_col(df_t, ["FECHA", "RECIB"]); col_fact = find_col(df_t, ["FECHA", "FACTUR"])
        df_t['F_Env'] = df_t[col_envio].apply(parse_fecha_segura) if col_envio else pd.NaT
        df_t['F_Rec'] = df_t[col_recibido].apply(parse_fecha_segura) if col_recibido else pd.NaT
        df_t['F_Fact'] = df_t[col_fact].apply(parse_fecha_segura) if col_fact else pd.NaT
        df_t['Dias_Asig_Conf'] = (df_t['F_Conf'] - df_t['F_Asig']).dt.days
        df_t['Dias_Conf_Env'] = (df_t['F_Env'] - df_t['F_Conf']).dt.days if col_envio else pd.Series(dtype=float)
        df_t['Dias_Env_Rec'] = (df_t['F_Rec'] - df_t['F_Env']).dt.days if col_envio and col_recibido else pd.Series(dtype=float)
        df_t['Dias_Rec_Fact'] = (df_t['F_Fact'] - df_t['F_Rec']).dt.days if col_recibido and col_fact else pd.Series(dtype=float)
        
        def get_promedio(serie):
            try:
                validos = serie[(serie >= 0) & (serie <= 365)]
                return round(validos.mean(), 1) if not validos.empty and pd.notna(validos.mean()) else 0
            except: return 0
        prom_1 = get_promedio(df_t['Dias_Asig_Conf']); prom_2 = get_promedio(df_t['Dias_Conf_Env']); prom_3 = get_promedio(df_t['Dias_Env_Rec']); prom_4 = get_promedio(df_t['Dias_Rec_Fact'])
        etapas = ['Asignación ➔ Confirmación', 'Confirmación ➔ Envío', 'Envío ➔ Recibido', 'Recibido ➔ Facturación']
        valores = [prom_1, prom_2, prom_3, prom_4]
        fig_tiempos = px.bar(x=valores, y=etapas, orientation='h', text=valores, labels={'x': 'Días Promedio', 'y': ''}, color=etapas, color_discrete_sequence=["#FF9800", "#2196F3", "#4CAF50", "#9C27B0"])
        fig_tiempos.update_traces(textposition='auto', showlegend=False); fig_tiempos.update_layout(xaxis_title="Días Promedio", yaxis_title="")
        st.plotly_chart(fig_tiempos, use_container_width=True)

elif vista_actual == "⚙️ Panel Operativo":
    st.markdown("### 📈 Indicadores Diarios")
    tz_mx = datetime.timezone(datetime.timedelta(hours=-6))
    hoy_dt_full = datetime.datetime.now(tz_mx)
    meses_es = {1:'ene', 2:'feb', 3:'mar', 4:'abr', 5:'may', 6:'jun', 7:'jul', 8:'ago', 9:'sep', 10:'oct', 11:'nov', 12:'dic'}
    hoy_str = f"{hoy_dt_full.day:02d}/{meses_es[hoy_dt_full.month]}/{hoy_dt_full.strftime('%y')}"
    hoy_dt = pd.to_datetime(hoy_dt_full.date())
    
    def parse_dt_safe_op(val):
        if pd.isna(val) or str(val).strip() == '': return pd.NaT
        val_str = str(val).lower()
        meses_map = {'ene':'01', 'feb':'02', 'mar':'03', 'abr':'04', 'may':'05', 'jun':'06', 'jul':'07', 'ago':'08', 'sep':'09', 'oct':'10', 'nov':'11', 'dic':'12'}
        for m_es, m_num in meses_map.items():
            if m_es in val_str: val_str = val_str.replace(m_es, m_num); break
        try: return pd.to_datetime(val_str, dayfirst=True)
        except: return pd.NaT

    if col_vencimiento:
        fechas_venc_dt = df_proceso[col_vencimiento].apply(parse_dt_safe_op)
        vencidas_pasadas_kpi = len(df_proceso[(fechas_venc_dt < hoy_dt) & (df_proceso[col_vencimiento] != '') & (~df_proceso[col_estatus].astype(str).str.upper().str.contains("CONFIRMAR"))])
    else: vencidas_pasadas_kpi = 0
        
    vencen_hoy = len(df_proceso[df_proceso[col_vencimiento] == hoy_str]) if col_vencimiento else 0
    recolecciones = len(df_recoleccion_total)
    por_confirmar_kpi = len(df_proceso[df_proceso[col_estatus].astype(str).str.upper().str.contains("CONFIRMAR") | (df_proceso[col_estatus].astype(str).str.strip() == "")]) if col_estatus else 0
    en_proceso = len(df_proceso[~df_proceso[col_estatus].astype(str).str.upper().str.contains("CONFIRMAR") & (df_proceso[col_estatus].astype(str).str.strip() != "")]) if col_estatus else len(df_proceso)
    partidas_por_facturar = len(df_trabajo[df_trabajo[col_estatus].astype(str).str.strip().str.upper() == "RECIBIDO"]) if col_estatus else 0
    
    kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)
    kpi1.metric("📦 En Proceso (Piezas)", en_proceso); kpi2.metric("⏳ Por Confirmar", por_confirmar_kpi); kpi3.metric("⚠️ Vencen Hoy", vencen_hoy)
    kpi4.metric("❌ Vencidos", vencidas_pasadas_kpi); kpi5.metric("↩️ En Recolección", recolecciones); kpi6.metric("🧾 Por Facturar", partidas_por_facturar)

    st.markdown("### 🎛️ Filtros de Búsqueda")
    filtro_col1, filtro_col2, filtro_col3, filtro_col4 = st.columns(4)
    with filtro_col1: taller_sel = st.multiselect("🏢 Taller:", sorted([str(t) for t in df_proceso[col_taller].dropna().unique() if str(t).strip() != '']) if col_taller else [], placeholder="Todos...")
    with filtro_col2: estatus_sel = st.multiselect("📊 Estatus:", sorted([str(e) for e in df_proceso[col_estatus].dropna().unique() if str(e).strip() != '']) if col_estatus else [], placeholder="Todos...")
    with filtro_col3:
        df_temp = df_proceso.copy()
        if taller_sel: df_temp = df_temp[df_temp[col_taller].astype(str).isin(taller_sel)]
        if estatus_sel: df_temp = df_temp[df_temp[col_estatus].astype(str).isin(estatus_sel)]
        siniestro_sel = st.multiselect(f"🚗 Siniestro - Vehículo:", sorted(list(df_temp['Filtro_Siniestro'].dropna().unique())) if 'Filtro_Siniestro' in df_temp.columns else [], placeholder="Todos...")
    with filtro_col4:
        df_temp_desc = df_temp.copy()
        if siniestro_sel: df_temp_desc = df_temp_desc[df_temp_desc['Filtro_Siniestro'].isin(siniestro_sel)]
        desc_sel = st.multiselect(f"⚙️ Refacción:", sorted(list(df_temp_desc[col_desc].dropna().astype(str).unique())) if col_desc in df_temp_desc.columns else [], placeholder="Todas...")

    df_filtrado = df_proceso.copy()
    if taller_sel: df_filtrado = df_filtrado[df_filtrado[col_taller].astype(str).isin(taller_sel)]
    if estatus_sel: df_filtrado = df_filtrado[df_filtrado[col_estatus].astype(str).isin(estatus_sel)]
    if siniestro_sel: df_filtrado = df_filtrado[df_filtrado['Filtro_Siniestro'].isin(siniestro_sel)]
    if desc_sel: df_filtrado = df_filtrado[df_filtrado[col_desc].astype(str).isin(desc_sel)]

    base_config = {}
    if col_id and col_id in df_filtrado.columns: base_config[col_id] = st.column_config.TextColumn("Siniestro")
    if 'Vehiculo_Info' in df_filtrado.columns: base_config['Vehiculo_Info'] = st.column_config.TextColumn("Vehículo")
    if col_taller: base_config[col_taller] = st.column_config.TextColumn("Taller", width="small")
    if col_asignacion: base_config[col_asignacion] = st.column_config.TextColumn("Asig.", width="small")
    if col_fecha_confi: base_config[col_fecha_confi] = st.column_config.TextColumn("Conf.", width="small")
    if col_cant: base_config[col_cant] = st.column_config.TextColumn("Cant", width="small")
    if col_desc: base_config[col_desc] = st.column_config.TextColumn("Descrip.") 
    if col_origen: base_config[col_origen] = st.column_config.TextColumn("Origen", width="small")
    if col_precio: base_config[col_precio] = st.column_config.TextColumn("Precio", width="small")
    if col_estatus: base_config[col_estatus] = st.column_config.TextColumn("Estatus", width="small")
    if col_vencimiento: base_config[col_vencimiento] = st.column_config.TextColumn("Venc.", width="small")
    if col_guia: base_config[col_guia] = st.column_config.TextColumn("Guía", width="small")
    if col_remision: base_config[col_remision] = st.column_config.TextColumn("Folio Remisión", width="small")
    if col_comentarios: base_config[col_comentarios] = st.column_config.TextColumn("Obs.") 

    # SHIELD ACTIVADO: Atrapa estatus vacíos o "POR CONFIRMAR"
    cond_confirmar = df_filtrado[col_estatus].astype(str).str.upper().str.contains("CONFIRMAR") | (df_filtrado[col_estatus].fillna('').astype(str).str.strip() == "")
    df_por_confirmar = df_filtrado[cond_confirmar].copy() if col_estatus else pd.DataFrame()
    
    with st.expander(f"⏳ Piezas por Confirmar | {len(df_por_confirmar)} Partida(s)", expanded=False):
        dfs_editados_conf = []
        if not df_por_confirmar.empty:
            for taller, df_taller in df_por_confirmar.groupby(col_taller):
                with st.expander(f"🏢 {taller}", expanded=False):
                    for siniestro_auto, df_grupo in df_taller.groupby(col_id):
                        st.markdown(f"**🚗 {siniestro_auto} | {df_grupo['Vehiculo_Info'].iloc[0]}**")
                        if not modo_consulta and permiso_edicion: 
                            df_grupo['Confirmar Surtido'] = False; df_grupo['Cancelar'] = False
                            cols_conf = [c for c in [col_cant, col_desc, col_origen, col_asignacion, col_vencimiento, col_estatus, col_comentarios, 'Confirmar Surtido', 'Cancelar'] if c in df_grupo.columns]
                            config_conf = base_config.copy()
                            config_conf.update({"Confirmar Surtido": st.column_config.CheckboxColumn("✅ Confirmar", default=False), "Cancelar": st.column_config.CheckboxColumn("🚫 Can", default=False)})
                            df_editado_parcial = st.data_editor(df_grupo[cols_conf], column_config=config_conf, disabled=[c for c in cols_conf if c not in ['Confirmar Surtido', 'Cancelar', col_comentarios]], hide_index=True, use_container_width=True, key=f"ed_conf_{taller}_{siniestro_auto}")
                            for col in [col_id, col_taller, col_marca, col_modelo, col_desc, col_origen]:
                                if col in df_grupo.columns and col not in df_editado_parcial.columns: df_editado_parcial[col] = df_grupo[col].values
                            dfs_editados_conf.append(df_editado_parcial)
                        else:
                            cols_conf = [c for c in [col_cant, col_desc, col_origen, col_asignacion, col_vencimiento, col_estatus, col_comentarios] if c in df_grupo.columns]
                            st.dataframe(df_grupo[cols_conf], column_config=base_config, hide_index=True, use_container_width=True)
        if dfs_editados_conf: df_editado_conf = pd.concat(dfs_editados_conf, ignore_index=True)

    df_vencimientos = df_filtrado[(df_filtrado[col_vencimiento] == hoy_str) & (~df_filtrado[col_estatus].astype(str).str.upper().str.contains("CONFIRMAR|ENTREGADO|RECIBIDO|FACTURADO|CANCELADO|RECOLEC")) & (df_filtrado[col_estatus].fillna('').astype(str).str.strip() != "")].copy() if col_vencimiento else pd.DataFrame()
    with st.expander(f"🚨 Vencimientos de Hoy | {len(df_vencimientos)} Partida(s)", expanded=False):
        if not df_vencimientos.empty:
            if not modo_consulta and permiso_edicion:
                df_vencimientos['Cancelar'] = False
                df_vencimientos['Reasignar'] = df_vencimientos[col_estatus].astype(str).str.upper() == "REASIGNAR" 
                df_vencimientos['Nueva Fecha'] = pd.NaT
                cols_venc = [c for c in [col_taller, col_id, 'Vehiculo_Info', col_cant, col_desc, col_precio, col_estatus, col_vencimiento, col_guia, col_comentarios, 'Cancelar', 'Reasignar', 'Nueva Fecha'] if c in df_vencimientos.columns]
                config_venc = base_config.copy()
                config_venc.update({"Cancelar": st.column_config.CheckboxColumn("🚫 Can", default=False), "Reasignar": st.column_config.CheckboxColumn("🔄 Reasig"), "Nueva Fecha": st.column_config.DateColumn("📅 Nueva Fecha", format="DD/MMM/YYYY")})
                df_editado_venc = st.data_editor(df_vencimientos[cols_venc], column_config=config_venc, disabled=[c for c in cols_venc if c not in ['Cancelar', 'Reasignar', 'Nueva Fecha', col_comentarios, col_guia]], hide_index=True, use_container_width=True, key="ed_venc")
                for col in [col_id, col_marca, col_modelo]:
                    if col in df_vencimientos.columns and col not in df_editado_venc.columns: df_editado_venc[col] = df_vencimientos[col].values
            else:
                cols_venc = [c for c in [col_taller, col_id, 'Vehiculo_Info', col_cant, col_desc, col_precio, col_estatus, col_vencimiento, col_guia, col_comentarios] if c in df_vencimientos.columns]
                st.dataframe(df_vencimientos[cols_venc], column_config=base_config, hide_index=True, use_container_width=True)
                
    if col_vencimiento and not df_filtrado.empty:
        fechas_venc_filtro = df_filtrado[col_vencimiento].apply(parse_dt_safe_op)
        df_atrasadas = df_filtrado[(fechas_venc_filtro < hoy_dt) & (df_filtrado[col_vencimiento] != '') & (~df_filtrado[col_estatus].astype(str).str.upper().str.contains("CONFIRMAR|ENTREGADO|RECIBIDO|FACTURADO|CANCELADO|RECOLEC")) & (df_filtrado[col_estatus].fillna('').astype(str).str.strip() != "")].copy()
    else: df_atrasadas = pd.DataFrame()
    with st.expander(f"❌ Vencimientos Atrasados | {len(df_atrasadas)} Partida(s)", expanded=False):
        if not df_atrasadas.empty:
            if not modo_consulta and permiso_edicion:
                df_atrasadas['Cancelar'] = False
                df_atrasadas['Reasignar'] = df_atrasadas[col_estatus].astype(str).str.upper() == "REASIGNAR" 
                df_atrasadas['Nueva Fecha'] = pd.NaT
                cols_atr = [c for c in [col_taller, col_id, 'Vehiculo_Info', col_cant, col_desc, col_precio, col_estatus, col_vencimiento, col_comentarios, 'Cancelar', 'Reasignar', 'Nueva Fecha'] if c in df_atrasadas.columns]
                config_atr = base_config.copy()
                config_atr.update({"Cancelar": st.column_config.CheckboxColumn("🚫 Can", default=False), "Reasignar": st.column_config.CheckboxColumn("🔄 Reasig"), "Nueva Fecha": st.column_config.DateColumn("📅 Nueva Fecha", format="DD/MMM/YYYY")})
                df_editado_atrasadas = st.data_editor(df_atrasadas[cols_atr], column_config=config_atr, disabled=[c for c in cols_atr if c not in ['Cancelar', 'Reasignar', 'Nueva Fecha', col_comentarios]], hide_index=True, use_container_width=True, key="ed_atr")
                for col in [col_id, col_marca, col_modelo]:
                    if col in df_atrasadas.columns and col not in df_editado_atrasadas.columns: df_editado_atrasadas[col] = df_atrasadas[col].values
            else:
                cols_atr = [c for c in [col_taller, col_id, 'Vehiculo_Info', col_cant, col_desc, col_precio, col_estatus, col_vencimiento, col_comentarios] if c in df_atrasadas.columns]
                st.dataframe(df_atrasadas[cols_atr], column_config=base_config, hide_index=True, use_container_width=True)

    df_por_recibir = df_filtrado[df_filtrado[col_estatus].astype(str).str.upper() == "ENTREGADO"].copy() if col_estatus else pd.DataFrame()
    with st.expander(f"📥 Por Recibir (Entregados en CDR) | {len(df_por_recibir)} Partida(s)", expanded=False):
        if not df_por_recibir.empty:
            if not modo_consulta and permiso_edicion:
                df_por_recibir['Marcar Recibido'] = False
                cols_cobro = [c for c in [col_taller, col_id, 'Vehiculo_Info', col_cant, col_desc, col_precio, col_estatus, col_comentarios, 'Marcar Recibido'] if c in df_por_recibir.columns]
                config_cobro = base_config.copy()
                config_cobro.update({"Marcar Recibido": st.column_config.CheckboxColumn("🏁 Marcar Recibido", default=False)})
                
                df_editado_cobro = st.data_editor(df_por_recibir[cols_cobro], column_config=config_cobro, disabled=[c for c in cols_cobro if c not in ['Marcar Recibido', col_comentarios]], hide_index=True, use_container_width=True, key="ed_cobro")
                
                for col in [col_id, col_desc]: 
                    if col in df_por_recibir.columns and col not in df_editado_cobro.columns: df_editado_cobro[col] = df_por_recibir[col].values
            else:
                cols_cobro = [c for c in [col_taller, col_id, 'Vehiculo_Info', col_cant, col_desc, col_precio, col_estatus, col_comentarios] if c in df_por_recibir.columns]
                st.dataframe(df_por_recibir[cols_cobro], column_config=base_config, hide_index=True, use_container_width=True)

    if col_estatus and col_estatus in df_filtrado.columns:
        # SHIELD ACTIVADO: Ignora celdas vacías en Pedidos Asignados para no mezclarlas
        mask_asignados = (~df_filtrado[col_estatus].fillna('').astype(str).str.upper().str.contains("CONFIRMAR|ENTREGADO|RECIBIDO|FACTURADO|CANCELADO")) & (df_filtrado[col_estatus].fillna('').astype(str).str.strip() != "")
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
                
            def generar_llave_temp(id_val, desc_val):
                id_str = str(id_val).strip().upper()
                if id_str.endswith('.0'): id_str = id_str[:-2]
                desc_str = ' '.join(str(desc_val).strip().upper().split())
                return f"{id_str}_{desc_str}"

            if not df_compras.empty:
                df_compras_temp = df_compras.copy()
                df_compras_temp['LLAVE_COMP'] = df_compras_temp.apply(lambda r: generar_llave_temp(r.get('Siniestro',''), r.get('Descripción Pieza','')), axis=1)
                dict_prov = dict(zip(df_compras_temp['LLAVE_COMP'], df_compras_temp['Proveedor']))
                dict_costo = dict(zip(df_compras_temp['LLAVE_COMP'], df_compras_temp['Costo Compra']))
                dict_eta = dict(zip(df_compras_temp['LLAVE_COMP'], df_compras_temp['Tiempo Entrega (Días)']))
                
                df_asignados['LLAVE_TEMP'] = df_asignados.apply(lambda r: generar_llave_temp(r.get(col_id,''), r.get(col_desc,'')), axis=1)
                df_asignados['Proveedor'] = df_asignados['LLAVE_TEMP'].map(dict_prov).fillna("")
                
                def safe_float(v):
                    try: return float(str(v).replace('$', '').replace(',', '').strip())
                    except: return 0.0
                df_asignados['Costo Compra'] = df_asignados['LLAVE_TEMP'].map(dict_costo).apply(safe_float)
                
                def safe_int(v):
                    try: return int(float(str(v).strip()))
                    except: return 0
                df_asignados['ETA (Días)'] = df_asignados['LLAVE_TEMP'].map(dict_eta).apply(safe_int)
            else:
                df_asignados['Proveedor'] = ""; df_asignados['Costo Compra'] = 0.0; df_asignados['ETA (Días)'] = 0     
            
            for taller, df_taller in df_asignados.groupby(col_taller):
                with st.expander(f"🏢 {taller}", expanded=False):
                    for siniestro_auto, df_grupo in df_taller.groupby(col_id):
                        st.markdown(f"**🚗 {siniestro_auto} | {df_grupo['Vehiculo_Info'].iloc[0]}**")
                        if not modo_consulta and permiso_edicion:
                            columnas_operacion = ['Proveedor', 'Costo Compra', 'ETA (Días)', 'Entregado', 'Recibido', 'Cancelar']
                            orden_deseado = [c for c in [col_asignacion, col_fecha_confi, col_cant, col_desc, col_origen, col_precio, col_estatus, col_vencimiento, col_guia, col_remision, col_comentarios] if c in df_grupo.columns] + columnas_operacion
                            config_pedidos = base_config.copy()
                            config_pedidos.update({ 
                                col_asignacion: st.column_config.TextColumn("Asig."), col_vencimiento: st.column_config.TextColumn("Venc."),
                                "Proveedor": st.column_config.SelectboxColumn("🏢 Proveedor", options=lista_proveedores), 
                                "Costo Compra": st.column_config.NumberColumn("💲 Costo", format="$ %.2f"), "ETA (Días)": st.column_config.NumberColumn("⏳ Días", step=1, disabled=True), 
                                "Entregado": st.column_config.CheckboxColumn("🚚 Ent"), "Recibido": st.column_config.CheckboxColumn("🏁 Rec"), "Cancelar": st.column_config.CheckboxColumn("🚫 Can") 
                            })
                            columnas_editables = ['Proveedor', 'Costo Compra', 'ETA (Días)', 'Entregado', 'Recibido', 'Cancelar', col_comentarios, col_guia, col_asignacion, col_vencimiento]
                            df_editado_parcial = st.data_editor(df_grupo[orden_deseado], column_config=config_pedidos, disabled=[c for c in orden_deseado if c not in columnas_editables], hide_index=True, use_container_width=True, key=f"ed_{taller}_{siniestro_auto}")
                            for col in [col_id, col_taller, col_marca, col_modelo, 'Vehiculo_Info', col_origen]:
                                if col in df_grupo.columns and col not in df_editado_parcial.columns: df_editado_parcial[col] = df_grupo[col].values
                            dfs_editados.append(df_editado_parcial)
                        else:
                            orden_deseado = [c for c in [col_asignacion, col_fecha_confi, col_cant, col_desc, col_origen, col_precio, col_estatus, col_vencimiento, col_guia, col_remision, col_comentarios] if c in df_grupo.columns]
                            st.dataframe(df_grupo[orden_deseado], column_config=base_config, hide_index=True, use_container_width=True)
        if dfs_editados: df_editado = pd.concat(dfs_editados, ignore_index=True)

    df_recoleccion = df_recoleccion_total.copy()
    if taller_sel: df_recoleccion = df_recoleccion[df_recoleccion[col_taller].astype(str).isin(taller_sel)]
    if siniestro_sel:
        ids_sel = [s.split(" - ")[0] for s in siniestro_sel]
        df_recoleccion = df_recoleccion[df_recoleccion[col_id].isin(ids_sel)]
    if desc_sel: df_recoleccion = df_recoleccion[df_recoleccion[col_desc].astype(str).isin(desc_sel)]

    with st.expander(f"↩️ Piezas para Recolección | {len(df_recoleccion)} Partida(s)", expanded=False):
        if not df_recoleccion.empty:
            cols_rec = [c for c in [col_taller, col_id, 'Vehiculo_Info', col_desc, col_cant, col_precio, col_estatus, col_vencimiento, col_comentarios] if c in df_recoleccion.columns]
            st.dataframe(df_recoleccion[cols_rec], column_config=base_config, hide_index=True, use_container_width=True)

config_c = {
                            'Siniestro': st.column_config.TextColumn("Siniestro", disabled=True, width="small"), 
                            'Auto': st.column_config.TextColumn("Auto", disabled=True, width="medium"),
                            'CDR': st.column_config.TextColumn("CDR", disabled=True, width="medium"), 
                            'Pieza': st.column_config.TextColumn("Pieza", disabled=True, width="medium"),
                            'Proveedor': st.column_config.TextColumn("Proveedor", width="medium"), 
                            'Costo': st.column_config.NumberColumn("Costo", format="$ %.2f", width="small"),
                            'ETA(Días)': st.column_config.NumberColumn("ETA(Días)", step=1, width="small"), 
                            'Llegada Est.': st.column_config.TextColumn("Llegada Est.", disabled=True, width="small"),
                            'Cond. Pago': st.column_config.SelectboxColumn("Cond. Pago", options=opciones_pago, width="small"), 
                            'Días Cr.': st.column_config.NumberColumn("Días Cr.", step=1, width="small"),
                            'Pago': st.column_config.SelectboxColumn("Pago", options=["", "Pendiente", "Pagado", "En Aclaración"], width="small"),
                            'Recibido': st.column_config.CheckboxColumn("🏁 Recibido", width="small"), 
                            'Cancelar Compra': st.column_config.CheckboxColumn("🚫 Cancelar", width="small"),
                            'Alerta Financiera': st.column_config.TextColumn("Alerta Financiera", disabled=True, width="medium")
                        }

# ==============================================================================
# === [BLOQUE 8: VISTAS - FACTURACIÓN Y REMISIONES] ===
# ==============================================================================
if vista_actual == "🧾 Facturación":
    st.markdown("### 🧾 Pedidos Listos para Facturar")
    if col_estatus and not df_trabajo_completo.empty:
        df_fact = df_trabajo_completo[df_trabajo_completo[col_estatus].astype(str).str.strip().str.upper() == "RECIBIDO"].copy()
        if not df_fact.empty:
            df_fact['Facturado'] = False
            dfs_editados_fact = []
            for taller, df_taller in df_fact.groupby(col_taller):
                with st.expander(f"🏢 {taller} | {len(df_taller)} Partida(s) pendiente(s)", expanded=True):
                    if not modo_consulta and permiso_edicion:
                        cols_fact = [c for c in [col_id, 'Vehiculo_Info', col_desc, col_cant, col_precio, col_comentarios, 'Facturado'] if c in df_taller.columns]
                        config_fact = {
                            col_id: st.column_config.TextColumn("Siniestro", disabled=True), 'Vehiculo_Info': st.column_config.TextColumn("Vehículo", disabled=True),
                            col_desc: st.column_config.TextColumn("Descripción", disabled=True), col_cant: st.column_config.TextColumn("Cant", disabled=True),
                            col_precio: st.column_config.TextColumn("Precio", disabled=True), col_comentarios: st.column_config.TextColumn("Observaciones", disabled=True),
                            'Facturado': st.column_config.CheckboxColumn("🧾 Facturar")
                        }
                        df_ed_fact = st.data_editor(df_taller[cols_fact], column_config=config_fact, disabled=[c for c in cols_fact if c != 'Facturado'], hide_index=True, use_container_width=True, key=f"ed_fact_{taller}")
                        for col in [col_id, col_desc]:
                            if col in df_taller.columns and col not in df_ed_fact.columns: df_ed_fact[col] = df_taller[col].values
                        dfs_editados_fact.append(df_ed_fact)
                    else:
                        cols_mostrar = [c for c in [col_id, 'Vehiculo_Info', col_desc, col_cant, col_precio, col_comentarios] if c in df_taller.columns]
                        st.dataframe(df_taller[cols_mostrar], hide_index=True, use_container_width=True)
            if dfs_editados_fact: df_editado_fact = pd.concat(dfs_editados_fact, ignore_index=True)
        else: st.success("✅ No hay pedidos pendientes de facturación en este momento.")
    else: st.warning("No hay datos cargados para facturación.")

if vista_actual == "📝 Remisiones":
    st.markdown("### 📝 Centro de Emisión de Remisiones")
    st.info("Busca por número de siniestro, nombre del taller o modelo del vehículo en TODA la base de datos.")
    if not df_completo.empty:
        col_estatus_univ = next((c for c in df_completo.columns if "ESTATUS" in str(c).upper() or "STATUS" in str(c).upper()), None)
        col_rem_univ = next((c for c in df_completo.columns if "REMISION" in str(c).upper() or "REMISIÓN" in str(c).upper()), None)
        col_id_univ = next((c for c in df_completo.columns if "SINIESTRO" in str(c).upper()), None)
        col_taller_univ = next((c for c in df_completo.columns if "TALLER" in str(c).upper()), None)
        col_marca_univ = next((c for c in df_completo.columns if "MARCA" in str(c).upper()), None)
        col_modelo_univ = next((c for c in df_completo.columns if "MODELO" in str(c).upper()), None)
        col_desc_univ = next((c for c in df_completo.columns if "DESCRIPCI" in str(c).upper() or "REFACCI" in str(c).upper()), None)
        col_cant_univ = next((c for c in df_completo.columns if "CANTIDAD" in str(c).upper() or "CANT" == str(c).upper()), None)
        
        df_base = df_completo.copy()
        df_base['Vehiculo_Info_Univ'] = df_base[col_marca_univ].astype(str) + " " + df_base[col_modelo_univ].astype(str)

        mask_pendientes = ((~df_base[col_estatus_univ].astype(str).str.upper().str.contains("CANCELADO|FACTURADO|ENTREGADO|RECIBIDO|CONFIRMAR")) & (df_base[col_rem_univ].astype(str).str.strip() == ""))
        df_busqueda = df_base[mask_pendientes].copy()
        
        if not df_busqueda.empty:
            df_busqueda['Busqueda_Global'] = df_busqueda[col_id_univ].astype(str) + " | " + df_busqueda[col_taller_univ].astype(str) + " | " + df_busqueda['Vehiculo_Info_Univ'].astype(str)
            lista_opciones = [""] + sorted(list(df_busqueda['Busqueda_Global'].dropna().unique()))
            col_busqueda, _ = st.columns([2, 1])
            with col_busqueda: siniestro_seleccionado = st.selectbox("🔍 Buscar Siniestro, Taller o Vehículo (Universal):", options=lista_opciones)
                
            if siniestro_seleccionado:
                siniestro_buscar = siniestro_seleccionado.split(" | ")[0].strip()
                df_siniestro = df_base[df_base[col_id_univ].astype(str) == siniestro_buscar].copy()
                if not df_siniestro.empty:
                    st.markdown(f"**🚗 Vehículo:** {df_siniestro['Vehiculo_Info_Univ'].iloc[0]} | **🏢 Taller:** {df_siniestro[col_taller_univ].iloc[0]}")
                    df_remisionar = df_siniestro[~df_siniestro[col_estatus_univ].astype(str).str.upper().str.contains("CANCELADO")].copy()
                    if not df_remisionar.empty:
                        df_remisionar['Seleccionar'] = False 
                        cols_mostrar = [c for c in [col_cant_univ, col_desc_univ, col_estatus_univ, col_rem_univ, 'Seleccionar'] if c in df_remisionar.columns]
                        config_rem = {
                            col_cant_univ: st.column_config.TextColumn("Cant", disabled=True), col_desc_univ: st.column_config.TextColumn("Descripción", disabled=True),
                            col_estatus_univ: st.column_config.TextColumn("Estatus", disabled=True), col_rem_univ: st.column_config.TextColumn("Folio Actual", disabled=True),
                            'Seleccionar': st.column_config.CheckboxColumn("📦 Incluir en Remisión")
                        }
                        df_editado_rem = st.data_editor(df_remisionar[cols_mostrar], column_config=config_rem, hide_index=True, use_container_width=True, key=f"ed_rem_tab_{siniestro_buscar}")
                        piezas_seleccionadas = df_editado_rem[df_editado_rem['Seleccionar'] == True]
                        piezas_validas = piezas_seleccionadas[piezas_seleccionadas[col_rem_univ].astype(str).str.strip() == ""]
                        
                        if not piezas_validas.empty:
                            col_espacio, col_boton = st.columns([8.5, 1.5])
                            with col_boton:
                                if st.button("🖨️ Generar Remisión PMR", type="primary", use_container_width=True):
                                    st.session_state['trigger_remision_manual'] = {'siniestro': siniestro_buscar, 'descripciones': piezas_validas[col_desc_univ].tolist()}
                                    st.rerun()
                        elif not piezas_seleccionadas.empty: st.warning("⚠️ No puedes generar una remisión para piezas que ya tienen un folio asignado.")
                    else: st.warning("Todas las piezas de este siniestro están canceladas.")
        else: st.success("✅ ¡Felicidades! No hay pedidos pendientes de remisionar en toda la base.")
    else: st.warning("La base de datos está vacía.")

# ==============================================================================
# === [BLOQUE 9: VISTAS - COTIZADOR, CONSULTAS Y CUARTEL GENERAL] ===
# ==============================================================================
if vista_actual == "Precios Promedio":
    st.markdown("## 💲 Precios Promedio Históricos")
    st.info("Filtra el historial de la base unificada para obtener referencias de precios (Promedio, Máximo y Mínimo) para nuevas cotizaciones.")

    if not df_completo.empty:
        df_cot = df_completo.copy()
        
        # Mapeo dinámico de columnas
        col_marca_cot = next((c for c in df_cot.columns if "MARCA" in str(c).upper()), None)
        col_modelo_cot = next((c for c in df_cot.columns if "MODELO" in str(c).upper()), None)
        col_ano_cot = next((c for c in df_cot.columns if "AÑO" in str(c).upper() or "ANO" in str(c).upper()), None)
        col_desc_cot = next((c for c in df_cot.columns if "DESCRIPCI" in str(c).upper() or "REFACCI" in str(c).upper()), None)
        col_origen_cot = next((c for c in df_cot.columns if "ORIGEN" in str(c).upper()), None)
        col_precio_cot = next((c for c in df_cot.columns if "PRECIO" in str(c).upper() or "COSTO" in str(c).upper()), None)

        if col_marca_cot and col_precio_cot and col_desc_cot:
            # Limpieza crucial: Quitar símbolos y convertir a número para las métricas matemáticas
            df_cot['Precio_Num'] = df_cot[col_precio_cot].astype(str).replace({r'\$': '', r',': '', r' ': ''}, regex=True)
            df_cot['Precio_Num'] = pd.to_numeric(df_cot['Precio_Num'], errors='coerce')
            df_cot = df_cot.dropna(subset=['Precio_Num']) 
            df_cot = df_cot[df_cot['Precio_Num'] > 0] 

            col_m, col_mo, col_a, col_p = st.columns(4)
            with col_m:
                lista_marcas = ["Todas"] + sorted(df_cot[col_marca_cot].dropna().astype(str).unique().tolist())
                filtro_marca = st.selectbox("Marca", options=lista_marcas)
            with col_mo:
                if filtro_marca != "Todas":
                    lista_modelos = ["Todos"] + sorted(df_cot[df_cot[col_marca_cot] == filtro_marca][col_modelo_cot].dropna().astype(str).unique().tolist())
                else:
                    lista_modelos = ["Todos"] + sorted(df_cot[col_modelo_cot].dropna().astype(str).unique().tolist())
                filtro_modelo = st.selectbox("Modelo", options=lista_modelos)
            with col_a:
                lista_anios = ["Todos"] + sorted(df_cot[col_ano_cot].dropna().astype(str).unique().tolist(), reverse=True)
                filtro_anio = st.selectbox("Año", options=lista_anios)
            with col_p:
                filtro_pieza = st.text_input("Buscar Pieza (Ej. Salpicadera)", value="")

            # Motor de filtrado
            if filtro_marca != "Todas":
                df_cot = df_cot[df_cot[col_marca_cot] == filtro_marca]
            if filtro_modelo != "Todos":
                df_cot = df_cot[df_cot[col_modelo_cot] == filtro_modelo]
            if filtro_anio != "Todos":
                df_cot = df_cot[df_cot[col_ano_cot].astype(str) == filtro_anio]
            if filtro_pieza.strip() != "":
                df_cot = df_cot[df_cot[col_desc_cot].astype(str).str.contains(filtro_pieza.strip(), case=False, na=False)]

            st.divider()

            if not df_cot.empty:
                precio_promedio = df_cot['Precio_Num'].mean()
                precio_max = df_cot['Precio_Num'].max()
                precio_min = df_cot['Precio_Num'].min()

                kpi1, kpi2, kpi3 = st.columns(3)
                kpi1.metric("⚖️ Precio Promedio", f"${precio_promedio:,.2f}" if pd.notnull(precio_promedio) else "$0.00")
                kpi2.metric("📈 Precio Máximo", f"${precio_max:,.2f}" if pd.notnull(precio_max) else "$0.00")
                kpi3.metric("📉 Precio Mínimo", f"${precio_min:,.2f}" if pd.notnull(precio_min) else "$0.00")

                st.caption(f"**Resultados encontrados:** {len(df_cot)} piezas históricas")

                columnas_vista = [c for c in [col_marca_cot, col_modelo_cot, col_ano_cot, col_desc_cot, col_origen_cot, col_precio_cot] if c]
                st.dataframe(df_cot[columnas_vista].sort_values(by=col_precio_cot, ascending=False), use_container_width=True, hide_index=True)
            else:
                st.info("No hay registros históricos que coincidan con estos filtros.")
        else:
            st.warning("Faltan columnas clave (Marca, Modelo, Descripción o Precio) en la base maestra.")
    else:
        st.warning("La base de datos está vacía.")

elif vista_actual == "🔍 Consultas":
    st.markdown("## 🔍 Consulta Global y Filtros de Búsqueda")
    st.info("Utiliza los filtros desplegables para encontrar refacciones y siniestros específicos en el histórico.")
    
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
        else:
            df_busqueda['Filtro_Siniestro'] = df_busqueda[col_id_univ] if col_id_univ else "S/N"
            
        filtro_col1, filtro_col2, filtro_col3, filtro_col4 = st.columns(4)
        with filtro_col1: 
            taller_sel = st.multiselect("🏢 Taller:", sorted([str(t) for t in df_busqueda[col_taller_univ].dropna().unique() if str(t).strip() != '']) if col_taller_univ else [], placeholder="Todos...")
        with filtro_col2: 
            estatus_sel = st.multiselect("📊 Estatus:", sorted([str(e) for e in df_busqueda[col_estatus_univ].dropna().unique() if str(e).strip() != '']) if col_estatus_univ else [], placeholder="Todos...")
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
        
        if taller_sel: 
            df_filtrado_global = df_filtrado_global[df_filtrado_global[col_taller_univ].astype(str).isin(taller_sel)]
            filtros_activos = True
        if estatus_sel: 
            df_filtrado_global = df_filtrado_global[df_filtrado_global[col_estatus_univ].astype(str).isin(estatus_sel)]
            filtros_activos = True
        if siniestro_sel: 
            df_filtrado_global = df_filtrado_global[df_filtrado_global['Filtro_Siniestro'].isin(siniestro_sel)]
            filtros_activos = True
        if desc_sel: 
            df_filtrado_global = df_filtrado_global[df_filtrado_global[col_desc_univ].astype(str).isin(desc_sel)]
            filtros_activos = True

        st.markdown("---")
        
        if filtros_activos:
            st.markdown(f"**✅ {len(df_filtrado_global)} registro(s) encontrado(s)** con los filtros seleccionados.")
            
            col_aseg_exp = next((c for c in df_filtrado_global.columns if "ASEGURADORA" in str(c).upper()), None)
            col_vin_exp = next((c for c in df_filtrado_global.columns if "VIN" in str(c).upper() or "SERIE" in str(c).upper()), None)
            col_cant_exp = next((c for c in df_filtrado_global.columns if "CANT" in str(c).upper()), None)
            
            # --- PARCHE VIRTUAL PARA CANTIDAD ---
            if not col_cant_exp:
                df_filtrado_global['Cant.'] = "1"
                col_cant_exp = 'Cant.'
            # ------------------------------------

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
        else:
            st.info("👆 Selecciona al menos un filtro en la parte superior para mostrar resultados.")
    else:
        st.warning("La base de datos está vacía.")

elif vista_actual == "🛠️ Cuartel General":
    st.markdown("### 🛠️ Cuartel General PMR (Solo Administración)")
    st.info("Bienvenido a la sala de máquinas. Desde aquí controlaremos respaldos, reimpresiones y rutas locales.")
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.markdown("#### 🚧 Próximas Implementaciones (Mapa de Ruta):")
        st.checkbox("Bóveda de Reimpresión de PDFs en Drive", value=False, disabled=True)
        st.checkbox("Ruta de Escape Local (Offline DB)", value=False, disabled=True)
        st.checkbox("Pantalla de Ruta Local para Don Dionicio", value=False, disabled=True)
        st.checkbox("Módulo de Paquetería", value=False, disabled=True)
        st.caption("_Nota: Estas funciones se encuentran bloqueadas temporalmente ya que representan la bitácora de desarrollo a futuro._")
    with col_c2:
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
    
    col_id_univ = next((c for c in df_completo.columns if "SINIESTRO" in str(c).upper()), None)
    col_desc_univ = next((c for c in df_completo.columns if "DESCRIPCI" in str(c).upper() or "REFACCI" in str(c).upper()), None)
    col_taller_univ = next((c for c in df_completo.columns if "TALLER" in str(c).upper()), None)
    col_marca_univ = next((c for c in df_completo.columns if "MARCA" in str(c).upper()), None)
    col_modelo_univ = next((c for c in df_completo.columns if "MODELO" in str(c).upper()), None)
    col_cant_univ = next((c for c in df_completo.columns if "CANTIDAD" in str(c).upper() or "CANT" == str(c).upper()), None)
    
    originales = {}
    for _, r in df_completo.iterrows():
        k = generar_llave(r.get(col_id_univ, ''), r.get(col_desc_univ, ''))
        originales[k] = {
            'comentario': str(r.get(next((c for c in df_completo.columns if "COMENTARIO" in str(c).upper() or "OBSERVACION" in str(c).upper()), ''), '')).strip(),
            'guia': str(r.get(next((c for c in df_completo.columns if "GUIA" in str(c).upper() or "GUÍA" in str(c).upper()), ''), '')).strip(),
            'estatus_db': str(r.get(next((c for c in df_completo.columns if "ESTATUS" in str(c).upper() or "STATUS" in str(c).upper()), ''), '')).strip().upper(),
            'remision_bool': str(r.get(next((c for c in df_completo.columns if "REMISION" in str(c).upper() or "REMISIÓN" in str(c).upper()), ''), '')).strip() != '',
            'vencimiento_db': str(r.get(next((c for c in df_completo.columns if "VENCIMIENTO" in str(c).upper() or "PROMESA" in str(c).upper()), ''), '')).strip(),
            'asignacion_db': str(r.get(next((c for c in df_completo.columns if "ASIGNACI" in str(c).upper()), ''), '')).strip()
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

    if btn_guardar:
        if not df_editado_conf.empty:
            for _, row in df_editado_conf.iterrows():
                k = generar_llave(row.get(col_id, ''), row.get(col_desc, ''))
                orig = originales.get(k, {'comentario': '', 'estatus_db': ''})
                nuevo_estatus = "CANCELADO" if row.get('Cancelar') else ("EN PROCESAMIENTO" if row.get('Confirmar Surtido') else None)
                comentario_actual = str(row.get(col_comentarios, '')).strip()
                if nuevo_estatus and nuevo_estatus != orig['estatus_db']: 
                    cambios_a_guardar.setdefault(k, {})['estatus'] = nuevo_estatus
                    if nuevo_estatus == "EN PROCESAMIENTO": cambios_a_guardar[k]['fecha_confi'] = fecha_hoy_sistema
                if comentario_actual != orig['comentario']: cambios_a_guardar.setdefault(k, {})['comentario'] = comentario_actual

        if not df_editado_venc.empty:
            for _, row in df_editado_venc.iterrows():
                k = generar_llave(row.get(col_id, ''), row.get(col_desc, ''))
                orig = originales.get(k, {'comentario': '', 'guia': '', 'estatus_db': ''})
                nuevo_estatus = "CANCELADO" if row.get('Cancelar') else None
                comentario_actual = str(row.get(col_comentarios, '')).strip()
                guia_actual = str(row.get(col_guia, '')).strip()
                nueva_fecha = row.get('Nueva Fecha')
                if pd.notnull(nueva_fecha) and str(nueva_fecha).strip() not in ['', 'NaT', 'None']:
                    try: fecha_str = pd.to_datetime(nueva_fecha).strftime('%d/%b/%y')
                    except: fecha_str = str(nueva_fecha)
                    cambios_a_guardar.setdefault(k, {})['vencimiento'] = fecha_str
                    if not nuevo_estatus: nuevo_estatus = "EN PROCESAMIENTO"
                elif row.get('Reasignar') and not nuevo_estatus: nuevo_estatus = "REASIGNAR" 
                if nuevo_estatus and nuevo_estatus != orig['estatus_db']: cambios_a_guardar.setdefault(k, {})['estatus'] = nuevo_estatus
                if comentario_actual != orig['comentario']: cambios_a_guardar.setdefault(k, {})['comentario'] = comentario_actual
                if guia_actual != orig['guia']: cambios_a_guardar.setdefault(k, {})['guia'] = guia_actual

        if not df_editado_atrasadas.empty:
            for _, row in df_editado_atrasadas.iterrows():
                k = generar_llave(row.get(col_id, ''), row.get(col_desc, ''))
                orig = originales.get(k, {'comentario': '', 'estatus_db': ''})
                nuevo_estatus = "CANCELADO" if row.get('Cancelar') else None
                comentario_actual = str(row.get(col_comentarios, '')).strip()
                nueva_fecha = row.get('Nueva Fecha')
                if pd.notnull(nueva_fecha) and str(nueva_fecha).strip() not in ['', 'NaT', 'None']:
                    try: fecha_str = pd.to_datetime(nueva_fecha).strftime('%d/%b/%y')
                    except: fecha_str = str(nueva_fecha)
                    cambios_a_guardar.setdefault(k, {})['vencimiento'] = fecha_str
                    if not nuevo_estatus: nuevo_estatus = "EN PROCESAMIENTO"
                elif row.get('Reasignar') and not nuevo_estatus: nuevo_estatus = "REASIGNAR" 
                if nuevo_estatus and nuevo_estatus != orig['estatus_db']: cambios_a_guardar.setdefault(k, {})['estatus'] = nuevo_estatus
                if comentario_actual != orig['comentario']: cambios_a_guardar.setdefault(k, {})['comentario'] = comentario_actual

        if not df_editado_cobro.empty:
            for _, row in df_editado_cobro.iterrows():
                k = generar_llave(row.get(col_id, ''), row.get(col_desc, ''))
                orig = originales.get(k, {'comentario': '', 'estatus_db': ''})
                comentario_actual = str(row.get(col_comentarios, '')).strip()
                if row.get('Marcar Recibido'): 
                    cambios_a_guardar.setdefault(k, {})['estatus'] = "RECIBIDO"
                    cambios_a_guardar[k]['fecha_recibido'] = fecha_hoy_sistema
                if comentario_actual != orig['comentario']: cambios_a_guardar.setdefault(k, {})['comentario'] = comentario_actual

        if not df_editado_fact.empty:
            for _, row in df_editado_fact.iterrows():
                k = generar_llave(row.get(col_id, ''), row.get(col_desc, ''))
                if row.get('Facturado'): 
                    cambios_a_guardar.setdefault(k, {})['estatus'] = "FACTURADO"
                    cambios_a_guardar[k]['fecha_facturacion'] = fecha_hoy_sistema

        if not df_editado.empty:
            for _, row in df_editado.iterrows():
                k = generar_llave(row.get(col_id, ''), row.get(col_desc, ''))
                orig = originales.get(k, {'comentario': '', 'guia': '', 'estatus_db': '', 'remision_bool': False, 'vencimiento_db': '', 'asignacion_db': ''})
                
                # LÓGICA AUTOMÁTICA DE PEDIDO: Si hay un proveedor seleccionado, asumimos que ya es un pedido en procesamiento
                prov_asignado = str(row.get('Proveedor', '')).strip()
                pedido_bool = True if prov_asignado != '' else False
                
                nuevo_estatus = "CANCELADO" if row.get('Cancelar') else "REASIGNAR" if row.get('Reasignacion') else "RECIBIDO" if row.get('Recibido') else "ENTREGADO" if row.get('Entregado') else "EN PROCESAMIENTO" if pedido_bool else None
                comentario_actual = str(row.get(col_comentarios, '')).strip()
                guia_actual = str(row.get(col_guia, '')).strip()
                venc_actual = str(row.get(col_vencimiento, '')).strip()
                asig_actual = str(row.get(col_asignacion, '')).strip()
                
                if nuevo_estatus and nuevo_estatus != orig['estatus_db']: 
                    cambios_a_guardar.setdefault(k, {})['estatus'] = nuevo_estatus
                    if nuevo_estatus == "RECIBIDO": cambios_a_guardar[k]['fecha_recibido'] = fecha_hoy_sistema
                if comentario_actual != orig['comentario']: cambios_a_guardar.setdefault(k, {})['comentario'] = comentario_actual
                if guia_actual != orig['guia']: cambios_a_guardar.setdefault(k, {})['guia'] = guia_actual
                if venc_actual and venc_actual != orig['vencimiento_db']: cambios_a_guardar.setdefault(k, {})['vencimiento'] = venc_actual
                if asig_actual and asig_actual != orig['asignacion_db']: cambios_a_guardar.setdefault(k, {})['asignacion'] = asig_actual
                
                if pedido_bool and nuevo_estatus != "CANCELADO":
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
                    orig = originales.get(k, {'estatus_db': '', 'remision_bool': False})
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
            with st.spinner("Sincronizando..."):
                try:
                    doc = init_connection()
                    if cambios_a_guardar:
                        ws_uni = doc.worksheet("BD_UNIFICADA")
                        datos_uni = ws_uni.get_all_values()
                        headers = [str(h).strip() for h in datos_uni[0]]
                        idx_id, idx_desc, idx_estatus, idx_rem = headers.index(col_id_univ), headers.index(col_desc_univ), headers.index(next((c for c in df_completo.columns if "ESTATUS" in str(c).upper() or "STATUS" in str(c).upper()), '')), headers.index(next((c for c in df_completo.columns if "REMISION" in str(c).upper() or "REMISIÓN" in str(c).upper()), ''))
                        idx_usr_rem = headers.index("Usuario Remisión") if "Usuario Remisión" in headers else -1
                        idx_coment = headers.index(next((c for c in df_completo.columns if "COMENTARIO" in str(c).upper() or "OBSERVACION" in str(c).upper()), '')) if next((c for c in df_completo.columns if "COMENTARIO" in str(c).upper() or "OBSERVACION" in str(c).upper()), '') in headers else -1
                        idx_guia = headers.index(next((c for c in df_completo.columns if "GUIA" in str(c).upper() or "GUÍA" in str(c).upper()), '')) if next((c for c in df_completo.columns if "GUIA" in str(c).upper() or "GUÍA" in str(c).upper()), '') in headers else -1
                        idx_venc = headers.index(next((c for c in df_completo.columns if "VENCIMIENTO" in str(c).upper() or "PROMESA" in str(c).upper()), '')) if next((c for c in df_completo.columns if "VENCIMIENTO" in str(c).upper() or "PROMESA" in str(c).upper()), '') in headers else -1
                        idx_asig = headers.index(next((c for c in df_completo.columns if "ASIGNACI" in str(c).upper()), '')) if next((c for c in df_completo.columns if "ASIGNACI" in str(c).upper()), '') in headers else -1
                        idx_confi = headers.index(next((c for c in df_completo.columns if "FECHA CONFI" in str(c).upper()), '')) if next((c for c in df_completo.columns if "FECHA CONFI" in str(c).upper()), '') in headers else -1
                        idx_envio = headers.index("Fecha Envío") if "Fecha Envío" in headers else -1
                        idx_recibido = headers.index("Fecha Recibido") if "Fecha Recibido" in headers else -1
                        idx_facturacion = headers.index("Fecha Facturación") if "Fecha Facturación" in headers else -1
                        
                        max_folio_pmr = 0
                        numeros = df_completo[next((c for c in df_completo.columns if "REMISION" in str(c).upper() or "REMISIÓN" in str(c).upper()), '')].astype(str).str.extract(r'(?i)PMR\s*-\s*0*(\d+)', expand=False)
                        if not numeros.empty: max_folio_pmr = int(pd.to_numeric(numeros, errors='coerce').max() if pd.notna(pd.to_numeric(numeros, errors='coerce').max()) else 0)

                        folios_asignados_en_sesion = {}
                        for k, v in cambios_a_guardar.items():
                            if v.get('generar_nuevo_folio'):
                                siniestro_id = k[0] 
                                if siniestro_id not in folios_asignados_en_sesion:
                                    max_folio_pmr += 1
                                    folios_asignados_en_sesion[siniestro_id] = f"PMR - {max_folio_pmr:03d}"
                                v['remision_num'] = folios_asignados_en_sesion[siniestro_id]

                        for i in range(1, len(datos_uni)):
                            k = generar_llave(datos_uni[i][idx_id], datos_uni[i][idx_desc])
                            if k in cambios_a_guardar:
                                c = cambios_a_guardar[k]
                                if 'estatus' in c: datos_uni[i][idx_estatus] = c['estatus']
                                if 'remision_num' in c: datos_uni[i][idx_rem] = c['remision_num']
                                if 'usuario_rem' in c and idx_usr_rem >= 0: datos_uni[i][idx_usr_rem] = c['usuario_rem']
                                if 'comentario' in c and idx_coment >= 0: datos_uni[i][idx_coment] = c['comentario']
                                if 'guia' in c and idx_guia >= 0: datos_uni[i][idx_guia] = c['guia']
                                if 'vencimiento' in c and idx_venc >= 0: datos_uni[i][idx_venc] = c['vencimiento']
                                if 'asignacion' in c and idx_asig >= 0: datos_uni[i][idx_asig] = c['asignacion']
                                if 'fecha_confi' in c and idx_confi >= 0: datos_uni[i][idx_confi] = c['fecha_confi']
                                if 'fecha_envio' in c and idx_envio >= 0: datos_uni[i][idx_envio] = c['fecha_envio']
                                if 'fecha_recibido' in c and idx_recibido >= 0: datos_uni[i][idx_recibido] = c['fecha_recibido']
                                if 'fecha_facturacion' in c and idx_facturacion >= 0: datos_uni[i][idx_facturacion] = c['fecha_facturacion']
                        ws_uni.update(range_name='A1', values=datos_uni, value_input_option='USER_ENTERED')

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
                                
                                # 1. Actualizaciones desde la pestaña COMPRAS
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
                                
                                # 2. Actualizaciones desde el PANEL OPERATIVO (Para piezas que ya existían en Compras)
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
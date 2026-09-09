# === [BLOQUE 1: IMPORTS, CONFIGURACIÓN VISUAL Y CSS] ===
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
from google.oauth2.service_account import Credentials

warnings.filterwarnings("ignore")

st.set_page_config(
    page_title="Dashboard PMR - Operación",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
        [data-testid="stDataFrame"] { zoom: 0.95; }
        .block-container { 
            padding-top: 2rem; 
            padding-bottom: 40px; 
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            max-width: 100% !important; 
        }
        @media (min-width: 768px) {
            div.element-container:has(#panel-fijo) + div {
                position: sticky; top: 2.875rem; z-index: 999;
                background-color: #0e1117; padding-top: 15px; padding-bottom: 10px;
                border-bottom: 1px solid #333; margin-bottom: 15px;
            }
        }
        div[role="radiogroup"] { display: flex; justify-content: center; gap: 15px; flex-wrap: wrap; }
        div[data-testid="stRadio"] div[role="radiogroup"] label {
            padding: 5px 15px !important; border-radius: 8px !important; background-color: #1e1e1e;
            border: 1px solid #333; transition: all 0.3s ease; cursor: pointer;
        }
        div[data-testid="stRadio"] div[role="radiogroup"] label:hover { background-color: #3b3b3b; }
        div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) {
            background-color: #ff4b4b !important; border-color: #ff4b4b !important;
            box-shadow: 0 0 10px rgba(255, 75, 75, 0.4);
        }
        div[data-testid="stRadio"] div[role="radiogroup"] label p { color: white !important; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# =====================================================================
# === [BLOQUE 0: CONEXIÓN TEMPRANA Y SISTEMA DE LOGIN] ===
# =====================================================================
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

# =====================================================================
# === MOTOR DE PERMISOS DINÁMICO (ROLES + VISTA ACTUAL) ===
# =====================================================================
usuario_activo = str(st.session_state.get('usuario_actual', '')).strip().upper()
rol_activo = str(st.session_state.get('rol_actual', '')).strip().upper()

# =====================================================================
# === [BLOQUE 2: MENÚ LATERAL Y HEADER PRINCIPAL] ===
with st.sidebar:
    rol_usuario = str(st.session_state.get('rol', st.session_state.get('rol_actual', 'Visor')))
    nombre_usuario = str(st.session_state.get('usuario_actual', 'Demo'))
    
    if "VISOR" in nombre_usuario.upper() or "DEMO" in str(st.session_state.get('usuario', '')).upper():
        rol_usuario = "Visor"

    st.success(f"👤 Operador activo: {nombre_usuario}\n\n🛡️ Rol: {rol_usuario}")
    st.markdown("---")
    st.markdown("🧭 **Navegación**")
    # Cambio de nombre de la pestaña a "Compras"
    vista_actual = st.radio("Navegación", ["📊 Analítico", "⚙️ Panel Operativo", "🛒 Compras", "🏢 Talleres", "📦 Inventario", "🧾 Facturación"], label_visibility="collapsed")
    st.markdown("---")
    if st.button("🚪 Cerrar Sesión"):
        st.session_state.clear()
        st.rerun()

st.markdown('<div id="panel-fijo"></div>', unsafe_allow_html=True)

col_logo, col_tit, col_ctrl = st.columns([1.5, 4, 3])
with col_logo:
    if os.path.exists("logo.png"): st.image("logo.png", width=130)

with col_ctrl:
    aseguradora_sel = st.selectbox("🛡️ Aseguradora:", ["Multiasistencias", "GNP"], label_visibility="collapsed")
    col_btn, col_chk = st.columns([1.2, 1])
    es_visor = "VISOR" in rol_usuario.upper()
    
    with col_chk:
        modo_consulta = st.checkbox("Modo Lectura", value=True if es_visor else False, disabled=es_visor)
    permiso_edicion = not modo_consulta
    
    with col_btn:
        btn_guardar = st.button("💾 Guardar Cambios", use_container_width=True, type="primary", disabled=not permiso_edicion)

with col_tit:
    color_aseg = "#00FF00" if aseguradora_sel == "Multiasistencias" else "#00529B"
    st.markdown(f"<h2 style='margin-bottom: 0;'>PMR - {vista_actual.split(' ')[0]} {vista_actual.split(' ', 1)[1]} | <span style='color: {color_aseg}; font-weight: bold;'>🛡️ {aseguradora_sel}</span></h2>", unsafe_allow_html=True)
    
# --- NUEVO SISTEMA NATIVO DE DESCARGA DE PDFS ---
if st.session_state.get('pdfs_list') or st.session_state.get('avisos_remision'):
    st.markdown("### 🖨️ Avisos y Remisiones")
    for aviso in st.session_state.get('avisos_remision', []):
        st.warning(aviso)
    
    if st.session_state.get('pdfs_list'):
        cols_pdf = st.columns(len(st.session_state['pdfs_list']) + 1)
        for i, pdf_obj in enumerate(st.session_state['pdfs_list']):
            with cols_pdf[i]:
                st.download_button(
                    label=f"📥 {pdf_obj['folio']}\n({pdf_obj['siniestro']})",
                    data=pdf_obj['bytes'],
                    file_name=pdf_obj['nombre'],
                    mime="application/pdf",
                    key=f"btn_pdf_dl_{i}"
                )
        with cols_pdf[-1]:
            if st.button("✅ Limpiar Avisos", type="primary"):
                st.session_state['pdfs_list'] = []
                st.session_state['avisos_remision'] = []
                st.rerun()
    st.markdown("---")
else:
    st.markdown("---")

# =====================================================================
# === [BLOQUE 3: CARGA Y PROCESAMIENTO DE DATOS] ===
def obtener_dataframe(nombre_hoja):
    try:
        doc = init_connection()
        ws = doc.worksheet(nombre_hoja)
        datos = ws.get_all_values()
        if not datos: return pd.DataFrame()
        headers = [str(h).strip() for h in datos[0]]
        for i in range(len(headers)):
            if headers[i] == "": headers[i] = f"Unnamed_{i}"
        return pd.DataFrame(datos[1:], columns=headers)
    except Exception as e:
        st.error(f"Error cargando hoja {nombre_hoja}: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def cargar_datos(): return obtener_dataframe("BD_UNIFICADA")
@st.cache_data(ttl=60)
def cargar_catalogo(): return obtener_dataframe("Catálogo")
@st.cache_data(ttl=60)
def cargar_compras(): return obtener_dataframe("BD_COMPRAS")
@st.cache_data(ttl=60)
def cargar_inventario():
    df_inv = obtener_dataframe("BD_INVENTARIO")
    if not df_inv.empty: df_inv = df_inv.dropna(how='all')
    return df_inv
@st.cache_data(ttl=60)
def cargar_placas(): return obtener_dataframe("BD_PLACAS")

df_completo = cargar_datos()
df_catalogo = cargar_catalogo()
df_compras = cargar_compras()
df_inventario = cargar_inventario()
df_placas = cargar_placas() 

df_proceso = pd.DataFrame()
df_trabajo = pd.DataFrame()
df_trabajo_completo = pd.DataFrame()
df_recoleccion_total = pd.DataFrame()
df_vista = pd.DataFrame()

df_editado_conf = pd.DataFrame()
df_editado_venc = pd.DataFrame()
df_editado_atrasadas = pd.DataFrame()
df_editado_cobro = pd.DataFrame()
df_editado = pd.DataFrame()
df_editado_compras = pd.DataFrame()
df_editado_catalogo = pd.DataFrame()
df_editado_inventario = pd.DataFrame()
df_editado_fact = pd.DataFrame() 

col_id = col_taller = col_marca = col_modelo = col_anio = col_serie = col_desc = col_estatus = col_precio = col_cant = col_asignacion = col_vencimiento = col_fecha_confi = col_remision = col_comentarios = col_guia = col_origen = col_aseg = None

if not df_completo.empty:
    col_aseg = next((c for c in df_completo.columns if "ASEGURADORA" in str(c).upper()), None)
    if col_aseg:
        if aseguradora_sel == "GNP":
            df_vista = df_completo[df_completo[col_aseg].astype(str).str.upper().str.contains("GNP")].copy()
        else:
            df_vista = df_completo[df_completo[col_aseg].astype(str).str.upper().str.contains("MULTI")].copy()
    else:
        df_vista = df_completo.copy()

if not df_vista.empty:
    cols = df_vista.columns.tolist()
    def obtener_col(substrings):
        for c in cols:
            c_upper = str(c).upper()
            if any(s in c_upper for s in substrings) and "DÍAS" not in c_upper and "DIAS" not in c_upper: return c
        return None
        
    col_id = obtener_col(["PEDIDO", "SINIESTRO", "ID PRINCIPAL"]) 
    col_taller = obtener_col(["TALLER"])
    col_marca = obtener_col(["MARCA"])
    col_modelo = obtener_col(["MODELO"])
    col_anio = obtener_col(["AÑO", "ANO", "YEAR"])
    col_serie = obtener_col(["SERIE", "VIN"])
    col_desc = obtener_col(["DESCRIPCI"])
    col_estatus = obtener_col(["ESTATUS"])
    col_precio = obtener_col(["PRECIO"])
    col_cant = obtener_col(["CANT"])
    col_asignacion = obtener_col(["ASIGNA"])
    col_vencimiento = obtener_col(["VENCIMIENTO"])
    col_fecha_confi = obtener_col(["CONFI"])
    col_remision = obtener_col(["REMISI"]) 
    col_comentarios = obtener_col(["COMENTARIO", "OBSERVACION"])
    col_guia = obtener_col(["GUIA", "GUÍA", "RASTREO"])
    col_origen = obtener_col(["ORIGEN", "TIPO PIEZA", "NUEVO"])
    
    columnas_base = [c for c in [col_id, col_taller, col_marca, col_modelo, col_anio, col_serie, col_desc, col_precio, col_cant, col_remision, col_asignacion, col_vencimiento, col_fecha_confi, col_estatus, col_comentarios, col_guia, col_aseg, col_origen] if c is not None]
    
    if columnas_base:
        df_trabajo_completo = df_completo[columnas_base].copy()
        df_trabajo = df_vista[columnas_base].copy()             
        df_trabajo = df_trabajo[df_trabajo[col_id].notna() & (df_trabajo[col_id].astype(str).str.strip() != '') & (df_trabajo[col_id].astype(str).str.lower() != 'nan')]
        
        if col_precio and col_precio in df_trabajo.columns:
            df_trabajo[col_precio] = pd.to_numeric(df_trabajo[col_precio].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce').fillna(0)
            df_trabajo_completo[col_precio] = pd.to_numeric(df_trabajo_completo[col_precio].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce').fillna(0)

        def parse_fecha_segura(val):
            if pd.isna(val) or str(val).strip() == '': return ''
            v_str = str(val).strip()
            if v_str.startswith("'"): v_str = v_str[1:] 
            try: return pd.to_datetime(v_str, dayfirst=True).strftime('%d/%b/%y')
            except:
                try: return pd.to_datetime(v_str).strftime('%d/%b/%y')
                except: return v_str 

        for c_fecha in [col_asignacion, col_vencimiento, col_fecha_confi]:
            if c_fecha and c_fecha in df_trabajo.columns:
                df_trabajo[c_fecha] = df_trabajo[c_fecha].apply(parse_fecha_segura)
                
        for c_txt in [col_remision, col_comentarios, col_estatus, col_guia, col_origen]:
            if c_txt and c_txt in df_trabajo.columns:
                df_trabajo[c_txt] = df_trabajo[c_txt].fillna('').astype(str).replace(['nan', 'None'], '')
                
        if col_guia not in df_trabajo.columns:
            df_trabajo['Guía'] = ""
            col_guia = 'Guía'
            
        def limpiar_guia_display(g):
            g = str(g).strip()
            if g.startswith('=HYPERLINK'): g = g.split(',')[-1].replace('"', '').replace(')', '').strip()
            if g.endswith('.0'): g = g[:-2]
            return '' if g.lower() in ['nan', 'none'] else g

        if col_guia and col_guia in df_trabajo.columns:
            df_trabajo[col_guia] = df_trabajo[col_guia].apply(limpiar_guia_display)
        
        if col_estatus:
            if modo_consulta:
                df_proceso = df_trabajo.copy()
            else:
                estatus_excluidos = ['RECIBIDO', 'FACTURADO', 'CANCELADO', 'CANCELO KARLA', 'RECOLECCION', 'REASIGNAR']
                df_proceso = df_trabajo[~df_trabajo[col_estatus].astype(str).str.strip().str.upper().isin(estatus_excluidos)].copy()
        else:
            df_proceso = df_trabajo.copy()
            
        def limpiar_siniestro(val):
            val_str = str(val).strip()
            return val_str[:-2] if val_str.endswith('.0') else val_str

        if col_id:
            df_proceso['Siniestro'] = df_proceso[col_id].apply(limpiar_siniestro)
            df_trabajo_completo['Siniestro'] = df_trabajo_completo[col_id].apply(limpiar_siniestro)
        else: df_proceso['Siniestro'] = ""

        def formatear_vehiculo(row):
            vehiculo = f"{row.get(col_marca, '')} {row.get(col_modelo, '')}".strip()
            anio = ""
            if col_anio and pd.notnull(row.get(col_anio)):
                try: anio = str(int(float(row[col_anio])))
                except ValueError: anio = str(row[col_anio]).strip()
            if anio and anio.lower() not in ['nan', 'none', '']: vehiculo += f" {anio}"
            serie = str(row.get(col_serie, '')).strip() if col_serie else ""
            if serie and serie.lower() not in ['nan', 'none', '']: vehiculo += f" - {serie}"
            return vehiculo

        df_proceso['Vehiculo_Info'] = df_proceso.apply(formatear_vehiculo, axis=1)
        df_proceso['Filtro_Siniestro'] = df_proceso.apply(lambda row: f"{row['Siniestro']} - {row['Vehiculo_Info']}", axis=1)
        df_trabajo_completo['Vehiculo_Info'] = df_trabajo_completo.apply(formatear_vehiculo, axis=1)

        df_recoleccion_total = df_trabajo[df_trabajo[col_estatus].str.contains('RECOLECCI', case=False, na=False)] if col_estatus else pd.DataFrame()
        if 'Siniestro' not in df_recoleccion_total.columns and col_id in df_recoleccion_total.columns:
             df_recoleccion_total['Siniestro'] = df_recoleccion_total[col_id].apply(limpiar_siniestro)
        if 'Vehiculo_Info' not in df_recoleccion_total.columns:
             df_recoleccion_total['Vehiculo_Info'] = df_recoleccion_total.apply(formatear_vehiculo, axis=1)

if not df_compras.empty:
    if 'Recibido' not in df_compras.columns: df_compras['Recibido'] = False
    else: df_compras['Recibido'] = df_compras['Recibido'].astype(str).str.strip().str.upper().isin(['TRUE', 'SI', '1', 'YES', 'V', 'X'])

if not df_inventario.empty:
    if 'Sin Existencia' not in df_inventario.columns: df_inventario['Sin Existencia'] = False
    else: df_inventario['Sin Existencia'] = df_inventario['Sin Existencia'].astype(str).str.strip().str.upper().isin(['TRUE', 'SI', '1', 'YES', 'V', 'X'])


# === [BLOQUE 4: VISTAS] ===
# Blindaje: Inicializamos variables vacías para evitar NameErrors si cambiamos de pestaña
df_editado_conf = pd.DataFrame()
df_editado_venc = pd.DataFrame()
df_editado_atrasadas = pd.DataFrame()
df_editado_cobro = pd.DataFrame()
df_editado_fact = pd.DataFrame()
df_editado = pd.DataFrame()

if vista_actual == "📊 Analítico":
    st.markdown("## 📊 Rendimiento de Operación")
    
    st.markdown("#### 1. Estado General de Partidas en Proceso")
    if col_estatus and col_vencimiento and not df_proceso.empty:
        df_grafico = df_proceso.copy()
        df_agrupado = df_grafico.groupby([col_vencimiento, col_estatus]).size().reset_index(name='Cantidad')
        fig = px.bar(df_agrupado, x=col_vencimiento, y='Cantidad', color=col_estatus, barmode='stack', color_discrete_sequence=["#1E88E5", "#64B5F6", "#0D47A1", "#1976D2", "#90CAF9"])
        col_graf, col_det = st.columns([2, 1])
        with col_graf:
            graf_sel = st.plotly_chart(fig, use_container_width=True, on_select="rerun")
        with col_det:
            st.markdown("📄 **Detalle de Partidas**")
            if graf_sel and len(graf_sel.selection.points) > 0:
                fecha_sel = graf_sel.selection.points[0]["x"]
                df_detalle = df_grafico[df_grafico[col_vencimiento] == fecha_sel]
                st.dataframe(df_detalle[['Siniestro', col_taller, col_estatus]], use_container_width=True, hide_index=True)
            else:
                st.info("👆 Haz clic en una barra para filtrar la tabla.")
    else:
        st.warning("No hay partidas en proceso para graficar.")

    st.markdown("---")
    st.markdown("#### 2. Pedidos por Llegar (Compras a Proveedores)")
    if not df_compras.empty:
        df_compras['Recibido_Bool'] = df_compras['Recibido'].astype(str).str.strip().str.upper().isin(['TRUE', 'SI', '1', 'YES', 'V', 'X'])
        df_compras_llegar = df_compras[df_compras['Recibido_Bool'] == False].copy()
        if not df_compras_llegar.empty:
            def parse_spanish_date(d_str):
                if not isinstance(d_str, str): return pd.NaT
                d_str = d_str.lower().replace('-', '/') 
                meses = {'ene':'01', 'feb':'02', 'mar':'03', 'abr':'04', 'may':'05', 'jun':'06', 'jul':'07', 'ago':'08', 'sep':'09', 'oct':'10', 'nov':'11', 'dic':'12'}
                for text, num in meses.items():
                    if text in d_str:
                        d_str = d_str.replace(text, num)
                        break
                try: return pd.to_datetime(d_str, format='%d/%m/%y', errors='coerce')
                except: return pd.NaT

            df_compras_llegar['Fecha_Compra_Dt'] = df_compras_llegar['Fecha Compra'].apply(parse_spanish_date)
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

        col_envio = find_col(df_t, ["FECHA", "ENVIO"])
        col_recibido = find_col(df_t, ["FECHA", "RECIB"])
        col_fact = find_col(df_t, ["FECHA", "FACTUR"])
        
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
        
        prom_1 = get_promedio(df_t['Dias_Asig_Conf'])
        prom_2 = get_promedio(df_t['Dias_Conf_Env'])
        prom_3 = get_promedio(df_t['Dias_Env_Rec'])
        prom_4 = get_promedio(df_t['Dias_Rec_Fact'])
        
        etapas = ['Asignación ➔ Confirmación', 'Confirmación ➔ Envío', 'Envío ➔ Recibido', 'Recibido ➔ Facturación']
        valores = [prom_1, prom_2, prom_3, prom_4]
        
        fig_tiempos = px.bar(x=valores, y=etapas, orientation='h', text=valores, 
                             labels={'x': 'Días Promedio', 'y': ''}, 
                             color=etapas, color_discrete_sequence=["#FF9800", "#2196F3", "#4CAF50", "#9C27B0"])
        fig_tiempos.update_traces(textposition='auto', showlegend=False)
        fig_tiempos.update_layout(xaxis_title="Días Promedio", yaxis_title="")
        st.plotly_chart(fig_tiempos, use_container_width=True)
        
        st.caption("💡 *Si alguna etapa marca 0, significa que los datos aún se están recopilando.*")

elif vista_actual == "⚙️ Panel Operativo":
    st.markdown("### 📈 Indicadores Diarios")
    hoy_str = datetime.datetime.now().strftime('%d/%b/%y')
    hoy_dt = pd.to_datetime(datetime.datetime.now().date())
    
    def parse_dt_safe(val):
        try: return pd.to_datetime(val, dayfirst=True)
        except: return pd.NaT

    if col_vencimiento:
        fechas_venc_dt = df_proceso[col_vencimiento].apply(parse_dt_safe)
        vencidas_pasadas_kpi = len(df_proceso[(fechas_venc_dt < hoy_dt) & (df_proceso[col_vencimiento] != '') & (~df_proceso[col_estatus].astype(str).str.upper().str.contains("CONFIRMAR"))])
    else: vencidas_pasadas_kpi = 0
        
    vencen_hoy = len(df_proceso[df_proceso[col_vencimiento] == hoy_str]) if col_vencimiento else 0
    recolecciones = len(df_recoleccion_total)
    por_confirmar_kpi = len(df_proceso[df_proceso[col_estatus].astype(str).str.upper().str.contains("CONFIRMAR")]) if col_estatus else 0
    en_proceso = len(df_proceso[~df_proceso[col_estatus].astype(str).str.upper().str.contains("CONFIRMAR")]) if col_estatus else len(df_proceso)
    partidas_por_facturar = len(df_trabajo[df_trabajo[col_estatus].astype(str).str.strip().str.upper() == "RECIBIDO"]) if col_estatus else 0
    
    kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)
    kpi1.metric("📦 En Proceso (CDR)", en_proceso)
    kpi2.metric("⏳ Por Confirmar", por_confirmar_kpi)
    kpi3.metric("⚠️ Vencen Hoy", vencen_hoy)
    kpi4.metric("❌ Vencidos", vencidas_pasadas_kpi)
    kpi5.metric("↩️ En Recolección", recolecciones)
    kpi6.metric("🧾 Por Facturar", partidas_por_facturar)

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
    if 'Siniestro' in df_filtrado.columns: base_config['Siniestro'] = st.column_config.TextColumn("Siniestro")
    if 'Vehiculo_Info' in df_filtrado.columns: base_config['Vehiculo_Info'] = st.column_config.TextColumn("Vehículo")
    if col_taller: base_config[col_taller] = st.column_config.TextColumn("Taller", width="small")
    if col_asignacion: base_config[col_asignacion] = st.column_config.TextColumn("Asig.", width="small")
    if col_fecha_confi: base_config[col_fecha_confi] = st.column_config.TextColumn("Conf.", width="small")
    if col_cant: base_config[col_cant] = st.column_config.TextColumn("Cant", width="small")
    if col_desc: base_config[col_desc] = st.column_config.TextColumn("Descrip.") 
    if col_precio: base_config[col_precio] = st.column_config.TextColumn("Precio", width="small")
    if col_estatus: base_config[col_estatus] = st.column_config.TextColumn("Estatus", width="small")
    if col_vencimiento: base_config[col_vencimiento] = st.column_config.TextColumn("Venc.", width="small")
    if col_guia: base_config[col_guia] = st.column_config.TextColumn("Guía", width="small")
    if col_remision: base_config[col_remision] = st.column_config.TextColumn("Folio Remisión", width="small")
    if col_comentarios: base_config[col_comentarios] = st.column_config.TextColumn("Obs.") 

    # --- PIEZAS POR CONFIRMAR AGRUPADAS (Corregido y blindado) ---
    df_por_confirmar = df_filtrado[df_filtrado[col_estatus].astype(str).str.upper().str.contains("CONFIRMAR")].copy() if col_estatus else pd.DataFrame()
    with st.expander(f"⏳ Piezas por Confirmar | {df_por_confirmar['Siniestro'].nunique() if not df_por_confirmar.empty else 0} Siniestros", expanded=False):
        dfs_editados_conf = []
        if not df_por_confirmar.empty:
            for taller, df_taller in df_por_confirmar.groupby(col_taller):
                with st.expander(f"🏢 {taller} | {df_taller['Siniestro'].nunique()} Siniestro(s)", expanded=False):
                    for siniestro_auto, df_grupo in df_taller.groupby('Siniestro'):
                        st.markdown(f"**🚗 {siniestro_auto} | {df_grupo['Vehiculo_Info'].iloc[0]}**")
                        if not modo_consulta and permiso_edicion: 
                            df_grupo['Confirmar Surtido'] = False
                            df_grupo['Cancelar'] = False
                            cols_conf = [c for c in [col_cant, col_desc, col_asignacion, col_vencimiento, col_estatus, col_comentarios, 'Confirmar Surtido', 'Cancelar'] if c in df_grupo.columns]
                            config_conf = base_config.copy()
                            config_conf.update({"Confirmar Surtido": st.column_config.CheckboxColumn("✅ Confirmar", default=False), "Cancelar": st.column_config.CheckboxColumn("🚫 Can", default=False)})
                            
                            df_editado_parcial = st.data_editor(df_grupo[cols_conf], column_config=config_conf, disabled=[c for c in cols_conf if c not in ['Confirmar Surtido', 'Cancelar', col_comentarios]], hide_index=True, use_container_width=True, key=f"ed_conf_{taller}_{siniestro_auto}")
                            
                            for col in [col_id, col_taller, col_marca, col_modelo, col_desc, 'Siniestro']:
                                if col in df_grupo.columns: df_editado_parcial[col] = df_grupo[col].values
                            dfs_editados_conf.append(df_editado_parcial)
                        else:
                            cols_conf = [c for c in [col_cant, col_desc, col_asignacion, col_vencimiento, col_estatus, col_comentarios] if c in df_grupo.columns]
                            st.dataframe(df_grupo[cols_conf], column_config=base_config, hide_index=True, use_container_width=True)
        if dfs_editados_conf: df_editado_conf = pd.concat(dfs_editados_conf, ignore_index=True)

    df_vencimientos = df_filtrado[(df_filtrado[col_vencimiento] == hoy_str) & (~df_filtrado[col_estatus].astype(str).str.upper().str.contains("CONFIRMAR"))].copy() if col_vencimiento else pd.DataFrame()
    with st.expander(f"🚨 Vencimientos de Hoy | {df_vencimientos['Siniestro'].nunique() if not df_vencimientos.empty else 0} Siniestros", expanded=False):
        if not df_vencimientos.empty:
            if not modo_consulta and permiso_edicion:
                df_vencimientos['Cancelar'] = False; df_vencimientos['Reasignar'] = False; df_vencimientos['Nueva Fecha'] = pd.NaT
                cols_venc = [c for c in [col_taller, 'Siniestro', 'Vehiculo_Info', col_cant, col_desc, col_precio, col_estatus, col_vencimiento, col_guia, col_comentarios, 'Cancelar', 'Reasignar', 'Nueva Fecha'] if c in df_vencimientos.columns]
                config_venc = base_config.copy()
                config_venc.update({"Cancelar": st.column_config.CheckboxColumn("🚫 Can", default=False), "Reasignar": st.column_config.CheckboxColumn("🔄 Reasig", default=False), "Nueva Fecha": st.column_config.DateColumn("📅 Nueva Fecha", format="DD/MMM/YYYY")})
                df_editado_venc = st.data_editor(df_vencimientos[cols_venc], column_config=config_venc, disabled=[c for c in cols_venc if c not in ['Cancelar', 'Reasignar', 'Nueva Fecha', col_comentarios, col_guia]], hide_index=True, use_container_width=True, key="ed_venc")
                for col in [col_id, col_marca, col_modelo]:
                    if col in df_vencimientos.columns: df_editado_venc[col] = df_vencimientos[col].values
            else:
                cols_venc = [c for c in [col_taller, 'Siniestro', 'Vehiculo_Info', col_cant, col_desc, col_precio, col_estatus, col_vencimiento, col_guia, col_comentarios] if c in df_vencimientos.columns]
                st.dataframe(df_vencimientos[cols_venc], column_config=base_config, hide_index=True, use_container_width=True)
                
    if col_vencimiento and not df_filtrado.empty:
        fechas_venc_filtro = df_filtrado[col_vencimiento].apply(parse_dt_safe)
        df_atrasadas = df_filtrado[(fechas_venc_filtro < hoy_dt) & (df_filtrado[col_vencimiento] != '') & (~df_filtrado[col_estatus].astype(str).str.upper().str.contains("CONFIRMAR"))].copy()
    else:
        df_atrasadas = pd.DataFrame()
    with st.expander(f"❌ Vencimientos Atrasados (Pendientes) | {df_atrasadas['Siniestro'].nunique() if not df_atrasadas.empty else 0} Siniestros", expanded=False):
        if not df_atrasadas.empty:
            if not modo_consulta and permiso_edicion:
                df_atrasadas['Cancelar'] = False; df_atrasadas['Reasignar'] = False; df_atrasadas['Nueva Fecha'] = pd.NaT
                cols_atr = [c for c in [col_taller, 'Siniestro', 'Vehiculo_Info', col_cant, col_desc, col_precio, col_estatus, col_vencimiento, col_comentarios, 'Cancelar', 'Reasignar', 'Nueva Fecha'] if c in df_atrasadas.columns]
                config_atr = base_config.copy()
                config_atr.update({"Cancelar": st.column_config.CheckboxColumn("🚫 Can", default=False), "Reasignar": st.column_config.CheckboxColumn("🔄 Reasig", default=False), "Nueva Fecha": st.column_config.DateColumn("📅 Nueva Fecha", format="DD/MMM/YYYY")})
                df_editado_atrasadas = st.data_editor(df_atrasadas[cols_atr], column_config=config_atr, disabled=[c for c in cols_atr if c not in ['Cancelar', 'Reasignar', 'Nueva Fecha', col_comentarios]], hide_index=True, use_container_width=True, key="ed_atr")
                for col in [col_id, col_marca, col_modelo]:
                    if col in df_atrasadas.columns: df_editado_atrasadas[col] = df_atrasadas[col].values
            else:
                cols_atr = [c for c in [col_taller, 'Siniestro', 'Vehiculo_Info', col_cant, col_desc, col_precio, col_estatus, col_vencimiento, col_comentarios] if c in df_atrasadas.columns]
                st.dataframe(df_atrasadas[cols_atr], column_config=base_config, hide_index=True, use_container_width=True)

    df_por_cobrar = df_filtrado[df_filtrado[col_estatus].astype(str).str.upper() == "ENTREGADO"].copy() if col_estatus else pd.DataFrame()
    with st.expander(f"💰 Por Cobrar (Entregados) | {df_por_cobrar['Siniestro'].nunique() if not df_por_cobrar.empty else 0} Siniestros", expanded=False):
        if not df_por_cobrar.empty:
            if not modo_consulta and permiso_edicion:
                df_por_cobrar['Marcar Recibido'] = False
                cols_cobro = [c for c in [col_taller, 'Siniestro', 'Vehiculo_Info', col_cant, col_desc, col_precio, col_estatus, col_comentarios, 'Marcar Recibido'] if c in df_por_cobrar.columns]
                config_cobro = base_config.copy()
                config_cobro.update({"Marcar Recibido": st.column_config.CheckboxColumn("🏁 Marcar Recibido", default=False)})
                df_editado_cobro = st.data_editor(df_por_cobrar[cols_cobro], column_config=config_cobro, disabled=[c for c in cols_cobro if c not in ['Marcar Recibido', col_comentarios]], hide_index=True, use_container_width=True, key="ed_cobro")
                for col in [col_id, col_desc]: 
                    if col in df_por_cobrar.columns: df_editado_cobro[col] = df_por_cobrar[col].values
            else:
                cols_cobro = [c for c in [col_taller, 'Siniestro', 'Vehiculo_Info', col_cant, col_desc, col_precio, col_estatus, col_comentarios] if c in df_por_cobrar.columns]
                st.dataframe(df_por_cobrar[cols_cobro], column_config=base_config, hide_index=True, use_container_width=True)

    df_asignados = df_filtrado[~df_filtrado[col_estatus].astype(str).str.upper().str.contains("CONFIRMAR")].copy() if col_estatus else df_filtrado.copy()
    with st.expander(f"📋 Pedidos Asignados (General) | {df_asignados['Siniestro'].nunique() if not df_asignados.empty else 0} Siniestros", expanded=False):
        dfs_editados = []
        if not df_asignados.empty:
            if col_estatus:
                estatus_upper = df_asignados[col_estatus].astype(str).str.upper()
                df_asignados['Pedido'] = estatus_upper.str.contains("EN PROCESAMIENTO")
                df_asignados['Entregado'] = estatus_upper.str.contains("ENTREGADO")
                df_asignados['Recibido'] = estatus_upper.str.contains("RECIBIDO")
                df_asignados['Reasignacion'] = estatus_upper.str.contains("REASIGNAR")
                df_asignados['Cancelar'] = estatus_upper.str.contains("CANCELADO")
            df_asignados['Remision'] = df_asignados[col_remision].astype(str).str.strip() != '' if col_remision else False
            df_asignados['Proveedor'] = "" 
            df_asignados['Costo Compra'] = 0.0 
            df_asignados['ETA (Días)'] = 0     
            
            for taller, df_taller in df_asignados.groupby(col_taller):
                with st.expander(f"🏢 {taller} | {df_taller['Siniestro'].nunique()} Siniestro(s)", expanded=False):
                    for siniestro_auto, df_grupo in df_taller.groupby('Siniestro'):
                        st.markdown(f"**🚗 {siniestro_auto} | {df_grupo['Vehiculo_Info'].iloc[0]}**")
                        if not modo_consulta and permiso_edicion:
                            columnas_checkbox = ['Pedido', 'Proveedor', 'Costo Compra', 'ETA (Días)', 'Remision', 'Entregado', 'Recibido', 'Reasignacion', 'Cancelar']
                            orden_deseado = [c for c in [col_asignacion, col_fecha_confi, col_cant, col_desc, col_precio, col_estatus, col_vencimiento, col_guia, col_remision, col_comentarios] if c in df_grupo.columns] + columnas_checkbox
                            
                            config_pedidos = base_config.copy()
                            config_pedidos.update({ 
                                col_asignacion: st.column_config.TextColumn("Asig. (Doble clic p/editar)"),
                                col_vencimiento: st.column_config.TextColumn("Venc. (Doble clic p/editar)"),
                                "Pedido": st.column_config.CheckboxColumn("🛒 Ped"), 
                                "Proveedor": st.column_config.TextColumn("🏢 Proveedor"), 
                                "Costo Compra": st.column_config.NumberColumn("💲 Costo", format="$ %.2f"), 
                                "ETA (Días)": st.column_config.NumberColumn("⏳ Días", step=1),
                                "Remision": st.column_config.CheckboxColumn("📝 Rem"), 
                                "Entregado": st.column_config.CheckboxColumn("🚚 Ent"), 
                                "Recibido": st.column_config.CheckboxColumn("🏁 Rec"), 
                                "Reasignacion": st.column_config.CheckboxColumn("🔄 Reasig"), 
                                "Cancelar": st.column_config.CheckboxColumn("🚫 Can") 
                            })
                            
                            columnas_editables = columnas_checkbox + [col_comentarios, col_guia, col_asignacion, col_vencimiento]
                            df_editado_parcial = st.data_editor(df_grupo[orden_deseado], column_config=config_pedidos, disabled=[c for c in orden_deseado if c not in columnas_editables], hide_index=True, use_container_width=True, key=f"ed_{taller}_{siniestro_auto}")
                            for col in [col_id, col_taller, col_marca, col_modelo, col_desc, 'Siniestro', 'Vehiculo_Info']:
                                if col in df_grupo.columns: df_editado_parcial[col] = df_grupo[col].values
                            dfs_editados.append(df_editado_parcial)
                        else:
                            orden_deseado = [c for c in [col_asignacion, col_fecha_confi, col_cant, col_desc, col_precio, col_estatus, col_vencimiento, col_guia, col_remision, col_comentarios] if c in df_grupo.columns]
                            st.dataframe(df_grupo[orden_deseado], column_config=base_config, hide_index=True, use_container_width=True)
        if dfs_editados: df_editado = pd.concat(dfs_editados, ignore_index=True)

    df_recoleccion = df_recoleccion_total.copy()
    if taller_sel: df_recoleccion = df_recoleccion[df_recoleccion[col_taller].astype(str).isin(taller_sel)]
    if siniestro_sel:
        ids_sel = [s.split(" - ")[0] for s in siniestro_sel]
        df_recoleccion = df_recoleccion[df_recoleccion['Siniestro'].isin(ids_sel)]
    if desc_sel: df_recoleccion = df_recoleccion[df_recoleccion[col_desc].astype(str).isin(desc_sel)]

    with st.expander(f"↩️ Piezas para Recolección | {df_recoleccion['Siniestro'].nunique() if not df_recoleccion.empty else 0} Siniestros", expanded=False):
        if not df_recoleccion.empty:
            cols_rec = [c for c in [col_taller, 'Siniestro', 'Vehiculo_Info', col_desc, col_cant, col_precio, col_estatus, col_vencimiento, col_comentarios] if c in df_recoleccion.columns]
            st.dataframe(df_recoleccion[cols_rec], column_config=base_config, hide_index=True, use_container_width=True)

# === [BLOQUE 6: VISTA 3 - PEDIDOS Y PROVEEDORES] ===
if vista_actual == "🛒 Compras":
    st.markdown("### 🛒 Panel de Compras (Gestión y Pagos)")
    if not df_compras.empty:
        for c in ['Condición Pago', 'Días Crédito', 'Estatus Pago']:
            if c not in df_compras.columns: df_compras[c] = ""
            
        df_compras['Recibido_Bool'] = df_compras['Recibido'].astype(str).str.strip().str.upper().isin(['TRUE', 'SI', '1', 'YES', 'V', 'X'])
        df_compras_disp = df_compras[(df_compras['Recibido_Bool'] == False) | (df_compras['Estatus Pago'].astype(str).str.upper() != 'PAGADO')].copy()
        
        if not df_compras_disp.empty:
            df_compras_disp = df_compras_disp.drop(columns=['Recibido_Bool'])
            
            def parse_spanish_date(d_str):
                if not isinstance(d_str, str): return pd.NaT
                d_str = d_str.lower().replace('-', '/') 
                meses = {'ene':'01', 'feb':'02', 'mar':'03', 'abr':'04', 'may':'05', 'jun':'06', 'jul':'07', 'ago':'08', 'sep':'09', 'oct':'10', 'nov':'11', 'dic':'12'}
                for text, num in meses.items():
                    if text in d_str:
                        d_str = d_str.replace(text, num)
                        break
                try: return pd.to_datetime(d_str, format='%d/%m/%y', errors='coerce')
                except: return pd.NaT

            df_compras_disp['Fecha_Compra_Dt'] = df_compras_disp['Fecha Compra'].apply(parse_spanish_date)
            df_compras_disp['ETA_Dias'] = pd.to_numeric(df_compras_disp['Tiempo Entrega (Días)'], errors='coerce').fillna(0)
            df_compras_disp['Llegada_Calculada'] = df_compras_disp['Fecha_Compra_Dt'] + pd.to_timedelta(df_compras_disp['ETA_Dias'], unit='d')
            
            df_compras_disp['Días Crédito'] = pd.to_numeric(df_compras_disp['Días Crédito'], errors='coerce').fillna(0)
            df_compras_disp['Fecha Límite Pago'] = pd.NaT
            mask_credito = df_compras_disp['Condición Pago'].astype(str).str.upper().str.contains('CREDITO|CRÉDITO')
            df_compras_disp.loc[mask_credito, 'Fecha Límite Pago'] = df_compras_disp.loc[mask_credito, 'Fecha_Compra_Dt'] + pd.to_timedelta(df_compras_disp.loc[mask_credito, 'Días Crédito'], unit='d')
            
            hoy_dt = pd.to_datetime(datetime.datetime.now().date())
            def calc_alerta_pago(row):
                if str(row['Estatus Pago']).upper() == 'PAGADO': return "✅ Saldado"
                cond = str(row['Condición Pago']).upper()
                if 'CREDITO' in cond or 'CRÉDITO' in cond:
                    if pd.notnull(row['Fecha Límite Pago']):
                        dias_restantes = (row['Fecha Límite Pago'] - hoy_dt).days
                        if dias_restantes < 0: return "🔴 Pago Vencido"
                        elif dias_restantes <= 3: return f"🟡 Pagar en {dias_restantes} días"
                        else: return f"🟢 {dias_restantes} días rest."
                elif 'PREVIO' in cond or 'ANTICIPO' in cond: return "🔵 Requiere Pago/Anticipo"
                elif 'CONTRA ENTREGA' in cond: return "🟠 Pagar al Recibir"
                return "⚪ Configurar Pago"
            
            df_compras_disp['Alerta Pago'] = df_compras_disp.apply(calc_alerta_pago, axis=1)
            # Ordenamos todo por fecha de llegada para tener una "Línea de tiempo" natural
            df_compras_disp = df_compras_disp.sort_values(by='Llegada_Calculada', ascending=True)

            df_compras_disp['Filtro_Busqueda'] = df_compras_disp['Siniestro'].astype(str) + " | " + df_compras_disp['Descripción Pieza'].astype(str)
            
            col_b1, col_b2, col_b3 = st.columns(3)
            with col_b1:
                lista_pedidos = sorted(list(df_compras_disp['Filtro_Busqueda'].unique()))
                busqueda_pedido = st.multiselect("🔍 Buscar Siniestro/Pieza:", options=lista_pedidos)
            with col_b2:
                df_compras_disp['Taller_Filtro'] = df_compras_disp['Taller'].replace('', 'SIN ASIGNAR')
                lista_talleres = sorted(list(df_compras_disp['Taller_Filtro'].unique()))
                busqueda_taller = st.multiselect("🏢 Filtrar por Taller (CDR):", options=lista_talleres)
            with col_b3:
                df_compras_disp['Prov_Filtro'] = df_compras_disp['Proveedor'].replace('', 'SIN ASIGNAR')
                lista_provs = sorted(list(df_compras_disp['Prov_Filtro'].unique()))
                busqueda_prov = st.multiselect("🏭 Filtrar por Proveedor:", options=lista_provs)

            if busqueda_pedido: df_compras_disp = df_compras_disp[df_compras_disp['Filtro_Busqueda'].isin(busqueda_pedido)].copy()
            if busqueda_taller: df_compras_disp = df_compras_disp[df_compras_disp['Taller_Filtro'].isin(busqueda_taller)].copy()
            if busqueda_prov: df_compras_disp = df_compras_disp[df_compras_disp['Prov_Filtro'].isin(busqueda_prov)].copy()
            
            st.markdown("#### 📦 Próximas Llegadas (Línea de Tiempo)")
            
            df_compras_disp['Imprimir Remisión'] = False
            df_compras_disp['Cancelar Compra'] = False
            df_compras_disp['Recibido'] = df_compras_disp['Recibido'].astype(str).str.upper().isin(['TRUE', 'SI', '1'])
            
            if not modo_consulta and permiso_edicion:
                config_compras = {
                    'Siniestro': st.column_config.TextColumn("Siniestro", disabled=True, width="small"),
                    'Descripción Pieza': st.column_config.TextColumn("Pieza", disabled=True),
                    'Proveedor': st.column_config.TextColumn("Proveedor"),
                    'Costo Compra': st.column_config.NumberColumn("Costo", format="$ %.2f", width="small"), 
                    'Tiempo Entrega (Días)': st.column_config.NumberColumn("ETA(Días)", step=1, width="small"),
                    'Fecha Llegada': st.column_config.TextColumn("Llegada Est.", disabled=True, width="small"),
                    'Condición Pago': st.column_config.SelectboxColumn("Cond. Pago", options=["Crédito", "Previo", "Anticipo", "Contra Entrega", ""], width="small"),
                    'Días Crédito': st.column_config.NumberColumn("Días Cr.", step=1, width="small"),
                    'Estatus Pago': st.column_config.SelectboxColumn("Pago", options=["Pendiente", "Pagado"], width="small"),
                    'Alerta Pago': st.column_config.TextColumn("Alerta Financiera", disabled=True),
                    'Recibido': st.column_config.CheckboxColumn("🏁 Recibido"), 
                    'Imprimir Remisión': st.column_config.CheckboxColumn("🖨️ Remisión"),
                    'Cancelar Compra': st.column_config.CheckboxColumn("🚫 Cancelar")
                }
                
                cols_ordenadas = ['Siniestro', 'Descripción Pieza', 'Proveedor', 'Costo Compra', 'Tiempo Entrega (Días)', 'Fecha Llegada', 'Condición Pago', 'Días Crédito', 'Alerta Pago', 'Estatus Pago', 'Recibido', 'Imprimir Remisión', 'Cancelar Compra']
                cols_mostrar = [c for c in cols_ordenadas if c in df_compras_disp.columns]
                
                columnas_editables = ['Proveedor', 'Costo Compra', 'Tiempo Entrega (Días)', 'Condición Pago', 'Días Crédito', 'Estatus Pago', 'Recibido', 'Imprimir Remisión', 'Cancelar Compra']
                
                df_editado_compras = st.data_editor(df_compras_disp[cols_mostrar], column_config=config_compras, disabled=[c for c in cols_mostrar if c not in columnas_editables], hide_index=True, use_container_width=True, key="ed_compras_flat")
                
                df_editado_compras.index = df_compras_disp.index
                st.session_state['df_editado_compras_temp'] = df_editado_compras
            else:
                cols_ordenadas = ['Siniestro', 'Descripción Pieza', 'Proveedor', 'Costo Compra', 'Tiempo Entrega (Días)', 'Fecha Llegada', 'Condición Pago', 'Alerta Pago', 'Estatus Pago']
                cols_mostrar = [c for c in cols_ordenadas if c in df_compras_disp.columns]
                st.dataframe(df_compras_disp[cols_mostrar], hide_index=True, use_container_width=True)
            
        else: st.success("✅ Todos los pedidos han sido recibidos y pagados.")
    else: st.warning("No hay órdenes de compra registradas actualmente.")
    
    st.markdown("---")
    st.markdown("### 🏢 Directorio de Proveedores")
    try: df_proveedores = cargar_datos.__wrapped__() if False else obtener_dataframe("BD_PROVEEDORES")
    except Exception: df_proveedores = pd.DataFrame()
    
    if permiso_edicion:
        with st.expander("➕ Registrar Nuevo Proveedor", expanded=False):
            with st.form("form_proveedores", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                p_prov = c1.text_input("Proveedor * (Obligatorio)")
                p_suc = c2.text_input("Sucursal")
                p_tiempo = c3.text_input("Tiempo de Entrega (Ej. 5 a 7 días)")
                c4, c5, c6 = st.columns(3)
                p_contacto = c4.text_input("Nombre de Contacto")
                p_tel = c5.text_input("Teléfono")
                p_correo = c6.text_input("Correo")
                p_dir = st.text_input("Dirección Completa")
                if st.form_submit_button("💾 Guardar Proveedor"):
                    if p_prov.strip() == "": st.error("❌ El nombre del Proveedor es obligatorio.")
                    else:
                        try:
                            doc = init_connection()
                            ws_p = doc.worksheet("BD_PROVEEDORES")
                            ws_p.append_row([p_prov.upper(), p_suc.upper(), p_dir.upper(), p_tiempo.upper(), p_contacto.upper(), p_tel, p_correo])
                            st.success(f"✅ Proveedor '{p_prov}' guardado exitosamente en la nube.")
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                        except Exception as e: st.error(f"❌ Error al guardar en la nube: {e}")
                        
    if not df_proveedores.empty: st.dataframe(df_proveedores.fillna(""), use_container_width=True, hide_index=True)

# === [BLOQUE 7: VISTAS 4 Y 5 - TALLERES E INVENTARIO] ===
if vista_actual == "🏢 Talleres":
    st.markdown("### 🏢 Base de Datos de Talleres")
    
    if permiso_edicion:
        with st.expander("➕ Registrar Nuevo Taller", expanded=False):
            st.info("Registra un nuevo taller. El Asesor se asignará automáticamente si la ciudad está en el directorio GNP.")
            mapa_asesores = {"Monterrey": "Oscar Landeros Martinez", "CDMX": "Yessica Vianney Martinez Olivar", "Guadalajara": "Estefany Dayanna Ochoa Aranda"}
            lista_estados = ["Aguascalientes", "Baja California", "CDMX", "Jalisco", "Nuevo León", "Yucatán"]
            c1, c2, c3 = st.columns([2, 2, 1])
            nuevo_taller = c1.text_input("Taller * (Obligatorio)")
            ciudad_sel = c2.selectbox("Ciudad", [""] + sorted(list(mapa_asesores.keys())) + ["Otra (Escribir manualmente)..."])
            if ciudad_sel == "Otra (Escribir manualmente)...":
                nueva_ciudad = c2.text_input("Ingresa la Ciudad")
                asesor_asignado = c3.text_input("Asesor Asignado (Manual)")
            elif ciudad_sel != "":
                nueva_ciudad = ciudad_sel
                asesor_asignado = mapa_asesores.get(ciudad_sel, "")
                c3.text_input("Asesor Asignado", value=asesor_asignado, disabled=True)
            else:
                nueva_ciudad = ""
                asesor_asignado = ""
                c3.text_input("Asesor Asignado", disabled=True)
            c4, c5, c6, c7 = st.columns(4)
            nuevo_estado = c4.selectbox("Estado", [""] + lista_estados)
            nuevo_seguro = c5.selectbox("Seguro", ["MULTI", "GNP", "AMBOS", "OTRO"])
            nuevo_contacto = c6.text_input("Contacto Taller")
            nuevo_tel = c7.text_input("Teléfono Contacto")
            c8, c9, c10 = st.columns([1, 1, 2])
            nuevo_wa = c8.text_input("Whatsapp")
            nuevo_correo = c9.text_input("Correo")
            nueva_dir = c10.text_input("Dirección Completa (Calle, Col.)")
            if st.button("💾 Guardar en Catálogo", type="primary"):
                if nuevo_taller.strip() == "": st.error("❌ El 'Nombre del Taller' es obligatorio.")
                else:
                    try:
                        doc = init_connection()
                        ws_c = doc.worksheet("Catálogo")
                        ws_c.append_row([nuevo_taller.upper(), nueva_dir.upper(), ciudad_sel.upper(), nuevo_estado.upper(), nuevo_contacto.upper(), nuevo_tel, nuevo_wa, nuevo_correo, asesor_asignado.upper(), nuevo_seguro.upper()], value_input_option='USER_ENTERED')
                        st.success(f"✅ Taller '{nuevo_taller}' agregado exitosamente en la nube.")
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                    except Exception as e: st.error(f"❌ Error al guardar en la nube: {e}")

    st.markdown("---")
    if not df_catalogo.empty:
        col_taller_cat = next((c for c in df_catalogo.columns if "TALLER" in str(c).upper()), None)
        if col_taller_cat:
            busqueda_taller = st.multiselect("🔍 Buscar Taller para editar:", options=sorted(list(df_catalogo[col_taller_cat].dropna().astype(str).unique())))
            df_cat_disp = df_catalogo[df_catalogo[col_taller_cat].astype(str).isin(busqueda_taller)].copy() if busqueda_taller else df_catalogo.copy()
        else: df_cat_disp = df_catalogo.copy()
        
        df_cat_disp = df_cat_disp[[c for c in df_cat_disp.columns if "Unnamed" not in str(c)]]
        for c in df_cat_disp.columns: df_cat_disp[c] = df_cat_disp[c].fillna("").astype(str).replace(['nan', 'None', '0', '0.0'], '')
        
        if permiso_edicion:
            st.data_editor(df_cat_disp, num_rows="dynamic", use_container_width=True, hide_index=True, key="ed_cat")
        else:
            st.dataframe(df_cat_disp, use_container_width=True, hide_index=True)

if vista_actual == "📦 Inventario":
    if permiso_edicion:
        with st.expander("➕ Registrar Nueva Pieza", expanded=False):
            with st.form("form_alta_inv", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                ubicacion_n = c1.text_input("Ubicación Física")
                oem_n = c2.text_input("No. Parte (OEM)")
                alt_n = c3.text_input("No. Parte Alterno")
                desc_n = st.text_input("Descripción de la Pieza * (Obligatorio)")
                c4, c5, c6 = st.columns(3)
                marca_n = c4.text_input("Marca")
                mod_n = c5.text_input("Modelo")
                ver_n = c6.text_input("Versión")
                c7, c8, c9 = st.columns(3)
                ano_n = c7.text_input("Años Compatibilidad")
                pos_n = c8.text_input("Posición / Lado")
                cant_n = c9.number_input("Cantidad", min_value=1, step=1)
                c10, c11, c12 = st.columns(3)
                est_n = c10.selectbox("Estado de la Pieza", ["NUEVA", "REPARADA", "USADA", "GENÉRICA"])
                costo_n = c11.number_input("Costo Adquisición", min_value=0.0, step=10.0)
                precio_n = c12.number_input("Precio Venta", min_value=0.0, step=10.0)
                c13, c14 = st.columns(2)
                sin_n = c13.text_input("No. Siniestro / Lote")
                ml_n = c14.text_input("SKU Mercado Libre")
                if st.form_submit_button("💾 Guardar en Inventario"):
                    if desc_n.strip() == "": st.error("❌ La 'Descripción de la Pieza' es obligatoria.")
                    else:
                        try:
                            doc = init_connection()
                            ws_i = doc.worksheet("BD_INVENTARIO")
                            ws_i.append_row([str(v).upper() if isinstance(v, str) else v for v in [ubicacion_n, oem_n, alt_n, desc_n, marca_n, mod_n, ver_n, ano_n, pos_n, cant_n, est_n, costo_n, precio_n, sin_n, ml_n, "NO"]], value_input_option='USER_ENTERED')
                            st.success("✅ Pieza agregada exitosamente en la nube.")
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                        except Exception as e: st.error(f"❌ Error al guardar en la nube: {e}")

        # --- MÓDULO NUEVO DE SALIDAS Y VENTAS (CORREGIDO ID Y CERO STOCK) ---
        st.markdown("---")
        with st.expander("📉 Registrar Salida / Venta", expanded=False):
            if not df_inventario.empty:
                col_skuint = next((c for c in df_inventario.columns if "SKU INT" in str(c).upper()), None)
                df_inv_act = df_inventario[df_inventario[col_skuint].astype(str).str.strip().str.upper() != 'PRE-001'].copy() if col_skuint else df_inventario.copy()
                
                # Filtro estricto: Que NO tenga etiqueta de "Sin Existencia" Y que la Cantidad Numérica sea mayor a 0
                df_inv_act['Cantidad_Num'] = pd.to_numeric(df_inv_act['Cantidad'], errors='coerce').fillna(0)
                df_stock = df_inv_act[(~df_inv_act['Sin Existencia']) & (df_inv_act['Cantidad_Num'] > 0)].copy()
                
                if not df_stock.empty:
                    # Se crea un ID único basado en la fila real de Google Sheets para evitar fallas por nombres iguales o celdas vacías
                    df_stock['GS_Row'] = df_stock.index + 2
                    df_stock['Filtro_Venta'] = df_stock.apply(lambda r: f"ID:{r['GS_Row']} - " + " | ".join([e.upper() for e in [str(r.get('Número de Parte (OEM)', '')), str(r.get('Marca', '')), str(r.get('Modelo', '')), str(r.get('Descripción de la Pieza', ''))] if str(e).strip() not in ['nan','none','']]), axis=1)
                    
                    with st.form("form_salida_inv", clear_on_submit=True):
                        st.info("Selecciona una pieza para descontar del inventario. Si la cantidad llega a 0, se ocultará automáticamente.")
                        pieza_sel = st.selectbox("Pieza a descontar:", options=[""] + sorted(list(df_stock['Filtro_Venta'].unique())))
                        
                        c_cant, c_dest = st.columns([1, 3])
                        cant_descontar = c_cant.number_input("Cantidad a sacar", min_value=1, step=1)
                        destino_salida = c_dest.text_input("Destino / Comentario (Ej. Venta Mostrador, Siniestro MULTI-123)")
                        
                        if st.form_submit_button("📉 Confirmar Salida"):
                            if not pieza_sel:
                                st.error("❌ Por favor selecciona una pieza.")
                            else:
                                try:
                                    fila_encontrada = int(pieza_sel.split(' - ')[0].replace('ID:', '').strip())
                                    
                                    doc = init_connection()
                                    ws_i = doc.worksheet("BD_INVENTARIO")
                                    datos_i = ws_i.get_all_values()
                                    headers = [str(h).strip().upper() for h in datos_i[0]]
                                    idx_cant = headers.index('CANTIDAD') if 'CANTIDAD' in headers else 9
                                    idx_sin = headers.index('NO. SINIESTRO / LOTE') if 'NO. SINIESTRO / LOTE' in headers else 13
                                    idx_sinexist = headers.index('SIN EXISTENCIA') if 'SIN EXISTENCIA' in headers else 15
                                    
                                    cant_actual_str = str(datos_i[fila_encontrada-1][idx_cant]).strip()
                                    cant_actual = int(float(cant_actual_str)) if cant_actual_str.replace('.','',1).isdigit() else 0
                                    nueva_cant = cant_actual - cant_descontar
                                    
                                    if nueva_cant <= 0:
                                        nueva_cant = 0
                                        ws_i.update_cell(fila_encontrada, idx_sinexist + 1, "SI")
                                    
                                    ws_i.update_cell(fila_encontrada, idx_cant + 1, nueva_cant)
                                    
                                    if destino_salida.strip():
                                        val_previo = str(datos_i[fila_encontrada-1][idx_sin]) if len(datos_i[fila_encontrada-1]) > idx_sin else ""
                                        nuevo_dest = f"{val_previo} [Salida: {destino_salida.upper()}]".strip()
                                        ws_i.update_cell(fila_encontrada, idx_sin + 1, nuevo_dest)
                                        
                                    st.success(f"✅ Salida registrada. Nuevo stock: {nueva_cant}")
                                    st.cache_data.clear()
                                    time.sleep(1)
                                    st.rerun()
                                        
                                except Exception as e:
                                    st.error(f"❌ Error al conectar con la nube: {e}")
                else:
                    st.warning("No hay piezas disponibles en stock (Cantidades agotadas).")

    st.markdown("---")
    if not df_inventario.empty:
        col_skuint = next((c for c in df_inventario.columns if "SKU INT" in str(c).upper()), None)
        df_inv_filtrado = df_inventario[df_inventario[col_skuint].astype(str).str.strip().str.upper() != 'PRE-001'].copy() if col_skuint else df_inventario.copy()
        
        # Filtramos también la vista global para que se oculten las que tienen cantidad 0
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
            
            df_inv_disp.insert(0, 'Nº', range(1, len(df_inv_disp) + 1))
            st.markdown(f"**🔢 Total de piezas listadas:** {len(df_inv_disp)}")
            
            if permiso_edicion:
                config_inv = {'Nº': st.column_config.NumberColumn("Nº", disabled=True), 'Sin Existencia': st.column_config.CheckboxColumn("Sin Existencia", default=False)}
                st.data_editor(df_inv_disp, num_rows="dynamic", column_config=config_inv, use_container_width=True, hide_index=True, key="ed_inv")
            else:
                st.dataframe(df_inv_disp, use_container_width=True, hide_index=True)
        else:
            st.info("El inventario está vacío o todas las piezas están agotadas.")

# === [BLOQUE 8: FACTURACIÓN] ===
if vista_actual == "🧾 Facturación":
    st.markdown("### 🧾 Pedidos Listos para Facturar")
    df_fact = df_trabajo[df_trabajo[col_estatus].astype(str).str.strip().str.upper() == "RECIBIDO"].copy() if col_estatus else pd.DataFrame()
    if not df_fact.empty:
        df_fact['Siniestro'] = df_fact[col_id].apply(lambda x: str(x)[:-2] if str(x).endswith('.0') else str(x)) if col_id else ""
        df_fact['Vehiculo_Info'] = df_fact.apply(lambda r: f"{r.get(col_marca, '')} {r.get(col_modelo, '')} {str(int(float(r[col_anio]))) if col_anio and pd.notnull(r.get(col_anio)) else ''}".strip(), axis=1)
        
        dict_placas = dict(zip(df_placas['Siniestro'].astype(str).str.strip().str.replace('.0', '', regex=False), df_placas['Placa'].astype(str))) if not df_placas.empty and 'Siniestro' in df_placas.columns else {}
        
        dfs_editados_fact = []
        for taller, df_taller_fact in df_fact.groupby(col_taller):
            with st.expander(f"🏢 {taller} | {df_taller_fact['Siniestro'].nunique()} Siniestro(s) para Facturar", expanded=False):
                for siniestro_f, df_g in df_taller_fact.groupby('Siniestro'):
                    placa_val = dict_placas.get(str(siniestro_f).strip(), "⚠️ PLACA PENDIENTE")
                    sufijo_multi = f" // {siniestro_f} // {placa_val} // {df_g['Vehiculo_Info'].iloc[0]}"
                    st.markdown(f"**🚗 {siniestro_f} | {df_g['Vehiculo_Info'].iloc[0]}**")
                    
                    df_mostrar_f = df_g.copy()
                    df_mostrar_f['Facturado'] = False
                    df_mostrar_f['Concepto Factura'] = df_mostrar_f.apply(lambda r: f"{r.get(col_desc, '')}{sufijo_multi}" if aseguradora_sel == "Multiasistencias" else r.get(col_desc, ''), axis=1)
                    
                    if permiso_edicion:
                        cols_mostrar = [c for c in ['Facturado', col_cant, 'Concepto Factura', col_precio, col_origen] if c in df_mostrar_f.columns or c == 'Facturado']
                        config_fact = {'Facturado': st.column_config.CheckboxColumn("✅ Facturado", default=False), 'Concepto Factura': st.column_config.TextColumn("Descripción para Factura", width="large"), col_precio: st.column_config.NumberColumn("Precio", format="$ %.2f")}
                        df_editado_parcial_f = st.data_editor(df_mostrar_f[cols_mostrar], column_config=config_fact, disabled=[c for c in cols_mostrar if c != 'Facturado'], hide_index=True, use_container_width=True, key=f"fact_{taller}_{siniestro_f}")
                        for col_llave in [col_id, col_desc]:
                            if col_llave in df_g.columns: df_editado_parcial_f[col_llave] = df_g[col_llave].values
                        dfs_editados_fact.append(df_editado_parcial_f)
                    else:
                        cols_mostrar = [c for c in [col_cant, 'Concepto Factura', col_precio, col_origen] if c in df_mostrar_f.columns]
                        st.dataframe(df_mostrar_f[cols_mostrar], hide_index=True, use_container_width=True)
                    
        if dfs_editados_fact: df_editado_fact = pd.concat(dfs_editados_fact, ignore_index=True)
    else: st.success("✅ No hay pedidos pendientes de facturación.")

# ==============================================================================
# === [BLOQUE 9: MOTOR DE GUARDADO Y PDF] ===
# ==============================================================================
if btn_guardar and permiso_edicion:
    def generar_llave(id_val, desc_val):
        id_str = str(id_val).strip().upper()
        if id_str.endswith('.0'): id_str = id_str[:-2]
        desc_str = ' '.join(str(desc_val).strip().upper().split())
        return (id_str if id_str not in ['NAN', 'NONE'] else '', desc_str if desc_str not in ['NAN', 'NONE'] else '')
    
    originales = {}
    for _, r in df_trabajo_completo.iterrows():
        k = generar_llave(r.get('Siniestro', r.get(col_id, '')), r.get(col_desc, ''))
        originales[k] = {
            'comentario': str(r.get(col_comentarios, '')).strip(),
            'guia': str(r.get(col_guia, '')).strip(),
            'estatus_db': str(r.get(col_estatus, '')).strip().upper(),
            'remision_bool': str(r.get(col_remision, '')).strip() != '',
            'aseg': str(r.get(col_aseg, '')).strip().upper(),
            'vencimiento_db': str(r.get(col_vencimiento, '')).strip(),
            'asignacion_db': str(r.get(col_asignacion, '')).strip()
        }
        
    cambios_a_guardar = {}
    cambios_bd_compras = {}

    tz_mx = datetime.timezone(datetime.timedelta(hours=-6))
    fecha_hoy_sistema = datetime.datetime.now(tz_mx).strftime('%d/%b/%y')

    if not df_editado_conf.empty:
        for _, row in df_editado_conf.iterrows():
            k = generar_llave(row.get('Siniestro', row.get(col_id, '')), row.get(col_desc, ''))
            orig = originales.get(k, {'comentario': '', 'estatus_db': ''})
            nuevo_estatus = "CANCELADO" if row.get('Cancelar') else ("EN PROCESAMIENTO" if row.get('Confirmar Surtido') else None)
            comentario_actual = str(row.get(col_comentarios, '')).strip()
            
            if nuevo_estatus and nuevo_estatus != orig['estatus_db']: 
                cambios_a_guardar.setdefault(k, {})['estatus'] = nuevo_estatus
                if nuevo_estatus == "EN PROCESAMIENTO":
                    cambios_a_guardar[k]['fecha_confi'] = fecha_hoy_sistema
                    
            if comentario_actual != orig['comentario']: 
                cambios_a_guardar.setdefault(k, {})['comentario'] = comentario_actual

    if not df_editado_venc.empty:
        for _, row in df_editado_venc.iterrows():
            k = generar_llave(row.get('Siniestro', row.get(col_id, '')), row.get(col_desc, ''))
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
            elif row.get('Reasignar') and not nuevo_estatus:
                nuevo_estatus = "EN PROCESAMIENTO"
            
            if nuevo_estatus and nuevo_estatus != orig['estatus_db']: cambios_a_guardar.setdefault(k, {})['estatus'] = nuevo_estatus
            if comentario_actual != orig['comentario']: cambios_a_guardar.setdefault(k, {})['comentario'] = comentario_actual
            if guia_actual != orig['guia']: cambios_a_guardar.setdefault(k, {})['guia'] = guia_actual

    if not df_editado_atrasadas.empty:
        for _, row in df_editado_atrasadas.iterrows():
            k = generar_llave(row.get('Siniestro', row.get(col_id, '')), row.get(col_desc, ''))
            orig = originales.get(k, {'comentario': '', 'estatus_db': ''})
            nuevo_estatus = "CANCELADO" if row.get('Cancelar') else None
            comentario_actual = str(row.get(col_comentarios, '')).strip()
            nueva_fecha = row.get('Nueva Fecha')
            
            if pd.notnull(nueva_fecha) and str(nueva_fecha).strip() not in ['', 'NaT', 'None']:
                try: fecha_str = pd.to_datetime(nueva_fecha).strftime('%d/%b/%y')
                except: fecha_str = str(nueva_fecha)
                cambios_a_guardar.setdefault(k, {})['vencimiento'] = fecha_str
                if not nuevo_estatus: nuevo_estatus = "EN PROCESAMIENTO"
            elif row.get('Reasignar') and not nuevo_estatus:
                nuevo_estatus = "EN PROCESAMIENTO"
            
            if nuevo_estatus and nuevo_estatus != orig['estatus_db']: cambios_a_guardar.setdefault(k, {})['estatus'] = nuevo_estatus
            if comentario_actual != orig['comentario']: cambios_a_guardar.setdefault(k, {})['comentario'] = comentario_actual

    if not df_editado_cobro.empty:
        for _, row in df_editado_cobro.iterrows():
            k = generar_llave(row.get('Siniestro', row.get(col_id, '')), row.get(col_desc, ''))
            orig = originales.get(k, {'comentario': '', 'estatus_db': ''})
            comentario_actual = str(row.get(col_comentarios, '')).strip()
            if row.get('Marcar Recibido'): 
                cambios_a_guardar.setdefault(k, {})['estatus'] = "RECIBIDO"
                cambios_a_guardar[k]['fecha_recibido'] = fecha_hoy_sistema
            if comentario_actual != orig['comentario']: 
                cambios_a_guardar.setdefault(k, {})['comentario'] = comentario_actual

    if not df_editado_fact.empty:
        for _, row in df_editado_fact.iterrows():
            k = generar_llave(row.get('Siniestro', row.get(col_id, '')), row.get(col_desc, ''))
            if row.get('Facturado'): 
                cambios_a_guardar.setdefault(k, {})['estatus'] = "FACTURADO"
                cambios_a_guardar[k]['fecha_facturacion'] = fecha_hoy_sistema

    if not df_editado.empty:
        for _, row in df_editado.iterrows():
            k = generar_llave(row.get('Siniestro', row.get(col_id, '')), row.get(col_desc, ''))
            orig = originales.get(k, {'comentario': '', 'guia': '', 'estatus_db': '', 'remision_bool': False, 'vencimiento_db': '', 'asignacion_db': ''})
            actual_rem_bool = row.get('Remision', False)
            pedido_bool = row.get('Pedido', False)
            
            nuevo_estatus = "CANCELADO" if row.get('Cancelar') else "REASIGNAR" if row.get('Reasignacion') else "RECIBIDO" if row.get('Recibido') else "ENTREGADO" if row.get('Entregado') else "EN TRANSITO" if row.get('Remision') else "EN PROCESAMIENTO" if pedido_bool else None
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
            
            if actual_rem_bool and not orig['remision_bool']: 
                cambios_a_guardar.setdefault(k, {}).update({'imprimir_remision': True, 'generar_nuevo_folio': True, 'usuario_rem': st.session_state.get('usuario_actual', 'Sistema'), 'fecha_envio': fecha_hoy_sistema})
                
            if pedido_bool:
                cambios_a_guardar.setdefault(k, {})['crear_compra'] = True
                cambios_a_guardar[k]['compra_prov'] = str(row.get('Proveedor', '')).strip()
                cambios_a_guardar[k]['compra_costo'] = str(row.get('Costo Compra', '0')).strip()
                cambios_a_guardar[k]['compra_eta'] = str(row.get('ETA (Días)', '0')).strip()
                cambios_a_guardar[k]['compra_taller'] = str(row.get(col_taller, '')).strip()
                cambios_a_guardar[k]['compra_vehiculo'] = str(row.get('Vehiculo_Info', '')).strip()

    # --- COMPRAS FINANCIERAS Y CANCELACIONES ---
    df_editado_compras = st.session_state.get('df_editado_compras_temp', pd.DataFrame())
    if not df_editado_compras.empty:
        for _, row in df_editado_compras.iterrows():
            k = generar_llave(row.get('Siniestro', ''), row.get('Descripción Pieza', ''))
            orig = originales.get(k, {'estatus_db': '', 'remision_bool': False})
            
            cambios_bd_compras.setdefault(k, {})
            
            # LÓGICA DE CANCELACIÓN DE COMPRA
            if row.get('Cancelar Compra'):
                cambios_bd_compras[k]['cancelar_compra'] = True
                # Regresamos el estatus a la bandeja de entrada del Panel Operativo
                cambios_a_guardar.setdefault(k, {})['estatus'] = "POR CONFIRMAR"
            else:
                cambios_bd_compras[k]['costo'] = str(row.get('Costo Compra', '')).replace('$', '').strip()
                cambios_bd_compras[k]['tiempo'] = row.get('Tiempo Entrega (Días)', '')
                cambios_bd_compras[k]['cond_pago'] = row.get('Condición Pago', '')
                cambios_bd_compras[k]['dias_credito'] = row.get('Días Crédito', '')
                cambios_bd_compras[k]['estatus_pago'] = row.get('Estatus Pago', '')
                cambios_bd_compras[k]['prov'] = row.get('Proveedor', '')
                cambios_bd_compras[k]['recibido'] = 'SI' if row.get('Recibido') else 'NO'
                
                if row.get('Imprimir Remisión'):
                    cambios_a_guardar.setdefault(k, {})['imprimir_remision'] = True
                    cambios_a_guardar[k]['estatus'] = "EN TRANSITO"
                    if not orig['remision_bool']:
                        cambios_a_guardar[k]['generar_nuevo_folio'] = True
                        cambios_a_guardar[k]['usuario_rem'] = st.session_state.get('usuario_actual', 'Sistema')
                        cambios_a_guardar[k]['fecha_envio'] = fecha_hoy_sistema
                elif row.get('Recibido'):
                    cambios_a_guardar.setdefault(k, {})['estatus'] = "EN PROCESAMIENTO" 

    with st.spinner("Sincronizando en la nube..."):
        try:
            doc = init_connection()
            
            # --- 1. SINCRONIZAR BD_UNIFICADA ---
            if cambios_a_guardar:
                ws_uni = doc.worksheet("BD_UNIFICADA")
                datos_uni = ws_uni.get_all_values()
                headers = [str(h).strip() for h in datos_uni[0]]
                idx_id, idx_desc, idx_estatus, idx_rem = headers.index(col_id), headers.index(col_desc), headers.index(col_estatus), headers.index(col_remision)
                idx_usr_rem = headers.index("Usuario Remisión") if "Usuario Remisión" in headers else -1
                idx_coment = headers.index(col_comentarios) if col_comentarios in headers else -1
                idx_guia = headers.index(col_guia) if col_guia in headers else -1
                idx_venc = headers.index(col_vencimiento) if col_vencimiento in headers else -1
                idx_asig = headers.index(col_asignacion) if col_asignacion in headers else -1
                idx_confi = headers.index(col_fecha_confi) if col_fecha_confi in headers else -1
                
                idx_envio = headers.index("Fecha Envío") if "Fecha Envío" in headers else -1
                idx_recibido = headers.index("Fecha Recibido") if "Fecha Recibido" in headers else -1
                idx_facturacion = headers.index("Fecha Facturación") if "Fecha Facturación" in headers else -1
                
                max_folios = {"MULTI": 0, "GNP": 0}
                for pref in ["MULTI", "GNP"]:
                    numeros = df_completo[col_remision].astype(str).str.extract(rf'(?i){pref}\s*-\s*0*(\d+)', expand=False)
                    max_folios[pref] = int(pd.to_numeric(numeros, errors='coerce').max() if pd.notna(pd.to_numeric(numeros, errors='coerce').max()) else 0)

                folios_asignados_en_sesion = {}
                
                for k, v in cambios_a_guardar.items():
                    if v.get('generar_nuevo_folio'):
                        siniestro_id = k[0] 
                        if siniestro_id not in folios_asignados_en_sesion:
                            aseguradora_base = originales.get(k, {}).get('aseg', 'GNP')
                            pref = "MULTI" if "MULTI" in aseguradora_base else "GNP"
                            max_folios[pref] += 1
                            folios_asignados_en_sesion[siniestro_id] = f"{pref} - {max_folios[pref]:03d}"
                            
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

            # --- 2. PUENTE A BD_COMPRAS (MECANISMO DE ELIMINACIÓN) ---
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
                            if any(str(celda).strip() for celda in fila): 
                                datos_comp.append(fila)
                        
                    def get_col_idx(name):
                        if name in headers_comp: return headers_comp.index(name)
                        headers_comp.append(name)
                        datos_comp[0] = headers_comp
                        for r in datos_comp[1:]: r.append("")
                        return len(headers_comp) - 1
                        
                    idx_c_sin = get_col_idx('Siniestro')
                    idx_c_desc = get_col_idx('Descripción Pieza')
                    i_tall = get_col_idx('Taller')
                    i_veh = get_col_idx('Vehículo')
                    i_prov = get_col_idx('Proveedor')
                    i_costo = get_col_idx('Costo Compra')
                    i_fcomp = get_col_idx('Fecha Compra')
                    i_tiempo = get_col_idx('Tiempo Entrega (Días)')
                    i_rec = get_col_idx('Recibido')
                    
                    i_cond_pago = get_col_idx('Condición Pago')
                    i_dias_cred = get_col_idx('Días Crédito')
                    i_est_pago = get_col_idx('Estatus Pago')
                    
                    llaves_en_compras = set()
                    nuevos_datos_comp = [headers_comp]
                    
                    for i in range(1, len(datos_comp)):
                        while len(datos_comp[i]) < len(headers_comp): datos_comp[i].append("")
                        k_c = generar_llave(datos_comp[i][idx_c_sin], datos_comp[i][idx_c_desc])
                        llaves_en_compras.add(k_c)
                        
                        eliminar_fila = False
                        
                        if k_c in cambios_bd_compras:
                            cb = cambios_bd_compras[k_c]
                            if cb.get('cancelar_compra'):
                                eliminar_fila = True
                            else:
                                if str(cb.get('costo','')).strip(): datos_comp[i][i_costo] = cb['costo']
                                if str(cb.get('tiempo','')).strip(): datos_comp[i][i_tiempo] = cb['tiempo']
                                if 'cond_pago' in cb and str(cb['cond_pago']).strip() != 'nan': datos_comp[i][i_cond_pago] = cb['cond_pago']
                                if 'dias_credito' in cb and str(cb['dias_credito']).strip() != 'nan': datos_comp[i][i_dias_cred] = cb['dias_credito']
                                if 'estatus_pago' in cb and str(cb['estatus_pago']).strip() != 'nan': datos_comp[i][i_est_pago] = cb['estatus_pago']
                                if 'prov' in cb and str(cb['prov']).strip() and str(cb['prov']).strip() != 'nan': datos_comp[i][i_prov] = cb['prov']
                                if 'recibido' in cb: datos_comp[i][i_rec] = cb['recibido']
                        
                        if not eliminar_fila:
                            nuevos_datos_comp.append(datos_comp[i])
                                
                    fecha_hoy_comp = datetime.datetime.now(tz_mx).strftime('%d/%b/%y')
                    
                    nuevas_filas = []
                    for k, v in cambios_a_guardar.items():
                        if v.get('crear_compra') and k not in llaves_en_compras:
                            n_row = [""] * len(headers_comp)
                            n_row[idx_c_sin] = k[0]
                            n_row[idx_c_desc] = k[1]
                            n_row[i_tall] = v.get('compra_taller', '')
                            n_row[i_veh] = v.get('compra_vehiculo', '')
                            n_row[i_prov] = v.get('compra_prov', '')
                            n_row[i_costo] = v.get('compra_costo', '0')
                            n_row[i_tiempo] = v.get('compra_eta', '0')
                            n_row[i_fcomp] = fecha_hoy_comp
                            n_row[i_rec] = 'NO'
                            nuevas_filas.append(n_row)
                    
                    filas_a_escribir = nuevos_datos_comp + nuevas_filas
                    while len(filas_a_escribir) < len(datos_comp_crudos):
                        filas_a_escribir.append([""] * len(headers_comp))
                        
                    ws_comp.update(range_name='A1', values=filas_a_escribir, value_input_option='USER_ENTERED')
                except Exception as e_comp:
                    st.warning(f"Nota: Hubo un problema sincronizando BD_COMPRAS: {e_comp}")

            # --- GENERACIÓN DE PDF (AHORA USANDO SISTEMA NATIVO DE BYTES) ---
            llaves_a_imprimir = [k for k, v in cambios_a_guardar.items() if v.get('imprimir_remision') == True]
            if llaves_a_imprimir:
                marcados_remision = df_trabajo_completo[df_trabajo_completo.apply(lambda r: generar_llave(r.get(col_id, ''), r.get(col_desc, '')) in llaves_a_imprimir, axis=1)]
                cols_agrup = [col_id, col_taller, col_marca, col_modelo]
                agrupadores = [c for c in cols_agrup if c in marcados_remision.columns]
                
                avisos_unicos = set()
                pdfs_list = []
                usuario_print = st.session_state.get('usuario_actual', 'Sistema')
                
                for keys, df_g in marcados_remision.groupby(agrupadores):
                    siniestro_v = keys[agrupadores.index(col_id)] if col_id in agrupadores else ""
                    taller_v = keys[agrupadores.index(col_taller)] if col_taller in agrupadores else ""
                    marca_v = keys[agrupadores.index(col_marca)] if col_marca in agrupadores else ""
                    modelo_v = keys[agrupadores.index(col_modelo)] if col_modelo in agrupadores else ""
                    
                    folio_str_print = "S/N"
                    for _, row_rem in df_g.iterrows():
                        key_rem = generar_llave(row_rem.get(col_id, ''), row_rem.get(col_desc, ''))
                        if key_rem in cambios_a_guardar and 'remision_num' in cambios_a_guardar[key_rem]:
                            folio_str_print = cambios_a_guardar[key_rem]['remision_num']
                            break
                    
                    fecha_actual = datetime.datetime.now(tz_mx)
                    hora_am_pm = fecha_actual.strftime('%I:%M %p')
                    firma_digital = f"Generado por: {usuario_print} - {fecha_actual.strftime('%d/%b/%Y')} {hora_am_pm}"
                    
                    dir_v = ""
                    col_cat_taller = next((c for c in df_catalogo.columns if "TALLER" in str(c).upper()), None)
                    if not df_catalogo.empty and col_cat_taller:
                        match_taller = df_catalogo[df_catalogo[col_cat_taller].astype(str).str.strip().str.upper() == str(taller_v).strip().upper()]
                        if not match_taller.empty:
                            col_dir = next((c for c in df_catalogo.columns if "DIRECCI" in str(c).upper()), None)
                            if col_dir: dir_v = str(match_taller.iloc[0].get(col_dir, '')).strip()
                        else:
                            avisos_unicos.add(f"⚠️ AVISO: El CDR '{taller_v}' no está registrado. Ve a la pestaña '🏢 Talleres' para agregarlo.")
                    else:
                        avisos_unicos.add(f"⚠️ AVISO: El CDR '{taller_v}' no está registrado. Ve a la pestaña '🏢 Talleres' para agregarlo.")

                    def limpiar_texto(txt): return str(txt).encode('latin-1', 'replace').decode('latin-1')

                    pdf = FPDF(orientation='L', unit='mm', format='A4')
                    pdf.set_auto_page_break(auto=False, margin=0) 
                    pdf.add_page()
                    
                    def dibujar_bloque_remision(x_offset):
                        y_offset = 15
                        if os.path.exists("logo.png"):
                            try: pdf.image("logo.png", x_offset, y_offset - 3, 30)
                            except: pass
                        
                        pdf.set_font("Arial", 'B', 10); pdf.set_text_color(0, 51, 102); pdf.set_xy(x_offset + 32, y_offset)
                        pdf.cell(70, 5, limpiar_texto("PREMIER SERVICIOS Y REFACCIONES"))
                        pdf.set_font("Arial", 'B', 8); pdf.set_xy(x_offset + 32, y_offset + 5)
                        pdf.cell(70, 4, limpiar_texto("PMR SERVICIOS AUTOMOTRIZ"))
                        pdf.set_font("Arial", '', 7); pdf.set_text_color(100, 100, 100); pdf.set_xy(x_offset + 32, y_offset + 9)
                        pdf.cell(70, 3, limpiar_texto("ALLENDE 228, AÑO DE JUAREZ"))
                        pdf.set_xy(x_offset + 32, y_offset + 12)
                        pdf.cell(70, 3, limpiar_texto("SAN NICOLAS DE LOS GARZA, N.L. | PSA 211015 B30"))

                        pdf.set_text_color(0, 0, 0); pdf.set_xy(x_offset + 105, y_offset); pdf.set_font("Arial", 'B', 9)
                        pdf.cell(30, 5, "REMISION", border=1, align='C')
                        pdf.set_text_color(200, 0, 0); pdf.set_font("Arial", 'B', 10)
                        pdf.set_xy(x_offset + 105, y_offset + 5)
                        pdf.cell(30, 6, folio_str_print, border=1, align='C')
                        
                        y_datos = y_offset + 22; pdf.set_fill_color(220, 220, 220)
                        pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", 'B', 7)
                        
                        pdf.set_xy(x_offset, y_datos)
                        pdf.cell(20, 5, "TALLER", border=1, fill=True); pdf.set_font("Arial", '', 7)
                        pdf.cell(115, 5, limpiar_texto(f" {taller_v}")[:75], border=1)
                        
                        y_datos += 5; pdf.set_xy(x_offset, y_datos)
                        pdf.set_font("Arial", 'B', 7); pdf.cell(20, 5, "DIRECCION", border=1, fill=True)
                        pdf.set_font("Arial", '', 7); pdf.cell(115, 5, limpiar_texto(f" {dir_v}")[:85], border=1)
                        
                        y_datos += 5; pdf.set_xy(x_offset, y_datos)
                        pdf.set_font("Arial", 'B', 7); pdf.cell(20, 5, "SINIESTRO", border=1, fill=True)
                        pdf.set_font("Arial", 'B', 8); pdf.cell(45, 5, limpiar_texto(f" {siniestro_v}"), border=1)
                        pdf.set_font("Arial", 'B', 7); pdf.cell(20, 5, "VEHICULO", border=1, fill=True)
                        pdf.set_font("Arial", '', 7); pdf.cell(50, 5, limpiar_texto(f" {marca_v} {modelo_v}")[:35], border=1)

                        y_tabla = y_datos + 10; pdf.set_xy(x_offset, y_tabla); pdf.set_fill_color(0, 0, 0)
                        pdf.set_text_color(255, 255, 255); pdf.set_font("Arial", 'B', 7)
                        pdf.cell(15, 6, "CANT", border=1, fill=True, align='C')
                        pdf.cell(120, 6, "DESCRIPCION", border=1, fill=True, align='C')

                        y_item = y_tabla + 6
                        pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", '', 7)
                        for _, row_rem in df_g.iterrows():
                            cant_v = str(row_rem.get(col_cant, 1))
                            if not cant_v.strip() or cant_v == 'nan': cant_v = '1'
                            pdf.set_xy(x_offset, y_item)
                            pdf.cell(15, 5, limpiar_texto(cant_v), border=1, align='C')
                            pdf.cell(120, 5, limpiar_texto(str(row_rem.get(col_desc, '')))[:80], border=1)
                            y_item += 5
                            
                        pdf.set_xy(x_offset, 192); pdf.set_font("Arial", 'I', 6); pdf.set_text_color(120, 120, 120)
                        pdf.cell(135, 4, limpiar_texto(firma_digital), align='R')

                    dibujar_bloque_remision(10)
                    pdf.set_draw_color(180, 180, 180); pdf.line(148.5, 10, 148.5, 200); pdf.set_draw_color(0, 0, 0)
                    dibujar_bloque_remision(152)

                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        pdf.output(tmp.name)
                        nombre_archivo = f"Remision_{folio_str_print.replace(' - ', '_')}_{siniestro_v}.pdf"
                        with open(tmp.name, "rb") as f: pdf_bytes = f.read()
                        
                        pdfs_list.append({
                            'folio': folio_str_print,
                            'siniestro': siniestro_v,
                            'bytes': pdf_bytes,
                            'nombre': nombre_archivo
                        })

                # Guardamos los PDFs directamente en la sesión
                st.session_state['pdfs_list'] = pdfs_list
                if avisos_unicos: st.session_state['avisos_remision'] = list(avisos_unicos)
            
            st.toast("✅ ¡Bases actualizadas exitosamente en la nube!", icon="✅")
            st.cache_data.clear()
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Error guardando: {e}")
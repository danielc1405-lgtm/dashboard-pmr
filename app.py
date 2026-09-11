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
from google.oauth2.service_account import Credentials

warnings.filterwarnings("ignore")

st.set_page_config(
    page_title="Dashboard PMR - Operación",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
        [data-testid="stDataFrame"] { zoom: 0.95; }
        .block-container { 
            padding-top: 1rem !important; 
            padding-bottom: 40px; 
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            max-width: 100% !important; 
        }
        header { visibility: hidden; }
        
        /* HACK PARA CONGELAR EL ENCABEZADO */
        div[data-testid="stVerticalBlock"] > div:has(div.stRadio) {
            position: sticky;
            top: 0px;
            z-index: 999;
            background-color: #0E1117; 
            padding-top: 15px;
            padding-bottom: 15px;
            border-bottom: 1px solid #333;
        }
        
        div.row-widget.stRadio > div { flex-direction: row; gap: 8px; flex-wrap: wrap; }
        div.row-widget.stRadio > div > label { 
            background-color: #1E1E24; 
            padding: 6px 14px; 
            border-radius: 6px; 
            cursor: pointer; 
            border: 1px solid #333; 
            font-size: 0.95rem;
            transition: all 0.3s ease;
        }
        div.row-widget.stRadio > div > label:hover { border-color: #F63366; background-color: #2A2A35;}
        div.row-widget.stRadio > div > label[data-checked="true"] { 
            background-color: #F63366; 
            color: white; 
            border-color: #F63366; 
        }
        div.row-widget.stRadio > div > label > div:first-child { display: none; }
        
        .header-coqueto {
            background: linear-gradient(90deg, #1A1A24 0%, #262730 100%);
            padding: 12px 20px;
            border-radius: 8px;
            border-left: 6px solid;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.2);
        }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# === [BLOQUE 0: CONEXIÓN TEMPRANA Y SISTEMA DE LOGIN] ===
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

# ==============================================================================
# === [BLOQUE 2: MENÚ UX COQUETO, FIJO Y HEADER PRINCIPAL] ===
# ==============================================================================
rol_usuario = str(st.session_state.get('rol', st.session_state.get('rol_actual', 'Visor')))
nombre_usuario = str(st.session_state.get('usuario_actual', 'Demo'))

if "VISOR" in nombre_usuario.upper() or "DEMO" in str(st.session_state.get('usuario', '')).upper():
    rol_usuario = "Visor"

# FILA 1: LOGO, NAVEGACIÓN Y CONTROLES (Esta fila es la que se queda congelada)
col_logo, col_menu, col_chk, col_btn, col_out = st.columns([1.2, 5.8, 1.2, 1.2, 0.6], vertical_alignment="center")

with col_logo:
    if os.path.exists("logo.png"): st.image("logo.png", width=110)

with col_menu:
    opciones_menu = ["📊 Analítico", "⚙️ Panel Operativo", "🛒 Compras", "🏢 Talleres", "📦 Inventario", "🧾 Facturación"]
    vista_actual = st.radio("Nav:", opciones_menu, horizontal=True, label_visibility="collapsed")

es_visor = "VISOR" in rol_usuario.upper()
with col_chk:
    modo_consulta = st.checkbox("Solo Lectura", value=True if es_visor else False, disabled=es_visor)
permiso_edicion = not modo_consulta

with col_btn:
    btn_guardar = st.button("💾 Guardar", use_container_width=True, type="primary", disabled=not permiso_edicion)

with col_out:
    if st.button("🚪", help="Cerrar Sesión"):
        st.session_state.clear()
        st.rerun()

# FILA 2: HEADER COQUETO (Aseguradora grande y Vista)
aseguradora_sel = st.selectbox("Selecciona Aseguradora:", ["Multiasistencias", "GNP"], label_visibility="collapsed")
    
color_aseg = "#00FF00" if aseguradora_sel == "Multiasistencias" else "#00AEEF"
border_color = color_aseg

st.markdown(f"""
    <div class="header-coqueto" style="border-left-color: {border_color};">
        <div>
            <h3 style="margin:0; padding:0; color:white; font-size: 1.6rem;">
                {vista_actual}
            </h3>
            <span style="color:#aaa; font-size:0.85rem;">👤 {nombre_usuario} | 🛡️ {rol_usuario}</span>
        </div>
        <div style="text-align: right;">
            <h2 style="margin:0; padding:0; color:{color_aseg}; font-size: 2rem; letter-spacing: 1px;">
                {aseguradora_sel.upper()}
            </h2>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- SISTEMA NATIVO DE DESCARGA DE PDFS ---
if st.session_state.get('pdfs_list') or st.session_state.get('avisos_remision'):
    for aviso in st.session_state.get('avisos_remision', []):
        st.warning(aviso)
    
    if st.session_state.get('pdfs_list'):
        cols_pdf = st.columns(len(st.session_state['pdfs_list']) + 1)
        for i, pdf_obj in enumerate(st.session_state['pdfs_list']):
            with cols_pdf[i]:
                st.download_button(
                    label=f"📥 {pdf_obj['folio']}",
                    data=pdf_obj['bytes'],
                    file_name=pdf_obj['nombre'],
                    mime="application/pdf",
                    key=f"btn_pdf_dl_{i}"
                )
        with cols_pdf[-1]:
            if st.button("✅ Limpiar Bandeja", type="primary"):
                st.session_state['pdfs_list'] = []
                st.session_state['avisos_remision'] = []
                st.rerun()

# ==============================================================================
# === [BLOQUE 3: CARGA Y PROCESAMIENTO DE DATOS] ===
# ==============================================================================
def obtener_dataframe(nombre_hoja):
    try:
        doc = init_connection()
        ws = doc.worksheet(nombre_hoja)
        datos = ws.get_all_values()
        if not datos: return pd.DataFrame()
        headers = [str(h).strip() for h in datos[0]]
        df = pd.DataFrame(datos[1:], columns=headers)
        return df
    except Exception as e:
        st.error(f"Error cargando hoja {nombre_hoja}: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=10)
def cargar_datos():
    df_uni = obtener_dataframe("BD_UNIFICADA")
    df_comp = obtener_dataframe("BD_COMPRAS")
    
    df_cat = obtener_dataframe("BD_TALLERES")
    if df_cat.empty:
        df_cat = obtener_dataframe("Catálogo")
        
    try: 
        df_inv = obtener_dataframe("BD_INVENTARIO")
        if not df_inv.empty and 'Sin Existencia' in df_inv.columns:
            df_inv['Sin Existencia'] = df_inv['Sin Existencia'].astype(str).str.strip().str.upper().isin(['TRUE', 'SI', '1', 'X', 'V', 'VERDADERO'])
    except: 
        df_inv = pd.DataFrame()
        
    if not df_uni.empty:
        if 'Siniestro Relacionado' in df_uni.columns:
            df_uni.rename(columns={'Siniestro Relacionado': 'Siniestro'}, inplace=True)
            
    return df_uni, df_comp, df_cat, df_inv

df_completo, df_compras, df_catalogo, df_inventario = cargar_datos()

aseguradora_filtro = aseguradora_sel.strip().upper()
palabra_clave_aseg = "MULTI" if "MULTI" in aseguradora_filtro else "GNP"

if not df_completo.empty:
    col_aseg_val = next((c for c in df_completo.columns if "ASEGURADORA" in str(c).upper()), None)
    if col_aseg_val:
        df_trabajo_completo = df_completo[df_completo[col_aseg_val].astype(str).str.upper().str.contains(palabra_clave_aseg, na=False)].copy()
        if df_trabajo_completo.empty:
            df_trabajo_completo = df_completo.copy()
    else:
        df_trabajo_completo = df_completo.copy()
else:
    df_trabajo_completo = pd.DataFrame()

if not df_trabajo_completo.empty:
    col_id = next((c for c in df_trabajo_completo.columns if "SINIESTRO" in str(c).upper()), None)
    col_taller = next((c for c in df_trabajo_completo.columns if "TALLER" in str(c).upper()), None)
    col_marca = next((c for c in df_trabajo_completo.columns if "MARCA" in str(c).upper()), None)
    col_modelo = next((c for c in df_trabajo_completo.columns if "MODELO" in str(c).upper()), None)
    col_desc = next((c for c in df_trabajo_completo.columns if "DESCRIPCI" in str(c).upper() or "REFACCI" in str(c).upper()), None)
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

    df_trabajo_completo['Filtro_Siniestro'] = df_trabajo_completo[col_id].astype(str) + " - " + df_trabajo_completo[col_marca].astype(str) + " " + df_trabajo_completo[col_modelo].astype(str)
    df_trabajo_completo['Vehiculo_Info'] = df_trabajo_completo[col_marca].astype(str) + " " + df_trabajo_completo[col_modelo].astype(str)
    
    df_trabajo = df_trabajo_completo.copy()
    df_proceso = df_trabajo[~df_trabajo[col_estatus].astype(str).str.upper().str.contains("CANCELADO|ENTREGADO|RECIBIDO|FACTURADO|REASIGNAR")].copy() if col_estatus else df_trabajo.copy()
    df_recoleccion_total = df_trabajo[df_trabajo[col_estatus].astype(str).str.upper().str.contains("REASIGNAR")].copy() if col_estatus else pd.DataFrame()
else:
    col_id = col_taller = col_marca = col_modelo = col_desc = col_cant = col_precio = col_estatus = col_vencimiento = col_asignacion = col_fecha_confi = col_guia = col_remision = col_comentarios = col_aseg = None
    df_trabajo = df_proceso = df_recoleccion_total = pd.DataFrame()


# ==============================================================================
# === [BLOQUE 4: VISTAS Y NOTIFICACIONES] ===
# ==============================================================================
df_editado_conf = pd.DataFrame()
df_editado_venc = pd.DataFrame()
df_editado_atrasadas = pd.DataFrame()
df_editado_cobro = pd.DataFrame()
df_editado_fact = pd.DataFrame()
df_editado = pd.DataFrame()

# --- SISTEMA DE NOTIFICACIONES GLOBALES (FRANJAS AMARILLAS) ---
if not modo_consulta:
    # 1. Alerta de Pedidos Nuevos (Provenientes de los Bots)
    if col_estatus and not df_trabajo_completo.empty:
        pendientes_bot = len(df_trabajo_completo[df_trabajo_completo[col_estatus].astype(str).str.upper().str.contains("CONFIRMAR")])
        if pendientes_bot > 0:
            st.warning(f"🚨 **¡ATENCIÓN!** Han ingresado **{pendientes_bot}** pedido(s) nuevo(s) por confirmar. Revisa el Panel Operativo.", icon="🚨")

    # 2. Alerta de Pedidos Recién Confirmados (Para proceder con surtido)
    if 'avisos_amarillos' in st.session_state and st.session_state['avisos_amarillos']:
        for aviso in st.session_state['avisos_amarillos']:
            st.warning(aviso, icon="🔔")
        
        # Botón para limpiar los avisos de surtido
        col_btn_aviso, _ = st.columns([2, 8])
        with col_btn_aviso:
            if st.button("✅ Enterado (Ocultar avisos)", use_container_width=True):
                st.session_state['avisos_amarillos'] = []
                st.rerun()

st.markdown("---") # Separador visual antes de cargar las vistas

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
                cols_mostrar = [c for c in [col_id, col_taller, col_estatus] if c in df_detalle.columns]
                st.dataframe(df_detalle[cols_mostrar], use_container_width=True, hide_index=True)
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
                    if text in d_str: d_str = d_str.replace(text, num); break
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
    kpi1.metric("📦 En Proceso (Piezas)", en_proceso)
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
    if col_id and col_id in df_filtrado.columns: base_config[col_id] = st.column_config.TextColumn("Siniestro")
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

    df_por_confirmar = df_filtrado[df_filtrado[col_estatus].astype(str).str.upper().str.contains("CONFIRMAR")].copy() if col_estatus else pd.DataFrame()
    with st.expander(f"⏳ Piezas por Confirmar | {len(df_por_confirmar)} Partida(s) en {df_por_confirmar[col_id].nunique() if (not df_por_confirmar.empty and col_id) else 0} Siniestro(s)", expanded=False):
        dfs_editados_conf = []
        if not df_por_confirmar.empty:
            for taller, df_taller in df_por_confirmar.groupby(col_taller):
                with st.expander(f"🏢 {taller} | {df_taller[col_id].nunique()} Siniestro(s)", expanded=False):
                    for siniestro_auto, df_grupo in df_taller.groupby(col_id):
                        st.markdown(f"**🚗 {siniestro_auto} | {df_grupo['Vehiculo_Info'].iloc[0]}**")
                        if not modo_consulta and permiso_edicion: 
                            df_grupo['Confirmar Surtido'] = False
                            df_grupo['Cancelar'] = False
                            cols_conf = [c for c in [col_cant, col_desc, col_asignacion, col_vencimiento, col_estatus, col_comentarios, 'Confirmar Surtido', 'Cancelar'] if c in df_grupo.columns]
                            config_conf = base_config.copy()
                            config_conf.update({"Confirmar Surtido": st.column_config.CheckboxColumn("✅ Confirmar", default=False), "Cancelar": st.column_config.CheckboxColumn("🚫 Can", default=False)})
                            
                            df_editado_parcial = st.data_editor(df_grupo[cols_conf], column_config=config_conf, disabled=[c for c in cols_conf if c not in ['Confirmar Surtido', 'Cancelar', col_comentarios]], hide_index=True, use_container_width=True, key=f"ed_conf_{taller}_{siniestro_auto}")
                            
                            for col in [col_id, col_taller, col_marca, col_modelo, col_desc]:
                                if col in df_grupo.columns: df_editado_parcial[col] = df_grupo[col].values
                            dfs_editados_conf.append(df_editado_parcial)
                        else:
                            cols_conf = [c for c in [col_cant, col_desc, col_asignacion, col_vencimiento, col_estatus, col_comentarios] if c in df_grupo.columns]
                            st.dataframe(df_grupo[cols_conf], column_config=base_config, hide_index=True, use_container_width=True)
        if dfs_editados_conf: df_editado_conf = pd.concat(dfs_editados_conf, ignore_index=True)

    df_vencimientos = df_filtrado[(df_filtrado[col_vencimiento] == hoy_str) & (~df_filtrado[col_estatus].astype(str).str.upper().str.contains("CONFIRMAR"))].copy() if col_vencimiento else pd.DataFrame()
    with st.expander(f"🚨 Vencimientos de Hoy | {len(df_vencimientos)} Partida(s) en {df_vencimientos[col_id].nunique() if (not df_vencimientos.empty and col_id) else 0} Siniestro(s)", expanded=False):
        if not df_vencimientos.empty:
            if not modo_consulta and permiso_edicion:
                df_vencimientos['Cancelar'] = False; df_vencimientos['Reasignar'] = False; df_vencimientos['Nueva Fecha'] = pd.NaT
                cols_venc = [c for c in [col_taller, col_id, 'Vehiculo_Info', col_cant, col_desc, col_precio, col_estatus, col_vencimiento, col_guia, col_comentarios, 'Cancelar', 'Reasignar', 'Nueva Fecha'] if c in df_vencimientos.columns]
                config_venc = base_config.copy()
                config_venc.update({"Cancelar": st.column_config.CheckboxColumn("🚫 Can", default=False), "Reasignar": st.column_config.CheckboxColumn("🔄 Reasig", default=False), "Nueva Fecha": st.column_config.DateColumn("📅 Nueva Fecha", format="DD/MMM/YYYY")})
                df_editado_venc = st.data_editor(df_vencimientos[cols_venc], column_config=config_venc, disabled=[c for c in cols_venc if c not in ['Cancelar', 'Reasignar', 'Nueva Fecha', col_comentarios, col_guia]], hide_index=True, use_container_width=True, key="ed_venc")
                for col in [col_id, col_marca, col_modelo]:
                    if col in df_vencimientos.columns: df_editado_venc[col] = df_vencimientos[col].values
            else:
                cols_venc = [c for c in [col_taller, col_id, 'Vehiculo_Info', col_cant, col_desc, col_precio, col_estatus, col_vencimiento, col_guia, col_comentarios] if c in df_vencimientos.columns]
                st.dataframe(df_vencimientos[cols_venc], column_config=base_config, hide_index=True, use_container_width=True)
                
    if col_vencimiento and not df_filtrado.empty:
        fechas_venc_filtro = df_filtrado[col_vencimiento].apply(parse_dt_safe)
        df_atrasadas = df_filtrado[(fechas_venc_filtro < hoy_dt) & (df_filtrado[col_vencimiento] != '') & (~df_filtrado[col_estatus].astype(str).str.upper().str.contains("CONFIRMAR"))].copy()
    else:
        df_atrasadas = pd.DataFrame()
    with st.expander(f"❌ Vencimientos Atrasados | {len(df_atrasadas)} Partida(s) en {df_atrasadas[col_id].nunique() if (not df_atrasadas.empty and col_id) else 0} Siniestro(s)", expanded=False):
        if not df_atrasadas.empty:
            if not modo_consulta and permiso_edicion:
                df_atrasadas['Cancelar'] = False; df_atrasadas['Reasignar'] = False; df_atrasadas['Nueva Fecha'] = pd.NaT
                cols_atr = [c for c in [col_taller, col_id, 'Vehiculo_Info', col_cant, col_desc, col_precio, col_estatus, col_vencimiento, col_comentarios, 'Cancelar', 'Reasignar', 'Nueva Fecha'] if c in df_atrasadas.columns]
                config_atr = base_config.copy()
                config_atr.update({"Cancelar": st.column_config.CheckboxColumn("🚫 Can", default=False), "Reasignar": st.column_config.CheckboxColumn("🔄 Reasig", default=False), "Nueva Fecha": st.column_config.DateColumn("📅 Nueva Fecha", format="DD/MMM/YYYY")})
                df_editado_atrasadas = st.data_editor(df_atrasadas[cols_atr], column_config=config_atr, disabled=[c for c in cols_atr if c not in ['Cancelar', 'Reasignar', 'Nueva Fecha', col_comentarios]], hide_index=True, use_container_width=True, key="ed_atr")
                for col in [col_id, col_marca, col_modelo]:
                    if col in df_atrasadas.columns: df_editado_atrasadas[col] = df_atrasadas[col].values
            else:
                cols_atr = [c for c in [col_taller, col_id, 'Vehiculo_Info', col_cant, col_desc, col_precio, col_estatus, col_vencimiento, col_comentarios] if c in df_atrasadas.columns]
                st.dataframe(df_atrasadas[cols_atr], column_config=base_config, hide_index=True, use_container_width=True)

    df_por_cobrar = df_filtrado[df_filtrado[col_estatus].astype(str).str.upper() == "ENTREGADO"].copy() if col_estatus else pd.DataFrame()
    with st.expander(f"💰 Por Cobrar (Entregados) | {len(df_por_cobrar)} Partida(s) en {df_por_cobrar[col_id].nunique() if (not df_por_cobrar.empty and col_id) else 0} Siniestro(s)", expanded=False):
        if not df_por_cobrar.empty:
            if not modo_consulta and permiso_edicion:
                df_por_cobrar['Marcar Recibido'] = False
                cols_cobro = [c for c in [col_taller, col_id, 'Vehiculo_Info', col_cant, col_desc, col_precio, col_estatus, col_comentarios, 'Marcar Recibido'] if c in df_por_cobrar.columns]
                config_cobro = base_config.copy()
                config_cobro.update({"Marcar Recibido": st.column_config.CheckboxColumn("🏁 Marcar Recibido", default=False)})
                df_editado_cobro = st.data_editor(df_por_cobrar[cols_cobro], column_config=config_cobro, disabled=[c for c in cols_cobro if c not in ['Marcar Recibido', col_comentarios]], hide_index=True, use_container_width=True, key="ed_cobro")
                for col in [col_id, col_desc]: 
                    if col in df_por_cobrar.columns: df_editado_cobro[col] = df_por_cobrar[col].values
            else:
                cols_cobro = [c for c in [col_taller, col_id, 'Vehiculo_Info', col_cant, col_desc, col_precio, col_estatus, col_comentarios] if c in df_por_cobrar.columns]
                st.dataframe(df_por_cobrar[cols_cobro], column_config=base_config, hide_index=True, use_container_width=True)

    if col_estatus and col_estatus in df_filtrado.columns:
        mask_asignados = ~df_filtrado[col_estatus].fillna('').astype(str).str.upper().str.contains("CONFIRMAR|ENTREGADO|RECIBIDO|FACTURADO|CANCELADO")
        df_asignados = df_filtrado[mask_asignados].copy()
    else:
        df_asignados = df_filtrado.copy()
    
    with st.expander(f"📋 Pedidos Asignados (General) | {len(df_asignados)} Partida(s) en {df_asignados[col_id].nunique() if (not df_asignados.empty and col_id) else 0} Siniestro(s)", expanded=False):
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
                with st.expander(f"🏢 {taller} | {df_taller[col_id].nunique()} Siniestro(s)", expanded=False):
                    for siniestro_auto, df_grupo in df_taller.groupby(col_id):
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
                            for col in [col_id, col_taller, col_marca, col_modelo, col_desc, 'Vehiculo_Info']:
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
        df_recoleccion = df_recoleccion[df_recoleccion[col_id].isin(ids_sel)]
    if desc_sel: df_recoleccion = df_recoleccion[df_recoleccion[col_desc].astype(str).isin(desc_sel)]

    with st.expander(f"↩️ Piezas para Recolección | {len(df_recoleccion)} Partida(s) en {df_recoleccion[col_id].nunique() if (not df_recoleccion.empty and col_id) else 0} Siniestro(s)", expanded=False):
        if not df_recoleccion.empty:
            cols_rec = [c for c in [col_taller, col_id, 'Vehiculo_Info', col_desc, col_cant, col_precio, col_estatus, col_vencimiento, col_comentarios] if c in df_recoleccion.columns]
            st.dataframe(df_recoleccion[cols_rec], column_config=base_config, hide_index=True, use_container_width=True)

# ==============================================================================
# === [BLOQUE 6: VISTA 3 - PEDIDOS Y PROVEEDORES] ===
# ==============================================================================
if vista_actual == "🛒 Compras":
    st.markdown("### 🛒 Panel de Compras (Gestión y Pagos)")
    
    try: df_proveedores = cargar_datos.__wrapped__() if False else obtener_dataframe("BD_PROVEEDORES")
    except Exception: df_proveedores = pd.DataFrame()
    
    if not df_compras.empty:
        for c in ['Condición Pago', 'Días Crédito', 'Estatus Pago']:
            if c not in df_compras.columns: df_compras[c] = ""
            
        df_compras['Recibido_Bool'] = df_compras['Recibido'].astype(str).str.strip().str.upper().isin(['TRUE', 'SI', '1', 'YES', 'V', 'X'])
        df_compras_disp = df_compras[(df_compras['Recibido_Bool'] == False) | (df_compras['Estatus Pago'].astype(str).str.upper() != 'PAGADO')].copy()
        
        if not df_compras_disp.empty:
            df_compras_disp = df_compras_disp.drop(columns=['Recibido_Bool'])
            
            if not df_proveedores.empty and 'Condición Pago' in df_proveedores.columns:
                dict_prov = df_proveedores.set_index('Proveedor').to_dict('index')
                
                def auto_cond(row):
                    if str(row['Condición Pago']).strip() in ["", "nan", "None"] and row['Proveedor'] in dict_prov:
                        return str(dict_prov[row['Proveedor']].get('Condición Pago', ''))
                    return row['Condición Pago']
                    
                def auto_dias(row):
                    val = str(row['Días Crédito']).strip()
                    if val in ["", "0", "nan", "None"] and row['Proveedor'] in dict_prov:
                        dias = dict_prov[row['Proveedor']].get('Días Crédito', '0')
                        return dias if str(dias).isdigit() else 0
                    return row['Días Crédito']

                df_compras_disp['Condición Pago'] = df_compras_disp.apply(auto_cond, axis=1)
                df_compras_disp['Días Crédito'] = df_compras_disp.apply(auto_dias, axis=1)
            
            df_compras_disp['Estatus Pago'] = df_compras_disp['Estatus Pago'].apply(lambda x: "Pendiente" if str(x).strip() in ["", "nan", "None"] else x)
            
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
            
            df_compras_disp['Fecha Llegada'] = df_compras_disp['Llegada_Calculada'].dt.strftime('%d/%b/%y').fillna('-')
            
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
            df_compras_disp = df_compras_disp.sort_values(by='Llegada_Calculada', ascending=True)

            df_compras_disp['Filtro_Busqueda'] = df_compras_disp['Siniestro'].astype(str) + " | " + df_compras_disp['Descripción Pieza'].astype(str)
            
            col_b1, col_b2, col_b3 = st.columns(3)
            with col_b1:
                lista_pedidos = sorted(list(df_compras_disp['Filtro_Busqueda'].unique()))
                busqueda_pedido = st.multiselect("🔍 Buscar Siniestro/Pieza:", options=lista_pedidos, key="ms_comp_ped")
            with col_b2:
                df_compras_disp['Taller_Filtro'] = df_compras_disp['Taller'].replace('', 'SIN ASIGNAR')
                lista_talleres = sorted(list(df_compras_disp['Taller_Filtro'].unique()))
                busqueda_taller = st.multiselect("🏢 Filtrar por Taller (CDR):", options=lista_talleres, key="ms_comp_tall")
            with col_b3:
                df_compras_disp['Prov_Filtro'] = df_compras_disp['Proveedor'].replace('', 'SIN ASIGNAR')
                lista_provs = sorted(list(df_compras_disp['Prov_Filtro'].unique()))
                busqueda_prov = st.multiselect("🏭 Filtrar por Proveedor:", options=lista_provs, key="ms_comp_prov")

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
    
    if permiso_edicion:
        with st.expander("➕ Registrar Nuevo Proveedor", expanded=False):
            with st.form("form_proveedores", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                p_prov = c1.text_input("Proveedor * (Obligatorio)")
                p_suc = c2.text_input("Sucursal")
                p_tiempo = c3.text_input("Tiempo de Entrega (Ej. 5 a 7 días)")
                
                c_f1, c_f2 = st.columns(2)
                p_cond = c_f1.selectbox("Condición de Pago por Defecto", options=["", "Crédito", "Previo", "Anticipo", "Contra Entrega"])
                p_dias = c_f2.number_input("Días de Crédito (Si aplica)", min_value=0, step=1)
                
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
                            ws_p.append_row([p_prov.upper(), p_suc.upper(), p_dir.upper(), p_tiempo.upper(), p_contacto.upper(), p_tel, p_correo, p_cond, str(p_dias)])
                            st.success(f"✅ Proveedor '{p_prov}' guardado exitosamente en la nube.")
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                        except Exception as e: st.error(f"❌ Error al guardar en la nube: {e}")
                        
    if not df_proveedores.empty: 
        cols_mostrar_prov = [c for c in ['Proveedor', 'Sucursal', 'Tiempo de Entrega', 'Contacto', 'Condición Pago', 'Días Crédito'] if c in df_proveedores.columns]
        st.dataframe(df_proveedores[cols_mostrar_prov].fillna(""), use_container_width=True, hide_index=True)

# ==============================================================================
# === [BLOQUE 7: VISTAS 4 Y 5 - TALLERES E INVENTARIO] ===
# ==============================================================================
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

# ==============================================================================
# === [BLOQUE 8: VISTA 5 - FACTURACIÓN] ===
# ==============================================================================
if vista_actual == "🧾 Facturación":
    st.markdown("### 🧾 Pedidos Listos para Facturar")
    
    if col_estatus and not df_trabajo_completo.empty:
        # Filtramos solo lo que ya fue RECIBIDO por el Taller
        df_fact = df_trabajo_completo[df_trabajo_completo[col_estatus].astype(str).str.strip().str.upper() == "RECIBIDO"].copy()
        
        if not df_fact.empty:
            df_fact['Facturado'] = False
            dfs_editados_fact = []
            
            # Agrupamos por taller para mantener la vista ordenada y limpia
            for taller, df_taller in df_fact.groupby(col_taller):
                with st.expander(f"🏢 {taller} | {len(df_taller)} Partida(s) pendiente(s)", expanded=True):
                    if not modo_consulta and permiso_edicion:
                        cols_fact = [c for c in [col_id, 'Vehiculo_Info', col_desc, col_cant, col_precio, col_comentarios, 'Facturado'] if c in df_taller.columns]
                        
                        config_fact = {
                            col_id: st.column_config.TextColumn("Siniestro", disabled=True),
                            'Vehiculo_Info': st.column_config.TextColumn("Vehículo", disabled=True),
                            col_desc: st.column_config.TextColumn("Descripción", disabled=True),
                            col_cant: st.column_config.TextColumn("Cant", disabled=True),
                            col_precio: st.column_config.TextColumn("Precio", disabled=True),
                            col_comentarios: st.column_config.TextColumn("Observaciones", disabled=True),
                            'Facturado': st.column_config.CheckboxColumn("🧾 Facturar")
                        }
                        
                        df_ed_fact = st.data_editor(
                            df_taller[cols_fact], 
                            column_config=config_fact, 
                            disabled=[c for c in cols_fact if c != 'Facturado'], 
                            hide_index=True, 
                            use_container_width=True, 
                            key=f"ed_fact_{taller}"
                        )
                        
                        for col in [col_id, col_desc]:
                            if col in df_taller.columns:
                                df_ed_fact[col] = df_taller[col].values
                                
                        dfs_editados_fact.append(df_ed_fact)
                    else:
                        cols_mostrar = [c for c in [col_id, 'Vehiculo_Info', col_desc, col_cant, col_precio, col_comentarios] if c in df_taller.columns]
                        st.dataframe(df_taller[cols_mostrar], hide_index=True, use_container_width=True)
            
            if dfs_editados_fact:
                df_editado_fact = pd.concat(dfs_editados_fact, ignore_index=True)
        else:
            st.success("✅ No hay pedidos pendientes de facturación en este momento.")
    else:
        st.warning("No hay datos cargados para facturación.")

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
            k = generar_llave(row.get(col_id, ''), row.get(col_desc, ''))
            orig = originales.get(k, {'comentario': '', 'estatus_db': ''})
            nuevo_estatus = "CANCELADO" if row.get('Cancelar') else ("EN PROCESAMIENTO" if row.get('Confirmar Surtido') else None)
            comentario_actual = str(row.get(col_comentarios, '')).strip()
            
            if nuevo_estatus and nuevo_estatus != orig['estatus_db']: 
                cambios_a_guardar.setdefault(k, {})['estatus'] = nuevo_estatus
                if nuevo_estatus == "EN PROCESAMIENTO":
                    cambios_a_guardar[k]['fecha_confi'] = fecha_hoy_sistema
                    
                    # --- NUEVO: REGISTRAR AVISO AMARILLO DE SURTIDO ---
                    if 'avisos_amarillos' not in st.session_state:
                        st.session_state['avisos_amarillos'] = []
                    mensaje_exito = f"Pedido **{k[0]}** confirmado. Proceder con surtido."
                    if mensaje_exito not in st.session_state['avisos_amarillos']:
                        st.session_state['avisos_amarillos'].append(mensaje_exito)
                    
            if comentario_actual != orig['comentario']: 
                cambios_a_guardar.setdefault(k, {})['comentario'] = comentario_actual

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
            elif row.get('Reasignar') and not nuevo_estatus:
                nuevo_estatus = "EN PROCESAMIENTO"
            
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
            elif row.get('Reasignar') and not nuevo_estatus:
                nuevo_estatus = "EN PROCESAMIENTO"
            
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
            if comentario_actual != orig['comentario']: 
                cambios_a_guardar.setdefault(k, {})['comentario'] = comentario_actual

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
                            # --- LA NUEVA LÓGICA SENIOR INFALIBLE ---
                            pref = "MULTI" if str(siniestro_id).upper().startswith('B') else "GNP"
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

                st.session_state['pdfs_list'] = pdfs_list
                if avisos_unicos: st.session_state['avisos_remision'] = list(avisos_unicos)
            
            st.toast("✅ ¡Bases actualizadas exitosamente en la nube!", icon="✅")
            st.cache_data.clear()
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Error guardando: {e}")
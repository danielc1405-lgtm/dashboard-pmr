# === [BLOQUE 1: IMPORTS, CONFIGURACIÓN VISUAL Y CSS] ===
import streamlit as st
import pandas as pd
import warnings
import time
import openpyxl
import os
import shutil
import datetime
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
            padding-top: 2rem; 
            padding-bottom: 40px; 
            max-width: 98% !important; 
        }
        @media (min-width: 768px) {
            div.element-container:has(#panel-fijo) + div {
                position: sticky; top: 2.875rem; z-index: 999;
                background-color: #0e1117; padding-top: 10px; padding-bottom: 15px;
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

st.sidebar.success(f"👤 Operador activo:\n**{st.session_state['usuario_actual']}**")
if st.sidebar.button("🚪 Cerrar Sesión"):
    st.session_state['autenticado'] = False
    st.rerun()
# =====================================================================


# =====================================================================
# === [NUEVO ORDEN: CARGA DE DATOS ANTES DEL GRÁFICO] ===
# =====================================================================
def obtener_dataframe(nombre_hoja):
    try:
        doc = init_connection()
        ws = doc.worksheet(nombre_hoja)
        datos = ws.get_all_values()
        if not datos: return pd.DataFrame()
        
        # Prevenir columnas duplicadas o vacías desde Sheets
        headers = [str(h).strip() for h in datos[0]]
        for i in range(len(headers)):
            if headers[i] == "": headers[i] = f"Unnamed_{i}"
            
        df = pd.DataFrame(datos[1:], columns=headers)
        return df
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


# === BLOQUE 2. GRÁFICO: ESTADO GENERAL DE PARTIDAS EN PROCESO ===
st.markdown("### 2. Estado General de Partidas en Proceso")

# Excluimos de la base principal (df_completo) todo lo que ya no está activo
estatus_excluidos = ['RECIBIDA', 'FACTURADA', 'FINALIZADA', 'ENTREGADA', 'CANCELADA']

# SECCIÓN CORREGIDA Y PROTEGIDA: Usa df_completo y verifica que existan las columnas para evitar errores extra
if not df_completo.empty and 'Estatus' in df_completo.columns and 'Fecha de Vencimiento' in df_completo.columns:
    df_grafico = df_completo[~df_completo['Estatus'].isin(estatus_excluidos)]
    
    if not df_grafico.empty:
        col_graf, col_det = st.columns([2, 1])
        
        with col_graf:
            # Agrupamos los datos para el gráfico
            df_agrupado = df_grafico.groupby(['Fecha de Vencimiento', 'Estatus']).size().reset_index(name='Cantidad de Partidas')
            
            # Generamos el gráfico de barras apiladas
            fig = px.bar(
                df_agrupado, 
                x='Fecha de Vencimiento', 
                y='Cantidad de Partidas', 
                color='Estatus',
                barmode='stack',
                color_discrete_sequence=["#1E88E5", "#64B5F6", "#0D47A1", "#1976D2", "#90CAF9"]
            )
            
            # Hacemos que el gráfico responda a clics
            grafico_seleccion = st.plotly_chart(fig, use_container_width=True, on_select="rerun")
            
        with col_det:
            st.markdown("📄 **Detalle de Partidas**")
            
            # Si el usuario hace clic en una barra, mostramos los detalles
            if grafico_seleccion and len(grafico_seleccion.selection.points) > 0:
                # Obtenemos la fecha a la que le hicieron clic
                fecha_sel = grafico_seleccion.selection.points[0]["x"]
                
                # Filtramos la tabla de detalles
                df_detalle = df_grafico[df_grafico['Fecha de Vencimiento'] == fecha_sel]
                
                st.dataframe(
                    df_detalle[['Siniestro', 'Taller', 'Estatus']], 
                    use_container_width=True, 
                    hide_index=True
                )
            else:
                st.info("👆 Haz clic en una barra del gráfico para filtrar la tabla.")
    else:
        st.success("No hay partidas en proceso en este momento.")
elif not df_completo.empty:
    st.warning("⚠️ No se pudieron graficar los datos. Verifica que las columnas 'Estatus' y 'Fecha de Vencimiento' existan en el archivo de base de datos.")


# INICIALIZACIÓN SEGURA DE VARIABLES
df_proceso = pd.DataFrame()
df_trabajo = pd.DataFrame()
df_trabajo_completo = pd.DataFrame()
df_recoleccion_total = pd.DataFrame()
df_vista = pd.DataFrame()

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
            if any(s in c_upper for s in substrings) and "DÍAS" not in c_upper and "DIAS" not in c_upper:
                return c
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
    
    columnas_base = [c for c in [col_id, col_taller, col_marca, col_modelo, col_anio, col_serie, col_desc, col_precio, col_cant,
                                 col_remision, col_asignacion, col_vencimiento, col_fecha_confi, col_estatus, col_comentarios, col_guia, col_aseg, col_origen] if c is not None]
    
    if columnas_base:
        df_trabajo_completo = df_completo[columnas_base].copy()
        df_trabajo = df_vista[columnas_base].copy()             
        
        df_trabajo = df_trabajo[df_trabajo[col_id].notna()]
        df_trabajo = df_trabajo[df_trabajo[col_id].astype(str).str.strip() != '']
        df_trabajo = df_trabajo[df_trabajo[col_id].astype(str).str.lower() != 'nan']
        
        # LIMPIEZA DE PRECIOS (De texto de Google Sheets a números limpios)
        if col_precio and col_precio in df_trabajo.columns:
            df_trabajo[col_precio] = pd.to_numeric(df_trabajo[col_precio].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce').fillna(0)
            df_trabajo_completo[col_precio] = pd.to_numeric(df_trabajo_completo[col_precio].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce').fillna(0)

        for c_fecha in [col_asignacion, col_vencimiento, col_fecha_confi]:
            if c_fecha and c_fecha in df_trabajo.columns:
                fechas_dt = pd.to_datetime(df_trabajo[c_fecha], errors='coerce', dayfirst=True)
                df_trabajo[c_fecha] = fechas_dt.dt.strftime('%d-%b-%y').fillna('')
                
        for c_txt in [col_remision, col_comentarios, col_estatus, col_guia, col_origen]:
            if c_txt and c_txt in df_trabajo.columns:
                df_trabajo[c_txt] = df_trabajo[c_txt].fillna('').astype(str).replace(['nan', 'None'], '')
                
        if col_guia not in df_trabajo.columns:
            df_trabajo['Guía'] = ""
            col_guia = 'Guía'
            
        def limpiar_guia_display(g):
            g = str(g).strip()
            if g.startswith('=HYPERLINK'):
                g = g.split(',')[-1].replace('"', '').replace(')', '').strip()
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
            if val_str.endswith('.0'): return val_str[:-2]
            return val_str

        if col_id:
            df_proceso['Siniestro'] = df_proceso[col_id].apply(limpiar_siniestro)
            df_trabajo_completo['Siniestro'] = df_trabajo_completo[col_id].apply(limpiar_siniestro)
        else:
            df_proceso['Siniestro'] = ""

        def formatear_vehiculo(row):
            vehiculo = f"{row.get(col_marca, '')} {row.get(col_modelo, '')}".strip()
            anio = ""
            if col_anio and pd.notnull(row.get(col_anio)):
                try:
                    anio = str(int(float(row[col_anio])))
                except ValueError:
                    anio = str(row[col_anio]).strip()
            if anio and anio.lower() not in ['nan', 'none', '']:
                vehiculo += f" {anio}"
            serie = str(row.get(col_serie, '')).strip() if col_serie else ""
            if serie and serie.lower() not in ['nan', 'none', '']:
                vehiculo += f" - {serie}"
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
    if 'Recibido' not in df_compras.columns:
        df_compras['Recibido'] = False
    else:
        df_compras['Recibido'] = df_compras['Recibido'].astype(str).str.strip().str.upper().isin(['TRUE', 'SI', '1', 'YES', 'V', 'X'])

if not df_inventario.empty:
    if 'Sin Existencia' not in df_inventario.columns:
        df_inventario['Sin Existencia'] = False
    else:
        df_inventario['Sin Existencia'] = df_inventario['Sin Existencia'].astype(str).str.strip().str.upper().isin(['TRUE', 'SI', '1', 'YES', 'V', 'X'])

# Variables Globales de Edición
df_editado_conf = pd.DataFrame()
df_editado_venc = pd.DataFrame()
df_editado_atrasadas = pd.DataFrame()
df_editado_cobro = pd.DataFrame()
df_editado = pd.DataFrame()
df_editado_compras = pd.DataFrame()
df_compras_disp = pd.DataFrame()
df_editado_catalogo = pd.DataFrame()
df_cat_disp = pd.DataFrame()
df_editado_inventario = pd.DataFrame()
df_inv_disp = pd.DataFrame()
df_editado_fact = pd.DataFrame() 
hubo_cambios_catalogo = False
hubo_cambios_inventario = False


# === [BLOQUE 4: VISTA 1 - ANALÍTICO] ===
if vista_actual == "📊 Analítico":
    st.markdown("## 📊 Rendimiento de Operación")
    
    # --- 1. PEDIDOS POR LLEGAR (DESDE BD_COMPRAS) ---
    st.markdown("#### 1. Pedidos por Llegar (Compras a Proveedores)")
    
    if not df_compras.empty:
        df_compras['Recibido_Bool'] = df_compras['Recibido'].astype(str).str.strip().str.upper().isin(['TRUE', 'SI', '1', 'YES', 'V', 'X'])
        df_compras_llegar = df_compras[df_compras['Recibido_Bool'] == False].copy()
        
        if not df_compras_llegar.empty:
            df_compras_llegar = df_compras_llegar.drop(columns=['Recibido_Bool'])
            
            # CÁLCULO DINÁMICO: Fecha de Llegada = Compra + Días
            df_compras_llegar['Fecha_Compra_Dt'] = pd.to_datetime(df_compras_llegar['Fecha Compra'], format='%d-%b-%y', errors='coerce')
            df_compras_llegar['ETA_Dias'] = pd.to_numeric(df_compras_llegar['Tiempo Entrega (Días)'], errors='coerce').fillna(0)
            df_compras_llegar['Llegada_Calculada'] = df_compras_llegar['Fecha_Compra_Dt'] + pd.to_timedelta(df_compras_llegar['ETA_Dias'], unit='d')
            
            # ORDENAMIENTO: Del más próximo a llegar al más lejano
            df_compras_llegar = df_compras_llegar.sort_values(by='Llegada_Calculada', ascending=True)
            
            # ALERTA DE ATRASO
            hoy_comparacion = pd.to_datetime(datetime.datetime.now().date())
            df_compras_llegar['Estatus'] = df_compras_llegar['Llegada_Calculada'].apply(
                lambda x: "🔴 Atrasado" if pd.notna(x) and x < hoy_comparacion else "🟢 En tiempo"
            )
            
            df_compras_llegar['Fecha Llegada'] = df_compras_llegar['Llegada_Calculada'].dt.strftime('%d-%b-%y').fillna('-')
            
            cols_llegar = [c for c in ['Siniestro', 'Taller', 'Vehículo', 'Descripción Pieza', 'Proveedor', 'Fecha Compra', 'Tiempo Entrega (Días)', 'Fecha Llegada', 'Estatus'] if c in df_compras_llegar.columns]
            st.dataframe(df_compras_llegar[cols_llegar], use_container_width=True, hide_index=True)
        else:
            st.info("✅ Todos los pedidos a proveedores han sido recibidos.")
    else:
        st.warning("No hay datos en la base de Compras.")
    
    st.markdown("<hr style='border: 1px solid #333; margin: 30px 0;'>", unsafe_allow_html=True)
    
    if not df_proceso.empty and col_estatus:
        # --- 2. VENCIMIENTOS DE PARTIDAS (INTERACTIVO) ---
        st.markdown("#### 2. Vencimientos de Partidas (Ventana de 30 días)")
        if col_vencimiento:
            df_fechas = df_proceso.copy()
            df_fechas['Fecha_Real'] = pd.to_datetime(df_fechas[col_vencimiento], format='%d-%b-%y', errors='coerce')
            df_fechas = df_fechas.dropna(subset=['Fecha_Real'])
            
            hoy = pd.to_datetime(datetime.datetime.now().date())
            ventana_inicio = hoy - pd.Timedelta(days=15)
            ventana_fin = hoy + pd.Timedelta(days=15)
            
            df_fechas = df_fechas[(df_fechas['Fecha_Real'] >= ventana_inicio) & (df_fechas['Fecha_Real'] <= ventana_fin)]
            
            if not df_fechas.empty:
                df_fechas['Fecha_Str'] = df_fechas['Fecha_Real'].dt.strftime('%Y-%m-%d')
                df_linea = df_fechas.groupby(['Fecha_Real', 'Fecha_Str', col_estatus]).size().reset_index(name='Cantidad de Partidas')
                
                fig_line = px.bar(
                    df_linea, 
                    x='Fecha_Real', 
                    y='Cantidad de Partidas', 
                    color=col_estatus,
                    barmode='stack',
                    labels={'Fecha_Real': 'Fecha de Vencimiento'}
                )
                fig_line.update_layout(
                    xaxis=dict(tickformat="%d-%b"), 
                    clickmode='event+select',
                    margin=dict(t=10, b=10, l=0, r=0), 
                    paper_bgcolor="rgba(0,0,0,0)", 
                    plot_bgcolor="rgba(0,0,0,0)"
                )
                
                col_graf_venc, col_tabla_venc = st.columns([1.5, 1])
                with col_graf_venc:
                    event = st.plotly_chart(fig_line, use_container_width=True, on_select="rerun")
                
                with col_tabla_venc:
                    st.markdown("📄 **Detalle de Vencimientos**")
                    if event and "selection" in event and event["selection"].get("points"):
                        puntos = event["selection"]["points"]
                        fechas_seleccionadas = [str(p["x"])[:10] for p in puntos] 
                        
                        df_filtro_grafico = df_fechas[df_fechas['Fecha_Str'].isin(fechas_seleccionadas)].copy()
                        
                        if not df_filtro_grafico.empty:
                            # Limpiamos la serie del vehículo cortando en el guion
                            if 'Vehiculo_Info' in df_filtro_grafico.columns:
                                df_filtro_grafico['Vehiculo_Info'] = df_filtro_grafico['Vehiculo_Info'].apply(lambda x: str(x).split(' - ')[0].strip())
                            
                            # Agregamos tanto el vehículo limpio como la descripción de la pieza
                            cols_mostrar_venc = [c for c in ['Siniestro', col_taller, 'Vehiculo_Info', col_desc, col_estatus] if c in df_filtro_grafico.columns]
                            st.dataframe(df_filtro_grafico[cols_mostrar_venc], hide_index=True, use_container_width=True)
                    else: 
                        st.info("👆 Haz clic en una barra del gráfico para filtrar la tabla.")
            else:
                st.info("No hay vencimientos programados en la ventana de -15 a +15 días.")
                
        st.markdown("<hr style='border: 1px solid #333; margin: 30px 0;'>", unsafe_allow_html=True)
        
        # --- 3. PEDIDOS POR CDR EN CURSO ---
        st.markdown("#### 3. Pedidos Activos por CDR (Taller)")
        if col_taller:
            df_talleres = df_proceso[col_taller].value_counts().reset_index()
            df_talleres.columns = ['Taller', 'Cantidad']
            fig_bar = px.bar(df_talleres, x='Cantidad', y='Taller', orientation='h')
            fig_bar.update_layout(yaxis={'categoryorder':'total ascending'}, margin=dict(t=10, b=0, l=0, r=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.warning("No hay datos activos en la base principal para graficar.")


# === [BLOQUE 5: VISTA 2 - PANEL OPERATIVO] ===
if vista_actual == "⚙️ Panel Operativo":
    st.markdown("### 📈 Indicadores Diarios")
    hoy_str = datetime.datetime.now().strftime('%d-%b-%y')
    hoy_dt = pd.to_datetime(datetime.datetime.now().date())
    
    if col_vencimiento:
        fechas_venc_dt = pd.to_datetime(df_proceso[col_vencimiento], format='%d-%b-%y', errors='coerce')
        # REGLA APLICADA: Excluir "CONFIRMAR" del KPI de vencidos
        vencidas_pasadas_kpi = len(df_proceso[(fechas_venc_dt < hoy_dt) & (df_proceso[col_vencimiento] != '') & (~df_proceso[col_estatus].astype(str).str.upper().str.contains("CONFIRMAR"))])
    else:
        vencidas_pasadas_kpi = 0
        
    vencen_hoy = len(df_proceso[df_proceso[col_vencimiento] == hoy_str]) if col_vencimiento else 0
    recolecciones = len(df_recoleccion_total)
    
    if col_estatus:
        por_confirmar_kpi = len(df_proceso[df_proceso[col_estatus].astype(str).str.upper().str.contains("CONFIRMAR")])
        en_proceso = len(df_proceso[~df_proceso[col_estatus].astype(str).str.upper().str.contains("CONFIRMAR")])
        # Restaurado: Cálculo de piezas listas para facturar
        partidas_por_facturar = len(df_trabajo[df_trabajo[col_estatus].astype(str).str.strip().str.upper() == "RECIBIDO"])
    else:
        por_confirmar_kpi = 0
        en_proceso = len(df_proceso)
        partidas_por_facturar = 0
    
    kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)
    kpi1.metric("📦 En Proceso (CDR)", en_proceso)
    kpi2.metric("⏳ Por Confirmar", por_confirmar_kpi)
    kpi3.metric("⚠️ Vencen Hoy", vencen_hoy)
    kpi4.metric("❌ Vencidos (Atrasados)", vencidas_pasadas_kpi)
    kpi5.metric("↩️ En Recolección", recolecciones)
    kpi6.metric("🧾 Por Facturar", partidas_por_facturar)

    st.markdown("---")

    st.markdown("### 🎛️ Filtros de Búsqueda")
    filtro_col1, filtro_col2, filtro_col3, filtro_col4 = st.columns(4)
    
    with filtro_col1:
        lista_talleres = sorted([str(t) for t in df_proceso[col_taller].dropna().unique() if str(t).strip() != '']) if col_taller else []
        taller_sel = st.multiselect("🏢 Taller:", lista_talleres, placeholder="Todos...")
        
    with filtro_col2:
        lista_estatus = sorted([str(e) for e in df_proceso[col_estatus].dropna().unique() if str(e).strip() != '']) if col_estatus else []
        estatus_sel = st.multiselect("📊 Estatus:", lista_estatus, placeholder="Todos...")

    with filtro_col3:
        df_temp = df_proceso.copy()
        if taller_sel: df_temp = df_temp[df_temp[col_taller].astype(str).isin(taller_sel)]
        if estatus_sel: df_temp = df_temp[df_temp[col_estatus].astype(str).isin(estatus_sel)]
        lista_siniestros = sorted(list(df_temp['Filtro_Siniestro'].dropna().unique())) if 'Filtro_Siniestro' in df_temp.columns else []
        siniestro_sel = st.multiselect(f"🚗 Siniestro - Vehículo:", lista_siniestros, placeholder="Todos...")

    with filtro_col4:
        df_temp_desc = df_proceso.copy()
        if taller_sel: df_temp_desc = df_temp_desc[df_temp_desc[col_taller].astype(str).isin(taller_sel)]
        if estatus_sel: df_temp_desc = df_temp_desc[df_temp_desc[col_estatus].astype(str).isin(estatus_sel)]
        if siniestro_sel: df_temp_desc = df_temp_desc[df_temp_desc['Filtro_Siniestro'].isin(siniestro_sel)]
        lista_desc_filtro = sorted(list(df_temp_desc[col_desc].dropna().astype(str).unique())) if col_desc in df_temp_desc.columns else []
        desc_sel = st.multiselect(f"⚙️ Refacción:", lista_desc_filtro, placeholder="Todas...")

    df_filtrado = df_proceso.copy()
    if taller_sel: df_filtrado = df_filtrado[df_filtrado[col_taller].astype(str).isin(taller_sel)]
    if estatus_sel: df_filtrado = df_filtrado[df_filtrado[col_estatus].astype(str).isin(estatus_sel)]
    if siniestro_sel: df_filtrado = df_filtrado[df_filtrado['Filtro_Siniestro'].isin(siniestro_sel)]
    if desc_sel: df_filtrado = df_filtrado[df_filtrado[col_desc].astype(str).isin(desc_sel)]

    df_recoleccion = df_recoleccion_total.copy()
    if taller_sel: df_recoleccion = df_recoleccion[df_recoleccion[col_taller].astype(str).isin(taller_sel)]
    if siniestro_sel:
        ids_sel = [s.split(" - ")[0] for s in siniestro_sel]
        df_recoleccion = df_recoleccion[df_recoleccion['Siniestro'].isin(ids_sel)]
    if desc_sel: df_recoleccion = df_recoleccion[df_recoleccion[col_desc].astype(str).isin(desc_sel)]

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
    if col_guia: base_config[col_guia] = st.column_config.TextColumn("Guía", width="small", help="Captura el número de rastreo")
    if col_remision: base_config[col_remision] = st.column_config.TextColumn("Folio Remisión", width="small")
    if col_comentarios: base_config[col_comentarios] = st.column_config.TextColumn("Obs.") 

    if col_estatus:
        df_por_confirmar = df_filtrado[df_filtrado[col_estatus].astype(str).str.upper().str.contains("CONFIRMAR")].copy()
    else:
        df_por_confirmar = pd.DataFrame()

    num_pedidos_conf = df_por_confirmar['Siniestro'].nunique() if not df_por_confirmar.empty else 0

    with st.expander(f"⏳ Piezas por Confirmar (Pendientes de CDR) | {num_pedidos_conf} Siniestros", expanded=False):
        if not df_por_confirmar.empty:
            st.info(f"Tienes {num_pedidos_conf} pedidos con partidas bloqueadas esperando confirmación.")
            if not modo_consulta:
                df_por_confirmar['Confirmar Surtido'] = False
                df_por_confirmar['Cancelar'] = False
                
            cols_conf = [c for c in [col_taller, 'Siniestro', 'Vehiculo_Info', col_cant, col_desc, col_asignacion, col_vencimiento, col_estatus, col_comentarios, 'Confirmar Surtido', 'Cancelar'] if c in df_por_confirmar.columns]
            df_mostrar_conf = df_por_confirmar[cols_conf]
            
            config_conf = base_config.copy()
            if not modo_consulta:
                config_conf.update({
                    "Confirmar Surtido": st.column_config.CheckboxColumn("✅ Confirmar", width="small", default=False),
                    "Cancelar": st.column_config.CheckboxColumn("🚫 Can", width="small", default=False)
                })
                
            bloqueadas_conf = [c for c in df_mostrar_conf.columns if c not in ['Confirmar Surtido', 'Cancelar', col_comentarios]]
            
            df_editado_conf_parcial = st.data_editor(df_mostrar_conf, column_config=config_conf, disabled=bloqueadas_conf, hide_index=True, use_container_width=True, key="editor_por_confirmar")
            df_editado_conf = df_editado_conf_parcial.copy()
            for col in [col_id, col_marca, col_modelo, col_desc]:
                if col in df_por_confirmar.columns: df_editado_conf[col] = df_por_confirmar[col].values
        else:
            st.success("✅ No hay piezas pendientes de confirmación.")

    df_vencimientos = df_filtrado[(df_filtrado[col_vencimiento] == hoy_str) & (~df_filtrado[col_estatus].astype(str).str.upper().str.contains("CONFIRMAR"))].copy() if col_vencimiento else pd.DataFrame()
    num_pedidos_venc = df_vencimientos['Siniestro'].nunique() if not df_vencimientos.empty else 0
    
    with st.expander(f"🚨 Vencimientos (Día en Curso) | {num_pedidos_venc} Siniestros", expanded=False):
        if not df_vencimientos.empty:
            st.error(f"⚠️ Atención: Tienes {num_pedidos_venc} pedidos con partidas que vencen hoy.")
            
            df_vencimientos['Cancelar'] = False
            df_vencimientos['Reasignar'] = False
            df_vencimientos['Nueva Fecha'] = None
                
            columnas_vista_venc = [c for c in [col_taller, 'Siniestro', 'Vehiculo_Info', col_cant, col_desc, col_precio, col_estatus, col_vencimiento, col_guia, col_comentarios, 'Cancelar', 'Reasignar', 'Nueva Fecha'] if c in df_vencimientos.columns]
            df_mostrar_venc = df_vencimientos[columnas_vista_venc]
            columnas_bloqueadas_venc = [c for c in df_mostrar_venc.columns if c not in ['Cancelar', 'Reasignar', 'Nueva Fecha', col_comentarios, col_guia]]
            
            config_venc = base_config.copy()
            config_venc.update({
                "Cancelar": st.column_config.CheckboxColumn("🚫 Can", width="small", default=False),
                "Reasignar": st.column_config.CheckboxColumn("🔄 Reasig", width="small", default=False),
                "Nueva Fecha": st.column_config.DateColumn("📅 Nueva Fecha", width="small", format="DD/MM/YYYY")
            })

            df_editado_venc_parcial = st.data_editor(df_mostrar_venc, column_config=config_venc, disabled=columnas_bloqueadas_venc, hide_index=True, use_container_width=True, key="editor_vencimientos")
            df_editado_venc = df_editado_venc_parcial.copy()
            for col in [col_id, col_marca, col_modelo]:
                if col in df_vencimientos.columns: df_editado_venc[col] = df_vencimientos[col].values
        else:
            st.success("✅ No hay partidas con vencimiento para el día de hoy.")

    if col_vencimiento and not df_filtrado.empty:
        fechas_venc_filtro = pd.to_datetime(df_filtrado[col_vencimiento], format='%d-%b-%y', errors='coerce')
        df_atrasadas = df_filtrado[(fechas_venc_filtro < hoy_dt) & (df_filtrado[col_vencimiento] != '') & (~df_filtrado[col_estatus].astype(str).str.upper().str.contains("CONFIRMAR"))].copy()
    else:
        df_atrasadas = pd.DataFrame()

    num_pedidos_atr = df_atrasadas['Siniestro'].nunique() if not df_atrasadas.empty else 0

    with st.expander(f"❌ Vencimientos Atrasados (Pendientes) | {num_pedidos_atr} Siniestros", expanded=False):
        if not df_atrasadas.empty:
            st.error(f"❌ Atención: Tienes {num_pedidos_atr} pedidos vencidos en días anteriores que siguen abiertos.")
            
            df_atrasadas['Cancelar'] = False
            df_atrasadas['Reasignar'] = False
            df_atrasadas['Nueva Fecha'] = None
                
            columnas_vista_atr = [c for c in [col_taller, 'Siniestro', 'Vehiculo_Info', col_cant, col_desc, col_precio, col_estatus, col_vencimiento, col_comentarios, 'Cancelar', 'Reasignar', 'Nueva Fecha'] if c in df_atrasadas.columns]
            df_mostrar_atr = df_atrasadas[columnas_vista_atr]
            columnas_bloqueadas_atr = [c for c in df_mostrar_atr.columns if c not in ['Cancelar', 'Reasignar', 'Nueva Fecha', col_comentarios]]
            
            config_atr = base_config.copy()
            config_atr.update({
                "Cancelar": st.column_config.CheckboxColumn("🚫 Can", width="small", default=False),
                "Reasignar": st.column_config.CheckboxColumn("🔄 Reasig", width="small", default=False),
                "Nueva Fecha": st.column_config.DateColumn("📅 Nueva Fecha", width="small", format="DD/MM/YYYY")
            })

            df_editado_atr_parcial = st.data_editor(df_mostrar_atr, column_config=config_atr, disabled=columnas_bloqueadas_atr, hide_index=True, use_container_width=True, key="editor_vencimientos_atrasados")
            df_editado_atrasadas = df_editado_atr_parcial.copy()
            for col in [col_id, col_marca, col_modelo]:
                if col in df_atrasadas.columns: df_editado_atrasadas[col] = df_atrasadas[col].values
        else:
            st.success("✅ No hay partidas atrasadas pendientes.")

    if col_estatus:
        df_por_cobrar = df_filtrado[df_filtrado[col_estatus].astype(str).str.upper() == "ENTREGADO"].copy()
    else:
        df_por_cobrar = pd.DataFrame()
        
    num_pedidos_cobrar = df_por_cobrar['Siniestro'].nunique() if not df_por_cobrar.empty else 0

    with st.expander(f"💰 Por Cobrar (Entregados pendientes de Recibo) | {num_pedidos_cobrar} Siniestros", expanded=False):
        if not df_por_cobrar.empty:
            st.success(f"💵 Tienes {num_pedidos_cobrar} pedidos listos para mandar a cobro.")
            df_por_cobrar['Marcar Recibido'] = False
            
            cols_cobro = [c for c in [col_taller, 'Siniestro', 'Vehiculo_Info', col_cant, col_desc, col_precio, col_estatus, col_comentarios, 'Marcar Recibido'] if c in df_por_cobrar.columns]
            df_mostrar_cobro = df_por_cobrar[cols_cobro]
            
            config_cobro = base_config.copy()
            config_cobro.update({"Marcar Recibido": st.column_config.CheckboxColumn("🏁 Marcar Recibido", width="small", default=False)})
            bloqueadas_cobro = [c for c in df_mostrar_cobro.columns if c not in ['Marcar Recibido', col_comentarios]]
            
            df_editado_cobro_parcial = st.data_editor(df_mostrar_cobro, column_config=config_cobro, disabled=bloqueadas_cobro, hide_index=True, use_container_width=True, key="editor_por_cobrar")
            df_editado_cobro = df_editado_cobro_parcial.copy()
            for col in [col_id, col_desc]: 
                if col in df_por_cobrar.columns: df_editado_cobro[col] = df_por_cobrar[col].values
        else:
            st.info("✅ No hay pedidos entregados pendientes de cobrar.")

    df_asignados = df_filtrado[~df_filtrado[col_estatus].astype(str).str.upper().str.contains("CONFIRMAR")].copy() if col_estatus else df_filtrado.copy()
    num_pedidos_asig = df_asignados['Siniestro'].nunique() if not df_asignados.empty else 0
    
    with st.expander(f"📋 Pedidos Asignados (General) | {num_pedidos_asig} Siniestros", expanded=False):
        dfs_editados = []
        if not df_asignados.empty:
            if col_estatus:
                estatus_upper = df_asignados[col_estatus].astype(str).str.upper()
                df_asignados['Pedido'] = estatus_upper.str.contains("EN PROCESAMIENTO")
                df_asignados['Entregado'] = estatus_upper.str.contains("ENTREGADO")
                df_asignados['Recibido'] = estatus_upper.str.contains("RECIBIDO")
                df_asignados['Reasignacion'] = estatus_upper.str.contains("REASIGNAR")
                df_asignados['Cancelar'] = estatus_upper.str.contains("CANCELADO")
            else:
                df_asignados['Pedido'] = False
                df_asignados['Entregado'] = False
                df_asignados['Recibido'] = False
                df_asignados['Reasignacion'] = False
                df_asignados['Cancelar'] = False
            
            df_asignados['Remision'] = df_asignados[col_remision].astype(str).str.strip() != '' if col_remision else False
            df_asignados['Proveedor'] = "" 
                
            for taller, df_taller in df_asignados.groupby(col_taller):
                num_pedidos = df_taller['Siniestro'].nunique()
                with st.expander(f"🏢 {taller} | {num_pedidos} Siniestro(s)", expanded=False):
                    for siniestro_auto, df_grupo in df_taller.groupby('Siniestro'):
                        vehiculo_str = df_grupo['Vehiculo_Info'].iloc[0] if not df_grupo.empty else ""
                        st.markdown(f"**🚗 {siniestro_auto} | {vehiculo_str}**")
                        
                        columnas_checkbox = ['Pedido', 'Proveedor', 'Remision', 'Entregado', 'Recibido', 'Reasignacion', 'Cancelar']
                        orden_deseado = [col_asignacion, col_fecha_confi, col_cant, col_desc, col_precio, col_estatus, col_vencimiento, col_guia, col_remision, col_comentarios]
                        orden_deseado = [c for c in orden_deseado if c and c in df_grupo.columns] + columnas_checkbox
                        
                        df_mostrar = df_grupo[orden_deseado]
                        columnas_bloqueadas = [c for c in df_mostrar.columns if c not in columnas_checkbox and c not in [col_comentarios, col_guia]]
                        
                        config_pedidos = base_config.copy()
                        config_pedidos.update({
                            "Pedido": st.column_config.CheckboxColumn("🛒 Ped", width="small", default=False),
                            "Proveedor": st.column_config.TextColumn("🏢 Proveedor", width="medium"),
                            "Remision": st.column_config.CheckboxColumn("📝 Rem", width="small", default=False),
                            "Entregado": st.column_config.CheckboxColumn("🚚 Ent", width="small", default=False),
                            "Recibido": st.column_config.CheckboxColumn("🏁 Rec", width="small", default=False),
                            "Reasignacion": st.column_config.CheckboxColumn("🔄 Reasig", width="small", default=False),
                            "Cancelar": st.column_config.CheckboxColumn("🚫 Can", width="small", default=False)
                        })

                        df_editado_parcial = st.data_editor(df_mostrar, column_config=config_pedidos, disabled=columnas_bloqueadas, hide_index=True, use_container_width=True, key=f"editor_{taller}_{siniestro_auto}")
                        for col in [col_id, col_taller, col_marca, col_modelo, col_desc, 'Siniestro', 'Vehiculo_Info']:
                            if col in df_grupo.columns: df_editado_parcial[col] = df_grupo[col].values
                        dfs_editados.append(df_editado_parcial)

        if dfs_editados: df_editado = pd.concat(dfs_editados, ignore_index=True)

    num_pedidos_rec = df_recoleccion['Siniestro'].nunique() if not df_recoleccion.empty and 'Siniestro' in df_recoleccion.columns else 0
    with st.expander(f"↩️ Piezas para Recolección | {num_pedidos_rec} Siniestros", expanded=False):
        if not df_recoleccion.empty:
            st.warning(f"🚚 Tienes {num_pedidos_rec} pedidos para recoger en los CDR.")
            columnas_vista_rec = [c for c in [col_taller, 'Siniestro', 'Vehiculo_Info', col_desc, col_cant, col_precio, col_estatus, col_vencimiento, col_comentarios] if c in df_recoleccion.columns]
            st.dataframe(df_recoleccion[columnas_vista_rec], column_config=base_config, hide_index=True, use_container_width=True)
        else:
            st.info("No hay piezas pendientes de recolección en este momento.")


# === [BLOQUE 6: VISTA 3 - PEDIDOS Y PROVEEDORES] ===
if vista_actual == "🛒 Pedidos y Proveedores":
    st.markdown("### 🛒 Panel de Compras (Por Llegar)")
    
    if not df_compras.empty:
        df_compras['Recibido_Bool'] = df_compras['Recibido'].astype(str).str.strip().str.upper().isin(['TRUE', 'SI', '1', 'YES', 'V', 'X'])
        df_compras_disp = df_compras[df_compras['Recibido_Bool'] == False].copy()
        
        if not df_compras_disp.empty:
            df_compras_disp = df_compras_disp.drop(columns=['Recibido_Bool'])
            
            df_compras_disp['Fecha_Compra_Dt'] = pd.to_datetime(df_compras_disp['Fecha Compra'], format='%d-%b-%y', errors='coerce')
            df_compras_disp['ETA_Dias'] = pd.to_numeric(df_compras_disp['Tiempo Entrega (Días)'], errors='coerce').fillna(0)
            df_compras_disp['Llegada_Calculada'] = df_compras_disp['Fecha_Compra_Dt'] + pd.to_timedelta(df_compras_disp['ETA_Dias'], unit='d')
            df_compras_disp['Fecha Llegada'] = df_compras_disp['Llegada_Calculada'].dt.strftime('%d-%b-%y').fillna('-')
            
            df_compras_disp = df_compras_disp.sort_values(by='Llegada_Calculada', ascending=True)

            df_compras_disp['Filtro_Busqueda'] = df_compras_disp['Siniestro'].astype(str) + " | " + df_compras_disp['Descripción Pieza'].astype(str)
            lista_pedidos = sorted(list(df_compras_disp['Filtro_Busqueda'].unique()))
            
            busqueda_pedido = st.multiselect(
                "🔍 Buscar Pedido (Escribe Siniestro o Pieza para filtrar al instante):", 
                options=lista_pedidos,
                placeholder="Selecciona uno o varios pedidos..."
            )
            
            if busqueda_pedido:
                df_compras_disp = df_compras_disp[df_compras_disp['Filtro_Busqueda'].isin(busqueda_pedido)].copy()

            for col_c in df_compras_disp.columns:
                if col_c not in ['Recibido', 'Filtro_Busqueda', 'Fecha_Compra_Dt', 'ETA_Dias', 'Llegada_Calculada']:
                    df_compras_disp[col_c] = df_compras_disp[col_c].fillna("").astype(str).replace(['nan', 'None'], '')
            
            df_compras_disp['Imprimir Remisión'] = False
            df_compras_disp['Recibido'] = False 
            
            config_compras = {
                'Costo Compra': st.column_config.NumberColumn("Costo Compra", format="$ %.2f"),
                'Tiempo Entrega (Días)': st.column_config.NumberColumn("Tiempo Entrega", step=1),
                'Fecha Compra': st.column_config.TextColumn("Fecha Compra", disabled=True),
                'Fecha Llegada': st.column_config.TextColumn("Llegada Estimada", disabled=True),
                'Recibido': st.column_config.CheckboxColumn("✅ Marcar Recibido", default=False),
                'Imprimir Remisión': st.column_config.CheckboxColumn("🖨️ Imprimir al Recibir", default=False),
                'Filtro_Busqueda': None, 
                'Fecha_Compra_Dt': None,
                'ETA_Dias': None,
                'Llegada_Calculada': None
            }
            
            bloqueadas_compras = [c for c in df_compras_disp.columns if c not in ['Costo Compra', 'Tiempo Entrega (Días)', 'Proveedor', 'Recibido', 'Imprimir Remisión']]
            
            cols_ordenadas = ['Siniestro', 'Taller', 'Vehículo', 'Descripción Pieza', 'Proveedor', 'Costo Compra', 'Fecha Compra', 'Tiempo Entrega (Días)', 'Fecha Llegada', 'Recibido', 'Imprimir Remisión', 'Filtro_Busqueda', 'Fecha_Compra_Dt', 'ETA_Dias', 'Llegada_Calculada']
            df_compras_disp = df_compras_disp[[c for c in cols_ordenadas if c in df_compras_disp.columns]]

            df_editado_compras_parcial = st.data_editor(df_compras_disp, column_config=config_compras, disabled=bloqueadas_compras, hide_index=True, use_container_width=True, key="editor_compras")
            
            df_editado_compras = df_editado_compras_parcial.copy()
            df_editado_compras.index = df_compras_disp.index 
            for col in ['Siniestro', 'Descripción Pieza']:
                if col in df_compras.columns: 
                    df_editado_compras[col] = df_compras_disp[col].values
        else:
            st.success("✅ Todos los pedidos de compras han sido recibidos.")
    else:
        st.warning("No hay órdenes de compra registradas actualmente.")

    st.markdown("<hr style='border: 1px solid #444; margin: 30px 0;'>", unsafe_allow_html=True)
    st.markdown("### 🏢 Directorio de Proveedores")
    
    try:
        df_proveedores = cargar_datos.__wrapped__() if False else obtener_dataframe("BD_PROVEEDORES")
    except Exception:
        df_proveedores = pd.DataFrame()

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
            
            submit_prov = st.form_submit_button("💾 Guardar Proveedor")
            
            if submit_prov:
                if p_prov.strip() == "":
                    st.error("❌ El nombre del Proveedor es obligatorio.")
                else:
                    try:
                        doc = init_connection()
                        ws_p = doc.worksheet("BD_PROVEEDORES")
                        ws_p.append_row([p_prov.upper(), p_suc.upper(), p_dir.upper(), p_tiempo.upper(), p_contacto.upper(), p_tel, p_correo])
                        
                        st.success(f"✅ Proveedor '{p_prov}' guardado exitosamente en la nube.")
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error al guardar en la nube: {e}")
                        
    if not df_proveedores.empty:
        st.dataframe(df_proveedores.fillna(""), use_container_width=True, hide_index=True)
    else:
        st.warning("No hay proveedores registrados aún.")


# === [BLOQUE 7: VISTAS 4 Y 5 - TALLERES E INVENTARIO] ===
if vista_actual == "🏢 Talleres":
    st.markdown("### 🏢 Base de Datos de Talleres")
    
    with st.expander("➕ Registrar Nuevo Taller", expanded=False):
        st.info("Registra un nuevo taller. El Asesor se asignará automáticamente si la ciudad está en el directorio GNP.")
        
        mapa_asesores = {
            "Monterrey": "Oscar Landeros Martinez", "Reynosa": "Oscar Landeros Martinez", "Saltillo": "Oscar Landeros Martinez", 
            "Torreón": "Oscar Landeros Martinez", "Tampico": "Oscar Landeros Martinez", "Cd. Juárez": "Oscar Landeros Martinez", 
            "Chihuahua": "Oscar Landeros Martinez", "Mexicali": "Oscar Landeros Martinez", "Tijuana": "Oscar Landeros Martinez", 
            "Cd. Obregón": "Oscar Landeros Martinez", "Culiacán": "Oscar Landeros Martinez", "Los Mochis": "Oscar Landeros Martinez", 
            "Hermosillo": "Oscar Landeros Martinez",
            "Querétaro": "Estefany Dayanna Ochoa Aranda", "Cuernavaca": "Estefany Dayanna Ochoa Aranda", "León": "Estefany Dayanna Ochoa Aranda", 
            "Aguascalientes": "Estefany Dayanna Ochoa Aranda", "Morelia": "Estefany Dayanna Ochoa Aranda", "Colima": "Estefany Dayanna Ochoa Aranda", 
            "Guadalajara": "Estefany Dayanna Ochoa Aranda",
            "Estado de México": "Diana Laura Avalos Garcia", "Toluca": "Diana Laura Avalos Garcia", "Pachuca": "Diana Laura Avalos Garcia",
            "Puebla": "Luis Antonio Ramirez De Arellano Alvarez", "San Luis Potosí": "Luis Antonio Ramirez De Arellano Alvarez", 
            "Villahermosa": "Luis Antonio Ramirez De Arellano Alvarez", "Mérida": "Luis Antonio Ramirez De Arellano Alvarez", 
            "Acapulco": "Luis Antonio Ramirez De Arellano Alvarez", "Oaxaca": "Luis Antonio Ramirez De Arellano Alvarez", 
            "Veracruz": "Luis Antonio Ramirez De Arellano Alvarez", "Xalapa": "Luis Antonio Ramirez De Arellano Alvarez", 
            "Cancún": "Luis Antonio Ramirez De Arellano Alvarez", "Coatzacoalcos": "Luis Antonio Ramirez De Arellano Alvarez",
            "CDMX": "Yessica Vianney Martinez Olivar"
        }

        lista_estados = ["Aguascalientes", "Baja California", "Baja California Sur", "Campeche", "Chiapas", "Chihuahua", "CDMX", "Coahuila", "Colima", "Durango", "Estado de México", "Guanajuato", "Guerrero", "Hidalgo", "Jalisco", "Michoacán", "Morelos", "Nayarit", "Nuevo León", "Oaxaca", "Puebla", "Querétaro", "Quintana Roo", "San Luis Potosí", "Sinaloa", "Sonora", "Tabasco", "Tamaulipas", "Tlaxcala", "Veracruz", "Yucatán", "Zacatecas"]

        c1, c2, c3 = st.columns([2, 2, 1])
        nuevo_taller = c1.text_input("Taller * (Obligatorio)")
        
        ciudad_sel = c2.selectbox("Ciudad", [""] + sorted(list(mapa_asesores.keys())) + ["Otra (Escribir manualmente)..."])
        if ciudad_sel == "Otra (Escribir manualmente)...":
            nueva_ciudad = c2.text_input("Ingresa la Ciudad")
            asesor_asignado = c3.text_input("Asesor Asignado (Manual)")
        elif ciudad_sel != "":
            nueva_ciudad = ciudad_sel
            asesor_asignado = mapa_asesores[ciudad_sel]
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
        
        submit_taller = st.button("💾 Guardar en Catálogo", type="primary")
        
        if submit_taller:
            if nuevo_taller.strip() == "":
                st.error("❌ El 'Nombre del Taller' es obligatorio.")
            else:
                try:
                    doc = init_connection()
                    ws_c = doc.worksheet("Catálogo")
                    
                    nueva_fila = [nuevo_taller.upper(), nueva_dir.upper(), ciudad_sel.upper(), nuevo_estado.upper(), nuevo_contacto.upper(), nuevo_tel, nuevo_wa, nuevo_correo, asesor_asignado.upper(), nuevo_seguro.upper()]
                    
                    ws_c.append_row(nueva_fila, value_input_option='USER_ENTERED')
                    
                    st.success(f"✅ Taller '{nuevo_taller}' agregado exitosamente en la nube.")
                    st.cache_data.clear()
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error al guardar en la nube: {e}")

    st.markdown("<hr style='border: 1px solid #444; margin-top: 10px; margin-bottom: 10px;'>", unsafe_allow_html=True)
    st.info("O edita el catálogo existente. (Puedes borrar un taller seleccionando la fila y presionando 'Suprimir').")
    
    if not df_catalogo.empty:
        col_taller_cat = next((c for c in df_catalogo.columns if "TALLER" in str(c).upper()), None)
        if col_taller_cat:
            lista_nombres_talleres = sorted(list(df_catalogo[col_taller_cat].dropna().astype(str).unique()))
            
            busqueda_taller = st.multiselect(
                "🔍 Buscar Taller para editar (Escribe para filtrar al instante):", 
                options=lista_nombres_talleres,
                placeholder="Selecciona uno o varios talleres..."
            )
            
            if busqueda_taller:
                df_cat_disp = df_catalogo[df_catalogo[col_taller_cat].astype(str).isin(busqueda_taller)].copy()
            else:
                df_cat_disp = df_catalogo.copy()
        else:
            df_cat_disp = df_catalogo.copy()
        
        cols_limpias = [c for c in df_cat_disp.columns if "Unnamed" not in str(c)]
        df_cat_disp = df_cat_disp[cols_limpias]
        
        for c in df_cat_disp.columns:
            df_cat_disp[c] = df_cat_disp[c].fillna("").astype(str).replace(['nan', 'None', '0', '0.0'], '')
        
        df_editado_catalogo = st.data_editor(
            df_cat_disp,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            key="editor_catalogo"
        )
    else:
        st.warning("No se encontró información en la hoja 'Catálogo'.")

if vista_actual == "📦 Inventario":
    st.markdown("### 📦 Control de Inventario Físico")
    
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
            
            submit_inv = st.form_submit_button("💾 Guardar en Inventario")
            
            if submit_inv:
                if desc_n.strip() == "":
                    st.error("❌ La 'Descripción de la Pieza' es obligatoria.")
                else:
                    try:
                        doc = init_connection()
                        ws_i = doc.worksheet("BD_INVENTARIO")
                        
                        datos_nueva_pieza = [ubicacion_n, oem_n, alt_n, desc_n, marca_n, mod_n, ver_n, ano_n, pos_n, cant_n, est_n, costo_n, precio_n, sin_n, ml_n, "NO"]
                        datos_mayusculas = [str(v).upper() if isinstance(v, str) else v for v in datos_nueva_pieza]
                        
                        ws_i.append_row(datos_mayusculas, value_input_option='USER_ENTERED')
                        
                        st.success("✅ Pieza agregada exitosamente en la nube.")
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error al guardar en la nube: {e}")

    st.markdown("<hr style='border: 1px solid #444; margin-top: 10px; margin-bottom: 10px;'>", unsafe_allow_html=True)
    st.info("Administra las piezas disponibles. Si marcas 'Sin Existencia' y guardas, la pieza dejará de mostrarse en esta vista. Selecciona una fila y pulsa Suprimir para eliminarla.")
    
    if not df_inventario.empty:
        col_skuint = next((c for c in df_inventario.columns if "SKU INT" in str(c).upper()), None)
        if col_skuint:
            df_inv_filtrado = df_inventario[df_inventario[col_skuint].astype(str).str.strip().str.upper() != 'PRE-001'].copy()
        else:
            df_inv_filtrado = df_inventario.copy()
        
        def crear_etiqueta_inv(row):
            oem = str(row.get('Número de Parte (OEM)', '')).strip()
            if oem.lower() in ['nan', 'none']: oem = ''
            marca = str(row.get('Marca', '')).strip()
            if marca.lower() in ['nan', 'none']: marca = ''
            modelo = str(row.get('Modelo', '')).strip()
            if modelo.lower() in ['nan', 'none']: modelo = ''
            desc = str(row.get('Descripción de la Pieza', '')).strip()
            if desc.lower() in ['nan', 'none']: desc = ''
            elementos = [e.upper() for e in [oem, marca, modelo, desc] if e]
            return " | ".join(elementos)

        df_inv_filtrado['Filtro_Busqueda'] = df_inv_filtrado.apply(crear_etiqueta_inv, axis=1)
        
        lista_piezas_inv = sorted(list(df_inv_filtrado['Filtro_Busqueda'].dropna().unique()))
        
        busqueda_inv = st.multiselect(
            "🔍 Buscar Pieza (No. Parte, Marca, Modelo o Descripción):", 
            options=lista_piezas_inv,
            placeholder="Escribe para buscar o selecciona del listado..."
        )
        
        if busqueda_inv:
            df_inv_disp = df_inv_filtrado[(df_inv_filtrado['Filtro_Busqueda'].isin(busqueda_inv)) & (~df_inv_filtrado['Sin Existencia'])].copy()
        else:
            df_inv_disp = df_inv_filtrado[~df_inv_filtrado['Sin Existencia']].copy()
            
        if 'Filtro_Busqueda' in df_inv_disp.columns:
            df_inv_disp = df_inv_disp.drop(columns=['Filtro_Busqueda'])
        
        for c in df_inv_disp.columns:
            if c != 'Sin Existencia':
                df_inv_disp[c] = df_inv_disp[c].fillna("").astype(str).replace(['nan', 'None', '0.0'], '').str.upper()
        
        config_inv = {
            'Sin Existencia': st.column_config.CheckboxColumn("Sin Existencia", default=False)
        }
        
        df_editado_inventario = st.data_editor(
            df_inv_disp,
            num_rows="dynamic",
            column_config=config_inv,
            use_container_width=True,
            hide_index=True,
            key="editor_inventario"
        )
    else:
        st.warning("No se encontró información en la hoja 'BD_INVENTARIO'.")

# === [BLOQUE 8: NUEVAS VISTAS (FACTURACIÓN Y PAQUETERÍA)] ===
if vista_actual == "🧾 Facturación":
    st.markdown("### 🧾 Pedidos Listos para Facturar")
    
    if col_estatus:
        df_fact = df_trabajo[df_trabajo[col_estatus].astype(str).str.strip().str.upper() == "RECIBIDO"].copy()
    else:
        df_fact = pd.DataFrame()
        
    def obtener_vehiculo_sin_serie(row):
        veh = f"{row.get(col_marca, '')} {row.get(col_modelo, '')}".strip()
        anio_val = ""
        if col_anio and pd.notnull(row.get(col_anio)):
            try:
                anio_val = str(int(row[col_anio]))
            except ValueError:
                anio_val = str(row[col_anio]).strip()
        if anio_val and anio_val.lower() not in ['nan', 'none', '']:
            veh += f" {anio_val}"
        return veh
        
    if not df_fact.empty:
        if col_id:
            df_fact['Siniestro'] = df_fact[col_id].apply(limpiar_siniestro)
        else:
            df_fact['Siniestro'] = ""
        
        df_fact['Vehiculo_Info'] = df_fact.apply(formatear_vehiculo, axis=1)

        st.info("Copia los datos para facturar. Marca '✅ Facturado' y luego 'Guardar' en el panel superior para sacar los pedidos de esta lista.")
        
        if not df_placas.empty and 'Siniestro' in df_placas.columns and 'Placa' in df_placas.columns:
            df_placas['Siniestro_Limpio'] = df_placas['Siniestro'].astype(str).str.strip().str.replace('.0', '', regex=False)
            dict_placas = dict(zip(df_placas['Siniestro_Limpio'], df_placas['Placa'].astype(str)))
        else:
            dict_placas = {}
        
        dfs_editados_fact = []
        
        for taller, df_taller_fact in df_fact.groupby(col_taller):
            num_pedidos_f = df_taller_fact['Siniestro'].nunique()
            
            with st.expander(f"🏢 {taller} | {num_pedidos_f} Siniestro(s) para Facturar", expanded=False):
                for siniestro_f, df_g in df_taller_fact.groupby('Siniestro'):
                    
                    placa_val = dict_placas.get(str(siniestro_f).strip(), "⚠️ PLACA PENDIENTE")
                    vehiculo_val_completo = df_g['Vehiculo_Info'].iloc[0] if not df_g.empty else ""
                    vehiculo_val_factura = obtener_vehiculo_sin_serie(df_g.iloc[0]) if not df_g.empty else ""
                    sufijo_multi = f" // {siniestro_f} // {placa_val} // {vehiculo_val_factura}"
                    
                    st.markdown(f"**🚗 {siniestro_f} | {vehiculo_val_completo}**")
                    
                    if aseguradora_sel == "Multiasistencias":
                        st.caption("Copia este sufijo y pégalo manualmente si necesitas separar las partidas en facturas distintas:")
                        st.code(sufijo_multi, language="text")
                    
                    df_mostrar_f = df_g.copy()
                    df_mostrar_f['Concepto Factura'] = ""
                    df_mostrar_f['Facturado'] = False
                    
                    for i, (idx, row) in enumerate(df_mostrar_f.iterrows()):
                        desc = str(row.get(col_desc, '')).strip()
                        if i == 0 and aseguradora_sel == "Multiasistencias":
                            concepto = f"{desc}{sufijo_multi}"
                        else:
                            concepto = desc
                        df_mostrar_f.at[idx, 'Concepto Factura'] = concepto
                    
                    cols_mostrar = ['Facturado', col_cant, 'Concepto Factura', col_precio, col_origen]
                    cols_mostrar = [c for c in cols_mostrar if c in df_mostrar_f.columns or c == 'Facturado']
                    bloqueadas_fact = [c for c in cols_mostrar if c != 'Facturado']
                    
                    config_fact = {
                        'Facturado': st.column_config.CheckboxColumn("✅ Facturado", width="small", default=False),
                        'Concepto Factura': st.column_config.TextColumn("Descripción para Factura", width="large"),
                        col_precio: st.column_config.NumberColumn("Precio", width="small", format="$ %.2f")
                    }
                    
                    df_editado_parcial_f = st.data_editor(
                        df_mostrar_f[cols_mostrar], 
                        column_config=config_fact, 
                        disabled=bloqueadas_fact, 
                        hide_index=True, 
                        use_container_width=True,
                        key=f"fact_{taller}_{siniestro_f}"
                    )
                    
                    for col_llave in [col_id, col_desc]:
                        if col_llave in df_g.columns:
                            df_editado_parcial_f[col_llave] = df_g[col_llave].values
                    
                    dfs_editados_fact.append(df_editado_parcial_f)
                    
        if dfs_editados_fact:
            df_editado_fact = pd.concat(dfs_editados_fact, ignore_index=True)
    else:
        st.success("✅ No hay pedidos pendientes de facturación.")

# === [BLOQUE 9: MOTOR GLOBAL DE GUARDADO EXCEL Y GENERACIÓN PDF (NUBE)] ===
import tempfile
import base64
import os
import datetime

if btn_guardar:
    def parsear_fecha_streamlit(val):
        if pd.isna(val): return None
        if isinstance(val, str):
            if len(val) >= 10 and val[4] == '-':
                return datetime.datetime.strptime(val[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
            try:
                return pd.to_datetime(val, dayfirst=True).strftime("%d/%m/%Y")
            except:
                return str(val)
        elif isinstance(val, datetime.date):
            return val.strftime("%d/%m/%Y")
        return str(val)
        
    def generar_llave(id_val, desc_val):
        id_str = str(id_val).strip().upper()
        if id_str.endswith('.0'): id_str = id_str[:-2]
        if id_str in ['NAN', 'NONE']: id_str = ''
        desc_str = str(desc_val).strip().upper()
        if desc_str in ['NAN', 'NONE']: desc_str = ''
        desc_str = ' '.join(desc_str.split())
        return (id_str, desc_str)
    
    originales = {}
    for _, row in df_trabajo_completo.iterrows():
        k = generar_llave(row.get(col_id, ''), row.get(col_desc, ''))
        originales[k] = {
            'comentario': str(row.get(col_comentarios, '')).strip(),
            'guia': str(row.get(col_guia, '')).strip(), 
            'estatus_db': str(row.get(col_estatus, '')).strip().upper(),
            'remision_bool': str(row.get(col_remision, '')).strip() != '' if col_remision else False
        }

    cambios_a_guardar = {}
    
    if not df_editado_conf.empty:
        for _, row in df_editado_conf.iterrows():
            k = generar_llave(row.get(col_id, ''), row.get(col_desc, ''))
            orig = originales.get(k, {'comentario': '', 'estatus_db': ''})
            nuevo_estatus = None
            nueva_fecha_conf = None
            if row.get('Cancelar'): nuevo_estatus = "CANCELADO"
            elif row.get('Confirmar Surtido'):
                nuevo_estatus = "EN PROCESAMIENTO"
                nueva_fecha_conf = datetime.datetime.now().strftime("%d/%m/%Y")
            cambio_estatus = (nuevo_estatus and nuevo_estatus != orig['estatus_db'])
            comentario_actual = str(row.get(col_comentarios, '')).strip()
            cambio_comentario = (comentario_actual != orig['comentario'])
            if cambio_estatus or cambio_comentario or nueva_fecha_conf:
                cambios_a_guardar[k] = {'estatus': nuevo_estatus if cambio_estatus else None, 'comentario': comentario_actual if cambio_comentario else None, 'nueva_fecha_conf': nueva_fecha_conf}
    
    df_venc_total = pd.concat([df_editado_venc, df_editado_atrasadas], ignore_index=True) if not df_editado_atrasadas.empty else df_editado_venc
    if not df_venc_total.empty:
        for _, row in df_venc_total.iterrows():
            k = generar_llave(row.get(col_id, ''), row.get(col_desc, ''))
            orig = originales.get(k, {'comentario': '', 'estatus_db': ''})
            nuevo_estatus = None
            nueva_fecha_venc = None
            if row.get('Cancelar'): nuevo_estatus = "CANCELADO"
            elif row.get('Reasignar'): 
                nuevo_estatus = "EN PROCESAMIENTO"
                val_fecha = row.get('Nueva Fecha')
                if pd.notna(val_fecha): nueva_fecha_venc = parsear_fecha_streamlit(val_fecha)
            cambio_estatus = (nuevo_estatus and nuevo_estatus != orig['estatus_db'])
            comentario_actual = str(row.get(col_comentarios, '')).strip()
            cambio_comentario = (comentario_actual != orig['comentario'])
            if cambio_estatus or cambio_comentario or nueva_fecha_venc:
                if k not in cambios_a_guardar: cambios_a_guardar[k] = {}
                if cambio_estatus: cambios_a_guardar[k]['estatus'] = nuevo_estatus
                if cambio_comentario: cambios_a_guardar[k]['comentario'] = comentario_actual
                if nueva_fecha_venc: cambios_a_guardar[k]['nueva_fecha_venc'] = nueva_fecha_venc

    if not df_editado_cobro.empty:
        for _, row in df_editado_cobro.iterrows():
            if row.get('Marcar Recibido'):
                k = generar_llave(row.get(col_id, ''), row.get(col_desc, ''))
                orig = originales.get(k, {'comentario': '', 'estatus_db': ''})
                comentario_actual = str(row.get(col_comentarios, '')).strip()
                if k not in cambios_a_guardar: cambios_a_guardar[k] = {}
                cambios_a_guardar[k]['estatus'] = "RECIBIDO"
                if comentario_actual != orig['comentario']: cambios_a_guardar[k]['comentario'] = comentario_actual

    if not df_editado_fact.empty:
        for _, row in df_editado_fact.iterrows():
            if row.get('Facturado'):
                k = generar_llave(row.get(col_id, ''), row.get(col_desc, ''))
                if k not in cambios_a_guardar: cambios_a_guardar[k] = {}
                cambios_a_guardar[k]['estatus'] = "FACTURADO"

    if not df_editado.empty:
        for _, row in df_editado.iterrows():
            k = generar_llave(row.get(col_id, ''), row.get(col_desc, ''))
            orig = originales.get(k, {'comentario': '', 'guia': '', 'estatus_db': '', 'remision_bool': False})
            
            orig_rem_bool = orig.get('remision_bool', False)
            actual_rem_bool = row.get('Remision', False)
            
            cambio_a_nueva_remision = actual_rem_bool and not orig_rem_bool
            quitar_remision = orig_rem_bool and not actual_rem_bool
            
            nuevo_estatus = None
            if row.get('Cancelar'): nuevo_estatus = "CANCELADO"
            elif row.get('Reasignacion'): nuevo_estatus = "EN PROCESAMIENTO"
            elif row.get('Recibido'): nuevo_estatus = "RECIBIDO"
            elif row.get('Entregado'): nuevo_estatus = "ENTREGADO"
            elif row.get('Remision'): nuevo_estatus = "EN TRANSITO"
            elif row.get('Pedido'): nuevo_estatus = "EN PROCESAMIENTO"
            elif quitar_remision: nuevo_estatus = "EN PROCESAMIENTO"
            
            cambio_estatus = (nuevo_estatus and nuevo_estatus != orig['estatus_db'])
            comentario_actual = str(row.get(col_comentarios, '')).strip()
            cambio_comentario = (comentario_actual != orig['comentario'])
            guia_actual = str(row.get(col_guia, '')).strip()
            cambio_guia = (guia_actual != orig['guia'])

            if cambio_estatus or cambio_comentario or cambio_guia or cambio_a_nueva_remision or quitar_remision:
                if k not in cambios_a_guardar: cambios_a_guardar[k] = {}
                if cambio_estatus: cambios_a_guardar[k]['estatus'] = nuevo_estatus
                if cambio_comentario: cambios_a_guardar[k]['comentario'] = comentario_actual
                if cambio_guia: cambios_a_guardar[k]['guia_link'] = guia_actual
                if quitar_remision: cambios_a_guardar[k]['remision_num'] = ""
                
                if cambio_a_nueva_remision:
                    cambios_a_guardar[k]['imprimir_remision'] = True
                    cambios_a_guardar[k]['generar_nuevo_folio'] = True
                    cambios_a_guardar[k]['usuario_rem'] = st.session_state.get('usuario_actual', 'Sistema')

    with st.spinner("Sincronizando con Google Sheets y generando PDFs..."):
        try:
            doc = init_connection()
            
            if cambios_a_guardar:
                ws_uni = doc.worksheet("BD_UNIFICADA")
                datos_uni = ws_uni.get_all_values()
                headers = [str(h).strip() for h in datos_uni[0]]
                
                idx_id = headers.index(col_id) if col_id in headers else -1
                idx_desc = headers.index(col_desc) if col_desc in headers else -1
                idx_estatus = headers.index(col_estatus) if col_estatus in headers else -1
                idx_coment = headers.index(col_comentarios) if col_comentarios in headers else -1
                idx_guia = headers.index(col_guia) if col_guia in headers else -1
                idx_rem = headers.index(col_remision) if col_remision in headers else -1
                idx_usr_rem = headers.index("Usuario Remisión") if "Usuario Remisión" in headers else -1
                
                max_folios = {"MULTI": 0, "GNP": 0}
                for pref in ["MULTI", "GNP"]:
                    regex_pat = rf'(?i){pref}\s*-\s*0*(\d+)'
                    numeros = df_completo[col_remision].astype(str).str.extract(regex_pat, expand=False)
                    max_f = pd.to_numeric(numeros, errors='coerce').max()
                    max_folios[pref] = int(max_f if pd.notna(max_f) else 0)

                llaves_a_imprimir = [k for k, v in cambios_a_guardar.items() if v.get('imprimir_remision') == True]
                marcados_remision = df_trabajo_completo[df_trabajo_completo.apply(lambda r: generar_llave(r.get(col_id, ''), r.get(col_desc, '')) in llaves_a_imprimir, axis=1)] if not df_trabajo_completo.empty else pd.DataFrame()
                
                grupos_imp = []
                if not marcados_remision.empty:
                    cols_agrup = [col_id, col_taller, col_marca, col_modelo, col_aseg]
                    agrupadores = [c for c in cols_agrup if c in marcados_remision.columns]
                    grupos_imp = marcados_remision.groupby(agrupadores)

                    for keys, df_g in grupos_imp:
                        aseg_val = str(keys[agrupadores.index(col_aseg)]).upper() if col_aseg in agrupadores else "GNP"
                        prefijo = "MULTI" if "MULTI" in aseg_val else "GNP"
                        
                        necesita_nuevo = False
                        folio_previo_grupo = ""
                        
                        for _, row_rem in df_g.iterrows():
                            key_rem = generar_llave(row_rem.get(col_id, ''), row_rem.get(col_desc, ''))
                            if key_rem in cambios_a_guardar:
                                if cambios_a_guardar[key_rem].get('generar_nuevo_folio'): necesita_nuevo = True
                                f_prev = str(row_rem.get(col_remision, '')).strip()
                                if f_prev and f_prev not in ['nan', 'None']: folio_previo_grupo = f_prev
                        
                        if necesita_nuevo and not folio_previo_grupo:
                            max_folios[prefijo] += 1
                            folio_asignado = f"{prefijo} - {max_folios[prefijo]:03d}"
                        else:
                            folio_asignado = folio_previo_grupo if folio_previo_grupo else f"{prefijo} - S/N"

                        for _, row_rem in df_g.iterrows():
                            key_rem = generar_llave(row_rem.get(col_id, ''), row_rem.get(col_desc, ''))
                            if key_rem in cambios_a_guardar:
                                if cambios_a_guardar[key_rem].get('generar_nuevo_folio'):
                                    cambios_a_guardar[key_rem]['remision_num'] = folio_asignado
                                cambios_a_guardar[key_rem]['folio_a_imprimir'] = folio_asignado

                if idx_id >= 0 and idx_desc >= 0:
                    for i in range(1, len(datos_uni)):
                        k = generar_llave(datos_uni[i][idx_id], datos_uni[i][idx_desc])
                        if k in cambios_a_guardar:
                            cambios = cambios_a_guardar[k]
                            if 'estatus' in cambios and idx_estatus >= 0: datos_uni[i][idx_estatus] = cambios['estatus']
                            if 'comentario' in cambios and idx_coment >= 0: datos_uni[i][idx_coment] = cambios['comentario']
                            if 'guia_link' in cambios and idx_guia >= 0: datos_uni[i][idx_guia] = cambios['guia_link']
                            if 'remision_num' in cambios and idx_rem >= 0: datos_uni[i][idx_rem] = cambios['remision_num']
                            if 'usuario_rem' in cambios and idx_usr_rem >= 0: datos_uni[i][idx_usr_rem] = cambios['usuario_rem']
                    
                    ws_uni.update(range_name='A1', values=datos_uni)

            # --- GENERACIÓN DE PDF EXCLUSIVA PARA DESCARGA LOCAL ---
            if 'grupos_imp' in locals() and grupos_imp:
                meses_es = {1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio", 7: "julio", 8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"}
                html_botones_flotantes = '<div style="position: fixed; top: 15px; left: 50%; transform: translateX(-50%); z-index: 999999; display: flex; flex-direction: column; gap: 10px; align-items: center; pointer-events: none;">'
                
                usuario_print = st.session_state.get('usuario_actual', 'Sistema')
                
                for keys, df_g in grupos_imp:
                    siniestro_v = keys[agrupadores.index(col_id)] if col_id in agrupadores else ""
                    taller_v = keys[agrupadores.index(col_taller)] if col_taller in agrupadores else ""
                    marca_v = keys[agrupadores.index(col_marca)] if col_marca in agrupadores else ""
                    modelo_v = keys[agrupadores.index(col_modelo)] if col_modelo in agrupadores else ""
                    
                    folio_str_print = "S/N"
                    for _, row_rem in df_g.iterrows():
                        key_rem = generar_llave(row_rem.get(col_id, ''), row_rem.get(col_desc, ''))
                        if key_rem in cambios_a_guardar and 'folio_a_imprimir' in cambios_a_guardar[key_rem]:
                            folio_str_print = cambios_a_guardar[key_rem]['folio_a_imprimir']
                            break
                    
                    fecha_actual = datetime.datetime.now()
                    hora_am_pm = fecha_actual.strftime('%I:%M %p')
                    firma_digital = f"Generado por: {usuario_print} - {fecha_actual.day}/{meses_es[fecha_actual.month][:3].capitalize()}/{fecha_actual.year} {hora_am_pm}"
                    
                    dir_v = tel_v = contacto_v = ""
                    col_cat_taller = next((c for c in df_catalogo.columns if "TALLER" in str(c).upper()), None)
                    if not df_catalogo.empty and col_cat_taller:
                        match_taller = df_catalogo[df_catalogo[col_cat_taller].astype(str).str.strip().str.upper() == str(taller_v).strip().upper()]
                        if not match_taller.empty:
                            col_dir = next((c for c in df_catalogo.columns if "DIRECCI" in str(c).upper()), None)
                            if col_dir: dir_v = str(match_taller.iloc[0].get(col_dir, '')).strip()
                    
                    def limpiar_texto(txt): return str(txt).encode('latin-1', 'replace').decode('latin-1')

                    pdf = FPDF(orientation='L', unit='mm', format='A4')
                    pdf.add_page()
                    
                    def dibujar_bloque_remision(x_offset, es_copia=False):
                        y_offset = 15
                        if os.path.exists("logo.png"):
                            try: pdf.image("logo.png", x_offset, y_offset - 3, 30)
                            except: pass
                        
                        pdf.set_font("Arial", 'B', 10)
                        pdf.set_text_color(0, 51, 102)
                        pdf.set_xy(x_offset + 32, y_offset)
                        pdf.cell(70, 5, limpiar_texto("PREMIER SERVICIOS Y REFACCIONES"), ln=True)
                        pdf.set_font("Arial", 'B', 8)
                        pdf.set_xy(x_offset + 32, y_offset + 5)
                        pdf.cell(70, 4, limpiar_texto("PMR SERVICIOS AUTOMOTRIZ"), ln=True)
                        pdf.set_font("Arial", '', 7)
                        pdf.set_text_color(100, 100, 100)
                        pdf.set_x(x_offset + 32)
                        pdf.cell(70, 3, limpiar_texto("ALLENDE 228, AÑO DE JUAREZ"), ln=True)
                        pdf.set_x(x_offset + 32)
                        pdf.cell(70, 3, limpiar_texto("SAN NICOLAS DE LOS GARZA, N.L. | PSA 211015 B30"), ln=True)

                        pdf.set_text_color(0, 0, 0)
                        pdf.set_xy(x_offset + 105, y_offset)
                        pdf.set_font("Arial", 'B', 9)
                        pdf.cell(30, 5, "REMISION", border=1, align='C', ln=True)
                        pdf.set_x(x_offset + 105)
                        pdf.set_text_color(200, 0, 0)
                        pdf.set_font("Arial", 'B', 10)
                        pdf.cell(30, 6, folio_str_print, border=1, align='C', ln=True)
                        
                        y_datos = y_offset + 22
                        pdf.set_xy(x_offset, y_datos)
                        pdf.set_fill_color(220, 220, 220)
                        pdf.set_text_color(0, 0, 0)
                        pdf.set_font("Arial", 'B', 7)
                        
                        pdf.cell(20, 5, "TALLER", border=1, fill=True)
                        pdf.set_font("Arial", '', 7)
                        pdf.cell(115, 5, limpiar_texto(f" {taller_v}"), border=1, ln=True)
                        pdf.set_x(x_offset)
                        pdf.set_font("Arial", 'B', 7)
                        pdf.cell(20, 5, "DIRECCION", border=1, fill=True)
                        pdf.set_font("Arial", '', 7)
                        pdf.cell(115, 5, limpiar_texto(f" {dir_v}"), border=1, ln=True)
                        pdf.set_x(x_offset)
                        pdf.set_font("Arial", 'B', 7)
                        pdf.cell(20, 5, "SINIESTRO", border=1, fill=True)
                        pdf.set_font("Arial", 'B', 8)
                        pdf.cell(45, 5, limpiar_texto(f" {siniestro_v}"), border=1)
                        pdf.set_font("Arial", 'B', 7)
                        pdf.cell(20, 5, "VEHICULO", border=1, fill=True)
                        pdf.set_font("Arial", '', 7)
                        pdf.cell(50, 5, limpiar_texto(f" {marca_v} {modelo_v}"), border=1, ln=True)

                        y_tabla = y_datos + 20
                        pdf.set_xy(x_offset, y_tabla)
                        pdf.set_fill_color(0, 0, 0)
                        pdf.set_text_color(255, 255, 255)
                        pdf.set_font("Arial", 'B', 7)
                        pdf.cell(15, 6, "CANT", border=1, fill=True, align='C')
                        pdf.cell(120, 6, "DESCRIPCION", border=1, fill=True, align='C')
                        pdf.ln(6)

                        pdf.set_text_color(0, 0, 0)
                        pdf.set_font("Arial", '', 7)
                        for _, row_rem in df_g.iterrows():
                            cant_v = str(row_rem.get(col_cant, 1))
                            if not cant_v.strip() or cant_v == 'nan': cant_v = '1'
                            desc_v = str(row_rem.get(col_desc, ''))
                            pdf.set_x(x_offset)
                            pdf.cell(15, 5, limpiar_texto(cant_v), border=1, align='C')
                            pdf.cell(120, 5, limpiar_texto(desc_v), border=1)
                            pdf.ln(5)
                            
                        # Firma Digital al pie del bloque
                        pdf.set_xy(x_offset, 192)
                        pdf.set_font("Arial", 'I', 6)
                        pdf.set_text_color(120, 120, 120)
                        pdf.cell(135, 4, limpiar_texto(firma_digital), align='R')

                    dibujar_bloque_remision(10, False)
                    pdf.set_draw_color(180, 180, 180)
                    pdf.line(148.5, 10, 148.5, 200)
                    pdf.set_draw_color(0, 0, 0)
                    dibujar_bloque_remision(152, True)

                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        pdf.output(tmp.name)
                        nombre_archivo = f"Remision_{folio_str_print.replace(' - ', '_')}_{siniestro_v}.pdf"
                        with open(tmp.name, "rb") as f: pdf_bytes = f.read()
                        b64 = base64.b64encode(pdf_bytes).decode()
                        html_botones_flotantes += f'<a href="data:application/pdf;base64,{b64}" download="{nombre_archivo}" style="pointer-events: auto; display: inline-block; padding: 12px 24px; background-color: #FF4B4B; color: white; text-decoration: none; border-radius: 8px; font-weight: bold; font-family: sans-serif; box-shadow: 0 4px 15px rgba(0,0,0,0.5); border: 2px solid white;">📄 Descargar {nombre_archivo}</a>'
                
                html_botones_flotantes += '</div>'
                st.markdown(html_botones_flotantes, unsafe_allow_html=True)
            
            st.toast("✅ ¡Bases actualizadas exitosamente en la nube!", icon="✅")
            
        except Exception as e:
            st.error(f"❌ Error general: {e}")
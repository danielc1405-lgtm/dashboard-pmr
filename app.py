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
st.set_page_config(page_title="PMR Hub AI", page_icon="📦", layout="wide", initial_sidebar_state="collapsed")

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

        /* --- ESTILO GLOBAL TERMINAL MATRIX --- */
        @keyframes matrix_pulse {
            0% { box-shadow: 0 0 10px rgba(0, 255, 65, 0.25), inset 0 0 15px rgba(0, 255, 65, 0.15); }
            50% { box-shadow: 0 0 22px rgba(0, 255, 65, 0.55), inset 0 0 25px rgba(0, 255, 65, 0.25); }
            100% { box-shadow: 0 0 10px rgba(0, 255, 65, 0.25), inset 0 0 15px rgba(0, 255, 65, 0.15); }
        }
        .matrix-terminal {
            background-color: #020502;
            background-image: 
                linear-gradient(rgba(0, 255, 65, 0.04) 1px, transparent 1px),
                radial-gradient(rgba(0, 40, 10, 0.35), #000000 90%);
            background-size: 100% 3px, 100% 100%;
            color: #00FF41;
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 13.5px;
            line-height: 1.45;
            padding: 16px 20px;
            border-radius: 10px;
            border: 1px solid #00FF41;
            animation: matrix_pulse 3s infinite ease-in-out;
            min-height: 180px;
            height: auto;
            white-space: pre-wrap;
            position: relative;
            text-shadow: 0 0 6px rgba(0, 255, 65, 0.65);
        }
        .matrix-header {
            color: #88FF99;
            font-family: 'Consolas', monospace;
            font-size: 11.5px;
            letter-spacing: 2px;
            border-bottom: 1px dashed rgba(0, 255, 65, 0.4);
            padding-bottom: 6px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
        }
        .matrix-katakana {
            color: rgba(0, 255, 65, 0.22);
            font-size: 11px;
            letter-spacing: 3px;
            user-select: none;
        }
        .matrix-cursor {
            display: inline-block;
            width: 9px;
            height: 15px;
            background-color: #00FF41;
            vertical-align: middle;
            animation: blink_mtx 0.8s infinite;
        }
        @keyframes blink_mtx { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
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
    st.markdown("<br>", unsafe_allow_html=True)
    
    col_logo1, col_logo2, col_logo3 = st.columns([1.5, 1, 1.5])
    with col_logo2:
        import os
        if os.path.exists("logo.png"):
            st.image("logo.png", use_container_width=True)
            
    st.markdown("<h1 style='text-align: center; color: #FF4B4B;'>🧠 PMR Hub AI</h1>", unsafe_allow_html=True)
    
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
    "📊 Analítico", "🚚 Operación del Día", "⚙️ Panel Operativo", "🛒 Compras", "🏢 Directorio", 
    "📦 Inventario", "📝 Remisiones", "🧾 Facturación", "🚚 Rutas", "Precios Promedio", "🔍 Consultas", "🛠️ Cuartel General"
]   

# --- FUNCIÓN DE LA VENTANA EMERGENTE (POP-UP CON LANZADOR DE BOTS) ---
@st.dialog("🖥️ Centro de Bots y Monitor Flotante PMR", width="large")
def abrir_popup_monitor():
    import html
    import subprocess
    import sys

    # Dividimos la parte superior: Lanzador a la izquierda y Estatus/WhatsApp a la derecha
    col_lanzador, col_resultados = st.columns([1.1, 1.9], gap="medium")

    with col_lanzador:
        with st.form("form_lanzador_bots_popup"):
            st.markdown("**1. Panel de Ejecución**")
            st.caption("Selecciona el robot a correr:")
            bot_sel_pop = st.selectbox(
                "Robot:",
                ["GNP Inpart", "Multiasistencia", "Paquetexpress (Rastreo)"],
                label_visibility="collapsed"
            )
            modo_ext_pop = st.radio(
                "Modo de Ejecución:",
                ["Oculto (Rápido)", "Visual (Ver Chrome)"],
                horizontal=True
            )
            btn_iniciar_pop = st.form_submit_button("🚀 Iniciar Robot", type="primary", use_container_width=True)

        if st.button("🧹 Limpiar Bandeja y Consola", use_container_width=True, key="btn_limpiar_popup"):
            st.session_state.pop('temp_wa_alerts', None)
            st.session_state.pop('temp_criticos_alerts', None)
            st.session_state.pop('temp_bot_log', None)
            st.session_state.pop('temp_bot_status', None)
            st.session_state.pop('temp_bot_resumen', None)

        spinner_pop = st.empty()

    # Contenedor para la Consola Matrix (abajo de las columnas para que ocupe todo el ancho)
    st.markdown("**🖥️ Consola Matrix en Tiempo Real**")
    contenedor_matrix_pop = st.empty()

    def pintar_matrix_pop(log_txt, activo=False):
        estado_mtx = "🟢 EJECUTANDO EN VIVO..." if activo else "⚡ SISTEMA EN ESPERA / COMPLETADO"
        cursor_html = '<span class="matrix-cursor"></span>' if activo else ''
        contenido_limpio = html.escape(log_txt) if log_txt else "Esperando orden de ejecución..."
        html_box = f"""
        <div class="matrix-terminal" style="max-height: 260px; overflow-y: auto;">
            <div class="matrix-header">
                <span>PMR // MATRIX_CORE_TERMINAL v2.6</span>
                <span class="matrix-katakana">ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄ010110</span>
                <span>{estado_mtx}</span>
            </div>
            <div>{contenido_limpio}{cursor_html}</div>
        </div>
        """
        contenedor_matrix_pop.markdown(html_box, unsafe_allow_html=True)

    # --- SI PRESIONAS "INICIAR ROBOT" DENTRO DEL POP-UP ---
    if btn_iniciar_pop:
        if bot_sel_pop == "GNP Inpart":
            archivo_ejecutar = "gnp_inpart.py"
        elif bot_sel_pop == "Multiasistencia":
            archivo_ejecutar = "sincronizador_multiasistencia.py"
        else:
            archivo_ejecutar = "motor_rastreo.py"

        arg_modo = "--oculto" if "Oculto" in modo_ext_pop else "--visual"

        with spinner_pop:
            with st.spinner(f"Corriendo {bot_sel_pop} en vivo..."):
                try:
                    with open("credentials.json", "w", encoding="utf-8") as f:
                        f.write(st.secrets["google_credentials"])

                    pintar_matrix_pop(f"[SISTEMA] Despertando a {bot_sel_pop}...\n", activo=True)
                    subprocess.run([sys.executable, '-m', 'playwright', 'install', 'chromium'], check=False)

                    cmd = [sys.executable, "-u", archivo_ejecutar]
                    if bot_sel_pop != "Paquetexpress (Rastreo)":
                        cmd.append(arg_modo)

                    env_bot = os.environ.copy()
                    env_bot["PYTHONIOENCODING"] = "utf-8"
                    env_bot["PYTHONUNBUFFERED"] = "1"

                    proceso = subprocess.Popen(
                        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, bufsize=1, env=env_bot, encoding="utf-8", errors="replace"
                    )

                    lineas_acumuladas = []
                    for linea_rt in iter(proceso.stdout.readline, ''):
                        if not linea_rt:
                            break
                        lineas_acumuladas.append(linea_rt)
                        pintar_matrix_pop("".join(lineas_acumuladas), activo=True)

                    proceso.stdout.close()
                    returncode = proceso.wait()
                    salida_completa = "".join(lineas_acumuladas).strip()

                    # Resumen
                    if bot_sel_pop == "Paquetexpress (Rastreo)":
                        guias_rev = len(re.findall(r"Buscando gu[íi]a:", salida_completa))
                        st.session_state['temp_bot_resumen'] = f"📊 **Resumen ({bot_sel_pop}):** {guias_rev} guías consultadas."
                    else:
                        revisados = "0"
                        m_multi = re.search(r"Quedan\s+(\d+)\s+siniestros", salida_completa)
                        m_gnp = re.search(r"Total le[íi]dos[^:]*:\s*(\d+)", salida_completa)
                        if m_multi: revisados = m_multi.group(1)
                        elif m_gnp: revisados = m_gnp.group(1)
                        st.session_state['temp_bot_resumen'] = f"📊 **Resumen ({bot_sel_pop}):** {revisados} pedidos revisados."

                    # Extraer WhatsApp
                    if "REPORTES LISTOS PARA COPIAR" in salida_completa:
                        parte_wa = re.split(r"REPORTES LISTOS PARA COPIAR(?: A WHATSAPP)?", salida_completa)[1]
                        for corte in ["🔄 PIEZAS REACTIVADAS", "🟠 CAMBIOS DE PRECIO", "🟡 ALERTAS DE PRECIO", "!!!!!"]:
                            if corte in parte_wa:
                                parte_wa = parte_wa.split(corte)[0]
                        st.session_state['temp_wa_alerts'] = re.sub(r'^[=\s]+', '', parte_wa).strip()
                    elif bot_sel_pop != "Paquetexpress (Rastreo)":
                        st.session_state['temp_wa_alerts'] = "No hubo asignaciones nuevas en esta corrida."

                    # Extraer Estatus Crítico
                    marcadores_alerta = ["🔄 PIEZAS REACTIVADAS", "🟠 CAMBIOS DE PRECIO", "🟡 ALERTAS DE PRECIO", "REVISIÓN DE ESTATUS CRÍTICO"]
                    idx_inicio_crit = -1
                    for m_al in marcadores_alerta:
                        pos = salida_completa.find(m_al)
                        if pos != -1 and (idx_inicio_crit == -1 or pos < idx_inicio_crit):
                            idx_inicio_crit = pos

                    if idx_inicio_crit != -1:
                        bloque_crit = salida_completa[idx_inicio_crit:]
                        lineas_crit = [l for l in bloque_crit.splitlines() if set(l.strip()) != {'!'} and "REVISIÓN DE ESTATUS CRÍTICO" not in l]
                        st.session_state['temp_criticos_alerts'] = "\n".join(lineas_crit).strip()
                    elif bot_sel_pop != "Paquetexpress (Rastreo)":
                        st.session_state['temp_criticos_alerts'] = "✅ Sin alertas críticas ni partidas vencidas."

                    # Guardar log limpio
                    salida_tecnica = salida_completa[:idx_inicio_crit] if idx_inicio_crit != -1 else salida_completa
                    if "REPORTES LISTOS PARA COPIAR" in salida_tecnica:
                        salida_tecnica = re.split(r"=+\s*\n\s*📱?\s*REPORTES LISTOS PARA COPIAR", salida_tecnica)[0]

                    st.session_state['temp_bot_log'] = salida_tecnica.strip()
                    st.session_state['temp_bot_status'] = f"✅ {bot_sel_pop} finalizado." if returncode == 0 else f"⚠️ {bot_sel_pop} terminó con advertencias."
                    st.cache_data.clear()

                except Exception as e:
                    st.error(f"Error al lanzar el bot: {e}")
                finally:
                    if os.path.exists("credentials.json"):
                        os.remove("credentials.json")

    # Pintamos la consola Matrix con el estado final (o previo si solo abriste la ventana)
    pintar_matrix_pop(st.session_state.get('temp_bot_log', ''), activo=False)

    # Llenamos la columna derecha con las pestañas de Estatus Crítico y WhatsApp actualizadas
    with col_resultados:
        t_crit, t_wa = st.tabs(["🚨 Estatus Crítico (Hoy y Vencidos)", "📱 Mensajes WhatsApp"])
        with t_crit:
            texto_criticos = st.session_state.get('temp_criticos_alerts', "Corre GNP Inpart o Multiasistencia para ver el radar aquí.")
            st.text_area("Criticos Output PopUp", value=texto_criticos, height=195, label_visibility="collapsed")
        with t_wa:
            texto_wa = st.session_state.get('temp_wa_alerts', "Corre un robot primero para ver los mensajes aquí.")
            st.text_area("WhatsApp Output PopUp", value=texto_wa, height=195, label_visibility="collapsed")

    if st.session_state.get('temp_bot_resumen'):
        st.caption(f"{st.session_state.get('temp_bot_status', '')} | {st.session_state.get('temp_bot_resumen', '')}")

# El parámetro vertical_alignment="center" alinea todo a la misma altura (6 columnas ahora)
col_logo, col_menu, col_aseg, col_btn_ref, col_btn_pop, col_btn = st.columns([1.2, 5.0, 1.4, 0.4, 0.4, 1.2], vertical_alignment="center")

with col_logo:
    try: 
        st.image("logo.png", use_column_width=True)
    except: 
        st.markdown("**PREMIER**")

with col_menu:
    vista_actual = st.radio("Navegación", opciones_menu, horizontal=True, label_visibility="collapsed")

with col_aseg:
    vistas_con_aseguradora = ["📊 Analítico", "⚙️ Panel Operativo", "🧾 Facturación", "🔍 Consultas"]
    if vista_actual in vistas_con_aseguradora:
        opciones_aseg = ["Multiasistencias", "GNP", "Todas (Consolidado)"] if vista_actual == "📊 Analítico" else ["Multiasistencias", "GNP"]
        aseguradora_sel = st.selectbox("Aseguradora", opciones_aseg, label_visibility="collapsed")
    else:
        aseguradora_sel = "MULTI" 

with col_btn_ref:
    if st.button("🔄", help="Forzar recarga de datos desde Google Sheets", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

with col_btn_pop:
    if st.button("🖥️", help="Abrir Pop-up con Estatus Crítico y Consola Matrix", use_container_width=True):
        abrir_popup_monitor()

with col_btn:
    btn_guardar = st.button("💾 Guardar", type="primary", use_container_width=True)
    espacio_spinner = st.empty()

# ==============================================================================
# === [BLOQUE 4: CARGA Y PROCESAMIENTO DE DATOS (LAZY LOADING)] ===
# ==============================================================================
import re

def obtener_dataframe(nombre_hoja, silent=False):
    try:
        doc = init_connection()
        ws = doc.worksheet(nombre_hoja)
        datos = ws.get_all_values()
        if not datos: return pd.DataFrame()
        headers = [str(h).strip() for h in datos[0]]
        filas_limpias = [fila for fila in datos[1:] if any(str(celda).strip() for celda in fila)]
        return pd.DataFrame(filas_limpias, columns=headers)
    except Exception as e:
        if not silent: st.error(f"Error cargando hoja {nombre_hoja}: {e}")
        return pd.DataFrame()

# --- CACHÉ INDEPENDIENTE POR MÓDULO ---
@st.cache_data(ttl=600)
def cargar_base_viva(): return obtener_dataframe("BD_UNIFICADA")

@st.cache_data(ttl=600)
def cargar_historico(): return obtener_dataframe("BD_HISTORICO", silent=True)

@st.cache_data(ttl=600)
def cargar_compras(): return obtener_dataframe("BD_COMPRAS", silent=True)

@st.cache_data(ttl=600)
def cargar_catalogos():
    df_cat = obtener_dataframe("BD_TALLERES", silent=True)
    if df_cat.empty: df_cat = obtener_dataframe("Catálogo", silent=True)
    df_prov = obtener_dataframe("BD_PROVEEDORES", silent=True)
    return df_cat, df_prov

@st.cache_data(ttl=600)
def cargar_inventario():
    df_inv = obtener_dataframe("BD_INVENTARIO", silent=True)
    if not df_inv.empty and 'Sin Existencia' in df_inv.columns:
        df_inv['Sin Existencia'] = df_inv['Sin Existencia'].astype(str).str.strip().str.upper().isin(['TRUE', 'SI', '1', 'X', 'V', 'VERDADERO'])
    return df_inv

# --- LÓGICA DE CARGA DIFERIDA (LAZY LOADING) ---
df_uni = cargar_base_viva()
if not df_uni.empty and 'Siniestro Relacionado' in df_uni.columns: 
    df_uni.rename(columns={'Siniestro Relacionado': 'Siniestro'}, inplace=True)

# Carga inteligente de histórico
df_historico = pd.DataFrame()
if vista_actual in ["🔍 Consultas", "📊 Analítico", "Precios Promedio", "📝 Remisiones", "🛠️ Cuartel General", "🚚 Operación del Día", "⚙️ Panel Operativo", "🚚 Rutas"] or modo_consulta:
    df_historico = cargar_historico()
    if not df_historico.empty and 'Siniestro Relacionado' in df_historico.columns and 'Siniestro' not in df_historico.columns:
        df_historico.rename(columns={'Siniestro Relacionado': 'Siniestro'}, inplace=True)

df_completo = df_uni.copy()
if not df_historico.empty:
    if vista_actual in ["🔍 Consultas", "📊 Analítico", "Precios Promedio"]:
        df_completo = pd.concat([df_completo, df_historico], ignore_index=True)
    elif vista_actual in ["⚙️ Panel Operativo", "🚚 Operación del Día", "🚚 Rutas"]:
        # Rescatamos del histórico los reembolsos o recolecciones que sigan activos
        c_est_h = next((c for c in df_historico.columns if "ESTATUS" in str(c).upper() or "STATUS" in str(c).upper()), None)
        if c_est_h:
            df_hist_activos = df_historico[df_historico[c_est_h].astype(str).str.upper().str.contains("PROCESO DE REEMBOLSO|RECOLECC|ENTREGADO|PAGO A TALLER", na=False)].copy()
            if not df_hist_activos.empty:
                df_completo = pd.concat([df_completo, df_hist_activos], ignore_index=True)

# Solo carga compras si la pestaña lo requiere (Incluye Operación del Día y Consultas)
df_compras = cargar_compras() if vista_actual in ["🛒 Compras", "📊 Analítico", "🚚 Operación del Día", "⚙️ Panel Operativo", "🚚 Rutas", "🔍 Consultas"] else pd.DataFrame()

# Solo carga catálogos si la pestaña los usa
df_catalogo = pd.DataFrame(); df_proveedores = pd.DataFrame()
if vista_actual in ["⚙️ Panel Operativo", "🚚 Operación del Día", "🛒 Compras", "🚚 Rutas", "🏢 Directorio", "📝 Remisiones", "🔍 Consultas"]:
    df_catalogo, df_proveedores = cargar_catalogos()

# Solo carga inventario si entras a su pestaña
df_inventario = cargar_inventario() if vista_actual == "📦 Inventario" else pd.DataFrame()

# --- PROCESAMIENTO DE DATOS ---
aseguradora_filtro = aseguradora_sel.strip().upper()
if "TODAS" in aseguradora_filtro:
    palabra_clave_aseg = "TODAS"
elif "MULTI" in aseguradora_filtro:
    palabra_clave_aseg = "MULTI"
else:
    palabra_clave_aseg = "GNP"

if not df_completo.empty:
    col_aseg_val = next((c for c in df_completo.columns if "ASEGURADORA" in str(c).upper()), None)
    if col_aseg_val and palabra_clave_aseg != "TODAS":
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

    # Optimización: Solo formatear fechas si la vista actual lo requiere visualmente o para filtros
    if vista_actual in ["⚙️ Panel Operativo", "📊 Analítico", "🛒 Compras", "🔍 Consultas"]:
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
df_editado_cobro = pd.DataFrame(); df_editado_fact = pd.DataFrame(); df_editado = pd.DataFrame(); df_editado_reemb = pd.DataFrame(); df_editado_transito_op = pd.DataFrame()    

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
            df_base_notif = df_completo if vista_actual == "🛒 Compras" else df_trabajo_completo
            df_en_proceso_notif = df_base_notif[df_base_notif[col_estatus].astype(str).str.upper() == "EN PROCESAMIENTO"].copy()
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
                    
                    

# ==============================================================================
# === [BLOQUE 6: VISTAS - ANALÍTICO Y OPERATIVO] ===
# ==============================================================================
import plotly.graph_objects as go
import pandas as pd
import datetime

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

# Función blindada contra columnas duplicadas en Google Sheets
def safe_apply_date(df_obj, col_name):
    if col_name and col_name in df_obj.columns:
        serie = df_obj[col_name].iloc[:, 0] if isinstance(df_obj[col_name], pd.DataFrame) else df_obj[col_name]
        return serie.apply(parse_dt_safe_op)
    return pd.Series(pd.NaT, index=df_obj.index)

# --- INTERCEPTOR DE PAQUETERÍA (AUTOMATIZACIÓN "ENTREGADOS EN CDR") ---
if not df_proceso.empty and col_estatus_envio and col_estatus:
    def verificar_entrega_paqueteria(row):
        rastreo = str(row.get(col_estatus_envio, '')).strip().lower()
        estatus_actual = str(row.get(col_estatus, '')).strip().upper()
        if "delivery" in rastreo or "entregado" in rastreo:
            if estatus_actual not in ["RECIBIDO", "FACTURADO", "CANCELADO", "REEMBOLSADO", "EN PROCESO DE REEMBOLSO", "EN PROCESO DE CAMBIO", "EN PROCESO DE RECOLECCIÓN", "PÉRDIDA TOTAL", "PAGO DE DAÑOS"]:
                return "ENTREGADO"
        return row[col_estatus]
        
    df_proceso[col_estatus] = df_proceso.apply(verificar_entrega_paqueteria, axis=1)
    df_trabajo[col_estatus] = df_trabajo.apply(verificar_entrega_paqueteria, axis=1)

# ------------------------------------------------------------------------------
# --- VISTA 1: ANALÍTICO ---
# ------------------------------------------------------------------------------
if vista_actual == "📊 Analítico":
    st.markdown(f"## 📊 Rendimiento de Operación ({aseguradora_sel})")
    
    def gen_llave_ana(s, d):
        sv = str(s).strip().upper()
        if sv.endswith('.0'): sv = sv[:-2]
        return f"{sv}_{' '.join(str(d).strip().upper().split())}"

    # --- 1. VELOCIDAD LOGÍSTICA ---
    st.markdown("#### ⏱️ 1. Velocidad Logística (Desde el 04/Sep/2026)")
    st.caption("Promedios de tiempo calculados con datos reales de la aseguradora seleccionada.")
    if col_asignacion and col_fecha_confi and not df_trabajo.empty:
        df_vel = df_trabajo.copy()
        
        def buscar_col_ana(keywords):
            for c in df_vel.columns:
                c_up = str(c).upper().replace('Í','I').replace('Ó','O')
                if all(k in c_up for k in keywords): return c
            return None
            
        c_envio_a = buscar_col_ana(["FECHA", "ENVIO"])
        c_rec_a = buscar_col_ana(["FECHA", "RECIB"])
        c_fac_a = buscar_col_ana(["FECHA", "FACTUR"])
        
        df_vel['F_Asig_D'] = safe_apply_date(df_vel, col_asignacion)
        
        fecha_inicio_sistema = pd.to_datetime('2026-09-04')
        df_vel_mes = df_vel[df_vel['F_Asig_D'] >= fecha_inicio_sistema].copy()
        
        if col_estatus:
            df_vel_mes = df_vel_mes[~df_vel_mes[col_estatus].astype(str).str.upper().isin(["CANCELADO", "PÉRDIDA TOTAL", "PAGO DE DAÑOS"])]
        
        if not df_vel_mes.empty:
            df_vel_mes['F_Conf_D'] = safe_apply_date(df_vel_mes, col_fecha_confi)
            df_vel_mes['F_Env_D'] = safe_apply_date(df_vel_mes, c_envio_a)
            df_vel_mes['F_Rec_D'] = safe_apply_date(df_vel_mes, c_rec_a)
            df_vel_mes['F_Fac_D'] = safe_apply_date(df_vel_mes, c_fac_a)
            
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

    # --- 2. RESUMEN FINANCIERO MENSUAL (ARRIBA DEL EMBUDO) ---
    st.markdown("#### 💰 2. Resumen Financiero Mensual")
    st.caption("Evolución de montos basada en la Fecha de Asignación (La suma de las 5 columnas equivale al total Asignado).")
    
    if col_asignacion and col_precio and col_estatus and not df_trabajo.empty:
        df_fin = df_trabajo.copy()
        df_fin['F_Asig_D'] = safe_apply_date(df_fin, col_asignacion)
        
        def clean_money(val):
            try: return float(str(val).replace('$', '').replace('\\', '').replace(',', '').strip())
            except: return 0.0
        df_fin['Monto'] = df_fin[col_precio].apply(clean_money)
        
        def cat_financiera(e):
            e_upper = str(e).upper().strip()
            if "FACTURADO" in e_upper or "RECIBIDO" in e_upper or "ENTREGADO" in e_upper or "PAGO A TALLER" in e_upper: return "✅ Concretado"
            if "PÉRDIDA TOTAL" in e_upper or "PERDIDA TOTAL" in e_upper: return "💥 PT"
            if "PAGO DE DAÑOS" in e_upper or "PAGO DE DANOS" in e_upper: return "💸 PDD"
            if "CANCELADO" in e_upper: return "🚫 Cancelado"
            return "⚙️ En Proceso"
            
        df_fin['Cat_Fin'] = df_fin[col_estatus].apply(cat_financiera)
        df_fin = df_fin[df_fin['F_Asig_D'].notna()].copy()
        
        if not df_fin.empty:
            df_fin['Año'] = df_fin['F_Asig_D'].dt.year
            df_fin['Mes_Sort'] = df_fin['F_Asig_D'].dt.strftime('%Y-%m')
            meses_es_nombres = {1:'Enero', 2:'Febrero', 3:'Marzo', 4:'Abril', 5:'Mayo', 6:'Junio', 7:'Julio', 8:'Agosto', 9:'Septiembre', 10:'Octubre', 11:'Noviembre', 12:'Diciembre'}
            df_fin['Mes_Str'] = df_fin['F_Asig_D'].apply(lambda d: f"{meses_es_nombres[d.month]} {d.year}")
            
            pivot_fin = pd.pivot_table(df_fin, values='Monto', index=['Año', 'Mes_Sort', 'Mes_Str'], columns='Cat_Fin', aggfunc='sum', fill_value=0.0).reset_index()
            
            cols_5 = ['⚙️ En Proceso', '✅ Concretado', '💸 PDD', '💥 PT', '🚫 Cancelado']
            for col_req in cols_5:
                if col_req not in pivot_fin.columns: pivot_fin[col_req] = 0.0
                
            pivot_fin['📥 Asignado'] = pivot_fin['⚙️ En Proceso'] + pivot_fin['✅ Concretado'] + pivot_fin['💸 PDD'] + pivot_fin['💥 PT'] + pivot_fin['🚫 Cancelado']
            
            pivot_fin = pivot_fin.sort_values('Mes_Sort', ascending=True)
            pivot_fin['📈 Acumulado Concretado'] = pivot_fin['✅ Concretado'].cumsum()
            
            cols_dinero = ['📥 Asignado', '⚙️ En Proceso', '✅ Concretado', '💸 PDD', '💥 PT', '🚫 Cancelado', '📈 Acumulado Concretado']
            for c in cols_dinero:
                pivot_fin[c] = pivot_fin[c].apply(lambda x: f"${x:,.2f}")
                
            pivot_fin = pivot_fin.sort_values('Mes_Sort', ascending=False)
            cols_mostrar = ['Mes_Str'] + cols_dinero
            
            anios_disp = sorted(pivot_fin['Año'].unique(), reverse=True)
            if anios_disp:
                anio_actual = anios_disp[0]
                df_actual = pivot_fin[pivot_fin['Año'] == anio_actual]
                st.markdown(f"##### 📅 Año {anio_actual}")
                st.dataframe(df_actual[cols_mostrar].rename(columns={'Mes_Str': 'Mes de Asignación'}), use_container_width=True, hide_index=True)
                
                for anio_ant in anios_disp[1:]:
                    df_ant = pivot_fin[pivot_fin['Año'] == anio_ant]
                    with st.expander(f"📁 Historial Financiero {anio_ant} (Da clic para expandir)"):
                        st.dataframe(df_ant[cols_mostrar].rename(columns={'Mes_Str': 'Mes de Asignación'}), use_container_width=True, hide_index=True)
        else:
            st.info("No hay fechas de asignación válidas para procesar el financiero.")
    else:
        st.info("No hay datos para calcular.")

    st.markdown("---")

    # --- 3. EMBUDO Y 4. TOP MARCAS (CERRADOS POR DEFECTO) ---
    c_graf1, c_graf2 = st.columns([1, 1.2])
    with c_graf1:
        st.markdown("#### 🌪️ 3. Embudo de Operación (Activos)")
        if not df_uni.empty and col_estatus:
            df_emb = df_uni.copy()
            if col_aseg and palabra_clave_aseg != "TODAS":
                df_emb = df_emb[df_emb[col_aseg].astype(str).str.upper().str.contains(palabra_clave_aseg, na=False)]
            f_conf = len(df_emb[df_emb[col_estatus].astype(str).str.upper().str.contains("CONFIRMAR", na=False)])
            f_proc = len(df_emb[df_emb[col_estatus].astype(str).str.upper() == "EN PROCESAMIENTO"])
            f_tran = len(df_emb[df_emb[col_estatus].astype(str).str.upper() == "EN TRANSITO"])
            f_ent = len(df_emb[df_emb[col_estatus].astype(str).str.upper() == "ENTREGADO"])
            
            etapas_fun = ["Por Confirmar", "En Procesamiento", "En Tránsito", "Entregados a Taller"]
            valores_fun = [f_conf, f_proc, f_tran, f_ent]
            
            fig_funnel = go.Figure(go.Funnel(
                y=etapas_fun, x=valores_fun, textinfo="value+percent initial",
                marker={"color": ["#FF4B4B", "#FF9800", "#FFEB3B", "#4CAF50"]}
            ))
            fig_funnel.update_layout(margin=dict(t=20, b=20, l=0, r=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_funnel, use_container_width=True)
            
    with c_graf2:
        st.markdown("#### 🏆 4. Análisis Histórico por Marca (Top 4)")
        if col_marca and col_modelo and not df_trabajo.empty:
            df_m = df_trabajo.copy()
            df_m['M_Lim'] = df_m[col_marca].astype(str).str.strip().str.upper()
            df_m['Mod_Lim'] = df_m[col_modelo].astype(str).str.strip().str.upper()
            
            df_m = df_m[(df_m['M_Lim'] != '') & (df_m['M_Lim'] != 'NAN') & (df_m['M_Lim'] != 'S/D')]
            df_m = df_m[(df_m['Mod_Lim'] != '') & (df_m['Mod_Lim'] != 'NAN') & (df_m['Mod_Lim'] != 'S/D')]

            def agrupar_pieza_familia(desc):
                d = str(desc).strip().upper()
                if not d or d in ['NAN', 'NONE', 'S/D']: return "OTRAS"
                if "QUINTA PUERTA" in d or "5TA PUERTA" in d or "TAPA CAJUELA" in d or "CAJUELA" in d: return "Tapa Cajuela / 5ta Puerta"
                if "PUERTA" in d or "PTA." in d or d.startswith("PTA "): return "Puertas"
                if "SALPICADERA" in d: return "Salpicaderas"
                if "GUARDAFANGO" in d or "TOLVA LODERA" in d or "LODERA" in d: return "Tolvas / Guardafangos"
                if "FACIA" in d or "FASCIA" in d: return "Fascias"
                if "FARO" in d: return "Faros"
                if "CALAVERA" in d: return "Calaveras"
                if "COFRE" in d: return "Cofres"
                if "PARRILLA" in d: return "Parrillas"
                if "ESPEJO" in d: return "Espejos"
                if "RADIADOR" in d or "CONDENSADOR" in d: return "Radiadores / Condensadores"
                if "TOLVA" in d: return "Tolvas"
                if "MOLDURA" in d or d.startswith("MOLD."): return "Molduras"
                if "REFUERZO" in d: return "Refuerzos"
                if "SOPORTE" in d or d.startswith("SOP."): return "Soportes"
                return d.split()[0].title()
            
            if col_desc and col_desc in df_m.columns:
                df_m['Familia_Pieza'] = df_m[col_desc].apply(agrupar_pieza_familia)
            else:
                df_m['Familia_Pieza'] = "S/D"
            
            top_brands = df_m.groupby('M_Lim').agg(Siniestros=('M_Lim', 'count')).reset_index().sort_values('Siniestros', ascending=False).head(4)
            
            for _, b_row in top_brands.iterrows():
                b_name = b_row['M_Lim']
                b_tot = b_row['Siniestros']
                
                df_mod = df_m[df_m['M_Lim'] == b_name]
                top_models = df_mod['Mod_Lim'].value_counts().head(4)
                top_piezas = df_mod[df_mod['Familia_Pieza'] != 'OTRAS']['Familia_Pieza'].value_counts().head(5)
                
                with st.expander(f"🚗 **{b_name}** | {b_tot} Partidas Históricas", expanded=False):
                    cm1, cm2 = st.columns(2)
                    with cm1:
                        st.markdown("**🚘 Modelos más movidos:**")
                        for mod, cnt in top_models.items():
                            st.markdown(f"- {mod} (`{cnt}`)")
                    with cm2:
                        st.markdown("**🛠️ Top 5 Piezas:**")
                        for pza, cnt_p in top_piezas.items():
                            st.markdown(f"- {pza} (`{cnt_p}`)")

# ------------------------------------------------------------------------------
# --- VISTA 1.5: OPERACIÓN DEL DÍA ---
# ------------------------------------------------------------------------------
elif vista_actual == "🚚 Operación del Día":
    st.markdown("## 🚚 Monitor Logístico Global (Operación del Día)")
    
    # --- 1. MONITOR DE RUTA EN VIVO ---
    doc = init_connection()
    try:
        ws_rutas = doc.worksheet("BD_RUTAS")
        datos_rutas = ws_rutas.get_all_values()
        df_rutas = pd.DataFrame(datos_rutas[1:], columns=[str(h).strip().upper() for h in datos_rutas[0]]) if len(datos_rutas) > 1 else pd.DataFrame()
    except Exception:
        df_rutas = pd.DataFrame()
        
    if not df_rutas.empty and 'ESTATUS' in df_rutas.columns:
        fecha_hoy_str = datetime.datetime.now(tz_mx).strftime("%d/%m/%Y")
        # Solo rutas programadas el día de HOY (las de días anteriores ya no se arrastran)
        df_rutas_dia = df_rutas[df_rutas['FECHA'].astype(str).str.contains(fecha_hoy_str, na=False)].copy()
        
        df_rutas_pendientes = df_rutas_dia[df_rutas_dia['ESTATUS'].astype(str).str.upper() == 'PENDIENTE']
        df_rutas_completados = df_rutas_dia[df_rutas_dia['ESTATUS'].astype(str).str.upper() == 'COMPLETADO']
        
        paradas_pendientes = df_rutas_pendientes['ID_RUTA'].nunique() if 'ID_RUTA' in df_rutas_dia.columns else len(df_rutas_pendientes)
        paradas_completadas = df_rutas_completados['ID_RUTA'].nunique() if 'ID_RUTA' in df_rutas_dia.columns else len(df_rutas_completados)
        total_paradas = paradas_pendientes + paradas_completadas
        
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("🚩 Viajes Asignados", total_paradas)
        col_m2.metric("✅ Completados por Operador", paradas_completadas)
        col_m3.metric("⏳ Pendientes en Calle", paradas_pendientes)
        
        if total_paradas > 0:
            progreso = paradas_completadas / total_paradas
            st.progress(progreso, text=f"Avance de Ruta: {int(progreso*100)}%")
            
            st.markdown("#### 📍 Destinos del Día")
            df_resumen = df_rutas_dia.groupby('ID_RUTA').agg({
                'TIPO_OPERACION': 'first', 'LUGAR': 'first', 'SINIESTRO': lambda x: ", ".join(x.unique()),
                'VEHICULO': 'first', 'NOTA': 'first', 'PIEZA': 'count', 'ESTATUS': 'first'
            }).reset_index()
            
            df_resumen['No.'] = range(1, len(df_resumen) + 1)
            df_resumen['Estado'] = df_resumen['ESTATUS'].apply(lambda x: "✅ Completado" if str(x).strip().upper() == 'COMPLETADO' else "⏳ Pendiente")
            df_resumen['Operación'] = df_resumen['TIPO_OPERACION'].str.upper() + " (" + df_resumen['PIEZA'].astype(str) + " pzas)"
            
            def extraer_destino(nota):
                n = str(nota)
                if "Llevar a: " in n: return n.split("Llevar a: ")[1].split(" | ")[0]
                elif "Foráneo: " in n: return f"{n.split('Foráneo: ')[1].split(')')[0]} (Foráneo -> Base)"
                return "Mismo Lugar"
                
            def extraer_instruccion(nota):
                n = str(nota)
                if " | " in n: return n.split(" | ", 1)[1]
                elif "Llevar a: " not in n and "Foráneo: " not in n: return n
                return ""
                
            def acortar_vehiculo(v_str):
                partes = str(v_str).split('|')
                if len(partes) >= 2: return f"{' '.join(partes[0].strip().split()[:2])} | {partes[1].strip()}"
                return str(v_str)

            df_resumen['Destino Final'] = df_resumen['NOTA'].apply(extraer_destino)
            df_resumen['Instrucción'] = df_resumen['NOTA'].apply(extraer_instruccion)
            df_resumen['Vehículo Corto'] = df_resumen['VEHICULO'].apply(acortar_vehiculo)
            df_resumen['Eliminar'] = False
            
            df_destinos = df_resumen[['No.', 'LUGAR', 'Operación', 'SINIESTRO', 'Destino Final', 'Vehículo Corto', 'Instrucción', 'Estado', 'Eliminar']].rename(
                columns={'LUGAR': 'Lugar a Visitar', 'SINIESTRO': 'Siniestro(s)', 'Vehículo Corto': 'Vehículo'}
            )
            
            ed_destinos = st.data_editor(
                df_destinos,
                column_config={
                    "Eliminar": st.column_config.CheckboxColumn("❌", default=False, width="small")
                },
                disabled=['No.', 'Lugar a Visitar', 'Operación', 'Siniestro(s)', 'Destino Final', 'Vehículo', 'Instrucción', 'Estado'],
                hide_index=True,
                use_container_width=True,
                key="ed_destinos_dia_op"
            )
            
            seleccion_borrar = ed_destinos[ed_destinos['Eliminar'] == True]
            if not seleccion_borrar.empty:
                ids_borrar = set(df_resumen.loc[seleccion_borrar.index, 'ID_RUTA'].astype(str).str.strip())
                if st.button("🗑️ Eliminar", type="primary", key="btn_del_ruta_op"):
                    with st.spinner("Eliminando de la ruta..."):
                        try:
                            idx_id_r = [str(h).strip().upper() for h in datos_rutas[0]].index("ID_RUTA")
                            filas_conservar = [datos_rutas[0]] + [
                                fila_r for fila_r in datos_rutas[1:]
                                if not (len(fila_r) > idx_id_r and str(fila_r[idx_id_r]).strip() in ids_borrar)
                            ]
                            ws_rutas.clear()
                            ws_rutas.update(range_name='A1', values=filas_conservar, value_input_option='USER_ENTERED')
                            st.toast("Visita(s) eliminada(s)", icon="🗑️")
                            time.sleep(0.6)
                            st.rerun()
                        except Exception as e_del:
                            st.error(f"Error al eliminar: {e_del}")
            
            # --- APARTADO PARA REVIVIR COMPLETADAS POR ERROR DESDE EL DASHBOARD ---
            df_comp_hoy = df_resumen[df_resumen['ESTATUS'].astype(str).str.upper() == 'COMPLETADO'].copy()
            if not df_comp_hoy.empty:
                with st.expander(f"♻️ Visitas Completadas Hoy ({len(df_comp_hoy)}) — Revivir si el operador marcó por error", expanded=False):
                    c_rev1, c_rev2 = st.columns([3, 1], vertical_alignment="bottom")
                    with c_rev1:
                        opciones_rev = [f"{r['ID_RUTA']} | {r['LUGAR']} ({r['Operación']} - {r['SINIESTRO']})" for _, r in df_comp_hoy.iterrows()]
                        ruta_a_revivir = st.selectbox("Selecciona la visita que deseas regresar al celular del chofer:", opciones_rev, key="sel_revivir_ruta_op")
                    with c_rev2:
                        if st.button("♻️ Revivir", type="primary", use_container_width=True, key="btn_revivir_ruta_op"):
                            id_target = ruta_a_revivir.split(" | ")[0].strip()
                            with st.spinner("Restaurando parada a PENDIENTE..."):
                                try:
                                    idx_id_r = [str(h).strip().upper() for h in datos_rutas[0]].index("ID_RUTA")
                                    idx_est_r = [str(h).strip().upper() for h in datos_rutas[0]].index("ESTATUS") + 1
                                    celdas_r = [gspread.Cell(row=i+2, col=idx_est_r, value="PENDIENTE") for i, fila_r in enumerate(datos_rutas[1:]) if len(fila_r) > idx_id_r and str(fila_r[idx_id_r]).strip() == id_target]
                                    if celdas_r:
                                        ws_rutas.update_cells(celdas_r, value_input_option='USER_ENTERED')
                                        st.success(f"✅ Parada {id_target} devuelta a PENDIENTE.")
                                        time.sleep(0.8)
                                        st.rerun()
                                except Exception as e_r:
                                    st.error(f"Error al revivir ruta: {e_r}")
        else:
            st.caption("No hay viajes activos despachados el día de hoy.")

    st.markdown("---")
    st.markdown("### 📦 Estatus de Piezas en Operación (Multiasistencias + GNP)")
    
    def gen_llave_op_dia(s, d):
        sv = str(s).strip().upper()
        if sv.endswith('.0'): sv = sv[:-2]
        return f"{sv}_{' '.join(str(d).strip().upper().split())}"

    # Diccionario de estados por taller para distinguir Ruta Local vs Foráneo
    dict_est_taller_op = {}
    if not df_catalogo.empty:
        c_t_cat = next((c for c in df_catalogo.columns if 'TALLER' in str(c).upper()), None)
        c_e_cat = next((c for c in df_catalogo.columns if 'ESTADO' in str(c).upper()), None)
        if c_t_cat and c_e_cat:
            dict_est_taller_op = dict(zip(df_catalogo[c_t_cat].astype(str).str.strip().str.upper(), df_catalogo[c_e_cat].astype(str).str.strip().str.upper()))

    # --- PUENTE AUTOMÁTICO: SI EL CHOFER COMPLETA UNA ENTREGA EN BD_RUTAS -> PASA A ENTREGADO EN BD_UNIFICADA ---
    llaves_entregadas_chofer = {}
    if not df_rutas.empty and {'TIPO_OPERACION', 'ESTATUS', 'SINIESTRO', 'PIEZA'}.issubset(df_rutas.columns):
        df_r_ent_comp = df_rutas[
            (df_rutas['TIPO_OPERACION'].astype(str).str.strip().str.upper() == 'ENTREGA') &
            (df_rutas['ESTATUS'].astype(str).str.strip().str.upper() == 'COMPLETADO')
        ]
        for _, r_ch in df_r_ent_comp.iterrows():
            k_ch = gen_llave_op_dia(r_ch.get('SINIESTRO', ''), r_ch.get('PIEZA', ''))
            f_ch = str(r_ch.get('FECHA', '')).split()[0].strip()
            llaves_entregadas_chofer[k_ch] = estandarizar_fechas_mx(f_ch) if f_ch else hoy_str

    df_op_dia = df_completo.copy() if not df_completo.empty else pd.DataFrame()
    
    if not df_op_dia.empty and col_estatus:
        c_rec_sync_col = next((c for c in df_op_dia.columns if "FECHA REC" in str(c).upper() or "FECHA ENT" in str(c).upper()), None)
        llaves_por_sincronizar_chofer = {}

        def clasificar_estatus_logistico(row):
            est = str(row.get(col_estatus, '')).strip().upper()
            rastreo = str(row.get(col_estatus_envio, '')).strip().lower() if col_estatus_envio else ''
            guia_val = str(row.get(col_guia, '')).strip() if col_guia else ''
            k_row = gen_llave_op_dia(row.get(col_id, ''), row.get(col_desc, ''))
            
            if "TRANSITO (RECOLECC" in est:
                return "EN TRANSITO (RECOLECCIÓN)"
            est_cerrados = ["RECIBIDO", "FACTURADO", "CANCELADO", "REEMBOLSADO", "EN PROCESO DE REEMBOLSO", "EN PROCESO DE CAMBIO", "EN PROCESO DE RECOLECCIÓN", "PÉRDIDA TOTAL", "PAGO DE DAÑOS"]
            if est in est_cerrados or est == "PAGO A TALLER":
                return est
            # Si el chofer ya marcó COMPLETADO en BD_RUTAS y en BD_UNIFICADA seguía EN TRANSITO:
            if k_row in llaves_entregadas_chofer and est in ["EN TRANSITO", "EN PROCESAMIENTO"]:
                llaves_por_sincronizar_chofer[k_row] = llaves_entregadas_chofer[k_row]
                return "ENTREGADO"
            if "delivery" in rastreo or "entregado" in rastreo:
                return "ENTREGADO"
            if est != "ENTREGADO" and guia_val not in ['', 'nan', 'None', 'NAN']:
                return "EN TRANSITO"
            return est

        df_op_dia[col_estatus] = df_op_dia.apply(clasificar_estatus_logistico, axis=1)

        # Si detectamos entregas recién completadas por el chofer, actualizamos BD_UNIFICADA en segundo plano
        if llaves_por_sincronizar_chofer:
            try:
                ws_u_ch = doc.worksheet("BD_UNIFICADA")
                datos_u_ch = ws_u_ch.get_all_values()
                if datos_u_ch:
                    h_u_ch = [str(h).strip().upper() for h in datos_u_ch[0]]
                    idx_id_ch = next((i for i, h in enumerate(h_u_ch) if "SINIESTRO" in h), -1)
                    idx_de_ch = next((i for i, h in enumerate(h_u_ch) if "DESCRIPCI" in h or "REFACCI" in h), -1)
                    idx_es_ch = next((i for i, h in enumerate(h_u_ch) if h in ["ESTATUS", "STATUS"]), -1)
                    idx_ev_ch = next((i for i, h in enumerate(h_u_ch) if "ESTATUS ENV" in h or "RASTREO" in h), -1)
                    idx_fr_ch = next((i for i, h in enumerate(h_u_ch) if "FECHA REC" in h or "FECHA ENT" in h), -1)
                    celdas_ch = []
                    if idx_id_ch >= 0 and idx_de_ch >= 0 and idx_es_ch >= 0:
                        for row_i, r_val in enumerate(datos_u_ch[1:], start=2):
                            if len(r_val) > max(idx_id_ch, idx_de_ch, idx_es_ch):
                                k_u_ch = gen_llave_op_dia(r_val[idx_id_ch], r_val[idx_de_ch])
                                if k_u_ch in llaves_por_sincronizar_chofer and str(r_val[idx_es_ch]).strip().upper() != "ENTREGADO":
                                    celdas_ch.append(gspread.Cell(row=row_i, col=idx_es_ch + 1, value="ENTREGADO"))
                                    if idx_ev_ch >= 0 and not str(r_val[idx_ev_ch]).strip():
                                        celdas_ch.append(gspread.Cell(row=row_i, col=idx_ev_ch + 1, value="Entregado (Ruta Local)"))
                                    if idx_fr_ch >= 0 and not str(r_val[idx_fr_ch]).strip():
                                        celdas_ch.append(gspread.Cell(row=row_i, col=idx_fr_ch + 1, value=llaves_por_sincronizar_chofer[k_u_ch]))
                        if celdas_ch:
                            ws_u_ch.update_cells(celdas_ch, value_input_option='USER_ENTERED')
                            st.cache_data.clear()
            except Exception:
                pass

        estatus_validos = ["ENTREGADO", "PAGO A TALLER", "EN TRANSITO", "EN TRANSITO (RECOLECCIÓN)", "EN PROCESAMIENTO", "EN PROCESO DE RECOLECCIÓN", "EN PROCESO DE REEMBOLSO"]
        df_mon = df_op_dia[df_op_dia[col_estatus].astype(str).str.upper().isin(estatus_validos)].copy()
            
        if not df_mon.empty:
            dict_prov_dia = {}; dict_llegada_dia = {}
            if not df_compras.empty:
                c_sin_a = next((c for c in df_compras.columns if "SINIESTRO" in str(c).upper()), None)
                c_desc_a = next((c for c in df_compras.columns if "DESCRIPCI" in str(c).upper()), None)
                if c_sin_a and c_desc_a:
                    df_c_ana = df_compras.copy()
                    df_c_ana['LLAVE'] = df_c_ana.apply(lambda r: gen_llave_op_dia(r.get(c_sin_a,''), r.get(c_desc_a,'')), axis=1)
                    dict_prov_dia = dict(zip(df_c_ana['LLAVE'], df_c_ana['Proveedor']))
                    
                    def parse_spanish_date_comp_a(d_str):
                        if not isinstance(d_str, str): return pd.NaT
                        d_str = d_str.lower().replace('-', '/') 
                        meses = {'ene':'01', 'feb':'02', 'mar':'03', 'abr':'04', 'may':'05', 'jun':'06', 'jul':'07', 'ago':'08', 'sep':'09', 'oct':'10', 'nov':'11', 'dic':'12'}
                        for text, num in meses.items():
                            if text in d_str: d_str = d_str.replace(text, num); break
                        try: return pd.to_datetime(d_str, format='%d/%m/%y', errors='coerce')
                        except: return pd.NaT
                    df_c_ana['Fecha_Compra_Dt'] = df_c_ana['Fecha Compra'].apply(parse_spanish_date_comp_a)
                    df_c_ana['ETA_Num'] = pd.to_numeric(df_c_ana['Tiempo Entrega (Días)'], errors='coerce').fillna(0)
                    df_c_ana['Llegada_Calc'] = df_c_ana['Fecha_Compra_Dt'] + pd.to_timedelta(df_c_ana['ETA_Num'], unit='d')
                    df_c_ana['Fecha Llegada'] = df_c_ana['Llegada_Calc'].dt.strftime('%d/%b/%y').fillna('-')
                    dict_llegada_dia = dict(zip(df_c_ana['LLAVE'], df_c_ana['Fecha Llegada']))

            def armar_vehiculo_dia(row):
                m = str(row.get(col_marca, '')).strip().upper()
                mod = str(row.get(col_modelo, '')).strip().upper()
                vehiculo = mod if mod.startswith(m) and m != "" else f"{m} {mod}".strip()
                if col_ano:
                    ano = str(row.get(col_ano, '')).strip()
                    if ano.endswith('.0'): ano = ano[:-2]
                    if ano not in ['', 'NAN', 'NONE']: vehiculo += f" | {ano}"
                return vehiculo

            df_mon['Vehiculo_Info'] = df_mon.apply(armar_vehiculo_dia, axis=1)
            df_mon['LLAVE'] = df_mon.apply(lambda r: gen_llave_op_dia(r.get(col_id,''), r.get(col_desc,'')), axis=1)
            df_mon['Proveedor'] = df_mon['LLAVE'].map(dict_prov_dia).fillna("-")
            df_mon['Llegada Est.'] = df_mon['LLAVE'].map(dict_llegada_dia).fillna("-")
            df_mon['Aseguradora'] = df_mon.get(col_aseg, pd.Series(["MULTI"]*len(df_mon))).apply(lambda x: "MULTI" if "MULTI" in str(x).upper() else ("GNP" if "GNP" in str(x).upper() else "OTRA"))
            
            c_env_disp = next((c for c in df_mon.columns if "FECHA ENV" in str(c).upper()), None)
            c_rec_disp = next((c for c in df_mon.columns if "FECHA REC" in str(c).upper() or "FECHA ENT" in str(c).upper()), None)
            c_col_recibio_w = next((c for c in df_mon.columns if str(c).strip().upper() in ["RECIBIO", "RECIBIÓ", "QUIEN RECIBIO", "QUIÉN RECIBIÓ"]), None)
            def obtener_quien_recibio(r):
                val_w = str(r.get(c_col_recibio_w, '')).strip() if c_col_recibio_w else ''
                if val_w not in ['', 'nan', 'None', 'NAN']: return val_w
                val_env = str(r.get(col_estatus_envio, '')).strip() if col_estatus_envio else ''
                if val_env in ['', 'nan', 'None', 'NAN']: return ''
                m_paren = re.search(r'\((.*?)\)', val_env)
                if m_paren: return m_paren.group(1).strip().title()
                limpio = re.sub(r'(?i)^entregado(\s+a\s+domicilio)?[\s:,-]*', '', val_env).strip()
                return limpio.title() if limpio else ''
            df_mon['_Quien_Recibio_Real'] = df_mon.apply(obtener_quien_recibio, axis=1)
            c_quien_rec = '_Quien_Recibio_Real'
            
            df_reembolsos_op = df_mon[df_mon[col_estatus].astype(str).str.upper() == "EN PROCESO DE REEMBOLSO"].copy()
            df_mon_normal = df_mon[df_mon[col_estatus].astype(str).str.upper() != "EN PROCESO DE REEMBOLSO"].copy()

            # Preparamos los DataFrames de cada pestaña de Operación del Día
            df_ent_op_tab = df_mon_normal[df_mon_normal[col_estatus].astype(str).str.upper().isin(["ENTREGADO", "PAGO A TALLER"])].copy()
            df_tra_op_tab = df_mon_normal[df_mon_normal[col_estatus].astype(str).str.upper() == "EN TRANSITO"].copy()
            df_recol_transito = df_mon_normal[df_mon_normal[col_estatus].astype(str).str.upper() == "EN TRANSITO (RECOLECCIÓN)"].copy()
            
            df_en_proc_op = df_mon_normal[df_mon_normal[col_estatus].astype(str).str.upper() == "EN PROCESAMIENTO"].copy()
            if not df_en_proc_op.empty:
                mask_sin_prov = df_en_proc_op['Proveedor'].astype(str).str.strip().isin(['-', '', 'nan', 'None', 'NAN'])
                df_con_prov_op = df_en_proc_op[~mask_sin_prov].copy()
                df_sin_prov_op = df_en_proc_op[mask_sin_prov].copy()
            else:
                df_con_prov_op = pd.DataFrame()
                df_sin_prov_op = pd.DataFrame()

            def lbl_od(icono, nombre, df_t):
                if df_t.empty: return f"{icono} {nombre} (0)"
                n_sin = df_t[col_id].nunique() if col_id and col_id in df_t.columns else len(df_t)
                return f"{icono} {nombre} ({n_sin} Sin. | {len(df_t)} Pzas)"

            tab_od_rec, tab_od_tra, tab_od_lleg, tab_od_sinp, tab_od_dev, tab_od_reemb = st.tabs([
                lbl_od("📥", "Por Recibir en Portal", df_ent_op_tab),
                lbl_od("🚚", "En Tránsito / Paquetería", df_tra_op_tab),
                lbl_od("🛒", "Compras por Llegar", df_con_prov_op),
                lbl_od("⏳", "Pendientes de Compra", df_sin_prov_op),
                lbl_od("↩️", "Devoluciones en Tránsito", df_recol_transito),
                lbl_od("💸", "Reembolsos", df_reembolsos_op)
            ])

            def format_rastreo(r):
                g = str(r.get('Guía', '')).strip()
                api = str(r.get('Rastreo API', '')).strip().lower()
                t_nom = str(r.get('Taller', '')).strip().upper()
                est_cdr = dict_est_taller_op.get(t_nom, "NUEVO LEON").replace("Ó", "O")
                es_local_cdr = ("NUEVO LEON" in est_cdr or "NL" in est_cdr or "N.L" in est_cdr)
                
                if g in ['', 'nan', 'none', 'NAN', 'None']:
                    return "🚚 Ruta Local / Sin Guía" if es_local_cdr else "⏳ Pendiente de Guía (Foráneo)"
                if api in ["falta información", "falta informacion", "", "nan", "none"]:
                    fecha_envio_dt = parse_dt_safe_op(str(r.get('📤 F. Envío', r.get('F. Envío', ''))))
                    if pd.notna(fecha_envio_dt) and (hoy_dt - fecha_envio_dt).days > 3: return "⚠️ API no responde"
                    return "Recién documentado (En sitio)"
                return r.get('Rastreo API', '')

            # PESTAÑA 1: POR RECIBIR EN PORTAL (ENTREGADO + PAGO A TALLER)
            with tab_od_rec:
                if not df_ent_op_tab.empty:
                    df_est = df_ent_op_tab.copy()
                    if c_env_disp and c_env_disp in df_est.columns: df_est[c_env_disp] = df_est[c_env_disp].apply(estandarizar_fechas_mx)
                    if c_rec_disp and c_rec_disp in df_est.columns: df_est[c_rec_disp] = df_est[c_rec_disp].apply(estandarizar_fechas_mx)
                    cols_ver = ['Aseguradora', col_taller, col_id, 'Vehiculo_Info', col_desc, col_estatus, col_paqueteria, col_guia, c_env_disp, c_rec_disp, c_quien_rec, col_comentarios]
                    rename_dict = {col_taller: 'Taller', col_id: 'Siniestro', 'Vehiculo_Info': 'Auto', col_desc: 'Pieza', col_estatus: 'Estatus', col_paqueteria: 'Paquetería', col_guia: 'Guía', c_env_disp: '📤 F. Envío', c_rec_disp: '📅 F. Entrega', c_quien_rec: '👤 Recibió / Detalle', col_comentarios: 'Observaciones'}
                    cols_finales = [c for c in cols_ver if c and c in df_est.columns]
                    df_vista = df_est[cols_finales].copy().rename(columns=rename_dict)
                    
                    if not modo_consulta and permiso_edicion:
                        df_vista['Marcar Recibido'] = False
                        cols_ed_op = [c for c in df_vista.columns if c not in ['Marcar Recibido', 'Observaciones']]
                        ed_ent_op = st.data_editor(
                            df_vista,
                            column_config={
                                "Marcar Recibido": st.column_config.CheckboxColumn("🏁 Recibido", default=False, width="small"),
                                "Observaciones": st.column_config.TextColumn("📝 Observaciones", width="medium")
                            },
                            disabled=cols_ed_op,
                            use_container_width=True,
                            hide_index=True,
                            key="ed_entregados_op_dia"
                        )
                        ed_ent_op[col_id] = df_est[col_id].values
                        ed_ent_op[col_desc] = df_est[col_desc].values
                        if col_comentarios and 'Observaciones' in ed_ent_op.columns:
                            ed_ent_op[col_comentarios] = ed_ent_op['Observaciones'].values
                        df_editado_cobro = ed_ent_op.copy()
                    else:
                        st.dataframe(df_vista, use_container_width=True, hide_index=True)
                else:
                    st.success("✅ No hay partidas pendientes de recepción en portal.")

            # PESTAÑA 2: EN TRÁNSITO / PAQUETERÍA
            with tab_od_tra:
                if not df_tra_op_tab.empty:
                    df_est = df_tra_op_tab.copy()
                    if c_env_disp and c_env_disp in df_est.columns: df_est[c_env_disp] = df_est[c_env_disp].apply(estandarizar_fechas_mx)
                    cols_ver = ['Aseguradora', col_taller, col_id, 'Vehiculo_Info', col_desc, col_paqueteria, col_guia, col_estatus_envio, c_env_disp, col_comentarios]
                    rename_dict = {col_taller: 'Taller', col_id: 'Siniestro', 'Vehiculo_Info': 'Auto', col_desc: 'Pieza', col_paqueteria: 'Paquetería', col_guia: 'Guía', col_estatus_envio: 'Rastreo API', c_env_disp: '📤 F. Envío', col_comentarios: 'Observaciones'}
                    cols_finales = [c for c in cols_ver if c and c in df_est.columns]
                    df_vista = df_est[cols_finales].copy().rename(columns=rename_dict)
                    if 'Rastreo API' in df_vista.columns:
                        df_vista['Rastreo API'] = df_vista.apply(format_rastreo, axis=1)
                        
                    if not modo_consulta and permiso_edicion:
                        df_vista['Marcar Entregado'] = False
                        df_vista['Marcar Recibido'] = False
                        cols_ed_tr = [c for c in df_vista.columns if c not in ['Marcar Entregado', 'Marcar Recibido', 'Paquetería', 'Guía', 'Observaciones']]
                        ed_tran_op = st.data_editor(
                            df_vista,
                            column_config={
                                "Paquetería": st.column_config.SelectboxColumn("Paquetería", options=["", "PAQUETEXPRESS", "FEDEX", "DHL", "ESTAFETA", "AFIMEX"], width="small"),
                                "Guía": st.column_config.TextColumn("Guía", width="small"),
                                "Marcar Entregado": st.column_config.CheckboxColumn("🚚 Entregado", default=False, width="small"),
                                "Marcar Recibido": st.column_config.CheckboxColumn("🏁 Recibido", default=False, width="small"),
                                "Observaciones": st.column_config.TextColumn("📝 Observaciones", width="medium")
                            },
                            disabled=cols_ed_tr,
                            use_container_width=True,
                            hide_index=True,
                            key="ed_transito_op_dia"
                        )
                        ed_tran_op[col_id] = df_est[col_id].values
                        ed_tran_op[col_desc] = df_est[col_desc].values
                        if col_paqueteria and 'Paquetería' in ed_tran_op.columns:
                            ed_tran_op[col_paqueteria] = ed_tran_op['Paquetería'].values
                        if col_guia and 'Guía' in ed_tran_op.columns:
                            ed_tran_op[col_guia] = ed_tran_op['Guía'].values
                        if col_comentarios and 'Observaciones' in ed_tran_op.columns:
                            ed_tran_op[col_comentarios] = ed_tran_op['Observaciones'].values
                        df_editado_transito_op = ed_tran_op.copy()
                    else:
                        st.dataframe(df_vista, use_container_width=True, hide_index=True)
                else:
                    st.success("✅ No hay piezas actualmente en tránsito.")

            # PESTAÑA 3: COMPRAS POR LLEGAR (CON PROVEEDOR)
            with tab_od_lleg:
                if not df_con_prov_op.empty:
                    cols_ver_p = ['Aseguradora', col_taller, col_id, 'Vehiculo_Info', col_desc, 'Proveedor', 'Llegada Est.', col_comentarios]
                    rename_dict_p = {col_taller: 'Taller', col_id: 'Siniestro', 'Vehiculo_Info': 'Auto', col_desc: 'Pieza', 'Llegada Est.': 'Llegada Prevista', col_comentarios: 'Observaciones'}
                    cols_f = [c for c in cols_ver_p if c and c in df_con_prov_op.columns]
                    st.dataframe(df_con_prov_op[cols_f].rename(columns=rename_dict_p), use_container_width=True, hide_index=True)
                else:
                    st.success("✅ No hay compras pendientes por llegar de proveedor.")

            # PESTAÑA 4: PIEZAS PENDIENTES DE COMPRA (SIN PROVEEDOR)
            with tab_od_sinp:
                if not df_sin_prov_op.empty:
                    cols_ver_sp = ['Aseguradora', col_taller, col_id, 'Vehiculo_Info', col_desc, col_comentarios]
                    rename_dict_p = {col_taller: 'Taller', col_id: 'Siniestro', 'Vehiculo_Info': 'Auto', col_desc: 'Pieza', col_comentarios: 'Observaciones'}
                    cols_f_sp = [c for c in cols_ver_sp if c and c in df_sin_prov_op.columns]
                    st.dataframe(df_sin_prov_op[cols_f_sp].rename(columns=rename_dict_p), use_container_width=True, hide_index=True)
                else:
                    st.success("✅ Todas las piezas en procesamiento tienen proveedor asignado.")

            # PESTAÑA 5: DEVOLUCIONES / RECOLECCIONES EN TRÁNSITO
            with tab_od_dev:
                if not df_recol_transito.empty:
                    cols_ver_recol = ['Aseguradora', col_taller, col_id, 'Vehiculo_Info', col_desc, col_paqueteria, col_guia, col_estatus_envio, col_comentarios]
                    rename_recol = {col_taller: 'Taller', col_id: 'Siniestro', 'Vehiculo_Info': 'Auto', col_desc: 'Pieza', col_paqueteria: 'Paquetería Guía', col_guia: 'Guía Devolución', col_estatus_envio: 'Rastreo API', col_comentarios: 'Observaciones'}
                    cols_f_rec = [c for c in cols_ver_recol if c and c in df_recol_transito.columns]
                    st.dataframe(df_recol_transito[cols_f_rec].rename(columns=rename_recol), use_container_width=True, hide_index=True)
                else:
                    st.success("✅ No hay recolecciones en tránsito hacia la base.")

            # PESTAÑA 6: REEMBOLSOS EN PROCESO
            with tab_od_reemb:
                if not df_reembolsos_op.empty:
                    cols_reemb = ['Aseguradora', col_taller, col_id, 'Vehiculo_Info', col_desc, col_precio, col_comentarios]
                    cols_reemb_f = [c for c in cols_reemb if c and c in df_reembolsos_op.columns]
                    df_vista_reemb = df_reembolsos_op[cols_reemb_f].rename(columns={col_taller: 'Taller', col_id: 'Siniestro', 'Vehiculo_Info': 'Auto', col_desc: 'Pieza', col_precio: 'Costo de Pieza', col_comentarios: 'Observaciones'})
                    st.dataframe(df_vista_reemb, use_container_width=True, hide_index=True)
                else:
                    st.success("✅ Sin reembolsos activos en proceso.")
        else: st.success("No hay operación logística pendiente en este momento.")
    else: st.warning("No hay datos en la base principal.")

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
    
    excluir_kpi = ["PÉRDIDA TOTAL", "PAGO DE DAÑOS"]
    por_confirmar_kpi = len(df_proceso[(df_proceso[col_estatus].astype(str).str.upper().str.contains("CONFIRMAR") | (df_proceso[col_estatus].astype(str).str.strip() == "")) & (~df_proceso[col_estatus].astype(str).str.upper().isin(excluir_kpi))]) if col_estatus else 0
    en_proceso = len(df_proceso[~df_proceso[col_estatus].astype(str).str.upper().str.contains("CONFIRMAR") & (~df_proceso[col_estatus].astype(str).str.upper().isin(excluir_kpi)) & (df_proceso[col_estatus].astype(str).str.strip() != "")]) if col_estatus else len(df_proceso)
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

    if col_estatus:
        df_proceso = df_proceso[~df_proceso[col_estatus].astype(str).str.upper().isin(excluir_kpi)]

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
        df_compras_temp = df_compras.copy()
        df_compras_temp['LLAVE_COMP'] = df_compras_temp.apply(lambda r: generar_llave_temp(r.get('Siniestro',''), r.get('Descripción Pieza','')), axis=1)
        dict_prov = dict(zip(df_compras_temp['LLAVE_COMP'], df_compras_temp['Proveedor']))
        dict_costo = dict(zip(df_compras_temp['LLAVE_COMP'], df_compras_temp['Costo Compra']))
        df_filtrado['LLAVE_TEMP'] = df_filtrado.apply(lambda r: generar_llave_temp(r.get(col_id,''), r.get(col_desc,'')), axis=1)
        df_filtrado['Proveedor'] = df_filtrado['LLAVE_TEMP'].map(dict_prov).fillna("")
        def safe_float(v):
            try: return float(str(v).replace('$', '').replace(',', '').strip())
            except: return 0.0
        df_filtrado['Costo Compra'] = df_filtrado['LLAVE_TEMP'].map(dict_costo).apply(safe_float)
    else:
        df_filtrado['Proveedor'] = ""; df_filtrado['Costo Compra'] = 0.0

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

    # --- PREPARACIÓN DE LOS 7 DATAFRAMES DEL PANEL OPERATIVO ---
    cond_confirmar = df_filtrado[col_estatus].astype(str).str.upper().str.contains("CONFIRMAR") | (df_filtrado[col_estatus].fillna('').astype(str).str.strip() == "")
    df_por_confirmar = df_filtrado[cond_confirmar].copy() if col_estatus else pd.DataFrame()

    regex_excluir = "CONFIRMAR|ENTREGADO|PAGO A TALLER|RECIBIDO|FACTURADO|CANCELADO|RECOLEC|REEMBOLSO|PÉRDIDA TOTAL|PAGO DE DAÑOS"
    df_vencimientos = df_filtrado[(df_filtrado[col_vencimiento] == hoy_str) & (~df_filtrado[col_estatus].astype(str).str.upper().str.contains(regex_excluir)) & (df_filtrado[col_estatus].fillna('').astype(str).str.strip() != "")].copy() if col_vencimiento else pd.DataFrame()

    if col_vencimiento and not df_filtrado.empty:
        fechas_venc_filtro = df_filtrado[col_vencimiento].apply(parse_dt_safe_op)
        df_atrasadas = df_filtrado[(fechas_venc_filtro < hoy_dt) & (df_filtrado[col_vencimiento] != '') & (~df_filtrado[col_estatus].astype(str).str.upper().str.contains(regex_excluir)) & (df_filtrado[col_estatus].fillna('').astype(str).str.strip() != "")].copy()
    else:
        df_atrasadas = pd.DataFrame()

    df_por_recibir = df_filtrado[df_filtrado[col_estatus].astype(str).str.upper().isin(["ENTREGADO", "PAGO A TALLER"])].copy() if col_estatus else pd.DataFrame()

    if col_estatus and col_estatus in df_filtrado.columns:
        mask_asignados = (~df_filtrado[col_estatus].fillna('').astype(str).str.upper().str.contains(regex_excluir)) & (df_filtrado[col_estatus].fillna('').astype(str).str.strip() != "")
        df_asignados = df_filtrado[mask_asignados].copy()
    else:
        df_asignados = df_filtrado.copy()

    df_reembolsos = df_filtrado[df_filtrado[col_estatus].astype(str).str.upper().str.contains("REEMBOLSO")].copy() if col_estatus else pd.DataFrame()

    df_recoleccion = df_recoleccion_total.copy()
    if 'Estado_CDR' in df_proceso.columns: 
        df_recoleccion['Estado_CDR'] = df_recoleccion[col_taller].astype(str).str.strip().str.upper().map(dict_estados).fillna("S/D") if col_taller else "S/D"
    if estado_sel: df_recoleccion = df_recoleccion[df_recoleccion['Estado_CDR'].astype(str).isin(estado_sel)]
    if taller_sel: df_recoleccion = df_recoleccion[df_recoleccion[col_taller].astype(str).isin(taller_sel)]
    if siniestro_sel:
        ids_sel = [s.split(" - ")[0] for s in siniestro_sel]
        df_recoleccion = df_recoleccion[df_recoleccion[col_id].isin(ids_sel)]
    if desc_sel: df_recoleccion = df_recoleccion[df_recoleccion[col_desc].astype(str).isin(desc_sel)]

    st.markdown("---")

    # --- PESTAÑAS DE ESTATUS EN PANEL OPERATIVO ---
    # --- FUNCIÓN PARA CONTAR SINIESTROS (PEDIDOS) Y PIEZAS EN CADA PESTAÑA ---
    def lbl_po(icono, titulo, df_b):
        if df_b.empty: return f"{icono} {titulo} (0)"
        n_sin = df_b['Agrupador_Visual'].nunique() if 'Agrupador_Visual' in df_b.columns else (df_b[col_id].nunique() if col_id and col_id in df_b.columns else len(df_b))
        return f"{icono} {titulo} ({n_sin} Sin. | {len(df_b)} Pzas)"

    # --- PESTAÑAS DE ESTATUS EN PANEL OPERATIVO ---
    tab_po_conf, tab_po_vhoy, tab_po_vatr, tab_po_recib, tab_po_asig, tab_po_reemb, tab_po_recol = st.tabs([
        lbl_po("⏳", "Por Confirmar", df_por_confirmar),
        lbl_po("🚨", "Vencen Hoy", df_vencimientos),
        lbl_po("❌", "Atrasados", df_atrasadas),
        lbl_po("📥", "Por Recibir", df_por_recibir),
        lbl_po("📋", "Asignados", df_asignados),
        lbl_po("💸", "Reembolsos", df_reembolsos),
        lbl_po("↩️", "Recolección", df_recoleccion)
    ])

    # 1. PESTAÑA: PIEZAS POR CONFIRMAR
    with tab_po_conf:
        dfs_editados_conf = []
        if not df_por_confirmar.empty:
            for taller, df_taller in df_por_confirmar.groupby(col_taller):
                n_sin_t = df_taller['Agrupador_Visual'].nunique()
                with st.expander(f"🏢 {taller} — 🚗 {n_sin_t} Pedido(s) | 📦 {len(df_taller)} Pieza(s)", expanded=False):
                    for siniestro_auto, df_grupo in df_taller.groupby('Agrupador_Visual'):
                        st.markdown(f"**🚗 Pedido / Siniestro: `{siniestro_auto}` | {df_grupo['Vehiculo_Info'].iloc[0]}**")
                        if permiso_edicion: 
                            df_grupo['Confirmar Surtido'] = False; df_grupo['Pago_Danos'] = False; df_grupo['Cancelar'] = False; df_grupo['Pérdida Total'] = False; df_grupo['PDD'] = False
                            cols_visibles = [c for c in [col_id, col_cant, col_desc, col_origen, col_precio, col_vencimiento] if c in df_grupo.columns] + ['Proveedor', 'Costo Compra', 'Confirmar Surtido', 'Pago_Danos', 'Cancelar', 'Pérdida Total', 'PDD'] + [c for c in [col_comentarios] if c in df_grupo.columns]
                            config_conf = base_config.copy()
                            config_conf.update({"Confirmar Surtido": st.column_config.CheckboxColumn("✅ Confirmar", default=False), "Pago_Danos": st.column_config.CheckboxColumn("💵 Pago *", default=False), "Cancelar": st.column_config.CheckboxColumn("🚫 Can", default=False), "Pérdida Total": st.column_config.CheckboxColumn("💥 PT", default=False), "PDD": st.column_config.CheckboxColumn("💸 PDD", default=False), "Proveedor": st.column_config.SelectboxColumn("🏢 Proveedor", options=lista_proveedores), "Costo Compra": st.column_config.NumberColumn("💲 Costo ($)", format="%.2f")})
                            columnas_editables = ['Proveedor', 'Costo Compra', 'Confirmar Surtido', 'Pago_Danos', 'Cancelar', 'Pérdida Total', 'PDD', col_comentarios]
                            df_editado_parcial = st.data_editor(df_grupo[cols_visibles], column_config=config_conf, disabled=[c for c in cols_visibles if c not in columnas_editables], hide_index=True, use_container_width=True, key=f"ed_conf_{taller}_{siniestro_auto}")
                            for col in df_grupo.columns:
                                if col not in df_editado_parcial.columns: df_editado_parcial[col] = df_grupo[col].values
                            dfs_editados_conf.append(df_editado_parcial)
                        else:
                            cols_visibles = [c for c in [col_id, col_cant, col_desc, col_origen, col_precio, col_vencimiento, col_comentarios] if c in df_grupo.columns]
                            st.dataframe(df_grupo[cols_visibles], column_config=base_config, hide_index=True, use_container_width=True)
            if dfs_editados_conf: df_editado_conf = pd.concat(dfs_editados_conf, ignore_index=True)
        else:
            st.success("✅ No hay partidas pendientes por confirmar.")

    # 2. PESTAÑA: VENCIMIENTOS DE HOY
    with tab_po_vhoy:
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
        else:
            st.success("✅ No hay partidas que venzan el día de hoy.")

    # 3. PESTAÑA: VENCIMIENTOS ATRASADOS
    with tab_po_vatr:
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
        else:
            st.success("✅ Sin vencimientos atrasados.")

    # 4. PESTAÑA: POR RECIBIR (ENTREGADOS EN CDR / PAGO A TALLER)
    with tab_po_recib:
        if not df_por_recibir.empty:
            c_f_entrega = next((c for c in df_por_recibir.columns if any(x in str(c).upper() for x in ["FECHA REC", "FECHA ENT", "LLEGADA"])), None)
            if c_f_entrega:
                df_por_recibir[c_f_entrega] = df_por_recibir[c_f_entrega].apply(estandarizar_fechas_mx)
                base_config[c_f_entrega] = st.column_config.TextColumn("📅 F. Entrega", disabled=True)
            
            col_fecha_lista = [c_f_entrega] if c_f_entrega else []

            if permiso_edicion:
                df_por_recibir['Marcar Recibido'] = False
                cols_visibles = [c for c in [col_id, 'Vehiculo_Info', col_taller, col_cant, col_desc, col_origen, col_precio, col_estatus] if c in df_por_recibir.columns] + ['Marcar Recibido'] + [c for c in [col_paqueteria, col_guia] + col_fecha_lista + [col_comentarios] if c in df_por_recibir.columns]
                config_cobro = base_config.copy()
                config_cobro.update({"Marcar Recibido": st.column_config.CheckboxColumn("🏁 Marcar Recibido", default=False)})
                df_editado_cobro = st.data_editor(df_por_recibir[cols_visibles], column_config=config_cobro, disabled=[c for c in cols_visibles if c not in ['Marcar Recibido', col_comentarios]], hide_index=True, use_container_width=True, key="ed_cobro")
                for col in df_por_recibir.columns: 
                    if col not in df_editado_cobro.columns: df_editado_cobro[col] = df_por_recibir[col].values
            else:
                cols_visibles = [c for c in [col_id, 'Vehiculo_Info', col_taller, col_cant, col_desc, col_origen, col_precio, col_paqueteria, col_guia] + col_fecha_lista + [col_comentarios] if c in df_por_recibir.columns]
                st.dataframe(df_por_recibir[cols_visibles], column_config=base_config, hide_index=True, use_container_width=True)
        else:
            st.info("No hay partidas pendientes de recepción en portal para esta aseguradora.")

    # 5. PESTAÑA: PEDIDOS ASIGNADOS (GENERAL)
    with tab_po_asig:
        dfs_editados = []
        if not df_asignados.empty:
            if col_estatus:
                estatus_upper = df_asignados[col_estatus].astype(str).str.upper()
                df_asignados['Entregado'] = estatus_upper.str.contains("ENTREGADO")
                df_asignados['Recibido'] = estatus_upper.str.contains("RECIBIDO")
                df_asignados['Cancelar'] = estatus_upper.str.contains("CANCELADO")
                df_asignados['Pago_Danos'] = estatus_upper.str.contains("PAGO DE DAÑOS")
            
            for taller, df_taller in df_asignados.groupby(col_taller):
                n_sin_t = df_taller['Agrupador_Visual'].nunique()
                with st.expander(f"🏢 {taller} — 🚗 {n_sin_t} Pedido(s) | 📦 {len(df_taller)} Pieza(s)", expanded=False):
                    for siniestro_auto, df_grupo in df_taller.groupby('Agrupador_Visual'):
                        st.markdown(f"**🚗 Pedido / Siniestro: `{siniestro_auto}` | {df_grupo['Vehiculo_Info'].iloc[0]}**")
                        if permiso_edicion:
                            cols_visibles = [c for c in [col_id, col_cant, col_desc, col_origen, col_precio, col_vencimiento] if c in df_grupo.columns] + ['Proveedor', 'Costo Compra'] + [c for c in [col_paqueteria, col_guia, col_estatus_envio, col_remision] if c in df_grupo.columns] + ['Entregado', 'Recibido', 'Pago_Danos', 'Cancelar'] + [c for c in [col_comentarios] if c in df_grupo.columns]
                            config_pedidos = base_config.copy()
                            config_pedidos.update({ 
                                "Proveedor": st.column_config.SelectboxColumn("🏢 Proveedor", options=lista_proveedores), 
                                "Costo Compra": st.column_config.NumberColumn("💲 Costo ($)", format="%.2f"), 
                                col_estatus_envio: st.column_config.TextColumn("📍 Rastreo", disabled=True), 
                                "Entregado": st.column_config.CheckboxColumn("🚚 Ent", default=False), 
                                "Recibido": st.column_config.CheckboxColumn("🏁 Rec", default=False), 
                                "Pago_Danos": st.column_config.CheckboxColumn("💵 Pago *", default=False),
                                "Cancelar": st.column_config.CheckboxColumn("🚫 Can", default=False) 
                            })
                            columnas_editables = ['Proveedor', 'Costo Compra', col_paqueteria, col_guia, col_remision, 'Entregado', 'Recibido', 'Pago_Danos', 'Cancelar', col_comentarios, col_vencimiento]
                            df_editado_parcial = st.data_editor(df_grupo[cols_visibles], column_config=config_pedidos, disabled=[c for c in cols_visibles if c not in columnas_editables], hide_index=True, use_container_width=True, key=f"ed_{taller}_{siniestro_auto}")
                            for col in df_grupo.columns:
                                if col not in df_editado_parcial.columns: df_editado_parcial[col] = df_grupo[col].values
                            dfs_editados.append(df_editado_parcial)
                        else:
                            cols_visibles = [c for c in [col_id, col_cant, col_desc, col_origen, col_precio, col_vencimiento, col_paqueteria, col_guia, col_estatus_envio, col_remision, col_comentarios] if c in df_grupo.columns]
                            st.dataframe(df_grupo[cols_visibles], column_config=base_config, hide_index=True, use_container_width=True)
            if dfs_editados: df_editado = pd.concat(dfs_editados, ignore_index=True)
        else:
            st.info("No hay pedidos asignados en proceso con los filtros actuales.")

    # 6. PESTAÑA: REEMBOLSOS
    with tab_po_reemb:
        if not df_reembolsos.empty:
            if permiso_edicion:
                df_reembolsos['Marcar Reembolsado'] = False
                cols_visibles = [c for c in [col_id, col_taller, col_cant, col_desc, col_origen, col_precio, col_estatus] if c in df_reembolsos.columns] + ['Marcar Reembolsado'] + [c for c in ['Proveedor', 'Costo Compra', col_paqueteria, col_guia, col_comentarios] if c in df_reembolsos.columns]
                config_reemb = base_config.copy()
                config_reemb.update({"Marcar Reembolsado": st.column_config.CheckboxColumn("✅ Reembolsado", default=False)})
                df_editado_reemb = st.data_editor(df_reembolsos[cols_visibles], column_config=config_reemb, disabled=[c for c in cols_visibles if c not in ['Marcar Reembolsado', col_paqueteria, col_guia, col_comentarios]], hide_index=True, use_container_width=True, key="ed_reemb")
                for col in df_reembolsos.columns: 
                    if col not in df_editado_reemb.columns: df_editado_reemb[col] = df_reembolsos[col].values
            else:
                cols_visibles = [c for c in [col_id, col_taller, col_cant, col_desc, col_origen, col_precio, col_estatus, 'Proveedor', 'Costo Compra', col_paqueteria, col_guia, col_comentarios] if c in df_reembolsos.columns]
                st.dataframe(df_reembolsos[cols_visibles], column_config=base_config, hide_index=True, use_container_width=True)
        else:
            st.success("✅ No hay reembolsos pendientes.")

    # 7. PESTAÑA: PIEZAS PARA RECOLECCIÓN
    df_editado_rec = pd.DataFrame()
    with tab_po_recol:
        if not df_recoleccion.empty:
            if permiso_edicion:
                df_recoleccion['En_Retorno'] = df_recoleccion[col_estatus].astype(str).str.upper().str.contains("TRANSITO", na=False)
                df_recoleccion['Guia_Retorno'] = ""
                cols_rec = [c for c in [col_id, col_taller, col_cant, col_desc, col_precio, col_estatus] if c in df_recoleccion.columns] + [c for c in [col_paqueteria, col_guia] if c in df_recoleccion.columns] + ['Guia_Retorno', 'En_Retorno'] + [c for c in [col_comentarios] if c in df_recoleccion.columns]
                config_rec = base_config.copy()
                if col_guia: config_rec[col_guia] = st.column_config.TextColumn("Guía Actual / Ida")
                config_rec["Guia_Retorno"] = st.column_config.TextColumn("🆕 Guía Retorno (Capturar aquí)")
                config_rec["En_Retorno"] = st.column_config.CheckboxColumn("🚚 En Retorno", default=False)
                cols_edit_rec = [col_paqueteria, col_guia, 'Guia_Retorno', 'En_Retorno', col_comentarios]
                df_editado_rec = st.data_editor(df_recoleccion[cols_rec], column_config=config_rec, disabled=[c for c in cols_rec if c not in cols_edit_rec], hide_index=True, use_container_width=True, key="ed_rec_panel")
                for col in df_recoleccion.columns: 
                    if col not in df_editado_rec.columns: df_editado_rec[col] = df_recoleccion[col].values
            else:
                cols_rec = [c for c in [col_id, col_taller, col_cant, col_desc, col_precio, col_estatus, col_paqueteria, col_guia, col_comentarios] if c in df_recoleccion.columns]
                st.dataframe(df_recoleccion[cols_rec], column_config=base_config, hide_index=True, use_container_width=True)
        else:
            st.success("✅ No hay piezas pendientes de recolección.")

# ==============================================================================
# === [BLOQUE 7: VISTAS - COMPRAS, TALLERES E INVENTARIO] ===
# ==============================================================================
elif vista_actual == "🛒 Compras":
    st.markdown("### 🛒 Panel de Compras (Gestión y Pagos)")
    
    # --- FUNCIÓN DE BÚSQUEDA LOCAL PARA COMPRAS ---
    def buscar_columna_compras(df_o_lista, exactos, parciales, excluidos=["ENV", "PAGO"]):
        cols = df_o_lista.columns if hasattr(df_o_lista, 'columns') else df_o_lista
        cols_up = [str(c).strip().upper() for c in cols]
        for ex in exactos:
            if ex in cols_up: return cols[cols_up.index(ex)]
        for i, c_up in enumerate(cols_up):
            for p in parciales:
                if p in c_up and not any(exc in c_up for exc in excluidos): return cols[i]
        return None

    def normalizar_llave_compra(sin_val, desc_val):
        s_clean = str(sin_val).strip().upper()
        if s_clean.endswith('.0'): s_clean = s_clean[:-2]
        d_clean = " ".join(str(desc_val).strip().upper().split())
        return f"{s_clean}_{d_clean}"

    # Diccionario global de Comentarios desde BD_UNIFICADA para que viajen a Compras
    dict_obs_global = {}
    if not df_completo.empty:
        c_id_obs = buscar_columna_compras(df_completo, ["PEDIDO / SINIESTRO", "SINIESTRO"], ["SINIESTRO"])
        c_de_obs = buscar_columna_compras(df_completo, ["DESCRIPCIÓN", "DESCRIPCION"], ["DESCRIPCI", "REFACCI"])
        c_co_obs = buscar_columna_compras(df_completo, ["COMENTARIOS", "OBSERVACIONES", "COMENTARIO", "OBSERVACION"], ["COMENTARIO", "OBSERVACION"])
        if c_id_obs and c_de_obs and c_co_obs:
            for _, r_ob in df_completo.iterrows():
                k_ob = normalizar_llave_compra(r_ob.get(c_id_obs, ''), r_ob.get(c_de_obs, ''))
                val_ob = str(r_ob.get(c_co_obs, '')).strip()
                if val_ob not in ['', 'nan', 'None']:
                    dict_obs_global[k_ob] = val_ob

    # 1. Ignoramos el filtro de aseguradora para compras y tomamos df_completo
    df_proceso_compras = pd.DataFrame()
    if not df_completo.empty:
        col_est_comp = buscar_columna_compras(df_completo, ["ESTATUS", "STATUS"], ["ESTATUS", "STATUS"])
        if col_est_comp:
            df_proceso_compras = df_completo[~df_completo[col_est_comp].astype(str).str.upper().isin(["PÉRDIDA TOTAL", "PAGO DE DAÑOS", "CANCELADO"])].copy()

    def normalizar_pago(val):
        v = str(val).strip().upper()
        if v in ['', 'NONE', 'NAN']: return ''
        if 'PLAT' in v: return 'Pago en Plataforma'
        if 'CONTRA' in v: return 'Contra Entrega'
        if 'CRED' in v or 'CRÉD' in v: return 'Crédito'
        if 'ANTICIPADO' in v or 'PREV' in v or 'CONTADO' in v: return 'Pago Anticipado'
        if 'ANTIC' in v: return 'Anticipo'
        return str(val).strip()

    if not df_proveedores.empty and 'Condición Pago' in df_proveedores.columns:
        df_proveedores['Condición Pago'] = df_proveedores['Condición Pago'].apply(normalizar_pago)

    # --- DICCIONARIO DE PROVEEDORES Y OPCIONES PARA DESPLEGABLE (INCLUYE EBAY / MERCADO LIBRE / INVENTARIO) ---
    dict_provs = {
        'EBAY': {'eta': '10', 'cond': 'Pago en Plataforma', 'dias': '0'},
        'MERCADO LIBRE': {'eta': '5', 'cond': 'Pago en Plataforma', 'dias': '0'},
        'INVENTARIO': {'eta': '0', 'cond': 'Pago Anticipado', 'dias': '0'}
    }
    lista_opciones_prov = [""]
    temp_provs = ["EBAY", "MERCADO LIBRE", "INVENTARIO"]
    if not df_proveedores.empty:
        for _, rp in df_proveedores.iterrows():
            p_n = str(rp.get('Proveedor', '')).strip().upper()
            s_n = str(rp.get('Sucursal', '')).strip().upper()
            if not p_n or p_n == 'NAN': continue
            llave_full = f"{p_n} - {s_n}" if (s_n and s_n != 'NAN') else p_n
            t_str = str(rp.get('Tiempo de Entrega', '')).upper()
            nums = re.findall(r'\d+', t_str)
            eta_v = nums[-1] if nums else "0"
            cond_v = normalizar_pago(rp.get('Condición Pago', ''))
            dias_v = str(rp.get('Días Crédito', '0')).strip()
            dict_provs[llave_full] = {'eta': eta_v, 'cond': cond_v, 'dias': dias_v}
            dict_provs[p_n] = {'eta': eta_v, 'cond': cond_v, 'dias': dias_v}
            temp_provs.append(llave_full)
    lista_opciones_prov = [""] + sorted(list(set(temp_provs)))

    # ==========================================================================
    # 1. PREPARACIÓN DE DATOS PARA PESTAÑAS DE COMPRAS
    # ==========================================================================
    df_por_comprar = pd.DataFrame()
    if not df_proceso_compras.empty and col_est_comp:
        df_en_proc = df_proceso_compras[df_proceso_compras[col_est_comp].astype(str).str.upper().str.strip() == "EN PROCESAMIENTO"].copy()

        llaves_ya_compradas = set()
        if not df_compras.empty:
            c_sin_comp = buscar_columna_compras(df_compras, ["SINIESTRO", "PEDIDO / SINIESTRO"], ["SINIESTRO"])
            c_pza_comp = buscar_columna_compras(df_compras, ["DESCRIPCIÓN PIEZA", "DESCRIPCION PIEZA", "PIEZA"], ["DESCRIP", "PIEZA"])
            c_prv_comp = buscar_columna_compras(df_compras, ["PROVEEDOR"], ["PROVEEDOR"])
            if c_sin_comp and c_pza_comp:
                for _, rc in df_compras.iterrows():
                    s_c = str(rc.get(c_sin_comp, '')).strip()
                    d_c = str(rc.get(c_pza_comp, '')).strip()
                    p_c = str(rc.get(c_prv_comp, '')).strip() if c_prv_comp else 'OK'
                    if s_c and d_c and p_c not in ['', 'nan', 'None', 'NAN']:
                        llaves_ya_compradas.add(normalizar_llave_compra(s_c, d_c))

        if not df_en_proc.empty:
            c_id_c = buscar_columna_compras(df_en_proc, ["PEDIDO / SINIESTRO", "SINIESTRO"], ["SINIESTRO"])
            c_desc_c = buscar_columna_compras(df_en_proc, ["DESCRIPCIÓN", "DESCRIPCION"], ["DESCRIPCI", "REFACCI"])
            df_en_proc['_llave_compra'] = df_en_proc.apply(
                lambda r: normalizar_llave_compra(r.get(c_id_c, ''), r.get(c_desc_c, '')), axis=1
            )
            df_por_comprar = df_en_proc[~df_en_proc['_llave_compra'].isin(llaves_ya_compradas)].copy()

    c_id_cnt_c = buscar_columna_compras(df_por_comprar, ["PEDIDO / SINIESTRO", "SINIESTRO"], ["SINIESTRO"]) if not df_por_comprar.empty else None
    n_sin_por_comp = df_por_comprar[c_id_cnt_c].nunique() if (not df_por_comprar.empty and c_id_cnt_c) else len(df_por_comprar)
    
    tab_comp_pend, tab_comp_lleg = st.tabs([
        f"🛒 1. Pendientes de Compra ({n_sin_por_comp} Sin. | {len(df_por_comprar)} Pzas)",
        "📦 2. Próximas Llegadas y Pagos"
    ])

    # ==========================================================================
    # PESTAÑA 1: PEDIDOS PENDIENTES DE COMPRA (CAPTURA RÁPIDA)
    # ==========================================================================
    with tab_comp_pend:
        if not df_por_comprar.empty:
            st.caption("Selecciona el **Proveedor** (incluso con costo $0.00), agrega **Observaciones** o marca **🚫 Cancelar** y presiona el botón rojo para aplicar.")
            
            c_id_c = buscar_columna_compras(df_por_comprar, ["PEDIDO / SINIESTRO", "SINIESTRO"], ["SINIESTRO"])
            c_marca_c = buscar_columna_compras(df_por_comprar, ["MARCA"], ["MARCA"])
            c_modelo_c = buscar_columna_compras(df_por_comprar, ["MODELO"], ["MODELO"])
            c_ano_c = buscar_columna_compras(df_por_comprar, ["AÑO", "ANO"], ["AÑO", "ANO"])
            c_vin_c = buscar_columna_compras(df_por_comprar, ["VIN", "SERIE"], ["VIN", "SERIE"])
            c_taller_c = buscar_columna_compras(df_por_comprar, ["TALLER", "CDR"], ["TALLER"])
            c_desc_c = buscar_columna_compras(df_por_comprar, ["DESCRIPCIÓN", "DESCRIPCION"], ["DESCRIPCI", "REFACCI"])
            c_precio_c = buscar_columna_compras(df_por_comprar, ["PRECIO", "COSTO VENTA"], ["PRECIO", "COSTO"])
            c_aseg_c = buscar_columna_compras(df_por_comprar, ["ASEGURADORA"], ["ASEGURADORA"])
            c_obs_c = buscar_columna_compras(df_por_comprar, ["COMENTARIOS", "OBSERVACIONES", "COMENTARIO", "OBSERVACION"], ["COMENTARIO", "OBSERVACION"])
            
            def armar_auto_limpio(r):
                m = str(r.get(c_marca_c, '')).strip().upper() if c_marca_c else ''
                mod = str(r.get(c_modelo_c, '')).strip().upper() if c_modelo_c else ''
                if mod.startswith(m) and m != "": return mod
                return f"{m} {mod}".strip()

            df_cap = pd.DataFrame()
            df_cap['Siniestro'] = df_por_comprar[c_id_c].astype(str).str.strip().values if c_id_c else ""
            df_cap['Taller'] = df_por_comprar[c_taller_c].astype(str).str.strip().values if c_taller_c else ""
            df_cap['Auto'] = df_por_comprar.apply(armar_auto_limpio, axis=1).values
            df_cap['Año'] = df_por_comprar[c_ano_c].astype(str).str.replace('.0', '', regex=False).str.strip().values if c_ano_c else ""
            df_cap['VIN / Serie'] = df_por_comprar[c_vin_c].astype(str).str.strip().str.upper().values if c_vin_c else ""
            df_cap['Pieza'] = df_por_comprar[c_desc_c].astype(str).str.strip().values if c_desc_c else ""
            df_cap['_Aseguradora'] = df_por_comprar[c_aseg_c].astype(str).str.strip().str.upper().values if c_aseg_c else "MULTI"
            
            if c_precio_c:
                df_cap['Precio Aut.'] = pd.to_numeric(df_por_comprar[c_precio_c].astype(str).str.replace('$', '', regex=False).str.replace(',', '', regex=False).str.strip(), errors='coerce').fillna(0.0).values
            else: df_cap['Precio Aut.'] = 0.0

            df_cap['Proveedor'] = ""
            df_cap['Costo Compra'] = 0.0
            df_cap['Cancelar'] = False
            df_cap['Observaciones'] = df_por_comprar[c_obs_c].fillna("").astype(str).replace(['nan', 'None'], '').str.strip().values if c_obs_c else ""

            if not modo_consulta and permiso_edicion:
                if 'reset_key_compras' not in st.session_state: st.session_state['reset_key_compras'] = 0

                config_pend = {
                    'Siniestro': st.column_config.TextColumn("Siniestro", disabled=True, width="small"),
                    'Taller': st.column_config.TextColumn("Taller", disabled=True, width="medium"),
                    'Auto': st.column_config.TextColumn("Auto", disabled=True, width="medium"),
                    'Año': st.column_config.TextColumn("Año", disabled=True, width="small"),
                    'VIN / Serie': st.column_config.TextColumn("VIN / Serie", disabled=True, width="medium"),
                    'Pieza': st.column_config.TextColumn("Pieza", disabled=True, width="medium"),
                    'Precio Aut.': st.column_config.NumberColumn("Precio Aut.", format="$ %.2f", disabled=True, width="small"),
                    'Proveedor': st.column_config.SelectboxColumn("🏪 Proveedor", options=lista_opciones_prov, width="medium"),
                    'Costo Compra': st.column_config.NumberColumn("💲 Costo Compra", format="$ %.2f", min_value=0.0, step=0.01, width="small"),
                    'Cancelar': st.column_config.CheckboxColumn("🚫 Can", default=False, width="small"),
                    'Observaciones': st.column_config.TextColumn("📝 Obs.", width="medium")
                }
                df_cap_edit = st.data_editor(
                    df_cap.drop(columns=['_Aseguradora']),
                    column_config=config_pend,
                    hide_index=True,
                    use_container_width=True,
                    key=f"ed_pendientes_compra_rapida_{st.session_state['reset_key_compras']}"
                )
                
                df_cap_edit['_Aseguradora'] = df_cap['_Aseguradora'].values
                df_cap_edit['_Obs_Orig'] = df_cap['Observaciones'].values
                st.session_state['df_cap_edit_temp'] = df_cap_edit

                btn_rapido = st.button("💾 Registrar Compras / Cambios Capturados", type="primary", key="btn_guardar_compras_rapidas")
                if btn_rapido or (btn_guardar and vista_actual == "🛒 Compras"):
                    cond_prov = ~df_cap_edit['Proveedor'].astype(str).str.strip().isin(["", "None", "nan", "NAN"])
                    cond_canc = df_cap_edit['Cancelar'] == True
                    cond_obs = df_cap_edit['Observaciones'].astype(str).str.strip() != df_cap_edit['_Obs_Orig'].astype(str).str.strip()
                    
                    filas_listas = df_cap_edit[cond_prov & (~cond_canc)].copy()
                    filas_uni_upd = df_cap_edit[cond_canc | cond_obs].copy()

                    if filas_listas.empty and filas_uni_upd.empty:
                        st.warning("⚠️ Selecciona un Proveedor, marca Cancelar o edita una Observación antes de guardar.")
                    else:
                        with st.spinner("Sincronizando compras y observaciones en la nube..."):
                            try:
                                doc = init_connection()
                                
                                if not filas_uni_upd.empty:
                                    ws_u_c = doc.worksheet("BD_UNIFICADA")
                                    datos_u_c = ws_u_c.get_all_values()
                                    head_u_c = [str(h).strip() for h in datos_u_c[0]]
                                    id_u_idx = head_u_c.index(buscar_columna_compras(head_u_c, ["PEDIDO / SINIESTRO", "SINIESTRO"], ["SINIESTRO"]))
                                    de_u_idx = head_u_c.index(buscar_columna_compras(head_u_c, ["DESCRIPCIÓN", "DESCRIPCION"], ["DESCRIPCI", "REFACCI"]))
                                    es_u_idx = head_u_c.index(buscar_columna_compras(head_u_c, ["ESTATUS", "STATUS"], ["ESTATUS", "STATUS"]))
                                    co_u_col = buscar_columna_compras(head_u_c, ["COMENTARIOS", "OBSERVACIONES", "COMENTARIO", "OBSERVACION"], ["COMENTARIO", "OBSERVACION"])
                                    co_u_idx = head_u_c.index(co_u_col) if co_u_col else -1
                                    
                                    mapa_filas_u = {}
                                    for idx_r, r_u in enumerate(datos_u_c[1:], start=2):
                                        if len(r_u) > max(id_u_idx, de_u_idx):
                                            mapa_filas_u[normalizar_llave_compra(r_u[id_u_idx], r_u[de_u_idx])] = idx_r
                                            
                                    celdas_u_mod = []
                                    for _, r_up in filas_uni_upd.iterrows():
                                        k_up = normalizar_llave_compra(r_up['Siniestro'], r_up['Pieza'])
                                        if k_up in mapa_filas_u:
                                            fila_gs = mapa_filas_u[k_up]
                                            if r_up['Cancelar']:
                                                celdas_u_mod.append(gspread.Cell(row=fila_gs, col=es_u_idx + 1, value="CANCELADO"))
                                            if co_u_idx >= 0 and str(r_up['Observaciones']).strip() != str(r_up['_Obs_Orig']).strip():
                                                celdas_u_mod.append(gspread.Cell(row=fila_gs, col=co_u_idx + 1, value=str(r_up['Observaciones']).strip()))
                                    if celdas_u_mod:
                                        ws_u_c.update_cells(celdas_u_mod, value_input_option='USER_ENTERED')

                                if not filas_listas.empty:
                                    ws_comp = doc.worksheet("BD_COMPRAS")
                                    datos_comp_all = ws_comp.get_all_values()
                                    headers_comp = [str(h).strip() for h in datos_comp_all[0]]
                                    headers_up = [h.upper() for h in headers_comp]

                                    def idx_col_c(posibles):
                                        for p in posibles:
                                            if p.upper() in headers_up: return headers_up.index(p.upper())
                                        return -1

                                    i_sin = idx_col_c(["SINIESTRO", "PEDIDO / SINIESTRO"])
                                    i_veh = idx_col_c(["VEHÍCULO", "VEHICULO", "AUTO"])
                                    i_tal = idx_col_c(["TALLER", "CDR"])
                                    i_pza = idx_col_c(["DESCRIPCIÓN PIEZA", "DESCRIPCION PIEZA", "PIEZA", "DESCRIPCIÓN"])
                                    i_prv = idx_col_c(["PROVEEDOR"])
                                    i_cos = idx_col_c(["COSTO COMPRA", "COSTO"])
                                    i_fec = idx_col_c(["FECHA COMPRA", "FECHA"])
                                    i_eta = idx_col_c(["TIEMPO ENTREGA (DÍAS)", "TIEMPO ENTREGA (DIAS)", "ETA"])
                                    i_con = idx_col_c(["CONDICIÓN PAGO", "CONDICION PAGO"])
                                    i_dia = idx_col_c(["DÍAS CRÉDITO", "DIAS CREDITO"])
                                    i_pag = idx_col_c(["ESTATUS PAGO", "PAGO"])
                                    i_rec = idx_col_c(["RECIBIDO"])
                                    i_ase = idx_col_c(["ASEGURADORA"])

                                    mapa_existentes_comp = {}
                                    for idx_c_r, r_comp in enumerate(datos_comp_all[1:], start=2):
                                        if i_sin >= 0 and i_pza >= 0 and len(r_comp) > max(i_sin, i_pza):
                                            mapa_existentes_comp[normalizar_llave_compra(r_comp[i_sin], r_comp[i_pza])] = idx_c_r

                                    tz_mx_c = datetime.timezone(datetime.timedelta(hours=-6))
                                    meses_es = {1:'ene', 2:'feb', 3:'mar', 4:'abr', 5:'may', 6:'jun', 7:'jul', 8:'ago', 9:'sep', 10:'oct', 11:'nov', 12:'dic'}
                                    hoy_dt_c = datetime.datetime.now(tz_mx_c)
                                    fecha_hoy_c = f"{hoy_dt_c.day:02d}/{meses_es[hoy_dt_c.month]}/{hoy_dt_c.strftime('%y')}"

                                    nuevas_filas_c = []
                                    celdas_comp_upd = []
                                    for _, r_new in filas_listas.iterrows():
                                        prov_sel = str(r_new['Proveedor']).strip().upper()
                                        costo_sel = round(float(r_new['Costo Compra']), 2) if pd.notna(r_new['Costo Compra']) else 0.0
                                        datos_p_sel = dict_provs.get(prov_sel, {'eta': '0', 'cond': '', 'dias': '0'})
                                        k_check = normalizar_llave_compra(r_new['Siniestro'], r_new['Pieza'])

                                        if k_check in mapa_existentes_comp:
                                            f_row_c = mapa_existentes_comp[k_check]
                                            if i_prv >= 0: celdas_comp_upd.append(gspread.Cell(row=f_row_c, col=i_prv+1, value=prov_sel))
                                            if i_cos >= 0: celdas_comp_upd.append(gspread.Cell(row=f_row_c, col=i_cos+1, value=costo_sel))
                                            if i_fec >= 0: celdas_comp_upd.append(gspread.Cell(row=f_row_c, col=i_fec+1, value=fecha_hoy_c))
                                            if i_eta >= 0: celdas_comp_upd.append(gspread.Cell(row=f_row_c, col=i_eta+1, value=int(datos_p_sel['eta']) if str(datos_p_sel['eta']).isdigit() else 0))
                                            if i_con >= 0: celdas_comp_upd.append(gspread.Cell(row=f_row_c, col=i_con+1, value=datos_p_sel['cond']))
                                            if i_rec >= 0: celdas_comp_upd.append(gspread.Cell(row=f_row_c, col=i_rec+1, value="NO"))
                                        else:
                                            fila_c = [""] * len(headers_comp)
                                            partes_v = [str(r_new['Auto']).strip(), str(r_new['Año']).strip(), str(r_new['VIN / Serie']).strip()]
                                            veh_limpio = " | ".join([p for p in partes_v if p and p not in ['NAN', 'NONE']])
                                            
                                            if i_sin >= 0: fila_c[i_sin] = str(r_new['Siniestro']).strip()
                                            if i_veh >= 0: fila_c[i_veh] = veh_limpio
                                            if i_tal >= 0: fila_c[i_tal] = str(r_new['Taller']).strip()
                                            if i_pza >= 0: fila_c[i_pza] = str(r_new['Pieza']).strip()
                                            if i_prv >= 0: fila_c[i_prv] = prov_sel
                                            if i_cos >= 0: fila_c[i_cos] = costo_sel
                                            if i_fec >= 0: fila_c[i_fec] = fecha_hoy_c
                                            if i_eta >= 0: fila_c[i_eta] = int(datos_p_sel['eta']) if str(datos_p_sel['eta']).isdigit() else 0
                                            if i_con >= 0: fila_c[i_con] = datos_p_sel['cond']
                                            if i_dia >= 0: fila_c[i_dia] = int(datos_p_sel['dias']) if str(datos_p_sel['dias']).isdigit() else 0
                                            if i_pag >= 0: fila_c[i_pag] = "Pendiente"
                                            if i_rec >= 0: fila_c[i_rec] = "NO"
                                            if i_ase >= 0: fila_c[i_ase] = str(r_new['_Aseguradora']).strip()

                                            nuevas_filas_c.append(fila_c)

                                    if celdas_comp_upd:
                                        ws_comp.update_cells(celdas_comp_upd, value_input_option='USER_ENTERED')
                                    if nuevas_filas_c:
                                        ws_comp.append_rows(nuevas_filas_c, value_input_option='USER_ENTERED', table_range="A1")

                                st.session_state['reset_key_compras'] += 1
                                st.cache_data.clear()
                                st.success("✅ ¡Cambios y compras actualizados exitosamente!")
                                time.sleep(0.8)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error al registrar compras: {e}")
            else:
                st.dataframe(df_cap.drop(columns=['Proveedor', 'Costo Compra', 'Cancelar', '_Aseguradora']), hide_index=True, use_container_width=True)
        else:
            st.success("🎉 ¡Excelente! Todas las piezas en procesamiento ya tienen su compra registrada.")

    # ==========================================================================
    # PESTAÑA 2: PRÓXIMAS LLEGADAS (LÍNEA DE TIEMPO Y SEGUIMIENTO)
    # ==========================================================================
    with tab_comp_lleg:
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
                
                if not df_completo.empty:
                    c_id_u = buscar_columna_compras(df_completo, ["PEDIDO / SINIESTRO", "SINIESTRO"], ["SINIESTRO"])
                    c_de_u = buscar_columna_compras(df_completo, ["DESCRIPCIÓN", "DESCRIPCION"], ["DESCRIPCI", "REFACCI"])
                    c_es_u = buscar_columna_compras(df_completo, ["ESTATUS", "STATUS"], ["ESTATUS", "STATUS"])
                    c_re_u = buscar_columna_compras(df_completo, ["REMISION", "REMISIÓN", "FOLIO REMISION"], ["REMISION", "REMISIÓN"])
                    c_gu_u = buscar_columna_compras(df_completo, ["GUIA", "GUÍA", "NO. GUIA"], ["GUIA", "GUÍA"])
                    
                    llaves_finalizadas = set()
                    llaves_con_remision = set()
                    for _, ru in df_completo.iterrows():
                        k_u = normalizar_llave_compra(ru.get(c_id_u, ''), ru.get(c_de_u, ''))
                        est_u = str(ru.get(c_es_u, '')).strip().upper() if c_es_u else ''
                        rem_u = str(ru.get(c_re_u, '')).strip() if c_re_u else ''
                        gui_u = str(ru.get(c_gu_u, '')).strip() if c_gu_u else ''
                        if est_u in ['ENTREGADO', 'RECIBIDO', 'FACTURADO', 'CANCELADO', 'PÉRDIDA TOTAL', 'PAGO DE DAÑOS'] or (gui_u not in ['', 'nan', 'None', 'NAN']):
                            llaves_finalizadas.add(k_u)
                        if rem_u not in ['', 'nan', 'None', 'NAN'] or est_u == 'EN TRANSITO':
                            llaves_con_remision.add(k_u)
                    
                    df_c['_llave_c'] = df_c.apply(lambda r: normalizar_llave_compra(r.get('Siniestro', ''), r.get('Descripción Pieza', '')), axis=1)
                    es_inv = df_c['Proveedor'].astype(str).str.strip().str.upper() == 'INVENTARIO'
                    df_c.loc[df_c['_llave_c'].isin(llaves_finalizadas) | (es_inv & df_c['_llave_c'].isin(llaves_con_remision)), 'Recibido_Bool'] = True
                else:
                    df_c['_llave_c'] = df_c.apply(lambda r: normalizar_llave_compra(r.get('Siniestro', ''), r.get('Descripción Pieza', '')), axis=1)
                    
                if not modo_consulta: df_c = df_c[df_c['Recibido_Bool'] == False].copy()
                if df_c.empty: st.success("✅ Todo está al día. No hay pedidos pendientes de recepción con estos filtros.")
                else:
                    df_c['Cancelar Compra'] = False
                    df_c['Observaciones'] = df_c['_llave_c'].map(dict_obs_global).fillna("")
                    if 'Condición Pago' in df_c.columns:
                        df_c['Condición Pago'] = df_c['Condición Pago'].apply(normalizar_pago)

                    if not df_proveedores.empty:
                        for idx, r_c in df_c.iterrows():
                            prov_actual = str(r_c.get('Proveedor', '')).strip().upper()
                            if prov_actual in dict_provs:
                                datos_p = dict_provs[prov_actual]
                                eta_actual = pd.to_numeric(r_c.get('Tiempo Entrega (Días)', 0), errors='coerce')
                                if pd.isna(eta_actual) or eta_actual == 0: df_c.at[idx, 'Tiempo Entrega (Días)'] = datos_p['eta']
                                cond_actual = normalizar_pago(r_c.get('Condición Pago', ''))
                                if not cond_actual: df_c.at[idx, 'Condición Pago'] = datos_p['cond']
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
                        estatus_p = str(row.get('Estatus Pago', '')).strip().upper()
                        if estatus_p == 'PAGADO': return '✅ Liquidado'
                            
                        cond = normalizar_pago(row.get('Condición Pago', ''))
                        dias_cr = pd.to_numeric(row.get('Días Crédito', 0), errors='coerce')
                        if pd.isna(dias_cr): dias_cr = 0
                        
                        if cond == 'Pago Anticipado': return '🔴 Pagar p/ pedir'
                        elif cond == 'Anticipo': return '🟠 Dar Anticipo / Liquidar'
                        elif cond == 'Contra Entrega': return '💵 Pagar al Recibir'
                        elif cond == 'Pago en Plataforma': return '🔵 Pagado en Plataforma'
                        elif cond == 'Crédito':
                            if pd.notna(row['Fecha_Compra_Dt']):
                                vencimiento = row['Fecha_Compra_Dt'] + pd.to_timedelta(dias_cr, unit='d')
                                dias_restantes = (vencimiento - hoy_dt_alert).days
                                f_venc = vencimiento.strftime('%d/%b')
                                if dias_restantes < 0: return f"❌ VENCIDO ({f_venc})"
                                elif dias_restantes <= 3: return f"🟠 Vence pronto: {f_venc}"
                                else: return f"🟢 En tiempo: {f_venc}"
                            else: return f"🟡 Crédito ({int(dias_cr)} días)"
                        return '⚪ Sin Condición Definida'
                        
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
                    cols_mostrar = ['Siniestro', 'Taller', 'Vehículo_Corto', 'Descripción Pieza', 'Proveedor', 'Costo Compra', 'ETA (Días)', 'Llegada Est.', 'Condición Pago', 'Días Crédito', 'Estatus Pago', 'Recibido_Bool', 'Cancelar Compra', 'Alerta Financiera', 'Observaciones']
                    df_disp = df_c[[c for c in cols_mostrar if c in df_c.columns]].copy()
                    df_disp.rename(columns={'Vehículo_Corto': 'Auto', 'Taller': 'CDR', 'Descripción Pieza': 'Pieza', 'Costo Compra': 'Costo', 'ETA (Días)': 'ETA', 'Recibido_Bool': 'Recibido', 'Estatus Pago': 'Pago', 'Condición Pago': 'Cond. Pago', 'Días Crédito': 'Días Cr.'}, inplace=True)
                
                    if not modo_consulta and permiso_edicion:
                        opciones_pago = ["", "Pago Anticipado", "Anticipo", "Contra Entrega", "Crédito", "Pago en Plataforma"]
                        config_c = {
                            'Siniestro': st.column_config.TextColumn("Siniestro", disabled=True, width="small"), 
                            'CDR': st.column_config.TextColumn("CDR", disabled=True, width="medium"), 
                            'Auto': st.column_config.TextColumn("Auto", disabled=True, width="medium"),
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
                            'Alerta Financiera': st.column_config.TextColumn("Alerta Financiera", disabled=True, width="medium"),
                            'Observaciones': st.column_config.TextColumn("📝 Obs.", width="medium")
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
    # PESTAÑA 1: TALLERES (CDR) - FUSIONADO Y EDITABLE
    # ==========================
    with tab_talleres:
        col_taller_cat = next((c for c in df_catalogo.columns if "TALLER" in str(c).upper()), None)
        col_dir_cat = next((c for c in df_catalogo.columns if "DIRECCI" in str(c).upper()), None)
        col_tel_cat = next((c for c in df_catalogo.columns if "TELEFONO" in str(c).upper() or "TEL" in str(c).upper()), None)
        col_ciudad_cat = next((c for c in df_catalogo.columns if "CIUDAD" in str(c).upper()), None)
        col_estado_cat = next((c for c in df_catalogo.columns if "ESTADO" in str(c).upper()), None)
        
        df_cat_work = df_catalogo.copy()
        # Guardamos la fila real de Sheets para poder actualizar
        df_cat_work['_GS_Row'] = df_cat_work.index + 2
        
        busqueda_taller = st.text_input("🔍 Buscar Taller por nombre, ciudad o estado...")
        df_cat_filtrado = df_cat_work.copy()
        
        if busqueda_taller:
            mask = df_cat_filtrado.apply(lambda row: row.astype(str).str.contains(busqueda_taller, case=False, na=False).any(), axis=1)
            df_cat_filtrado = df_cat_filtrado[mask].copy()

        cols_vista_cat = [c for c in df_cat_filtrado.columns if "Unnamed" not in str(c) and c != '_GS_Row']
        
        if cols_vista_cat:
            if not modo_consulta and permiso_edicion:
                st.caption("💡 Edita directamente en la tabla (Contacto, Teléfono, WhatsApp, etc.) y presiona **Guardar Cambios en Talleres**.")
                
                cfg_cat_ed = {}
                if col_taller_cat: cfg_cat_ed[col_taller_cat] = st.column_config.TextColumn("Taller", disabled=True) # El nombre del taller suele ser la llave, mejor no editarlo aquí
                
                df_cat_editado = st.data_editor(
                    df_cat_filtrado[cols_vista_cat],
                    column_config=cfg_cat_ed,
                    hide_index=True,
                    use_container_width=True,
                    key="editor_directorio_talleres"
                )
                
                if st.button("💾 Guardar Cambios en Talleres", type="primary", key="btn_save_dir_talleres"):
                    with st.spinner("Actualizando catálogo de talleres en la nube..."):
                        try:
                            doc = init_connection()
                            try: 
                                ws_cat = doc.worksheet("BD_TALLERES")
                            except:
                                ws_cat = doc.worksheet("Catálogo")
                                
                            headers_t = [str(h).strip() for h in ws_cat.row_values(1)]
                            celdas_tall_update = []

                            for idx_fila in df_cat_editado.index:
                                gs_row = int(df_cat_filtrado.loc[idx_fila, '_GS_Row'])
                                for col_name in cols_vista_cat:
                                    val_orig = str(df_cat_filtrado.loc[idx_fila, col_name]).strip()
                                    val_nuevo = str(df_cat_editado.loc[idx_fila, col_name]).strip()
                                    if val_nuevo in ['nan', 'None']: val_nuevo = ""
                                    if val_orig in ['nan', 'None']: val_orig = ""
                                    
                                    if val_orig != val_nuevo and col_name in headers_t:
                                        col_idx_gs = headers_t.index(col_name) + 1
                                        celdas_tall_update.append(gspread.Cell(row=gs_row, col=col_idx_gs, value=val_nuevo))

                            if celdas_tall_update:
                                ws_cat.update_cells(celdas_tall_update, value_input_option='USER_ENTERED')
                                st.success(f"✅ Se actualizaron {len(celdas_tall_update)} dato(s) en la base de Talleres.")
                                st.cache_data.clear()
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.info("No se detectaron cambios por guardar.")
                        except Exception as e:
                            st.error(f"Error actualizando talleres: {e}")
            else:
                st.dataframe(df_cat_filtrado[cols_vista_cat], hide_index=True, use_container_width=True)

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
    # PESTAÑA 2: PROVEEDORES (EDITABLE)
    # ==========================
    with tab_proveedores:
        if not df_proveedores.empty:
            def norm_pago_dir(val):
                v = str(val).strip().upper()
                if v in ['', 'NONE', 'NAN']: return ''
                if 'PLAT' in v: return 'Pago en Plataforma'
                if 'CONTRA' in v: return 'Contra Entrega'
                if 'CRED' in v or 'CRÉD' in v: return 'Crédito'
                if 'ANTICIPADO' in v or 'PREV' in v or 'CONTADO' in v: return 'Pago Anticipado'
                if 'ANTIC' in v: return 'Anticipo'
                return str(val).strip()

            df_prov_work = df_proveedores.copy()
            # Guardamos el número exacto de fila de Google Sheets (+2 por encabezado e índice base 0)
            df_prov_work['_GS_Row'] = df_prov_work.index + 2
            if 'Condición Pago' in df_prov_work.columns:
                df_prov_work['Condición Pago'] = df_prov_work['Condición Pago'].apply(norm_pago_dir)

            busqueda_prov = st.text_input("🔍 Buscar Proveedor por nombre, marca o especialidad...")
            df_prov_filtrado = df_prov_work.copy()
            
            if busqueda_prov:
                mask = df_prov_filtrado.apply(lambda row: row.astype(str).str.contains(busqueda_prov, case=False, na=False).any(), axis=1)
                df_prov_filtrado = df_prov_filtrado[mask].copy()

            cols_prov = ['Proveedor', 'Sucursal', 'Marcas Especialidad', 'Tiempo de Entrega', 'Días Crédito', 'Condición Pago', 'Teléfono', 'Dirección']
            cols_vista_prov = [c for c in cols_prov if c in df_prov_filtrado.columns]

            if not modo_consulta and permiso_edicion:
                st.caption("💡 Edita cualquier celda directamente (Condición de Pago, Días Crédito, Teléfono, etc.) y presiona **Guardar Cambios en Proveedores**.")
                opciones_cond_dir = ["", "Pago Anticipado", "Anticipo", "Contra Entrega", "Crédito", "Pago en Plataforma"]
                
                cfg_prov_ed = {
                    'Proveedor': st.column_config.TextColumn("Proveedor", width="medium"),
                    'Sucursal': st.column_config.TextColumn("Sucursal", width="small"),
                    'Marcas Especialidad': st.column_config.TextColumn("Especialidad", width="medium"),
                    'Tiempo de Entrega': st.column_config.NumberColumn("ETA (Días)", min_value=0, step=1, width="small"),
                    'Días Crédito': st.column_config.NumberColumn("Días Crédito", min_value=0, step=1, width="small"),
                    'Condición Pago': st.column_config.SelectboxColumn("Condición Pago", options=opciones_cond_dir, width="medium"),
                    'Teléfono': st.column_config.TextColumn("Teléfono", width="small"),
                    'Dirección': st.column_config.TextColumn("Dirección", width="large")
                }
                
                df_prov_editado = st.data_editor(
                    df_prov_filtrado[cols_vista_prov],
                    column_config=cfg_prov_ed,
                    hide_index=True,
                    use_container_width=True,
                    key="editor_directorio_proveedores"
                )

                if st.button("💾 Guardar Cambios en Proveedores", type="primary", key="btn_save_dir_prov"):
                    with st.spinner("Actualizando catálogo de proveedores en la nube..."):
                        try:
                            doc = init_connection()
                            ws_prov = doc.worksheet("BD_PROVEEDORES")
                            headers_p = [str(h).strip() for h in ws_prov.row_values(1)]
                            celdas_prov_update = []

                            for idx_fila in df_prov_editado.index:
                                gs_row = int(df_prov_filtrado.loc[idx_fila, '_GS_Row'])
                                for col_name in cols_vista_prov:
                                    val_orig = str(df_prov_filtrado.loc[idx_fila, col_name]).strip()
                                    val_nuevo = str(df_prov_editado.loc[idx_fila, col_name]).strip()
                                    if val_nuevo in ['nan', 'None']: val_nuevo = ""
                                    if val_orig in ['nan', 'None']: val_orig = ""
                                    
                                    if val_orig != val_nuevo and col_name in headers_p:
                                        col_idx_gs = headers_p.index(col_name) + 1
                                        celdas_prov_update.append(gspread.Cell(row=gs_row, col=col_idx_gs, value=val_nuevo))

                            if celdas_prov_update:
                                ws_prov.update_cells(celdas_prov_update, value_input_option='USER_ENTERED')
                                st.success(f"✅ Se actualizaron {len(celdas_prov_update)} dato(s) en BD_PROVEEDORES.")
                                st.cache_data.clear()
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.info("No se detectaron cambios por guardar.")
                        except Exception as e:
                            st.error(f"Error actualizando proveedores: {e}")
            else:
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
                        nuevo_tiempo = col5.number_input("Tiempo de Entrega (Días)", min_value=0, value=0, step=1)
                        nueva_cond_pago = col6.selectbox("Condición de Pago", ["Contra Entrega", "Pago Anticipado", "Anticipo", "Crédito", "Pago en Plataforma"])
                        nuevos_dias_c = col7.number_input("Días Crédito", min_value=0, value=0, step=1)
                        
                        if st.form_submit_button("Guardar Proveedor", type="primary"):
                            if nuevo_prov.strip():
                                with st.spinner("Guardando proveedor en la base de datos..."):
                                    try:
                                        doc = init_connection()
                                        ws_prov = doc.worksheet("BD_PROVEEDORES")
                                        headers = [str(h).strip() for h in ws_prov.row_values(1)]
                                        fila_nueva = [""] * max(len(headers), 10)
                                        
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
                                        
                                        ws_prov.append_row(fila_nueva[:len(headers)] if headers else fila_nueva, value_input_option='USER_ENTERED')
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
    st.markdown("### 📝 Centro de Remisiones y Envíos")
    
    tab_rem_log, tab_rem_libre = st.tabs(["📑 Remisión Logística (Aseguradoras)", "➕ Remisión Libre (Venta Directa)"])
    
    # =========================================================================
    # PESTAÑA 2: REMISIÓN LIBRE (VENTA DIRECTA)
    # =========================================================================
    with tab_rem_libre:
        st.markdown("#### ➕ Nueva Remisión Libre (Folios PMR-V)")
        st.caption("Genera una remisión independiente para clientes externos o ventas casuales (No afecta a BD_UNIFICADA).")
        
        with st.form("form_remision_libre", clear_on_submit=True):
            col_c1, col_c2 = st.columns([2, 1])
            cliente_libre = col_c1.text_input("Nombre del Cliente / Taller Externo *")
            fecha_libre = col_c2.date_input("Fecha de Remisión", value="today", format="DD/MM/YYYY")
            
            dir_libre = st.text_input("Dirección de Entrega * (Requerida para la ruta y la remisión)")
            
            col_v1, col_v2 = st.columns(2)
            vehiculo_libre = col_v1.text_input("Vehículo (Opcional, Ej. Nissan Versa 2020)")
            siniestro_libre = col_v2.text_input("Referencia / Siniestro (Opcional)", value="S/N")
            
            st.markdown("**📦 Artículos a Vender**")
            df_articulos_base = pd.DataFrame([{"Cant": 1, "Descripción": "", "Precio Unitario": 0.0}] * 4)
            ed_articulos = st.data_editor(
                df_articulos_base,
                num_rows="dynamic",
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Cant": st.column_config.NumberColumn("Cant", min_value=1, step=1, width="small"),
                    "Descripción": st.column_config.TextColumn("Descripción del Artículo", width="large"),
                    "Precio Unitario": st.column_config.NumberColumn("Precio ($)", format="%.2f", min_value=0.0, step=10.0, width="medium")
                },
                key="ed_articulos_libre"
            )
            
            despachar_ruta = st.checkbox("🚚 Despachar en ruta local hoy (Agrega el destino a Operación del Día para que el chofer lo entregue)", value=False)
            btn_libre = st.form_submit_button("📄 Generar y Descargar Remisión", type="primary")
            
            if btn_libre:
                if not cliente_libre.strip() or not dir_libre.strip():
                    st.error("⚠️ El Nombre del Cliente y la Dirección son obligatorios.")
                else:
                    articulos_validos = []
                    for _, r_art in ed_articulos.iterrows():
                        if str(r_art.get("Descripción", "")).strip():
                            articulos_validos.append({
                                'cant': str(r_art.get("Cant", "1")),
                                'desc': str(r_art.get("Descripción", "")).strip(),
                                'precio': float(r_art.get("Precio Unitario", 0.0))
                            })
                    
                    if not articulos_validos:
                        st.error("⚠️ Debes capturar al menos un artículo válido.")
                    else:
                        folio_libre = f"PMR-V-{datetime.datetime.now().strftime('%y%m%d%H%M')}"
                        usuario_print = st.session_state.get('usuario_actual', 'Sistema')
                        fecha_header = fecha_libre.strftime('%d/%b/%Y').upper()
                        
                        pdf = FPDF(orientation='L', unit='mm', format='A4')
                        pdf.set_auto_page_break(auto=False, margin=0); pdf.add_page()
                        
                        def limpiar_texto(txt): return str(txt).encode('latin-1', 'replace').decode('latin-1')

                        def dibujar_bloque_remision_libre(x_offset):
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
                            pdf.set_text_color(200, 0, 0); pdf.set_font("Arial", 'B', 10); pdf.set_xy(x_offset + 105, y_offset + 5); pdf.cell(30, 6, limpiar_texto(folio_libre), border=1, align='C')
                            pdf.set_text_color(100, 100, 100); pdf.set_font("Arial", '', 7); pdf.set_xy(x_offset + 105, y_offset + 12); pdf.cell(30, 4, f"FECHA: {fecha_header}", align='C')
                            
                            y_datos = y_offset + 22; pdf.set_fill_color(220, 220, 220); pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", 'B', 7)
                            pdf.set_xy(x_offset, y_datos); pdf.cell(20, 5, "CLIENTE", border=1, fill=True); pdf.set_font("Arial", '', 7); pdf.cell(115, 5, limpiar_texto(f" {cliente_libre}")[:75], border=1)
                            y_datos += 5; pdf.set_xy(x_offset, y_datos); pdf.set_font("Arial", 'B', 7); pdf.cell(20, 5, "DIRECCION", border=1, fill=True); pdf.set_font("Arial", '', 7); pdf.cell(115, 5, limpiar_texto(f" {dir_libre}")[:85], border=1)
                            y_datos += 5; pdf.set_xy(x_offset, y_datos); pdf.set_font("Arial", 'B', 7); pdf.cell(20, 5, "REFERENCIA", border=1, fill=True); pdf.set_font("Arial", 'B', 8); pdf.cell(45, 5, limpiar_texto(f" {siniestro_libre}"), border=1)
                            pdf.set_font("Arial", 'B', 7); pdf.cell(20, 5, "VEHICULO", border=1, fill=True); pdf.set_font("Arial", '', 7); pdf.cell(50, 5, limpiar_texto(f" {vehiculo_libre}")[:35], border=1)

                            y_tabla = y_datos + 10; pdf.set_xy(x_offset, y_tabla); pdf.set_fill_color(0, 0, 0); pdf.set_text_color(255, 255, 255); pdf.set_font("Arial", 'B', 7)
                            pdf.cell(12, 6, "CANT", border=1, fill=True, align='C'); pdf.cell(103, 6, "DESCRIPCION", border=1, fill=True, align='C'); pdf.cell(20, 6, "PRECIO", border=1, fill=True, align='C')

                            y_item = y_tabla + 6; pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", '', 7)
                            total_venta = 0.0
                            for item in articulos_validos:
                                pdf.set_xy(x_offset, y_item); 
                                pdf.cell(12, 5, limpiar_texto(item['cant']), border=1, align='C'); 
                                pdf.cell(103, 5, limpiar_texto(item['desc'])[:70], border=1)
                                if item['precio'] > 0:
                                    pdf.cell(20, 5, f"${item['precio']:,.2f}", border=1, align='R')
                                    total_venta += (float(item['cant']) * item['precio'])
                                else:
                                    pdf.cell(20, 5, "", border=1, align='C')
                                y_item += 5
                                
                            if total_venta > 0:
                                pdf.set_xy(x_offset + 115, y_item)
                                pdf.set_font("Arial", 'B', 7)
                                pdf.cell(20, 5, f"${total_venta:,.2f}", border=1, align='R')

                            pdf.set_xy(x_offset, 192); pdf.set_font("Arial", 'I', 6); pdf.set_text_color(120, 120, 120); pdf.cell(135, 4, f"Generado por: {usuario_print} (Venta Externa)", align='R')

                        dibujar_bloque_remision_libre(10)
                        pdf.set_draw_color(180, 180, 180); pdf.line(148.5, 10, 148.5, 200); pdf.set_draw_color(0, 0, 0)
                        dibujar_bloque_remision_libre(152)

                        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                            pdf.output(tmp.name)
                            nombre_archivo = f"Remision_Libre_{folio_libre}.pdf"
                            with open(tmp.name, "rb") as f: pdf_bytes = f.read()
                            
                        st.session_state['pdfs_list'] = [{'folio': folio_libre, 'siniestro': siniestro_libre, 'bytes': pdf_bytes, 'nombre': nombre_archivo}]
                        
                        if despachar_ruta:
                            try:
                                doc = init_connection()
                                ws_r = doc.worksheet("BD_RUTAS")
                                id_ruta = f"RT-{datetime.datetime.now().strftime('%y%m%d-%H%M')}-VEN"
                                fecha_hoy_r = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
                                desc_resumen = " + ".join([item['desc'] for item in articulos_validos])
                                nota_final = f"Venta Directa: Cobrar ${sum([float(i['cant']) * i['precio'] for i in articulos_validos]):,.2f}" if sum([i['precio'] for i in articulos_validos]) > 0 else "Venta Directa / Entrega Manual"
                                
                                fila_ruta = [id_ruta, fecha_hoy_r, "ENTREGA", cliente_libre.upper(), dir_libre.upper(), str(vehiculo_libre).upper(), "S/D", desc_resumen.upper(), str(siniestro_libre).upper(), nota_final, "PENDIENTE"]
                                ws_r.append_row(fila_ruta, value_input_option='USER_ENTERED')
                                st.success("✅ Visita agregada a la ruta del operador exitosamente.")
                            except Exception as e:
                                st.error(f"⚠️ Se generó el PDF pero hubo un error enviando a la ruta: {e}")
                        st.rerun()

    # =========================================================================
    # PESTAÑA 1: REMISIÓN LOGÍSTICA (ASEGURADORAS)
    # =========================================================================
    with tab_rem_log:
        st.markdown("#### 📝 Envíos a Talleres y Reimpresiones")
        
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
            estatus_permitidos = ["EN PROCESAMIENTO"]
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
                for aseguradora in ["MULTI", "GNP", "OTRA"]:
                    df_aseg = df_filtrado_rem[df_filtrado_rem['Aseg_Grupo'] == aseguradora]
                    if not df_aseg.empty:
                        icono = "🔵" if aseguradora == "MULTI" else ("🟠" if aseguradora == "GNP" else "⚪")
                        nombre_aseg = "MULTIASISTENCIAS" if aseguradora == "MULTI" else aseguradora
                        
                        with st.expander(f"{icono} {nombre_aseg} | {len(df_aseg)} Partida(s) lista(s) para remisionar", expanded=False):
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
                                            for idx_pieza, row_p in df_sin_rem.reset_index().iterrows():
                                                desc_val = str(row_p.get(col_desc_r, ''))
                                                if st.checkbox(desc_val, value=True, key=f"chk_{aseguradora}_{siniestro_v}_{idx_pieza}_{desc_val}"):
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

        st.markdown("---")
        st.markdown("### 🖨️ Bóveda de Reimpresión")
        st.info("Busca por Número de Siniestro para ver y reimprimir todas las remisiones asociadas a él.")
        
        if col_remision_univ and not df_completo.empty:
            df_con_folio = df_completo[df_completo[col_remision_univ].astype(str).str.upper().str.contains("PMR", na=False)].copy()
            
            if not df_con_folio.empty:
                col_id_reimp = buscar_col_local(df_con_folio, ["PEDIDO / SINIESTRO", "SINIESTRO"], ["SINIESTRO"])
                col_taller_reimp = buscar_col_local(df_con_folio, ["TALLER", "CDR"], ["TALLER"])
                col_desc_reimp = buscar_col_local(df_con_folio, ["DESCRIPCIÓN", "DESCRIPCION"], ["DESCRIPCI", "REFACCI"])
                col_cant_reimp = buscar_col_local(df_con_folio, ["CANTIDAD", "CANT"], ["CANTIDAD", "CANT"])
                col_marca_reimp = buscar_col_local(df_con_folio, ["MARCA"], ["MARCA"])
                col_modelo_reimp = buscar_col_local(df_con_folio, ["MODELO"], ["MODELO"])
                
                col_search, _ = st.columns([1, 1])
                with col_search:
                    lista_siniestros_con_folio = sorted(list(df_con_folio[col_id_reimp].dropna().astype(str).unique()))
                    siniestro_a_reimprimir = st.selectbox("🔍 Buscar por Número de Siniestro:", [""] + lista_siniestros_con_folio, help="Selecciona el siniestro para ver sus remisiones guardadas.")
                    
                if siniestro_a_reimprimir:
                    df_sin_reimp = df_con_folio[df_con_folio[col_id_reimp].astype(str).str.strip() == siniestro_a_reimprimir].copy()
                    
                    if not df_sin_reimp.empty:
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
                                        
                                        col_envio = buscar_col_local(df_folio, ["FECHA ENVIO", "FECHA ENVÍO"], ["FECHA ENV"])
                                        fecha_header = str(fila_0.get(col_envio, '')).strip() if col_envio else ''
                                        if not fecha_header or fecha_header in ['nan', 'None']: 
                                            tz_mx = datetime.timezone(datetime.timedelta(hours=-6))
                                            fecha_header = datetime.datetime.now(tz_mx).strftime('%d/%b/%Y').upper()
                                        else:
                                            fecha_header = fecha_header.upper()
                                            
                                        firma_digital = f"Reimpresión solicitada por: {st.session_state.get('usuario_actual', 'Sistema')}"
                                        
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
    st.markdown("## 🚚 Despachador de Rutas (Logística Local - Nuevo León)")
    st.info("Selecciona los destinos que visitará el operador hoy. Desmarca las piezas que NO deseas enviar en este viaje.")
    
       
    # --- FUNCIÓN MAESTRA DE DESPACHO ---
    def despachar_a_bd_rutas(df_seleccion, tipo_operacion, notas_general=""):
        if df_seleccion.empty: return False
        try:
            filas_insertar = []
            fecha_hoy = datetime.datetime.now(tz_mx).strftime("%d/%m/%Y %H:%M")
            
            # 1. Determinar agrupador estricto según la operación
            if tipo_operacion.lower() in ['compra', 'cotizacion']:
                col_agrupar = 'Proveedor' if 'Proveedor' in df_seleccion.columns else df_seleccion.columns[0]
            else:
                col_agrupar = 'Taller' if 'Taller' in df_seleccion.columns else df_seleccion.columns[0]
            
            # 2. Buscar el diccionario de direcciones y ESTADOS (Para saber si es local o foráneo)
            dict_direcciones = {}
            dict_estado_talleres = {}
            
            if not df_catalogo.empty:
                c_tall = next((c for c in df_catalogo.columns if 'TALLER' in str(c).upper()), None)
                c_dir = next((c for c in df_catalogo.columns if 'DIRECC' in str(c).upper()), None)
                c_est = next((c for c in df_catalogo.columns if 'ESTADO' in str(c).upper()), None)
                if c_tall and c_dir: dict_direcciones.update(dict(zip(df_catalogo[c_tall].astype(str).str.strip().str.upper(), df_catalogo[c_dir])))
                if c_tall and c_est: dict_estado_talleres = dict(zip(df_catalogo[c_tall].astype(str).str.strip().str.upper(), df_catalogo[c_est].astype(str).str.strip().str.upper()))
                
            if not df_proveedores.empty:
                c_prov = next((c for c in df_proveedores.columns if 'PROVEEDOR' in str(c).upper() or 'NOMBRE' in str(c).upper()), None)
                c_suc_p = next((c for c in df_proveedores.columns if 'SUCURSAL' in str(c).upper()), None)
                c_dir_p = next((c for c in df_proveedores.columns if 'DIRECC' in str(c).upper()), None)
                if c_prov and c_dir_p:
                    for _, rp_d in df_proveedores.iterrows():
                        p_nom = str(rp_d.get(c_prov, '')).strip().upper()
                        s_nom = str(rp_d.get(c_suc_p, '')).strip().upper() if c_suc_p else ""
                        d_val = str(rp_d.get(c_dir_p, '')).strip()
                        if p_nom and d_val:
                            dict_direcciones[p_nom] = d_val
                            if s_nom and s_nom != 'NAN':
                                dict_direcciones[f"{p_nom} - {s_nom}"] = d_val
            if 'Direccion_Manual' in df_seleccion.columns:
                for _, r_dm in df_seleccion.iterrows():
                    if str(r_dm.get('Direccion_Manual', '')).strip():
                        dict_direcciones[str(r_dm.get(col_agrupar, '')).strip().upper()] = str(r_dm.get('Direccion_Manual', '')).strip()

            for lugar, grupo in df_seleccion.groupby(col_agrupar):
                lugar_str = str(lugar).strip()
                id_ruta = f"RT-{datetime.datetime.now(tz_mx).strftime('%y%m%d-%H%M')}-{lugar_str[:3].upper()}"
                direccion_calculada = dict_direcciones.get(lugar_str.upper(), "Ver Google Maps / Sin Dirección Registrada")
                
                vehiculo_calculado = str(grupo['Vehiculo_Info'].iloc[0]) if 'Vehiculo_Info' in grupo.columns else "S/D"
                vin_calculado = str(grupo.get(col_vin, "S/D").iloc[0]) if col_vin and col_vin in grupo.columns else "S/D"
                
                for _, row in grupo.iterrows():
                    siniestro = str(row.get(col_id, row.get('Pedido / Siniestro', ''))) if col_id else ''
                    pieza = str(row.get(col_desc, row.get('Descrip.', ''))) if col_desc else ''
                    
                    # 3. LIGAR DESTINO FINAL (LOCAL VS FORÁNEO) EN NOTAS
                    nota_final = notas_general
                    if tipo_operacion.lower() == 'compra':
                        taller_destino = str(row.get('Taller', '')).strip()
                        if taller_destino and taller_destino.lower() != 'nan':
                            estado_taller = dict_estado_talleres.get(taller_destino.upper(), "")
                            
                            # Lógica para detectar estado local (Nuevo León)
                            es_local = False
                            estado_str = str(estado_taller).upper().replace("Ó", "O")
                            if "NUEVO LEON" in estado_str or "NL" in estado_str or "N.L" in estado_str:
                                es_local = True
                            
                            if es_local:
                                nota_final = f"Llevar a: {taller_destino} | {notas_general}".strip(" |")
                            else:
                                nota_final = f"Dejar en Base (Foráneo: {taller_destino}) | {notas_general}".strip(" |")

                    # Estructura obligatoria para BD_RUTAS
                    fila = [id_ruta, fecha_hoy, tipo_operacion.upper(), lugar_str, direccion_calculada, vehiculo_calculado, vin_calculado, pieza, siniestro, nota_final, "PENDIENTE"]
                    filas_insertar.append(fila)
            
            if filas_insertar:
                ws_r = doc.worksheet("BD_RUTAS")
                existentes_r = ws_r.get_all_values()
                if len(existentes_r) == 0: 
                    ws_r.append_row(["ID_RUTA", "FECHA", "TIPO_OPERACION", "LUGAR", "DIRECCION", "VEHICULO", "VIN", "PIEZA", "SINIESTRO", "NOTA", "ESTATUS"])
                    existentes_r = []
                
                hoy_prefijo = datetime.datetime.now(tz_mx).strftime("%d/%m/%Y")
                llaves_hoy_r = set()
                for r_ex in existentes_r[1:]:
                    if len(r_ex) >= 11 and hoy_prefijo in str(r_ex[1]) and str(r_ex[10]).strip().upper() == "PENDIENTE":
                        # Llave: TIPO_OPERACION + LUGAR + PIEZA + SINIESTRO
                        llaves_hoy_r.add(f"{str(r_ex[2]).strip().upper()}_{str(r_ex[3]).strip().upper()}_{str(r_ex[7]).strip().upper()}_{str(r_ex[8]).strip().upper()}")
                
                filas_unicas = []
                for f_ins in filas_insertar:
                    k_ins = f"{str(f_ins[2]).strip().upper()}_{str(f_ins[3]).strip().upper()}_{str(f_ins[7]).strip().upper()}_{str(f_ins[8]).strip().upper()}"
                    if k_ins not in llaves_hoy_r:
                        filas_unicas.append(f_ins)
                        llaves_hoy_r.add(k_ins)
                
                if filas_unicas:
                    ws_r.append_rows(filas_unicas, value_input_option='USER_ENTERED')
                    return True
                else:
                    st.toast("ℹ️ Esta partida ya estaba en la ruta activa de hoy.", icon="ℹ️")
                    return False
        except Exception as e:
            st.error(f"Error al despachar: {e}")
            return False

    doc = init_connection()

    # --- PESTAÑAS DE OPERACIÓN ---
    tab_entregas, tab_recolecciones, tab_compras, tab_cotizaciones = st.tabs(["📦 Entregas (CDR)", "↩️ Recolecciones (CDR)", "🛒 Compras", "🔎 Cotizaciones"])
    
    # ---------------------------------------------------------
    # TAB 1: ENTREGAS (SOLO NUEVO LEÓN Y SIN PAQUETERÍA)
    # ---------------------------------------------------------
    with tab_entregas:
        st.caption("Muestra únicamente piezas con remisión generada (**EN TRÁNSITO**), sin guía de paquetería y cuyo taller pertenece a **Nuevo León**.")
        # Unificamos ambas aseguradoras para que el despachador vea todas las entregas locales juntas
        df_base_ent = df_completo.copy() if not df_completo.empty else pd.DataFrame()
        df_ent = df_base_ent[df_base_ent[col_estatus].astype(str).str.upper() == "EN TRANSITO"].copy() if not df_base_ent.empty and col_estatus else pd.DataFrame()
        
        if not df_ent.empty:
            # 1. Excluir las que ya tienen paquetería o número de guía
            if col_paqueteria and col_paqueteria in df_ent.columns:
                df_ent = df_ent[df_ent[col_paqueteria].astype(str).str.strip().isin(['', 'nan', 'None', 'NAN'])]
            if col_guia and col_guia in df_ent.columns:
                df_ent = df_ent[df_ent[col_guia].astype(str).str.strip().isin(['', 'nan', 'None', 'NAN'])]
                
            # 2. Filtrar estrictamente talleres de NUEVO LEÓN
            if not df_catalogo.empty and col_taller:
                c_tall_cat = next((c for c in df_catalogo.columns if 'TALLER' in str(c).upper()), None)
                c_est_cat = next((c for c in df_catalogo.columns if 'ESTADO' in str(c).upper()), None)
                if c_tall_cat and c_est_cat:
                    dict_est_cdr = dict(zip(df_catalogo[c_tall_cat].astype(str).str.strip().str.upper(), df_catalogo[c_est_cat].astype(str).str.strip().str.upper()))
                    def es_taller_nl(t_val):
                        est_t = dict_est_cdr.get(str(t_val).strip().upper(), "NUEVO LEON").replace("Ó", "O")
                        return ("NUEVO LEON" in est_t or "NL" in est_t or "N.L" in est_t)
                    df_ent = df_ent[df_ent[col_taller].apply(es_taller_nl)].copy()

        if not df_ent.empty:
            df_ent['Vehiculo_Info'] = df_ent.apply(armar_vehiculo, axis=1)
            df_ent['Enviar Hoy'] = False
            for taller, df_taller in df_ent.groupby(col_taller):
                with st.expander(f"🏢 {taller} | {len(df_taller)} pieza(s) lista(s) para ruta local", expanded=False):
                    cols_ver = [c for c in ['Enviar Hoy', col_id, 'Vehiculo_Info', col_desc, col_estatus, col_remision, col_comentarios] if c in df_taller.columns]
                    cfg = {
                        "Enviar Hoy": st.column_config.CheckboxColumn("🚚 Enviar Hoy", default=False),
                        col_id: st.column_config.TextColumn("Pedido / Siniestro", disabled=True),
                        'Vehiculo_Info': st.column_config.TextColumn("Vehículo", disabled=True),
                        col_desc: st.column_config.TextColumn("Descripción", disabled=True)
                    }
                    ed_ent = st.data_editor(df_taller[cols_ver], column_config=cfg, hide_index=True, use_container_width=True, key=f"ent_{taller}")
                    
                    notas_ent = st.text_input("📝 Instrucciones / Notas:", placeholder="Ej. Dejar con el jefe de taller", key=f"notas_ent_{taller}")
                    
                    if st.button(f"➕ Enviar Selección a {taller}", key=f"btn_ent_{taller}"):
                        seleccionados = ed_ent[ed_ent['Enviar Hoy'] == True]
                        if not seleccionados.empty:
                            df_envio = df_taller.loc[seleccionados.index].copy()
                            if despachar_a_bd_rutas(df_envio, "entrega", notas_ent):
                                st.success("¡Destino agregado a la ruta del operador!")
                                st.rerun()
                        else: st.warning("Selecciona al menos una pieza.")
        else:
            st.success("No hay piezas 'En Tránsito' de Nuevo León pendientes de envío local a CDR.")

    # ---------------------------------------------------------
    # TAB 2: RECOLECCIONES
    # ---------------------------------------------------------
    with tab_recolecciones:
        df_rec = df_completo[df_completo[col_estatus].astype(str).str.upper() == "EN PROCESO DE RECOLECCIÓN"].copy() if not df_completo.empty and col_estatus else pd.DataFrame()

        if not df_rec.empty:
            df_rec['Vehiculo_Info'] = df_rec.apply(armar_vehiculo, axis=1)
            df_rec['Enviar Hoy'] = False
            for taller, df_taller in df_rec.groupby(col_taller):
                with st.expander(f"↩️ {taller} | {len(df_taller)} piezas a recolectar", expanded=False):
                    cols_ver = [c for c in ['Enviar Hoy', col_id, 'Vehiculo_Info', col_desc, col_estatus, col_paqueteria, col_guia, col_comentarios] if c in df_taller.columns]
                    cfg_rec = {
                        "Enviar Hoy": st.column_config.CheckboxColumn("🚚 Enviar Hoy", default=False),
                        col_id: st.column_config.TextColumn("Siniestro", disabled=True),
                        'Vehiculo_Info': st.column_config.TextColumn("Vehículo", disabled=True),
                        col_desc: st.column_config.TextColumn("Descripción", disabled=True)
                    }
                    ed_rec = st.data_editor(df_taller[cols_ver], column_config=cfg_rec, hide_index=True, use_container_width=True, key=f"rec_{taller}")
                        
                    notas_rec = st.text_input("📝 Instrucciones / Notas:", placeholder="Ej. Pedir acuse de recibo físico", key=f"notas_rec_{taller}")
                        
                    if st.button(f"➕ Enviar Selección a Ruta", key=f"btn_rec_{taller}"):
                        seleccionados = ed_rec[ed_rec['Enviar Hoy'] == True]
                        if not seleccionados.empty:
                            df_envio = df_taller.loc[seleccionados.index].copy()
                            if despachar_a_bd_rutas(df_envio, "recoleccion", notas_rec):
                                st.success("¡Recolección asignada al operador!")
                                st.rerun()
                        else: st.warning("Selecciona al menos una pieza.")

                    if st.button(f"🔙 El Taller se quedó la pieza (Regresar a Entregado)", key=f"btn_cancel_rec_{taller}"):
                        seleccionados = ed_rec[ed_rec['Enviar Hoy'] == True]
                        if not seleccionados.empty:
                            try:
                                ws_u = doc.worksheet("BD_UNIFICADA")
                                datos_u = ws_u.get_all_values()
                                head_u = [str(h).strip().upper() for h in datos_u[0]]
                                idx_est = head_u.index(col_estatus.upper()) + 1
                                idx_sin = head_u.index(col_id.upper())
                                idx_desc = head_u.index(col_desc.upper())
                                celdas_upd = []
                                for _, r_sel in seleccionados.iterrows():
                                    for i, r_u in enumerate(datos_u[1:]):
                                        if str(r_u[idx_sin]).strip().upper() == str(r_sel[col_id]).strip().upper() and str(r_u[idx_desc]).strip().upper() == str(r_sel[col_desc]).strip().upper():
                                            celdas_upd.append(gspread.Cell(row=i+2, col=idx_est, value="ENTREGADO"))
                                if celdas_upd:
                                    ws_u.update_cells(celdas_upd, value_input_option='USER_ENTERED')
                                    st.success("Pieza regresada a 'Entregado' exitosamente.")
                                    st.cache_data.clear()
                                    time.sleep(1)
                                    st.rerun()
                            except Exception as e: st.error(f"Error: {e}")
                        else: st.warning("Selecciona al menos una pieza.")
        else:
            st.success("No hay recolecciones con estatus 'EN PROCESO DE RECOLECCIÓN'.")

    # ---------------------------------------------------------
    # TAB 3: COMPRAS (ALIMENTADO DIRECTO DE PRÓXIMAS LLEGADAS)
    # ---------------------------------------------------------
    with tab_compras:
        st.caption("Lista de compras activas en **📦 Próximas Llegadas** pendientes de recolectar con proveedor. Al enviarlas con el operador, se marcarán automáticamente como **Recibidas** en el módulo de Compras.")
        if not df_compras.empty and not df_completo.empty:
            def gen_llave_rutas(id_val, desc_val):
                id_str = str(id_val).strip().upper()
                if id_str.endswith('.0'): id_str = id_str[:-2]
                return f"{id_str}_{' '.join(str(desc_val).strip().upper().split())}"

            df_c_todas_pend = df_compras.copy()
            df_c_todas_pend['_GS_Row_Comp'] = df_c_todas_pend.index + 2
            df_c_todas_pend['Recibido_Bool'] = df_c_todas_pend['Recibido'].astype(str).str.strip().str.upper().isin(['TRUE', 'SI', '1', 'YES', 'V', 'X'])
            df_c_todas_pend = df_c_todas_pend[df_c_todas_pend['Recibido_Bool'] == False].copy()
            
            total_en_prox_llegadas = len(df_c_todas_pend)
            excluidas_ebay = len(df_c_todas_pend[df_c_todas_pend['Proveedor'].astype(str).str.strip().str.upper().isin(['EBAY', 'INVENTARIO'])])

            df_c_pend = df_c_todas_pend[
                df_c_todas_pend['Proveedor'].notna() & 
                (~df_c_todas_pend['Proveedor'].astype(str).str.strip().str.upper().isin(['', 'NAN', 'NONE', 'INVENTARIO', 'EBAY']))
            ].copy()

            if not df_c_pend.empty:
                df_c_pend['LLAVE'] = df_c_pend.apply(lambda r: gen_llave_rutas(r.get('Siniestro', ''), r.get('Descripción Pieza', '')), axis=1)

                df_base_global = df_completo.copy()
                c_id_g = next((c for c in df_base_global.columns if "SINIESTRO" in str(c).upper()), col_id)
                c_desc_g = next((c for c in df_base_global.columns if "DESCRIPCI" in str(c).upper() or "REFACCI" in str(c).upper()), col_desc)
                c_est_g = next((c for c in df_base_global.columns if "ESTATUS" in str(c).upper() and "ENV" not in str(c).upper() and "PAGO" not in str(c).upper()), col_estatus)
                c_vin_g = next((c for c in df_base_global.columns if "VIN" in str(c).upper() or "SERIE" in str(c).upper()), col_vin)

                df_base_global['LLAVE'] = df_base_global.apply(lambda r: gen_llave_rutas(r.get(c_id_g, ''), r.get(c_desc_g, '')), axis=1)
                
                c_obs_g = next((c for c in df_base_global.columns if "COMENTARIO" in str(c).upper() or "OBSERVACION" in str(c).upper()), col_comentarios)
                dict_est_g = dict(zip(df_base_global['LLAVE'], df_base_global[c_est_g].astype(str).str.strip().str.upper())) if c_est_g else {}
                dict_vin_g = dict(zip(df_base_global['LLAVE'], df_base_global[c_vin_g].astype(str).str.strip())) if c_vin_g else {}
                dict_obs_g = dict(zip(df_base_global['LLAVE'], df_base_global[c_obs_g].astype(str).str.strip())) if c_obs_g else {}

                df_c_pend['Estatus_Real'] = df_c_pend['LLAVE'].map(dict_est_g).fillna("EN PROCESAMIENTO")
                df_c_pend['VIN_Real'] = df_c_pend['LLAVE'].map(dict_vin_g).fillna("S/D")
                df_c_pend['Observaciones'] = df_c_pend['LLAVE'].map(dict_obs_g).replace(['nan', 'None'], '').fillna("")

                estatus_excluidos = ["ENTREGADO", "RECIBIDO", "FACTURADO", "CANCELADO", "PÉRDIDA TOTAL", "PERDIDA TOTAL", "PAGO DE DAÑOS"]
                df_comp_rutas = df_c_pend[~df_c_pend['Estatus_Real'].isin(estatus_excluidos)].copy()

                # --- RESUMEN VISUAL DE CONTEO ---
                kc1, kc2, kc3 = st.columns(3)
                kc1.metric("📦 Total en Próximas Llegadas", total_en_prox_llegadas)
                kc2.metric("🚚 Listas para Recolección", f"{len(df_comp_rutas)} pza(s) en {df_comp_rutas['Proveedor'].nunique()} prov.")
                kc3.metric("🌐 Excluidas (eBay / Inv.)", excluidas_ebay)

                if not df_comp_rutas.empty:
                    df_comp_rutas['Enviar Hoy'] = False
                    df_comp_rutas['Siniestro_Col'] = df_comp_rutas['Siniestro'].astype(str).str.strip()
                    df_comp_rutas['Vehiculo_Info'] = df_comp_rutas.get('Vehículo', pd.Series(["S/D"]*len(df_comp_rutas))).astype(str).str.strip()
                    df_comp_rutas['Pieza_Col'] = df_comp_rutas['Descripción Pieza'].astype(str).str.strip()

                    for prov, df_prov in df_comp_rutas.groupby('Proveedor'):
                        with st.expander(f"🛒 {prov} | {len(df_prov)} pieza(s) en Próximas Llegadas", expanded=False):
                            cols_ver = ['Enviar Hoy', 'Siniestro_Col', 'Vehiculo_Info', 'Taller', 'Pieza_Col', 'Costo Compra', 'Estatus_Real']
                            cols_ver = [c for c in cols_ver if c in df_prov.columns]
                            cfg_comp = {
                                "Enviar Hoy": st.column_config.CheckboxColumn("🚚 Recoger Hoy", default=False),
                                "Siniestro_Col": st.column_config.TextColumn("Siniestro", disabled=True),
                                "Vehiculo_Info": st.column_config.TextColumn("Vehículo", disabled=True),
                                "Taller": st.column_config.TextColumn("Destino (CDR)", disabled=True),
                                "Pieza_Col": st.column_config.TextColumn("Pieza a recoger", disabled=True),
                                "Costo Compra": st.column_config.TextColumn("Costo", disabled=True),
                                "Estatus_Real": st.column_config.TextColumn("Estatus", disabled=True)
                            }
                            ed_comp = st.data_editor(df_prov[cols_ver], column_config=cfg_comp, hide_index=True, use_container_width=True, key=f"comp_{prov}")
                            
                            notas_comp = st.text_input("📝 Instrucciones / Notas:", placeholder="Ej. Pagar en efectivo al llegar / Ir a Papelería Angie", key=f"notas_comp_{prov}")
                            
                            if st.button(f"➕ Enviar al Operador a {prov} y Marcar Recibido", type="primary", key=f"btn_comp_{prov}"):
                                seleccionados = ed_comp[ed_comp['Enviar Hoy'] == True]
                                if not seleccionados.empty:
                                    df_envio = df_prov.loc[seleccionados.index].copy()
                                    df_envio['Proveedor'] = prov
                                    if col_id: df_envio[col_id] = df_envio['Siniestro_Col']
                                    if col_desc: df_envio[col_desc] = df_envio['Pieza_Col']
                                    if col_vin: df_envio[col_vin] = df_envio['VIN_Real']
                                    
                                    if despachar_a_bd_rutas(df_envio, "compra", notas_comp):
                                        try:
                                            ws_c_upd = doc.worksheet("BD_COMPRAS")
                                            headers_c_upd = [str(h).strip().upper() for h in ws_c_upd.row_values(1)]
                                            if "RECIBIDO" in headers_c_upd:
                                                col_idx_rec = headers_c_upd.index("RECIBIDO") + 1
                                                celdas_rec = [
                                                    gspread.Cell(row=int(r_env['_GS_Row_Comp']), col=col_idx_rec, value="SI")
                                                    for _, r_env in df_envio.iterrows()
                                                ]
                                                if celdas_rec:
                                                    ws_c_upd.update_cells(celdas_rec, value_input_option='USER_ENTERED')
                                        except Exception as e_rec:
                                            st.warning(f"Se envió a ruta, pero hubo un detalle al marcar Recibido en BD_COMPRAS: {e_rec}")

                                        st.cache_data.clear()
                                        st.success(f"✅ ¡Visita a {prov} asignada al operador y marcada como Recibida en Compras!")
                                        time.sleep(1)
                                        st.rerun()
                                else:
                                    st.warning("Selecciona al menos una pieza marcando la casilla '🚚 Recoger Hoy'.")
                else:
                    st.info("No hay compras pendientes de recolección local en Próximas Llegadas.")
            else:
                st.info("No hay compras activas pendientes de recepción en Próximas Llegadas.")
        else:
            st.info("Falta información de compras para cruzar datos.")

    # ---------------------------------------------------------
    # TAB 4: COTIZACIONES EVENTUALES
    # ---------------------------------------------------------
    with tab_cotizaciones:
        st.markdown("### 🔎 Asignar Cotización / Visita Especial")
        st.caption("Usa esta pestaña para enviar al operador a revisar o comprar piezas eventuales.")
        
        lista_provs_cot = []
        dict_dir_cot = {}
        if not df_proveedores.empty:
            c_prv_c = next((c for c in df_proveedores.columns if 'PROVEEDOR' in str(c).upper() or 'NOMBRE' in str(c).upper()), None)
            c_suc_c = next((c for c in df_proveedores.columns if 'SUCURSAL' in str(c).upper()), None)
            c_dir_c = next((c for c in df_proveedores.columns if 'DIRECC' in str(c).upper()), None)
            if c_prv_c:
                for _, rp_c in df_proveedores.iterrows():
                    p_n = str(rp_c.get(c_prv_c, '')).strip().upper()
                    s_n = str(rp_c.get(c_suc_c, '')).strip().upper() if c_suc_c else ""
                    if not p_n or p_n == 'NAN': continue
                    llave_p = f"{p_n} - {s_n}" if (s_n and s_n != 'NAN') else p_n
                    lista_provs_cot.append(llave_p)
                    if c_dir_c and str(rp_c.get(c_dir_c, '')).strip():
                        dict_dir_cot[llave_p] = str(rp_c.get(c_dir_c, '')).strip()
                lista_provs_cot = sorted(list(set(lista_provs_cot)))

        col_sel_p, col_vin_p = st.columns(2)
        with col_sel_p:
            prov_eventual = st.selectbox("Lugar (Yonke / Agencia / Proveedor) *", ["", "-- ESCRIBIR NUEVO --"] + lista_provs_cot, key="sel_prov_cot_ruta")
        with col_vin_p:
            vin_eventual = st.text_input("VIN / Número de Serie (Opcional)", key="vin_cot_ruta")

        if prov_eventual == "":
            st.info("👆 Selecciona un lugar arriba para habilitar la captura.")
        else:
            with st.form("form_cotizacion_ruta", clear_on_submit=False):
                nuevo_prov = ""
                nueva_suc_cot = ""
                nuevas_marcas_cot = ""
                nuevo_tel_cot = ""
                nuevo_tiempo_cot = "Inmediata"
                nueva_cond_cot = "Contra Entrega"
                nuevos_dias_cot = 0
                guardar_en_directorio = True

                if prov_eventual == "-- ESCRIBIR NUEVO --":
                    st.markdown("##### 🏢 Datos del Nuevo Proveedor (Se registrará en `BD_PROVEEDORES`)")
                    cp1, cp2, cp3 = st.columns([2, 1.5, 1.5])
                    nuevo_prov = cp1.text_input("Nombre del Proveedor * (Ej. GOVI)").strip().upper()
                    nueva_suc_cot = cp2.text_input("Sucursal / Zona (Ej. STO DOMINGO)").strip().upper()
                    nuevo_tel_cot = cp3.text_input("Teléfono / Contacto").strip()

                    cp4, cp5 = st.columns([2.5, 1.5])
                    dir_eventual = cp4.text_input("Dirección Completa (Para navegación del chofer) *").strip()
                    nuevas_marcas_cot = cp5.text_input("Marcas / Especialidad", placeholder="Ej. Suspensión, General").strip().upper()

                    cp6, cp7, cp8 = st.columns(3)
                    nuevo_tiempo_cot = cp6.selectbox("Tiempo Promedio de Entrega", ["Inmediata", "1 a 2 días", "3 a 5 días", "Más de 5 días", "Bajo Pedido"])
                    nueva_cond_cot = cp7.selectbox("Condición de Pago", ["Contra Entrega", "Pago Anticipado", "Anticipo", "Crédito", "Pago en Plataforma"])
                    nuevos_dias_cot = cp8.number_input("Días Crédito", min_value=0, value=0, step=1)
                    guardar_en_directorio = st.checkbox("☑️ Guardar este proveedor en el Directorio (BD_PROVEEDORES)", value=True)
                else:
                    dir_precargada = dict_dir_cot.get(prov_eventual, "")
                    dir_eventual = st.text_input("Dirección o Zona (Para que navegue el chofer)", value=dir_precargada)

                st.markdown("##### ⚙️ Piezas a buscar / comprar")
                st.caption("Puedes capturar solo el **# Parte**, solo la **Descripción**, o ambos. Usa el signo **`+`** abajo de la tabla para agregar más renglones.")
                
                df_piezas_base = pd.DataFrame([
                    {"No. Parte": "", "Descripción de la Pieza": ""},
                    {"No. Parte": "", "Descripción de la Pieza": ""}
                ])
                ed_piezas_cot = st.data_editor(
                    df_piezas_base,
                    num_rows="dynamic",
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "No. Parte": st.column_config.TextColumn("🔢 # Parte / SKU", width="medium"),
                        "Descripción de la Pieza": st.column_config.TextColumn("🛠️ Descripción de la Pieza", width="large")
                    },
                    key="ed_tabla_piezas_cot"
                )
                
                notas_eventual = st.text_input("📝 Instrucciones / Notas para el operador:", placeholder="Ej. Preguntar por  X / Pedir factura")
                
                btn_cot = st.form_submit_button("➕ Enviar Cotización a la Ruta", type="primary")
                
                if btn_cot:
                    if prov_eventual == "-- ESCRIBIR NUEVO --":
                        nombre_final = f"{nuevo_prov} - {nueva_suc_cot}" if nueva_suc_cot else nuevo_prov
                    else:
                        nombre_final = prov_eventual

                    piezas_lista = []
                    for _, r_pz in ed_piezas_cot.iterrows():
                        np_val = str(r_pz.get("No. Parte", "")).strip().upper()
                        ds_val = str(r_pz.get("Descripción de la Pieza", "")).strip().upper()
                        if np_val == "NAN": np_val = ""
                        if ds_val == "NAN": ds_val = ""
                        
                        if np_val and ds_val:
                            piezas_lista.append(f"[{np_val}] {ds_val}")
                        elif np_val:
                            piezas_lista.append(f"NP: {np_val}")
                        elif ds_val:
                            piezas_lista.append(ds_val)

                    if not nombre_final or len(piezas_lista) == 0:
                        st.error("⚠️ El Lugar y al menos 1 Pieza (No. Parte o Descripción) son obligatorios.")
                    else:
                        if prov_eventual == "-- ESCRIBIR NUEVO --" and guardar_en_directorio and nuevo_prov:
                            try:
                                ws_p = doc.worksheet("BD_PROVEEDORES")
                                headers_p = [str(h).strip() for h in ws_p.row_values(1)]
                                fila_prov = [""] * max(len(headers_p), 10)
                                
                                def safe_idx_p(name):
                                    for idx_h, h_val in enumerate(headers_p):
                                        if h_val.upper() == name.upper():
                                            return idx_h
                                    return -1

                                i_prv = safe_idx_p('Proveedor')
                                i_suc = safe_idx_p('Sucursal')
                                i_mar = safe_idx_p('Marcas Especialidad')
                                i_tel = safe_idx_p('Teléfono')
                                i_dir = safe_idx_p('Dirección')
                                i_tie = safe_idx_p('Tiempo de Entrega')
                                i_con = safe_idx_p('Condición Pago')
                                i_dia = safe_idx_p('Días Crédito')

                                if i_prv >= 0: fila_prov[i_prv] = nuevo_prov
                                if i_suc >= 0: fila_prov[i_suc] = nueva_suc_cot
                                if i_mar >= 0: fila_prov[i_mar] = nuevas_marcas_cot
                                if i_tel >= 0: fila_prov[i_tel] = str(nuevo_tel_cot)
                                if i_dir >= 0: fila_prov[i_dir] = dir_eventual.upper()
                                if i_tie >= 0: fila_prov[i_tie] = nuevo_tiempo_cot
                                if i_con >= 0: fila_prov[i_con] = nueva_cond_cot
                                if i_dia >= 0: fila_prov[i_dia] = str(nuevos_dias_cot)

                                ws_p.append_row(fila_prov[:len(headers_p)] if headers_p else fila_prov, value_input_option='USER_ENTERED')
                                st.cache_data.clear()
                            except Exception as e_prov:
                                st.warning(f"Nota: No se pudo guardar en BD_PROVEEDORES ({e_prov}), pero se enviará a la ruta.")
                        
                        datos_cot = {
                            'Proveedor': [nombre_final] * len(piezas_lista),
                            'Vehiculo_Info': ["Cotización / Compra Directa"] * len(piezas_lista),
                            'Descrip.': piezas_lista,
                            'Direccion_Manual': [dir_eventual] * len(piezas_lista)
                        }
                        if col_vin: datos_cot[col_vin] = [vin_eventual if vin_eventual else "S/D"] * len(piezas_lista)
                        if col_id: datos_cot[col_id] = ["N/A"] * len(piezas_lista)
                        
                        df_cot = pd.DataFrame(datos_cot)
                        if col_desc and col_desc not in df_cot.columns:
                            df_cot[col_desc] = piezas_lista
                        
                        if despachar_a_bd_rutas(df_cot, "cotizacion", notas_eventual):
                            st.success(f"✅ ¡Enviado a ruta para {nombre_final} ({len(piezas_lista)} pieza(s))!")
                            time.sleep(1)
                            st.rerun()

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
                                            # El clon (CAMBIO) es un pedido nuevo activo: SOLO debe insertarse en BD_UNIFICADA
                                            if fila_en_uni:
                                                filas_nuevas_uni.append(crear_fila_clon(encabezados_uni, fila_en_uni, datos_uni))
                                            elif fila_en_hist:
                                                filas_nuevas_uni.append(crear_fila_clon(encabezados_hist, fila_en_hist, datos_hist))
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
                            df_comp_exp['_F_Comp_Dt'] = df_comp_exp['Fecha Compra'].apply(parse_dt_safe_op) if 'Fecha Compra' in df_comp_exp.columns else pd.NaT
                            df_comp_exp['_ETA_Num'] = pd.to_numeric(df_comp_exp.get('Tiempo Entrega (Días)', 0), errors='coerce').fillna(0)
                            df_comp_exp['Llegada Est.'] = (df_comp_exp['_F_Comp_Dt'] + pd.to_timedelta(df_comp_exp['_ETA_Num'], unit='d')).dt.strftime('%d/%b/%y').fillna('-')
                            
                            cols_comp = ['Siniestro', 'Taller', 'Descripción Pieza', 'Proveedor', 'Costo Compra', 'Fecha Compra', 'Tiempo Entrega (Días)', 'Llegada Est.', 'Estatus Pago', 'Recibido']
                            df_comp_disp = df_comp_exp[[c for c in cols_comp if c in df_comp_exp.columns]].copy()
                            df_comp_disp.rename(columns={'Descripción Pieza': 'Pieza', 'Costo Compra': 'Costo', 'Tiempo Entrega (Días)': 'ETA (Días)'}, inplace=True)
                            st.dataframe(df_comp_disp, hide_index=True, use_container_width=True)
                        else: st.info("No existen registros de compras o pagos capturados para estos siniestros.")
                else: st.warning("La base de datos de compras no está disponible.")
        else: st.info("👆 Selecciona al menos un filtro en la parte superior para mostrar resultados.")
    else: st.warning("La base de datos está vacía.")

elif vista_actual == "🛠️ Cuartel General":
    import io
    import subprocess
    import sys
    import os
    import re

    st.markdown("### 🛠️ Cuartel General PMR (Sala de Máquinas)")
    
    # --- SUB-PESTAÑAS ESTILO DIRECTORIO (100% ANCHO PARA CADA MÓDULO) ---
    tab_bots, tab_mant = st.tabs(["🤖 Centro de Bots y Alertas", "💾 Mantenimiento y Pendientes"])

    # =========================================================================
    # PESTAÑA 1: CENTRO DE BOTS Y ALERTAS (PANTALLA COMPLETA)
    # =========================================================================
    with tab_bots:
        st.markdown("""
            <style>
            @keyframes matrix_pulse {
                0% { box-shadow: 0 0 10px rgba(0, 255, 65, 0.25), inset 0 0 15px rgba(0, 255, 65, 0.15); }
                50% { box-shadow: 0 0 22px rgba(0, 255, 65, 0.55), inset 0 0 25px rgba(0, 255, 65, 0.25); }
                100% { box-shadow: 0 0 10px rgba(0, 255, 65, 0.25), inset 0 0 15px rgba(0, 255, 65, 0.15); }
            }
            @keyframes matrix_scanline {
                0% { background-position: 0 0; }
                100% { background-position: 0 100%; }
            }
            .matrix-terminal {
                background-color: #020502;
                background-image: 
                    linear-gradient(rgba(0, 255, 65, 0.04) 1px, transparent 1px),
                    radial-gradient(rgba(0, 40, 10, 0.35), #000000 90%);
                background-size: 100% 3px, 100% 100%;
                color: #00FF41;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 13.5px;
                line-height: 1.45;
                padding: 16px 20px;
                border-radius: 10px;
                border: 1px solid #00FF41;
                animation: matrix_pulse 3s infinite ease-in-out;
                min-height: 180px;
                height: auto;
                white-space: pre-wrap;
                position: relative;
                text-shadow: 0 0 6px rgba(0, 255, 65, 0.65);
            }
            .matrix-header {
                color: #88FF99;
                font-family: 'Consolas', monospace;
                font-size: 11.5px;
                letter-spacing: 2px;
                border-bottom: 1px dashed rgba(0, 255, 65, 0.4);
                padding-bottom: 6px;
                margin-bottom: 10px;
                display: flex;
                justify-content: space-between;
            }
            .matrix-katakana {
                color: rgba(0, 255, 65, 0.22);
                font-size: 11px;
                letter-spacing: 3px;
                user-select: none;
            }
            .matrix-cursor {
                display: inline-block;
                width: 9px;
                height: 15px;
                background-color: #00FF41;
                vertical-align: middle;
                animation: blink_mtx 0.8s infinite;
            }
            @keyframes blink_mtx { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
            </style>
        """, unsafe_allow_html=True)

        col_ctrl, col_wa = st.columns([1.1, 1.9], gap="large")

        with col_ctrl:
            with st.form("form_lanzador_bots_master"):
                st.markdown("**1. Panel de Ejecución**")
                st.caption("Selecciona el robot que deseas correr en el servidor:")
                bot_seleccionado = st.selectbox(
                    "Seleccionar Robot:", 
                    ["GNP Inpart", "Multiasistencia", "Paquetexpress (Rastreo)"], 
                    label_visibility="collapsed"
                )
                modo_extraccion = st.radio(
                    "Modo de Ejecución:", 
                    ["Oculto (Rápido)", "Visual (Ver Chrome)"], 
                    horizontal=True
                )
                st.write("")
                btn_extraer = st.form_submit_button("🚀 Iniciar Robot", type="primary", use_container_width=True)

            if st.button("🧹 Limpiar Bandeja y Consola", use_container_width=True, key="btn_limpiar_wa"):
                st.session_state.pop('temp_wa_alerts', None)
                st.session_state.pop('temp_criticos_alerts', None)
                st.session_state.pop('temp_bot_log', None)
                st.session_state.pop('temp_bot_status', None)
                st.session_state.pop('temp_bot_resumen', None)
                st.rerun()

            espacio_spinner = st.empty()

        with col_wa:
            with st.container(border=True):
                st.markdown("**2. Mensajes Generados (WhatsApp)**")
                st.caption("Copia el bloque de nuevas asignaciones y pégalo directo en WhatsApp Web:")
                texto_wa = st.session_state.get('temp_wa_alerts', "Realiza una extracción primero para ver los mensajes aquí.")
                st.text_area("WhatsApp Output", value=texto_wa, height=175, label_visibility="collapsed")

        # --- CONSOLA MATRIX EN TIEMPO REAL ---
        st.markdown("**🖥️ Consola Matrix en Tiempo Real (Streaming Directo del Robot)**")
        contenedor_matrix = st.empty()

        def render_matrix_terminal(log_txt, activo=False):
            import html
            estado_mtx = "🟢 EJECUTANDO EN VIVO..." if activo else "⚡ SISTEMA EN ESPERA / COMPLETADO"
            cursor_html = '<span class="matrix-cursor"></span>' if activo else ''
            contenido_limpio = html.escape(log_txt) if log_txt else "Esperando orden de ejecución en el Cuartel General..."
            html_box = f"""
            <div class="matrix-terminal">
                <div class="matrix-header">
                    <span>PMR // MATRIX_CORE_TERMINAL v2.6</span>
                    <span class="matrix-katakana">ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄ010110</span>
                    <span>{estado_mtx}</span>
                </div>
                <div>{contenido_limpio}{cursor_html}</div>
            </div>
            """
            contenedor_matrix.markdown(html_box, unsafe_allow_html=True)

        # Mostrar bitácora previa si no se está corriendo en este instante
        if not btn_extraer:
            render_matrix_terminal(st.session_state.get('temp_bot_log', ''), activo=False)

        # --- CUADRO INDEPENDIENTE PARA REVISIÓN DE ESTATUS CRÍTICO ---
        with st.container(border=True):
            st.markdown("**3. 🚨 Revisión de Estatus Crítico (Hoy y Vencidos en Base Maestra)**")
            st.caption("Radar de partidas vencidas, por vencer hoy, reactivadas o con alertas de precio:")
            texto_criticos = st.session_state.get('temp_criticos_alerts', "Realiza una extracción de GNP Inpart o Multiasistencia para ver el radar de vencimientos aquí.")
            st.text_area("Criticos Output", value=texto_criticos, height=185, label_visibility="collapsed")

        # --- LÓGICA DE EJECUCIÓN DEL ROBOT CON STREAMING EN TIEMPO REAL ---
        if btn_extraer:
            if bot_seleccionado == "GNP Inpart":
                archivo_ejecutar = "gnp_inpart.py"
            elif bot_seleccionado == "Multiasistencia":
                archivo_ejecutar = "sincronizador_multiasistencia.py"
            else:
                archivo_ejecutar = "motor_rastreo.py"
                
            arg_modo = "--oculto" if "Oculto" in modo_extraccion else "--visual"
            
            with espacio_spinner:
                with st.spinner(f"Corriendo {bot_seleccionado} en vivo..."):
                    try:
                        with open("credentials.json", "w", encoding="utf-8") as f:
                            f.write(st.secrets["google_credentials"])
                            
                        render_matrix_terminal(f"[SISTEMA] Verificando motor Chromium y despertando a {bot_seleccionado}...\n", activo=True)
                        subprocess.run([sys.executable, '-m', 'playwright', 'install', 'chromium'], check=False)
                        
                        # Bandera -u obligatoria para que Python escupa cada línea en tiempo real sin esperar al final
                        cmd = [sys.executable, "-u", archivo_ejecutar]
                        if bot_seleccionado != "Paquetexpress (Rastreo)":
                            cmd.append(arg_modo)
                        
                        env_bot = os.environ.copy()
                        env_bot["PYTHONIOENCODING"] = "utf-8"
                        env_bot["PYTHONUNBUFFERED"] = "1"

                        proceso = subprocess.Popen(
                            cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True,
                            bufsize=1,
                            env=env_bot,
                            encoding="utf-8",
                            errors="replace"
                        )
                        
                        lineas_acumuladas = []
                        for linea_rt in iter(proceso.stdout.readline, ''):
                            if not linea_rt:
                                break
                            lineas_acumuladas.append(linea_rt)
                            # Mostramos todo el progreso acumulado para que la terminal crezca conforme avanza
                            vista_completa_rt = "".join(lineas_acumuladas)
                            render_matrix_terminal(vista_completa_rt, activo=True)
                            
                        proceso.stdout.close()
                        returncode = proceso.wait()
                        salida_completa = "".join(lineas_acumuladas).strip()
                        
                        # 4. Calcular resumen de pedidos revisados
                        if bot_seleccionado == "Paquetexpress (Rastreo)":
                            guias_rev = len(re.findall(r"Buscando gu[íi]a:", salida_completa))
                            st.session_state['temp_bot_resumen'] = f"📊 **Resumen ({bot_seleccionado}):** Se consultaron **{guias_rev}** guías únicas en Paquetexpress."
                        else:
                            revisados = "0"
                            m_multi = re.search(r"Quedan\s+(\d+)\s+siniestros", salida_completa)
                            m_gnp = re.search(r"Total le[íi]dos[^:]*:\s*(\d+)", salida_completa)
                            if m_multi: revisados = m_multi.group(1)
                            elif m_gnp: revisados = m_gnp.group(1)
                            st.session_state['temp_bot_resumen'] = f"📊 **Resumen ({bot_seleccionado}):** Se revisaron **{revisados}** pedidos activos en el portal."
                        
                        # 5. Extraer limpiamente el bloque de WhatsApp
                        if "REPORTES LISTOS PARA COPIAR" in salida_completa:
                            parte_wa = re.split(r"REPORTES LISTOS PARA COPIAR(?: A WHATSAPP)?", salida_completa)[1]
                            for corte in ["🔄 PIEZAS REACTIVADAS", "🟠 CAMBIOS DE PRECIO", "🟡 ALERTAS DE PRECIO", "!!!!!"]:
                                if corte in parte_wa:
                                    parte_wa = parte_wa.split(corte)[0]
                            parte_wa = re.sub(r'^[=\s]+', '', parte_wa).strip()
                            st.session_state['temp_wa_alerts'] = parte_wa
                        elif bot_seleccionado != "Paquetexpress (Rastreo)":
                            st.session_state['temp_wa_alerts'] = "No hubo asignaciones nuevas para enviar por WhatsApp en esta corrida."

                        # 6. Extraer Revisión de Estatus Crítico y Alertas a su propio cuadro
                        marcadores_alerta = ["🔄 PIEZAS REACTIVADAS", "🟠 CAMBIOS DE PRECIO", "🟡 ALERTAS DE PRECIO", "REVISIÓN DE ESTATUS CRÍTICO"]
                        idx_inicio_crit = -1
                        for m_al in marcadores_alerta:
                            pos = salida_completa.find(m_al)
                            if pos != -1 and (idx_inicio_crit == -1 or pos < idx_inicio_crit):
                                idx_inicio_crit = pos
                                
                        if idx_inicio_crit != -1:
                            bloque_crit = salida_completa[idx_inicio_crit:]
                            lineas_crit = []
                            for l in bloque_crit.splitlines():
                                if set(l.strip()) == {'!'} or "REVISIÓN DE ESTATUS CRÍTICO" in l:
                                    continue
                                lineas_crit.append(l)
                            st.session_state['temp_criticos_alerts'] = "\n".join(lineas_crit).strip()
                        elif bot_seleccionado != "Paquetexpress (Rastreo)":
                            st.session_state['temp_criticos_alerts'] = "✅ Sin alertas críticas ni partidas vencidas en este momento."

                        # 7. Guardar la bitácora completa en la consola Matrix (conservando el progreso [1/N])
                        salida_tecnica = salida_completa
                        if idx_inicio_crit != -1:
                            salida_tecnica = salida_tecnica[:idx_inicio_crit]
                        if "REPORTES LISTOS PARA COPIAR" in salida_tecnica:
                            salida_tecnica = re.split(r"=+\s*\n\s*📱?\s*REPORTES LISTOS PARA COPIAR", salida_tecnica)[0]
                            
                        st.session_state['temp_bot_log'] = salida_tecnica.strip()
                        render_matrix_terminal(st.session_state['temp_bot_log'], activo=False)
                        
                        if returncode == 0:
                            st.session_state['temp_bot_status'] = f"✅ Ejecución de {bot_seleccionado} finalizada con éxito."
                        else:
                            st.session_state['temp_bot_status'] = f"⚠️ {bot_seleccionado} terminó con advertencias (revisa la consola Matrix)."
                            
                        st.cache_data.clear()
                        st.rerun()
                            
                    except Exception as e:
                        st.error(f"Error inesperado al lanzar el bot: {e}")
                    finally:
                        if os.path.exists("credentials.json"):
                            os.remove("credentials.json")

        # --- SECCIÓN INFERIOR: ESTATUS Y RESUMEN ---
        if st.session_state.get('temp_bot_status'):
            st.markdown("---")
            c_stat1, c_stat2 = st.columns(2)
            with c_stat1:
                if "✅" in st.session_state['temp_bot_status']:
                    st.success(st.session_state['temp_bot_status'])
                else:
                    st.warning(st.session_state['temp_bot_status'])
            with c_stat2:
                if st.session_state.get('temp_bot_resumen'):
                    st.info(st.session_state['temp_bot_resumen'])

    # =========================================================================
    # PESTAÑA 2: MANTENIMIENTO Y PENDIENTES
    # =========================================================================
    with tab_mant:
        col_m1, col_m2 = st.columns([1.2, 1.8], gap="large")
        
        with col_m1:
            st.markdown("#### 💾 Respaldo y Limpieza de Rutas")
            with st.container(border=True):
                st.markdown("**1. Descargar Historial Local (Plan B)**")
                st.caption("Descarga un archivo Excel con todas las rutas registradas.")
                if st.button("📥 Generar Respaldo de Rutas", use_container_width=True, key="btn_respaldo_rutas"):
                    with st.spinner("Empaquetando datos..."):
                        try:
                            doc = init_connection()
                            ws_rutas = doc.worksheet("BD_RUTAS")
                            datos = ws_rutas.get_all_values()
                            if len(datos) > 1:
                                df_respaldo = pd.DataFrame(datos[1:], columns=datos[0])
                                buffer = io.BytesIO()
                                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                                    df_respaldo.to_excel(writer, index=False, sheet_name='Historial_Rutas')
                                st.download_button(
                                    label="💾 Descargar Excel", 
                                    data=buffer.getvalue(), 
                                    file_name=f"Respaldo_Rutas_PMR_{datetime.datetime.now(tz_mx).strftime('%Y%m%d_%H%M')}.xlsx", 
                                    mime="application/vnd.ms-excel", 
                                    type="primary", 
                                    use_container_width=True, 
                                    key="dl_excel_rutas"
                                )
                            else: st.warning("La base de rutas está vacía.")
                        except Exception as e: st.error(f"Error: {e}")

            with st.container(border=True):
                st.markdown("**2. Purgar Nube (Optimizar App Móvil)**")
                st.caption("Conserva únicamente los viajes pendientes y los del día de hoy.")
                if st.button("🧹 Limpiar Viajes Antiguos", use_container_width=True, key="btn_limpiar_nube"):
                    with st.spinner("Limpiando el servidor..."):
                        try:
                            doc = init_connection()
                            ws_rutas = doc.worksheet("BD_RUTAS")
                            datos = ws_rutas.get_all_values()
                            if len(datos) > 1:
                                df_rutas_limpieza = pd.DataFrame(datos[1:], columns=[str(h).strip().upper() for h in datos[0]])
                                fecha_hoy_str = datetime.datetime.now(tz_mx).strftime("%d/%m/%Y")
                                cond_pendientes = df_rutas_limpieza['ESTATUS'].astype(str).str.upper() == 'PENDIENTE'
                                cond_hoy = df_rutas_limpieza['FECHA'].astype(str).str.contains(fecha_hoy_str, na=False)
                                df_a_conservar = df_rutas_limpieza[cond_pendientes | cond_hoy].copy()
                                filas_eliminadas = len(df_rutas_limpieza) - len(df_a_conservar)
                                
                                if filas_eliminadas > 0:
                                    ws_rutas.clear()
                                    filas_nuevas = [datos[0]]
                                    filas_nuevas.extend(df_a_conservar.values.tolist())
                                    ws_rutas.update(range_name='A1', values=filas_nuevas, value_input_option='USER_ENTERED')
                                    st.success(f"✅ Nube optimizada. Se eliminaron {filas_eliminadas} viajes.")
                                else: st.info("La base ya está optimizada.")
                            else: st.info("No hay datos para limpiar.")
                        except Exception as e: st.error(f"Error: {e}")

        with col_m2:
            st.markdown("#### 📌 Tareas, Bugs y Pendientes")
            try:
                doc = init_connection(); ws_notas = doc.worksheet("BD_NOTAS")
                datos_notas = ws_notas.get_all_values()
                if not datos_notas: ws_notas.append_row(["Fecha", "Nota", "Estatus"]); datos_notas = [["Fecha", "Nota", "Estatus"]]
                df_notas = pd.DataFrame(datos_notas[1:], columns=datos_notas[0])
                
                with st.form("form_nueva_nota", clear_on_submit=True):
                    c_in, c_bt = st.columns([3, 1])
                    with c_in:
                        nueva_nota = st.text_input("Nueva tarea o idea:", placeholder="Escribe aquí un pendiente o idea...", label_visibility="collapsed")
                    with c_bt:
                        sub_nota = st.form_submit_button("➕ Agregar", use_container_width=True)
                    if sub_nota and nueva_nota.strip():
                        fecha_str = datetime.datetime.now().strftime("%d/%b/%y %H:%M")
                        ws_notas.append_row([fecha_str, nueva_nota.strip(), "PENDIENTE"], value_input_option='USER_ENTERED')
                        st.success("Guardado."); time.sleep(0.5); st.rerun()

                if not df_notas.empty:
                    df_notas['GS_Row'] = df_notas.index + 2
                    df_pendientes = df_notas[df_notas['Estatus'].astype(str).str.upper() != 'COMPLETADO']
                    if df_pendientes.empty: 
                        st.info("¡Todo al día! Buen trabajo.")
                    else:
                        for _, row in df_pendientes.iterrows():
                            marcado = st.checkbox(f"**{row['Nota']}** *(Reportado: {row['Fecha']})*", key=f"nota_cg_{row['GS_Row']}")
                            if marcado:
                                ws_notas.update_cell(row['GS_Row'], 3, "COMPLETADO")
                                st.toast(f"Tarea completada: {row['Nota']}", icon="✅"); time.sleep(0.5); st.rerun()
                else: st.info("¡Todo al día!")
            except gspread.exceptions.WorksheetNotFound: st.error("⚠️ Crea la pestaña **BD_NOTAS** en Google Sheets.")
            except Exception as e: st.error(f"⚠️ Error al cargar notas: {e}")

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

    if btn_guardar:
        if not df_editado_conf.empty:
            for _, row in df_editado_conf.iterrows():
                k = generar_llave(row.get(col_id, ''), row.get(col_desc, ''))
                orig = originales.get(k, {'comentario': '', 'estatus_db': ''})
                        
                prov_conf = str(row.get('Proveedor', '')).strip()
                nuevo_estatus = None
                if row.get('Pérdida Total'): nuevo_estatus = "PÉRDIDA TOTAL"
                elif row.get('PDD'): nuevo_estatus = "PAGO DE DAÑOS"
                elif row.get('Cancelar'): nuevo_estatus = "CANCELADO"
                elif row.get('Pago_Danos'): nuevo_estatus = "PAGO A TALLER"
                elif row.get('Confirmar Surtido') or prov_conf not in ['', 'None', 'nan']: 
                    nuevo_estatus = "EN PROCESAMIENTO"
                
                comentario_actual = str(row.get(col_comentarios, '')).strip()
                if nuevo_estatus and nuevo_estatus != orig['estatus_db']: 
                    cambios_a_guardar.setdefault(k, {})['estatus'] = nuevo_estatus
                    if nuevo_estatus in ["EN PROCESAMIENTO", "PAGO A TALLER"]: 
                        cambios_a_guardar[k]['fecha_confi'] = fecha_hoy_sistema
                if comentario_actual != orig['comentario']: cambios_a_guardar.setdefault(k, {})['comentario'] = comentario_actual

                # --- AQUÍ ENTRA LA MAGIA PARA CREAR LA COMPRA DIRECTO AL CONFIRMAR ---
                prov_conf = str(row.get('Proveedor', '')).strip()
                if prov_conf not in ['', 'None', 'nan'] and nuevo_estatus != "CANCELADO":
                    cambios_a_guardar.setdefault(k, {})['crear_compra'] = True
                    cambios_a_guardar[k]['compra_prov'] = prov_conf
                    cambios_a_guardar[k]['compra_costo'] = str(row.get('Costo Compra', '0')).strip()
                    cambios_a_guardar[k]['compra_taller'] = str(row.get(col_taller, '')).strip()
                    
                    # Armar vehículo homologado
                    v_info = str(row.get('Vehiculo_Info', '')).strip()
                    partes = v_info.split(' | ')
                    v_auto = partes[0].strip() if len(partes) > 0 else v_info
                    v_ano = partes[1].strip() if len(partes) > 1 else ""
                    v_vin = str(row.get(col_vin, '')).strip() if col_vin in row else ""
                    vehiculo_homologado = " | ".join([p for p in [v_auto, v_ano, v_vin] if p and p not in ['NAN', 'NONE']])
                    cambios_a_guardar[k]['compra_vehiculo'] = vehiculo_homologado

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
                    if guia_actual != orig['guia']:
                        cambios_a_guardar.setdefault(k, {})['guia'] = guia_actual
                        if guia_actual not in ['', 'nan', 'None', 'NAN']:
                            cambios_bd_compras.setdefault(k, {})['recibido'] = 'SI'

        if 'df_editado_rec' in locals() and not df_editado_rec.empty:
            for _, row in df_editado_rec.iterrows():
                k = generar_llave(row.get(col_id, ''), row.get(col_desc, ''))
                orig = originales.get(k, {'comentario': '', 'paqueteria': '', 'guia': '', 'estatus_db': ''})
                
                comentario_actual = str(row.get(col_comentarios, '')).strip()
                paq_actual = str(row.get(col_paqueteria, '')).strip()
                guia_actual = str(row.get(col_guia, '')).strip()
                guia_retorno_nueva = str(row.get('Guia_Retorno', '')).strip()
                en_retorno_chk = bool(row.get('En_Retorno', False))
                
                if comentario_actual != orig['comentario']: cambios_a_guardar.setdefault(k, {})['comentario'] = comentario_actual
                if paq_actual != orig['paqueteria']: cambios_a_guardar.setdefault(k, {})['paqueteria'] = paq_actual
                
                # Si escribiste una Guía Retorno nueva o cambiaste la columna Guía o marcaste la casilla En Retorno:
                if guia_retorno_nueva not in ['', 'nan', 'None', 'NAN']:
                    cambios_a_guardar.setdefault(k, {})['guia'] = guia_retorno_nueva
                    cambios_a_guardar[k]['estatus'] = 'EN TRANSITO (RECOLECCIÓN)'
                    cambios_a_guardar[k]['estatus_envio'] = 'Recolección en Tránsito'
                    cambios_a_guardar[k]['fecha_envio'] = fecha_hoy_sistema
                elif guia_actual != orig['guia'] and guia_actual not in ['', 'nan', 'None', 'NAN']:
                    cambios_a_guardar.setdefault(k, {})['guia'] = guia_actual
                    cambios_a_guardar[k]['estatus'] = 'EN TRANSITO (RECOLECCIÓN)'
                    cambios_a_guardar[k]['estatus_envio'] = 'Recolección en Tránsito'
                    cambios_a_guardar[k]['fecha_envio'] = fecha_hoy_sistema
                elif en_retorno_chk and orig['estatus_db'] != 'EN TRANSITO (RECOLECCIÓN)':
                    cambios_a_guardar.setdefault(k, {})['estatus'] = 'EN TRANSITO (RECOLECCIÓN)'
                    cambios_a_guardar[k]['estatus_envio'] = 'Recolección en Tránsito'

        if not df_editado_cobro.empty:
            for _, row in df_editado_cobro.iterrows():
                k = generar_llave(row.get(col_id, ''), row.get(col_desc, ''))
                orig = originales.get(k, {'comentario': '', 'estatus_db': ''})
                if row.get('Marcar Recibido') and cambios_a_guardar.get(k, {}).get('estatus') != "CANCELADO": 
                    cambios_a_guardar.setdefault(k, {})['estatus'] = "RECIBIDO"
                    cambios_a_guardar[k]['fecha_recibido'] = fecha_hoy_sistema
                comentario_actual = str(row.get(col_comentarios, '')).strip()
                if comentario_actual != orig['comentario']: cambios_a_guardar.setdefault(k, {})['comentario'] = comentario_actual

        if 'df_editado_transito_op' in locals() and not df_editado_transito_op.empty:
            for _, row in df_editado_transito_op.iterrows():
                k = generar_llave(row.get(col_id, ''), row.get(col_desc, ''))
                orig = originales.get(k, {'comentario': '', 'paqueteria': '', 'guia': '', 'estatus_db': ''})
                
                if row.get('Marcar Recibido') and cambios_a_guardar.get(k, {}).get('estatus') != "CANCELADO":
                    cambios_a_guardar.setdefault(k, {})['estatus'] = "RECIBIDO"
                    cambios_a_guardar[k]['fecha_recibido'] = fecha_hoy_sistema
                    cambios_bd_compras.setdefault(k, {})['recibido'] = 'SI'
                elif row.get('Marcar Entregado') and cambios_a_guardar.get(k, {}).get('estatus') != "CANCELADO":
                    cambios_a_guardar.setdefault(k, {})['estatus'] = "ENTREGADO"
                    cambios_a_guardar[k]['fecha_recibido'] = fecha_hoy_sistema
                    if not orig.get('guia'):
                        cambios_a_guardar[k]['estatus_envio'] = "Entregado (Ruta Local)"
                    cambios_bd_compras.setdefault(k, {})['recibido'] = 'SI'
                    
                comentario_actual = str(row.get(col_comentarios, '')).strip()
                paq_actual = str(row.get(col_paqueteria, '')).strip() if col_paqueteria else ''
                guia_actual = str(row.get(col_guia, '')).strip() if col_guia else ''
                
                if comentario_actual != orig['comentario']: cambios_a_guardar.setdefault(k, {})['comentario'] = comentario_actual
                if col_paqueteria and paq_actual != orig['paqueteria']: cambios_a_guardar.setdefault(k, {})['paqueteria'] = paq_actual
                if col_guia and guia_actual != orig['guia']:
                    cambios_a_guardar.setdefault(k, {})['guia'] = guia_actual
                    if guia_actual not in ['', 'nan', 'None', 'NAN']:
                        cambios_bd_compras.setdefault(k, {})['recibido'] = 'SI'

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
            c_id_real = buscar_columna(df_editado, ["PEDIDO / SINIESTRO", "SINIESTRO"], ["SINIESTRO"])
            c_desc_real = buscar_columna(df_editado, ["DESCRIPCIÓN", "DESCRIPCION"], ["DESCRIPCI", "REFACCI"])
            
            if c_id_real and c_desc_real:
                for _, row in df_editado.iterrows():
                    k = generar_llave(row.get(c_id_real, ''), row.get(c_desc_real, ''))
                    orig = originales.get(k, {'comentario': '', 'paqueteria': '', 'guia': '', 'estatus_db': '', 'remision_bool': False, 'vencimiento_db': '', 'asignacion_db': ''})
                    
                    if row.get('Cancelar') and 'estatus' not in cambios_a_guardar.get(k, {}): 
                        cambios_a_guardar.setdefault(k, {})['estatus'] = "CANCELADO"
                    elif row.get('Pago_Danos') and 'estatus' not in cambios_a_guardar.get(k, {}): 
                        cambios_a_guardar.setdefault(k, {})['estatus'] = "PAGO A TALLER"
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
                    if guia_actual != orig['guia']:
                        cambios_a_guardar.setdefault(k, {})['guia'] = guia_actual
                        if guia_actual not in ['', 'nan', 'None', 'NAN']:
                            cambios_bd_compras.setdefault(k, {})['recibido'] = 'SI'
                            if 'estatus' not in cambios_a_guardar.get(k, {}) and orig['estatus_db'] in ['EN PROCESAMIENTO', 'POR CONFIRMAR', '']:
                                cambios_a_guardar[k]['estatus'] = 'EN TRANSITO'
                                cambios_a_guardar[k]['fecha_envio'] = fecha_hoy_sistema
                    if venc_actual and venc_actual != orig['vencimiento_db'] and 'vencimiento' not in cambios_a_guardar.get(k, {}): cambios_a_guardar.setdefault(k, {})['vencimiento'] = venc_actual
                    if asig_actual and asig_actual != orig['asignacion_db']: cambios_a_guardar.setdefault(k, {})['asignacion'] = asig_actual
                    
                    prov_asignado = str(row.get('Proveedor', '')).strip()
                    if prov_asignado != '' and cambios_a_guardar.get(k, {}).get('estatus', orig['estatus_db']) != "CANCELADO":
                        cambios_a_guardar.setdefault(k, {})['crear_compra'] = True
                        cambios_a_guardar[k]['compra_prov'] = prov_asignado
                        cambios_a_guardar[k]['compra_costo'] = str(row.get('Costo Compra', '0')).strip()
                        cambios_a_guardar[k]['compra_taller'] = str(row.get(col_taller, '')).strip()
                        
                        v_info = str(row.get('Vehiculo_Info', '')).strip()
                        partes = v_info.split(' | ')
                        v_auto = partes[0].strip() if len(partes) > 0 else v_info
                        v_ano = partes[1].strip() if len(partes) > 1 else ""
                        v_vin = str(row.get(col_vin, '')).strip() if col_vin in row else ""
                        partes_limpias = [v_auto, v_ano, v_vin]
                        vehiculo_homologado = " | ".join([p for p in partes_limpias if p and p not in ['NAN', 'NONE']])
                        
                        cambios_a_guardar[k]['compra_vehiculo'] = vehiculo_homologado

        if vista_actual == "🛒 Compras":
            df_cap_temp = st.session_state.get('df_cap_edit_temp', pd.DataFrame())
            if not df_cap_temp.empty:
                for _, r_cap in df_cap_temp.iterrows():
                    k_cap = generar_llave(r_cap.get('Siniestro', ''), r_cap.get('Pieza', ''))
                    orig_cap = originales.get(k_cap, {'comentario': ''})
                    
                    obs_cap = str(r_cap.get('Observaciones', '')).strip()
                    if obs_cap not in ['nan', 'None'] and obs_cap != orig_cap.get('comentario', ''):
                        cambios_a_guardar.setdefault(k_cap, {})['comentario'] = obs_cap
                        
                    if r_cap.get('Cancelar') == True:
                        cambios_a_guardar.setdefault(k_cap, {})['estatus'] = "CANCELADO"
                    else:
                        prov_cap = str(r_cap.get('Proveedor', '')).strip().upper()
                        if prov_cap not in ['', 'NONE', 'NAN']:
                            costo_val = r_cap.get('Costo Compra', 0.0)
                            costo_str = str(round(float(costo_val), 2)) if pd.notna(costo_val) else '0'
                            partes_v = [str(r_cap.get('Auto', '')).strip(), str(r_cap.get('Año', '')).strip(), str(r_cap.get('VIN / Serie', '')).strip()]
                            veh_hom = " | ".join([p for p in partes_v if p and p not in ['NAN', 'NONE']])
                            
                            cambios_a_guardar.setdefault(k_cap, {})['crear_compra'] = True
                            cambios_a_guardar[k_cap]['compra_prov'] = prov_cap
                            cambios_a_guardar[k_cap]['compra_costo'] = costo_str
                            cambios_a_guardar[k_cap]['compra_taller'] = str(r_cap.get('Taller', '')).strip()
                            cambios_a_guardar[k_cap]['compra_vehiculo'] = veh_hom

            df_editado_compras = st.session_state.get('df_editado_compras_temp', pd.DataFrame())
            if not df_editado_compras.empty:
                for _, row in df_editado_compras.iterrows():
                    k = generar_llave(row.get('Siniestro', ''), row.get('Descripción Pieza', ''))
                    orig = originales.get(k, {'comentario': ''})
                    obs_comp = str(row.get('Observaciones', '')).strip()
                    if obs_comp not in ['nan', 'None'] and obs_comp != orig.get('comentario', ''):
                        cambios_a_guardar.setdefault(k, {})['comentario'] = obs_comp
                        
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
                                'est_env': headers.index(buscar_columna(headers, ["ESTATUS ENVIO", "ESTATUS ENVÍO", "RASTREO"], ["ESTATUS ENV", "RASTREO"], excluidos=[])) if buscar_columna(headers, ["ESTATUS ENVIO", "ESTATUS ENVÍO", "RASTREO"], ["ESTATUS ENV", "RASTREO"], excluidos=[]) else -1,
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
                                    if 'estatus_envio' in c and mapa_hoja.get('est_env', -1) >= 0: datos_hoja[i][mapa_hoja['est_env']] = c['estatus_envio']
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
                                headers_comp = ['Siniestro', 'Taller', 'Vehículo', 'Descripción Pieza', 'Proveedor', 'Costo Compra', 'Fecha Compra', 'Tiempo Entrega (Días)', 'Recibido', 'Condición Pago', 'Días Crédito', 'Estatus Pago', 'Aseguradora']
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
                            i_rec = get_col_idx('Recibido'); i_cond_pago = get_col_idx('Condición Pago'); i_dias_cred = get_col_idx('Días Crédito'); i_est_pago = get_col_idx('Estatus Pago'); i_aseg = get_col_idx('Aseguradora')
                            
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
                                    if po_prov == 'EBAY':
                                        datos_comp[i][i_tiempo] = '10'; datos_comp[i][i_cond_pago] = 'Pago en Plataforma'; datos_comp[i][i_dias_cred] = '0'
                                    elif po_prov == 'MERCADO LIBRE':
                                        datos_comp[i][i_tiempo] = '5'; datos_comp[i][i_cond_pago] = 'Pago en Plataforma'; datos_comp[i][i_dias_cred] = '0'
                                    if po_costo and po_costo not in ['None', 'nan', '']:
                                        datos_comp[i][i_costo] = po_costo

                                if not eliminar_fila: nuevos_datos_comp.append(datos_comp[i])
                                        
                            fecha_hoy_comp = datetime.datetime.now(tz_mx).strftime('%d/%b/%y')
                            nuevas_filas = []
                            for k, v in cambios_a_guardar.items():
                                if v.get('crear_compra') and k not in llaves_en_compras:
                                    n_row = [""] * len(headers_comp)
                                    # Extraer los datos guardados desde el Panel Operativo
                                    veh_info = str(v.get('compra_vehiculo', '')).strip()
                                    
                                    # Tratar de buscar el año y el VIN original desde df_completo para armar el formato homologado
                                    veh_homologado = veh_info
                                    if not df_completo.empty:
                                        match_row = df_completo[
                                            (df_completo[col_id_univ].astype(str).str.strip().str.upper() == str(k[0]).upper()) & 
                                            (df_completo[col_desc_univ].astype(str).str.strip().str.upper() == str(k[1]).upper())
                                        ]
                                        if not match_row.empty:
                                            r_orig = match_row.iloc[0]
                                            c_m = str(r_orig.get(col_marca_univ, '')).strip().upper()
                                            c_mod = str(r_orig.get(col_modelo_univ, '')).strip().upper()
                                            auto_b = c_mod if c_mod.startswith(c_m) else f"{c_m} {c_mod}".strip()
                                            
                                            col_ano_buscar = next((c for c in df_completo.columns if "AÑO" in str(c).upper() or "ANO" in str(c).upper()), None)
                                            col_vin_buscar = next((c for c in df_completo.columns if "VIN" in str(c).upper() or "SERIE" in str(c).upper()), None)
                                            col_aseg_buscar = next((c for c in df_completo.columns if "ASEGURADORA" in str(c).upper()), None)
                                            
                                            ano_b = str(r_orig.get(col_ano_buscar, '')).replace('.0', '').strip() if col_ano_buscar else ""
                                            vin_b = str(r_orig.get(col_vin_buscar, '')).strip().upper() if col_vin_buscar else ""
                                            aseg_b = str(r_orig.get(col_aseg_buscar, '')).strip().upper() if col_aseg_buscar else ""
                                            
                                            partes_v = [auto_b, ano_b, vin_b]
                                            veh_homologado = " | ".join([p for p in partes_v if p and p not in ['NAN', 'NONE']])
                                            n_row[i_aseg] = aseg_b

                                    n_row[idx_c_sin] = k[0]
                                    n_row[idx_c_desc] = k[1]
                                    n_row[i_tall] = v.get('compra_taller', '')
                                    n_row[i_veh] = veh_homologado
                                    n_row[i_fcomp] = fecha_hoy_comp
                                    n_row[i_rec] = 'NO'
                                    n_row[i_costo] = v.get('compra_costo', '0')
                                    n_row[i_est_pago] = 'Pendiente'
                                    
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
                                                # Normalizar condición de pago a los 5 estatus homologados
                                                cond_raw = str(row_p.get('Condición Pago', '')).strip().upper()
                                                if 'PLAT' in cond_raw: cond_pago_calc = 'Pago en Plataforma'
                                                elif 'CONTRA' in cond_raw: cond_pago_calc = 'Contra Entrega'
                                                elif 'CRED' in cond_raw or 'CRÉD' in cond_raw: cond_pago_calc = 'Crédito'
                                                elif 'ANTICIPADO' in cond_raw or 'PREV' in cond_raw or 'CONTADO' in cond_raw: cond_pago_calc = 'Pago Anticipado'
                                                elif 'ANTIC' in cond_raw: cond_pago_calc = 'Anticipo'
                                                
                                                dias_cred_calc = str(row_p.get('Días Crédito', '0')).strip()
                                                break
                                    if nombre_prov_completo == 'EBAY':
                                        eta_calc = '10'; cond_pago_calc = 'Pago en Plataforma'; dias_cred_calc = '0'
                                    elif nombre_prov_completo == 'MERCADO LIBRE':
                                        eta_calc = '5'; cond_pago_calc = 'Pago en Plataforma'; dias_cred_calc = '0'
                                    n_row[i_prov] = nombre_prov_completo; n_row[i_tiempo] = eta_calc if eta_calc else '0'
                                    n_row[i_cond_pago] = cond_pago_calc; n_row[i_dias_cred] = dias_cred_calc
                                    nuevas_filas.append(n_row)
                            
                            filas_a_escribir = nuevos_datos_comp + nuevas_filas
                            while len(filas_a_escribir) < len(datos_comp_crudos): filas_a_escribir.append([""] * len(headers_comp))
                            # --- EL AJUSTE FINAL: table_range="A1" y clear() ---
                            ws_comp.clear()
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
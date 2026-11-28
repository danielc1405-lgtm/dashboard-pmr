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
        
        /* 1. Reducir al mínimo el margen superior de la aplicación */
        header[data-testid="stHeader"], footer { 
            visibility: hidden !important; 
            display: none !important; 
        }
        .block-container, 
        div[data-testid="stMainBlockContainer"], 
        div[data-testid="stAppViewBlockContainer"] { 
            padding-top: 8.2rem !important; 
            padding-bottom: 1rem !important; 
            padding-left: 1rem !important; 
            padding-right: 1rem !important; 
            max-width: 100% !important; 
            overflow: visible !important; 
        }
        /* Permitir barra de desplazamiento (scroll) visible en contenedores con altura fija (ej. Lista de Tareas) */
        div[data-testid="stVerticalBlock"][style*="height"],
        div[data-testid="stVerticalBlockBorderWrapper"][style*="height"],
        div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > div[data-testid="stVerticalBlock"][style*="height"]) {
            overflow-y: auto !important;
            overflow-x: hidden !important;
            scrollbar-width: thin !important;
            scrollbar-color: #E50914 #141720 !important;
        }
        
        /* 2. Fondo negro puro global y eliminar parpadeo gris en tablas */
        [data-testid="stDataGrid"] { opacity: 1 !important; }
        .st-emotion-cache-1kyxreq { display: none !important; }
        .stApp, div[data-testid="stAppViewContainer"] { 
            transition: none !important; 
            background-color: #000000 !important; 
        }

        /* 3. Encabezado Superior 100% FIJO (Aplica SOLO a la barra con el Logo y el Menú) */
        div[data-testid="stHorizontalBlock"]:has([data-testid="stImage"]):has([data-testid="stRadio"]) {
            position: fixed !important;
            top: 0px !important;
            left: 0.8rem !important;
            right: 0.8rem !important;
            z-index: 999990 !important;
            background-color: #0B0E14 !important;
            padding: 8px 16px !important;
            border-radius: 0px 0px 10px 10px !important;
            border: 1px solid #1F2430 !important;
            border-top: none !important;
            box-shadow: 0px 8px 20px rgba(0, 0, 0, 0.92) !important;
            margin-top: 0px !important;
        }
        
        /* 4. Menú de Navegación (st.radio) en una sola línea */
        div[data-testid="stRadio"] > div[role="radiogroup"] {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            gap: 6px !important;
            overflow-x: auto !important;
            overflow-y: hidden !important;
            padding-bottom: 2px !important;
            scrollbar-width: none !important;
        }
        div[data-testid="stRadio"] > div[role="radiogroup"]::-webkit-scrollbar {
            display: none !important;
        }
        div[data-testid="stRadio"] > div[role="radiogroup"] > label {
            flex-shrink: 0 !important;
            white-space: nowrap !important;
            background-color: #141720 !important;
            padding: 4px 10px !important;
            border-radius: 6px !important;
            border: 1px solid #2B303C !important;
            margin-right: 0px !important;
            cursor: pointer !important;
            transition: all 0.2s ease !important;
        }
        div[data-testid="stRadio"] > div[role="radiogroup"] > label:hover {
            border-color: #E50914 !important;
            background-color: #1F2430 !important;
        }
        div[data-testid="stRadio"] > div[role="radiogroup"] > label:has(input:checked) {
            background-color: #1F2430 !important;
            border-color: #E50914 !important;
        }
        div[data-testid="stRadio"] p {
            font-size: 0.82rem !important;
            white-space: nowrap !important;
            margin: 0 !important;
        }

        /* 5. Rojo vivo en TODOS los botones primarios (Normales, Formularios y Descargas) */
        div.stButton > button,
        div[data-testid="stFormSubmitButton"] > button,
        div[data-testid="stDownloadButton"] > button {
            min-height: 2.4rem !important;
            height: 2.4rem !important;
            padding: 0.2rem 0.6rem !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            white-space: nowrap !important;
        }
        div.stButton > button[kind="primary"],
        div[data-testid="stFormSubmitButton"] > button[kind="primary"],
        div[data-testid="stFormSubmitButton"] > button,
        div[data-testid="stDownloadButton"] > button[kind="primary"] {
            background-color: #E50914 !important;
            border-color: #E50914 !important;
            color: #FFFFFF !important;
            font-weight: 600 !important;
            opacity: 1 !important;
        }
        div.stButton > button[kind="primary"]:hover,
        div[data-testid="stFormSubmitButton"] > button[kind="primary"]:hover,
        div[data-testid="stFormSubmitButton"] > button:hover,
        div[data-testid="stDownloadButton"] > button[kind="primary"]:hover {
            background-color: #B20710 !important;
            border-color: #B20710 !important;
            color: #FFFFFF !important;
        }

        /* 6. Eliminar tonos deslavados en Ventanas Emergentes (Pop-ups), Inputs y TextAreas */
        div[role="dialog"],
        div[data-testid="stDialog"] > div {
            background-color: #05070A !important;
            border: 1px solid #2B303C !important;
            box-shadow: 0px 12px 35px rgba(0, 0, 0, 0.95) !important;
        }
        div[data-baseweb="modal"] > div:first-child,
        div[data-testid="stModal"] > div:first-child {
            background-color: rgba(0, 0, 0, 0.85) !important;
        }
        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] > div,
        div[data-baseweb="textarea"],
        textarea {
            background-color: #0D1017 !important;
            border-color: #2B303C !important;
            color: #FFFFFF !important;
        }

        /* 7. Estilo Global Terminal Matrix */
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
        .matrix-katakana { color: rgba(0, 255, 65, 0.22); font-size: 11px; letter-spacing: 3px; user-select: none; }
        .matrix-cursor {
            display: inline-block; width: 9px; height: 15px; background-color: #00FF41;
            vertical-align: middle; animation: blink_mtx 0.8s infinite;
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

# Auto-login silencioso si la URL recuerda al usuario (evita cierres al reconectar Streamlit Cloud)
if not st.session_state['autenticado'] and 'usr' in st.query_params:
    try:
        usr_url = str(st.query_params['usr']).strip()
        if usr_url:
            doc_auto = init_connection()
            ws_u_auto = doc_auto.worksheet("Usuarios")
            df_u_auto = pd.DataFrame(ws_u_auto.get_all_records())
            match_auto = df_u_auto[df_u_auto['Nombre Completo'].astype(str).str.strip().str.upper() == usr_url.upper()]
            if not match_auto.empty:
                nom_ok = str(match_auto.iloc[0]['Nombre Completo']).strip()
                rol_ok = str(match_auto.iloc[0]['Rol']).strip()
                st.session_state['autenticado'] = True
                st.session_state['usuario_actual'] = nom_ok
                st.session_state['rol_actual'] = rol_ok
                st.session_state['permiso_edicion'] = ("DIONICIO" not in nom_ok.upper())
    except Exception:
        pass

if not st.session_state['autenticado']:
    col_l1, col_l2, col_l3 = st.columns([1.2, 1.6, 1.2])
    with col_l2:
        _, c_logo_mid, _ = st.columns([1, 1.2, 1])
        with c_logo_mid:
            try:
                st.image("logo.png", width=180)
            except Exception:
                pass
        st.markdown("<h2 style='text-align: center; color: #FFFFFF;'>🔐 Acceso PMR Hub AI</h2>", unsafe_allow_html=True)
        with st.form("login_form_pmr"):
            usuario_in = st.text_input("👤 Usuario").strip().lower()
            password_in = st.text_input("🔑 Contraseña", type="password")
            if st.form_submit_button("Entrar", type="primary", use_container_width=True):
                try:
                    doc_l = init_connection()
                    df_u_l = pd.DataFrame(doc_l.worksheet("Usuarios").get_all_records())
                    df_u_l['Usuario'] = df_u_l['Usuario'].astype(str).str.strip().str.lower()
                    df_u_l['Password'] = df_u_l['Password'].astype(str).str.strip()
                    match = df_u_l[(df_u_l['Usuario'] == usuario_in) & (df_u_l['Password'] == password_in)]
                    if not match.empty:
                        nom_u = str(match.iloc[0]['Nombre Completo']).strip()
                        st.session_state['autenticado'] = True
                        st.session_state['usuario_actual'] = nom_u
                        st.session_state['rol_actual'] = str(match.iloc[0]['Rol']).strip()
                        st.session_state['permiso_edicion'] = ("DIONICIO" not in nom_u.upper())
                        st.query_params['usr'] = nom_u
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

# --- FUNCIÓN DE LA VENTANA EMERGENTE (POP-UP CON LANZADOR DE BOTS Y CENTRO DE REPORTERÍA) ---
@st.dialog("🖥️ Cuartel General Flotante PMR", width="large")
def abrir_popup_monitor():
    import html
    import subprocess
    import sys

    tab_bots, tab_reporte = st.tabs(["🤖 Monitor y Lanzador de Bots", "📊 Centro de Reportería"])

    with tab_bots:
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

        if btn_iniciar_pop:
            if bot_sel_pop == "GNP Inpart": archivo_ejecutar = "gnp_inpart.py"
            elif bot_sel_pop == "Multiasistencia": archivo_ejecutar = "sincronizador_multiasistencia.py"
            else: archivo_ejecutar = "motor_rastreo.py"

            arg_modo = "--oculto" if "Oculto" in modo_ext_pop else "--visual"

            with spinner_pop:
                with st.spinner(f"Corriendo {bot_sel_pop} en vivo..."):
                    try:
                        with open("credentials.json", "w", encoding="utf-8") as f:
                            f.write(st.secrets["google_credentials"])

                        pintar_matrix_pop(f"[SISTEMA] Despertando a {bot_sel_pop}...\n", activo=True)
                        subprocess.run([sys.executable, '-m', 'playwright', 'install', 'chromium'], check=False)

                        cmd = [sys.executable, "-u", archivo_ejecutar]
                        if bot_sel_pop != "Paquetexpress (Rastreo)": cmd.append(arg_modo)

                        env_bot = os.environ.copy()
                        env_bot["PYTHONIOENCODING"] = "utf-8"
                        env_bot["PYTHONUNBUFFERED"] = "1"

                        proceso = subprocess.Popen(
                            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, bufsize=1, env=env_bot, encoding="utf-8", errors="replace"
                        )

                        lineas_acumuladas = []
                        for linea_rt in iter(proceso.stdout.readline, ''):
                            if not linea_rt: break
                            lineas_acumuladas.append(linea_rt)
                            pintar_matrix_pop("".join(lineas_acumuladas), activo=True)

                        proceso.stdout.close()
                        returncode = proceso.wait()
                        salida_completa = "".join(lineas_acumuladas).strip()

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

                        if "REPORTES LISTOS PARA COPIAR" in salida_completa:
                            parte_wa = re.split(r"REPORTES LISTOS PARA COPIAR(?: A WHATSAPP)?", salida_completa)[1]
                            for corte in ["🔄 PIEZAS REACTIVADAS", "🟠 CAMBIOS DE PRECIO", "🟡 ALERTAS DE PRECIO", "!!!!!"]:
                                if corte in parte_wa: parte_wa = parte_wa.split(corte)[0]
                            st.session_state['temp_wa_alerts'] = re.sub(r'^[=\s]+', '', parte_wa).strip()
                        elif bot_sel_pop != "Paquetexpress (Rastreo)":
                            st.session_state['temp_wa_alerts'] = "No hubo asignaciones nuevas en esta corrida."

                        marcadores_alerta = ["🔄 PIEZAS REACTIVADAS", "🟠 CAMBIOS DE PRECIO", "🟡 ALERTAS DE PRECIO", "REVISIÓN DE ESTATUS CRÍTICO"]
                        idx_inicio_crit = -1
                        for m_al in marcadores_alerta:
                            pos = salida_completa.find(m_al)
                            if pos != -1 and (idx_inicio_crit == -1 or pos < idx_inicio_crit): idx_inicio_crit = pos

                        if idx_inicio_crit != -1:
                            bloque_crit = salida_completa[idx_inicio_crit:]
                            lineas_crit = [l for l in bloque_crit.splitlines() if set(l.strip()) != {'!'} and "REVISIÓN DE ESTATUS CRÍTICO" not in l]
                            st.session_state['temp_criticos_alerts'] = "\n".join(lineas_crit).strip()
                        elif bot_sel_pop != "Paquetexpress (Rastreo)":
                            st.session_state['temp_criticos_alerts'] = "✅ Sin alertas críticas ni partidas vencidas."

                        salida_tecnica = salida_completa[:idx_inicio_crit] if idx_inicio_crit != -1 else salida_completa
                        if "REPORTES LISTOS PARA COPIAR" in salida_tecnica:
                            salida_tecnica = re.split(r"=+\s*\n\s*📱?\s*REPORTES LISTOS PARA COPIAR", salida_tecnica)[0]

                        st.session_state['temp_bot_log'] = salida_tecnica.strip()
                        st.session_state['temp_bot_status'] = f"✅ {bot_sel_pop} finalizado." if returncode == 0 else f"⚠️ {bot_sel_pop} terminó con advertencias."
                        st.cache_data.clear()

                    except Exception as e: st.error(f"Error al lanzar el bot: {e}")
                    finally:
                        if os.path.exists("credentials.json"): os.remove("credentials.json")

        pintar_matrix_pop(st.session_state.get('temp_bot_log', ''), activo=False)

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

    # =========================================================================
    # PESTAÑA 2: CENTRO DE REPORTERÍA (CON CALENDARIO DE INICIO Y FIN)
    # =========================================================================
    with tab_reporte:
        import io
        if 'reporte_activo_popup' not in st.session_state:
            st.session_state['reporte_activo_popup'] = "Informe de Tiempos y SLA por Plaza (Auditoría BBVA)"

        tz_mx_cal = datetime.timezone(datetime.timedelta(hours=-6))
        hoy_cal_date = datetime.datetime.now(tz_mx_cal).date()
        if st.session_state.get('_ultimo_dia_rep_pop') != hoy_cal_date:
            st.session_state['_ultimo_dia_rep_pop'] = hoy_cal_date
            st.session_state.pop('cal_fin_rep_pop', None)

        with st.container(border=True):
            st.markdown("**1. Lanzador de Reportes Ejecutivos**")
            c_sel_rep, c_aseg_rep, c_ini_rep, c_fin_rep, c_btn_rep = st.columns([2.2, 0.8, 1.0, 1.0, 1.0], vertical_alignment="bottom")
            with c_sel_rep:
                tipo_rep_sel = st.selectbox(
                    "Selecciona el Reporte:",
                    [
                        "Informe de Tiempos y SLA por Plaza (Auditoría BBVA)",
                        "Reporte Operativo",
                        "Reporte de Compras (Pendientes y Por Llegar)",
                        "Reporte de Préstamos del Personal"
                    ],
                    key="sel_tipo_rep_pop"
                )
            with c_aseg_rep:
                aseg_rep_sel = st.selectbox("Aseguradora:", ["TODAS", "MULTI", "GNP"], key="sel_aseg_rep_pop")
            with c_ini_rep:
                fecha_ini_rep = st.date_input("📅 Fecha Inicio:", value=datetime.date(2026, 9, 1), format="DD/MM/YYYY", key="cal_ini_rep_pop")
            with c_fin_rep:
                fecha_fin_rep = st.date_input("📅 Fecha Fin:", value=hoy_cal_date, format="DD/MM/YYYY", key="cal_fin_rep_pop")
            with c_btn_rep:
                if st.button("📊 Ejecutar Reporte", type="primary", use_container_width=True, key="btn_ejecutar_rep_pop"):
                    st.session_state['reporte_activo_popup'] = tipo_rep_sel

        def fetch_seguro_pop(hoja):
            try:
                doc = init_connection()
                datos = doc.worksheet(hoja).get_all_values()
                return pd.DataFrame(datos[1:], columns=[str(h).strip() for h in datos[0]]) if len(datos) > 1 else pd.DataFrame()
            except Exception:
                return pd.DataFrame()

        def get_c_pop(df, nombres, excluidos=[]):
            for c in df.columns:
                c_up = str(c).strip().upper().replace('Í', 'I').replace('Ó', 'O')
                if any(n in c_up for n in nombres) and not any(ex in c_up for ex in excluidos):
                    return c
            return None

        def limpiar_txt_pdf(txt):
            return str(txt).encode('latin-1', 'replace').decode('latin-1')

        def parse_dt_rep_pop(val):
            if pd.isna(val) or str(val).strip() == '': return pd.NaT
            val_str = str(val).lower().replace('-', '/')
            if val_str.replace('.', '', 1).isdigit():
                v_num = float(val_str)
                if v_num > 30000: return pd.to_datetime('1899-12-30') + pd.to_timedelta(v_num, unit='D')
            meses_map = {'ene':'01', 'feb':'02', 'mar':'03', 'abr':'04', 'may':'05', 'jun':'06', 'jul':'07', 'ago':'08', 'sep':'09', 'oct':'10', 'nov':'11', 'dic':'12'}
            for m_es, m_num in meses_map.items():
                if m_es in val_str: val_str = val_str.replace(m_es, m_num); break
            try: return pd.to_datetime(val_str, dayfirst=True, errors='coerce')
            except Exception: return pd.NaT

        def generar_excel_corporativo_pmr(hojas_bloques, titulo_reporte):
            try:
                import xlsxwriter
            except ImportError:
                import subprocess, sys
                subprocess.run([sys.executable, "-m", "pip", "install", "xlsxwriter"], check=False)

            buffer_xl = io.BytesIO()
            with pd.ExcelWriter(buffer_xl, engine='xlsxwriter') as writer:
                wb = writer.book
                f_tit = wb.add_format({'bold': True, 'font_size': 12, 'font_color': '#FFFFFF', 'bg_color': '#0B2240', 'valign': 'vcenter'})
                f_sec = wb.add_format({'bold': True, 'font_size': 10, 'font_color': '#0B2240', 'bg_color': '#D9E1F2', 'border': 1, 'valign': 'vcenter'})
                f_hdr = wb.add_format({'bold': True, 'font_size': 9.5, 'font_color': '#FFFFFF', 'bg_color': '#1F4E78', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
                f_cel = wb.add_format({'font_size': 9, 'border': 1, 'valign': 'vcenter'})
                f_zeb = wb.add_format({'font_size': 9, 'bg_color': '#F2F5F9', 'border': 1, 'valign': 'vcenter'})
                f_mon = wb.add_format({'font_size': 9, 'border': 1, 'num_format': '$ #,##0.00', 'align': 'right', 'valign': 'vcenter'})
                f_mzb = wb.add_format({'font_size': 9, 'bg_color': '#F2F5F9', 'border': 1, 'num_format': '$ #,##0.00', 'align': 'right', 'valign': 'vcenter'})
                f_tlb = wb.add_format({'bold': True, 'font_size': 9.5, 'bg_color': '#D9E1F2', 'border': 1, 'align': 'right'})
                f_tvl = wb.add_format({'bold': True, 'font_size': 9.5, 'bg_color': '#D9E1F2', 'border': 1, 'num_format': '$ #,##0.00', 'align': 'right'})

                for nom_hoja, lista_tablas in hojas_bloques.items():
                    sh_name = re.sub(r'[\\/*?:\[\]]', '', str(nom_hoja))[:31] or "Reporte"
                    ws = wb.add_worksheet(sh_name)
                    writer.sheets[sh_name] = ws
                    max_cols_hoja = max([len(df_t.columns) for _, df_t in lista_tablas if df_t is not None and not df_t.empty] or [6])
                    ws.merge_range(0, 0, 0, max(1, max_cols_hoja - 1), f"  PMR SERVICIOS AUTOMOTRICES — {titulo_reporte.upper()} ({hoy_cal_date.strftime('%d/%m/%Y')})", f_tit)
                    ws.set_row(0, 24)

                    curr_row = 2
                    anchos_max = {}
                    for tit_sec, df_t in lista_tablas:
                        df_c = df_t.fillna("").copy() if (df_t is not None and not df_t.empty) else pd.DataFrame([{"Estado": "Sin registros en este apartado"}])
                        n_r, n_c = df_c.shape
                        ws.merge_range(curr_row, 0, curr_row, max(1, n_c - 1), f"  {tit_sec}", f_sec)
                        ws.set_row(curr_row, 19)
                        curr_row += 1

                        cols_mon = set()
                        ws.set_row(curr_row, 21)
                        for c_i, col_nom in enumerate(df_c.columns):
                            ws.write(curr_row, c_i, str(col_nom), f_hdr)
                            anchos_max[c_i] = max(anchos_max.get(c_i, 10), len(str(col_nom)) + 4)
                            if any(k in str(col_nom).upper() for k in ["PRECIO", "COSTO", "MONTO", "ADEUDADO", "AUTORIZADO", "TOTAL ($)"]):
                                cols_mon.add(c_i)
                        curr_row += 1

                        totales = {}
                        for r_i in range(n_r):
                            es_par = (r_i % 2 == 1)
                            ws.set_row(curr_row, 17)
                            for c_i in range(n_c):
                                val = df_c.iat[r_i, c_i]
                                anchos_max[c_i] = max(anchos_max.get(c_i, 10), len(str(val)) + 3)
                                if c_i in cols_mon:
                                    val_s = str(val).replace('$', '').replace(',', '').strip()
                                    if not val_s or val_s.lower() in ['nan', 'none']:
                                        ws.write(curr_row, c_i, "", f_zeb if es_par else f_cel)
                                    else:
                                        try:
                                            v_num = float(val_s)
                                            ws.write_number(curr_row, c_i, v_num, f_mzb if es_par else f_mon)
                                            totales[c_i] = totales.get(c_i, 0.0) + v_num
                                        except Exception:
                                            ws.write(curr_row, c_i, str(val), f_zeb if es_par else f_cel)
                                else:
                                    ws.write(curr_row, c_i, val if isinstance(val, (int, float)) else str(val), f_zeb if es_par else f_cel)
                            curr_row += 1

                        if totales:
                            ws.set_row(curr_row, 19)
                            for c_i in range(n_c):
                                if c_i in totales:
                                    ws.write_number(curr_row, c_i, totales[c_i], f_tvl)
                                elif c_i == max(0, min(cols_mon) - 1):
                                    ws.write(curr_row, c_i, "TOTAL:", f_tlb)
                                else:
                                    ws.write(curr_row, c_i, "", f_tlb)
                            curr_row += 1
                        curr_row += 2

                    for c_i, w_val in anchos_max.items():
                        ws.set_column(c_i, c_i, min(max(w_val, 12), 42))
            return buffer_xl.getvalue()

        def crear_pdf_tablas_apiladas(titulo_doc, subtitulo_doc, bloques_pdf):
            pdf = FPDF(orientation='L', unit='mm', format='A4')
            pdf.set_auto_page_break(auto=True, margin=10)
            pdf.add_page()
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(0, 7, limpiar_txt_pdf(f"PMR SERVICIOS AUTOMOTRICES - {titulo_doc}"), ln=True, align='C')
            pdf.set_font("Arial", '', 8)
            pdf.cell(0, 5, limpiar_txt_pdf(subtitulo_doc), ln=True, align='C')
            pdf.ln(2)
            for tit_b, df_b, cols_w in bloques_pdf:
                pdf.set_font("Arial", 'B', 9)
                pdf.cell(0, 6, limpiar_txt_pdf(tit_b), ln=True)
                if df_b is None or df_b.empty:
                    pdf.set_font("Arial", 'I', 8)
                    pdf.cell(0, 5, limpiar_txt_pdf("Sin registros en este apartado."), ln=True)
                    pdf.ln(3)
                    continue
                pdf.set_fill_color(0, 51, 102); pdf.set_text_color(255, 255, 255); pdf.set_font("Arial", 'B', 7)
                for h_t, w_t in cols_w:
                    pdf.cell(w_t, 6, limpiar_txt_pdf(h_t[:20]), border=1, fill=True, align='C')
                pdf.ln()
                pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", '', 6.5)
                tot_pdf = {}
                for _, r_b in df_b.iterrows():
                    for h_t, w_t in cols_w:
                        es_dinero = any(k in h_t.upper() for k in ["PRECIO", "COSTO", "MONTO", "ADEUDADO", "AUTORIZADO"])
                        if es_dinero:
                            val_s = str(r_b.get(h_t, '')).replace('$', '').replace(',', '').strip()
                            if not val_s or val_s.lower() in ['nan', 'none']:
                                pdf.cell(w_t, 5, "", border=1, align='R')
                            else:
                                try:
                                    v_f = float(val_s)
                                    tot_pdf[h_t] = tot_pdf.get(h_t, 0.0) + v_f
                                    pdf.cell(w_t, 5, f"${v_f:,.2f}", border=1, align='R')
                                except Exception:
                                    pdf.cell(w_t, 5, "", border=1, align='R')
                        else:
                            pdf.cell(w_t, 5, limpiar_txt_pdf(str(r_b.get(h_t, ''))[:34]), border=1)
                    pdf.ln()
                if tot_pdf:
                    pdf.set_font("Arial", 'B', 7)
                    for h_t, w_t in cols_w:
                        if h_t in tot_pdf:
                            pdf.cell(w_t, 5.5, f"${tot_pdf[h_t]:,.2f}", border=1, align='R')
                        else:
                            pdf.cell(w_t, 5.5, "", border=1)
                    pdf.ln()
                pdf.ln(3)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_f:
                pdf.output(tmp_f.name)
                with open(tmp_f.name, "rb") as f_r: return f_r.read()

        # ---------------------------------------------------------------------
        # 1. REPORTE OPERATIVO
        # ---------------------------------------------------------------------
        if st.session_state['reporte_activo_popup'] == "Reporte Operativo":
            st.markdown("### 📋 Reporte Operativo: Pedidos en Proceso")
            df_rep_u = fetch_seguro_pop("BD_UNIFICADA")
            df_rep_c = fetch_seguro_pop("BD_COMPRAS")
            if not df_rep_u.empty:
                c_id, c_cdr = get_c_pop(df_rep_u, ["SINIESTRO", "PEDIDO"]), get_c_pop(df_rep_u, ["TALLER", "CDR"])
                c_marca, c_modelo = get_c_pop(df_rep_u, ["MARCA"]), get_c_pop(df_rep_u, ["MODELO"])
                c_ano, c_pieza = get_c_pop(df_rep_u, ["AÑO", "ANO"]), get_c_pop(df_rep_u, ["DESCRIPCI", "REFACCI"])
                c_precio_v = get_c_pop(df_rep_u, ["PRECIO", "COSTO"])
                c_guia, c_rastreo = get_c_pop(df_rep_u, ["GUIA"], excluidos=["RET", "DEV"]), get_c_pop(df_rep_u, ["ESTATUS ENV", "RASTREO"])
                c_venc, c_est = get_c_pop(df_rep_u, ["VENCIMIENTO", "PROMESA"]), get_c_pop(df_rep_u, ["ESTATUS", "STATUS"], excluidos=["ENV", "PAGO"])
                c_aseg, c_obs = get_c_pop(df_rep_u, ["ASEGURADORA"]), get_c_pop(df_rep_u, ["COMENTARIO", "OBSERVACION"])

                def limpiar_dinero_op(val):
                    s = str(val).replace('$', '').replace(',', '').replace('\\', '').strip()
                    if not s or s.lower() in ['nan', 'none', '-']:
                        return None
                    try:
                        return float(s)
                    except Exception:
                        return None

                estatus_excluir = ["CANCELADO", "RECIBIDO", "FACTURADO", "REEMBOLSADO", "PÉRDIDA TOTAL", "PAGO DE DAÑOS", "PERDIDA TOTAL"]
                df_rep = df_rep_u[~df_rep_u[c_est].astype(str).str.upper().isin(estatus_excluir)].copy()

                dict_prov_rep = {}
                dict_costo_rep = {}
                if not df_rep_c.empty:
                    cc_sin = get_c_pop(df_rep_c, ["SINIESTRO", "PEDIDO"])
                    cc_pz = get_c_pop(df_rep_c, ["DESCRIPCI", "PIEZA"])
                    cc_pr = get_c_pop(df_rep_c, ["PROVEEDOR"])
                    cc_cos = get_c_pop(df_rep_c, ["COSTO COMPRA", "COSTO", "PRECIO"])
                    if cc_sin and cc_pz:
                        for _, rc in df_rep_c.iterrows():
                            sv = str(rc.get(cc_sin, '')).strip().upper().removesuffix('.0')
                            pv = ' '.join(str(rc.get(cc_pz, '')).strip().upper().split())
                            llave_rc = f"{sv}_{pv}"
                            if cc_pr:
                                pr_val = str(rc.get(cc_pr, '')).strip()
                                if pr_val and pr_val.lower() not in ['nan', 'none']:
                                    dict_prov_rep[llave_rc] = pr_val
                            if cc_cos:
                                cos_num = limpiar_dinero_op(rc.get(cc_cos, ''))
                                if cos_num is not None and cos_num > 0:
                                    dict_costo_rep[llave_rc] = cos_num

                df_rep['_llave_op'] = df_rep.apply(lambda r: f"{str(r.get(c_id,'')).strip().upper().removesuffix('.0')}_{' '.join(str(r.get(c_pieza,'')).strip().upper().split())}", axis=1)
                df_rep['PRECIO VENTA'] = df_rep[c_precio_v].apply(limpiar_dinero_op) if c_precio_v else None
                df_rep['PROVEEDOR'] = df_rep['_llave_op'].map(dict_prov_rep).fillna("")
                df_rep['PRECIO COMPRA'] = df_rep['_llave_op'].map(dict_costo_rep)
                df_rep['COMPAÑÍA'] = df_rep[c_aseg].astype(str).str.upper().apply(lambda x: "GNP" if "GNP" in x else "MULTI") if c_aseg else "MULTI"
                if aseg_rep_sel != "TODAS":
                    df_rep = df_rep[df_rep['COMPAÑÍA'] == aseg_rep_sel].copy()

                df_rep.rename(columns={c_id: 'SINIESTRO/PEDIDO', c_cdr: 'CDR', c_marca: 'MARCA', c_modelo: 'MODELO', c_ano: 'AÑO', c_pieza: 'PIEZA', c_guia: 'GUÍA', c_rastreo: 'ESTATUS GUÍA', c_venc: 'FECHA VENCIMIENTO', c_est: 'ESTATUS', c_obs: 'OBSERVACIONES'}, inplace=True)
                cols_op = ['COMPAÑÍA', 'ESTATUS', 'SINIESTRO/PEDIDO', 'CDR', 'MARCA', 'MODELO', 'AÑO', 'PIEZA', 'PRECIO VENTA', 'PROVEEDOR', 'PRECIO COMPRA', 'GUÍA', 'ESTATUS GUÍA', 'FECHA VENCIMIENTO', 'OBSERVACIONES']
                for col in cols_op:
                    if col not in df_rep.columns: df_rep[col] = ""
                df_rep = df_rep[cols_op].sort_values(by=['COMPAÑÍA', 'ESTATUS'])
                st.dataframe(
                    df_rep,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "PRECIO VENTA": st.column_config.NumberColumn("PRECIO VENTA", format="$ %.2f"),
                        "PRECIO COMPRA": st.column_config.NumberColumn("PRECIO COMPRA", format="$ %.2f")
                    }
                )

                b_pdf = crear_pdf_tablas_apiladas(
                    "REPORTE OPERATIVO",
                    f"Emisión: {hoy_cal_date.strftime('%d/%m/%Y')} | Partidas: {len(df_rep)}",
                    [("PEDIDOS ACTIVOS EN PROCESO", df_rep, [
                        ('COMPAÑÍA', 14), ('ESTATUS', 24), ('SINIESTRO/PEDIDO', 23), ('CDR', 38),
                        ('MODELO', 26), ('PIEZA', 44), ('PRECIO VENTA', 22), ('PROVEEDOR', 34),
                        ('PRECIO COMPRA', 22), ('FECHA VENCIMIENTO', 22)
                    ])]
                )
                b_xlsx = generar_excel_corporativo_pmr({"Reporte_Operativo": [("1. PEDIDOS EN PROCESO", df_rep)]}, "Reporte Operativo")
                c1, c2 = st.columns(2)
                c1.download_button("🖨️ Descargar Reporte Operativo (PDF)", data=b_pdf, file_name=f"Reporte_Operativo_PMR_{hoy_cal_date.strftime('%d%m%Y')}.pdf", mime="application/pdf", type="primary", use_container_width=True)
                c2.download_button("📊 Descargar Reporte Operativo (.XLSX)", data=b_xlsx, file_name=f"Reporte_Operativo_PMR_{hoy_cal_date.strftime('%d%m%Y')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

        # ---------------------------------------------------------------------
        # 2. REPORTE DE COMPRAS (2 TABLAS APILADAS EN 1 SOLA VISTA / HOJA)
        # ---------------------------------------------------------------------
        elif st.session_state['reporte_activo_popup'] == "Reporte de Compras (Pendientes y Por Llegar)":
            st.markdown("### 🛒 Reporte Ejecutivo de Compras (1 Sola Vista Consolidada)")
            df_rc_u = fetch_seguro_pop("BD_UNIFICADA")
            df_rc_c = fetch_seguro_pop("BD_COMPRAS")
            if not df_rc_u.empty:
                c_id_u, c_tal_u = get_c_pop(df_rc_u, ["SINIESTRO", "PEDIDO"]), get_c_pop(df_rc_u, ["TALLER", "CDR"])
                c_mar_u, c_mod_u = get_c_pop(df_rc_u, ["MARCA"]), get_c_pop(df_rc_u, ["MODELO"])
                c_ano_u, c_vin_u = get_c_pop(df_rc_u, ["AÑO", "ANO"]), get_c_pop(df_rc_u, ["VIN", "SERIE"])
                c_pza_u, c_pre_u = get_c_pop(df_rc_u, ["DESCRIPCI", "REFACCI"]), get_c_pop(df_rc_u, ["PRECIO", "COSTO"])
                c_est_u, c_ase_u = get_c_pop(df_rc_u, ["ESTATUS", "STATUS"], excluidos=["ENV", "PAGO"]), get_c_pop(df_rc_u, ["ASEGURADORA"])
                c_obs_u, c_gui_u, c_rem_u = get_c_pop(df_rc_u, ["COMENTARIO", "OBSERVACION"]), get_c_pop(df_rc_u, ["GUIA"], excluidos=["RET", "DEV"]), get_c_pop(df_rc_u, ["REMISION"])

                def norm_k_rc(s, d):
                    return f"{str(s).strip().upper().removesuffix('.0')}_{' '.join(str(d).strip().upper().split())}"

                llaves_compradas_rc = set()
                if not df_rc_c.empty:
                    cc_s, cc_d, cc_p = get_c_pop(df_rc_c, ["SINIESTRO", "PEDIDO"]), get_c_pop(df_rc_c, ["DESCRIPCI", "PIEZA"]), get_c_pop(df_rc_c, ["PROVEEDOR"])
                    if cc_s and cc_d:
                        for _, r_c in df_rc_c.iterrows():
                            if str(r_c.get(cc_s, '')).strip() and str(r_c.get(cc_p, '')).strip() not in ['', 'nan', 'None', 'NAN']:
                                llaves_compradas_rc.add(norm_k_rc(r_c.get(cc_s, ''), r_c.get(cc_d, '')))

                df_en_proc_rc = df_rc_u[df_rc_u[c_est_u].astype(str).str.strip().str.upper() == "EN PROCESAMIENTO"].copy() if c_est_u else pd.DataFrame()
                if not df_en_proc_rc.empty:
                    df_en_proc_rc['_k_rc'] = df_en_proc_rc.apply(lambda r: norm_k_rc(r.get(c_id_u, ''), r.get(c_pza_u, '')), axis=1)
                    df_pend_comp_rep = df_en_proc_rc[~df_en_proc_rc['_k_rc'].isin(llaves_compradas_rc)].copy()
                else:
                    df_pend_comp_rep = pd.DataFrame()

                if not df_pend_comp_rep.empty:
                    df_pend_comp_rep['Compañía'] = df_pend_comp_rep[c_ase_u].astype(str).str.upper().apply(lambda x: "GNP" if "GNP" in x else "MULTI") if c_ase_u else "MULTI"
                    if aseg_rep_sel != "TODAS":
                        df_pend_comp_rep = df_pend_comp_rep[df_pend_comp_rep['Compañía'] == aseg_rep_sel].copy()
                    df_pend_out = pd.DataFrame({
                        'Compañía': df_pend_comp_rep['Compañía'],
                        'Siniestro': df_pend_comp_rep[c_id_u].astype(str).str.strip(),
                        'Taller (CDR)': df_pend_comp_rep[c_tal_u].astype(str).str.strip(),
                        'Vehículo': (df_pend_comp_rep[c_mar_u].astype(str).str.strip() + " " + df_pend_comp_rep[c_mod_u].astype(str).str.strip()).str.strip(),
                        'Año': df_pend_comp_rep[c_ano_u].astype(str).str.replace('.0', '', regex=False).str.strip() if c_ano_u else "",
                        'VIN / Serie': df_pend_comp_rep[c_vin_u].astype(str).str.strip() if c_vin_u else "",
                        'Pieza': df_pend_comp_rep[c_pza_u].astype(str).str.strip(),
                        'Precio Autorizado ($)': pd.to_numeric(df_pend_comp_rep[c_pre_u].astype(str).str.replace('$', '').str.replace(',', '').str.strip(), errors='coerce').fillna(0.0) if c_pre_u else 0.0,
                        'Observaciones': df_pend_comp_rep[c_obs_u].astype(str).replace(['nan', 'None'], '').str.strip() if c_obs_u else ""
                    })
                else:
                    df_pend_out = pd.DataFrame(columns=['Compañía', 'Siniestro', 'Taller (CDR)', 'Vehículo', 'Año', 'VIN / Serie', 'Pieza', 'Precio Autorizado ($)', 'Observaciones'])

                df_lleg_out = pd.DataFrame(columns=['Siniestro', 'Taller (CDR)', 'Vehículo', 'Pieza', 'Proveedor', 'Costo Compra ($)', 'Fecha Compra', 'Llegada Estimada', 'Condición Pago', 'Estatus Pago', 'Observaciones'])
                if not df_rc_c.empty:
                    df_c_work = df_rc_c.copy()
                    df_c_work['Recibido_Bool'] = df_c_work.get('Recibido', pd.Series(['NO']*len(df_c_work))).astype(str).str.strip().str.upper().isin(['TRUE', 'SI', '1', 'YES', 'V', 'X'])
                    llaves_fin_u, llaves_rem_u, dict_obs_u = set(), set(), {}
                    for _, ru in df_rc_u.iterrows():
                        ku = norm_k_rc(ru.get(c_id_u, ''), ru.get(c_pza_u, ''))
                        est_u_v = str(ru.get(c_est_u, '')).strip().upper() if c_est_u else ''
                        if c_obs_u and str(ru.get(c_obs_u, '')).strip() not in ['', 'nan', 'None']: dict_obs_u[ku] = str(ru.get(c_obs_u, '')).strip()
                        if est_u_v in ['ENTREGADO', 'RECIBIDO', 'FACTURADO', 'CANCELADO', 'PÉRDIDA TOTAL', 'PAGO DE DAÑOS'] or (c_gui_u and str(ru.get(c_gui_u, '')).strip() not in ['', 'nan', 'None', 'NAN']):
                            llaves_fin_u.add(ku)
                        if (c_rem_u and str(ru.get(c_rem_u, '')).strip() not in ['', 'nan', 'None', 'NAN']) or est_u_v == 'EN TRANSITO':
                            llaves_rem_u.add(ku)

                    df_c_work['_k_rc'] = df_c_work.apply(lambda r: norm_k_rc(r.get('Siniestro', ''), r.get('Descripción Pieza', '')), axis=1)
                    es_inv_c = df_c_work.get('Proveedor', pd.Series(['']*len(df_c_work))).astype(str).str.strip().str.upper() == 'INVENTARIO'
                    df_c_work.loc[df_c_work['_k_rc'].isin(llaves_fin_u) | (es_inv_c & df_c_work['_k_rc'].isin(llaves_rem_u)), 'Recibido_Bool'] = True
                    df_c_act = df_c_work[df_c_work['Recibido_Bool'] == False].copy()
                    if aseg_rep_sel != "TODAS" and 'Aseguradora' in df_c_act.columns:
                        df_c_act = df_c_act[df_c_act['Aseguradora'].astype(str).str.upper().str.contains(aseg_rep_sel, na=False)].copy()

                    if not df_c_act.empty:
                        f_dt = df_c_act['Fecha Compra'].apply(parse_dt_rep_pop)
                        eta_n = pd.to_numeric(df_c_act.get('Tiempo Entrega (Días)', 0), errors='coerce').fillna(0)
                        df_lleg_out = pd.DataFrame({
                            'Siniestro': df_c_act['Siniestro'].astype(str).str.strip(),
                            'Taller (CDR)': df_c_act['Taller'].astype(str).str.strip(),
                            'Vehículo': df_c_act.get('Vehículo', pd.Series(['']*len(df_c_act))).astype(str).str.strip(),
                            'Pieza': df_c_act['Descripción Pieza'].astype(str).str.strip(),
                            'Proveedor': df_c_act['Proveedor'].astype(str).str.strip(),
                            'Costo Compra ($)': pd.to_numeric(df_c_act['Costo Compra'].astype(str).str.replace('$', '').str.replace(',', '').str.strip(), errors='coerce').fillna(0.0),
                            'Fecha Compra': df_c_act['Fecha Compra'].astype(str).str.strip(),
                            'Llegada Estimada': (f_dt + pd.to_timedelta(eta_n, unit='d')).dt.strftime('%d/%m/%Y').fillna('-'),
                            'Condición Pago': df_c_act.get('Condición Pago', pd.Series(['']*len(df_c_act))).astype(str).str.strip(),
                            'Estatus Pago': df_c_act.get('Estatus Pago', pd.Series(['']*len(df_c_act))).astype(str).str.strip(),
                            'Observaciones': df_c_act['_k_rc'].map(dict_obs_u).fillna("")
                        })

                kc1, kc2, kc3, kc4 = st.columns(4)
                kc1.metric("🚨 1. Pendientes de Compra", f"{len(df_pend_out)} pzas")
                kc2.metric("💰 Presupuesto Autorizado", f"${df_pend_out['Precio Autorizado ($)'].sum():,.2f}")
                kc3.metric("📦 2. Compras por Llegar", f"{len(df_lleg_out)} pzas")
                kc4.metric("💵 Total Costo Compras", f"${df_lleg_out['Costo Compra ($)'].sum():,.2f}")

                st.markdown("#### 🚨 1. Piezas Pendientes de Compra (Urgente)")
                st.dataframe(df_pend_out, use_container_width=True, hide_index=True)
                st.markdown("#### 📦 2. Compras por Llegar y Estatus de Pago")
                st.dataframe(df_lleg_out, use_container_width=True, hide_index=True)

                b_pdf_c = crear_pdf_tablas_apiladas(
                    "REPORTE CONSOLIDADO DE COMPRAS",
                    f"Fecha: {hoy_cal_date.strftime('%d/%m/%Y')} | Pendientes: {len(df_pend_out)} (${df_pend_out['Precio Autorizado ($)'].sum():,.2f}) | Por Llegar: {len(df_lleg_out)} (${df_lleg_out['Costo Compra ($)'].sum():,.2f})",
                    [
                        ("1. PIEZAS PENDIENTES DE COMPRA (URGENTE)", df_pend_out, [('Compañía', 16), ('Siniestro', 25), ('Taller (CDR)', 48), ('Vehículo', 40), ('Año', 14), ('VIN / Serie', 36), ('Pieza', 62), ('Precio Autorizado ($)', 28)]),
                        ("2. COMPRAS POR LLEGAR Y ESTATUS DE PAGO", df_lleg_out, [('Siniestro', 25), ('Taller (CDR)', 45), ('Pieza', 58), ('Proveedor', 44), ('Costo Compra ($)', 25), ('Llegada Estimada', 25), ('Condición Pago', 26), ('Estatus Pago', 22)])
                    ]
                )
                b_xlsx_c = generar_excel_corporativo_pmr(
                    {"Reporte_Compras": [("1. PIEZAS PENDIENTES DE COMPRA (URGENTE)", df_pend_out), ("2. COMPRAS POR LLEGAR Y ESTATUS DE PAGO", df_lleg_out)]},
                    "Reporte Consolidado de Compras"
                )
                dc1, dc2 = st.columns(2)
                dc1.download_button("🖨️ Descargar Reporte de Compras (PDF - 1 Vista)", data=b_pdf_c, file_name=f"Reporte_Compras_PMR_{hoy_cal_date.strftime('%d%m%Y')}.pdf", mime="application/pdf", type="primary", use_container_width=True)
                dc2.download_button("📊 Descargar Reporte de Compras (.XLSX - 1 Hoja Consolidada)", data=b_xlsx_c, file_name=f"Reporte_Compras_PMR_{hoy_cal_date.strftime('%d%m%Y')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

        # ---------------------------------------------------------------------
        # 3. REPORTE DE PRÉSTAMOS DEL PERSONAL (2 TABLAS EN 1 HOJA + HISTÓRICO OPCIONAL)
        # ---------------------------------------------------------------------
        elif st.session_state['reporte_activo_popup'] == "Reporte de Préstamos del Personal":
            st.markdown("### 💸 Reporte Ejecutivo de Préstamos del Personal")
            incluir_hist_pagados = st.checkbox("☑️ Incluir historial de préstamos ya liquidados en una 2da hoja de Excel", value=False, key="chk_hist_prest_pop")
            df_gp = fetch_seguro_pop("GASTOS_EMPLEADOS")
            if not df_gp.empty:
                df_gp['Monto ($)'] = pd.to_numeric(df_gp.get('Monto', pd.Series([0]*len(df_gp))).astype(str).str.replace('$', '').str.replace(',', '').str.strip(), errors='coerce').fillna(0.0)
                df_gp_pend = df_gp[df_gp.get('Estado', pd.Series(['']*len(df_gp))).astype(str).str.upper() == 'PENDIENTE REEMBOLSO'].copy()
                df_gp_pag = df_gp[df_gp.get('Estado', pd.Series(['']*len(df_gp))).astype(str).str.upper() != 'PENDIENTE REEMBOLSO'].copy()

                if not df_gp_pend.empty:
                    df_res_emp = df_gp_pend.groupby('Empleado', as_index=False).agg(
                        Gastos_Pendientes=('Monto ($)', 'count'),
                        Total_Adeudado=('Monto ($)', 'sum')
                    ).sort_values(by='Total_Adeudado', ascending=False).rename(columns={'Gastos_Pendientes': 'Gastos Pendientes (Cant.)', 'Total_Adeudado': 'Total Adeudado ($)'})
                else:
                    df_res_emp = pd.DataFrame(columns=['Empleado', 'Gastos Pendientes (Cant.)', 'Total Adeudado ($)'])

                df_det_pend = pd.DataFrame({
                    'Fecha': df_gp_pend.get('Fecha', pd.Series(dtype=str)),
                    'Empleado': df_gp_pend.get('Empleado', pd.Series(dtype=str)),
                    'Método de Pago': df_gp_pend.get('Método de Pago', pd.Series(dtype=str)),
                    'Proveedor / Negocio': df_gp_pend.get('Proveedor', pd.Series(dtype=str)),
                    'Siniestro': df_gp_pend.get('Siniestro', pd.Series(dtype=str)),
                    'Refacción / Concepto': df_gp_pend.get('Refacción', pd.Series(dtype=str)),
                    'Monto ($)': df_gp_pend.get('Monto ($)', pd.Series(dtype=float))
                })

                kp1, kp2, kp3 = st.columns(3)
                kp1.metric("💰 Gran Total Adeudado PMR", f"${df_det_pend['Monto ($)'].sum():,.2f}" if not df_det_pend.empty else "$0.00")
                kp2.metric("👤 Empleados con Saldo", f"{len(df_res_emp)}")
                kp3.metric("🧾 Gastos por Reembolsar", f"{len(df_det_pend)}")

                st.markdown("#### 👤 1. Resumen de Saldo Adeudado por Empleado")
                st.dataframe(df_res_emp, use_container_width=True, hide_index=True)
                st.markdown("#### 🧾 2. Desglose de Gastos Pendientes de Reembolso")
                st.dataframe(df_det_pend, use_container_width=True, hide_index=True)

                b_pdf_p = crear_pdf_tablas_apiladas(
                    "ESTADO DE CUENTA PRÉSTAMOS DEL PERSONAL",
                    f"Fecha de corte: {hoy_cal_date.strftime('%d/%m/%Y')} | Total Adeudado: ${df_det_pend['Monto ($)'].sum():,.2f}",
                    [
                        ("1. RESUMEN DE SALDO ADEUDADO POR EMPLEADO", df_res_emp, [('Empleado', 70), ('Gastos Pendientes (Cant.)', 50), ('Total Adeudado ($)', 55)]),
                        ("2. DESGLOSE DE GASTOS PENDIENTES DE REEMBOLSO", df_det_pend, [('Fecha', 25), ('Empleado', 32), ('Método de Pago', 32), ('Proveedor / Negocio', 52), ('Siniestro', 28), ('Refacción / Concepto', 72), ('Monto ($)', 28)])
                    ]
                )
                hojas_prest_xlsx = {
                    "Prestamos_Pendientes": [
                        ("1. RESUMEN DE SALDO ADEUDADO POR EMPLEADO", df_res_emp),
                        ("2. DESGLOSE DE GASTOS PENDIENTES DE REEMBOLSO", df_det_pend)
                    ]
                }
                if incluir_hist_pagados and not df_gp_pag.empty:
                    hojas_prest_xlsx["Historial_Liquidados"] = [("HISTORIAL DE PRÉSTAMOS LIQUIDADOS", df_gp_pag[['Fecha', 'Empleado', 'Método de Pago', 'Proveedor', 'Siniestro', 'Refacción', 'Monto ($)', 'Estado']])]

                b_xlsx_p = generar_excel_corporativo_pmr(hojas_prest_xlsx, "Estado de Cuenta Préstamos del Personal")
                dp1, dp2 = st.columns(2)
                dp1.download_button("🖨️ Descargar Préstamos (PDF - 1 Hoja)", data=b_pdf_p, file_name=f"Reporte_Prestamos_PMR_{hoy_cal_date.strftime('%d%m%Y')}.pdf", mime="application/pdf", type="primary", use_container_width=True)
                dp2.download_button("📊 Descargar Préstamos (.XLSX - 1 Hoja Consolidada)", data=b_xlsx_p, file_name=f"Reporte_Prestamos_PMR_{hoy_cal_date.strftime('%d%m%Y')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
            else:
                st.info("No hay registros en GASTOS_EMPLEADOS.")

        # ---------------------------------------------------------------------
        # 4. INFORME DETALLADO DE TIEMPOS Y SLA POR PLAZA / TALLER / SINIESTRO
        # ---------------------------------------------------------------------
        else:
            rango_str_titulo = f"{fecha_ini_rep.strftime('%d/%m/%Y')} al {fecha_fin_rep.strftime('%d/%m/%Y')}"
            st.markdown(f"### ⏱️ Informe Detallado de Tiempos Logísticos ({rango_str_titulo})")
            df_u_sla, df_h_sla = fetch_seguro_pop("BD_UNIFICADA"), fetch_seguro_pop("BD_HISTORICO")
            df_t_sla, df_r_sla = fetch_seguro_pop("BD_TALLERES"), fetch_seguro_pop("BD_RUTAS")
            if not df_h_sla.empty and 'Siniestro Relacionado' in df_h_sla.columns and 'Pedido / Siniestro' not in df_h_sla.columns:
                df_h_sla.rename(columns={'Siniestro Relacionado': 'Pedido / Siniestro'}, inplace=True)
            df_total_sla = pd.concat([df_u_sla, df_h_sla], ignore_index=True) if not df_h_sla.empty else df_u_sla.copy()

            if not df_total_sla.empty:
                c_sin_s, c_tal_s = get_c_pop(df_total_sla, ["SINIESTRO", "PEDIDO"]), get_c_pop(df_total_sla, ["TALLER", "CDR"])
                c_mar_s, c_mod_s = get_c_pop(df_total_sla, ["MARCA"]), get_c_pop(df_total_sla, ["MODELO", "VEH"])
                c_pza_s, c_can_s = get_c_pop(df_total_sla, ["DESCRIPCI", "REFACCI"]), get_c_pop(df_total_sla, ["CANTIDAD", "CANT"])
                c_est_s, c_ase_s = get_c_pop(df_total_sla, ["ESTATUS", "STATUS"], excluidos=["ENV", "PAGO"]), get_c_pop(df_total_sla, ["ASEGURADORA"])
                c_f_asig, c_f_conf = get_c_pop(df_total_sla, ["ASIGNACI"]), get_c_pop(df_total_sla, ["FECHA CONFI", "CONFIRMACI"])
                c_f_env, c_f_ent, c_f_rec = get_c_pop(df_total_sla, ["FECHA ENV"]), get_c_pop(df_total_sla, ["FECHA ENT", "LLEGADA"]), get_c_pop(df_total_sla, ["FECHA REC"])

                if c_sin_s and c_pza_s:
                    df_total_sla = df_total_sla.drop_duplicates(subset=[c_sin_s, c_pza_s], keep='first').copy()
                df_total_sla['_Cant_Num'] = pd.to_numeric(df_total_sla[c_can_s], errors='coerce').fillna(1).clip(lower=1).astype(int) if (c_can_s and c_can_s in df_total_sla.columns) else 1

                dict_ciudad_t, dict_estado_t = {}, {}
                if not df_t_sla.empty:
                    ct_nom, ct_ciu, ct_est = get_c_pop(df_t_sla, ["TALLER", "CDR"]), get_c_pop(df_t_sla, ["CIUDAD", "MUNICIPIO", "PLAZA"]), get_c_pop(df_t_sla, ["ESTADO"])
                    if ct_nom:
                        for _, rt in df_t_sla.iterrows():
                            kt = str(rt.get(ct_nom, '')).strip().upper()
                            if kt:
                                if ct_ciu: dict_ciudad_t[kt] = str(rt.get(ct_ciu, '')).strip().upper()
                                if ct_est: dict_estado_t[kt] = str(rt.get(ct_est, '')).strip().upper()

                def inferir_plaza(taller_raw):
                    t_up = str(taller_raw).strip().upper()
                    ciu, edo = dict_ciudad_t.get(t_up, ""), dict_estado_t.get(t_up, "")
                    if not ciu:
                        if any(k in t_up for k in ["TORREON", "LAGUNA", "GOMEZ PALACIO"]): ciu, edo = "TORREON", "COAHUILA"
                        elif "SALTILLO" in t_up: ciu, edo = "SALTILLO", "COAHUILA"
                        elif any(k in t_up for k in ["TAMPICO", "MADERO", "ALTAMIRA"]): ciu, edo = "TAMPICO", "TAMAULIPAS"
                        elif any(k in t_up for k in ["POTOSI", "SLP", "VALLES"]): ciu, edo = "SAN LUIS POTOSI", "SAN LUIS POTOSI"
                        elif "MERIDA" in t_up: ciu, edo = "MERIDA", "YUCATAN"
                        elif "AGUASCALIENTES" in t_up: ciu, edo = "AGUASCALIENTES", "AGUASCALIENTES"
                        else: ciu = "MONTERREY"
                    if not edo: edo = "NUEVO LEON" if "MONTERREY" in ciu else "S/D"
                    return pd.Series([ciu, edo])

                df_total_sla[['Plaza_Ciudad', 'Estado_Plaza']] = df_total_sla[c_tal_s].apply(inferir_plaza)
                if c_ase_s and aseg_rep_sel != "TODAS":
                    df_total_sla = df_total_sla[df_total_sla[c_ase_s].astype(str).str.upper().str.contains(aseg_rep_sel, na=False)].copy()

                def safe_apply_dt_s(df_o, c_n):
                    if c_n and c_n in df_o.columns:
                        s = df_o[c_n].iloc[:, 0] if isinstance(df_o[c_n], pd.DataFrame) else df_o[c_n]
                        return s.apply(parse_dt_rep_pop)
                    return pd.Series(pd.NaT, index=df_o.index)

                df_total_sla['DT_Asig'] = safe_apply_dt_s(df_total_sla, c_f_asig)
                df_total_sla['DT_Conf'] = safe_apply_dt_s(df_total_sla, c_f_conf)
                df_total_sla['DT_Env'] = safe_apply_dt_s(df_total_sla, c_f_env)
                df_total_sla['DT_Rec'] = safe_apply_dt_s(df_total_sla, c_f_rec)
                df_total_sla['DT_Ent'] = safe_apply_dt_s(df_total_sla, c_f_ent) if (c_f_ent and c_f_ent != c_f_rec) else df_total_sla['DT_Rec']

                df_total_sla = df_total_sla[df_total_sla['DT_Asig'].notna()].copy()
                dt_ini_f, dt_fin_f = pd.to_datetime(fecha_ini_rep), pd.to_datetime(fecha_fin_rep) + pd.Timedelta(hours=23, minutes=59, seconds=59)
                df_total_sla = df_total_sla[(df_total_sla['DT_Asig'] >= dt_ini_f) & (df_total_sla['DT_Asig'] <= dt_fin_f)].copy()
                if c_est_s:
                    df_total_sla = df_total_sla[~df_total_sla[c_est_s].astype(str).str.upper().isin(["PÉRDIDA TOTAL", "PERDIDA TOTAL", "PAGO DE DAÑOS", "PAGO DE DANOS"])].copy()

                if not df_total_sla.empty:
                    def limp_d(s): return s.where((s >= 0) & (s <= 90), pd.NA)
                    df_total_sla['D_Asig_Conf'] = limp_d((df_total_sla['DT_Conf'] - df_total_sla['DT_Asig']).dt.days)
                    df_total_sla['D_Conf_Env'] = limp_d((df_total_sla['DT_Env'] - df_total_sla['DT_Conf']).dt.days)
                    df_total_sla['D_Env_Ent'] = limp_d((df_total_sla['DT_Ent'] - df_total_sla['DT_Env']).dt.days)
                    df_total_sla['D_Ent_Rec'] = limp_d((df_total_sla['DT_Rec'] - df_total_sla['DT_Ent']).dt.days)

                    es_canc_m = df_total_sla[c_est_s].astype(str).str.upper().str.contains("CANCELAD|REEMBOLS", na=False) if c_est_s else pd.Series(False, index=df_total_sla.index)
                    f_cierre = df_total_sla['DT_Rec'].combine_first(df_total_sla['DT_Ent']).combine_first(df_total_sla['DT_Env'])
                    df_total_sla['D_Ciclo_Total'] = limp_d((f_cierre - df_total_sla['DT_Asig']).dt.days)
                    df_total_sla.loc[es_canc_m, 'D_Ciclo_Total'] = pd.NA

                    df_total_sla['Auditoria_BBVA'] = df_total_sla.apply(lambda r: "🚫 Cancelada (No Surtida)" if ("CANCELAD" in str(r.get(c_est_s,'')).upper() or "REEMBOLS" in str(r.get(c_est_s,'')).upper()) else ("⏳ En Proceso / Sin Fecha Cierre" if pd.isna(r.get('D_Ciclo_Total', pd.NA)) else ("✅ Cumple (0 a 7 días)" if float(r.get('D_Ciclo_Total')) <= 7 else "❌ Excede (> 7 días)")), axis=1)
                    df_total_sla['Cumple_0_7_Dias'] = df_total_sla['Auditoria_BBVA'].apply(lambda x: 1 if "Cumple" in x else (0 if "Excede" in x else pd.NA))

                    cf_est, cf_ciu, cf_aud = st.columns(3)
                    estados_sel = cf_est.multiselect("🗺️ Filtrar Estado:", options=sorted(df_total_sla['Estado_Plaza'].dropna().unique().tolist()), default=[], key="ms_estados_sla_pop")
                    df_sla_view = df_total_sla[df_total_sla['Estado_Plaza'].isin(estados_sel)].copy() if estados_sel else df_total_sla.copy()
                    ciudades_sel = cf_ciu.multiselect("🏙️ Filtrar Ciudad / Plaza:", options=sorted(df_sla_view['Plaza_Ciudad'].dropna().unique().tolist()), default=[], key="ms_ciudades_sla_pop")
                    if ciudades_sel: df_sla_view = df_sla_view[df_sla_view['Plaza_Ciudad'].isin(ciudades_sel)].copy()
                    aud_sel = cf_aud.multiselect("🔍 Filtrar Estatus Auditoría BBVA:", options=sorted(df_sla_view['Auditoria_BBVA'].dropna().unique().tolist()), default=[], key="ms_aud_sla_pop")
                    if aud_sel: df_sla_view = df_sla_view[df_sla_view['Auditoria_BBVA'].isin(aud_sel)].copy()

                    def prom_s(s):
                        sv = pd.to_numeric(s, errors='coerce').dropna()
                        return round(sv.mean(), 1) if not sv.empty else 0.0

                    def resumen_grp_sla(df_in, cols_g):
                        filas = []
                        for keys, grp in df_in.groupby(cols_g, dropna=False):
                            if not isinstance(keys, tuple): keys = (keys,)
                            d_f = {cols_g[i]: keys[i] for i in range(len(cols_g))}
                            tot_p = int(grp['_Cant_Num'].sum())
                            canc_p = int(grp[grp['Auditoria_BBVA'] == "🚫 Cancelada (No Surtida)"]['_Cant_Num'].sum())
                            surt_p = tot_p - canc_p
                            s_7 = pd.to_numeric(grp['Cumple_0_7_Dias'], errors='coerce').dropna()
                            ef_7 = round(s_7.mean() * 100, 1) if not s_7.empty else 0.0
                            d_f.update({
                                'Piezas': tot_p, 'Surtidas': surt_p, 'Canceladas': canc_p,
                                '% Surtido': f"{round((surt_p/tot_p)*100, 1) if tot_p>0 else 0.0}%",
                                '1. Asig ➔ Conf (días)': prom_s(grp['D_Asig_Conf']),
                                '2. Conf ➔ Envío (días)': prom_s(grp['D_Conf_Env']),
                                '3. Envío ➔ Entrega (días)': prom_s(grp['D_Env_Ent']),
                                '4. Entrega ➔ Recibo (días)': prom_s(grp['D_Ent_Rec']),
                                'Ciclo Total (días)': prom_s(grp['D_Ciclo_Total']),
                                '% Ef. 0-7 Días': f"{ef_7}%", '_ef': ef_7
                            })
                            filas.append(d_f)
                        df_o = pd.DataFrame(filas)
                        return df_o.sort_values(by=['Piezas', '_ef'], ascending=[False, True]).drop(columns=['_ef']) if not df_o.empty else df_o

                    df_por_estado = resumen_grp_sla(df_sla_view, ['Estado_Plaza']).rename(columns={'Estado_Plaza': 'Estado'})
                    df_por_ciudad = resumen_grp_sla(df_sla_view, ['Estado_Plaza', 'Plaza_Ciudad']).rename(columns={'Estado_Plaza': 'Estado', 'Plaza_Ciudad': 'Ciudad / Plaza'})
                    df_por_taller = resumen_grp_sla(df_sla_view, ['Estado_Plaza', 'Plaza_Ciudad', c_tal_s]).rename(columns={'Estado_Plaza': 'Estado', 'Plaza_Ciudad': 'Ciudad', c_tal_s: 'Taller (CDR)'})

                    df_det_sin = df_sla_view.copy()
                    for c_dt_f, nom_f in [('DT_Asig', 'F. Asignación'), ('DT_Conf', 'F. Confirmación'), ('DT_Env', 'F. Envío'), ('DT_Ent', 'F. Entrega'), ('DT_Rec', 'F. Recibo')]:
                        df_det_sin[nom_f] = df_det_sin[c_dt_f].dt.strftime('%d/%m/%Y').fillna('-')
                    df_det_sin['Vehículo'] = df_det_sin[c_mar_s].astype(str) + " " + df_det_sin[c_mod_s].astype(str)
                    cols_n4 = [c for c in ['Estado_Plaza', 'Plaza_Ciudad', c_tal_s, c_sin_s, 'Vehículo', '_Cant_Num', c_pza_s, c_est_s, 'Auditoria_BBVA', 'F. Asignación', 'F. Confirmación', 'D_Asig_Conf', 'F. Envío', 'D_Conf_Env', 'F. Entrega', 'D_Env_Ent', 'F. Recibo', 'D_Ent_Rec', 'D_Ciclo_Total'] if c in df_det_sin.columns]
                    df_por_siniestro = df_det_sin[cols_n4].rename(columns={'Estado_Plaza': 'Estado', 'Plaza_Ciudad': 'Ciudad', c_tal_s: 'Taller (CDR)', c_sin_s: 'Siniestro', '_Cant_Num': 'Cant', c_pza_s: 'Pieza', c_est_s: 'Estatus Actual', 'Auditoria_BBVA': 'Evaluación 0-7d', 'D_Asig_Conf': 'Asig➔Conf (d)', 'D_Conf_Env': 'Conf➔Env (d)', 'D_Env_Ent': 'Env➔Ent (d)', 'D_Ent_Rec': 'Ent➔Rec (d)', 'D_Ciclo_Total': 'Total (d)'}).sort_values(by=['Estado', 'Ciudad', 'Taller (CDR)', 'Siniestro'])

                    st1, st2, st3, st4 = st.tabs([f"🗺️ 1. Por Estado ({len(df_por_estado)})", f"🏙️ 2. Por Ciudad ({len(df_por_ciudad)})", f"🏢 3. Por Taller ({len(df_por_taller)})", f"🚗 4. Siniestros Incluidos ({df_por_siniestro['Siniestro'].nunique()} Sin. | {int(df_por_siniestro['Cant'].sum())} Pzas)"])
                    with st1: st.dataframe(df_por_estado, use_container_width=True, hide_index=True)
                    with st2: st.dataframe(df_por_ciudad, use_container_width=True, hide_index=True)
                    with st3: st.dataframe(df_por_taller, use_container_width=True, hide_index=True)
                    with st4: st.dataframe(df_por_siniestro, use_container_width=True, hide_index=True)

                    b_pdf_sla = crear_pdf_tablas_apiladas(
                        "INFORME EJECUTIVO DE TIEMPOS Y DESEMPEÑO",
                        f"Periodo: {rango_str_titulo} | Aseguradora: {aseg_rep_sel} | Emisión: {hoy_cal_date.strftime('%d/%m/%Y')}",
                        [
                            ("1. RESUMEN EJECUTIVO POR ESTADO", df_por_estado, [('Estado', 55), ('Piezas', 18), ('Surtidas', 20), ('% Surtido', 22), ('1. Asig ➔ Conf (días)', 26), ('2. Conf ➔ Envío (días)', 26), ('3. Envío ➔ Entrega (días)', 28), ('4. Entrega ➔ Recibo (días)', 28), ('Ciclo Total (días)', 24), ('% Ef. 0-7 Días', 24)]),
                            ("2. RESUMEN EJECUTIVO POR CIUDAD", df_por_ciudad, [('Estado', 34), ('Ciudad / Plaza', 38), ('Piezas', 16), ('% Surtido', 20), ('1. Asig ➔ Conf (días)', 27), ('2. Conf ➔ Envío (días)', 27), ('3. Envío ➔ Entrega (días)', 29), ('4. Entrega ➔ Recibo (días)', 29), ('Ciclo Total (días)', 26), ('% Ef. 0-7 Días', 26)]),
                            ("3. DESGLOSE POR TALLER (CDR)", df_por_taller, [('Estado', 28), ('Ciudad', 28), ('Taller (CDR)', 56), ('Piezas', 14), ('% Surtido', 18), ('1. Asig ➔ Conf (días)', 22), ('2. Conf ➔ Envío (días)', 22), ('3. Envío ➔ Entrega (días)', 22), ('4. Entrega ➔ Recibo (días)', 22), ('Ciclo Total (días)', 20), ('% Ef. 0-7 Días', 20)])
                        ]
                    )
                    b_xlsx_sla = generar_excel_corporativo_pmr(
                        {
                            "Resumen_Ejecutivo": [("1. RESUMEN POR ESTADO", df_por_estado), ("2. RESUMEN POR CIUDAD", df_por_ciudad), ("3. DESGLOSE POR TALLER (CDR)", df_por_taller)],
                            "Detalle_Siniestros": [("4. EXPEDIENTE DE SINIESTROS Y PIEZAS AUDITADAS", df_por_siniestro)]
                        },
                        f"Informe de Tiempos y SLA ({rango_str_titulo})"
                    )
                    cs1, cs2 = st.columns(2)
                    cs1.download_button("🖨️ Descargar Informe Ejecutivo (PDF)", data=b_pdf_sla, file_name=f"Informe_Tiempos_PMR_{hoy_cal_date.strftime('%d%m%Y')}.pdf", mime="application/pdf", type="primary", use_container_width=True)
                    cs2.download_button("📊 Descargar Informe Auditado (.XLSX)", data=b_xlsx_sla, file_name=f"Informe_Tiempos_SLA_PMR_{hoy_cal_date.strftime('%d%m%Y')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
                else:
                    st.info("No se encontraron registros para el rango de fechas seleccionado.")
            else:
                st.warning("No hay datos disponibles para calcular los tiempos.")

# Encabezado estructurado en 2 niveles: Logo a la izquierda | Menú arriba y Controles abajo a la derecha
col_logo, col_derecha = st.columns([1.15, 8.85], vertical_alignment="center")

with col_logo:
    try: 
        st.image("logo.png", use_container_width=True)
    except: 
        st.markdown("**PREMIER**")

with col_derecha:
    vista_actual = st.radio("Navegación", opciones_menu, horizontal=True, label_visibility="collapsed")
    col_espacio, col_aseg, col_btn_dir, col_btn_fot, col_btn_ref, col_btn_pop, col_btn_gua = st.columns(
        [2.9, 1.4, 0.95, 0.95, 0.45, 0.45, 1.0], vertical_alignment="center"
    )

with col_aseg:
    if vista_actual == "📊 Analítico":
        aseguradora_sel = st.selectbox("Aseguradora", ["Multiasistencias", "GNP", "Todas (Consolidado)"], label_visibility="collapsed")
    else:
        aseguradora_sel = "Todas (Consolidado)" 

with col_btn_ref:
    if st.button("🔄", help="Forzar recarga de datos desde Google Sheets", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

with col_btn_pop:
    if st.button("🖥️", help="Abrir Pop-up con Estatus Crítico y Consola Matrix", use_container_width=True):
        abrir_popup_monitor()

# ==============================================================================
# === [SISTEMA DE TAREAS Y DIRECTORIO FUNCIONALES] ===
# ==============================================================================

@st.cache_data(ttl=600)
def obtener_mapa_usuarios():
    """Lee Usuarios con caché de 10 min para nunca saturar la cuota de Google Sheets."""
    usuarios_dropdown = []
    grupos_identidad = []
    try:
        doc = init_connection()
        ws_u = doc.worksheet("Usuarios")
        datos_u = ws_u.get_all_values()
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
    import re
    import unicodedata
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
    """Soporta 1 usuario o varios separados por coma (Chat Grupal)."""
    partes = [p.strip() for p in re.split(r'[,;]', str(campo_usuarios or '')) if p.strip()]
    return any(es_mismo_usuario(usuario, p, grupos_identidad) for p in partes)

def extraer_ultimo_evento_chat(row):
    """Devuelve (datetime_ultima_actividad, hora_corta, ultimo_autor) del hilo."""
    tz_mx_ch = datetime.timezone(datetime.timedelta(hours=-6))
    hoy_d_ch = datetime.datetime.now(tz_mx_ch).date()

    def _parse_dt_ch(txt):
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
                dt_p = _parse_dt_ch(m.group(1))
                autor_ult = m.group(2).strip()
                if dt_p:
                    dt_ult = dt_p
                break

    if dt_ult is None:
        dt_ult = _parse_dt_ch(row.get('Fecha_Creacion', ''))
    if not autor_ult:
        autor_ult = str(row.get('Emisor', '')).strip()

    if dt_ult is None:
        gs_r = int(row.get('GS_Row', 0) or 0)
        dt_ult = datetime.datetime(2000, 1, 1) + datetime.timedelta(seconds=gs_r)
        hora_corta = ""
    else:
        hora_corta = dt_ult.strftime("%H:%M") if dt_ult.date() == hoy_d_ch else dt_ult.strftime("%d/%m %H:%M")

    return dt_ult, hora_corta, autor_ult

def requiere_atencion_chat(row, usuario, grupos_identidad=None):
    """True si el chat está activo y el último mensaje fue enviado por otra persona."""
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

def acortar_taller_chat(taller_raw, max_len=18):
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

@st.cache_data(ttl=180)
def leer_tareas_normalizadas():
    """Lee Gestor_Tareas con caché de 20 seg para evitar bloqueos por exceso de consultas (Error 429)."""
    try:
        doc = init_connection()
        ws_tareas = doc.worksheet("Gestor_Tareas")
        datos = ws_tareas.get_all_values()
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
            if not st_normal and len(f_ext) > 6 and str(f_ext[6]).strip().lower() in ["pendiente", "resuelto", "finalizado"]:
                filas_limpias.append({
                    'GS_Row': idx_f,
                    'ID_Tarea': str(f_ext[0]).strip(),
                    'Fecha_Creacion': str(f_ext[1]).strip(),
                    'Emisor': str(f_ext[2]).strip(),
                    'Receptor': str(f_ext[3]).strip(),
                    'Siniestro / Taller / Piezas': str(f_ext[4]).strip(),
                    'Instruccion': str(f_ext[5]).strip(),
                    'Status': str(f_ext[6]).strip(),
                    'Respuesta': str(f_ext[7]).strip() if len(f_ext) > 7 else ""
                })
            else:
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

def actualizar_tarea_en_sheet(ws_tareas, headers, row_data, nuevo_status, nuevo_historial):
    """Actualiza Status y Respuesta en las columnas exactas de la hoja."""
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
    """Lee imágenes y documentos de BD_CHAT_IMAGENES y reconstruye el base64 completo."""
    mapa_adjuntos = {}
    try:
        doc = init_connection()
        ws_img = doc.worksheet("BD_CHAT_IMAGENES")
        filas = ws_img.get_all_values()
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
    """Elimina automáticamente de BD_CHAT_IMAGENES cualquier archivo con 5 o más días de antigüedad."""
    try:
        filas = ws_img.get_all_values()
        if len(filas) <= 1:
            return
        tz_mx_d = datetime.timezone(datetime.timedelta(hours=-6))
        ahora_d = datetime.datetime.now(tz_mx_d).replace(tzinfo=None)
        encabezado = filas[0]
        vigentes = [encabezado]
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
    """Guarda imagen (comprimida) o documento (PDF/Excel/Word/CSV <=450KB) en BD_CHAT_IMAGENES y depura >5 días."""
    import io
    import uuid
    import base64
    from PIL import Image

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
            raise ValueError("El documento supera el límite de 450 KB para Google Sheets.")
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
    tz_mx_f = datetime.timezone(datetime.timedelta(hours=-6))
    fecha_f = datetime.datetime.now(tz_mx_f).strftime("%d/%m/%Y %H:%M")

    doc = init_connection()
    try:
        ws_img = doc.worksheet("BD_CHAT_IMAGENES")
    except Exception:
        ws_img = doc.add_worksheet(title="BD_CHAT_IMAGENES", rows=1000, cols=20)

    # Depuración automática de archivos con 5+ días de antigüedad (1 vez por lote)
    if depurar:
        depurar_adjuntos_antiguos_chat(ws_img, dias_vigencia=5)

    primera_fila = ws_img.row_values(1)
    if not primera_fila:
        ws_img.append_row(["ID_FOTO", "FECHA", "AUTOR", "PARTE_1", "PARTE_2", "PARTE_3"], value_input_option="USER_ENTERED")

    # Asegurar columnas suficientes si el documento requiere más bloques de 42,000 caracteres
    cols_necesarias = 3 + len(partes)
    if ws_img.col_count < cols_necesarias:
        ws_img.resize(cols=cols_necesarias)

    nueva_fila_adj = [id_adj, fecha_f, str(autor).strip()] + partes
    ws_img.append_row(nueva_fila_adj, value_input_option="RAW")

    st.session_state.setdefault("cache_fotos_chat_local", {})[id_adj] = data_uri
    cargar_fotos_chat_sheets.clear()

    nom_seguro = re.sub(r'[\[\]\|]', '', str(nombre_archivo or f"archivo{ext}")).strip()
    return (f"[FOTO:{id_adj}]" if es_imagen else f"[DOC:{id_adj}|{nom_seguro}]")

@st.cache_data(ttl=600)
def cargar_stickers_locales():
    """Carga los stickers (.webp, .png, .gif, .jpg) desde la carpeta stickers/ del repo."""
    stickers = {}
    carpeta_st = "stickers"
    if not os.path.isdir(carpeta_st):
        return stickers
    mimes_st = {
        ".webp": "image/webp",
        ".png": "image/png",
        ".gif": "image/gif",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg"
    }
    for fname in sorted(os.listdir(carpeta_st)):
        ext = os.path.splitext(fname)[1].lower()
        if ext not in mimes_st:
            continue
        ruta = os.path.join(carpeta_st, fname)
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

def renderizar_hilo_chat(row, usuario_activo_real, grupos_identidad):
    """Dibuja una ventana estilo WhatsApp con soporte de imágenes, documentos, stickers, zoom, Ctrl+V y arrastre."""
    import html
    import re
    import streamlit.components.v1 as components

    texto_completo_chat = f"{row.get('Instruccion', '')} {row.get('Respuesta', '')}"
    mapa_fotos_chat = {}
    if "[FOTO:" in texto_completo_chat or "[DOC:" in texto_completo_chat:
        mapa_fotos_chat.update(cargar_fotos_chat_sheets())
        mapa_fotos_chat.update(st.session_state.get("cache_fotos_chat_local", {}))

    stickers_map = cargar_stickers_locales() if "[STICKER:" in texto_completo_chat.upper() else {}

    def formatear_texto_con_adjuntos(txt_crudo):
        txt_str = str(txt_crudo or "").strip()
        m_solo_st = re.fullmatch(r'\[STICKER:([A-Za-z0-9_-]+)\]', txt_str, flags=re.IGNORECASE)
        if m_solo_st:
            k_st = m_solo_st.group(1).strip().upper()
            info_st = stickers_map.get(k_st)
            if info_st:
                return f'<img src="{info_st["data_uri"]}" class="chat-sticker-solo" alt="{html.escape(k_st)}" />', True
            return f'<span style="color:#8696A0; font-style:italic;">[🏷️ Sticker: {html.escape(k_st)}]</span>', False

        txt_esc = html.escape(txt_str).replace('\n', '<br>')

        def _reemplazar_foto(m):
            id_f = m.group(1).strip().upper()
            src_f = mapa_fotos_chat.get(id_f, "")
            if src_f:
                return (
                    f'<div class="img-wrap">'
                    f'<img src="{src_f}" class="chat-img" onclick="abrirZoom(this.src)" title="Clic para ampliar imagen" />'
                    f'</div>'
                )
            return f'<span style="color:#8696A0; font-style:italic;">[📷 Imagen {id_f} expirada (&gt;5 días)]</span>'

        def _reemplazar_doc(m):
            id_d = m.group(1).strip().upper()
            nom_d = m.group(2).strip()
            src_d = mapa_fotos_chat.get(id_d, "")
            icono_d = "📊" if any(x in nom_d.lower() for x in [".xls", ".csv"]) else ("📝" if ".doc" in nom_d.lower() else "📄")
            if src_d:
                return (
                    f'<div class="doc-card">'
                    f'<a href="{src_d}" download="{nom_d}" class="doc-link" title="Descargar {nom_d}">'
                    f'{icono_d} <span>{nom_d}</span> <b>⬇️</b>'
                    f'</a></div>'
                )
            return f'<span style="color:#8696A0; font-style:italic;">[{icono_d} {nom_d} expirado (&gt;5 días)]</span>'

        def _reemplazar_sticker(m):
            k_st = m.group(1).strip().upper()
            info_st = stickers_map.get(k_st)
            if info_st:
                return f'<div class="img-wrap"><img src="{info_st["data_uri"]}" class="chat-sticker-inline" /></div>'
            return f'<span style="color:#8696A0;">[🏷️ {html.escape(k_st)}]</span>'

        txt_out = re.sub(r'\[FOTO:([A-Za-z0-9]+)\]', _reemplazar_foto, txt_esc)
        txt_out = re.sub(r'\[DOC:([A-Za-z0-9]+)\|([^\]]+)\]', _reemplazar_doc, txt_out)
        txt_out = re.sub(r'\[STICKER:([A-Za-z0-9_-]+)\]', _reemplazar_sticker, txt_out, flags=re.IGNORECASE)
        return txt_out, False

    def armar_burbuja_pc(autor, fecha, cuerpo_raw, es_mio):
        cuerpo_html, es_solo_sticker = formatear_texto_con_adjuntos(cuerpo_raw)
        align = "flex-end" if es_mio else "flex-start"
        color_autor = "#53BDEB" if es_mio else "#00A884"
        header_html = f'<div class="author" style="color:{color_autor};">{html.escape(autor)} <span class="time">• {html.escape(fecha)}</span></div>' if autor else ""
        if es_solo_sticker:
            return (
                f'<div class="msg-row" style="justify-content:{align};">'
                f'<div class="sticker-wrap" style="align-items:{align};">'
                f'{header_html}{cuerpo_html}'
                f'</div></div>'
            )
        bg = "#005C4B" if es_mio else "#1F2C34"
        radius = "10px 0px 10px 10px" if es_mio else "0px 10px 10px 10px"
        return (
            f'<div class="msg-row" style="justify-content:{align};">'
            f'<div class="bubble" style="background-color:{bg}; border-radius:{radius};">'
            f'{header_html}<div class="txt">{cuerpo_html}</div>'
            f'</div></div>'
        )

    emisor_orig = str(row.get('Emisor', 'Usuario')).strip()
    fecha_orig = str(row.get('Fecha_Creacion', '')).strip()
    es_mio_orig = es_mismo_usuario(usuario_activo_real, emisor_orig, grupos_identidad)

    burbujas = [armar_burbuja_pc(emisor_orig, fecha_orig, row.get('Instruccion', ''), es_mio_orig)]

    historial_raw = str(row.get('Respuesta', '')).strip()
    if historial_raw and historial_raw.lower() not in ["none", "nan", ""]:
        lineas = historial_raw.replace('\\n', '\n').split('\n')
        for linea in lineas:
            linea_limpia = linea.strip()
            if not linea_limpia:
                continue
            m = re.match(r'^\[(.*?)\]\s*([^:]+):\s*(.*)$', linea_limpia)
            if m:
                f_msg, autor_msg, txt_msg = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
                es_mio = es_mismo_usuario(usuario_activo_real, autor_msg, grupos_identidad)
            else:
                f_msg, autor_msg, txt_msg = "", "", linea_limpia
                es_mio = es_mismo_usuario(usuario_activo_real, linea_limpia, grupos_identidad) or (usuario_activo_real.lower() in linea_limpia.lower())
            burbujas.append(armar_burbuja_pc(autor_msg, f_msg, txt_msg, es_mio))

    es_indep_js = "true" if st.query_params.get("vista") == "tareas" else "false"
    iframe_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            html, body {{
                height: 100%;
                width: 100%;
                background-color: transparent;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                overflow: hidden;
            }}
            #chat-viewport {{
                height: 100%;
                width: 100%;
                overflow-y: auto;
                overflow-x: hidden;
                background-color: #0B141A;
                background-image: radial-gradient(#1F2C34 1px, transparent 1px);
                background-size: 20px 20px;
                border: 1px solid #222E35;
                border-radius: 10px;
                padding: 12px;
                position: relative;
            }}
            #chat-viewport::-webkit-scrollbar {{ width: 7px; }}
            #chat-viewport::-webkit-scrollbar-track {{ background: #0B141A; border-radius: 10px; }}
            #chat-viewport::-webkit-scrollbar-thumb {{ background: #374045; border-radius: 10px; }}
            .msg-row {{ display: flex; margin-bottom: 9px; width: 100%; }}
            .bubble {{
                color: #E9EDEF;
                padding: 7px 11px;
                max-width: 80%;
                box-shadow: 0 1px 2px rgba(0,0,0,0.5);
                word-wrap: break-word;
            }}
            .sticker-wrap {{ display: flex; flex-direction: column; max-width: 75%; }}
            .chat-sticker-solo {{
                width: 128px; max-width: 100%; height: auto;
                object-fit: contain;
                filter: drop-shadow(0 2px 6px rgba(0,0,0,0.55));
            }}
            .chat-sticker-inline {{
                width: 105px; height: auto; object-fit: contain;
            }}
            .author {{ font-size: 0.74rem; font-weight: 700; margin-bottom: 3px; }}
            .time {{ color: #8696A0; font-weight: normal; font-size: 0.68rem; }}
            .txt {{ font-size: 0.88rem; line-height: 1.38; }}
            .img-wrap {{ margin-top: 5px; margin-bottom: 3px; }}
            .chat-img {{
                max-width: 230px;
                max-height: 180px;
                border-radius: 8px;
                border: 1px solid rgba(255,255,255,0.18);
                cursor: zoom-in;
                display: block;
                transition: transform 0.15s ease;
            }}
            .chat-img:hover {{ transform: scale(1.02); border-color: #00A884; }}
            .doc-card {{
                margin-top: 5px;
                margin-bottom: 3px;
                background: rgba(0,0,0,0.28);
                border: 1px solid rgba(255,255,255,0.18);
                border-radius: 7px;
                padding: 6px 10px;
            }}
            .doc-link {{
                color: #E9EDEF;
                text-decoration: none;
                font-size: 0.82rem;
                display: flex;
                align-items: center;
                gap: 6px;
            }}
            .doc-link:hover {{ color: #53BDEB; }}
            #zoom-overlay {{
                display: none;
                position: fixed;
                top: 0; left: 0; width: 100%; height: 100%;
                background: rgba(0,0,0,0.92);
                z-index: 9999;
                align-items: center;
                justify-content: center;
                flex-direction: column;
                cursor: zoom-out;
            }}
            #zoom-overlay img {{
                max-width: 94%;
                max-height: 82%;
                border-radius: 8px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.8);
            }}
            #zoom-bar {{ margin-top: 8px; display: flex; gap: 12px; }}
            .zoom-btn {{
                background: #00A884;
                color: #fff;
                text-decoration: none;
                padding: 5px 14px;
                border-radius: 6px;
                font-size: 0.8rem;
                font-weight: 600;
            }}
        </style>
    </head>
    <body>
        <div id="chat-viewport">
            {''.join(burbujas)}
        </div>
        <div id="zoom-overlay" onclick="cerrarZoom()">
            <img id="zoom-img" src="" />
            <div id="zoom-bar">
                <a id="zoom-dl" class="zoom-btn" href="" download="foto_chat_pmr.jpg" onclick="event.stopPropagation();">⬇️ Descargar Imagen</a>
                <span class="zoom-btn" style="background:#374045;">✖ Cerrar</span>
            </div>
        </div>
        <script>
            const esIndependiente = {es_indep_js};
            const vp = document.getElementById('chat-viewport');
            function bajarAlFondo() {{ if (vp) {{ vp.scrollTop = vp.scrollHeight; }} }}

            function ajustarPanelesTareas() {{
                if (!esIndependiente) {{ bajarAlFondo(); return; }}
                try {{
                    const pWin = window.parent;
                    const parentDoc = pWin.document;
                    const myIframe = window.frameElement;
                    if (!myIframe) return;

                    const rectIf = myIframe.getBoundingClientRect();
                    if (rectIf.top <= 0) return;

                    const inBox = parentDoc.querySelector('.st-key-pmr_chat_input_box');
                    const hIn = (inBox && inBox.getBoundingClientRect().height > 20) ? inBox.getBoundingClientRect().height : 64;
                    const hChat = Math.max(220, Math.floor(pWin.innerHeight - rectIf.top - hIn - 82));

                    myIframe.setAttribute('height', String(hChat));
                    myIframe.style.setProperty('height', hChat + 'px', 'important');
                    myIframe.style.setProperty('min-height', hChat + 'px', 'important');
                    myIframe.style.setProperty('max-height', hChat + 'px', 'important');
                    myIframe.style.setProperty('display', 'block', 'important');

                    let cur = myIframe.parentElement;
                    let pasos = 0;
                    while (cur && pasos < 7) {{
                        if (cur.matches('[data-testid="stColumn"]') || cur.classList.contains('st-key-pmr_chat_float_open')) break;
                        cur.style.setProperty('height', hChat + 'px', 'important');
                        cur.style.setProperty('min-height', hChat + 'px', 'important');
                        cur.style.setProperty('max-height', hChat + 'px', 'important');
                        cur.style.setProperty('flex', 'none', 'important');
                        cur.style.setProperty('overflow', 'visible', 'important');
                        if (cur.classList.contains('st-key-pmr_chat_msgs_box')) {{
                            if (cur.parentElement && cur.parentElement.children.length === 1 && !cur.parentElement.matches('[data-testid="stColumn"]')) {{
                                cur.parentElement.style.setProperty('height', 'auto', 'important');
                                cur.parentElement.style.setProperty('flex', 'none', 'important');
                            }}
                            break;
                        }}
                        cur = cur.parentElement;
                        pasos++;
                    }}

                    const listaBox = parentDoc.querySelector('.st-key-pmr_lista_temas_scroll');
                    if (listaBox) {{
                        const rectL = listaBox.getBoundingClientRect();
                        if (rectL.top > 0) {{
                            const hLista = Math.max(220, Math.floor(pWin.innerHeight - rectL.top - 22));
                            listaBox.style.setProperty('height', hLista + 'px', 'important');
                            listaBox.style.setProperty('max-height', hLista + 'px', 'important');
                            listaBox.style.setProperty('min-height', hLista + 'px', 'important');
                            listaBox.style.setProperty('box-sizing', 'border-box', 'important');
                            if (listaBox.parentElement && listaBox.parentElement.children.length === 1 && !listaBox.parentElement.matches('[data-testid="stColumn"]')) {{
                                listaBox.parentElement.style.setProperty('height', hLista + 'px', 'important');
                                listaBox.parentElement.style.setProperty('max-height', hLista + 'px', 'important');
                            }}
                            listaBox.querySelectorAll('div[style*="height"]').forEach(d => {{
                                d.style.setProperty('height', '100%', 'important');
                                d.style.setProperty('max-height', '100%', 'important');
                            }});
                        }}
                    }}

                    bajarAlFondo();
                }} catch (e) {{}}
            }}

            ajustarPanelesTareas();
            window.addEventListener('load', ajustarPanelesTareas);
            setTimeout(ajustarPanelesTareas, 150);
            setTimeout(ajustarPanelesTareas, 450);
            try {{
                const pWinR = window.parent;
                if (pWinR._pmrResizeHandler) {{
                    pWinR.removeEventListener('resize', pWinR._pmrResizeHandler);
                }}
                pWinR._pmrResizeHandler = ajustarPanelesTareas;
                pWinR.addEventListener('resize', pWinR._pmrResizeHandler);
            }} catch (e) {{}}

            function abrirZoom(src) {{
                const ov = document.getElementById('zoom-overlay');
                document.getElementById('zoom-img').src = src;
                document.getElementById('zoom-dl').href = src;
                ov.style.display = 'flex';
            }}
            function cerrarZoom() {{
                document.getElementById('zoom-overlay').style.display = 'none';
            }}

            function enviarBlobAlUploader(blob) {{
                try {{
                    const pWin = window.parent;
                    const parentDoc = pWin.document;
                    const file = new pWin.File([blob], "captura_" + Date.now() + ".png", {{ type: blob.type || "image/png" }});
                    const floatWin = parentDoc.querySelector('.st-key-pmr_chat_float_open') || parentDoc.querySelector('div[data-testid="stVerticalBlockBorderWrapper"]:has(.pmr-chat-float-open)') || parentDoc;
                    const activePanel = floatWin.querySelector('div[role="tabpanel"]:not([hidden])') || floatWin;
                    let targetInput = activePanel.querySelector('input[type="file"]');
                    if (!targetInput) {{
                        const allInputs = floatWin.querySelectorAll('input[type="file"]');
                        if (allInputs.length > 0) targetInput = allInputs[0];
                    }}
                    if (targetInput) {{
                        const dt = new pWin.DataTransfer();
                        dt.items.add(file);
                        const setter = Object.getOwnPropertyDescriptor(pWin.HTMLInputElement.prototype, 'files').set;
                        if (setter) {{ setter.call(targetInput, dt.files); }} else {{ targetInput.files = dt.files; }}
                        targetInput.dispatchEvent(new pWin.Event('input', {{ bubbles: true }}));
                        targetInput.dispatchEvent(new pWin.Event('change', {{ bubbles: true }}));
                    }}
                }} catch (err) {{}}
            }}

            function manejarEventoPaste(e) {{
                const cd = e.clipboardData || (e.originalEvent && e.originalEvent.clipboardData);
                if (!cd || !cd.items) return;
                for (let i = 0; i < cd.items.length; i++) {{
                    if (cd.items[i].type && cd.items[i].type.indexOf('image') !== -1) {{
                        const blob = cd.items[i].getAsFile();
                        if (blob) {{
                            e.preventDefault();
                            enviarBlobAlUploader(blob);
                            break;
                        }}
                    }}
                }}
            }}

            document.addEventListener('paste', manejarEventoPaste, true);
            try {{
                const pWin = window.parent;
                const parentDoc = pWin.document;
                if (parentDoc._pmrPasteHandler) {{
                    parentDoc.removeEventListener('paste', parentDoc._pmrPasteHandler, true);
                }}
                parentDoc._pmrPasteHandler = manejarEventoPaste;
                parentDoc.addEventListener('paste', parentDoc._pmrPasteHandler, true);

                // Activar arrastre (Drag & Drop) en la barra de título de la ventana flotante
                const floatBox = parentDoc.querySelector('.st-key-pmr_chat_float_open') || parentDoc.querySelector('div[data-testid="stVerticalBlockBorderWrapper"]:has(.pmr-chat-float-open)');
                const handle = parentDoc.querySelector('.pmr-drag-handle');
                if (floatBox && handle && !handle._dragBound) {{
                    handle._dragBound = true;
                    handle.style.cursor = 'move';
                    let isDragging = false, offX = 0, offY = 0;
                    handle.addEventListener('mousedown', (ev) => {{
                        isDragging = true;
                        const rect = floatBox.getBoundingClientRect();
                        offX = ev.clientX - rect.left;
                        offY = ev.clientY - rect.top;
                        floatBox.style.right = 'auto';
                        floatBox.style.bottom = 'auto';
                        floatBox.style.left = rect.left + 'px';
                        floatBox.style.top = rect.top + 'px';
                        ev.preventDefault();
                    }});
                    parentDoc.addEventListener('mousemove', (ev) => {{
                        if (!isDragging) return;
                        floatBox.style.left = Math.max(0, Math.min(pWin.innerWidth - 180, ev.clientX - offX)) + 'px';
                        floatBox.style.top = Math.max(0, Math.min(pWin.innerHeight - 80, ev.clientY - offY)) + 'px';
                    }});
                    parentDoc.addEventListener('mouseup', () => {{ isDragging = false; }});
                }}
            }} catch (err) {{}}
        </script>
    </body>
    </html>
    """
    components.html(iframe_html, height=300, scrolling=False)

def contar_tareas_pendientes(usuario):
    try:
        _, grupos_id = obtener_mapa_usuarios()
        df_t, _ = leer_tareas_normalizadas()
        if df_t.empty:
            return 0
        return sum(1 for _, r in df_t.iterrows() if requiere_atencion_chat(r, usuario, grupos_id))
    except Exception:
        return 0

def renderizar_widget_tareas_flotante():
    estado_chat = st.session_state.get('chat_flotante_estado', 'minimizado')
    if estado_chat == 'cerrado':
        estado_chat = 'minimizado'

    st.markdown("""
        <style>
        .st-key-pmr_chat_float_open,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.pmr-chat-float-open) {
            position: fixed !important;
            bottom: 58px !important;
            right: 16px !important;
            width: 860px !important;
            max-width: 94vw !important;
            max-height: 80vh !important;
            overflow-y: auto !important;
            z-index: 999996 !important;
            background-color: #05070A !important;
            border: 1.5px solid #00A884 !important;
            border-radius: 12px !important;
            box-shadow: 0px 16px 45px rgba(0, 0, 0, 0.95) !important;
            padding: 10px 14px !important;
        }
        .st-key-pmr_chat_float_min,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.pmr-chat-float-min) {
            position: fixed !important;
            top: 8px !important;
            right: 22px !important;
            width: 215px !important;
            z-index: 999996 !important;
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0px !important;
        }
        .st-key-pmr_chat_float_open [data-testid="stFileUploaderDropzoneInstructions"],
        .st-key-pmr_chat_float_open [data-testid="stFileUploaderFile"],
        .st-key-pmr_chat_float_open [data-testid="stFileUploader"] small {
            display: none !important;
        }
        .st-key-pmr_chat_float_open [data-testid="stFileUploaderDropzone"] {
            padding: 0px !important;
            min-height: 2.4rem !important;
            height: 2.4rem !important;
            border: none !important;
            background: transparent !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }
        .st-key-pmr_chat_float_open [data-testid="stFileUploaderDropzone"] button {
            width: 100% !important;
            min-height: 2.4rem !important;
            height: 2.4rem !important;
            margin: 0px !important;
            padding: 0.2rem 0.4rem !important;
        }
        /* Tarjetas de 2 líneas limpias y alineadas 100% a la izquierda */
        .st-key-pmr_lista_temas_scroll button {
            height: auto !important;
            min-height: 3.1rem !important;
            padding: 7px 12px !important;
            display: flex !important;
            justify-content: flex-start !important;
            align-items: flex-start !important;
            text-align: left !important;
            white-space: normal !important;
        }
        .st-key-pmr_lista_temas_scroll button > div,
        .st-key-pmr_lista_temas_scroll button [data-testid="stMarkdownContainer"] {
            width: 100% !important;
            text-align: left !important;
            margin-left: 0px !important;
        }
        .st-key-pmr_lista_temas_scroll button p {
            white-space: pre-line !important;
            line-height: 1.3 !important;
            font-size: 0.81rem !important;
            text-align: left !important;
            width: 100% !important;
            margin: 0px !important;
        }
    """, unsafe_allow_html=True)

    # --- BOTÓN FIJO EN ESQUINA SUPERIOR DERECHA (ESTADO MINIMIZADO) ---
    if estado_chat == 'minimizado':
        with st.container(border=False, key="pmr_chat_float_min"):
            st.markdown('<span class="pmr-chat-float-min" style="display:none;"></span>', unsafe_allow_html=True)
            n_pend_min = contar_tareas_pendientes(usuario_activo)
            lbl_min = f"💬 Tareas ({n_pend_min})" if n_pend_min > 0 else "💬 Tareas"
            import urllib.parse
            usr_q = urllib.parse.quote(str(st.session_state.get('usuario_actual', '')))
            cm_a, cm_b = st.columns([3.2, 1.0], vertical_alignment="center")
            with cm_a:
                if st.button(lbl_min, key="btn_restaurar_chat_float", type="primary" if n_pend_min > 0 else "secondary", use_container_width=True):
                    leer_tareas_normalizadas.clear()
                    st.session_state['chat_flotante_estado'] = 'abierto'
                    st.rerun()
            with cm_b:
                st.link_button("↗️", url=f"?vista=tareas&usr={usr_q}", help="Abrir Tareas en ventana independiente con sonido", use_container_width=True)
        return

    # --- ESTADO ABIERTO (VENTANA FLOTANTE ARRASTRABLE Y MINIMIZABLE) ---
    es_ventana_indep = (st.query_params.get("vista") == "tareas")
    with st.container(border=True, key="pmr_chat_float_open"):
        st.markdown('<span class="pmr-chat-float-open" style="display:none;"></span>', unsafe_allow_html=True)
        if es_ventana_indep:
            st.markdown(
                '<div style="font-size:1.05rem; font-weight:700; color:#E9EDEF; padding:2px 4px; user-select:none;">'
                '🔔 Centro de Tareas y Mensajería'
                '</div>',
                unsafe_allow_html=True
            )
        else:
            ch_tit, ch_min, ch_cls = st.columns([6.4, 0.8, 0.8], vertical_alignment="center")
            with ch_tit:
                st.markdown(
                    '<div class="pmr-drag-handle" style="font-size:1.05rem; font-weight:700; color:#E9EDEF; padding:4px 6px; user-select:none;" title="Arrastra desde aquí para mover la ventana">'
                    '🔔 Centro de Tareas y Mensajería <span style="font-size:0.75rem; color:#8696A0; font-weight:normal;">(⠿ Arrastra para mover)</span>'
                    '</div>',
                    unsafe_allow_html=True
                )
            with ch_min:
                if st.button("➖", key="btn_min_chat_float", help="Minimizar para trabajar en el Dashboard", use_container_width=True):
                    st.session_state['chat_flotante_estado'] = 'minimizado'
                    st.rerun()
            with ch_cls:
                if st.button("✖", key="btn_cls_chat_float", help="Cerrar ventana", use_container_width=True):
                    st.session_state['chat_flotante_estado'] = 'cerrado'
                    st.rerun()

        doc = init_connection()
        usuario_activo_real = st.session_state.get('usuario_actual', 'Usuario Desconocido')
        usuarios_reales, grupos_identidad = obtener_mapa_usuarios()
        df_tareas, headers_tareas = leer_tareas_normalizadas()

        mapa_taller_sin = {}
        mapa_info_sin = {}
        try:
            if 'cargar_base_viva' in globals():
                df_uni_local = cargar_base_viva().copy()
            else:
                ws_uni = doc.worksheet("BD_UNIFICADA")
                datos_uni = ws_uni.get_all_values()
                df_uni_local = pd.DataFrame(datos_uni[1:], columns=[str(h).strip() for h in datos_uni[0]]) if len(datos_uni) > 1 else pd.DataFrame()
            
            col_sin_loc = next((c for c in df_uni_local.columns if "SINIESTRO" in str(c).upper() or "PEDIDO" in str(c).upper()), None)
            col_tall_loc = next((c for c in df_uni_local.columns if "TALLER" in str(c).upper() or "CDR" in str(c).upper()), None)
            col_marca_loc = next((c for c in df_uni_local.columns if "MARCA" in str(c).upper()), None)
            col_mod_loc = next((c for c in df_uni_local.columns if "MODELO" in str(c).upper() or "VEH" in str(c).upper()), None)
            col_desc_loc = next((c for c in df_uni_local.columns if "DESCRIPCI" in str(c).upper() or "REFACCI" in str(c).upper()), None)
            col_est_loc = next((c for c in df_uni_local.columns if "ESTATUS" in str(c).upper() and "ENV" not in str(c).upper() and "PAGO" not in str(c).upper()), None)

            if not df_uni_local.empty and col_sin_loc:
                for _, r_t in df_uni_local.drop_duplicates(subset=[col_sin_loc]).iterrows():
                    s_k = str(r_t.get(col_sin_loc, '')).strip().upper()
                    if s_k.endswith('.0'): s_k = s_k[:-2]
                    if not s_k or s_k == "NAN":
                        continue
                    t_v = str(r_t.get(col_tall_loc, '')).strip() if col_tall_loc else ""
                    m_v = str(r_t.get(col_marca_loc, '')).strip() if col_marca_loc else ""
                    mod_v = str(r_t.get(col_mod_loc, '')).strip() if col_mod_loc else ""
                    if t_v and t_v.lower() != "nan":
                        mapa_taller_sin[s_k] = t_v
                    mapa_info_sin[s_k] = {"taller": t_v, "marca": m_v, "modelo": mod_v}

            estatus_inactivos = ["CANCELADO", "RECIBIDO", "FACTURADO", "REEMBOLSADO", "PÉRDIDA TOTAL", "PERDIDA TOTAL", "PAGO DE DAÑOS", "PAGO DE DANOS"]
            if not df_uni_local.empty and col_est_loc:
                df_uni_local = df_uni_local[~df_uni_local[col_est_loc].astype(str).str.strip().str.upper().isin(estatus_inactivos)].copy()

            lista_siniestros = []
            if not df_uni_local.empty and col_sin_loc:
                df_unicos = df_uni_local.drop_duplicates(subset=[col_sin_loc])
                for _, r in df_unicos.iterrows():
                    sin_val = str(r.get(col_sin_loc, '')).strip()
                    mar_val = str(r.get(col_marca_loc, '')).strip() if col_marca_loc else ""
                    mod_val = str(r.get(col_mod_loc, '')).strip() if col_mod_loc else ""
                    veh_str = mod_val if mod_val.upper().startswith(mar_val.upper()) else f"{mar_val} {mod_val}".strip()
                    if sin_val and sin_val.lower() != "nan":
                        lista_siniestros.append(f"{sin_val} | {veh_str}" if veh_str else sin_val)
                lista_siniestros = sorted(lista_siniestros)
        except Exception:
            df_uni_local = pd.DataFrame()
            lista_siniestros = []

        chats_activos = pd.DataFrame()
        chats_finalizados = pd.DataFrame()
        n_atencion = 0

        if not df_tareas.empty:
            mask_mios = df_tareas.apply(
                lambda r: usuario_en_lista(usuario_activo_real, r.get('Receptor', ''), grupos_identidad) or es_mismo_usuario(usuario_activo_real, r.get('Emisor', ''), grupos_identidad),
                axis=1
            )
            df_mios = df_tareas[mask_mios].copy()
            if not df_mios.empty:
                chats_activos = df_mios[df_mios['Status'].astype(str).str.strip().str.lower().isin(['pendiente', 'resuelto'])].copy()
                chats_finalizados = df_mios[df_mios['Status'].astype(str).str.strip().str.lower() == 'finalizado'].copy()

                if not chats_activos.empty:
                    eventos_ch = chats_activos.apply(extraer_ultimo_evento_chat, axis=1)
                    chats_activos['_dt_ult'] = [ev[0] for ev in eventos_ch]
                    chats_activos['_hora_corta'] = [ev[1] for ev in eventos_ch]
                    chats_activos['_prio'] = chats_activos.apply(
                        lambda r: 0 if requiere_atencion_chat(r, usuario_activo_real, grupos_identidad) else 1,
                        axis=1
                    )
                    n_atencion = int((chats_activos['_prio'] == 0).sum())

        lbl_chats = f"💬 Chats ({n_atencion} nuevos)" if n_atencion > 0 else f"💬 Chats Activos ({len(chats_activos)})"
        tabs_tareas = st.tabs([lbl_chats, "➕ Nuevo Chat / Tarea", f"📁 Finalizados ({len(chats_finalizados)})"])

        # --- TAB 1: CHATS ACTIVOS ---
        with tabs_tareas[0]:
            if not chats_activos.empty:
                col_lista, col_ventana = st.columns([1.35, 2.65], gap="medium")

                def seleccionar_chat_cb(gs_id):
                    st.session_state['chat_activo_gs_row'] = gs_id

                def refrescar_lista_cb():
                    leer_tareas_normalizadas.clear()
                    cargar_fotos_chat_sheets.clear()

                with col_lista:
                    c_tit, c_ref_btn = st.columns([3, 1], vertical_alignment="center")
                    c_tit.markdown(f"##### 📋 Temas ({len(chats_activos)})")
                    c_ref_btn.button("🔄", key="btn_ref_wa_list", help="Actualizar mensajes", on_click=refrescar_lista_cb)

                    c_busq, c_ord = st.columns([1.65, 1.15], vertical_alignment="center")
                    with c_busq:
                        busqueda_chat = st.text_input(
                            "🔍 Buscar chat:",
                            placeholder="🔍 Siniestro, auto, taller...",
                            label_visibility="collapsed",
                            key="inp_buscar_chat_wa"
                        ).strip().lower()
                    with c_ord:
                        orden_sel = st.selectbox(
                            "Orden:",
                            ["🕐 Recientes", "🔴 Sin responder", "📅 Antiguos"],
                            label_visibility="collapsed",
                            key="sel_orden_chat_wa"
                        )

                    if orden_sel == "🕐 Recientes":
                        chats_ordenados = chats_activos.sort_values(by=['_dt_ult', 'GS_Row'], ascending=[False, False])
                    elif orden_sel == "📅 Antiguos":
                        chats_ordenados = chats_activos.sort_values(by=['_dt_ult', 'GS_Row'], ascending=[True, True])
                    else:
                        chats_ordenados = chats_activos.sort_values(by=['_prio', '_dt_ult', 'GS_Row'], ascending=[True, False, False])

                    chats_filtrados = chats_ordenados.copy()
                    if busqueda_chat:
                        def coincide_busqueda_chat(r):
                            ref_txt = str(r.get('Siniestro / Taller / Piezas', '')).lower()
                            id_s = ref_txt.split('|')[0].strip().upper()
                            if id_s.endswith('.0'): id_s = id_s[:-2]
                            taller_txt = str(mapa_taller_sin.get(id_s, '')).lower()
                            todo = f"{ref_txt} {taller_txt} {str(r.get('Emisor', '')).lower()} {str(r.get('Receptor', '')).lower()} {str(r.get('Instruccion', '')).lower()} {str(r.get('Respuesta', '')).lower()}"
                            return all(palabra in todo for palabra in busqueda_chat.split())
                        chats_filtrados = chats_ordenados[chats_ordenados.apply(coincide_busqueda_chat, axis=1)].copy()

                    opciones_ids_todas = chats_ordenados['GS_Row'].tolist()
                    opciones_ids = chats_filtrados['GS_Row'].tolist()

                    if 'chat_activo_gs_row' not in st.session_state or st.session_state['chat_activo_gs_row'] not in opciones_ids_todas:
                        st.session_state['chat_activo_gs_row'] = opciones_ids[0] if opciones_ids else opciones_ids_todas[0]
                    elif busqueda_chat and opciones_ids and st.session_state['chat_activo_gs_row'] not in opciones_ids:
                        st.session_state['chat_activo_gs_row'] = opciones_ids[0]

                    with st.container(height=320, border=True, key="pmr_lista_temas_scroll"):
                        if not opciones_ids:
                            st.caption("Sin coincidencias para tu búsqueda.")
                        for gs_r in opciones_ids:
                            fila_c = chats_ordenados[chats_ordenados['GS_Row'] == gs_r].iloc[0]
                            ref_c = str(fila_c.get('Siniestro / Taller / Piezas', 'General')).strip()
                            icono = "🔴" if fila_c.get('_prio', 1) == 0 else "🟢"

                            if ref_c.lower().startswith("general"):
                                titulo_l1 = ref_c.replace("General:", "").replace("GENERAL:", "").strip() or "Tema General"
                                if len(titulo_l1) > 32:
                                    titulo_l1 = titulo_l1[:31].rstrip() + "…"
                                linea_1 = f"{icono} 📌 {titulo_l1}"
                            else:
                                partes_r = [p.strip() for p in ref_c.split("|")]
                                id_s_c = partes_r[0].removesuffix('.0')
                                info_s = mapa_info_sin.get(id_s_c.upper(), {})
                                fallback_auto = partes_r[1] if (len(partes_r) > 1 and not partes_r[1].startswith("⚙️")) else ""
                                auto_c = acortar_auto_chat(info_s.get("marca", ""), info_s.get("modelo", ""), fallback_auto)
                                tall_c = acortar_taller_chat(info_s.get("taller", ""))
                                bloques_l1 = [b for b in [id_s_c, auto_c, tall_c] if b]
                                linea_1 = f"{icono} " + " · ".join(bloques_l1)

                            quienes_txt = formatear_participantes_corto(
                                fila_c.get('Emisor', ''),
                                fila_c.get('Receptor', ''),
                                usuario_activo_real,
                                grupos_identidad
                            )
                            hora_txt = str(fila_c.get('_hora_corta', '')).strip()
                            linea_2 = f"{quienes_txt} · {hora_txt}" if hora_txt else quienes_txt
                            es_seleccionado = (st.session_state['chat_activo_gs_row'] == gs_r)

                            st.button(
                                f"{linea_1}\n{linea_2}",
                                key=f"sel_chat_btn_{gs_r}",
                                type="primary" if es_seleccionado else "secondary",
                                use_container_width=True,
                                on_click=seleccionar_chat_cb,
                                args=(gs_r,)
                            )

                with col_ventana:
                    chat_sel_row = st.session_state['chat_activo_gs_row']
                    row_activa = chats_ordenados[chats_ordenados['GS_Row'] == chat_sel_row].iloc[0]
                    soy_emisor_chat = es_mismo_usuario(usuario_activo_real, row_activa.get('Emisor', ''), grupos_identidad)
                    st_chat = str(row_activa.get('Status', '')).strip().lower()

                    ref_completa_chat = str(row_activa.get("Siniestro / Taller / Piezas", "General")).strip()
                    id_sin_chat = ref_completa_chat.split("|")[0].strip().upper()
                    if id_sin_chat.endswith('.0'): id_sin_chat = id_sin_chat[:-2]
                    taller_chat = mapa_taller_sin.get(id_sin_chat, "")
                    html_taller_chat = f'  |  🏢 <b>Taller:</b> <span style="color:#E9EDEF; font-weight:600;">{taller_chat}</span>' if taller_chat else ""
                    rec_raw_h = str(row_activa.get("Receptor", "N/A")).strip()
                    es_grupo_h = ("," in rec_raw_h)
                    lbl_rec_h = "👥 <b>Grupo:</b>" if es_grupo_h else "🎯 <b>Para:</b>"

                    st.markdown(
                        f'<div style="background-color:#1F2C34; padding:8px 12px; border-radius:8px; margin-bottom:4px; border-left:4px solid #00A884;">'
                        f'<div style="font-size:0.9rem; font-weight:700; color:#E9EDEF;">🚗 {ref_completa_chat}</div>'
                        f'<div style="font-size:0.75rem; color:#8696A0;">'
                        f'👤 <b>Emisor:</b> {row_activa.get("Emisor", "N/A")}  |  {lbl_rec_h} {rec_raw_h}  |  📌 <b>Estatus:</b> {st_chat.upper()}{html_taller_chat}'
                        f'</div></div>',
                        unsafe_allow_html=True
                    )

                    with st.container(border=False, key="pmr_chat_msgs_box"):
                        renderizar_hilo_chat(row_activa, usuario_activo_real, grupos_identidad)

                    key_input_actual = f"wa_msg_input_{chat_sel_row}"
                    ver_up_key = f"ver_up_chat_{chat_sel_row}"
                    if ver_up_key not in st.session_state:
                        st.session_state[ver_up_key] = 0
                    key_uploader_actual = f"wa_img_up_{chat_sel_row}_{st.session_state[ver_up_key]}"

                    def enviar_msg_cb(row_act, soy_emi, k_inp, k_up, v_key):
                        texto = st.session_state.get(k_inp, "").strip()
                        arch_up = st.session_state.get(k_up, None)
                        if not texto and arch_up is None:
                            return

                        tag_adj = ""
                        if arch_up is not None:
                            try:
                                tag_adj = guardar_adjunto_chat_en_sheet(arch_up.getvalue(), arch_up.name, usuario_activo_real)
                            except Exception as e_adj:
                                st.toast(f"No se pudo subir el archivo: {e_adj}", icon="⚠️")
                                return

                        cuerpo_msg = f"{tag_adj} {texto}".strip() if (tag_adj and texto) else (tag_adj or texto)
                        if cuerpo_msg:
                            tz_mx_t = datetime.timezone(datetime.timedelta(hours=-6))
                            ahora_str = datetime.datetime.now(tz_mx_t).strftime("%d/%m/%Y %H:%M")
                            hist_prev = str(row_act.get('Respuesta', '')).strip()
                            linea_nueva = f"[{ahora_str}] {usuario_activo_real}: {cuerpo_msg}"
                            hist_final = f"{hist_prev}\n{linea_nueva}".strip() if hist_prev else linea_nueva
                            prox_status = "Pendiente" if soy_emi else "Resuelto"
                            ws_t = doc.worksheet("Gestor_Tareas")
                            actualizar_tarea_en_sheet(ws_t, headers_tareas, row_act, prox_status, hist_final)
                            leer_tareas_normalizadas.clear()
                            st.session_state[k_inp] = ""
                            st.session_state[v_key] = st.session_state.get(v_key, 0) + 1

                    def finalizar_chat_cb(row_act):
                        ws_t = doc.worksheet("Gestor_Tareas")
                        actualizar_tarea_en_sheet(ws_t, headers_tareas, row_act, "Finalizado", str(row_act.get('Respuesta', '')).strip())
                        leer_tareas_normalizadas.clear()

                    def enviar_sticker_pc_cb(row_act, soy_emi, clave_st):
                        tz_mx_t = datetime.timezone(datetime.timedelta(hours=-6))
                        ahora_str = datetime.datetime.now(tz_mx_t).strftime("%d/%m/%Y %H:%M")
                        hist_prev = str(row_act.get('Respuesta', '')).strip()
                        linea_nueva = f"[{ahora_str}] {usuario_activo_real}: [STICKER:{clave_st}]"
                        hist_final = f"{hist_prev}\n{linea_nueva}".strip() if hist_prev else linea_nueva
                        prox_status = "Pendiente" if soy_emi else "Resuelto"
                        ws_t = doc.worksheet("Gestor_Tareas")
                        actualizar_tarea_en_sheet(ws_t, headers_tareas, row_act, prox_status, hist_final)
                        leer_tareas_normalizadas.clear()

                    with st.container(border=True, key="pmr_chat_input_box"):
                        c_up_btn, c_st_btn, c_inp, c_send, c_fin = st.columns([0.75, 0.55, 2.15, 0.85, 0.85], vertical_alignment="bottom")
                        with c_up_btn:
                            archivo_chat_sel = st.file_uploader(
                                "Adjuntar:",
                                type=["png", "jpg", "jpeg", "webp", "pdf", "docx", "doc", "xlsx", "xls", "csv"],
                                key=key_uploader_actual,
                                label_visibility="collapsed"
                            )
                        with c_st_btn:
                            with st.popover("😀", use_container_width=True):
                                st_pc = cargar_stickers_locales()
                                if not st_pc:
                                    st.caption("Sin stickers en stickers/")
                                else:
                                    cols_st_pc = st.columns(3)
                                    for idx_sp, (k_sp, info_sp) in enumerate(st_pc.items()):
                                        with cols_st_pc[idx_sp % 3]:
                                            st.image(info_sp["path"], use_container_width=True)
                                            st.button(
                                                info_sp["etiqueta"][:10],
                                                key=f"pc_st_{chat_sel_row}_{k_sp}",
                                                use_container_width=True,
                                                on_click=enviar_sticker_pc_cb,
                                                args=(row_activa, soy_emisor_chat, k_sp)
                                            )
                        with c_inp:
                            st.text_input(
                                "Mensaje:",
                                key=key_input_actual,
                                placeholder="Escribe un mensaje o Ctrl+V para pegar captura...",
                                label_visibility="collapsed"
                            )
                        with c_send:
                            st.button(
                                "📤 Enviar",
                                key=f"wa_btn_send_{chat_sel_row}",
                                type="primary",
                                use_container_width=True,
                                on_click=enviar_msg_cb,
                                args=(row_activa, soy_emisor_chat, key_input_actual, key_uploader_actual, ver_up_key)
                            )
                        with c_fin:
                            st.button(
                                "🏁 Finalizar",
                                key=f"wa_btn_fin_{chat_sel_row}",
                                use_container_width=True,
                                help="Cerrar y archivar este tema",
                                on_click=finalizar_chat_cb,
                                args=(row_activa,)
                            )

                    if archivo_chat_sel is not None:
                        ext_sel = os.path.splitext(archivo_chat_sel.name.lower())[1]
                        if ext_sel in [".png", ".jpg", ".jpeg", ".webp"]:
                            st.image(archivo_chat_sel, caption=f"✅ {archivo_chat_sel.name} — Pulsa 📤 Enviar", width=130)
                        else:
                            st.info(f"📎 Archivo listo ({round(len(archivo_chat_sel.getvalue())/1024, 1)} KB): **{archivo_chat_sel.name}** — Pulsa **📤 Enviar** (vigencia 5 días).")

                    # --- HERRAMIENTA PARA ELIMINAR MENSAJES ENVIADOS POR ERROR ---
                    hist_raw_del = str(row_activa.get('Respuesta', '')).strip()
                    lineas_hist_del = [
                        l.strip() for l in hist_raw_del.replace('\\n', '\n').split('\n')
                        if l.strip() and l.strip().lower() not in ["none", "nan"]
                    ]
                    msg_ini_del = str(row_activa.get('Instruccion', '')).strip()

                    opciones_lineas_del = [f"0. [Mensaje Inicial] {row_activa.get('Emisor', '')}: {msg_ini_del}"]
                    for idx_l, l_txt in enumerate(lineas_hist_del, start=1):
                        opciones_lineas_del.append(f"{idx_l}. {l_txt}")

                    key_sel_del = f"sel_del_msg_{chat_sel_row}"

                    def eliminar_linea_chat_cb(row_act, lineas_actuales, k_sel):
                        sel_val = st.session_state.get(k_sel, "")
                        if not sel_val:
                            return
                        idx_borrar = int(sel_val.split(".")[0].strip())
                        ws_t = doc.worksheet("Gestor_Tareas")
                        row_mod = row_act.to_dict() if hasattr(row_act, "to_dict") else dict(row_act)
                        if idx_borrar == 0:
                            if lineas_actuales:
                                primera_resp = lineas_actuales[0]
                                m_p = re.match(r'^\[(.*?)\]\s*([^:]+):\s*(.*)$', primera_resp)
                                row_mod['Instruccion'] = m_p.group(3).strip() if m_p else primera_resp
                                nuevo_hist = "\n".join(lineas_actuales[1:])
                                actualizar_tarea_en_sheet(ws_t, headers_tareas, row_mod, row_mod.get('Status', 'Pendiente'), nuevo_hist)
                            else:
                                actualizar_tarea_en_sheet(ws_t, headers_tareas, row_mod, "Eliminado", "")
                        else:
                            pos_lista = idx_borrar - 1
                            if 0 <= pos_lista < len(lineas_actuales):
                                nuevas_lineas = [l for i, l in enumerate(lineas_actuales) if i != pos_lista]
                                nuevo_hist = "\n".join(nuevas_lineas)
                                actualizar_tarea_en_sheet(ws_t, headers_tareas, row_mod, row_mod.get('Status', 'Pendiente'), nuevo_hist)
                        leer_tareas_normalizadas.clear()

                    with st.expander("🗑️ Borrar un mensaje enviado por error en este chat", expanded=False):
                        c_del_sel, c_del_btn = st.columns([3.4, 1.4], vertical_alignment="bottom")
                        with c_del_sel:
                            st.selectbox(
                                "Selecciona la línea que deseas eliminar:",
                                options=opciones_lineas_del,
                                index=len(opciones_lineas_del) - 1,
                                key=key_sel_del
                            )
                        with c_del_btn:
                            st.button(
                                "🗑️ Eliminar Línea",
                                key=f"btn_del_msg_{chat_sel_row}",
                                use_container_width=True,
                                on_click=eliminar_linea_chat_cb,
                                args=(row_activa, lineas_hist_del, key_sel_del)
                            )
            else:
                st.info("🎉 No tienes conversaciones ni tareas activas por el momento.")

        # --- TAB 2: NUEVO CHAT / TAREA ---
        with tabs_tareas[1]:
            st.subheader("Abrir Nuevo Tema / Siniestro")
            v_nc = st.session_state.get('ver_nuevo_chat_form', 0)

            col_nueva_1, col_nueva_2 = st.columns(2)
            with col_nueva_1:
                usuarios_destino = st.multiselect(
                    "Participante(s) — 1 privado, varios para grupo:",
                    options=usuarios_reales,
                    placeholder="Selecciona uno o varios...",
                    key=f"nc_dest_{v_nc}"
                )
            with col_nueva_2:
                siniestro_seleccionado = st.selectbox("Tema / Siniestro (Solo Activos):", ["Seleccionar...", "General (Tema Libre)"] + lista_siniestros, key=f"nc_sin_{v_nc}")
            
            tema_libre = ""
            piezas_seleccionadas = []
            if siniestro_seleccionado == "General (Tema Libre)":
                tema_libre = st.text_input("Escribe el Asunto o Siniestro Histórico:", placeholder="Ej. Siniestro Histórico B801122 / Duda de Facturación", key=f"nc_tema_{v_nc}")
            elif siniestro_seleccionado != "Seleccionar..." and not df_uni_local.empty and col_desc_loc:
                id_sin_puro = siniestro_seleccionado.split(" | ")[0].strip()
                piezas_del_siniestro = df_uni_local[df_uni_local[col_sin_loc].astype(str).str.strip() == id_sin_puro][col_desc_loc].dropna().unique().tolist()
                piezas_seleccionadas = st.multiselect("Selecciona la(s) Pieza(s) implicada(s):", piezas_del_siniestro, key=f"nc_pzas_{v_nc}")

            instruccion_nueva = st.text_area("Mensaje inicial:", key=f"nc_msg_{v_nc}")
            adj_inicial_up = st.file_uploader(
                "📎 Adjuntar imagen o documento PDF/Excel/Word/CSV (Opcional, máx. 450 KB):",
                type=["png", "jpg", "jpeg", "webp", "pdf", "docx", "doc", "xlsx", "xls", "csv"],
                key=f"up_foto_nuevo_chat_{v_nc}"
            )
            
            if st.button("📤 Iniciar Conversación", type="primary", key=f"btn_iniciar_conv_{v_nc}"):
                if usuarios_destino and siniestro_seleccionado != "Seleccionar..." and (instruccion_nueva.strip() or adj_inicial_up is not None):
                    receptor_final = ", ".join(usuarios_destino)
                    import uuid
                    tz_mx_t = datetime.timezone(datetime.timedelta(hours=-6))
                    id_tarea = str(uuid.uuid4().hex)[:6].upper()
                    fecha_hoy = datetime.datetime.now(tz_mx_t).strftime("%Y-%m-%d %H:%M")
                    
                    if siniestro_seleccionado == "General (Tema Libre)":
                        ref_final = f"General: {tema_libre.strip()}" if tema_libre.strip() else "General"
                    else:
                        ref_final = siniestro_seleccionado
                        if piezas_seleccionadas:
                            ref_final += f" | ⚙️ Piezas: {', '.join(piezas_seleccionadas)}"

                    try:
                        tag_adj_ini = ""
                        if adj_inicial_up is not None:
                            tag_adj_ini = guardar_adjunto_chat_en_sheet(adj_inicial_up.getvalue(), adj_inicial_up.name, usuario_activo_real)

                        msg_ini_guardar = f"{tag_adj_ini} {instruccion_nueva.strip()}".strip() if (tag_adj_ini and instruccion_nueva.strip()) else (tag_adj_ini or instruccion_nueva.strip())

                        ws_tareas = doc.worksheet("Gestor_Tareas")
                        if not headers_tareas:
                            headers_tareas = [str(h).strip() for h in ws_tareas.row_values(1)]
                        if not headers_tareas:
                            headers_tareas = ["ID_Tarea", "Fecha_Creacion", "Emisor", "Receptor", "Siniestro / Taller / Piezas", "Instruccion", "Status", "Respuesta"]
                        headers_up = [str(h).strip().upper().rstrip(':') for h in headers_tareas]
                        nueva_fila = [""] * len(headers_tareas)

                        def pos_col(posibles, default_idx):
                            for p in posibles:
                                if p in headers_up:
                                    return headers_up.index(p)
                            return default_idx if default_idx < len(headers_tareas) else -1

                        i_id = pos_col(["ID_TAREA"], 0)
                        i_fe = pos_col(["FECHA_CREACION"], 1)
                        i_em = pos_col(["EMISOR"], 2)
                        i_re = pos_col(["RECEPTOR"], 3)
                        i_rf = pos_col(["SINIESTRO / TALLER / PIEZAS", "REFERENCIA"], 4)
                        i_in = pos_col(["INSTRUCCION"], 5)
                        i_st = pos_col(["STATUS", "ESTATUS"], 6)
                        i_rp = pos_col(["RESPUESTA"], 7)

                        if i_id >= 0: nueva_fila[i_id] = id_tarea
                        if i_fe >= 0: nueva_fila[i_fe] = fecha_hoy
                        if i_em >= 0: nueva_fila[i_em] = usuario_activo_real
                        if i_re >= 0: nueva_fila[i_re] = receptor_final
                        if i_rf >= 0: nueva_fila[i_rf] = ref_final
                        if i_in >= 0: nueva_fila[i_in] = msg_ini_guardar
                        if i_st >= 0: nueva_fila[i_st] = "Pendiente"
                        if i_rp >= 0: nueva_fila[i_rp] = ""

                        ws_tareas.append_row(nueva_fila, value_input_option='USER_ENTERED')
                        leer_tareas_normalizadas.clear()
                        st.session_state['ver_nuevo_chat_form'] = v_nc + 1
                        st.toast(f"✅ Conversación iniciada con {receptor_final}", icon="✅")
                        time.sleep(0.4)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error al guardar: {e}")
                else:
                    st.warning("⚠️ Selecciona el participante, el tema/siniestro y escribe un mensaje o adjunta un archivo.")    

        # --- TAB 3: HISTORIAL DE FINALIZADOS ---
        with tabs_tareas[2]:
            if not chats_finalizados.empty:
                cols_fin = [c for c in ['Fecha_Creacion', 'Emisor', 'Receptor', 'Siniestro / Taller / Piezas', 'Instruccion', 'Respuesta'] if c in chats_finalizados.columns]
                st.dataframe(chats_finalizados[cols_fin], hide_index=True, use_container_width=True)
            else:
                st.info("No hay conversaciones finalizadas en el archivo.")

# ==============================================================================
# === MODO VENTANA INDEPENDIENTE DE TAREAS (?vista=tareas) + AVISO SONORO ===
# ==============================================================================
@st.fragment(run_every=35)
def monitor_sonoro_tareas():
    """Revisa cada 35s si llegaron mensajes nuevos y reproduce un tono discreto."""
    import streamlit.components.v1 as components
    leer_tareas_normalizadas.clear()
    n_ahora = contar_tareas_pendientes(usuario_activo)
    n_prev = st.session_state.get('_ultimo_conteo_sonoro', n_ahora)
    if n_ahora > n_prev:
        st.toast(f"🔔 ¡Tienes {n_ahora} tarea(s)/mensaje(s) pendiente(s)!", icon="💬")
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
                gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.45);
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.start();
                osc.stop(ctx.currentTime + 0.45);
            } catch (e) {}
            </script>
        """, height=0)
    st.session_state['_ultimo_conteo_sonoro'] = n_ahora

if st.query_params.get("vista") == "tareas":
    st.session_state['chat_flotante_estado'] = 'abierto'
    monitor_sonoro_tareas()
    renderizar_widget_tareas_flotante()
    st.markdown("""
        <style>
        div[data-testid="stHorizontalBlock"]:has([data-testid="stImage"]):has([data-testid="stRadio"]),
        .st-key-pmr_chat_float_min {
            display: none !important;
        }
        .stApp, div[data-testid="stAppViewContainer"], .main {
            background-color: #05070A !important;
        }
        .st-key-pmr_chat_float_open,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.pmr-chat-float-open) {
            position: fixed !important;
            top: 0px !important;
            left: 0px !important;
            right: 0px !important;
            bottom: 0px !important;
            width: 100vw !important;
            max-width: 100vw !important;
            height: 100vh !important;
            max-height: 100vh !important;
            border-radius: 0px !important;
            border: none !important;
            box-shadow: none !important;
            z-index: 999999 !important;
            background-color: #05070A !important;
            padding: 12px 16px !important;
        }
        .st-key-pmr_chat_msgs_box {
            margin-bottom: 8px !important;
        }
        /* Frame independiente para la barra de botones */
        .st-key-pmr_chat_input_box {
            background-color: #0D1418 !important;
            border: 1px solid #222E35 !important;
            border-radius: 10px !important;
            padding: 8px 10px !important;
            position: relative !important;
            z-index: 10 !important;
        }
        /* Forzar botones en una sola fila compacta en móvil */
        .st-key-mob_top_bar div[data-testid="stHorizontalBlock"],
        .st-key-mob_msg_row div[data-testid="stHorizontalBlock"],
        .st-key-mob_tools_row div[data-testid="stHorizontalBlock"] {
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            gap: 6px !important;
            align-items: center !important;
        }
        .st-key-mob_top_bar div[data-testid="stColumn"],
        .st-key-mob_msg_row div[data-testid="stColumn"],
        .st-key-mob_tools_row div[data-testid="stColumn"] {
            min-width: 0px !important;
            width: auto !important;
        }
        .st-key-mob_top_bar div[data-testid="stColumn"]:nth-child(1) { flex: 1.15 1 0% !important; }
        .st-key-mob_top_bar div[data-testid="stColumn"]:nth-child(2) { flex: 0 0 46px !important; }
        .st-key-mob_top_bar div[data-testid="stColumn"]:nth-child(3) { flex: 1.25 1 0% !important; }
        .st-key-mob_top_bar div.stButton > button,
        .st-key-mob_top_bar [data-testid="stPopover"] > button {
            min-height: 2.2rem !important;
            height: 2.2rem !important;
            padding: 0px 8px !important;
            font-size: 0.84rem !important;
        }
        .st-key-mob_msg_row div[data-testid="stColumn"]:nth-child(1) { flex: 1 1 auto !important; }
        .st-key-mob_msg_row div[data-testid="stColumn"]:nth-child(2) { flex: 0 0 54px !important; }
        .st-key-mob_msg_row div.stButton > button {
            min-height: 2.4rem !important;
            height: 2.4rem !important;
            padding: 0px !important;
        }
        .st-key-mob_tools_row div[data-testid="stColumn"] { flex: 1 1 0% !important; }
        .st-key-mob_tools_row [data-testid="stPopover"] > button,
        .st-key-mob_tools_row [data-testid="stFileUploaderDropzone"],
        .st-key-mob_tools_row [data-testid="stFileUploaderDropzone"] button {
            min-height: 2.2rem !important;
            height: 2.2rem !important;
            font-size: 0.84rem !important;
        }
        </style>
    """, unsafe_allow_html=True)
    st.stop()

@st.dialog("📖 Directorio Operativo", width="large")
def abrir_directorio():
    st.subheader("Buscador de Contactos")
    busqueda_dir = st.text_input("🔍 Buscar por Nombre, Taller o Proveedor:", placeholder="Ej. Taller Bajio, Autopartes Monterrey...")
            
    if busqueda_dir:
        doc = init_connection()
        encontrados = 0
        
        try:
            ws_t = doc.worksheet("BD_TALLERES")
            df_t = pd.DataFrame(ws_t.get_all_records())
            mask_t = df_t.astype(str).apply(lambda row: row.str.contains(busqueda_dir, case=False, na=False)).any(axis=1)
            res_t = df_t[mask_t]
            if not res_t.empty:
                st.markdown("#### 🏢 Resultados en Talleres (CDR)")
                st.dataframe(res_t, hide_index=True, use_container_width=True)
                encontrados += len(res_t)
        except Exception:
            pass

        try:
            ws_p = doc.worksheet("BD_PROVEEDORES")
            df_p = pd.DataFrame(ws_p.get_all_records())
            mask_p = df_p.astype(str).apply(lambda row: row.str.contains(busqueda_dir, case=False, na=False)).any(axis=1)
            res_p = df_p[mask_p]
            if not res_p.empty:
                st.markdown("#### 📦 Resultados en Proveedores")
                st.dataframe(res_p, hide_index=True, use_container_width=True)
                encontrados += len(res_p)
        except Exception:
            pass

        if encontrados == 0:
            st.warning(f"No se encontraron coincidencias para '{busqueda_dir}'.")

@st.dialog("📸 Visor y Descargador de Fotos (GNP Inpart)", width="large")
def abrir_visor_fotos_inpart():
    import io
    import glob
    import shutil
    import zipfile
    import subprocess
    import sys

    st.caption("Filtra un pedido activo de GNP o escribe cualquier Número de Pedido / Cotización manualmente para descargar su galería completa en alta resolución.")

    # Cargar pedidos de GNP activos (vivos en el Dashboard) directo desde BD_UNIFICADA
    df_gnp_f = pd.DataFrame()
    try:
        doc_f = init_connection()
        datos_f = doc_f.worksheet("BD_UNIFICADA").get_all_values()
        if len(datos_f) > 1:
            df_base_f = pd.DataFrame(datos_f[1:], columns=[str(h).strip() for h in datos_f[0]])
            c_ase_f = next((c for c in df_base_f.columns if "ASEGURADORA" in str(c).upper()), None)
            c_id_f = next((c for c in df_base_f.columns if "SINIESTRO" in str(c).upper() or "PEDIDO" in str(c).upper()), None)
            c_tal_f = next((c for c in df_base_f.columns if "TALLER" in str(c).upper() or "CDR" in str(c).upper()), None)
            c_mar_f = next((c for c in df_base_f.columns if "MARCA" in str(c).upper()), None)
            c_mod_f = next((c for c in df_base_f.columns if "MODELO" in str(c).upper()), None)
            c_ano_f = next((c for c in df_base_f.columns if "AÑO" in str(c).upper() or "ANO" in str(c).upper()), None)
            c_est_f = next((c for c in df_base_f.columns if "ESTATUS" in str(c).upper() and "ENV" not in str(c).upper() and "PAGO" not in str(c).upper()), None)

            if c_ase_f:
                df_gnp_f = df_base_f[df_base_f[c_ase_f].astype(str).str.upper().str.contains("GNP", na=False)].copy()
            else:
                df_gnp_f = df_base_f.copy()

            estatus_inactivos_f = ["CANCELADO", "RECIBIDO", "FACTURADO", "REEMBOLSADO", "PÉRDIDA TOTAL", "PERDIDA TOTAL", "PAGO DE DAÑOS", "PAGO DE DANOS"]
            if not df_gnp_f.empty and c_est_f:
                df_gnp_f = df_gnp_f[~df_gnp_f[c_est_f].astype(str).str.strip().str.upper().isin(estatus_inactivos_f)].copy()

            if not df_gnp_f.empty and c_id_f:
                df_gnp_f['_ID_Limpio'] = df_gnp_f[c_id_f].astype(str).str.strip().str.removesuffix('.0')
                df_gnp_f = df_gnp_f[df_gnp_f['_ID_Limpio'] != ''].drop_duplicates(subset=['_ID_Limpio']).copy()
                df_gnp_f['_Taller_Limpio'] = df_gnp_f[c_tal_f].astype(str).str.strip() if c_tal_f else "S/D"
                df_gnp_f['_Etiqueta'] = df_gnp_f.apply(
                    lambda r: f"{r['_ID_Limpio']} | {str(r.get(c_mar_f,'')).strip()} {str(r.get(c_mod_f,'')).strip()} {str(r.get(c_ano_f,'')).strip().removesuffix('.0')} | {r['_Taller_Limpio']}",
                    axis=1
                )
    except Exception:
        df_gnp_f = pd.DataFrame()

    # Filtros estilo Panel Operativo + Captura Manual
    cf1, cf2, cf3 = st.columns([1.2, 1.8, 1.1], vertical_alignment="bottom")
    with cf1:
        talleres_gnp = sorted([t for t in df_gnp_f['_Taller_Limpio'].dropna().unique() if t]) if not df_gnp_f.empty else []
        taller_f_sel = st.selectbox("🏢 1. Filtrar por Taller:", ["Todos..."] + talleres_gnp, key="sel_tal_fotos_gnp")

    with cf2:
        df_gnp_sub = df_gnp_f[df_gnp_f['_Taller_Limpio'] == taller_f_sel] if (not df_gnp_f.empty and taller_f_sel != "Todos...") else df_gnp_f
        opciones_ped = sorted(df_gnp_sub['_Etiqueta'].dropna().unique().tolist()) if not df_gnp_sub.empty else []
        pedido_f_sel = st.selectbox("🚗 2. Seleccionar Pedido - Vehículo:", ["Seleccionar..."] + opciones_ped, key="sel_ped_fotos_gnp")

    with cf3:
        pedido_manual_in = st.text_input("✍️ O escribir No. Pedido:", placeholder="Ej. 1160098", key="inp_ped_manual_gnp")

    pedido_objetivo = pedido_manual_in.strip() if pedido_manual_in.strip() else (pedido_f_sel.split(" | ")[0].strip() if pedido_f_sel != "Seleccionar..." else "")

    c_btn_ext, c_btn_limp, c_modo_f = st.columns([1.8, 0.8, 1.1], vertical_alignment="center")
    with c_modo_f:
        modo_f_vis = st.radio("Modo:", ["Oculto (Rápido)", "Visual (PC Local)"], horizontal=True, key="rad_modo_fotos_gnp", label_visibility="collapsed")

    def limpiar_galeria_gnp_cb():
        carp_old = st.session_state.pop('fotos_gnp_carpeta', '')
        if carp_old and os.path.exists(carp_old):
            shutil.rmtree(carp_old, ignore_errors=True)
        st.session_state.pop('fotos_gnp_pedido', None)
        st.session_state.pop('fotos_gnp_log', None)

    c_btn_limp.button("🧹 Limpiar Pantalla", use_container_width=True, key="btn_limp_fotos_gnp", on_click=limpiar_galeria_gnp_cb)

    if c_btn_ext.button(f"📸 Extraer Fotografías del Pedido {pedido_objetivo}" if pedido_objetivo else "📸 Extraer Fotografías de Inpart", type="primary", use_container_width=True, disabled=(not pedido_objetivo)):
        carpeta_out = os.path.join(tempfile.gettempdir(), f"fotos_gnp_{pedido_objetivo}")
        if os.path.exists(carpeta_out):
            shutil.rmtree(carpeta_out, ignore_errors=True)
        os.makedirs(carpeta_out, exist_ok=True)

        arg_v = "--oculto" if "Oculto" in modo_f_vis else "--visual"
        with st.spinner(f"Conectando a GNP Inpart y descargando galería en Alta Resolución del pedido {pedido_objetivo}..."):
            try:
                with open("credentials.json", "w", encoding="utf-8") as f:
                    f.write(st.secrets["google_credentials"])
                subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=False)
                res_p = subprocess.run(
                    [sys.executable, "-u", "gnp_inpart.py", "--fotos", str(pedido_objetivo), carpeta_out, arg_v],
                    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300
                )
                st.session_state['fotos_gnp_carpeta'] = carpeta_out
                st.session_state['fotos_gnp_pedido'] = pedido_objetivo
                st.session_state['fotos_gnp_log'] = (res_p.stdout or "") + "\n" + (res_p.stderr or "")
            except Exception as e_f:
                st.error(f"Error al extraer fotos: {e_f}")
            finally:
                if os.path.exists("credentials.json"):
                    os.remove("credentials.json")

    carpeta_activa = st.session_state.get('fotos_gnp_carpeta', '')
    ped_activo_f = st.session_state.get('fotos_gnp_pedido', '')
    if carpeta_activa and os.path.exists(carpeta_activa):
        archivos_img = sorted(glob.glob(os.path.join(carpeta_activa, "*.jpg")) + glob.glob(os.path.join(carpeta_activa, "*.jpeg")) + glob.glob(os.path.join(carpeta_activa, "*.png")))
        if archivos_img:
            st.success(f"✅ Se extrajeron **{len(archivos_img)} fotografías** del Pedido GNP **`{ped_activo_f}`**.")

            # 1. Empaquetar en .ZIP
            buf_zip = io.BytesIO()
            with zipfile.ZipFile(buf_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                for ruta_i in archivos_img:
                    zf.write(ruta_i, arcname=os.path.basename(ruta_i))

            # 2. Empaquetar en Álbum .PDF
            pdf_f = FPDF(orientation='P', unit='mm', format='A4')
            pdf_f.set_auto_page_break(auto=False)
            for idx_i, ruta_i in enumerate(archivos_img):
                if idx_i % 2 == 0:
                    pdf_f.add_page()
                    pdf_f.set_font("Arial", 'B', 11)
                    pdf_f.cell(0, 8, f"PMR HUB AI - EXPEDIENTE FOTOGRAFICO GNP PEDIDO {ped_activo_f}", ln=True, align='C')
                y_pos = 22 if (idx_i % 2 == 0) else 155
                pdf_f.set_xy(15, y_pos)
                pdf_f.set_font("Arial", 'B', 9)
                pdf_f.cell(0, 6, f"Foto #{idx_i+1}: {os.path.basename(ruta_i)}", ln=True)
                try:
                    pdf_f.image(ruta_i, x=20, y=y_pos + 7, w=170, h=115)
                except Exception:
                    pass
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pf:
                pdf_f.output(tmp_pf.name)
                with open(tmp_pf.name, "rb") as f_rb: bytes_pdf_fotos = f_rb.read()

            cd1, cd2 = st.columns(2)
            cd1.download_button(
                label=f"📦 Descargar Todas las Fotos en .ZIP ({len(archivos_img)} imgs)",
                data=buf_zip.getvalue(),
                file_name=f"Fotos_GNP_{ped_activo_f}.zip",
                mime="application/zip",
                type="primary",
                use_container_width=True
            )
            cd2.download_button(
                label="📄 Descargar Álbum Fotográfico en .PDF",
                data=bytes_pdf_fotos,
                file_name=f"Album_GNP_{ped_activo_f}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

            st.markdown("##### 🔍 Vista Previa en Grande")
            cols_gal = st.columns(3)
            for i_img, r_img in enumerate(archivos_img):
                with cols_gal[i_img % 3]:
                    st.image(r_img, caption=os.path.basename(r_img), use_container_width=True)
        else:
            st.warning(f"No se encontraron imágenes adjuntas en el pedido {ped_activo_f}.")
            if st.session_state.get('fotos_gnp_log'):
                with st.expander("Ver bitácora técnica"):
                    st.code(st.session_state['fotos_gnp_log'])

# Inyección de los botones directamente en las columnas declaradas arriba
with col_btn_dir:
    if st.button("📖 Directorio", use_container_width=True):
        abrir_directorio()

with col_btn_fot:
    if st.button("📸 Fotos", help="Extraer y descargar fotografías de pedidos GNP Inpart", use_container_width=True):
        st.session_state.pop('fotos_gnp_carpeta', None)
        st.session_state.pop('fotos_gnp_pedido', None)
        st.session_state.pop('fotos_gnp_log', None)
        abrir_visor_fotos_inpart()


with col_btn_gua:
    btn_guardar = st.button("💾 Guardar", type="primary", use_container_width=True)
    espacio_spinner = st.empty()

# Renderizar el Centro de Tareas Flotante (Abierto o Minimizado en esquina inferior derecha)
renderizar_widget_tareas_flotante()


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
        c_est_h = next((c for c in df_historico.columns if "ESTATUS" in str(c).upper() or "STATUS" in str(c).upper()), None)
        if c_est_h:
            df_hist_activos = df_historico[df_historico[c_est_h].astype(str).str.upper().str.contains("PROCESO DE REEMBOLSO|RECOLECC|ENTREGADO|PAGO A TALLER", na=False)].copy()
            if not df_hist_activos.empty:
                df_completo = pd.concat([df_completo, df_hist_activos], ignore_index=True)
                # Evitar que una pieza que esté en ambas hojas se cuente doble:
                c_id_dedup = next((c for c in df_completo.columns if "SINIESTRO" in str(c).upper()), None)
                c_desc_dedup = next((c for c in df_completo.columns if "DESCRIPCI" in str(c).upper() or "REFACCI" in str(c).upper()), None)
                if c_id_dedup and c_desc_dedup:
                    df_completo = df_completo.drop_duplicates(subset=[c_id_dedup, c_desc_dedup], keep='first'). reset_index(drop=True)

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
    col_guia = next((c for c in df_trabajo_completo.columns if ("GUIA" in str(c).upper() or "GUÍA" in str(c).upper()) and "DEV" not in str(c).upper() and "RET" not in str(c).upper()), None)
    col_guia_dev = next((c for c in df_trabajo_completo.columns if ("DEV" in str(c).upper() or "RETORNO" in str(c).upper()) and ("GUIA" in str(c).upper() or "GUÍA" in str(c).upper())), None)
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
# === MÁSCARA COMERCIAL (MODO DEMO) ===
# ==============================================================================
if rol_activo == 'DEMO':
    def enmascarar_dinero(df):
        if not df.empty:
            cols_dinero = [c for c in df.columns if any(p in str(c).upper() for p in ["PRECIO", "COSTO"])]
            for c in cols_dinero:
                df[c] = "$ ***"
        return df
    
    df_completo = enmascarar_dinero(df_completo)
    df_trabajo = enmascarar_dinero(df_trabajo)
    df_proceso = enmascarar_dinero(df_proceso)
    df_trabajo_completo = enmascarar_dinero(df_trabajo_completo)
    df_recoleccion_total = enmascarar_dinero(df_recoleccion_total)
    if not df_compras.empty:
        df_compras = enmascarar_dinero(df_compras)

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
        
        # EL CAMBIO: Arrastrar las de HOY + TODAS las que se hayan quedado PENDIENTES
        cond_hoy = df_rutas['FECHA'].astype(str).str.contains(fecha_hoy_str, na=False)
        cond_pendiente = df_rutas['ESTATUS'].astype(str).str.strip().str.upper() == 'PENDIENTE'
        
        df_rutas_dia = df_rutas[cond_hoy | cond_pendiente].copy()
        
        # Limpieza de espacios con .str.strip()
        df_rutas_pendientes = df_rutas_dia[df_rutas_dia['ESTATUS'].astype(str).str.strip().str.upper() == 'PENDIENTE']
        df_rutas_completados = df_rutas_dia[df_rutas_dia['ESTATUS'].astype(str).str.strip().str.upper() == 'COMPLETADO']
        
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
            
            # --- FILTROS GLOBALES OPERACIÓN DEL DÍA ---
            df_mon['Filtro_Siniestro'] = df_mon[col_id].astype(str).str.strip() + " | " + df_mon['Vehiculo_Info']

            st.markdown("#### 🎛️ Filtros de Búsqueda (Logística)")
            f_col1, f_col2, f_col3, f_col4 = st.columns([1, 1, 1.5, 1.5])
            
            with f_col1:
                aseg_sel_od = st.multiselect("🛡️ Aseguradora:", sorted(list(df_mon['Aseguradora'].dropna().unique())), placeholder="Todas...")
            with f_col2:
                df_m1 = df_mon[df_mon['Aseguradora'].isin(aseg_sel_od)] if aseg_sel_od else df_mon
                taller_sel_od = st.multiselect("🏢 Taller:", sorted(list(df_m1[col_taller].dropna().astype(str).unique())), placeholder="Todos...")
            with f_col3:
                df_m2 = df_m1[df_m1[col_taller].astype(str).isin(taller_sel_od)] if taller_sel_od else df_m1
                sin_sel_od = st.multiselect("🚗 Siniestro - Auto:", sorted(list(df_m2['Filtro_Siniestro'].dropna().unique())), placeholder="Todos...")
            with f_col4:
                df_m3 = df_m2[df_m2['Filtro_Siniestro'].isin(sin_sel_od)] if sin_sel_od else df_m2
                pza_sel_od = st.multiselect("⚙️ Refacción:", sorted(list(df_m3[col_desc].dropna().astype(str).unique())), placeholder="Todas...")

            # Aplicar filtros a la base principal de OD
            if aseg_sel_od: df_mon = df_mon[df_mon['Aseguradora'].isin(aseg_sel_od)]
            if taller_sel_od: df_mon = df_mon[df_mon[col_taller].astype(str).isin(taller_sel_od)]
            if sin_sel_od: df_mon = df_mon[df_mon['Filtro_Siniestro'].isin(sin_sel_od)]
            if pza_sel_od: df_mon = df_mon[df_mon[col_desc].astype(str).isin(pza_sel_od)]
            # -------------------------------------------
            
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
                    cols_ver_recol = ['Aseguradora', col_taller, col_id, 'Vehiculo_Info', col_desc, col_paqueteria]
                    if col_guia: cols_ver_recol.append(col_guia)
                    if col_guia_dev: cols_ver_recol.append(col_guia_dev)
                    cols_ver_recol.extend([col_estatus_envio, col_comentarios])
                    
                    rename_recol = {col_taller: 'Taller', col_id: 'Siniestro', 'Vehiculo_Info': 'Auto', col_desc: 'Pieza', col_paqueteria: 'Paquetería'}
                    if col_guia: rename_recol[col_guia] = 'Guía Ida'
                    if col_guia_dev: rename_recol[col_guia_dev] = 'Guía Devolución'
                    rename_recol.update({col_estatus_envio: 'Rastreo API', col_comentarios: 'Observaciones'})
                    
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
    regex_excluir_kpi = "CONFIRMAR|ENTREGADO|PAGO A TALLER|RECIBIDO|FACTURADO|CANCELADO|RECOLEC|REEMBOLSO|PÉRDIDA TOTAL|PAGO DE DAÑOS"

    if col_estatus and not df_proceso.empty:
        est_str = df_proceso[col_estatus].fillna('').astype(str).str.strip()
        est_up = est_str.str.upper()
        mask_activos_surtido = (~est_up.str.contains(regex_excluir_kpi)) & (est_str != "")
    else:
        mask_activos_surtido = pd.Series(False, index=df_proceso.index)

    if col_vencimiento and not df_proceso.empty:
        fechas_venc_dt = df_proceso[col_vencimiento].apply(parse_dt_safe_op)
        vencidas_pasadas_kpi = len(df_proceso[(fechas_venc_dt < hoy_dt) & (df_proceso[col_vencimiento] != '') & mask_activos_surtido])
        vencen_hoy = len(df_proceso[(df_proceso[col_vencimiento] == hoy_str) & mask_activos_surtido])
    else:
        vencidas_pasadas_kpi = 0
        vencen_hoy = 0

    recolecciones = len(df_recoleccion_total)
    por_confirmar_kpi = len(df_proceso[(df_proceso[col_estatus].astype(str).str.upper().str.contains("CONFIRMAR") | (df_proceso[col_estatus].astype(str).str.strip() == "")) & (~df_proceso[col_estatus].astype(str).str.upper().isin(excluir_kpi))]) if col_estatus and not df_proceso.empty else 0
    
    # Si quieres que "En Proceso" muestre solo las piezas en surtido/tránsito (12), usa mask_activos_surtido:
    en_proceso = len(df_proceso[mask_activos_surtido]) if col_estatus and not df_proceso.empty else len(df_proceso)
    partidas_por_facturar = len(df_trabajo[df_trabajo[col_estatus].astype(str).str.strip().str.upper() == "RECIBIDO"]) if col_estatus and not df_trabajo.empty else 0
    
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
    
    def norm_cia_po(val):
        v = str(val).strip().upper()
        if "GNP" in v: return "GNP"
        if "MULTI" in v: return "MULTI"
        return v if v not in ["", "NAN", "NONE"] else "OTRA"

    df_proceso['Compania_Filtro'] = df_proceso[col_aseg].apply(norm_cia_po) if (col_aseg and col_aseg in df_proceso.columns) else "MULTI"
    if not df_recoleccion_total.empty:
        df_recoleccion_total['Compania_Filtro'] = df_recoleccion_total[col_aseg].apply(norm_cia_po) if (col_aseg and col_aseg in df_recoleccion_total.columns) else "MULTI"

    if col_estatus:
        df_proceso = df_proceso[~df_proceso[col_estatus].astype(str).str.upper().isin(excluir_kpi)]

    filtro_col0, filtro_col1, filtro_col2, filtro_col3, filtro_col4, filtro_col5 = st.columns([0.9, 1.1, 0.9, 1.4, 1.1, 1.4])

    with filtro_col0:
        compania_sel = st.multiselect("🛡️ Compañía:", sorted([str(c) for c in df_proceso['Compania_Filtro'].dropna().unique() if str(c).strip() != '']), placeholder="Todas...")
    with filtro_col1:
        df_t1 = df_proceso.copy()
        if compania_sel: df_t1 = df_t1[df_t1['Compania_Filtro'].astype(str).isin(compania_sel)]
        taller_sel = st.multiselect("🏢 Taller:", sorted([str(t) for t in df_t1[col_taller].dropna().unique() if str(t).strip() != '']) if col_taller else [], placeholder="Todos...")
    with filtro_col2:
        df_t2 = df_t1.copy()
        if taller_sel: df_t2 = df_t2[df_t2[col_taller].astype(str).isin(taller_sel)]
        estatus_sel = st.multiselect("📊 Estatus:", sorted([str(e) for e in df_t2[col_estatus].dropna().unique() if str(e).strip() != '']) if col_estatus else [], placeholder="Todos...")
    with filtro_col3:
        df_t3 = df_t2.copy()
        if estatus_sel: df_t3 = df_t3[df_t3[col_estatus].astype(str).isin(estatus_sel)]
        siniestro_sel = st.multiselect("🚗 Siniestro - Vehículo:", sorted(list(df_t3['Filtro_Siniestro'].dropna().unique())) if 'Filtro_Siniestro' in df_t3.columns else [], placeholder="Todos...")
    with filtro_col4:
        df_t4 = df_t3.copy()
        if siniestro_sel: df_t4 = df_t4[df_t4['Filtro_Siniestro'].isin(siniestro_sel)]
        vin_sel = st.multiselect("🏷️ VIN / Serie:", sorted(list(df_t4[col_vin].dropna().astype(str).unique())) if col_vin and col_vin in df_t4.columns else [], placeholder="Todos...")
    with filtro_col5:
        df_t5 = df_t4.copy()
        if vin_sel: df_t5 = df_t5[df_t5[col_vin].astype(str).isin(vin_sel)]
        desc_sel = st.multiselect("⚙️ Refacción:", sorted(list(df_t5[col_desc].dropna().astype(str).unique())) if col_desc in df_t5.columns else [], placeholder="Todas...")

    df_filtrado = df_proceso.copy()
    if compania_sel: df_filtrado = df_filtrado[df_filtrado['Compania_Filtro'].astype(str).isin(compania_sel)]
    if taller_sel: df_filtrado = df_filtrado[df_filtrado[col_taller].astype(str).isin(taller_sel)]
    if estatus_sel: df_filtrado = df_filtrado[df_filtrado[col_estatus].astype(str).isin(estatus_sel)]
    if siniestro_sel: df_filtrado = df_filtrado[df_filtrado['Filtro_Siniestro'].isin(siniestro_sel)]
    if vin_sel: df_filtrado = df_filtrado[df_filtrado[col_vin].astype(str).isin(vin_sel)]
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
    if compania_sel and 'Compania_Filtro' in df_recoleccion.columns:
        df_recoleccion = df_recoleccion[df_recoleccion['Compania_Filtro'].astype(str).isin(compania_sel)]
    if taller_sel: df_recoleccion = df_recoleccion[df_recoleccion[col_taller].astype(str).isin(taller_sel)]
    if siniestro_sel:
        ids_sel = [s.split(" - ")[0] for s in siniestro_sel]
        df_recoleccion = df_recoleccion[df_recoleccion[col_id].isin(ids_sel)]
    if vin_sel: df_recoleccion = df_recoleccion[df_recoleccion[col_vin].astype(str).isin(vin_sel)] # <-- LÍNEA NUEVA
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
        lbl_po("📋", "Confirmados", df_asignados),
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
                    # 1. Definimos la ventana emergente justo ANTES del ciclo for
                    @st.dialog("📱 Mensaje para WhatsApp")
                    def mostrar_dialogo_wa(mensaje):
                        st.caption("Haz clic en el ícono de la esquina superior derecha del cuadro para copiar:")
                        st.code(mensaje, language="markdown")

                    # 2. Tu ciclo for principal modificado
                    for siniestro_auto, df_grupo in df_taller.groupby('Agrupador_Visual'):
                        aseg_raw_g = str(df_grupo[col_aseg].iloc[0]).strip().upper() if (col_aseg and col_aseg in df_grupo.columns) else "MULTI"
                        badge_aseg = "🟠 GNP" if "GNP" in aseg_raw_g else "🔵 MULTI"

                        col_tit, col_btn_wa = st.columns([4, 1.2])
                        with col_tit:
                            st.markdown(f"**{badge_aseg} | 🚗 Pedido / Siniestro: `{siniestro_auto}` | {df_grupo['Vehiculo_Info'].iloc[0]}**")
                        with col_btn_wa:
                            if st.button("📱 Generar Mensaje WA", key=f"wa_btn_{taller}_{siniestro_auto}", use_container_width=True):
                                vehiculo_str = df_grupo['Vehiculo_Info'].iloc[0]
                                msg = "🚨 NUEVA ASIGNACIÓN 🚨\n"
                                msg += f"🛡️ Aseguradora: {'GNP' if 'GNP' in aseg_raw_g else 'MULTIASISTENCIA'}\n"
                                msg += f"🏢 Taller: {taller}\n"
                                msg += f"📄 Siniestro: {siniestro_auto}\n"
                                msg += f"🚗 Vehículo: {vehiculo_str}\n\n"
                                msg += "📦 Piezas:\n"
            
                                for _, fila_pza in df_grupo.iterrows():
                                    cant_str = str(fila_pza.get(col_cant, '1')).replace('.0', '').strip()
                                    if not cant_str or cant_str.lower() in ['nan', 'none']: cant_str = '1'
                                    desc_pza = str(fila_pza.get(col_desc, '')).strip()
                                    msg += f"🔹 {cant_str}x {desc_pza}\n"
            
                                mostrar_dialogo_wa(msg)

                        if permiso_edicion: 
                            df_grupo['Confirmar Surtido'] = False; df_grupo['Pago_Danos'] = False; df_grupo['Cancelar'] = False; df_grupo['Pérdida Total'] = False; df_grupo['PDD'] = False
                            cols_visibles = [c for c in [col_id, col_cant, col_desc, col_origen, col_precio, col_vencimiento] if c in df_grupo.columns] + ['Proveedor', 'Costo Compra', 'Confirmar Surtido', 'Pago_Danos', 'Cancelar', 'Pérdida Total', 'PDD'] + [c for c in [col_comentarios] if c in df_grupo.columns]
                            config_conf = base_config.copy()
                            config_conf.update({"Confirmar Surtido": st.column_config.CheckboxColumn("✅ Confirmar", default=False), "Pago_Danos": st.column_config.CheckboxColumn("💵 Pago *", default=False), "Cancelar": st.column_config.CheckboxColumn("🚫 Can", default=False), "Pérdida Total": st.column_config.CheckboxColumn("💥 PT", default=False), "PDD": st.column_config.CheckboxColumn("💸 PDD", default=False), "Proveedor": st.column_config.SelectboxColumn("🏢 Proveedor", options=lista_proveedores), "Costo Compra": st.column_config.NumberColumn("💲 Costo ($)", format="%.2f")})
                            columnas_editables = ['Proveedor', 'Costo Compra', 'Confirmar Surtido', 'Pago_Danos', 'Cancelar', 'Pérdida Total', 'PDD', col_comentarios]
                            k_ed_conf = f"ed_conf_{taller}_{siniestro_auto}"
                            df_editado_parcial = st.data_editor(df_grupo[cols_visibles], column_config=config_conf, disabled=[c for c in cols_visibles if c not in columnas_editables], hide_index=True, use_container_width=True, key=k_ed_conf)
                            for col in df_grupo.columns:
                                if col not in df_editado_parcial.columns: df_editado_parcial[col] = df_grupo[col].values
                            filas_mod_c = [int(i) for i in st.session_state.get(k_ed_conf, {}).get("edited_rows", {}).keys() if str(i).isdigit() and int(i) < len(df_editado_parcial)]
                            if filas_mod_c:
                                dfs_editados_conf.append(df_editado_parcial.iloc[filas_mod_c].copy())
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
                        aseg_raw_g = str(df_grupo[col_aseg].iloc[0]).strip().upper() if (col_aseg and col_aseg in df_grupo.columns) else "MULTI"
                        badge_aseg = "🟠 GNP" if "GNP" in aseg_raw_g else "🔵 MULTI"
                        st.markdown(f"**{badge_aseg} | 🚗 Pedido / Siniestro: `{siniestro_auto}` | {df_grupo['Vehiculo_Info'].iloc[0]}**")
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
                            k_ed_asig = f"ed_{taller}_{siniestro_auto}"
                            df_editado_parcial = st.data_editor(df_grupo[cols_visibles], column_config=config_pedidos, disabled=[c for c in cols_visibles if c not in columnas_editables], hide_index=True, use_container_width=True, key=k_ed_asig)
                            for col in df_grupo.columns:
                                if col not in df_editado_parcial.columns: df_editado_parcial[col] = df_grupo[col].values
                            filas_mod_a = [int(i) for i in st.session_state.get(k_ed_asig, {}).get("edited_rows", {}).keys() if str(i).isdigit() and int(i) < len(df_editado_parcial)]
                            if filas_mod_a:
                                dfs_editados.append(df_editado_parcial.iloc[filas_mod_a].copy())
                        else:
                            cols_visibles = [c for c in [col_id, col_cant, col_desc, col_origen, col_precio, col_vencimiento, col_paqueteria, col_guia, col_estatus_envio, col_remision, col_comentarios] if c in df_grupo.columns]
                            st.dataframe(df_grupo[cols_visibles], column_config=base_config, hide_index=True, use_container_width=True)
            if dfs_editados: df_editado = pd.concat(dfs_editados, ignore_index=True)
        else:
            st.info("No hay pedidos confirmados en proceso con los filtros actuales.")

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
                df_recoleccion['Guia_Retorno'] = df_recoleccion[col_guia_dev].fillna("") if col_guia_dev else ""
                df_recoleccion['Devolucion_Recibida'] = False
                cols_rec = [c for c in [col_id, col_taller, col_cant, col_desc, col_precio, col_estatus] if c in df_recoleccion.columns] + [c for c in [col_paqueteria, col_guia] if c in df_recoleccion.columns] + ['Guia_Retorno', 'En_Retorno', 'Devolucion_Recibida'] + [c for c in [col_comentarios] if c in df_recoleccion.columns]
                config_rec = base_config.copy()
                if col_guia: config_rec[col_guia] = st.column_config.TextColumn("Guía Actual / Ida")
                config_rec["Guia_Retorno"] = st.column_config.TextColumn("🆕 Guía Retorno (Capturar aquí)")
                config_rec["En_Retorno"] = st.column_config.CheckboxColumn("🚚 En Retorno", default=False)
                config_rec["Devolucion_Recibida"] = st.column_config.CheckboxColumn("🏁 Dev. Recibida", default=False)
                cols_edit_rec = [col_paqueteria, col_guia, 'Guia_Retorno', 'En_Retorno', 'Devolucion_Recibida', col_comentarios]
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

    # --- FILTROS GLOBALES DE COMPRAS ---
    c_tall_c = buscar_columna_compras(df_por_comprar, ["TALLER", "CDR"], ["TALLER"]) if not df_por_comprar.empty else None
    c_id_c = buscar_columna_compras(df_por_comprar, ["PEDIDO / SINIESTRO", "SINIESTRO"], ["SINIESTRO"]) if not df_por_comprar.empty else None
    c_desc_c = buscar_columna_compras(df_por_comprar, ["DESCRIPCIÓN", "DESCRIPCION"], ["DESCRIPCI", "REFACCI"]) if not df_por_comprar.empty else None

    st.markdown("#### 🎛️ Filtros de Búsqueda (Compras)")
    opciones_taller = set(); opciones_sin = set(); opciones_pza = set(); opciones_prov = set()
    
    if not df_por_comprar.empty:
        if c_tall_c: opciones_taller.update(df_por_comprar[c_tall_c].dropna().astype(str).tolist())
        if c_id_c: opciones_sin.update(df_por_comprar[c_id_c].dropna().astype(str).tolist())
        if c_desc_c: opciones_pza.update(df_por_comprar[c_desc_c].dropna().astype(str).tolist())
        
    if not df_compras.empty:
        opciones_taller.update(df_compras['Taller'].dropna().astype(str).tolist())
        opciones_sin.update(df_compras['Siniestro'].dropna().astype(str).tolist())
        opciones_pza.update(df_compras['Descripción Pieza'].dropna().astype(str).tolist())
        opciones_prov.update(df_compras['Proveedor'].dropna().astype(str).tolist())
        
    f_c1, f_c2, f_c3, f_c4 = st.columns([1, 1, 1.5, 1])
    with f_c1: f_tall_comp = st.multiselect("🏢 Taller:", sorted(list(opciones_taller)), placeholder="Todos...")
    with f_c2: f_sin_comp = st.multiselect("🚗 Siniestro:", sorted(list(opciones_sin)), placeholder="Todos...")
    with f_c3: f_pza_comp = st.multiselect("⚙️ Refacción:", sorted(list(opciones_pza)), placeholder="Todas...")
    with f_c4: f_prov_comp = st.multiselect("🏭 Proveedor (Llegadas):", sorted(list(opciones_prov)), placeholder="Todos...")

    # Aplicar filtros a Pestaña 1 (Pendientes)
    if not df_por_comprar.empty:
        if f_tall_comp and c_tall_c: df_por_comprar = df_por_comprar[df_por_comprar[c_tall_c].astype(str).isin(f_tall_comp)]
        if f_sin_comp and c_id_c: df_por_comprar = df_por_comprar[df_por_comprar[c_id_c].astype(str).isin(f_sin_comp)]
        if f_pza_comp and c_desc_c: df_por_comprar = df_por_comprar[df_por_comprar[c_desc_c].astype(str).isin(f_pza_comp)]

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
            # Aplicar los filtros globales a Pestaña 2 (Próximas Llegadas)
            if f_tall_comp: df_c = df_c[df_c['Taller'].astype(str).isin(f_tall_comp)]
            if f_sin_comp: df_c = df_c[df_c['Siniestro'].astype(str).isin(f_sin_comp)]
            if f_pza_comp: df_c = df_c[df_c['Descripción Pieza'].astype(str).isin(f_pza_comp)]
            if f_prov_comp: df_c = df_c[df_c['Proveedor'].astype(str).isin(f_prov_comp)]
            
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
                    st.subheader("Datos del Taller")
            
                    asesores_historicos = []
                    if not df_catalogo.empty:
                        col_ase_cat = next((c for c in df_catalogo.columns if "ASESOR" in str(c).upper()), None)
                        if col_ase_cat:
                            asesores_historicos = sorted([str(a).strip().upper() for a in df_catalogo[col_ase_cat].dropna().unique() if str(a).strip() not in ['', 'NAN', 'NONE']])

                    # Fila 1: Taller, Ciudad y Estado
                    c1, c2, c3 = st.columns([2, 2, 2])
                    nuevo_taller = c1.text_input("Nombre del Taller / CDR * (Obligatorio)")
            
                    col_ciudad_cat = next((c for c in df_catalogo.columns if "CIUDAD" in str(c).upper()), None)
                    ciudades_bd = [str(c).strip().title() for c in df_catalogo[col_ciudad_cat].dropna().unique() if str(c).strip() != ''] if col_ciudad_cat else []
                    lista_ciudades = sorted(list(set(ciudades_bd)))
            
                    ciudad_sel = c2.selectbox("Ciudad (Catálogo)", [""] + lista_ciudades)
                    ciudad_manual = c2.text_input("O escribe nueva Ciudad (si no está en lista)")
            
                    lista_estados_mexico = [
                        "Aguascalientes", "Baja California", "Baja California Sur", "Campeche", "Chiapas", 
                        "Chihuahua", "Ciudad de México", "Coahuila", "Colima", "Durango", "Estado de México", 
                        "Guanajuato", "Guerrero", "Hidalgo", "Jalisco", "Michoacán", "Morelos", "Nayarit", 
                        "Nuevo León", "Oaxaca", "Puebla", "Querétaro", "Quintana Roo", "San Luis Potosí", 
                        "Sinaloa", "Sonora", "Tabasco", "Tamaulipas", "Tlaxcala", "Veracruz", "Yucatán", "Zacatecas"
                    ]
                    nuevo_estado = c3.selectbox("Estado *", [""] + lista_estados_mexico)

                    # Fila 2: Dirección
                    c4, c5, c6 = st.columns([2, 2, 1])
                    nueva_calle = c4.text_input("Calle y Número")
                    nueva_colonia = c5.text_input("Colonia")
                    nuevo_cp = c6.text_input("Código Postal")
            
                    # Fila 3: Asesor, Seguro y Contacto
                    c7, c8, c9 = st.columns([1.5, 1.5, 1])
                    asesor_sel = c7.selectbox("Seleccionar Asesor Existente", [""] + asesores_historicos)
                    asesor_manual = c8.text_input("O escribir Nuevo Asesor (Prioridad si se llena)")
                    nuevo_seguro = c9.selectbox("Seguro", ["MULTI", "GNP", "AMBOS", "OTRO"])

                    # Fila 4: Contacto, Teléfono, WhatsApp y Correo
                    c10, c11, c12, c13 = st.columns([1.5, 1, 1, 1.5])
                    nuevo_contacto = c10.text_input("Contacto Taller")
                    nuevo_tel = c11.text_input("Teléfono Contacto")
                    nuevo_wa = c12.text_input("WhatsApp (Opcional)")
                    nuevo_correo = c13.text_input("Correo Electrónico")

                    submit_btn = st.form_submit_button("💾 Guardar Taller en Catálogo", type="primary")
                    if submit_btn:
                        nueva_ciudad = ciudad_manual.strip().title() if ciudad_manual.strip() else ciudad_sel.strip()
                        asesor_asignado = asesor_manual.strip().upper() if asesor_manual.strip() else asesor_sel.strip().upper()

                        if nuevo_taller.strip() and nueva_ciudad and nuevo_estado.strip():
                            partes_dir = [p.strip() for p in [nueva_calle, nueva_colonia, nuevo_cp] if p.strip() != ""]
                            nueva_dir = ", ".join(partes_dir)
                            wa_final = str(nuevo_wa).strip() if str(nuevo_wa).strip() else str(nuevo_tel).strip()

                            with st.spinner("Guardando en la base de datos..."):
                                try:
                                    doc = init_connection()
                                    try: 
                                        ws_cat = doc.worksheet("BD_TALLERES")
                                    except Exception:
                                        try: 
                                            ws_cat = doc.worksheet("Catálogo")
                                        except Exception:
                                            st.error("⚠️ No se encontró la pestaña BD_TALLERES. Verifica el nombre en Google Sheets.")
                                            st.stop()
                                    
                                    headers = [str(h).strip().upper() for h in ws_cat.row_values(1)]
                                    fila_nueva = [""] * len(headers)
                            
                                    # Búsqueda flexible por palabra clave para no fallar por nombres compuestos
                                    def buscar_idx_col(palabras_clave):
                                        for i, h_val in enumerate(headers):
                                            if any(k in h_val for k in palabras_clave):
                                                return i
                                        return -1
                            
                                    idx_tall = buscar_idx_col(['TALLER', 'CDR'])
                                    idx_cont = buscar_idx_col(['CONTACTO'])
                                    idx_tel = buscar_idx_col(['TELEFONO', 'TELÉFONO', 'TEL'])
                                    idx_wa = buscar_idx_col(['WHATSAPP', 'WA', 'CEL'])
                                    idx_corr = buscar_idx_col(['CORREO', 'EMAIL', 'MAIL'])
                                    idx_dir = buscar_idx_col(['DIRECCION', 'DIRECCIÓN', 'DOMICILIO'])
                                    idx_ciu = buscar_idx_col(['CIUDAD', 'MUNICIPIO', 'PLAZA'])
                                    idx_est = buscar_idx_col(['ESTADO'])
                                    idx_ase = buscar_idx_col(['ASESOR'])
                                    idx_seg = buscar_idx_col(['SEGURO', 'ASEGURADORA', 'COMPAÑIA'])
                            
                                    if idx_tall >= 0: fila_nueva[idx_tall] = nuevo_taller.strip().upper()
                                    if idx_cont >= 0: fila_nueva[idx_cont] = nuevo_contacto.strip().upper()
                                    if idx_tel >= 0: fila_nueva[idx_tel] = str(nuevo_tel).strip()
                                    if idx_wa >= 0: fila_nueva[idx_wa] = wa_final
                                    if idx_corr >= 0: fila_nueva[idx_corr] = nuevo_correo.strip().lower()
                                    if idx_dir >= 0: fila_nueva[idx_dir] = nueva_dir.upper()
                                    if idx_ciu >= 0: fila_nueva[idx_ciu] = nueva_ciudad.upper()
                                    if idx_est >= 0: fila_nueva[idx_est] = nuevo_estado.strip().upper()
                                    if idx_ase >= 0: fila_nueva[idx_ase] = asesor_asignado
                                    if idx_seg >= 0: fila_nueva[idx_seg] = nuevo_seguro.strip().upper()
                            
                                    ws_cat.append_row(fila_nueva, value_input_option='USER_ENTERED')
                                    st.success(f"✅ Taller '{nuevo_taller}' agregado exitosamente con todos sus datos.")
                                    st.cache_data.clear()
                                    time.sleep(1)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error guardando taller: {e}")
                        else:
                            st.warning("⚠️ Debes llenar al menos el Nombre, Ciudad y Estado.")

    
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

            cols_prov = ['Proveedor', 'Sucursal', 'Contacto', 'Teléfono', 'Marcas Especialidad', 'Tiempo de Entrega', 'Días Crédito', 'Condición Pago',  'Dirección']
            cols_vista_prov = [c for c in cols_prov if c in df_prov_filtrado.columns]

            if not modo_consulta and permiso_edicion:
                st.caption("💡 Edita cualquier celda directamente (Condición de Pago, Días Crédito, Teléfono, etc.) y presiona **Guardar Cambios en Proveedores**.")
                opciones_cond_dir = ["", "Pago Anticipado", "Anticipo", "Contra Entrega", "Crédito", "Pago en Plataforma"]
                
                cfg_prov_ed = {
                    'Proveedor': st.column_config.TextColumn("Proveedor", width="medium"),
                    'Sucursal': st.column_config.TextColumn("Sucursal", width="small"),
                    'Contacto': st.column_config.TextColumn("Contacto", width="medium"),
                    'Teléfono': st.column_config.TextColumn("Teléfono", width="small"),
                    'Marcas Especialidad': st.column_config.TextColumn("Especialidad", width="medium"),
                    'Tiempo de Entrega': st.column_config.NumberColumn("ETA (Días)", min_value=0, step=1, width="small"),
                    'Días Crédito': st.column_config.NumberColumn("Días Crédito", min_value=0, step=1, width="small"),
                    'Condición Pago': st.column_config.SelectboxColumn("Condición Pago", options=opciones_cond_dir, width="medium"),
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
                        
                        col3, col4, col4_1 = st.columns([1.5, 1.5, 1])
                        nuevas_marcas = col3.text_input("Marcas de Especialidad", placeholder="Ej. Nissan, Honda, Colisión")
                        nuevo_contacto_p = col4.text_input("Nombre del Contacto")
                        nuevo_tel_p = col4_1.text_input("Teléfono")
                        
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
                                        i_contacto = safe_idx('Contacto')
                                        i_mar = safe_idx('Marcas Especialidad')
                                        i_tel = safe_idx('Teléfono')
                                        i_dir = safe_idx('Dirección')
                                        i_tie = safe_idx('Tiempo de Entrega')
                                        i_con = safe_idx('Condición Pago')
                                        i_dia = safe_idx('Días Crédito')
                                        
                                        if i_prv >= 0: fila_nueva[i_prv] = nuevo_prov.upper()
                                        if i_suc >= 0: fila_nueva[i_suc] = nueva_sucursal.upper()
                                        if i_contacto >= 0: fila_nueva[i_contacto] = nuevo_contacto_p.title()
                                        if i_mar >= 0: fila_nueva[i_mar] = nuevas_marcas.upper()
                                        if i_tel >= 0: fila_nueva[i_tel] = str(nuevo_tel_p)
                                        if i_dir >= 0: fila_nueva[i_dir] = nueva_dir_p.upper()
                                        
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

        def obtener_direcciones_taller_rem(taller_nombre):
            """Devuelve lista de (etiqueta_visible, direccion_pura) si el taller tiene 1 o más sucursales."""
            if df_catalogo.empty:
                return []
            c_t = buscar_col_local(df_catalogo, ["TALLER", "CDR"], ["TALLER"])
            c_d = buscar_col_local(df_catalogo, ["DIRECCION", "DIRECCIÓN"], ["DIRECCI"])
            c_c = buscar_col_local(df_catalogo, ["CIUDAD", "MUNICIPIO", "PLAZA"], ["CIUDAD", "MUNICIPIO"])
            c_s = buscar_col_local(df_catalogo, ["SEGURO", "ASEGURADORA"], ["SEGURO", "ASEGURADORA"])
            if not c_t or not c_d:
                return []
            m = df_catalogo[df_catalogo[c_t].astype(str).str.strip().str.upper() == str(taller_nombre).strip().upper()]
            opciones, vistos = [], set()
            for _, r_cat in m.iterrows():
                d_v = str(r_cat.get(c_d, '')).strip()
                if not d_v or d_v.lower() in ['nan', 'none'] or d_v.upper() in vistos:
                    continue
                vistos.add(d_v.upper())
                ciu_v = str(r_cat.get(c_c, '')).strip() if c_c else ""
                seg_v = str(r_cat.get(c_s, '')).strip() if c_s else ""
                pref = " · ".join([x for x in [ciu_v, seg_v] if x and x.lower() not in ['nan', 'none']])
                etq = f"{pref} — {d_v}" if pref else d_v
                opciones.append((etq, d_v))
            return opciones

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
                                            dirs_taller_rem = obtener_direcciones_taller_rem(taller)
                                            dir_elegida_rem = dirs_taller_rem[0][1] if len(dirs_taller_rem) == 1 else ""
                                            if len(dirs_taller_rem) > 1:
                                                mapa_dirs_rem = dict(dirs_taller_rem)
                                                sel_dir_rem = st.selectbox(
                                                    f"📍 Sucursal / Dirección para {taller} (Obligatorio verificar):",
                                                    ["-- Seleccionar sucursal --"] + list(mapa_dirs_rem.keys()),
                                                    key=f"sel_dir_rem_{aseguradora}_{taller}_{siniestro_v}"
                                                )
                                                dir_elegida_rem = mapa_dirs_rem.get(sel_dir_rem, "")
                                            piezas_a_remisionar = []
                                            for idx_pieza, row_p in df_sin_rem.reset_index().iterrows():
                                                desc_val = str(row_p.get(col_desc_r, ''))
                                                if st.checkbox(desc_val, value=True, key=f"chk_{aseguradora}_{siniestro_v}_{idx_pieza}_{desc_val}"):
                                                    piezas_a_remisionar.append(desc_val)

                                            nota_rem_input = st.text_area(
                                                "📝 Notas / Observaciones en Remisión (Opcional):",
                                                placeholder="Ej. Entregar con Jefe de Taller, incluye grapas, revisar pieza al recibir...",
                                                height=68,
                                                key=f"nota_rem_{aseguradora}_{taller}_{siniestro_v}"
                                            )
                                                    
                                            if st.form_submit_button("📄 Generar Remisión PDF"):
                                                if len(dirs_taller_rem) > 1 and not dir_elegida_rem:
                                                    st.warning("⚠️ Este taller tiene varias sucursales. Selecciona la dirección correcta antes de generar la remisión.")
                                                elif piezas_a_remisionar:
                                                    st.session_state['trigger_remision_manual'] = {
                                                        'siniestro': siniestro_v,
                                                        'taller': taller,
                                                        'descripciones': piezas_a_remisionar,
                                                        'direccion_elegida': dir_elegida_rem,
                                                        'nota_remision': nota_rem_input.strip()
                                                    }
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

                                taller_reimp_prev = str(df_folio.iloc[0].get(col_taller_reimp, '')).strip()
                                dirs_reimp = obtener_direcciones_taller_rem(taller_reimp_prev)
                                dir_reimp_elegida = dirs_reimp[0][1] if len(dirs_reimp) == 1 else ""
                                if len(dirs_reimp) > 1:
                                    mapa_dirs_reimp = dict(dirs_reimp)
                                    sel_dir_reimp = st.selectbox(
                                        f"📍 Sucursal / Dirección para reimprimir ({taller_reimp_prev}):",
                                        ["-- Seleccionar sucursal --"] + list(mapa_dirs_reimp.keys()),
                                        key=f"sel_dir_reimp_{siniestro_a_reimprimir}_{folio_limpio}"
                                    )
                                    dir_reimp_elegida = mapa_dirs_reimp.get(sel_dir_reimp, "")

                                if st.button(f"🖨️ Generar PDF para {folio_limpio}", key=f"btn_reimp_{siniestro_a_reimprimir}_{folio_limpio}"):
                                    if len(dirs_reimp) > 1 and not dir_reimp_elegida:
                                        st.warning("⚠️ Este taller tiene varias sucursales. Selecciona la dirección correcta antes de reimprimir.")
                                        st.stop()
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
                                        
                                        dir_v = dir_reimp_elegida
                                        if not dir_v:
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
            if tipo_operacion.lower() in ['compra', 'cotizacion', 'pago']:
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
                    # Prevenir duplicados si se programó hoy o si aún sigue pendiente de un día anterior
                    if len(r_ex) >= 11 and (hoy_prefijo in str(r_ex[1]) or str(r_ex[10]).strip().upper() == "PENDIENTE"):
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

    def obtener_sucursales_taller_ruta(taller_nombre):
        if df_catalogo.empty:
            return []
        c_t = next((c for c in df_catalogo.columns if 'TALLER' in str(c).upper()), None)
        c_d = next((c for c in df_catalogo.columns if 'DIRECC' in str(c).upper()), None)
        c_c = next((c for c in df_catalogo.columns if 'CIUDAD' in str(c).upper() or 'MUNICIPIO' in str(c).upper()), None)
        c_s = next((c for c in df_catalogo.columns if 'SEGURO' in str(c).upper() or 'ASEGURADORA' in str(c).upper()), None)
        if not c_t or not c_d:
            return []
        m = df_catalogo[df_catalogo[c_t].astype(str).str.strip().str.upper() == str(taller_nombre).strip().upper()]
        opciones, vistos = [], set()
        for _, r_cat in m.iterrows():
            d_v = str(r_cat.get(c_d, '')).strip()
            if not d_v or d_v.lower() in ['nan', 'none'] or d_v.upper() in vistos:
                continue
            vistos.add(d_v.upper())
            ciu_v = str(r_cat.get(c_c, '')).strip() if c_c else ""
            seg_v = str(r_cat.get(c_s, '')).strip() if c_s else ""
            pref = " · ".join([x for x in [ciu_v, seg_v] if x and x.lower() not in ['nan', 'none']])
            opciones.append((f"{pref} — {d_v}" if pref else d_v, d_v))
        return opciones

    def obtener_sucursales_prov_ruta(prov_nombre):
        """Agrupa todas las sucursales de un mismo proveedor (ej. RADEC - GPE, RADEC - CENTRO) con su dirección."""
        if df_proveedores.empty:
            return []
        c_p = next((c for c in df_proveedores.columns if 'PROVEEDOR' in str(c).upper() or 'NOMBRE' in str(c).upper()), None)
        c_s = next((c for c in df_proveedores.columns if 'SUCURSAL' in str(c).upper()), None)
        c_d = next((c for c in df_proveedores.columns if 'DIRECC' in str(c).upper()), None)
        if not c_p or not c_d:
            return []
        base_p = str(prov_nombre).split(" - ")[0].strip().upper()
        m = df_proveedores[df_proveedores[c_p].astype(str).str.strip().str.upper() == base_p]
        opciones, vistos = [], set()
        for _, rp in m.iterrows():
            p_n = str(rp.get(c_p, '')).strip().upper()
            s_n = str(rp.get(c_s, '')).strip().upper() if c_s else ""
            d_v = str(rp.get(c_d, '')).strip()
            nom_full = f"{p_n} - {s_n}" if (s_n and s_n not in ['NAN', 'NONE']) else p_n
            llave_v = f"{nom_full}|{d_v.upper()}"
            if not d_v or d_v.lower() in ['nan', 'none'] or llave_v in vistos:
                continue
            vistos.add(llave_v)
            opciones.append((f"{nom_full} — {d_v}", nom_full, d_v))
        return opciones

    # --- FILTROS RÁPIDOS DE RUTAS ---
    fr1, fr2, fr3 = st.columns([1.3, 1.2, 1.3])
    with fr1:
        f_ruta_lugar = st.text_input("🏢 Filtrar Taller / Proveedor:", placeholder="Ej. MERCADO LIBRE, GG...", key="f_rut_lug").strip().upper()
    with fr2:
        f_ruta_sin = st.text_input("🚗 Filtrar Siniestro:", placeholder="Ej. B86787861...", key="f_rut_sin").strip().upper()
    with fr3:
        f_ruta_pza = st.text_input("⚙️ Filtrar Refacción:", placeholder="Ej. FACIA, DEPOSITO...", key="f_rut_pza").strip().upper()

    # --- PESTAÑAS DE OPERACIÓN ---
    tab_entregas, tab_recolecciones, tab_compras, tab_eventuales = st.tabs(["📦 Entregas (CDR)", "↩️ Recolecciones (CDR)", "🛒 Compras", "🔄 Eventuales"])
    
    # ---------------------------------------------------------
    # TAB 1: ENTREGAS (SOLO NUEVO LEÓN Y SIN PAQUETERÍA)
    # ---------------------------------------------------------
    with tab_entregas:
        st.caption("Muestra piezas con remisión (o listas localmente) para enviar, sin guía de paquetería y cuyo taller pertenece a **Nuevo León**.")
        df_base_ent = df_completo.copy() if not df_completo.empty else pd.DataFrame()
        
        if not df_base_ent.empty and col_estatus:
            # CORRECCIÓN: Volvemos a incluir EN PROCESAMIENTO para no perder los pedidos listos locales.
            estatus_permitidos = ["EN TRANSITO", "EN PROCESAMIENTO"]
            df_ent = df_base_ent[df_base_ent[col_estatus].astype(str).str.upper().isin(estatus_permitidos)].copy()
        else:
            df_ent = pd.DataFrame()
        
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

                    dirs_ent_t = obtener_sucursales_taller_ruta(taller)
                    dir_ent_elegida = dirs_ent_t[0][1] if len(dirs_ent_t) == 1 else ""
                    if len(dirs_ent_t) > 1:
                        mapa_de = dict(dirs_ent_t)
                        sel_de = st.selectbox(
                            f"📍 Sucursal / Dirección para {taller} (Obligatorio confirmar):",
                            ["-- Seleccionar sucursal --"] + list(mapa_de.keys()),
                            key=f"sel_dir_ent_{taller}"
                        )
                        dir_ent_elegida = mapa_de.get(sel_de, "")

                    notas_ent = st.text_input("📝 Instrucciones / Notas:", placeholder="Ej. Dejar con el jefe de taller", key=f"notas_ent_{taller}")

                    if st.button(f"➕ Enviar Selección a {taller}", key=f"btn_ent_{taller}"):
                        seleccionados = ed_ent[ed_ent['Enviar Hoy'] == True]
                        if len(dirs_ent_t) > 1 and not dir_ent_elegida:
                            st.warning("⚠️ Este taller tiene varias sucursales. Selecciona la dirección correcta antes de despachar.")
                        elif not seleccionados.empty:
                            df_envio = df_taller.loc[seleccionados.index].copy()
                            if dir_ent_elegida:
                                df_envio['Direccion_Manual'] = dir_ent_elegida
                            if despachar_a_bd_rutas(df_envio, "entrega", notas_ent):
                                st.success("¡Destino agregado a la ruta del operador!")
                                st.rerun()
                        else: st.warning("Selecciona al menos una pieza.")
                    
        else:
            st.success("No hay piezas de Nuevo León pendientes de envío local a CDR.")

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
                        
                    dirs_rec_t = obtener_sucursales_taller_ruta(taller)
                    dir_rec_elegida = dirs_rec_t[0][1] if len(dirs_rec_t) == 1 else ""
                    if len(dirs_rec_t) > 1:
                        mapa_dr = dict(dirs_rec_t)
                        sel_dr = st.selectbox(
                            f"📍 Sucursal / Dirección para {taller} (Obligatorio confirmar):",
                            ["-- Seleccionar sucursal --"] + list(mapa_dr.keys()),
                            key=f"sel_dir_rec_{taller}"
                        )
                        dir_rec_elegida = mapa_dr.get(sel_dr, "")

                    notas_rec = st.text_input("📝 Instrucciones / Notas:", placeholder="Ej. Pedir acuse de recibo físico", key=f"notas_rec_{taller}")
                        
                    if st.button(f"➕ Enviar Selección a Ruta", key=f"btn_rec_{taller}"):
                        seleccionados = ed_rec[ed_rec['Enviar Hoy'] == True]
                        if len(dirs_rec_t) > 1 and not dir_rec_elegida:
                            st.warning("⚠️ Este taller tiene varias sucursales. Selecciona la dirección correcta antes de despachar.")
                        elif not seleccionados.empty:
                            df_envio = df_taller.loc[seleccionados.index].copy()
                            if dir_rec_elegida:
                                df_envio['Direccion_Manual'] = dir_rec_elegida
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
    # TAB 3: COMPRAS (COTIZAR, PAGAR Y RECOLECTAR EN BASE)
    # ---------------------------------------------------------
    with tab_compras:
        st.caption("Lista de piezas activas en **📦 Próximas Llegadas**. Selecciona la acción requerida (Cotizar, Pagar, Recoger o Directo CDR).")
        if not df_compras.empty and not df_completo.empty:
            def gen_llave_rutas(id_val, desc_val):
                id_str = str(id_val).strip().upper()
                if id_str.endswith('.0'): id_str = id_str[:-2]
                return f"{id_str}_{' '.join(str(desc_val).strip().upper().split())}"

            df_c_todas_pend = df_compras.copy()
            df_c_todas_pend['_GS_Row_Comp'] = df_c_todas_pend.index + 2
            
            # Filtros para mantener limpio el panel del chofer
            df_c_todas_pend['Recibido_Bool'] = df_c_todas_pend['Recibido'].astype(str).str.strip().str.upper().isin(['TRUE', 'SI', '1', 'YES', 'V', 'X'])
            df_c_todas_pend['Omitir_Ruta'] = df_c_todas_pend['Recibido'].astype(str).str.strip().str.upper().str.contains('DIRECTO')
            
            # Nos quedamos solo con lo que NO está recibido y NO va directo a CDR
            df_c_todas_pend = df_c_todas_pend[(df_c_todas_pend['Recibido_Bool'] == False) & (df_c_todas_pend['Omitir_Ruta'] == False)].copy()
            
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

                kc1, kc2, kc3 = st.columns(3)
                kc1.metric("📦 Total en Próximas Llegadas", total_en_prox_llegadas)
                kc2.metric("🚚 Pendientes en Proveedores", f"{len(df_comp_rutas)} pza(s)")
                kc3.metric("🌐 Excluidas (eBay / Inv.)", excluidas_ebay)

                if not df_comp_rutas.empty:
                    df_comp_rutas['Cotizar'] = False
                    df_comp_rutas['Pagar'] = False
                    df_comp_rutas['Recoger'] = False
                    df_comp_rutas['Directo'] = False
                    df_comp_rutas['Siniestro_Col'] = df_comp_rutas['Siniestro'].astype(str).str.strip()
                    df_comp_rutas['Vehiculo_Info'] = df_comp_rutas.get('Vehículo', pd.Series(["S/D"]*len(df_comp_rutas))).astype(str).str.strip()
                    df_comp_rutas['Pieza_Col'] = df_comp_rutas['Descripción Pieza'].astype(str).str.strip()
                    
                    st.markdown("#### 🏪 Gestión Global con Proveedores")
                    for prov, df_prov in df_comp_rutas.groupby('Proveedor'):
                        if f_ruta_lugar and f_ruta_lugar not in str(prov).upper():
                            continue
                        if f_ruta_sin:
                            df_prov = df_prov[df_prov['Siniestro_Col'].astype(str).str.upper().str.contains(f_ruta_sin, na=False)]
                        if f_ruta_pza:
                            df_prov = df_prov[df_prov['Pieza_Col'].astype(str).str.upper().str.contains(f_ruta_pza, na=False)]
                        if df_prov.empty:
                            continue
                        with st.expander(f"🛒 {prov} | {len(df_prov)} pieza(s) gestionables", expanded=False):
                            cols_ver = ['Cotizar', 'Pagar', 'Recoger', 'Directo', 'Siniestro_Col', 'Vehiculo_Info', 'Pieza_Col', 'Costo Compra', 'Condición Pago', 'Estatus_Real']
                            cols_ver = [c for c in cols_ver if c in df_prov.columns]
                            
                            cfg_comp = {
                                "Cotizar": st.column_config.CheckboxColumn("🔍 Cotizar", default=False),
                                "Pagar": st.column_config.CheckboxColumn("💵 Pagar", default=False),
                                "Recoger": st.column_config.CheckboxColumn("📦 Recoger", default=False),
                                "Directo": st.column_config.CheckboxColumn("🚚 Directo CDR", default=False, help="Oculta la pieza de las rutas marcándola como 'DIRECTO CDR' en la base, sin darla por recibida aún."),
                                "Siniestro_Col": st.column_config.TextColumn("Siniestro", disabled=True),
                                "Vehiculo_Info": st.column_config.TextColumn("Vehículo", disabled=True),
                                "Pieza_Col": st.column_config.TextColumn("Pieza", disabled=True),
                                "Costo Compra": st.column_config.TextColumn("Costo", disabled=True),
                                "Condición Pago": st.column_config.TextColumn("Condición", disabled=True),
                                "Estatus_Real": st.column_config.TextColumn("Estatus", disabled=True)
                            }
                            ed_comp = st.data_editor(df_prov[cols_ver], column_config=cfg_comp, hide_index=True, use_container_width=True, key=f"gest_{prov}")

                            sucs_prov_c = obtener_sucursales_prov_ruta(prov)
                            prov_despacho_final = prov
                            dir_prov_despacho = ""
                            if len(sucs_prov_c) > 1:
                                mapa_sp = {etq: (nom_f, d_f) for etq, nom_f, d_f in sucs_prov_c}
                                lista_etq_sp = list(mapa_sp.keys())
                                idx_def_sp = next((i for i, (_, nom_f, _) in enumerate(sucs_prov_c) if nom_f == str(prov).strip().upper()), 0)
                                sel_sp = st.selectbox(
                                    f"📍 Confirmar Sucursal / Dirección de {str(prov).split(' - ')[0].strip()}:",
                                    lista_etq_sp,
                                    index=idx_def_sp,
                                    key=f"sel_suc_prov_{prov}"
                                )
                                prov_despacho_final, dir_prov_despacho = mapa_sp[sel_sp]
                            elif len(sucs_prov_c) == 1:
                                st.caption(f"📍 **Dirección:** {sucs_prov_c[0][2]}")
                                dir_prov_despacho = sucs_prov_c[0][2]

                            notas_comp = st.text_input("📝 Instrucciones para el Operador:", placeholder="Ej. Pagar en efectivo y traer factura...", key=f"notas_gest_{prov}")

                            k_ver_qr_c = f"ver_qr_comp_{prov}"
                            v_qr_c = st.session_state.get(k_ver_qr_c, 0)
                            c_qr_c, c_btn_c = st.columns([1.5, 1.5], vertical_alignment="bottom")
                            with c_qr_c:
                                qr_comp_up = st.file_uploader(
                                    "📷 Adjuntar QR / Fotos (Opcional - Múltiple):",
                                    type=["png", "jpg", "jpeg", "webp"],
                                    accept_multiple_files=True,
                                    key=f"qr_comp_ruta_{prov}_{v_qr_c}"
                                )
                            with c_btn_c:
                                btn_gest_ok = st.button(f"➕ Procesar Selección para {prov}", type="primary", use_container_width=True, key=f"btn_gest_{prov}")

                            if btn_gest_ok:
                                seleccionados = ed_comp[(ed_comp['Cotizar'] == True) | (ed_comp['Pagar'] == True) | (ed_comp['Recoger'] == True) | (ed_comp['Directo'] == True)]
                                
                                if not seleccionados.empty:
                                    notas_comp_final = notas_comp
                                    if qr_comp_up:
                                        archivos_c = qr_comp_up if isinstance(qr_comp_up, list) else [qr_comp_up]
                                        for idx_fc, f_c in enumerate(archivos_c):
                                            try:
                                                tag_qr = guardar_adjunto_chat_en_sheet(f_c.getvalue(), f_c.name, usuario_activo, depurar=(idx_fc == 0))
                                                notas_comp_final = f"{notas_comp_final} {tag_qr}".strip()
                                            except Exception as e_qr:
                                                st.warning(f"No se pudo adjuntar {f_c.name}: {e_qr}")

                                    df_envio = df_prov.loc[seleccionados.index].copy()
                                    df_envio['Proveedor'] = prov_despacho_final
                                    if dir_prov_despacho:
                                        df_envio['Direccion_Manual'] = dir_prov_despacho
                                    if col_id: df_envio[col_id] = df_envio['Siniestro_Col']
                                    if col_desc: df_envio[col_desc] = df_envio['Pieza_Col']
                                    if col_vin: df_envio[col_vin] = df_envio['VIN_Real']
                                    
                                    exito = False
                                    try:
                                        # 1. COTIZAR
                                        df_cot = df_envio[seleccionados['Cotizar'] == True]
                                        if not df_cot.empty:
                                            if despachar_a_bd_rutas(df_cot, "cotizacion", f"[COTIZAR] {notas_comp_final}"): exito = True
                                        
                                        # 2. PAGAR
                                        df_pag = df_envio[seleccionados['Pagar'] == True]
                                        if not df_pag.empty:
                                            if despachar_a_bd_rutas(df_pag, "pago", f"[PAGAR] {notas_comp_final}"):
                                                exito = True
                                                ws_c_upd = doc.worksheet("BD_COMPRAS")
                                                headers_c_upd = [str(h).strip().upper() for h in ws_c_upd.row_values(1)]
                                                if "ESTATUS PAGO" in headers_c_upd:
                                                    col_idx_pago = headers_c_upd.index("ESTATUS PAGO") + 1
                                                    celdas_pago = [gspread.Cell(row=int(r_env['_GS_Row_Comp']), col=col_idx_pago, value="Pagado") for _, r_env in df_pag.iterrows()]
                                                    if celdas_pago: ws_c_upd.update_cells(celdas_pago, value_input_option='USER_ENTERED')
                                        
                                        # 3. RECOGER (Manda a ruta y marca Recibido = SI)
                                        df_rec = df_envio[seleccionados['Recoger'] == True]
                                        if not df_rec.empty:
                                            if despachar_a_bd_rutas(df_rec, "compra", f"[RECOGER] {notas_comp_final}"):
                                                exito = True
                                                ws_c_upd = doc.worksheet("BD_COMPRAS")
                                                headers_c_upd = [str(h).strip().upper() for h in ws_c_upd.row_values(1)]
                                                if "RECIBIDO" in headers_c_upd:
                                                    col_idx_rec = headers_c_upd.index("RECIBIDO") + 1
                                                    celdas_rec = [gspread.Cell(row=int(r_env['_GS_Row_Comp']), col=col_idx_rec, value="SI") for _, r_env in df_rec.iterrows()]
                                                    if celdas_rec: ws_c_upd.update_cells(celdas_rec, value_input_option='USER_ENTERED')

                                        # 4. DIRECTO A CDR (Escribe "DIRECTO CDR" en vez de "SI" y NO manda a ruta)
                                        df_dir = df_envio[seleccionados['Directo'] == True]
                                        if not df_dir.empty:
                                            exito = True
                                            ws_c_upd = doc.worksheet("BD_COMPRAS")
                                            headers_c_upd = [str(h).strip().upper() for h in ws_c_upd.row_values(1)]
                                            if "RECIBIDO" in headers_c_upd:
                                                col_idx_rec = headers_c_upd.index("RECIBIDO") + 1
                                                celdas_rec = [gspread.Cell(row=int(r_env['_GS_Row_Comp']), col=col_idx_rec, value="DIRECTO CDR") for _, r_env in df_dir.iterrows()]
                                                if celdas_rec: ws_c_upd.update_cells(celdas_rec, value_input_option='USER_ENTERED')
                                        
                                        if exito:
                                            st.session_state[k_ver_qr_c] = v_qr_c + 1
                                            st.cache_data.clear()
                                            st.success(f"✅ ¡Operación procesada para {prov}!")
                                            time.sleep(1)
                                            st.rerun()
                                    except Exception as e_bd:
                                        st.warning(f"Hubo un error de sincronización: {e_bd}")
                                else:
                                    st.warning("⚠️ Selecciona al menos una pieza y marca una acción.")
                else:
                    st.info("No hay rutas activas pendientes en Próximas Llegadas.")
            else:
                st.info("No hay compras activas pendientes de recepción.")
        else:
            st.info("Falta información de compras para cruzar datos.")

    # ---------------------------------------------------------
    # TAB 4: VUELTAS EVENTUALES (COTIZAR, REVISAR, REPARACIÓN, PAQUETERÍA)
    # ---------------------------------------------------------
    with tab_eventuales:
        st.markdown("### 🔄 Vueltas Eventuales")
        st.caption("Programa visitas especiales: cotizaciones, revisiones físicas en taller, entregas/recolecciones de reparación o paqueterías ocurre.")

        # 1. Catálogo unificado (Talleres + Proveedores) con direcciones precargadas
        lista_lugares_ev = []
        dict_dir_ev = {}

        if not df_catalogo.empty:
            c_tall_e = next((c for c in df_catalogo.columns if 'TALLER' in str(c).upper()), None)
            c_dir_t = next((c for c in df_catalogo.columns if 'DIRECC' in str(c).upper()), None)
            if c_tall_e:
                for _, rt_e in df_catalogo.iterrows():
                    t_nom = str(rt_e.get(c_tall_e, '')).strip().upper()
                    if not t_nom or t_nom in ['NAN', 'NONE']: continue
                    etq_t = f"[TALLER] {t_nom}"
                    lista_lugares_ev.append(etq_t)
                    if c_dir_t and str(rt_e.get(c_dir_t, '')).strip() not in ['', 'nan', 'None']:
                        dict_dir_ev[etq_t] = str(rt_e.get(c_dir_t, '')).strip()

        if not df_proveedores.empty:
            c_prv_c = next((c for c in df_proveedores.columns if 'PROVEEDOR' in str(c).upper() or 'NOMBRE' in str(c).upper()), None)
            c_suc_c = next((c for c in df_proveedores.columns if 'SUCURSAL' in str(c).upper()), None)
            c_dir_c = next((c for c in df_proveedores.columns if 'DIRECC' in str(c).upper()), None)
            if c_prv_c:
                for _, rp_c in df_proveedores.iterrows():
                    p_n = str(rp_c.get(c_prv_c, '')).strip().upper()
                    s_n = str(rp_c.get(c_suc_c, '')).strip().upper() if c_suc_c else ""
                    if not p_n or p_n in ['NAN', 'NONE']: continue
                    llave_p = f"{p_n} - {s_n}" if (s_n and s_n not in ['NAN', 'NONE']) else p_n
                    etq_p = f"[PROV] {llave_p}"
                    lista_lugares_ev.append(etq_p)
                    if c_dir_c and str(rp_c.get(c_dir_c, '')).strip() not in ['', 'nan', 'None']:
                        dict_dir_ev[etq_p] = str(rp_c.get(c_dir_c, '')).strip()

        lista_lugares_ev = sorted(list(set(lista_lugares_ev)))

        # 2. Lista opcional de Siniestros Activos para autocompletar Vehículo, VIN y Piezas
        lista_sin_ev = ["General / Sin Siniestro"]
        mapa_sin_info_ev = {}
        if not df_completo.empty and col_id:
            df_ev_act = df_completo.copy()
            if col_estatus:
                est_cerr_ev = ["CANCELADO", "RECIBIDO", "FACTURADO", "REEMBOLSADO", "PÉRDIDA TOTAL", "PERDIDA TOTAL", "PAGO DE DAÑOS", "PAGO DE DANOS"]
                df_ev_act = df_ev_act[~df_ev_act[col_estatus].astype(str).str.strip().str.upper().isin(est_cerr_ev)].copy()
            if not df_ev_act.empty:
                df_ev_act['_Veh_Ev'] = df_ev_act.apply(armar_vehiculo, axis=1)
                for sid_val, grp_s in df_ev_act.groupby(col_id):
                    sid_str = str(sid_val).strip().removesuffix('.0')
                    if not sid_str or sid_str.upper() in ['NAN', 'NONE']: continue
                    veh_s = str(grp_s['_Veh_Ev'].iloc[0]).strip()
                    vin_s = str(grp_s[col_vin].iloc[0]).strip() if (col_vin and col_vin in grp_s.columns) else ""
                    if vin_s.upper() in ['NAN', 'NONE']: vin_s = ""
                    tall_s = str(grp_s[col_taller].iloc[0]).strip().upper() if (col_taller and col_taller in grp_s.columns) else ""
                    piezas_s = sorted(list(set([str(x).strip() for x in grp_s[col_desc].dropna().tolist() if str(x).strip()]))) if (col_desc and col_desc in grp_s.columns) else []
                    etq_sin = f"{sid_str} | {veh_s}"
                    lista_sin_ev.append(etq_sin)
                    mapa_sin_info_ev[etq_sin] = {'id': sid_str, 'veh': veh_s, 'vin': vin_s, 'taller': tall_s, 'piezas': piezas_s}
        lista_sin_ev = ["General / Sin Siniestro"] + sorted(lista_sin_ev[1:])

        # Fila 1: Tipo de Vuelta + Siniestro Activo (Opcional)
        mapa_tipos_vuelta = {
            "🔎 Cotización / Búsqueda": "COTIZACION",
            "🧐 Revisión en Taller": "REVISION",
            "🔧 Reparación - Entrega": "REPARACION - ENTREGA",
            "🔧 Reparación - Recolección": "REPARACION - RECOLECCION",
            "📦 Paquetería (Ocurre)": "PAQUETERIA"
        }
        ce1, ce2 = st.columns([1.2, 1.8])
        with ce1:
            tipo_vuelta_lbl = st.selectbox("Tipo de Vuelta *", list(mapa_tipos_vuelta.keys()), key="sel_tipo_vuelta_ev")
        with ce2:
            sin_ev_sel = st.selectbox("🚗 Siniestro Activo (Opcional - Autocompleta datos):", lista_sin_ev, key="sel_sin_ev_ruta")

        info_sin_ev = mapa_sin_info_ev.get(sin_ev_sel, {})
        idx_lugar_default = 0
        if info_sin_ev.get('taller'):
            etq_taller_match = f"[TALLER] {info_sin_ev['taller']}"
            if etq_taller_match in lista_lugares_ev:
                idx_lugar_default = lista_lugares_ev.index(etq_taller_match) + 2

        # Fila 2: Lugar (Catálogo Unificado) + VIN
        col_sel_p, col_vin_p = st.columns([1.8, 1.2])
        with col_sel_p:
            prov_eventual = st.selectbox(
                "Lugar (Taller / Proveedor / Reparación / Paquetería) *",
                ["", "-- ESCRIBIR NUEVO --"] + lista_lugares_ev,
                index=idx_lugar_default,
                key=f"sel_prov_cot_ruta_{info_sin_ev.get('id', 'gen')}"
            )
        with col_vin_p:
            vin_eventual = st.text_input(
                "VIN / Número de Serie (Opcional)",
                value=info_sin_ev.get('vin', ''),
                key=f"vin_cot_ruta_{info_sin_ev.get('id', 'gen')}"
            )

        if prov_eventual == "":
            st.info("👆 Selecciona un lugar arriba para habilitar la captura.")
        else:
            v_qr_ev = st.session_state.get("ver_qr_ev_ruta", 0)
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
                    st.markdown("##### 🏢 Datos del Nuevo Lugar / Proveedor")
                    cp1, cp2, cp3 = st.columns([2, 1.5, 1.5])
                    nuevo_prov = cp1.text_input("Nombre del Lugar * (Ej. TALLER DE FASCIAS / PAQUETEXPRESS)").strip().upper()
                    nueva_suc_cot = cp2.text_input("Sucursal / Zona (Ej. ESCOBEDO)").strip().upper()
                    nuevo_tel_cot = cp3.text_input("Teléfono / Contacto").strip()

                    cp4, cp5 = st.columns([2.5, 1.5])
                    dir_eventual = cp4.text_input("Dirección Completa (Para navegación del chofer) *").strip()
                    nuevas_marcas_cot = cp5.text_input("Especialidad / Notas", placeholder="Ej. Reparación de fascias, Paquetería").strip().upper()

                    cp6, cp7, cp8 = st.columns(3)
                    nuevo_tiempo_cot = cp6.selectbox("Tiempo Promedio de Entrega", ["Inmediata", "1 a 2 días", "3 a 5 días", "Más de 5 días", "Bajo Pedido"])
                    nueva_cond_cot = cp7.selectbox("Condición de Pago", ["Contra Entrega", "Pago Anticipado", "Anticipo", "Crédito", "Pago en Plataforma"])
                    nuevos_dias_cot = cp8.number_input("Días Crédito", min_value=0, value=0, step=1)
                    guardar_en_directorio = st.checkbox("☑️ Guardar este lugar en el Directorio (BD_PROVEEDORES)", value=False)
                else:
                    dir_precargada = dict_dir_ev.get(prov_eventual, "")
                    dir_eventual = st.text_input("Dirección o Zona (Para que navegue el chofer)", value=dir_precargada)

                st.markdown("##### ⚙️ Piezas implicadas en la vuelta")
                piezas_sin_sel = []
                if info_sin_ev.get('piezas'):
                    piezas_sin_sel = st.multiselect(
                        "Selecciona las piezas del siniestro:",
                        options=info_sin_ev['piezas'],
                        default=info_sin_ev['piezas'][:1] if len(info_sin_ev['piezas']) == 1 else [],
                        key=f"ms_pzas_ev_{info_sin_ev.get('id', 'gen')}"
                    )

                st.caption("También puedes capturar piezas manuales o # de parte abajo (usa `+` para agregar más renglones):")
                df_piezas_base = pd.DataFrame([{"No. Parte": "", "Descripción de la Pieza": ""}])
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

                notas_eventual = st.text_input("📝 Instrucciones / Notas para el operador:", placeholder="Ej. Recoger fascia para llevar a detallar / Tomar fotos de la pieza dañada...")
                qr_ev_up = st.file_uploader(
                    "📷 Adjuntar QR / Fotos para el chofer (Opcional - puedes subir varias):",
                    type=["png", "jpg", "jpeg", "webp"],
                    accept_multiple_files=True,
                    key=f"qr_ev_ruta_{v_qr_ev}"
                )

                btn_cot = st.form_submit_button(f"➕ Enviar Vuelta ({mapa_tipos_vuelta[tipo_vuelta_lbl]}) a la Ruta", type="primary")

                if btn_cot:
                    if prov_eventual == "-- ESCRIBIR NUEVO --":
                        nombre_final = f"{nuevo_prov} - {nueva_suc_cot}" if nueva_suc_cot else nuevo_prov
                    else:
                        nombre_final = prov_eventual.replace("[TALLER] ", "").replace("[PROV] ", "").strip()

                    piezas_lista = list(piezas_sin_sel)
                    for _, r_pz in ed_piezas_cot.iterrows():
                        np_val = str(r_pz.get("No. Parte", "")).strip().upper()
                        ds_val = str(r_pz.get("Descripción de la Pieza", "")).strip().upper()
                        if np_val == "NAN": np_val = ""
                        if ds_val == "NAN": ds_val = ""
                        if np_val and ds_val: piezas_lista.append(f"[{np_val}] {ds_val}")
                        elif np_val: piezas_lista.append(f"NP: {np_val}")
                        elif ds_val: piezas_lista.append(ds_val)

                    if not nombre_final or len(piezas_lista) == 0:
                        st.error("⚠️ El Lugar y al menos 1 Pieza (seleccionada o capturada) son obligatorios.")
                    else:
                        if prov_eventual == "-- ESCRIBIR NUEVO --" and guardar_en_directorio and nuevo_prov:
                            try:
                                ws_p = doc.worksheet("BD_PROVEEDORES")
                                headers_p = [str(h).strip() for h in ws_p.row_values(1)]
                                fila_prov = [""] * max(len(headers_p), 10)
                                def safe_idx_p(name):
                                    for idx_h, h_val in enumerate(headers_p):
                                        if h_val.upper() == name.upper(): return idx_h
                                    return -1
                                i_prv = safe_idx_p('Proveedor'); i_suc = safe_idx_p('Sucursal'); i_mar = safe_idx_p('Marcas Especialidad')
                                i_tel = safe_idx_p('Teléfono'); i_dir = safe_idx_p('Dirección'); i_tie = safe_idx_p('Tiempo de Entrega')
                                i_con = safe_idx_p('Condición Pago'); i_dia = safe_idx_p('Días Crédito')
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

                        tipo_op_final = mapa_tipos_vuelta[tipo_vuelta_lbl]
                        veh_ev_final = info_sin_ev.get('veh', f"Vuelta Eventual ({tipo_op_final})")
                        sin_ev_final = info_sin_ev.get('id', 'N/A')

                        resumen_pzas_ev = ", ".join(piezas_lista)
                        prefijo_ev = f"[{tipo_op_final}] {veh_ev_final} (Sin: {sin_ev_final}) | Pieza(s): {resumen_pzas_ev}"
                        notas_con_pieza = f"{prefijo_ev} — {notas_eventual.strip()}" if notas_eventual.strip() else prefijo_ev

                        datos_ev = {
                            'Proveedor': [nombre_final] * len(piezas_lista),
                            'Taller': [nombre_final] * len(piezas_lista),
                            'Vehiculo_Info': [veh_ev_final] * len(piezas_lista),
                            'Descrip.': piezas_lista,
                            'Direccion_Manual': [dir_eventual] * len(piezas_lista)
                        }
                        if col_vin: datos_ev[col_vin] = [vin_eventual if vin_eventual else "S/D"] * len(piezas_lista)
                        if col_id: datos_ev[col_id] = [sin_ev_final] * len(piezas_lista)

                        df_ev_out = pd.DataFrame(datos_ev)
                        if col_desc and col_desc not in df_ev_out.columns: df_ev_out[col_desc] = piezas_lista

                        if qr_ev_up:
                            archivos_ev = qr_ev_up if isinstance(qr_ev_up, list) else [qr_ev_up]
                            for idx_fev, f_ev in enumerate(archivos_ev):
                                try:
                                    tag_qr_ev = guardar_adjunto_chat_en_sheet(f_ev.getvalue(), f_ev.name, usuario_activo, depurar=(idx_fev == 0))
                                    notas_con_pieza = f"{notas_con_pieza} {tag_qr_ev}".strip()
                                except Exception as e_qr_ev:
                                    st.warning(f"No se pudo adjuntar {f_ev.name}: {e_qr_ev}")

                        if despachar_a_bd_rutas(df_ev_out, tipo_op_final, notas_con_pieza):
                            st.session_state["ver_qr_ev_ruta"] = v_qr_ev + 1
                            st.success(f"✅ ¡Vuelta de {tipo_op_final} enviada a ruta para {nombre_final} ({len(piezas_lista)} pieza(s))!")
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
    tab_bots, tab_cotizador, tab_mant, tab_prestamos = st.tabs(["🤖 Centro de Bots y Alertas", "⚡ Mesa de Cotizaciones (IA)", "💾 Mantenimiento y Pendientes", "💸 Préstamos a Empleados"])

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
            @st.cache_data(ttl=300)
            def leer_config_bots_seguro():
                doc_c = init_connection()
                try:
                    ws_c = doc_c.worksheet("BD_CONFIG_BOTS")
                    return ws_c.get_all_values()
                except gspread.exceptions.WorksheetNotFound:
                    ws_c = doc_c.add_worksheet(title="BD_CONFIG_BOTS", rows=200, cols=3)
                    filas_ini = [
                        ["Clave", "Valor", "Notas"],
                        ["MULTI_USER", "PMA5816", "Usuario Portal Multiasistencia"],
                        ["MULTI_PASS", "PmrNov1.", "Contraseña Portal Multiasistencia"],
                        ["TC_USD", "20.50", "Tipo de cambio USD a MXN para eBay"]
                    ]
                    ws_c.append_rows(filas_ini, value_input_option='USER_ENTERED')
                    return filas_ini
                except Exception:
                    return []

            with st.container(border=True):
                st.markdown("**🔐 Credenciales, IA Key, Portales Web y Diccionario (Cotizador)**")
                filas_cfg = leer_config_bots_seguro()

                mapa_cfg_ui = {}
                abrev_lista_ui = []
                portales_lista_ui = []
                for r_c in filas_cfg[1:]:
                    if len(r_c) >= 2:
                        k_c, v_c = str(r_c[0]).strip().upper(), str(r_c[1]).strip()
                        nota_c = str(r_c[2]).strip().upper() if len(r_c) >= 3 else "TODAS"
                        if k_c.startswith("ABREV_"):
                            abrev_lista_ui.append({"Abreviatura Portal": k_c.replace("ABREV_", ""), "Significado Completo": v_c})
                        elif k_c.startswith("PORTAL_"):
                            portales_lista_ui.append({"Nombre Portal": k_c.replace("PORTAL_", ""), "Dominio / URL": v_c, "Categoría": nota_c})
                        else:
                            mapa_cfg_ui[k_c] = v_c

                if not portales_lista_ui:
                    portales_lista_ui = [
                        {"Nombre Portal": "RADEC", "Dominio / URL": "radec.com.mx", "Categoría": "GENERICA"},
                        {"Nombre Portal": "PARTSOUQ", "Dominio / URL": "partsouq.com", "Categoría": "ORIGINAL"},
                        {"Nombre Portal": "PARTSLINK24", "Dominio / URL": "partslink24.com", "Categoría": "ORIGINAL"},
                        {"Nombre Portal": "KIAPARTSNOW", "Dominio / URL": "kiapartsnow.com", "Categoría": "ORIGINAL"},
                        {"Nombre Portal": "FORDPARTSGIANT", "Dominio / URL": "fordpartsgiant.com", "Categoría": "ORIGINAL"},
                        {"Nombre Portal": "GMPARTSGIANT", "Dominio / URL": "gmpartsgiant.com", "Categoría": "ORIGINAL"},
                        {"Nombre Portal": "NISSANPARTSDEAL", "Dominio / URL": "nissanpartsdeal.com", "Categoría": "ORIGINAL"},
                        {"Nombre Portal": "MERCADO LIBRE", "Dominio / URL": "mercadolibre.com.mx", "Categoría": "TODAS"},
                        {"Nombre Portal": "EBAY MOTORS", "Dominio / URL": "ebay.com", "Categoría": "SEMINUEVA"}
                    ]

                usr_m_in = st.text_input("Usuario Multiasistencia:", value=mapa_cfg_ui.get("MULTI_USER", "PMA5816"))
                pwd_m_in = st.text_input("Contraseña Multiasistencia:", value=mapa_cfg_ui.get("MULTI_PASS", "Pmroct1."), type="password")
                gem_key_in = st.text_input("🤖 Gemini API Key (Obligatoria para buscar en Radec / PartSouq / ML / eBay):", value=mapa_cfg_ui.get("GEMINI_API_KEY", ""), type="password")
                tc_usd_in = st.number_input("Tipo de Cambio USD -> MXN:", min_value=15.0, max_value=35.0, value=float(mapa_cfg_ui.get("TC_USD", 20.50)), step=0.25)

                st.caption("🌐 **Portales Web de Búsqueda:** Agrega aquí cualquier página nueva (usa el signo `+` abajo de la tabla):")
                df_portales_base = pd.DataFrame(portales_lista_ui)
                ed_portales_ui = st.data_editor(
                    df_portales_base,
                    num_rows="dynamic",
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Categoría": st.column_config.SelectboxColumn("Categoría", options=["ORIGINAL", "SEMINUEVA", "GENERICA", "TODAS"])
                    },
                    key="ed_portales_bot"
                )

                st.caption("📖 **Diccionario de abreviaturas del portal** (ej. `ANITIN.` -> `ANTINIEBLA`):")
                df_abrev_base = pd.DataFrame(abrev_lista_ui) if abrev_lista_ui else pd.DataFrame([{"Abreviatura Portal": "ANITIN.", "Significado Completo": "ANTINIEBLA"}])
                ed_abrev_ui = st.data_editor(df_abrev_base, num_rows="dynamic", use_container_width=True, hide_index=True, key="ed_diccionario_bot")

                if st.button("💾 Guardar Cambios de Configuración", type="primary", key="btn_save_cfg_bot"):
                    try:
                        doc_cfg = init_connection()
                        ws_cfg = doc_cfg.worksheet("BD_CONFIG_BOTS")
                        nuevas_filas_cfg = [
                            ["Clave", "Valor", "Notas"],
                            ["MULTI_USER", usr_m_in.strip(), "Usuario Portal Multiasistencia"],
                            ["MULTI_PASS", pwd_m_in.strip(), "Contraseña Portal Multiasistencia"],
                            ["GEMINI_API_KEY", gem_key_in.strip(), "API Key de Google AI Studio para buscador web"],
                            ["TC_USD", str(tc_usd_in), "Tipo de cambio USD a MXN para eBay"]
                        ]
                        for _, r_pt in ed_portales_ui.iterrows():
                            pt_nom = str(r_pt.get("Nombre Portal", "")).strip().upper()
                            pt_url = str(r_pt.get("Dominio / URL", "")).strip().lower()
                            pt_cat = str(r_pt.get("Categoría", "TODAS")).strip().upper()
                            if pt_nom and pt_url and pt_nom != "NAN":
                                nuevas_filas_cfg.append([f"PORTAL_{pt_nom}", pt_url, pt_cat])

                        for _, r_ab in ed_abrev_ui.iterrows():
                            ab_k = str(r_ab.get("Abreviatura Portal", "")).strip().upper()
                            ab_v = str(r_ab.get("Significado Completo", "")).strip().upper()
                            if ab_k and ab_v and ab_k != "NAN":
                                nuevas_filas_cfg.append([f"ABREV_{ab_k}", ab_v, "Diccionario usuario"])

                        ws_cfg.clear()
                        ws_cfg.update(range_name='A1', values=nuevas_filas_cfg, value_input_option='USER_ENTERED')
                        leer_config_bots_seguro.clear()
                        st.success("✅ Configuración, API Key y Portales Web guardados correctamente.")
                        time.sleep(0.6)
                        st.rerun()
                    except Exception as e_cfg:
                        st.error(f"Error al guardar configuración: {e_cfg}")

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

    # =========================================================================
    # PESTAÑA 3: MÓDULO DE PRÉSTAMOS A EMPLEADOS
    # =========================================================================
    with tab_prestamos:
        st.markdown("#### 💸 Registro de Préstamos / Gastos de Empleados a favor de PMR")
        st.caption("Registra los pagos de refacciones o servicios que los empleados hacen de su bolsa (Efectivo, TDC, etc.) para su posterior reembolso.")
        
        with st.form("form_prestamos_empleados", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            emp_p = c1.selectbox("Empleado", ["Daniel", "Dionicio", "Diana", "Marco", "Otro"])
            met_p = c2.selectbox("Método de Pago", ["Efectivo", "TDC", "Tarjeta Débito", "Transferencia"])
            fec_p = c3.date_input("Fecha del Gasto")
            
            c4, c5 = st.columns([2, 1])
            
            lista_provs = ["OTRO (Escribir libremente)"]
            df_prov_temp = cargar_catalogos()[1]
            if not df_prov_temp.empty and 'Proveedor' in df_prov_temp.columns:
                provs_bd = [p for p in df_prov_temp['Proveedor'].dropna().unique().tolist() if str(p).strip() != ""]
                lista_provs.extend(sorted(provs_bd))
            
            prov_sel = c4.selectbox("Proveedor / Negocio", lista_provs)
            prov_libre = c4.text_input("Si elegiste 'OTRO', especifica el proveedor o concepto aquí:")
            
            monto_p = c5.number_input("Monto Pagado ($)", min_value=0.0, step=100.0, format="%.2f")
            
            c6, c7 = st.columns(2)
            sin_p = c6.text_input("Siniestro (Opcional, ej. SIN x)")
            ref_p = c7.text_input("Refacción / Descripción del gasto")
            
            btn_prestamo = st.form_submit_button("💾 Guardar Registro", type="primary")
            
            if btn_prestamo:
                if monto_p > 0:
                    prov_final = prov_libre if prov_sel == "OTRO (Escribir libremente)" else prov_sel
                    if not prov_final: prov_final = "S/D"
                    
                    nueva_fila = [
                        fec_p.strftime("%Y-%m-%d"), emp_p, met_p, prov_final, monto_p, sin_p, ref_p, "PENDIENTE REEMBOLSO"
                    ]
                    try:
                        doc_prestamo = init_connection()
                        ws_gastos = doc_prestamo.worksheet("GASTOS_EMPLEADOS")
                        ws_gastos.append_row(nueva_fila)
                        st.success(f"✅ Gasto de {emp_p} por ${monto_p:,.2f} en {prov_final} registrado correctamente.")
                    except Exception as e:
                        if "WorksheetNotFound" in str(e):
                            st.error("❌ No existe la pestaña 'GASTOS_EMPLEADOS' en tu Google Sheet. Por favor créala primero.")
                        else:
                            st.error(f"Error al guardar: {e}")
                else:
                    st.warning("⚠️ El monto debe ser mayor a $0.00.")

        # --- RESUMEN DE DEUDAS ACTIVAS (AHORA SÍ ESTÁ FUERA DEL FORMULARIO Y DEL IF) ---
        st.markdown("### 📋 Resumen de Deudas PMR")

        try:
            doc_prestamos = init_connection()
            ws_gastos_resumen = doc_prestamos.worksheet("GASTOS_EMPLEADOS")
            datos_gastos = ws_gastos_resumen.get_all_values()
    
            if len(datos_gastos) > 1:
                df_gastos = pd.DataFrame(datos_gastos[1:], columns=datos_gastos[0])
                df_gastos['GS_Row'] = df_gastos.index + 2 # <--- Se agrega para ubicar la fila exacta en Sheets
        
                if 'Estado' in df_gastos.columns:
                    df_activos = df_gastos[df_gastos['Estado'].astype(str).str.upper() == 'PENDIENTE REEMBOLSO'].copy() 
                else:
                    df_activos = pd.DataFrame() 
        
                if not df_activos.empty:
                    empleados_con_deuda = df_activos['Empleado'].unique()
            
                    for empleado in empleados_con_deuda:
                        df_empleado = df_activos[df_activos['Empleado'] == empleado].copy()
                        df_empleado['Monto'] = pd.to_numeric(df_empleado['Monto'], errors='coerce').fillna(0)
                        total_deuda = df_empleado['Monto'].sum()
                
                        with st.expander(f"👤 {empleado} | Total adeudado: ${total_deuda:,.2f}"):
                            # 1. Habilitar checkbox y editor
                            df_empleado['Liquidar'] = False
                            cols_disp = ['Liquidar', 'Fecha', 'Proveedor', 'Refacción', 'Monto']
                            cols_a_mostrar = [c for c in cols_disp if c in df_empleado.columns or c == 'Liquidar']
                    
                            df_ed_emp = st.data_editor(
                                df_empleado[cols_a_mostrar],
                                column_config={
                                    "Liquidar": st.column_config.CheckboxColumn("✅ Pagar", default=False),
                                    "Monto": st.column_config.NumberColumn("Monto", format="$ %.2f")
                                },
                                hide_index=True,
                                use_container_width=True,
                                disabled=[c for c in cols_a_mostrar if c != 'Liquidar'],
                                key=f"ed_deuda_{empleado}"
                            )
                            
                            # 2. Botón de ejecución
                            if st.button(f"💵 Registrar Pago a {empleado}", key=f"btn_pagar_{empleado}"):
                                seleccionados = df_ed_emp[df_ed_emp['Liquidar'] == True]
                                if not seleccionados.empty:
                                    with st.spinner("Actualizando pagos en la nube..."):
                                        try:
                                            idx_estado = datos_gastos[0].index('Estado') + 1
                                            celdas_pago = []
                                            
                                            for idx_sel in seleccionados.index:
                                                gs_row = int(df_empleado.loc[idx_sel, 'GS_Row'])
                                                celdas_pago.append(gspread.Cell(row=gs_row, col=idx_estado, value="PAGADO"))
                                            
                                            if celdas_pago:
                                                ws_gastos_resumen.update_cells(celdas_pago, value_input_option='USER_ENTERED')
                                                st.success(f"✅ Se liquidaron {len(seleccionados)} adeudos de {empleado}.")
                                                time.sleep(1)
                                                st.rerun()
                                        except Exception as e_pago:
                                            st.error(f"Error al liquidar: {e_pago}")
                                else:
                                    st.warning("Selecciona al menos un registro de la tabla para liquidar.")
                else:
                    st.info("No hay préstamos activos a favor de PMR en este momento.")
            else:
                st.info("La base de gastos está vacía.")
        
        except Exception as e:
            st.error(f"No se pudo cargar el resumen de gastos: {e}")

    # =========================================================================
    # PESTAÑA 4: MESA DE COTIZACIONES (IA) - MULTIASISTENCIA
    # =========================================================================
    with tab_cotizador:
        st.markdown("#### ⚡ Mesa de Decisión y Cotizador Automático (Multiasistencia)")
        st.caption("1️⃣ Extrae cotizaciones activas • 2️⃣ Edita precios/orígenes con calma en la tabla • 3️⃣ Guarda o Envía al Portal.")

        @st.cache_data(ttl=180)
        def leer_cotizaciones_cache():
            doc_c = init_connection()
            ws_c = doc_c.worksheet("BD_COTIZACIONES")
            return ws_c.get_all_values()

        # Botones principales y selector de vista Chrome
        col_btn_ext, col_btn_env, col_modo_cot = st.columns([1.4, 1.6, 1.2], vertical_alignment="center")
        with col_modo_cot:
            modo_bot_cot = st.radio("Vista Chrome:", ["Oculto (Rápido)", "Visual (PC Local)"], horizontal=True, key="rad_modo_cot")
        arg_vis_cot = "--oculto" if "Oculto" in modo_bot_cot else "--visual"

        btn_run_ext = col_btn_ext.button("🔎 1. Extraer Nuevas Cotizaciones", type="primary", use_container_width=True)
        btn_run_env = col_btn_env.button("🚀 2. Guardar y Enviar Validadas al Portal", type="primary", use_container_width=True)

        # Botones secundarios (Reporte PDF y Limpieza de Evidencias)
        col_btn_pdf, col_btn_ref_c, col_btn_limp = st.columns([1.5, 1.0, 1.5], vertical_alignment="center")
        
        if col_btn_pdf.button("📄 Descargar Reporte PDF", use_container_width=True):
            try:
                doc_pdf = init_connection()
                ws_pdf = doc_pdf.worksheet("BD_COTIZACIONES")
                d_p = ws_pdf.get_all_values()
                if len(d_p) > 1:
                    df_pdf = pd.DataFrame(d_p[1:], columns=[str(h).strip() for h in d_p[0]])
                    df_pdf_pend = df_pdf[df_pdf['Estatus_Cotizacion'].astype(str).str.upper() == 'PENDIENTE']
                    if not df_pdf_pend.empty:
                        pdf_rep = FPDF(orientation='L', unit='mm', format='A4')
                        pdf_rep.set_auto_page_break(auto=True, margin=10)
                        pdf_rep.add_page()
                        pdf_rep.set_font("Arial", 'B', 12)
                        pdf_rep.cell(0, 8, "REPORTE DE COTIZACIONES PENDIENTES - PMR HUB AI", ln=True, align='C')
                        pdf_rep.set_font("Arial", '', 8)
                        pdf_rep.cell(0, 5, f"Fecha de emision: {datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-6))).strftime('%d/%m/%Y')}", ln=True, align='C')
                        pdf_rep.ln(4)

                        pdf_rep.set_fill_color(0, 51, 102)
                        pdf_rep.set_text_color(255, 255, 255)
                        pdf_rep.set_font("Arial", 'B', 8)
                        headers_p_pdf = ['Siniestro', 'Taller', 'Vehiculo', 'Pieza', 'Origen', 'Costo', 'Flete', 'Final']
                        widths_pdf = [25, 45, 55, 75, 22, 18, 18, 22]
                        for h_i, h_t in enumerate(headers_p_pdf):
                            pdf_rep.cell(widths_pdf[h_i], 6, h_t, border=1, fill=True, align='C')
                        pdf_rep.ln()

                        pdf_rep.set_text_color(0, 0, 0)
                        pdf_rep.set_font("Arial", '', 7)
                        for _, rp in df_pdf_pend.iterrows():
                            pdf_rep.cell(widths_pdf[0], 5, str(rp.get('Siniestro',''))[:15], border=1)
                            pdf_rep.cell(widths_pdf[1], 5, str(rp.get('Taller',''))[:30], border=1)
                            pdf_rep.cell(widths_pdf[2], 5, f"{rp.get('Marca','')} {rp.get('Vehiculo','')}"[:35], border=1)
                            pdf_rep.cell(widths_pdf[3], 5, str(rp.get('Descripcion_Portal',''))[:45], border=1)
                            pdf_rep.cell(widths_pdf[4], 5, str(rp.get('Origen_Portal',''))[:12], border=1, align='C')
                            pdf_rep.cell(widths_pdf[5], 5, f"${float(rp.get('Costo_Base',0) or 0):,.0f}", border=1, align='R')
                            pdf_rep.cell(widths_pdf[6], 5, f"${float(rp.get('Flete_Estimado',0) or 0):,.0f}", border=1, align='R')
                            pdf_rep.cell(widths_pdf[7], 5, f"${float(rp.get('Precio_Final_Enviar',0) or 0):,.0f}", border=1, align='R')
                            pdf_rep.ln()

                        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_p:
                            pdf_rep.output(tmp_p.name)
                            with open(tmp_p.name, "rb") as f_p: pdf_b_rep = f_p.read()
                        st.download_button(
                            label="📥 Descargar PDF Generado",
                            data=pdf_b_rep,
                            file_name=f"Reporte_Cotizaciones_{datetime.datetime.now().strftime('%d%m%Y')}.pdf",
                            mime="application/pdf",
                            type="primary",
                            key="dl_pdf_cotizaciones_gen"
                        )
                    else:
                        st.warning("No hay cotizaciones pendientes para generar el PDF.")
            except Exception as e_pdf:
                st.error(f"Error generando PDF: {e_pdf}")

        if col_btn_ref_c.button("🔄 Refrescar", use_container_width=True):
            leer_cotizaciones_cache.clear()
            st.rerun()

        if os.path.exists("evidencia_antes_grabar.png") or os.path.exists("evidencia_despues_grabar.png"):
            if col_btn_limp.button("🧹 Limpiar Evidencias", use_container_width=True, key="btn_limpiar_evidencias"):
                try:
                    if os.path.exists("evidencia_antes_grabar.png"): os.remove("evidencia_antes_grabar.png")
                    if os.path.exists("evidencia_despues_grabar.png"): os.remove("evidencia_despues_grabar.png")
                    st.success("Evidencias limpiadas.")
                    st.rerun()
                except Exception:
                    pass

        with st.expander("🖥️ Ver Bitácora de Ejecución en Vivo del Robot Cotizador", expanded=False):
            consola_cot_vivo = st.empty()
            consola_cot_vivo.code(st.session_state.get('log_cotizador_ai', 'Esperando orden de ejecución...'))

        try:
            datos_cot_ui = leer_cotizaciones_cache()
            df_cot_ui = pd.DataFrame(datos_cot_ui[1:], columns=[str(h).strip() for h in datos_cot_ui[0]]) if len(datos_cot_ui) > 1 else pd.DataFrame()
        except Exception:
            datos_cot_ui = []
            df_cot_ui = pd.DataFrame()

        if not df_cot_ui.empty and 'Estatus_Cotizacion' in df_cot_ui.columns:
            df_cot_ui['_GS_Row'] = df_cot_ui.index + 2
            df_cot_ui = df_cot_ui.drop_duplicates(subset=['Siniestro', 'Partida_Idx'], keep='last').copy()

            import urllib.parse

            # Archivar automáticamente en Historial las cotizaciones cuya Fecha_Fin ya venció
            if 'Fecha_Fin' in df_cot_ui.columns:
                hoy_cot_dt = pd.to_datetime(datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-6))).date())
                fechas_fin_dt = df_cot_ui['Fecha_Fin'].apply(parse_dt_safe_op)
                mask_vencidas_cot = (df_cot_ui['Estatus_Cotizacion'].astype(str).str.upper() == 'PENDIENTE') & fechas_fin_dt.notna() & (fechas_fin_dt < hoy_cot_dt)
                if mask_vencidas_cot.any():
                    try:
                        doc_arch = init_connection()
                        ws_arch = doc_arch.worksheet("BD_COTIZACIONES")
                        idx_est_col = [str(h).strip() for h in datos_cot_ui[0]].index("Estatus_Cotizacion") + 1
                        celdas_arch = [
                            gspread.Cell(row=int(r_gs), col=idx_est_col, value="HISTORIAL / CERRADA")
                            for r_gs in df_cot_ui.loc[mask_vencidas_cot, '_GS_Row']
                        ]
                        if celdas_arch:
                            ws_arch.update_cells(celdas_arch, value_input_option='USER_ENTERED')
                            leer_cotizaciones_cache.clear()
                            df_cot_ui.loc[mask_vencidas_cot, 'Estatus_Cotizacion'] = "HISTORIAL / CERRADA"
                    except Exception:
                        pass

            df_pend_cot = df_cot_ui[df_cot_ui['Estatus_Cotizacion'].astype(str).str.upper() == 'PENDIENTE'].copy()
            df_hist_cot = df_cot_ui[df_cot_ui['Estatus_Cotizacion'].astype(str).str.upper() != 'PENDIENTE'].copy()

            if not df_pend_cot.empty:
                for col_num in ['Precio_Original', 'Precio_No_Original', 'Precio_Generica', 'Precio_Historial', 'Flete_Estimado', 'Costo_Base', 'Margen_Pct', 'Precio_Sugerido', 'Precio_Libre', 'Precio_Final_Enviar']:
                    if col_num in df_pend_cot.columns:
                        df_pend_cot[col_num] = pd.to_numeric(df_pend_cot[col_num].astype(str).str.replace('$', '').str.replace(',', ''), errors='coerce').fillna(0.0)

                df_pend_cot['Validar_Bool'] = df_pend_cot['Validar_Envio'].astype(str).str.upper().isin(['TRUE', 'SI', '1', 'VERDADERO'])

                mapa_etiquetas_sin = {"Todos": f"📋 Todos los Siniestros Pendientes ({df_pend_cot['Siniestro'].nunique()})"}
                for sin_k, grp_s in df_pend_cot.groupby('Siniestro', sort=False):
                    r0 = grp_s.iloc[0]
                    marca_s = str(r0.get('Marca', '')).strip()
                    veh_s = str(r0.get('Vehiculo', '')).strip()
                    auto_str = veh_s if veh_s.upper().startswith(marca_s.upper()) else f"{marca_s} {veh_s}".strip()
                    ano_s = str(r0.get('Modelo_Ano', '')).strip()
                    tal_s = str(r0.get('Taller', '')).strip()
                    mapa_etiquetas_sin[sin_k] = f"{sin_k} {auto_str} {ano_s} {tal_s}".strip()

                sin_cot_sel = st.selectbox(
                    "🚗 Selecciona el Siniestro a revisar:",
                    options=list(mapa_etiquetas_sin.keys()),
                    format_func=lambda x: mapa_etiquetas_sin.get(x, x),
                    key="sel_siniestro_cot_ui"
                )
                if sin_cot_sel != "Todos":
                    df_pend_cot = df_pend_cot[df_pend_cot['Siniestro'] == sin_cot_sel].copy()

                primera = df_pend_cot.iloc[0]
                st.info(
                    f"🚘 **Vehículo:** {primera.get('Marca','')} {primera.get('Vehiculo','')} ({primera.get('Modelo_Ano','')}) | "
                    f"🔢 **VIN:** `{primera.get('VIN','')}` | 🏢 **Taller:** {primera.get('Taller','')} ({primera.get('Ciudad','')}, {primera.get('Estado','')}) | "
                    f"⏰ **Cierre Subasta:** {primera.get('Fecha_Fin','')}"
                )

                # Convertir las 3 columnas de precios en hipervínculos directos con el monto visible
                def construir_celdas_precio_link(row):
                    q_raw = str(row.get('Busqueda_Sugerida', row.get('Descripcion_Portal', ''))).strip().upper()
                    marca_r = str(row.get('Marca', '')).strip().upper()
                    vin_r = str(row.get('VIN', '')).strip()

                    # Traducir variantes regionales para la búsqueda en vivo (ej. REFLECTOR -> CUARTO REFLEJANTE)
                    q_radec = q_raw.replace("REFLECTOR", "CUARTO REFLEJANTE").replace("REFLEJANTE", "CUARTO REFLEJANTE")
                    q_radec = re.sub(r'\bCUARTO\s+CUARTO\b', 'CUARTO', q_radec)
                    if marca_r:
                        q_radec = q_radec.replace(f" {marca_r} ", " ")

                    # 1. ORIGINAL -> PartSouq por VIN o búsqueda OEM de la pieza exacta
                    url_orig = f"https://www.google.com/search?q={urllib.parse.quote(q_raw + ' ' + vin_r + ' OEM original partsouq')}"
                    # 2. NO ORIG (Semi) -> Mercado Libre México de la pieza exacta
                    url_semi = f"https://listado.mercadolibre.com.mx/{urllib.parse.quote(q_raw.replace(' ', '-'))}"
                    # 3. GENÉRICA -> Exclusivo en Radec sin mezclar Mercado Libre y sin URLs 404 inventadas
                    url_gen = f"https://www.google.com/search?q={urllib.parse.quote('site:radec.com.mx ' + q_radec)}"

                    urls_fijas = [url_orig, url_semi, url_gen]
                    res = []
                    for idx_c, col_p in enumerate(['Precio_Original', 'Precio_No_Original', 'Precio_Generica']):
                        val_p = float(row.get(col_p, 0) or 0)
                        url_c = urls_fijas[idx_c]
                        if val_p > 0:
                            res.append(f"{url_c}#$ {val_p:,.0f}")
                        else:
                            res.append(f"{url_c}#$ 0")
                    return pd.Series(res)

                df_pend_cot[['Link_Precio_Orig', 'Link_Precio_Semi', 'Link_Precio_Gen']] = df_pend_cot.apply(construir_celdas_precio_link, axis=1)

                cols_tabla_cot = [
                    c for c in [
                        'Siniestro', 'Partida_Idx', 'Cantidad', 'Descripcion_Portal',
                        'Link_Precio_Orig', 'Link_Precio_Semi', 'Link_Precio_Gen', 'Precio_Historial',
                        'Flete_Estimado', 'Fuente_Seleccionada', 'Origen_Portal',
                        'Costo_Base', 'Margen_Pct', 'Precio_Sugerido', 'Precio_Libre',
                        'Codigo_Hub', 'Validar_Bool'
                    ] if c in df_pend_cot.columns
                ]

                with st.form("form_mesa_cotizador_estable", clear_on_submit=False):
                    ed_cot_df = st.data_editor(
                        df_pend_cot[cols_tabla_cot],
                        hide_index=True,
                        use_container_width=True,
                        column_config={
                            'Siniestro': st.column_config.TextColumn("Siniestro", disabled=True, width="small"),
                            'Partida_Idx': st.column_config.NumberColumn("#", disabled=True, width="small"),
                            'Cantidad': st.column_config.TextColumn("Cant", disabled=True, width="small"),
                            'Descripcion_Portal': st.column_config.TextColumn("Pieza", disabled=True, width="medium"),
                            'Link_Precio_Orig': st.column_config.LinkColumn("1. ORIGINAL", display_text=r"#(.*)$", disabled=True, width="small"),
                            'Link_Precio_Semi': st.column_config.LinkColumn("2. NO ORIG (Semi)", display_text=r"#(.*)$", disabled=True, width="small"),
                            'Link_Precio_Gen': st.column_config.LinkColumn("3. GENÉRICA", display_text=r"#(.*)$", disabled=True, width="small"),
                            'Precio_Historial': st.column_config.NumberColumn("Hist. PMR", format="$ %.0f", disabled=True, width="small"),
                            'Flete_Estimado': st.column_config.NumberColumn("🚚 Flete", format="$ %.0f", width="small"),
                            'Fuente_Seleccionada': st.column_config.SelectboxColumn("Dónde Comprar", options=["ML", "EB", "RADEC", "PARTSOUQ", "INV", "LOC", "AGENCIA", "MAN"], width="small"),
                            'Origen_Portal': st.column_config.SelectboxColumn("Origen Portal", options=["ORIGINAL", "NO ORIGINAL", "SEMINUEVA"], width="small"),
                            'Costo_Base': st.column_config.NumberColumn("Costo Base", format="$ %.0f", width="small"),
                            'Margen_Pct': st.column_config.SelectboxColumn("% Utilidad", options=[15, 20, 25, 30, 35, 40, 45, 50, 60, 65, 70, 75, 80, 85, 90, 100], width="small"),
                            'Precio_Sugerido': st.column_config.NumberColumn("💡 Sugerido", format="$ %.0f", disabled=True, width="small"),
                            'Precio_Libre': st.column_config.NumberColumn("✍️ Precio Libre", format="$ %.0f", help="Si escribes un monto > 0 aquí, este se enviará al portal en lugar del sugerido.", width="small"),
                            'Codigo_Hub': st.column_config.TextColumn("Código Portal", width="small"),
                            'Validar_Bool': st.column_config.CheckboxColumn("✅ Validar", default=False, width="small")
                        },
                        key="editor_mesa_cotizador"
                    )

                    c_f1, c_f2 = st.columns(2)
                    btn_save_borrador = c_f1.form_submit_button("💾 Guardar Cambios / Recalcular Sugeridos", use_container_width=True)
                    btn_run_env = c_f2.form_submit_button("🚀 Guardar Selección y Enviar Validadas al Portal (7 Días)", type="primary", use_container_width=True)

                def guardar_cambios_mesa_en_sheet():
                    headers_c = [str(h).strip() for h in datos_cot_ui[0]]
                    celdas_cot_upd = []
                    import random

                    for idx_r in ed_cot_df.index:
                        gs_r = int(df_pend_cot.loc[idx_r, '_GS_Row'])
                        fila_ed = ed_cot_df.loc[idx_r]

                        costo_b = float(fila_ed['Costo_Base'])
                        flete_b = float(fila_ed['Flete_Estimado'])
                        margen_b = float(fila_ed['Margen_Pct'])
                        libre_b = float(fila_ed['Precio_Libre'])
                        fuente_b = str(fila_ed['Fuente_Seleccionada']).strip().upper()
                        origen_b = str(fila_ed['Origen_Portal']).strip().upper()
                        validar_b = "TRUE" if fila_ed['Validar_Bool'] else "FALSE"

                        nuevo_sug = max(1000, round((costo_b + flete_b) * (1.0 + margen_b / 100.0))) if costo_b > 0 else 0
                        precio_final_env = max(1000, round(libre_b)) if libre_b > 0 else nuevo_sug

                        cod_actual = str(fila_ed['Codigo_Hub']).strip().upper()
                        sufijo_num = re.findall(r'\d{3}$', cod_actual)
                        num_3 = sufijo_num[0] if sufijo_num else str(random.randint(100, 999))
                        tag_prov = re.sub(r'[^A-Z]', '', fuente_b)[:5]
                        if not tag_prov: tag_prov = "RAD"
                        nuevo_cod_hub = f"HUB{tag_prov}{num_3}"

                        cambios_fila = {
                            'Flete_Estimado': flete_b,
                            'Fuente_Seleccionada': fuente_b,
                            'Origen_Portal': origen_b,
                            'Costo_Base': costo_b,
                            'Margen_Pct': margen_b,
                            'Precio_Sugerido': nuevo_sug,
                            'Precio_Libre': libre_b,
                            'Precio_Final_Enviar': precio_final_env,
                            'Codigo_Hub': nuevo_cod_hub,
                            'Validar_Envio': validar_b
                        }
                        for col_k, val_k in cambios_fila.items():
                            if col_k in headers_c:
                                celdas_cot_upd.append(gspread.Cell(row=gs_r, col=headers_c.index(col_k) + 1, value=val_k))

                    if celdas_cot_upd:
                        doc_upd = init_connection()
                        ws_upd = doc_upd.worksheet("BD_COTIZACIONES")
                        ws_upd.update_cells(celdas_cot_upd, value_input_option='USER_ENTERED')
                        leer_cotizaciones_cache.clear()

                if btn_save_borrador:
                    with st.spinner("Guardando borrador en BD_COTIZACIONES..."):
                        guardar_cambios_mesa_en_sheet()
                        st.success("✅ Cambios guardados y precios recalculados.")
                        time.sleep(0.5)
                        st.rerun()

                if btn_run_env:
                    with st.spinner("Guardando tu selección antes de abrir el portal..."):
                        guardar_cambios_mesa_en_sheet()
            else:
                st.info("No hay cotizaciones pendientes en la mesa. Presiona **🔎 1. Extraer Nuevas Cotizaciones del Portal**.")

            if not df_hist_cot.empty:
                with st.expander(f"📊 Historial de Cotizaciones Enviadas al Portal ({len(df_hist_cot)} partidas) — Marca para regresar a la mesa si requieres reenviar", expanded=False):
                    df_hist_view = df_hist_cot.copy()
                    df_hist_view['Reenviar_Bool'] = False
                    cols_hist_ver = [
                        c for c in [
                            'Reenviar_Bool', 'Fecha_Extraccion', 'Siniestro', 'Marca', 'Vehiculo',
                            'Modelo_Ano', 'Taller', 'Descripcion_Portal', 'Precio_Final_Enviar',
                            'Origen_Portal', 'Codigo_Hub'
                        ] if c in df_hist_view.columns
                    ]
                    ed_hist_cot = st.data_editor(
                        df_hist_view[cols_hist_ver],
                        hide_index=True,
                        use_container_width=True,
                        column_config={
                            'Reenviar_Bool': st.column_config.CheckboxColumn("🔄 Reenviar", default=False, width="small"),
                            'Precio_Final_Enviar': st.column_config.TextColumn("Precio Enviado", disabled=True),
                            'Descripcion_Portal': st.column_config.TextColumn("Pieza", disabled=True)
                        },
                        disabled=[c for c in cols_hist_ver if c != 'Reenviar_Bool'],
                        key="editor_historial_cot_reenvio"
                    )
                    seleccion_reenviar = ed_hist_cot[ed_hist_cot['Reenviar_Bool'] == True]
                    if not seleccion_reenviar.empty:
                        if st.button("♻️ Regresar Seleccionadas a la Mesa (Cambiar a PENDIENTE)", type="primary", key="btn_revivir_cot"):
                            with st.spinner("Devolviendo partidas a la mesa de cotización..."):
                                doc_rev = init_connection()
                                ws_rev = doc_rev.worksheet("BD_COTIZACIONES")
                                headers_rev = [str(h).strip() for h in datos_cot_ui[0]]
                                idx_est_rev = headers_rev.index("Estatus_Cotizacion") + 1
                                idx_val_rev = headers_rev.index("Validar_Envio") + 1
                                celdas_rev = []
                                for idx_sel in seleccion_reenviar.index:
                                    gs_row_rev = int(df_hist_cot.loc[idx_sel, '_GS_Row'])
                                    celdas_rev.append(gspread.Cell(row=gs_row_rev, col=idx_est_rev, value="PENDIENTE"))
                                    celdas_rev.append(gspread.Cell(row=gs_row_rev, col=idx_val_rev, value="TRUE"))
                                if celdas_rev:
                                    ws_rev.update_cells(celdas_rev, value_input_option='USER_ENTERED')
                                    leer_cotizaciones_cache.clear()
                                    st.success("✅ Partida(s) devuelta(s) a la mesa listas para enviar.")
                                    time.sleep(0.5)
                                    st.rerun()
        else:
            st.info("Aún no existen registros en `BD_COTIZACIONES`. Presiona **🔎 1. Extraer Nuevas Cotizaciones del Portal**.")

        if btn_run_ext or btn_run_env:
            accion_flag = "--extraer" if btn_run_ext else "--enviar"
            with st.spinner("Ejecutando robot cotizador en vivo..."):
                try:
                    with open("credentials.json", "w", encoding="utf-8") as f:
                        f.write(st.secrets["google_credentials"])
                    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=False)

                    env_cot = os.environ.copy()
                    env_cot["PYTHONIOENCODING"] = "utf-8"
                    env_cot["PYTHONUNBUFFERED"] = "1"

                    proc_cot = subprocess.Popen(
                        [sys.executable, "-u", "cotizador_multiasistencia.py", accion_flag, arg_vis_cot],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1,
                        env=env_cot,
                        encoding="utf-8",
                        errors="replace"
                    )
                    lineas_cot = []
                    for linea_c in iter(proc_cot.stdout.readline, ''):
                        if not linea_c:
                            break
                        lineas_cot.append(linea_c)
                        consola_cot_vivo.code("".join(lineas_cot))

                    proc_cot.stdout.close()
                    proc_cot.wait()
                    st.session_state['log_cotizador_ai'] = "".join(lineas_cot)
                    leer_cotizaciones_cache.clear()
                    st.rerun()
                finally:
                    if os.path.exists("credentials.json"):
                        os.remove("credentials.json")

        if os.path.exists("evidencia_antes_grabar.png") or os.path.exists("evidencia_despues_grabar.png"):
            with st.expander("📸 Ver Evidencia Visual de Chrome en el Portal (Antes y Después de Grabar)", expanded=True):
                c_ev1, c_ev2 = st.columns(2)
                if os.path.exists("evidencia_antes_grabar.png"):
                    c_ev1.image("evidencia_antes_grabar.png", caption="1. Pliego llenado antes de presionar Grabar")
                if os.path.exists("evidencia_despues_grabar.png"):
                    c_ev2.image("evidencia_despues_grabar.png", caption="2. Respuesta del portal tras presionar Grabar")

# ==============================================================================
# === [BLOQUE 10: MOTOR DE GUARDADO Y SINCRONIZACIÓN] ===
# ==============================================================================
trigger_rem = st.session_state.pop('trigger_remision_manual', None)

if permiso_edicion:
    if btn_guardar or trigger_rem:
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
    col_guia_univ = buscar_columna(df_completo, ["GUIA", "GUÍA", "NO. GUIA"], ["GUIA", "GUÍA"], excluidos=["RETORNO", "DEV", "ENV", "PAGO"])
    col_guia_dev_univ = buscar_columna(df_completo, ["GUIA RETORNO", "GUÍA RETORNO", "GUIA DEVOLUCION", "GUÍA DEVOLUCIÓN"], ["GUIA RET", "GUIA DEV"])
    col_rem_univ = buscar_columna(df_completo, ["REMISION", "REMISIÓN", "FOLIO REMISION"], ["REMISION", "REMISIÓN"])
    col_coment_univ = buscar_columna(df_completo, ["COMENTARIOS", "OBSERVACIONES", "COMENTARIO", "OBSERVACION"], ["COMENTARIO", "OBSERVACION"])
    col_venc_univ = buscar_columna(df_completo, ["VENCIMIENTO", "FECHA VENCIMIENTO", "PROMESA"], ["VENCIMIENTO", "PROMESA"])
    col_asig_univ = buscar_columna(df_completo, ["ASIGNACION", "FECHA ASIGNACION"], ["ASIGNACI"])
    
    # Filtrar todas las tablas operativas estrictamente por edited_rows (Cero falsos positivos y máxima velocidad)
    def filtrar_solo_editadas(df_ed, state_key):
        if df_ed is None or not isinstance(df_ed, pd.DataFrame) or df_ed.empty:
            return pd.DataFrame()
        filas_idx = [
            int(i) for i in st.session_state.get(state_key, {}).get("edited_rows", {}).keys()
            if str(i).isdigit() and int(i) < len(df_ed)
        ]
        return df_ed.iloc[filas_idx].copy() if filas_idx else pd.DataFrame()

    df_editado_venc = filtrar_solo_editadas(df_editado_venc, "ed_venc")
    df_editado_atrasadas = filtrar_solo_editadas(df_editado_atrasadas, "ed_atr")
    df_editado_cobro = filtrar_solo_editadas(df_editado_cobro, "ed_entregados_op_dia" if vista_actual == "🚚 Operación del Día" else "ed_cobro")
    df_editado_reemb = filtrar_solo_editadas(df_editado_reemb, "ed_reemb")
    if 'df_editado_rec' in locals():
        df_editado_rec = filtrar_solo_editadas(df_editado_rec, "ed_rec_panel")
    if 'df_editado_transito_op' in locals():
        df_editado_transito_op = filtrar_solo_editadas(df_editado_transito_op, "ed_transito_op_dia")
    df_editado_fact = filtrar_solo_editadas(df_editado_fact, "ed_facturacion")

    if vista_actual == "🛒 Compras":
        k_cap_fast = f"ed_pendientes_compra_rapida_{st.session_state.get('reset_key_compras', 0)}"
        st.session_state['df_cap_edit_temp'] = filtrar_solo_editadas(st.session_state.get('df_cap_edit_temp', pd.DataFrame()), k_cap_fast)

    hay_ediciones_activas = any(
        isinstance(d, pd.DataFrame) and not d.empty for d in [
            df_editado_conf, df_editado_venc, df_editado_atrasadas, df_editado_cobro,
            df_editado, df_editado_reemb,
            locals().get('df_editado_rec', pd.DataFrame()),
            locals().get('df_editado_transito_op', pd.DataFrame()),
            df_editado_fact,
            st.session_state.get('df_cap_edit_temp', pd.DataFrame()) if vista_actual == "🛒 Compras" else pd.DataFrame(),
            filtrar_solo_editadas(st.session_state.get('df_editado_compras_temp', pd.DataFrame()), "ed_compras_main") if vista_actual == "🛒 Compras" else pd.DataFrame()
        ]
    )

    originales = {}
    compras_previas_map = {}
    if hay_ediciones_activas or btn_guardar or trigger_rem:
        for _, r in df_completo.iterrows():
            k = generar_llave(r.get(col_id_univ, ''), r.get(col_desc_univ, ''))
            raw_venc = str(r.get(col_venc_univ, '')).strip() if col_venc_univ else ""
            venc_formateada = estandarizar_fechas_mx(raw_venc) if raw_venc else ""

            originales[k] = {
                'comentario': str(r.get(col_coment_univ, '')).strip() if col_coment_univ else '',
                'paqueteria': str(r.get(col_paqueteria_univ, '')).strip() if col_paqueteria_univ else '',
                'guia': str(r.get(col_guia_univ, '')).strip() if col_guia_univ else '',
                'guia_retorno': str(r.get(col_guia_dev_univ, '')).strip() if col_guia_dev_univ else '',
                'estatus_db': str(r.get(col_estatus_univ, '')).strip().upper() if col_estatus_univ else '',
                'remision_bool': str(r.get(col_rem_univ, '')).strip() != '' if col_rem_univ else False,
                'vencimiento_db': venc_formateada,
                'asignacion_db': str(r.get(col_asig_univ, '')).strip() if col_asig_univ else ''
            }

        if not df_compras.empty:
            for _, r_cp in df_compras.iterrows():
                k_cp = generar_llave(r_cp.get('Siniestro', ''), r_cp.get('Descripción Pieza', ''))
                try:
                    c_cp_f = float(str(r_cp.get('Costo Compra', '0')).replace('$', '').replace(',', '').strip() or 0.0)
                except Exception:
                    c_cp_f = 0.0
                compras_previas_map[k_cp] = {
                    'prov': str(r_cp.get('Proveedor', '')).strip(),
                    'costo': round(c_cp_f, 2)
                }

    cambios_a_guardar = {}
    cambios_bd_compras = {}
    tz_mx = datetime.timezone(datetime.timedelta(hours=-6))
    fecha_hoy_sistema = datetime.datetime.now(tz_mx).strftime('%d/%b/%y')

    if trigger_rem:
        dir_trig = str(trigger_rem.get('direccion_elegida', '')).strip()
        nota_trig = str(trigger_rem.get('nota_remision', '')).strip()
        for desc in trigger_rem['descripciones']:
            k = generar_llave(trigger_rem['siniestro'], desc)
            orig = originales.get(k, {'remision_bool': False})
            cambios_a_guardar.setdefault(k, {}).update({
                'estatus': 'EN TRANSITO',
                'imprimir_remision': True,
                'usuario_rem': st.session_state.get('usuario_actual', 'Sistema'),
                'fecha_envio': fecha_hoy_sistema,
                'direccion_elegida': dir_trig,
                'nota_remision': nota_trig
            })
            if not orig['remision_bool']: cambios_a_guardar[k]['generar_nuevo_folio'] = True

    if hay_ediciones_activas:
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

        # --- INICIO DEL BLOQUE A REEMPLAZAR 1 ---
        if 'df_editado_rec' in locals() and not df_editado_rec.empty:
            for _, row in df_editado_rec.iterrows():
                k = generar_llave(row.get(col_id, ''), row.get(col_desc, ''))
                orig = originales.get(k, {'comentario': '', 'paqueteria': '', 'guia': '', 'guia_retorno': '', 'estatus_db': ''})
                
                comentario_actual = str(row.get(col_comentarios, '')).strip()
                paq_actual = str(row.get(col_paqueteria, '')).strip()
                guia_actual = str(row.get(col_guia, '')).strip()
                guia_retorno_nueva = str(row.get('Guia_Retorno', '')).strip()
                en_retorno_chk = bool(row.get('En_Retorno', False))
                dev_recibida_chk = bool(row.get('Devolucion_Recibida', False))
                
                if dev_recibida_chk:
                    cambios_a_guardar.setdefault(k, {})['estatus'] = 'CANCELADO' 
                    cambios_a_guardar[k]['estatus_envio'] = 'Devolución Recibida'
                else:
                    if comentario_actual != orig['comentario']: cambios_a_guardar.setdefault(k, {})['comentario'] = comentario_actual
                    if paq_actual != orig['paqueteria']: cambios_a_guardar.setdefault(k, {})['paqueteria'] = paq_actual
                    if guia_actual != orig['guia']: cambios_a_guardar.setdefault(k, {})['guia'] = guia_actual
                    
                    if guia_retorno_nueva != orig['guia_retorno'] and guia_retorno_nueva not in ['', 'nan', 'None', 'NAN']:
                        cambios_a_guardar.setdefault(k, {})['guia_retorno'] = guia_retorno_nueva
                        cambios_a_guardar[k]['estatus'] = 'EN TRANSITO (RECOLECCIÓN)'
                        cambios_a_guardar[k]['estatus_envio'] = 'Recolección en Tránsito'
                        cambios_a_guardar[k]['fecha_envio'] = fecha_hoy_sistema
                    elif en_retorno_chk and orig['estatus_db'] != 'EN TRANSITO (RECOLECCIÓN)':
                        cambios_a_guardar.setdefault(k, {})['estatus'] = 'EN TRANSITO (RECOLECCIÓN)'
                        cambios_a_guardar[k]['estatus_envio'] = 'Recolección en Tránsito'
        # --- FIN DEL BLOQUE A REEMPLAZAR 1 ---

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
                    try:
                        costo_asig_num = round(float(str(row.get('Costo Compra', '0')).replace('$', '').replace(',', '').strip() or 0.0), 2)
                    except Exception:
                        costo_asig_num = 0.0
                    prev_cp = compras_previas_map.get(k, {'prov': '', 'costo': 0.0})
                    cambio_compra_real = (prov_asignado != prev_cp['prov']) or (costo_asig_num != prev_cp['costo'])

                    if prov_asignado != '' and cambio_compra_real and cambios_a_guardar.get(k, {}).get('estatus', orig['estatus_db']) != "CANCELADO":
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
            filas_mod_comp = [
                int(i) for i in st.session_state.get("ed_compras_main", {}).get("edited_rows", {}).keys()
                if str(i).isdigit() and int(i) < len(df_editado_compras)
            ]
            df_editado_compras_mod = df_editado_compras.iloc[filas_mod_comp] if (not df_editado_compras.empty and filas_mod_comp) else pd.DataFrame()

            if not df_editado_compras_mod.empty:
                for _, row in df_editado_compras_mod.iterrows():
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

    # --- POP-UP INTERCEPTOR DE CAMBIOS SIN GUARDAR AL CAMBIAR DE PESTAÑA ---
    vista_previa_ux = st.session_state.get('_vista_ux_anterior', vista_actual)
    cambio_de_pestana = (vista_actual != vista_previa_ux)
    st.session_state['_vista_ux_anterior'] = vista_actual

    ejecutar_guardado_popup = st.session_state.pop('_ux_confirmar_guardado', False)
    if ejecutar_guardado_popup:
        cambios_a_guardar = st.session_state.pop('_ux_pend_uni', {})
        cambios_bd_compras = st.session_state.pop('_ux_pend_comp', {})
        st.session_state.pop('_ux_mostrar_popup', None)
        st.session_state.pop('_ux_vista_origen', None)
    elif btn_guardar or trigger_rem:
        st.session_state.pop('_ux_pend_uni', None)
        st.session_state.pop('_ux_pend_comp', None)
        st.session_state.pop('_ux_mostrar_popup', None)
        st.session_state.pop('_ux_vista_origen', None)
    else:
        if not cambio_de_pestana:
            if cambios_a_guardar or cambios_bd_compras:
                st.session_state['_ux_pend_uni'] = cambios_a_guardar
                st.session_state['_ux_pend_comp'] = cambios_bd_compras
                st.session_state['_ux_vista_origen'] = vista_actual
            elif st.session_state.get('_ux_vista_origen') == vista_actual and not st.session_state.get('_ux_mostrar_popup'):
                st.session_state.pop('_ux_pend_uni', None)
                st.session_state.pop('_ux_pend_comp', None)
                st.session_state.pop('_ux_vista_origen', None)
        else:
            if st.session_state.get('_ux_pend_uni') or st.session_state.get('_ux_pend_comp'):
                st.session_state['_ux_mostrar_popup'] = True

    @st.dialog("⚠️ Cambios pendientes por guardar")
    def abrir_popup_cambios_sin_guardar():
        pend_u = st.session_state.get('_ux_pend_uni', {})
        pend_c = st.session_state.get('_ux_pend_comp', {})
        vista_orig_txt = st.session_state.get('_ux_vista_origen', 'la pestaña anterior')
        llaves_mod = list(set(list(pend_u.keys()) + list(pend_c.keys())))

        st.warning(f"Realizaste modificaciones en **{len(llaves_mod)} partida(s)** dentro de **{vista_orig_txt}** y cambiaste de pestaña sin guardar.")
        with st.container(border=True):
            st.caption("📋 **Partidas con cambios pendientes:**")
            for k_s, k_d in llaves_mod[:8]:
                st.markdown(f"- **`{k_s}`** — {k_d}")
            if len(llaves_mod) > 8:
                st.caption(f"... y {len(llaves_mod) - 8} partida(s) más.")

        col_p_save, col_p_cancel = st.columns(2)
        if col_p_save.button("💾 Guardar Cambios", type="primary", use_container_width=True, key="btn_pop_ux_save"):
            st.session_state['_ux_confirmar_guardado'] = True
            st.session_state['_ux_mostrar_popup'] = False
            st.rerun()
        if col_p_cancel.button("🚫 Descartar / Cancelar", use_container_width=True, key="btn_pop_ux_discard"):
            st.session_state.pop('_ux_pend_uni', None)
            st.session_state.pop('_ux_pend_comp', None)
            st.session_state.pop('_ux_mostrar_popup', None)
            st.session_state.pop('_ux_vista_origen', None)
            st.toast("🗑️ Cambios no guardados descartados.", icon="🗑️")
            st.rerun()

    if st.session_state.get('_ux_mostrar_popup') and (st.session_state.get('_ux_pend_uni') or st.session_state.get('_ux_pend_comp')):
        abrir_popup_cambios_sin_guardar()

    if (cambios_a_guardar or cambios_bd_compras) and (btn_guardar or trigger_rem or ejecutar_guardado_popup):
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

                        # --- INICIO DEL BLOQUE A REEMPLAZAR 2 ---
                        def mapear_columnas(headers, datos_matriz=None):
                            if not headers: return {}
                            
                            def safe_idx(exactos, parciales, excluidos):
                                col_name = buscar_columna(headers, exactos, parciales, excluidos)
                                if col_name: return headers.index(col_name)
                                if datos_matriz is not None and "RETORNO" in exactos[0]:
                                    headers.append("GUIA RETORNO")
                                    datos_matriz[0].append("GUIA RETORNO")
                                    for fila in datos_matriz[1:]: fila.append("")
                                    return len(headers) - 1
                                return -1

                            return {
                                'id': safe_idx(["PEDIDO / SINIESTRO", "SINIESTRO"], ["SINIESTRO"], []),
                                'desc': safe_idx(["DESCRIPCIÓN", "DESCRIPCION"], ["DESCRIPCI", "REFACCI"], []),
                                'estatus': safe_idx(["ESTATUS", "STATUS"], ["ESTATUS", "STATUS"], []),
                                'est_env': safe_idx(["ESTATUS ENVIO", "ESTATUS ENVÍO", "RASTREO"], ["ESTATUS ENV", "RASTREO"], []),
                                'rem': safe_idx(["REMISION", "REMISIÓN", "FOLIO REMISION"], ["REMISION", "REMISIÓN"], []),
                                'usr_rem': safe_idx(["USUARIO REMISION", "USUARIO REMISIÓN"], ["USUARIO REM"], []),
                                'coment': safe_idx(["COMENTARIOS", "COMENTARIO", "OBSERVACION"], ["COMENTARIO", "OBSERVACION"], []),
                                'paq': safe_idx(["PAQUETERIA", "PAQUETERÍA"], ["PAQUETER"], []),
                                'guia': safe_idx(["GUIA", "GUÍA", "NO. GUIA"], ["GUIA", "GUÍA"], ["RETORNO", "DEV"]),
                                'guia_ret': safe_idx(["GUIA RETORNO", "GUÍA RETORNO", "GUIA DEVOLUCION", "GUÍA DEVOLUCIÓN"], ["GUIA RET", "GUIA DEV"], []),
                                'venc': safe_idx(["VENCIMIENTO", "FECHA VENCIMIENTO", "PROMESA"], ["VENCIMIENTO", "PROMESA"], []),
                                'asig': safe_idx(["ASIGNACION", "FECHA ASIGNACION"], ["ASIGNACI"], []),
                                'confi': safe_idx(["CONFIRMACION", "FECHA CONFIRMACION"], ["FECHA CONFI"], []),
                                'envio': safe_idx(["FECHA ENVIO", "FECHA ENVÍO"], ["FECHA ENV"], []),
                                'recibido': safe_idx(["FECHA RECIBIDO"], ["FECHA REC"], []),
                                'fact': safe_idx(["FECHA FACTURACION", "FECHA FACTURACIÓN"], ["FECHA FAC"], [])
                            }
                        # --- FIN DEL BLOQUE A REEMPLAZAR 2 ---

                        mapa_uni = mapear_columnas(headers_uni, datos_uni)
                        mapa_hist = mapear_columnas(headers_hist, datos_hist)

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

                        # --- INICIO DEL BLOQUE A REEMPLAZAR 3 ---
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
                                    if 'guia_retorno' in c and mapa_hoja.get('guia_ret', -1) >= 0: datos_hoja[i][mapa_hoja['guia_ret']] = c['guia_retorno'] # <-- ESCRITURA EN SHEETS AQUÍ
                                    if 'vencimiento' in c and mapa_hoja['venc'] >= 0: datos_hoja[i][mapa_hoja['venc']] = c['vencimiento']
                                    if 'asignacion' in c and mapa_hoja['asig'] >= 0: datos_hoja[i][mapa_hoja['asig']] = c['asignacion']
                                    if 'fecha_confi' in c and mapa_hoja['confi'] >= 0: datos_hoja[i][mapa_hoja['confi']] = c['fecha_confi']
                                    if 'fecha_envio' in c and mapa_hoja['envio'] >= 0: datos_hoja[i][mapa_hoja['envio']] = c['fecha_envio']
                                    if 'fecha_recibido' in c and mapa_hoja['recibido'] >= 0: datos_hoja[i][mapa_hoja['recibido']] = c['fecha_recibido']
                                    if 'fecha_facturacion' in c and mapa_hoja['fact'] >= 0: datos_hoja[i][mapa_hoja['fact']] = c['fecha_facturacion']
                            return cambio_realizado
# --- FIN DEL BLOQUE A REEMPLAZAR 3 ---

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
                            dir_elegida_pdf = ""
                            nota_rem_pdf = ""
                            for _, row_rem in df_g.iterrows():
                                key_rem = generar_llave(row_rem.get(col_id_univ, ''), row_rem.get(col_desc_univ, ''))
                                if key_rem in cambios_a_guardar:
                                    if folio_str_print == "S/N" and 'remision_num' in cambios_a_guardar[key_rem]:
                                        folio_str_print = cambios_a_guardar[key_rem]['remision_num']
                                    if not dir_elegida_pdf and cambios_a_guardar[key_rem].get('direccion_elegida'):
                                        dir_elegida_pdf = str(cambios_a_guardar[key_rem]['direccion_elegida']).strip()
                                    if not nota_rem_pdf and cambios_a_guardar[key_rem].get('nota_remision'):
                                        nota_rem_pdf = str(cambios_a_guardar[key_rem]['nota_remision']).strip()
                                    if folio_str_print != "S/N" and dir_elegida_pdf and nota_rem_pdf:
                                        break
                            
                            fecha_actual = datetime.datetime.now(tz_mx)
                            fecha_header = fecha_actual.strftime('%d/%b/%Y').upper()
                            firma_digital = f"Generado por: {usuario_print}"
                            
                            dir_v = dir_elegida_pdf
                            if not dir_v:
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

                                if nota_rem_pdf:
                                    y_nota = y_item + 4
                                    pdf.set_fill_color(220, 220, 220); pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", 'B', 7)
                                    pdf.set_xy(x_offset, y_nota); pdf.cell(135, 5, " NOTAS / OBSERVACIONES", border=1, fill=True)
                                    pdf.set_font("Arial", '', 7)
                                    pdf.set_left_margin(x_offset)
                                    pdf.set_xy(x_offset, y_nota + 5)
                                    pdf.multi_cell(135, 4.2, limpiar_texto(nota_rem_pdf)[:420], border=1)
                                    pdf.set_left_margin(10)

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
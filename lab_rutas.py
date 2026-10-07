# ==========================================
# 0. CONFIGURACIÓN, IMPORTS Y CONEXIÓN
# ==========================================
import streamlit as st
from streamlit_geolocation import streamlit_geolocation
import pandas as pd
import gspread
import json
from google.oauth2.service_account import Credentials
import datetime
import time

# Configuración enfocada en móviles
st.set_page_config(page_title="Rutas PMR", page_icon="🚚", layout="centered")

# --- CONEXIÓN A GOOGLE SHEETS ---
SHEET_ID = "10jrOsS054n0atMk8GxQilkXqm6LjsnrwPOZnSx8iDek"

@st.cache_resource
def init_connection():
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    cred_dict = json.loads(st.secrets["google_credentials"])
    credenciales = Credentials.from_service_account_info(cred_dict, scopes=scopes)
    cliente = gspread.authorize(credenciales)
    return cliente.open_by_key(SHEET_ID)

# ==========================================
# 1. SISTEMA DE LOGIN Y ESTILOS CSS
# ==========================================
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

st.markdown("""
    <style>
    div[data-testid="stExpander"] details summary p {
        font-size: 1.5rem !important;
        font-weight: 800 !important;
        color: #FFFFFF !important;
        line-height: 1.3 !important;
        padding-top: 5px !important;
        padding-bottom: 5px !important;
    }
    .stButton>button, .stLinkButton>a { 
        width: 100% !important; 
        height: 55px !important; 
        font-size: 16px !important; 
        font-weight: bold !important; 
        border-radius: 8px !important; 
        display: flex !important; 
        align-items: center !important; 
        justify-content: center !important;
        text-decoration: none !important;
        margin: 0px !important;
    }
    .tarjeta { background-color: #1E1E1E; padding: 20px; border-radius: 15px; margin-bottom: 10px; border: 1px solid #333;}
    .datos-auto { background-color: #2D2D2D; padding: 12px; border-radius: 8px; margin-bottom: 10px; font-size: 14px; color: #FFF; border-left: 4px solid #F63366;}
    .nota-operador { background-color: #3b2a00; border-left: 5px solid #FFD700; padding: 10px; margin-bottom: 15px; border-radius: 5px; color: #FFF; font-size: 15px;}
    </style>
""", unsafe_allow_html=True)

if not st.session_state['autenticado']:
    st.markdown("<h1 style='text-align: center; color: #FF4B4B;'>🚚 Acceso a Rutas</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Ingresa tus credenciales para ver tu ruta de hoy.</p>", unsafe_allow_html=True)
    
    with st.form("login_form"):
        usuario_input = st.text_input("👤 Usuario").strip().lower()
        password_input = st.text_input("🔑 Contraseña", type="password")
        btn_login = st.form_submit_button("Entrar a mi Ruta", use_container_width=True)
        
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
                    st.rerun()
                else: st.error("❌ Usuario o contraseña incorrectos.")
            except Exception as e: st.error(f"Error al conectar con la base de usuarios: {e}")
    st.stop()

# ==========================================
# 2. MOTOR DE DESCARGA DESDE LA NUBE
# ==========================================
def formatear_vin(vin):
    """Separa el VIN en bloques de 4 caracteres para facilitar lectura."""
    v = str(vin).replace(" ", "").upper()
    if not v or v in ['NAN', 'S/D', 'NONE']: return "S/D"
    return " ".join([v[i:i+4] for i in range(0, len(v), 4)])

def cargar_rutas_nube():
    try:
        doc = init_connection()
        ws_rutas = doc.worksheet("BD_RUTAS")
        datos = ws_rutas.get_all_values()
        
        if len(datos) > 1:
            headers = [str(h).strip() for h in datos[0]]
            df = pd.DataFrame(datos[1:], columns=headers)
            df_pendientes = df[df['Estatus_App'].astype(str).str.upper() == 'PENDIENTE'].copy()
            
            rutas_descargadas = []
            for _, row in df_pendientes.iterrows():
                texto_piezas = str(row.get('Piezas', 'Pieza general'))
                lista_piezas = [{"desc": p.strip(), "np": ""} for p in texto_piezas.split("|") if p.strip()]
                texto_siniestros = str(row.get('Siniestros', ''))
                lista_siniestros = [s.strip() for s in texto_siniestros.split(",") if s.strip()]
                nota_op = str(row.get('Notas', '')).strip() if 'Notas' in df.columns else ""
                
                parada = {
                    "id": str(row.get('ID_Ruta', '')),
                    "tipo": str(row.get('Tipo_Operacion', 'entrega')).lower(),
                    "lugar": str(row.get('Lugar', 'S/D')),
                    "direccion": str(row.get('Direccion', 'S/D')),
                    "vehiculo": str(row.get('Vehiculo', '')),
                    "serie": formatear_vin(row.get('VIN', '')),
                    "piezas": lista_piezas,
                    "siniestros": lista_siniestros,
                    "notas": nota_op
                }
                rutas_descargadas.append(parada)
            
            st.session_state['ruta_hoy'] = rutas_descargadas
            return True
    except Exception as e:
        st.error(f"Error conectando a BD_RUTAS: {e}")
        return False
    return False

if 'ruta_hoy' not in st.session_state: st.session_state['ruta_hoy'] = []
if 'parada_activa' not in st.session_state: st.session_state['parada_activa'] = None

# ==========================================
# 3. ENCABEZADO Y SINCRONIZACIÓN
# ==========================================
st.title("🚚 Mi Ruta de Hoy")
st.caption(f"👤 Operador: **{st.session_state['usuario_actual']}**")

if st.button("🔄 Sincronizar (Descargar Ruta)", use_container_width=True, type="primary"):
    with st.spinner("Descargando asignaciones..."):
        if cargar_rutas_nube(): st.toast("Ruta actualizada exitosamente", icon="☁️")
            
st.markdown("---")

# ==========================================
# 4. RENDERIZADO DE TARJETAS
# ==========================================
if not st.session_state['ruta_hoy']:
    st.info("👋 ¡Todo limpio! No tienes destinos pendientes.")
else:
    def cambiar_posicion_nombre(old_idx, key_selectbox):
        seleccion = st.session_state[key_selectbox]
        new_idx = int(seleccion.split(" - ")[0]) - 1
        if old_idx != new_idx:
            ruta = st.session_state['ruta_hoy']
            item = ruta.pop(old_idx)
            ruta.insert(new_idx, item)
            st.session_state['ruta_hoy'] = ruta

    for i, parada in enumerate(st.session_state['ruta_hoy']):
        
        # 4 COLORES TOTALMENTE INDEPENDIENTES
        if parada['tipo'] == 'entrega': icono = "🟢"
        elif parada['tipo'] == 'recoleccion': icono = "🟠"
        elif parada['tipo'] == 'compra': icono = "🟣"
        else: icono = "🔵" # cotizacion
            
        titulo_tarjeta = f"{icono} #{i+1} - {parada['lugar']}"
        
        with st.expander(titulo_tarjeta, expanded=False):
            opciones_orden = [f"{idx + 1} - {r['lugar']}" for idx, r in enumerate(st.session_state['ruta_hoy'])]
            st.selectbox("Mover al lugar:", options=opciones_orden, index=i, key=f"pos_{parada['id']}", on_change=cambiar_posicion_nombre, args=(i, f"pos_{parada['id']}"))
            
            st.markdown("---")
            st.caption(f"📍 **Dirección:** {parada['direccion']}")
            
            # --- NOTAS PARA EL OPERADOR ---
            if parada['notas']:
                st.markdown(f'<div class="nota-operador">⚠️ <b>INSTRUCCIÓN:</b> {parada["notas"]}</div>', unsafe_allow_html=True)
            
            # --- 4 VISTAS ESPECÍFICAS ---
            if parada['tipo'] == 'entrega':
                st.markdown(f"**Siniestro / Pedido:** {', '.join(parada['siniestros'])}")
                st.markdown(f'<div class="datos-auto">🚗 <b>Vehículo:</b> {parada.get("vehiculo", "S/D")}</div>', unsafe_allow_html=True)
                st.markdown(f"**📦 Piezas a Entregar ({len(parada['piezas'])}):**")
                for p in parada['piezas']: st.markdown(f"- {p['desc']}")

            elif parada['tipo'] == 'recoleccion':
                st.markdown(f"**Siniestro / Pedido:** {', '.join(parada['siniestros'])}")
                st.markdown(f'<div class="datos-auto">🚗 <b>Vehículo:</b> {parada.get("vehiculo", "S/D")}</div>', unsafe_allow_html=True)
                st.markdown(f"**↩️ Piezas a Recolectar (Devolución) ({len(parada['piezas'])}):**")
                for p in parada['piezas']: st.markdown(f"- {p['desc']}")

            elif parada['tipo'] == 'compra':
                st.markdown(f'<div class="datos-auto">🚗 <b>Vehículo:</b> {parada.get("vehiculo", "S/D")}<br>🏷️ <b>Serie (VIN):</b> {parada.get("serie", "S/D")}</div>', unsafe_allow_html=True)
                st.markdown(f"**🛒 Piezas a Recoger (Compra) ({len(parada['piezas'])}):**")
                for p in parada['piezas']: st.markdown(f"- {p['desc']}")

            elif parada['tipo'] == 'cotizacion':
                st.markdown(f'<div class="datos-auto">🚗 <b>Vehículo:</b> {parada.get("vehiculo", "S/D")}<br>🏷️ <b>Serie (VIN):</b> {parada.get("serie", "S/D")}</div>', unsafe_allow_html=True)
                st.markdown(f"**🔎 Piezas a Cotizar ({len(parada['piezas'])}):**")
                for p in parada['piezas']: st.markdown(f"- {p['desc']}")
                
            # --- BOTONES Y GPS ---
            st.markdown("<br>", unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                query_str = f"{parada['lugar']} {parada['direccion']}".replace(' ', '+')
                st.link_button("🧭 Navegar", f"https://www.google.com/maps/search/?api=1&query={query_str}", use_container_width=True)
                
            with col2:
                texto_btn = "✅ Check-In" if parada['tipo'] == 'entrega' else "🔄 Check-In"
                if st.button(texto_btn, key=f"btn_check_{parada['id']}", type="primary", use_container_width=True):
                    st.session_state['parada_activa'] = parada['id']

            if st.session_state.get('parada_activa') == parada['id']:
                st.info("👇 Presiona el botón para capturar GPS y confirmar.")
                ubicacion = streamlit_geolocation()
                
                if ubicacion and ubicacion.get('latitude'):
                    lat = ubicacion['latitude']
                    lon = ubicacion['longitude']
                    st.success(f"📍 Ubicación capturada.")
                    
                    if st.button("Confirmar Operación", key=f"save_{parada['id']}", use_container_width=True):
                        with st.spinner("Subiendo datos a la nube..."):
                            try:
                                doc = init_connection()
                                ws_rutas = doc.worksheet("BD_RUTAS")
                                datos = ws_rutas.get_all_values()
                                fila_encontrada = next((idx + 1 for idx, r in enumerate(datos) if r[0] == parada['id']), None)
                                
                                if fila_encontrada:
                                    ws_rutas.update_cell(fila_encontrada, 10, "Completado")
                                    ws_rutas.update_cell(fila_encontrada, 11, str(lat))
                                    ws_rutas.update_cell(fila_encontrada, 12, str(lon))
                                    st.success(f"¡Estatus actualizado en la nube! ✅")
                                    st.session_state['parada_activa'] = None
                                    time.sleep(1.5)
                                    cargar_rutas_nube()
                                    st.rerun()
                            except Exception as e: st.error(f"Error actualizando sistema: {e}")
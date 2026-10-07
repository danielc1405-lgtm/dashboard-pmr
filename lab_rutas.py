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
# 1. SISTEMA DE LOGIN (REAL) Y ESTILOS CSS
# ==========================================
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

# Estilos CSS
st.markdown("""
    <style>
    /* Agrandar enormemente los nombres de los destinos en el expander */
    div[data-testid="stExpander"] details summary p {
        font-size: 1.5rem !important;
        font-weight: 800 !important;
        color: #FFFFFF !important;
        line-height: 1.3 !important;
        padding-top: 5px !important;
        padding-bottom: 5px !important;
    }
    /* Homologar tamaños y alineación vertical para botones */
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
    </style>
""", unsafe_allow_html=True)

# Pantalla de Login si no está autenticado
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
                else:
                    st.error("❌ Usuario o contraseña incorrectos.")
            except Exception as e:
                st.error(f"Error al conectar con la base de usuarios: {e}")
    st.stop()

# ==========================================
# 2. MOTOR DE DESCARGA DESDE LA NUBE
# ==========================================
def cargar_rutas_nube():
    try:
        doc = init_connection()
        ws_rutas = doc.worksheet("BD_RUTAS")
        datos = ws_rutas.get_all_values()
        
        if len(datos) > 1:
            headers = [str(h).strip() for h in datos[0]]
            df = pd.DataFrame(datos[1:], columns=headers)
            
            # Filtrar solo pendientes
            df_pendientes = df[df['Estatus_App'].astype(str).str.upper() == 'PENDIENTE'].copy()
            
            rutas_descargadas = []
            for _, row in df_pendientes.iterrows():
                
                # Transformar el string de piezas "Faro Derecho|Moldura" en una lista de diccionarios
                texto_piezas = str(row.get('Piezas', 'Pieza general'))
                lista_piezas = []
                for p in texto_piezas.split("|"):
                    if p.strip(): lista_piezas.append({"desc": p.strip(), "np": ""})
                
                # Transformar Siniestros
                texto_siniestros = str(row.get('Siniestros', ''))
                lista_siniestros = [s.strip() for s in texto_siniestros.split(",") if s.strip()]
                
                parada = {
                    "id": str(row.get('ID_Ruta', '')),
                    "tipo": str(row.get('Tipo_Operacion', 'entrega')).lower(),
                    "lugar": str(row.get('Lugar', 'S/D')),
                    "direccion": str(row.get('Direccion', 'S/D')),
                    "vehiculo": str(row.get('Vehiculo', '')),
                    "serie": str(row.get('VIN', '')),
                    "piezas": lista_piezas,
                    "siniestros": lista_siniestros
                }
                rutas_descargadas.append(parada)
            
            st.session_state['ruta_hoy'] = rutas_descargadas
            return True
    except Exception as e:
        st.error(f"Error conectando a BD_RUTAS: {e}")
        return False
    return False

# Inicializar vacío si no se ha cargado
if 'ruta_hoy' not in st.session_state:
    st.session_state['ruta_hoy'] = []

# ==========================================
# 3. ENCABEZADO Y SINCRONIZACIÓN
# ==========================================
st.title("🚚 Mi Ruta de Hoy")
st.caption(f"👤 Operador: **{st.session_state['usuario_actual']}**")

if st.button("🔄 Sincronizar (Descargar Ruta)", use_container_width=True, type="primary"):
    with st.spinner("Descargando asignaciones..."):
        if cargar_rutas_nube():
            st.toast("Ruta actualizada exitosamente", icon="☁️")
            
st.markdown("---")

# ==========================================
# 4. RENDERIZADO DE TARJETAS (INFO DINÁMICA)
# ==========================================
if not st.session_state['ruta_hoy']:
    st.info("👋 ¡Todo limpio! No tienes destinos pendientes. Presiona 'Sincronizar' para revisar si hay nuevas asignaciones.")
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
        
        # Titulo y color dependiendo del tipo
        if parada['tipo'] == 'entrega':
            icono = "🟢"
        elif parada['tipo'] == 'recoleccion':
            icono = "🟠"
        else: # Cotizacion
            icono = "🔵"
            
        titulo_tarjeta = f"{icono} #{i+1} - {parada['lugar']}"
        
        with st.expander(titulo_tarjeta, expanded=False):
            
            # Selector de Orden
            opciones_orden = [f"{idx + 1} - {r['lugar']}" for idx, r in enumerate(st.session_state['ruta_hoy'])]
            st.selectbox(
                "Mover al lugar:", 
                options=opciones_orden,
                index=i,
                key=f"pos_{parada['id']}",
                on_change=cambiar_posicion_nombre,
                args=(i, f"pos_{parada['id']}")
            )
            
            st.markdown("---")
            st.caption(f"📍 **Dirección:** {parada['direccion']}")
            
            # -----------------------------------------------------------
            # RENDERIZADO ESPECÍFICO SEGÚN TIPO DE VIAJE
            # -----------------------------------------------------------
            if parada['tipo'] == 'entrega':
                # FORMATO DE ENTREGA
                st.markdown(f"**Siniestro / Pedido:** {', '.join(parada['siniestros'])}")
                st.markdown(f"""
                <div class="datos-auto">
                    🚗 <b>Vehículo:</b> {parada.get('vehiculo', 'S/D')}
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"**📦 Piezas a Entregar ({len(parada['piezas'])}):**")
                for p in parada['piezas']: st.markdown(f"- {p['desc']}")

            elif parada['tipo'] == 'recoleccion':
                # FORMATO DE COMPRAS / RECOLECCIÓN
                st.markdown(f"""
                <div class="datos-auto">
                    🚗 <b>Vehículo:</b> {parada.get('vehiculo', 'S/D')}<br>
                    🏷️ <b>Serie (VIN):</b> {parada.get('serie', 'S/D')}
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"**↩️ Piezas a Recoger ({len(parada['piezas'])}):**")
                for p in parada['piezas']: 
                    np_str = f" *(NP: {p['np']})*" if p.get('np') else ""
                    st.markdown(f"- {p['desc']}{np_str}")

            else:
                # FORMATO DE COTIZACIÓN
                st.markdown(f"""
                <div class="datos-auto">
                    🚗 <b>Vehículo:</b> {parada.get('vehiculo', 'S/D')}<br>
                    🏷️ <b>Serie (VIN):</b> {parada.get('serie', 'S/D')}
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"**🔎 Piezas / Número de Parte ({len(parada['piezas'])}):**")
                for p in parada['piezas']: 
                    np_str = f" *(NP: {p['np']})*" if p.get('np') else ""
                    st.markdown(f"- {p['desc']}{np_str}")
            # -----------------------------------------------------------

            st.markdown("<br>", unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            
            with col1:
                # FIX MAPAS: Busca la combinación del Lugar + Dirección exacta
                query_str = f"{parada['lugar']} {parada['direccion']}".replace(' ', '+')
                url_maps = f"https://www.google.com/maps/search/?api=1&query={query_str}"
                st.link_button("🧭 Navegar", url_maps, use_container_width=True)
                
            with col2:
                texto_btn = "✅ Check-In" if parada['tipo'] == 'entrega' else "🔄 Check-In"
                if st.button(texto_btn, key=f"btn_check_{parada['id']}", type="primary", use_container_width=True):
                    st.session_state[f'check_{parada["id"]}'] = True

            if st.session_state.get(f'check_{parada["id"]}', False):
                st.info("👇 Presiona el botón para capturar GPS y confirmar.")
                ubicacion = streamlit_geolocation(key=f"geo_{parada['id']}")
                
                if ubicacion and ubicacion.get('latitude'):
                    lat = ubicacion['latitude']
                    lon = ubicacion['longitude']
                    st.success(f"📍 Ubicación capturada.")
                    st.markdown(f"[🗺️ Ver en Mapa para Auditoría](https://www.google.com/maps?q={lat},{lon})")
                    
                    if st.button("Confirmar Operación", key=f"save_{parada['id']}", use_container_width=True):
                        with st.spinner("Subiendo datos a la nube..."):
                            try:
                                doc = init_connection()
                                ws_rutas = doc.worksheet("BD_RUTAS")
                                datos = ws_rutas.get_all_values()
                                
                                id_buscado = parada['id']
                                fila_encontrada = None
                                
                                for row_idx, row_data in enumerate(datos):
                                    if row_data[0] == id_buscado:
                                        fila_encontrada = row_idx + 1
                                        break
                                
                                if fila_encontrada:
                                    ws_rutas.update_cell(fila_encontrada, 10, "Completado")
                                    ws_rutas.update_cell(fila_encontrada, 11, str(lat))
                                    ws_rutas.update_cell(fila_encontrada, 12, str(lon))
                                    
                                    st.success(f"¡Estatus de {parada['lugar']} actualizado en la nube! ✅")
                                    time.sleep(1.5)
                                    cargar_rutas_nube()
                                    st.rerun()
                                else:
                                    st.error("Error: No se encontró este folio en la base de datos.")
                            except Exception as e:
                                st.error(f"Error actualizando sistema: {e}")
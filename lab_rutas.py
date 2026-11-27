# ==========================================
# 0. CONFIGURACIÓN, IMPORTS Y CONEXIÓN
# ==========================================
import streamlit as st
import pandas as pd
import gspread
import json
import re
import base64
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

@st.cache_data(ttl=300)
def cargar_fotos_nube():
    """Lee las imágenes/QR de BD_CHAT_IMAGENES para mostrarlas en la ruta del operador."""
    mapa_fotos = {}
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
                        mapa_fotos[id_f] = b64_full
    except Exception:
        pass
    return mapa_fotos

# ==========================================
# 1. SISTEMA DE LOGIN Y ESTILOS CSS
# ==========================================
if 'autenticado' not in st.session_state:
    if 'usr' in st.query_params:
        st.session_state['autenticado'] = True
        st.session_state['usuario_actual'] = st.query_params['usr']
    else:
        st.session_state['autenticado'] = False

st.markdown("""
    <style>
    div[data-testid="stExpander"] details summary p {
        font-size: 1.45rem !important;
        font-weight: 800 !important;
        color: #FFFFFF !important;
        line-height: 1.3 !important;
        padding-top: 4px !important;
        padding-bottom: 4px !important;
    }
    .stButton>button, .stLinkButton>a { 
        width: 100% !important; 
        height: 52px !important; 
        font-size: 16px !important; 
        font-weight: bold !important; 
        border-radius: 8px !important; 
        display: flex !important; 
        align-items: center !important; 
        justify-content: center !important;
        text-decoration: none !important;
        margin: 0px !important;
    }
    .datos-auto { background-color: #2D2D2D; padding: 10px 12px; border-radius: 8px; margin-bottom: 10px; font-size: 14px; color: #FFF; border-left: 4px solid #F63366; line-height: 1.45;}
    .nota-operador { background-color: #3b2a00; border-left: 5px solid #FFD700; padding: 10px 12px; margin-top: 6px; margin-bottom: 10px; border-radius: 5px; color: #FFF; font-size: 15px; line-height: 1.35;}
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
                    nombre_usuario = match.iloc[0]['Nombre Completo']
                    st.session_state['autenticado'] = True
                    st.session_state['usuario_actual'] = nombre_usuario
                    st.query_params['usr'] = nombre_usuario
                    st.rerun()
                else:
                    st.error("❌ Usuario o contraseña incorrectos.")
            except Exception as e:
                st.error(f"Error al conectar con la base de usuarios: {e}")
    st.stop()

# ==========================================
# 2. MOTOR DE DESCARGA Y LIMPIEZA DE TEXTOS
# ==========================================
def formatear_vin(vin):
    v = str(vin).replace(" ", "").upper()
    if not v or v in ['NAN', 'S/D', 'NONE']:
        return "S/D"
    return " ".join([v[i:i+4] for i in range(0, len(v), 4)])

def limpiar_vehiculo(veh_str, vin_raw=""):
    """Elimina palabras consecutivas duplicadas (ej. VOLKSWAGEN VOLKSWAGEN) y el VIN repetido."""
    v = str(veh_str).strip()
    if not v or v.upper() in ['NAN', 'NONE', 'S/D']:
        return "S/D"
    vin_limpio = str(vin_raw).replace(" ", "").upper()
    partes = [p.strip() for p in v.split("|") if p.strip()]
    partes_limpias = []
    for p in partes:
        p_sin_esp = p.replace(" ", "").upper()
        # Omitir segmento si coincide con el VIN o tiene formato de VIN (17 caracteres alfanuméricos)
        if vin_limpio and vin_limpio not in ['NAN', 'S/D', 'NONE'] and p_sin_esp == vin_limpio:
            continue
        if len(p_sin_esp) == 17 and p_sin_esp.isalnum() and any(c.isdigit() for c in p_sin_esp) and any(c.isalpha() for c in p_sin_esp):
            continue
        # Quitar palabras consecutivas duplicadas (ej. VOLKSWAGEN VOLKSWAGEN -> VOLKSWAGEN)
        p = re.sub(r'\b(\w+)(\s+\1\b)+', r'\1', p, flags=re.IGNORECASE)
        partes_limpias.append(p)
    return " | ".join(partes_limpias) if partes_limpias else v

def cargar_rutas_nube():
    try:
        doc = init_connection()
        ws_rutas = doc.worksheet("BD_RUTAS")
        datos = ws_rutas.get_all_values()
        
        if len(datos) > 1:
            headers = [str(h).strip().upper() for h in datos[0]]
            df = pd.DataFrame(datos[1:], columns=headers)
            
            col_estatus = next((c for c in df.columns if 'ESTATUS' in c), None)
            col_id_ruta = next((c for c in df.columns if 'ID_RUTA' in c), None)
            col_piezas = next((c for c in df.columns if 'PIEZA' in c), None)
            col_siniestros = next((c for c in df.columns if 'SINIESTRO' in c), None)
            col_notas = next((c for c in df.columns if 'NOTA' in c), None)
            
            if not col_estatus or not col_id_ruta:
                st.error("Error: Faltan columnas clave (ID_Ruta o Estatus) en BD_RUTAS.")
                return False

            tz_mx = datetime.timezone(datetime.timedelta(hours=-6))
            hoy_str_r = datetime.datetime.now(tz_mx).strftime("%d/%m/%Y")
            col_fecha = next((c for c in df.columns if 'FECHA' in c), None)

            df_pendientes = df[df[col_estatus].astype(str).str.strip().str.upper() == 'PENDIENTE'].copy()
            
            if col_fecha:
                df_completadas = df[(df[col_estatus].astype(str).str.strip().str.upper() == 'COMPLETADO') & (df[col_fecha].astype(str).str.contains(hoy_str_r, na=False))].copy()
            else:
                df_completadas = df[df[col_estatus].astype(str).str.strip().str.upper() == 'COMPLETADO'].tail(15).copy()
            
            def armar_diccionario_rutas(df_sub):
                r_dict = {}
                for _, row in df_sub.iterrows():
                    id_ruta = str(row.get(col_id_ruta, ''))
                    pieza_actual = str(row.get(col_piezas, '')) if col_piezas else ''
                    sin_actual = str(row.get(col_siniestros, '')) if col_siniestros else ''
                    vin_raw = str(row.get('VIN', ''))
                    
                    if id_ruta not in r_dict:
                        r_dict[id_ruta] = {
                            "id": id_ruta,
                            "tipo": str(row.get('TIPO_OPERACION', 'entrega')).strip().lower(),
                            "lugar": str(row.get('LUGAR', 'S/D')),
                            "direccion": str(row.get('DIRECCION', 'S/D')),
                            "vehiculo": limpiar_vehiculo(row.get('VEHICULO', 'S/D'), vin_raw),
                            "serie": formatear_vin(vin_raw),
                            "piezas": [{"desc": pieza_actual, "np": ""}] if pieza_actual and pieza_actual not in ['S/D', ''] else [],
                            "siniestros": [sin_actual] if sin_actual and sin_actual not in ['S/D', ''] else [],
                            "notas": str(row.get(col_notas, '')) if col_notas else ""
                        }
                    else:
                        if pieza_actual and pieza_actual not in ['S/D', '']: 
                            r_dict[id_ruta]["piezas"].append({"desc": pieza_actual, "np": ""})
                        if sin_actual and sin_actual not in ['S/D', ''] and sin_actual not in r_dict[id_ruta]["siniestros"]:
                            r_dict[id_ruta]["siniestros"].append(sin_actual)
                        nota_fila = str(row.get(col_notas, '')) if col_notas else ""
                        for tag_extra in re.findall(r'\[FOTO:[A-Za-z0-9]+\]', nota_fila, flags=re.IGNORECASE):
                            if tag_extra.upper() not in r_dict[id_ruta]["notas"].upper():
                                r_dict[id_ruta]["notas"] = f"{r_dict[id_ruta]['notas']} {tag_extra}".strip()
                return list(r_dict.values())
            
            cargar_fotos_nube.clear()
            st.session_state['ruta_hoy'] = armar_diccionario_rutas(df_pendientes)
            st.session_state['ruta_completadas_hoy'] = armar_diccionario_rutas(df_completadas)
            return True
    except Exception as e:
        st.error(f"Error conectando a BD_RUTAS: {e}")
        return False
    return False

if 'ruta_hoy' not in st.session_state:
    st.session_state['ruta_hoy'] = []

# ==========================================
# 3. ENCABEZADO Y SINCRONIZACIÓN
# ==========================================
st.title("🚚 Mi Ruta de Hoy")
st.caption(f"👤 Operador: **{st.session_state['usuario_actual']}**")

if st.button("🔄 Sincronizar (Descargar Ruta)", use_container_width=True, type="primary"):
    cargar_fotos_nube.clear()
    with st.spinner("Descargando asignaciones..."):
        if cargar_rutas_nube():
            st.toast("Ruta actualizada exitosamente", icon="☁️")
            
st.markdown("---")

# ==========================================
# 4. RENDERIZADO DE TARJETAS
# ==========================================
if not st.session_state['ruta_hoy']:
    st.info("👋 ¡Todo limpio! No tienes destinos pendientes.")
else:
    # Cargar fotos/QR solo si alguna nota tiene [FOTO:...]
    hay_fotos = any("[FOTO:" in str(p.get("notas", "")).upper() for p in st.session_state['ruta_hoy'])
    mapa_fotos_ruta = cargar_fotos_nube() if hay_fotos else {}

    def cambiar_posicion_nombre(old_idx, key_selectbox):
        seleccion = st.session_state[key_selectbox]
        new_idx = int(seleccion.split(" - ")[0]) - 1
        if old_idx != new_idx:
            ruta = st.session_state['ruta_hoy']
            item = ruta.pop(old_idx)
            ruta.insert(new_idx, item)
            st.session_state['ruta_hoy'] = ruta

    for i, parada in enumerate(st.session_state['ruta_hoy']):
        tipo_p = parada['tipo']
        
        # --- DEFINICIÓN DE ICONOS ---
        if tipo_p == 'entrega': icono = "📦"
        elif tipo_p == 'recoleccion': icono = "↩️"
        elif tipo_p == 'compra': icono = "🛒"
        elif tipo_p == 'cotizacion': icono = "🔍"
        elif tipo_p == 'pago': icono = "💵"
        elif 'reparacion' in tipo_p: icono = "🔧"
        elif 'revision' in tipo_p: icono = "🧐"
        elif 'paqueteria' in tipo_p: icono = "📬"
        else: icono = "🔵"
            
        titulo_tarjeta = f"{icono} #{i+1} - {parada['lugar']}"
        
        with st.expander(titulo_tarjeta, expanded=False):
            opciones_orden = [f"{idx + 1} - {r['lugar']}" for idx, r in enumerate(st.session_state['ruta_hoy'])]
            st.selectbox("Mover al lugar:", options=opciones_orden, index=i, key=f"pos_{parada['id']}", on_change=cambiar_posicion_nombre, args=(i, f"pos_{parada['id']}"))
            
            # Extraer etiquetas [FOTO:ID] únicas de las notas para mostrar QR / imágenes
            notas_raw = str(parada.get('notas', '')).strip()
            ids_fotos = list(dict.fromkeys([f.upper() for f in re.findall(r'\[FOTO:([A-Za-z0-9]+)\]', notas_raw, flags=re.IGNORECASE)]))
            notas_limpias = re.sub(r'\[FOTO:[A-Za-z0-9]+\]', '', notas_raw, flags=re.IGNORECASE).strip()

            if notas_limpias:
                st.markdown(f'<div class="nota-operador">⚠️ {notas_limpias}</div>', unsafe_allow_html=True)

            # Mostrar QR / Fotos adjuntas directamente en la tarjeta
            total_f = len(ids_fotos)
            for idx_f, fid in enumerate(ids_fotos, start=1):
                src_b64 = mapa_fotos_ruta.get(fid, "")
                if src_b64:
                    try:
                        b64_puro = src_b64.split(",", 1)[1] if "," in src_b64 else src_b64
                        etq_f = f"📷 Foto {idx_f} de {total_f} ({fid})" if total_f > 1 else f"📷 Código / Foto ({fid})"
                        st.image(base64.b64decode(b64_puro), caption=etq_f, use_container_width=True)
                    except Exception:
                        st.caption(f"⚠️ No se pudo mostrar la imagen ({fid}).")
                else:
                    st.caption(f"⚠️ Imagen ({fid}) no disponible o expirada (>5 días).")

            veh_txt = parada.get("vehiculo", "S/D")
            vin_txt = parada.get("serie", "S/D")
            sin_txt = ", ".join(parada['siniestros']) if parada['siniestros'] else ""

            if tipo_p == 'entrega':
                if sin_txt: st.markdown(f"**Siniestro / Pedido:** {sin_txt}")
                st.markdown(f'<div class="datos-auto">🚗 {veh_txt}</div>', unsafe_allow_html=True)
                st.markdown(f"**📦 Piezas a Entregar ({len(parada['piezas'])}):**")
                for p in parada['piezas']: st.markdown(f"- {p['desc']}")

            elif tipo_p == 'recoleccion':
                if sin_txt: st.markdown(f"**Siniestro / Pedido:** {sin_txt}")
                st.markdown(f'<div class="datos-auto">🚗 {veh_txt}</div>', unsafe_allow_html=True)
                st.markdown(f"**↩️ Piezas a Recolectar (Devolución) ({len(parada['piezas'])}):**")
                for p in parada['piezas']: st.markdown(f"- {p['desc']}")

            elif tipo_p == 'compra':
                st.markdown(f'<div class="datos-auto">🚗 {veh_txt}<br>🏷️ <b>Serie (VIN):</b> {vin_txt}</div>', unsafe_allow_html=True)
                st.markdown(f"**🛒 Piezas a Recoger (Compra) ({len(parada['piezas'])}):**")
                for p in parada['piezas']: st.markdown(f"- {p['desc']}")

            elif tipo_p == 'cotizacion':
                st.markdown(f'<div class="datos-auto">🚗 {veh_txt}<br>🏷️ <b>Serie (VIN):</b> {vin_txt}</div>', unsafe_allow_html=True)
                st.markdown(f"**🔎 Piezas a Cotizar ({len(parada['piezas'])}):**")
                for p in parada['piezas']: st.markdown(f"- {p['desc']}")

            elif tipo_p == 'pago':
                st.markdown(f'<div class="datos-auto">🚗 {veh_txt}<br>🏷️ <b>Serie (VIN):</b> {vin_txt}</div>', unsafe_allow_html=True)
                st.markdown(f"**💵 Pago a Proveedor ({len(parada['piezas'])} pza):**")
                for p in parada['piezas']: st.markdown(f"- {p['desc']}")

            else:
                # Vueltas eventuales (Reparación, Revisión, Paquetería, etc.)
                if sin_txt and sin_txt.upper() != "N/A":
                    st.markdown(f"**Siniestro / Pedido:** {sin_txt}")
                st.markdown(f'<div class="datos-auto">🚗 {veh_txt}<br>🏷️ <b>Serie (VIN):</b> {vin_txt}</div>', unsafe_allow_html=True)
                if parada['piezas']:
                    st.markdown(f"**{icono} Piezas ({len(parada['piezas'])}):**")
                    for p in parada['piezas']: st.markdown(f"- {p['desc']}")

            st.markdown("<br>", unsafe_allow_html=True)
            
            # --- CHECK-IN RÁPIDO Y DIRECTO ---
            col1, col2 = st.columns(2)
            with col1:
                query_str = f"{parada['lugar']} {parada['direccion']}".replace(' ', '+')
                st.link_button("🧭 Navegar", f"https://www.google.com/maps/search/?api=1&query={query_str}", use_container_width=True)
            with col2:
                if tipo_p == 'entrega': 
                    texto_btn = f"{icono} Entregado"
                elif tipo_p in ['compra', 'recoleccion'] or 'recoleccion' in tipo_p: 
                    texto_btn = f"{icono} Recolectado"
                elif tipo_p == 'pago': 
                    texto_btn = f"{icono} Pago Realizado"
                else: 
                    texto_btn = f"{icono} Visita Lista"
                
                if st.button(texto_btn, key=f"save_{parada['id']}", type="primary", use_container_width=True):
                    with st.spinner("Registrando operación..."):
                        try:
                            doc = init_connection()
                            ws_rutas = doc.worksheet("BD_RUTAS")
                            datos = ws_rutas.get_all_values()
                            
                            filas_a_actualizar = [idx + 1 for idx, r in enumerate(datos) if r[0] == parada['id']]
                            if filas_a_actualizar:
                                celdas_cambio = [gspread.Cell(row=fila_idx, col=11, value="Completado") for fila_idx in filas_a_actualizar]
                                ws_rutas.update_cells(celdas_cambio, value_input_option='USER_ENTERED')
                                st.success("¡Listo! ✅")
                                time.sleep(1)
                                cargar_rutas_nube()
                                st.rerun()
                            else:
                                st.error("Error: No se encontró este folio en la base.")
                        except Exception as e:
                            st.error(f"Error actualizando sistema: {e}")

# ==========================================
# 5. SECCIÓN PARA REVIVIR VISITAS COMPLETADAS POR ERROR
# ==========================================
if st.session_state.get('ruta_completadas_hoy'):
    st.markdown("---")
    with st.expander(f"✅ Visitas Completadas Hoy ({len(st.session_state['ruta_completadas_hoy'])}) — ¿Marcaste una por error?", expanded=False):
        st.caption("Si marcaste una visita por accidente, presiona **♻️ Revivir a mi Ruta** para regresarla a tu lista activa.")
        for comp in st.session_state['ruta_completadas_hoy']:
            st.markdown(f"**{comp['lugar']}** ({comp['tipo'].upper()} - {len(comp['piezas'])} pza(s))")
            if st.button(f"♻️ Revivir: {comp['lugar']}", key=f"rev_{comp['id']}", use_container_width=True):
                with st.spinner("Regresando visita a tu ruta activa..."):
                    try:
                        doc = init_connection()
                        ws_rutas = doc.worksheet("BD_RUTAS")
                        datos = ws_rutas.get_all_values()
                        filas_rev = [idx + 1 for idx, r in enumerate(datos) if r[0] == comp['id']]
                        if filas_rev:
                            celdas_rev = [gspread.Cell(row=f_idx, col=11, value="PENDIENTE") for f_idx in filas_rev]
                            ws_rutas.update_cells(celdas_rev, value_input_option='USER_ENTERED')
                            st.success("¡Visita restaurada a tu ruta! 🚚")
                            time.sleep(0.8)
                            cargar_rutas_nube()
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error al revivir: {e}")
            st.markdown("---")
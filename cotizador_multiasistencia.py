# =========================================================================
    # PESTAÑA 4: MESA DE COTIZACIONES (IA) - MULTIASISTENCIA
    # =========================================================================
    with tab_cotizador:
        st.markdown("#### ⚡ Mesa de Decisión y Cotizador Automático (Multiasistencia)")
        st.caption("1️⃣ Extrae cotizaciones activas • 2️⃣ Captura tu Precio Libre o Costo Base, marca **✅ Validar** y presiona **🚀 Guardar y Enviar al Portal** (un solo paso).")

        col_btn_ext, col_btn_env, col_modo_cot = st.columns([1.4, 1.6, 1.0], vertical_alignment="center")
        with col_modo_cot:
            modo_bot_cot = st.radio("Vista Chrome:", ["Oculto (Rápido)", "Visual (PC Local)"], horizontal=True, key="rad_modo_cot")
        arg_vis_cot = "--oculto" if "Oculto" in modo_bot_cot else "--visual"

        btn_run_ext = col_btn_ext.button("🔎 1. Extraer Cotizaciones y Buscar Precios", type="primary", use_container_width=True)
        btn_run_env = col_btn_env.button("🚀 2. Guardar Selección y Enviar Validadas al Portal (7 Días)", type="primary", use_container_width=True)

        with st.expander("🖥️ Ver Bitácora de Ejecución en Vivo del Robot Cotizador", expanded=False):
            consola_cot_vivo = st.empty()
            consola_cot_vivo.code(st.session_state.get('log_cotizador_ai', 'Esperando orden de ejecución...'))

        try:
            doc_cot = init_connection()
            ws_cot_ui = doc_cot.worksheet("BD_COTIZACIONES")
            datos_cot_ui = ws_cot_ui.get_all_values()
            df_cot_ui = pd.DataFrame(datos_cot_ui[1:], columns=[str(h).strip() for h in datos_cot_ui[0]]) if len(datos_cot_ui) > 1 else pd.DataFrame()
        except Exception:
            df_cot_ui = pd.DataFrame()

        if not df_cot_ui.empty and 'Estatus_Cotizacion' in df_cot_ui.columns:
            df_cot_ui['_GS_Row'] = df_cot_ui.index + 2
            # Eliminar duplicados visuales por Siniestro + Partida_Idx conservando el más reciente
            df_cot_ui = df_cot_ui.drop_duplicates(subset=['Siniestro', 'Partida_Idx'], keep='last').copy()

            df_pend_cot = df_cot_ui[df_cot_ui['Estatus_Cotizacion'].astype(str).str.upper() == 'PENDIENTE'].copy()
            df_hist_cot = df_cot_ui[df_cot_ui['Estatus_Cotizacion'].astype(str).str.upper() == 'ENVIADA PORTAL'].copy()

            if not df_pend_cot.empty:
                for col_num in ['Precio_Original', 'Precio_No_Original', 'Precio_Generica', 'Precio_Historial', 'Flete_Estimado', 'Costo_Base', 'Margen_Pct', 'Precio_Sugerido', 'Precio_Libre', 'Precio_Final_Enviar']:
                    if col_num in df_pend_cot.columns:
                        df_pend_cot[col_num] = pd.to_numeric(df_pend_cot[col_num].astype(str).str.replace('$', '').str.replace(',', ''), errors='coerce').fillna(0.0)

                df_pend_cot['Validar_Bool'] = df_pend_cot['Validar_Envio'].astype(str).str.upper().isin(['TRUE', 'SI', '1', 'VERDADERO'])

                # Construir etiqueta "B82548962 CHEVROLET CAVALIER 2019 AUTOPRIME"
                mapa_etiquetas_sin = {"Todos": "📋 Todos los Siniestros Pendientes"}
                for sin_k, grp_s in df_pend_cot.groupby('Siniestro', sort=False):
                    r0 = grp_s.iloc[0]
                    marca_s = str(r0.get('Marca', '')).strip()
                    veh_s = str(r0.get('Vehiculo', '')).strip()
                    if veh_s.upper().startswith(marca_s.upper()):
                        auto_str = veh_s
                    else:
                        auto_str = f"{marca_s} {veh_s}".strip()
                    ano_s = str(r0.get('Modelo_Ano', '')).strip()
                    tal_s = str(r0.get('Taller', '')).strip()
                    mapa_etiquetas_sin[sin_k] = f"{sin_k} {auto_str} {ano_s} {tal_s}".strip()

                siniestros_disp = list(mapa_etiquetas_sin.keys())
                sin_cot_sel = st.selectbox(
                    "🚗 Selecciona el Siniestro a revisar:",
                    options=siniestros_disp,
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

                cols_tabla_cot = [
                    c for c in [
                        'Siniestro', 'Partida_Idx', 'Cantidad', 'Descripcion_Portal',
                        'Precio_Original', 'Precio_No_Original', 'Precio_Generica', 'Precio_Historial',
                        'Flete_Estimado', 'Fuente_Seleccionada', 'Origen_Portal',
                        'Costo_Base', 'Margen_Pct', 'Precio_Sugerido', 'Precio_Libre',
                        'Codigo_Hub', 'Link_Referencia', 'Validar_Bool'
                    ] if c in df_pend_cot.columns
                ]

                ed_cot_df = st.data_editor(
                    df_pend_cot[cols_tabla_cot],
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        'Siniestro': st.column_config.TextColumn("Siniestro", disabled=True, width="small"),
                        'Partida_Idx': st.column_config.NumberColumn("#", disabled=True, width="small"),
                        'Cantidad': st.column_config.TextColumn("Cant", disabled=True, width="small"),
                        'Descripcion_Portal': st.column_config.TextColumn("Pieza", disabled=True, width="medium"),
                        'Precio_Original': st.column_config.NumberColumn("1. ORIGINAL", format="$ %.0f", disabled=True, width="small"),
                        'Precio_No_Original': st.column_config.NumberColumn("2. NO ORIG (Semi)", format="$ %.0f", disabled=True, width="small"),
                        'Precio_Generica': st.column_config.NumberColumn("3. GENÉRICA", format="$ %.0f", disabled=True, width="small"),
                        'Precio_Historial': st.column_config.NumberColumn("Hist. PMR", format="$ %.0f", disabled=True, width="small"),
                        'Flete_Estimado': st.column_config.NumberColumn("🚚 Flete", format="$ %.0f", width="small"),
                        'Fuente_Seleccionada': st.column_config.SelectboxColumn("Dónde Comprar", options=["ML", "EB", "INV", "LOC", "AGENCIA", "MAN"], width="small"),
                        'Origen_Portal': st.column_config.SelectboxColumn("Origen Portal", options=["ORIGINAL", "NO ORIGINAL", "SEMINUEVA"], width="small"),
                        'Costo_Base': st.column_config.NumberColumn("Costo Base", format="$ %.0f", width="small"),
                        'Margen_Pct': st.column_config.SelectboxColumn("% Utilidad", options=[15, 20, 25, 30, 35, 40, 45, 50, 60, 70, 80, 100], width="small"),
                        'Precio_Sugerido': st.column_config.NumberColumn("💡 Sugerido", format="$ %.0f", disabled=True, width="small"),
                        'Precio_Libre': st.column_config.NumberColumn("✍️ Precio Libre", format="$ %.0f", help="Si escribes un monto > 0 aquí, este se enviará al portal en lugar del sugerido.", width="small"),
                        'Codigo_Hub': st.column_config.TextColumn("Código Portal", width="small"),
                        'Link_Referencia': st.column_config.LinkColumn("🔗 Producto", display_text="Ver Producto", width="small"),
                        'Validar_Bool': st.column_config.CheckboxColumn("✅ Validar", default=False, width="small")
                    },
                    key="editor_mesa_cotizador"
                )

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

                        nuevo_sug = round((costo_b + flete_b) * (1.0 + margen_b / 100.0)) if costo_b > 0 else 0
                        precio_final_env = round(libre_b) if libre_b > 0 else nuevo_sug

                        cod_actual = str(fila_ed['Codigo_Hub']).strip().upper()
                        sufijo_num = re.findall(r'\d{3}$', cod_actual)
                        num_3 = sufijo_num[0] if sufijo_num else str(random.randint(100, 999))
                        nuevo_cod_hub = f"HUB{fuente_b}{num_3}"

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
                        ws_cot_ui.update_cells(celdas_cot_upd, value_input_option='USER_ENTERED')

                if st.button("💾 Solo Guardar Borrador / Recalcular Sugeridos", key="btn_save_mesa_cot"):
                    with st.spinner("Guardando borrador en BD_COTIZACIONES..."):
                        guardar_cambios_mesa_en_sheet()
                        st.success("✅ Borrador guardado y precios recalculados.")
                        time.sleep(0.5)
                        st.rerun()

                # Si presionó el botón 2 (Enviar al Portal), primero guardamos automáticamente la tabla en Sheets
                if btn_run_env:
                    with st.spinner("Guardando tu selección antes de abrir el portal..."):
                        guardar_cambios_mesa_en_sheet()
            else:
                st.info("No hay cotizaciones pendientes en la mesa. Presiona **🔎 1. Extraer Cotizaciones y Buscar Precios** para traer las del portal.")

            if not df_hist_cot.empty:
                with st.expander(f"📊 Historial de Cotizaciones Enviadas al Portal ({len(df_hist_cot)} partidas)", expanded=False):
                    st.dataframe(df_hist_cot.drop(columns=['_GS_Row'], errors='ignore'), hide_index=True, use_container_width=True)
        else:
            st.info("Aún no existen registros en `BD_COTIZACIONES`. Presiona **🔎 1. Extraer Cotizaciones y Buscar Precios** para inicializar la hoja automáticamente.")

        # Ejecución en vivo del robot (Extracción o Envío)
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
                    st.cache_data.clear()
                    st.rerun()
                finally:
                    if os.path.exists("credentials.json"):
                        os.remove("credentials.json")

        # Mostrar Capturas de Evidencia de Chrome si existen
        if os.path.exists("evidencia_antes_grabar.png") or os.path.exists("evidencia_despues_grabar.png"):
            with st.expander("📸 Ver Evidencia Visual de Chrome en el Portal (Antes y Después de Grabar)", expanded=True):
                c_ev1, c_ev2 = st.columns(2)
                if os.path.exists("evidencia_antes_grabar.png"):
                    c_ev1.image("evidencia_antes_grabar.png", caption="1. Pliego llenado antes de presionar Grabar")
                if os.path.exists("evidencia_despues_grabar.png"):
                    c_ev2.image("evidencia_despues_grabar.png", caption="2. Respuesta del portal tras presionar Grabar")
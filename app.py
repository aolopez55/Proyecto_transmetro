import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

# Configuración de la página Web
st.set_page_config(
    page_title="Transmetro - Sistema de Control Operativo",
    page_icon="🚌",
    layout="wide"
)

# Estilos CSS
st.markdown("""
    <style>
    .main-header { font-size: 26px; font-weight: bold; color: #1F4E78; }
    .station-card {
        background-color: #F8F9FA;
        border-left: 5px solid #1F4E78;
        padding: 12px;
        margin-bottom: 10px;
        border-radius: 6px;
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# CONEXIÓN A LA BASE DE DATOS POSTGRESQL (NEON.TECH)
# -----------------------------------------------------------------------------
@st.cache_resource
def get_db_engine():
    # Si existen secretos configurados en Streamlit Cloud, los usa; de lo contrario, usa las credenciales por defecto
    if "postgres" in st.secrets:
        cfg = st.secrets["postgres"]
        db_url = f"postgresql+psycopg2://{cfg['user']}:{cfg['password']}@{cfg['host']}:{cfg['port']}/{cfg['database']}?sslmode=require"
    else:
        # Tus credenciales directas de Neon
        user = "transmetro_db_owner"
        password = "npg_q9AZrBWy8XSN"  # ⚠️ Coloca aquí tu contraseña de Neon
        host = "ep-tiny-cloud-b4h9eg0r-pooler.c-6.us-east-2.aws.neon.tech"
        port = 5432
        db_name = "transmetro_db"
        db_url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db_name}?sslmode=require"
    
    return create_engine(db_url)

# Inicializar la variable engine global para SQLAlchemy
engine = get_db_engine()


# -----------------------------------------------------------------------------
# GESTIÓN DE SESIÓN Y LOGIN
# -----------------------------------------------------------------------------
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["user_info"] = None

def autenticar_usuario(username, password):
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT id_usuario, username, nombre_completo, rol 
                FROM usuario 
                WHERE username = :user AND password_hash = :pass AND activo = TRUE;
            """)
            result = conn.execute(query, {"user": username.strip(), "pass": password.strip()}).fetchone()
            if result:
                return {
                    "id_usuario": result[0],
                    "username": result[1],
                    "nombre": result[2],
                    "rol": result[3]
                }
            return None
    except Exception as e:
        st.error(f"Error al verificar credenciales: {e}")
        return None

# PANTALLA DE LOGIN
if not st.session_state["logged_in"]:
    col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
    with col_l2:
        st.markdown("<h2 style='text-align: center; color: #1F4E78;'>🚌 Sistema Transmetro</h2>", unsafe_allow_html=True)
        st.markdown("<h4 style='text-align: center;'>Inicio de Sesión Operativo</h4>", unsafe_allow_html=True)
        st.write("---")
        
        user_input = st.text_input("Usuario:")
        pass_input = st.text_input("Contraseña:", type="password")
        
        if st.button("Iniciar Sesión", use_container_width=True):
            user_data = autenticar_usuario(user_input, pass_input)
            if user_data:
                st.session_state["logged_in"] = True
                st.session_state["user_info"] = user_data
                st.success(f"Bienvenido, {user_data['nombre']}")
                st.rerun()
            else:
                st.error("⚠️ Usuario o contraseña incorrectos.")
        
        st.info("💡 **Credenciales de prueba:**\n- **Admin:** `admin` / `admin123`\n- **Operador:** `operador` / `operador123`\n- **Flota:** `flota` / `flota123`")
    st.stop()  # Detiene la ejecución si no ha iniciado sesión

# -----------------------------------------------------------------------------
# NAVEGACIÓN PRINCIPAL (USUARIO AUTENTICADO)
# -----------------------------------------------------------------------------
user_actual = st.session_state["user_info"]

st.sidebar.image("https://img.icons8.com/color/96/bus.png", width=70)
st.sidebar.title("Transmetro Control")
st.sidebar.markdown(f"👤 **Usuario:** {user_actual['nombre']}")
st.sidebar.markdown(f"🔑 **Rol:** `{user_actual['rol']}`")

if st.sidebar.button("🚪 Cerrar Sesión"):
    st.session_state["logged_in"] = False
    st.session_state["user_info"] = None
    st.rerun()

st.sidebar.write("---")

# Nombres exactos de las opciones
OPCION_LINEAS = "🗺️ Gestión de Líneas & Rutas"
OPCION_BUSES = "🚌 Flota de Buses & Pilotos"
OPCION_ESTACIONES = "🏢 Estaciones & Parqueos"
OPCION_GUARDIAS = "🛡️ Accesos & Guardias"
OPCION_OPERADOR = "🚨 Operador de Estación"

# Filtrar módulos según el ROL asignado al usuario
if user_actual["rol"] == "Administrador":
    modulos_disponibles = [OPCION_LINEAS, OPCION_BUSES, OPCION_ESTACIONES, OPCION_GUARDIAS, OPCION_OPERADOR]
elif user_actual["rol"] == "Operador":
    modulos_disponibles = [OPCION_OPERADOR, OPCION_ESTACIONES]
elif user_actual["rol"] == "Flota":
    modulos_disponibles = [OPCION_BUSES, OPCION_LINEAS]
else:
    modulos_disponibles = [OPCION_OPERADOR]

menu = st.sidebar.radio("Módulos Principales:", modulos_disponibles)

# -----------------------------------------------------------------------------
# MÓDULO 1: GESTIÓN DE LÍNEAS & RUTAS
# -----------------------------------------------------------------------------
if menu == OPCION_LINEAS:
    st.markdown('<p class="main-header">Gestión de Líneas y Esquema Visual de Paradas</p>', unsafe_allow_html=True)

    tab_ver, tab_crear_linea = st.tabs(["📌 Ver / Editar Línea y Paradas", "➕ Crear Nueva Línea"])

    with tab_ver:
        try:
            with engine.connect() as conn:
                lineas = pd.read_sql("SELECT id_linea, nombre_linea, color_identificador FROM linea ORDER BY nombre_linea;", conn)
        except Exception as e:
            st.error(f"Error de conexión con la base de datos: {e}")
            lineas = pd.DataFrame()

        if not lineas.empty:
            col_l1, col_l2 = st.columns([2, 1])
            with col_l1:
                linea_seleccionada = st.selectbox("Seleccionar Línea a Gestionar:", lineas["nombre_linea"])
                id_linea_sel = lineas[lineas["nombre_linea"] == linea_seleccionada]["id_linea"].values[0]
                color_lin = lineas[lineas["nombre_linea"] == linea_seleccionada]["color_identificador"].values[0]

            with engine.connect() as conn:
                query_ruta = text("""
                    SELECT le.orden_estacion, e.id_estacion, e.nombre as estacion, 
                           m.nombre as municipalidad, le.distancia_siguiente_km
                    FROM linea_estacion le
                    JOIN estacion e ON le.id_estacion = e.id_estacion
                    JOIN municipalidad m ON e.id_municipalidad = m.id_municipalidad
                    WHERE le.id_linea = :id_linea
                    ORDER BY le.orden_estacion;
                """)
                df_ruta = pd.read_sql(query_ruta, conn, params={"id_linea": int(id_linea_sel)})

            distancia_total = df_ruta["distancia_siguiente_km"].sum() if not df_ruta.empty else 0.0

            # Indicadores
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("Color Identificador", str(color_lin))
            col_m2.metric("Total Estaciones", len(df_ruta))
            col_m3.metric("Distancia Total Recorrido", f"{distancia_total:.2f} km")

            st.divider()

            # Esquema Visual
            st.subheader(f"🚏 Esquema Visual de Recorrido: {linea_seleccionada}")
            if not df_ruta.empty:
                total_paradas = len(df_ruta)
                for idx, row in df_ruta.iterrows():
                    num_parada = row['orden_estacion']
                    nombre_est = row['estacion']
                    muni = row['municipalidad']
                    dist_sig = row['distancia_siguiente_km']
                    
                    st.markdown(f"""
                        <div style="background-color: #FFFFFF; border-left: 8px solid #1F4E78; border-radius: 8px; padding: 12px 18px; box-shadow: 0 2px 4px rgba(0,0,0,0.08); margin-bottom: 5px;">
                            <span style="font-size: 18px; font-weight: bold; color: #1F4E78;">🛑 Parada #{num_parada}: {nombre_est}</span>
                            <span style="font-size: 13px; color: #6c757d; margin-left: 10px;">({muni})</span>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    if idx < total_paradas - 1:
                        st.markdown(f"""
                            <div style="border-left: 3px dashed #1F4E78; margin-left: 20px; padding-left: 15px; padding-top: 5px; padding-bottom: 5px; color: #28a745; font-weight: 500; font-size: 14px;">
                                ⬇️ <b>{dist_sig:.2f} km</b> hacia la siguiente estación
                            </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown("""
                            <div style="margin-left: 20px; padding-left: 15px; padding-top: 5px; color: #dc3545; font-weight: bold; font-size: 13px;">
                                🏁 <b>Estación Terminal de la Línea</b>
                            </div>
                        """, unsafe_allow_html=True)
            else:
                st.info("Esta línea aún no cuenta con estaciones asignadas.")

            st.divider()
            col_ag1, col_ag2 = st.columns(2)

            with col_ag1:
                st.subheader("➕ Agregar Parada a la Ruta")
                with engine.connect() as conn:
                    query_estaciones_disponibles = text("""
                        SELECT id_estacion, nombre FROM estacion 
                        WHERE id_estacion NOT IN (SELECT id_estacion FROM linea_estacion WHERE id_linea = :id_linea)
                        ORDER BY nombre;
                    """)
                    estaciones_disp = pd.read_sql(query_estaciones_disponibles, conn, params={"id_linea": int(id_linea_sel)})

                if not estaciones_disp.empty:
                    est_nueva = st.selectbox("Seleccionar Estación:", estaciones_disp["nombre"])
                    id_est_nueva = estaciones_disp[estaciones_disp["nombre"] == est_nueva]["id_estacion"].values[0]
                    orden_nuevo = len(df_ruta) + 1
                    
                    if len(df_ruta) == 0:
                        st.info("📌 Esta es la **primera estación** de la línea, no requiere ingresar distancia.")
                        dist_nueva = 0.0
                    else:
                        dist_nueva = st.number_input(f"Distancia desde la Estación #{len(df_ruta)} a esta estación (km):", min_value=0.1, value=1.5, step=0.1)

                    if st.button("Guardar Parada en la Ruta"):
                        try:
                            with engine.begin() as conn:
                                if len(df_ruta) > 0:
                                    ultima_estacion_id = df_ruta.iloc[-1]['id_estacion']
                                    conn.execute(text("UPDATE linea_estacion SET distancia_siguiente_km = :dist WHERE id_linea = :id_l AND id_estacion = :id_e;"),
                                                 {"dist": float(dist_nueva), "id_l": int(id_linea_sel), "id_e": int(ultima_estacion_id)})

                                conn.execute(text("INSERT INTO linea_estacion (id_linea, id_estacion, orden_estacion, distancia_siguiente_km) VALUES (:id_linea, :id_estacion, :orden, 0.0);"),
                                             {"id_linea": int(id_linea_sel), "id_estacion": int(id_est_nueva), "orden": int(orden_nuevo)})

                            st.success("✅ Estación agregada a la línea correctamente.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al agregar parada: {e}")
                else:
                    st.warning("⚠️ No hay más estaciones disponibles para asignar a esta línea.")

            with col_ag2:
                st.subheader("🚌 Asignar Bus a esta Línea")
                with engine.connect() as conn:
                    query_buses = text("""
                        SELECT b.id_bus, b.numero_unidad, p.nombres || ' ' || p.apellidos as piloto
                        FROM bus b JOIN piloto p ON p.id_bus_asociado = b.id_bus
                        WHERE b.id_linea IS NULL OR b.id_linea = :id_l;
                    """)
                    buses_disp = pd.read_sql(query_buses, conn, params={"id_l": int(id_linea_sel)})

                if not buses_disp.empty:
                    bus_sel = st.selectbox("Bus Disponible (Requiere Piloto):", buses_disp["numero_unidad"] + " - Piloto: " + buses_disp["piloto"])
                    id_bus_sel = buses_disp[buses_disp["numero_unidad"] == bus_sel.split(" - ")[0]]["id_bus"].values[0]

                    if st.button("Asignar Bus a la Línea"):
                        with engine.begin() as conn:
                            conn.execute(text("UPDATE bus SET id_linea = :id_l WHERE id_bus = :id_b;"),
                                         {"id_l": int(id_linea_sel), "id_b": int(id_bus_sel)})
                        st.success("Bus asignado a la línea.")
                        st.rerun()
                else:
                    st.warning("No hay buses disponibles con piloto asignado.")
        else:
            st.warning("⚠️ No existen líneas registradas en la base de datos.")

    with tab_crear_linea:
        st.subheader("➕ Registrar Nueva Línea de Transmetro")
        try:
            with engine.connect() as conn:
                munis = pd.read_sql("SELECT id_municipalidad, nombre FROM municipalidad ORDER BY nombre;", conn)
        except Exception:
            munis = pd.DataFrame()

        if not munis.empty:
            col_cl1, col_cl2 = st.columns(2)
            with col_cl1:
                nom_linea = st.text_input("Nombre de la Línea (ej. Línea 13):")
                color_linea = st.text_input("Color Identificador:", value="Verde")
            with col_cl2:
                muni_linea = st.selectbox("Municipalidad Administradora:", munis["nombre"])
                id_muni_linea = munis[munis["nombre"] == muni_linea]["id_municipalidad"].values[0]

            if st.button("Guardar Nueva Línea"):
                if nom_linea.strip():
                    try:
                        with engine.begin() as conn:
                            conn.execute(text("INSERT INTO linea (nombre_linea, color_identificador, id_municipalidad) VALUES (:nom, :col, :id_m);"),
                                         {"nom": nom_linea.strip(), "col": color_linea.strip(), "id_m": int(id_muni_linea)})
                        st.success(f"Línea '{nom_linea}' creada exitosamente.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al crear línea: {e}")

# -----------------------------------------------------------------------------
# MÓDULO 2: FLOTA DE BUSES & PILOTOS
# -----------------------------------------------------------------------------
elif menu == OPCION_BUSES:
    st.markdown('<p class="main-header">Gestión de Flota de Buses y Registro de Pilotos</p>', unsafe_allow_html=True)
    tab_flota, tab_crear_bus, tab_crear_piloto = st.tabs(["🚌 Ver Flota", "➕ Registrar Bus", "👨‍✈️ Registrar Piloto"])

    with tab_flota:
        with engine.connect() as conn:
            df_flota = pd.read_sql("""
                SELECT b.numero_unidad, b.placa, b.capacidad_pasajeros,
                       p.nombre_parqueo as parqueo_asignado,
                       COALESCE(pi.nombres || ' ' || pi.apellidos, '⚠️ SIN PILOTO') as piloto_asignado,
                       COALESCE(l.nombre_linea, 'Sin Línea') as linea_actual
                FROM bus b JOIN parqueo p ON b.id_parqueo = p.id_parqueo
                LEFT JOIN piloto pi ON pi.id_bus_asociado = b.id_bus
                LEFT JOIN linea l ON b.id_linea = l.id_linea;
            """, conn)
        st.dataframe(df_flota, use_container_width=True)

    with tab_crear_bus:
        st.subheader("➕ Registrar Nuevo Bus")
        with engine.connect() as conn:
            parqueos = pd.read_sql("SELECT id_parqueo, nombre_parqueo FROM parqueo;", conn)

        col_b1, col_b2 = st.columns(2)
        with col_b1:
            num_unidad = st.text_input("Número de Unidad (ej. TR-105):")
            placa_bus = st.text_input("Número de Placa:", value="U-000TM")
        with col_b2:
            cap_bus = st.number_input("Capacidad de Pasajeros:", min_value=50, value=100, step=10)
            parq_bus = st.selectbox("Parqueo Asignado (Obligatorio):", parqueos["nombre_parqueo"])
            id_parq_bus = parqueos[parqueos["nombre_parqueo"] == parq_bus]["id_parqueo"].values[0]

        if st.button("Guardar Bus"):
            if num_unidad.strip():
                try:
                    with engine.begin() as conn:
                        conn.execute(text("INSERT INTO bus (placa, numero_unidad, capacidad_pasajeros, id_parqueo) VALUES (:placa, :num, :cap, :id_p);"),
                                     {"placa": placa_bus, "num": num_unidad, "cap": int(cap_bus), "id_p": int(id_parq_bus)})
                    st.success(f"Bus '{num_unidad}' registrado correctamente.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al registrar bus: {e}")

    with tab_crear_piloto:
        st.subheader("👨‍✈️ Registrar Nuevo Piloto")
        with engine.connect() as conn:
            buses_sin_piloto = pd.read_sql("SELECT b.id_bus, b.numero_unidad FROM bus b LEFT JOIN piloto p ON p.id_bus_asociado = b.id_bus WHERE p.id_piloto IS NULL;", conn)

        col_p1, col_p2 = st.columns(2)
        with col_p1:
            dpi_piloto = st.text_input("DPI:")
            nom_piloto = st.text_input("Nombres:")
            ape_piloto = st.text_input("Apellidos:")
            tel_piloto = st.text_input("Teléfono de Contacto:")
        with col_p2:
            residencia_piloto = st.text_input("Dirección de Residencia:")
            educacion_piloto = st.text_input("Historial Educativo / Licencia:", value="Diversificado / Licencia Tipo A")
            bus_asoc = st.selectbox("Asignar Bus Inicial (Opcional):", ["Sin Asignar"] + list(buses_sin_piloto["numero_unidad"]))

        if st.button("Guardar Piloto"):
            if dpi_piloto and nom_piloto:
                try:
                    id_b_asoc = int(buses_sin_piloto[buses_sin_piloto["numero_unidad"] == bus_asoc]["id_bus"].values[0]) if bus_asoc != "Sin Asignar" else None
                    with engine.begin() as conn:
                        conn.execute(text("INSERT INTO piloto (dpi, nombres, apellidos, historial_educativo, direccion_residencia, telefono, id_bus_asociado) VALUES (:dpi, :nom, :ape, :edu, :dir, :tel, :id_b);"),
                                     {"dpi": dpi_piloto, "nom": nom_piloto, "ape": ape_piloto, "edu": educacion_piloto, "dir": residencia_piloto, "tel": tel_piloto, "id_b": id_b_asoc})
                    st.success("Piloto registrado exitosamente.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar piloto: {e}")

# -----------------------------------------------------------------------------
# MÓDULO 3: ESTACIONES & PARQUEOS
# -----------------------------------------------------------------------------
elif menu == OPCION_ESTACIONES:
    st.markdown('<p class="main-header">Gestión de Estaciones y Parqueos</p>', unsafe_allow_html=True)
    tab_ver_est, tab_crear_est, tab_crear_parq = st.tabs(["🏢 Ver Estaciones y Parqueos", "➕ Crear Nueva Estación", "🅿️ Registrar / Asignar Parqueo"])

    with tab_ver_est:
        with engine.connect() as conn:
            df_estaciones = pd.read_sql("""
                SELECT e.id_estacion, e.nombre as estacion, e.capacidad_maxima_pasajeros, 
                       m.nombre as municipalidad, COALESCE(p.nombre_parqueo, 'Sin Parqueo') as parqueo
                FROM estacion e JOIN municipalidad m ON e.id_municipalidad = m.id_municipalidad
                LEFT JOIN parqueo p ON p.id_estacion = e.id_estacion ORDER BY e.nombre;
            """, conn)
        st.dataframe(df_estaciones, use_container_width=True)

    with tab_crear_est:
        st.subheader("➕ Registrar Nueva Estación de Bus")
        with engine.connect() as conn:
            munis = pd.read_sql("SELECT id_municipalidad, nombre FROM municipalidad ORDER BY nombre;", conn)

        if not munis.empty:
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                nombre_estacion = st.text_input("Nombre de la Estación:")
                capacidad_estacion = st.number_input("Capacidad Máxima de Pasajeros:", min_value=50, value=500, step=50)
                muni_sel = st.selectbox("Municipalidad Perteneciente:", munis["nombre"])
                id_muni_sel = munis[munis["nombre"] == muni_sel]["id_municipalidad"].values[0]

            with col_e2:
                tiene_parqueo = st.checkbox("¿Desea crear un parqueo de buses para esta estación?")
                nombre_parqueo = st.text_input("Nombre del Parqueo:") if tiene_parqueo else None
                capacidad_buses_parqueo = st.number_input("Capacidad de Buses:", min_value=1, value=15, step=1) if tiene_parqueo else 0

            if st.button("Guardar Estación"):
                if nombre_estacion.strip():
                    try:
                        with engine.begin() as conn:
                            res = conn.execute(text("INSERT INTO estacion (nombre, capacidad_maxima_pasajeros, aforo_actual_pasajeros, id_municipalidad) VALUES (:nombre, :cap, 0, :id_muni) RETURNING id_estacion;"),
                                               {"nombre": nombre_estacion.strip(), "cap": int(capacidad_estacion), "id_muni": int(id_muni_sel)})
                            id_est_creada = res.fetchone()[0]

                            if tiene_parqueo and nombre_parqueo:
                                conn.execute(text("INSERT INTO parqueo (nombre_parqueo, capacidad_buses, id_estacion) VALUES (:nom_p, :cap_p, :id_e);"),
                                             {"nom_p": nombre_parqueo.strip(), "cap_p": int(capacidad_buses_parqueo), "id_e": int(id_est_creada)})

                        st.success(f"✅ Estación '{nombre_estacion}' registrada exitosamente.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar la estación: {e}")

    with tab_crear_parq:
        st.subheader("🅿️ Asignar Parqueo a Estación Existente")
        with engine.connect() as conn:
            estaciones_sin_p = pd.read_sql("SELECT e.id_estacion, e.nombre FROM estacion e LEFT JOIN parqueo p ON p.id_estacion = e.id_estacion WHERE p.id_parqueo IS NULL ORDER BY e.nombre;", conn)

        if not estaciones_sin_p.empty:
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                est_p_sel = st.selectbox("Seleccionar Estación:", estaciones_sin_p["nombre"])
                id_est_p_sel = estaciones_sin_p[estaciones_sin_p["nombre"] == est_p_sel]["id_estacion"].values[0]
            with col_p2:
                nom_p_nuevo = st.text_input("Nombre del Nuevo Parqueo:", value=f"Parqueo {est_p_sel}")
                cap_p_nueva = st.number_input("Capacidad de Buses:", min_value=1, value=10, step=1)

            if st.button("Guardar y Asignar Parqueo"):
                if nom_p_nuevo.strip():
                    try:
                        with engine.begin() as conn:
                            conn.execute(text("INSERT INTO parqueo (nombre_parqueo, capacidad_buses, id_estacion) VALUES (:nom_p, :cap_p, :id_e);"),
                                         {"nom_p": nom_p_nuevo.strip(), "cap_p": int(cap_p_nueva), "id_e": int(id_est_p_sel)})
                        st.success("✅ Parqueo asignado correctamente.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al asignar parqueo: {e}")

# -----------------------------------------------------------------------------
# MÓDULO 4: ACCESOS & GUARDIAS
# -----------------------------------------------------------------------------
elif menu == OPCION_GUARDIAS:
    st.markdown('<p class="main-header">Control de Seguridad en Accesos</p>', unsafe_allow_html=True)
    with engine.connect() as conn:
        df_guardias = pd.read_sql("""
            SELECT e.nombre as estacion, a.nombre_acceso, STRING_AGG(g.nombres || ' ' || g.apellidos, ', ') as guardias
            FROM acceso a JOIN estacion e ON a.id_estacion = e.id_estacion
            LEFT JOIN guardia g ON g.id_acceso = a.id_acceso
            GROUP BY e.nombre, a.nombre_acceso;
        """, conn)
    st.dataframe(df_guardias, use_container_width=True)

# -----------------------------------------------------------------------------
# MÓDULO 5: OPERADOR DE ESTACIÓN
# -----------------------------------------------------------------------------
elif menu == OPCION_OPERADOR:
    st.markdown('<p class="main-header">Puesto de Trabajo del Operador</p>', unsafe_allow_html=True)
    with engine.connect() as conn:
        estaciones_op = pd.read_sql("SELECT id_estacion, nombre, capacidad_maxima_pasajeros, aforo_actual_pasajeros FROM estacion ORDER BY nombre;", conn)

    if not estaciones_op.empty:
        est_sel = st.selectbox("Seleccionar Estación a Monitorear:", estaciones_op["nombre"])
        datos_est = estaciones_op[estaciones_op["nombre"] == est_sel].iloc[0]

        col_o1, col_o2 = st.columns(2)
        with col_o1:
            nuevo_aforo = st.number_input("Ocupación Actual de Pasajeros:", min_value=0, value=int(datos_est["aforo_actual_pasajeros"]))
            if st.button("Actualizar Ocupación"):
                with engine.begin() as conn:
                    conn.execute(text("UPDATE estacion SET aforo_actual_pasajeros = :a WHERE id_estacion = :id;"),
                                 {"a": int(nuevo_aforo), "id": int(datos_est["id_estacion"])})
                st.success("Aforo actualizado correctamente.")
                st.rerun()

        with col_o2:
            cap = datos_est["capacidad_maxima_pasajeros"]
            aforo = datos_est["aforo_actual_pasajeros"]
            pct = (aforo / cap) * 100 if cap > 0 else 0
            st.metric("Nivel de Ocupación Estación", f"{aforo} / {cap}", f"{pct:.1f}%")
            
            # Alertas
            if aforo >= (cap * 1.5):
                st.error("🚨 ALERTA CRÍTICA DE SATURACIÓN (≥ 150% de capacidad). Enviar bus de refuerzo inmediatamente.")
            elif aforo >= cap:
                st.warning("⚠️ CAPACIDAD NOMINAL ALCANZADA (100%). Monitorear aforo de acceso.")
            else:
                st.success("✅ Aforo dentro de rangos operativos normales.")

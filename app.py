import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine, text

# Configuración de la página Web
st.set_page_config(
    page_title="Transmetro - Control Integrado",
    page_icon="🚌",
    layout="wide"
)

# Estilos CSS personalizados
st.markdown("""
    <style>
    .main-header { font-size: 28px; font-weight: bold; color: #1F4E78; }
    .stAlert { border-radius: 8px; }
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

def get_db_connection():
    # Obtener credenciales desde secretos o valores por defecto
    if "postgres" in st.secrets:
        cfg = dict(st.secrets["postgres"])
        cfg["sslmode"] = "require"
        try:
            return psycopg2.connect(**cfg, cursor_factory=RealDictCursor)
        except Exception as e:
            st.error(f"Error al conectar con PostgreSQL: {e}")
            return None
    else:
        try:
            conn = psycopg2.connect(
                host="ep-tiny-cloud-b4h9eg0r-pooler.c-6.us-east-2.aws.neon.tech",
                database="transmetro_db",
                user="transmetro_db_owner",
                password="TU_PASSWORD_AQUI",  # ⚠️ Coloca aquí tu contraseña de Neon
                port=5432,
                sslmode="require"  # ⚠️ Esencial para Neon
            )
            return conn
        except Exception as e:
            st.error(f"Error al conectar con PostgreSQL: {e}")
            return None

# -----------------------------------------------------------------------------
# NAVEGACIÓN PRINCIPAL
# -----------------------------------------------------------------------------
st.sidebar.image("https://img.icons8.com/color/96/bus.png", width=70)
st.sidebar.title("Transmetro Control")

menu = st.sidebar.radio(
    "Módulos Principales:",
    [
        "🗺️ Gestión de Líneas & Rutas",
        "🚌 Flota de Buses & Pilotos",
        "🏢 Estaciones & Parqueos",
        "🛡️ Accesos & Guardias",
        "🚨 Operador de Estación"
    ]
)

# -----------------------------------------------------------------------------
# MÓDULO 1: GESTIÓN DE LÍNEAS & RUTAS
# -----------------------------------------------------------------------------
if menu == "🗺️️ Gestión de Líneas & Rutas":
    st.markdown('<p class="main-header">Gestión de Líneas y Esquema Visual de Paradas</p>', unsafe_allow_html=True)

    tab_ver, tab_crear_linea = st.tabs(["📌 Ver / Editar Línea y Paradas", "➕ Crear Nueva Línea"])

    with tab_ver:
        with engine.connect() as conn:
            lineas = pd.read_sql("SELECT id_linea, nombre_linea, color_identificador FROM linea ORDER BY nombre_linea;", conn)

        if not lineas.empty:
            col_l1, col_l2 = st.columns([2, 1])
            with col_l1:
                linea_seleccionada = st.selectbox("Seleccionar Línea:", lineas["nombre_linea"])
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

                query_buses = text("""
                    SELECT b.id_bus, b.numero_unidad, b.placa, p.nombres || ' ' || p.apellidos as piloto
                    FROM bus b
                    LEFT JOIN piloto p ON p.id_bus_asociado = b.id_bus
                    WHERE b.id_linea = :id_linea;
                """)
                df_buses_linea = pd.read_sql(query_buses, conn, params={"id_linea": int(id_linea_sel)})

            distancia_total = df_ruta["distancia_siguiente_km"].sum() if not df_ruta.empty else 0.0

            # Indicadores de Línea
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("Color Identificador", str(color_lin))
            col_m2.metric("Total Estaciones", len(df_ruta))
            col_m3.metric("Distancia Total Recorrido", f"{distancia_total:.2f} km")

            st.divider()

            # Visualización Dinámica del Recorrido
            st.subheader(f"🚏 Esquema de Recorrido: {linea_seleccionada}")
            if not df_ruta.empty:
                for idx, row in df_ruta.iterrows():
                    st.markdown(f"""
                        <div class="station-card">
                            <b>Parada #{row['orden_estacion']} - {row['estacion']}</b> ({row['municipalidad']})<br>
                            <small>📍 Distancia a la siguiente parada: <b>{row['distancia_siguiente_km']} km</b></small>
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Esta línea aún no cuenta con estaciones asignadas.")

            st.divider()
            col_ag1, col_ag2 = st.columns(2)

            with col_ag1:
                st.subheader("➕ Agregar Parada a la Ruta")
                with engine.connect() as conn:
                    estaciones_todas = pd.read_sql("SELECT id_estacion, nombre FROM estacion ORDER BY nombre;", conn)

                if not estaciones_todas.empty:
                    est_nueva = st.selectbox("Seleccionar Estación:", estaciones_todas["nombre"])
                    id_est_nueva = estaciones_todas[estaciones_todas["nombre"] == est_nueva]["id_estacion"].values[0]
                    orden_nuevo = st.number_input("Número de Parada (1, 2, 3...):", min_value=1, value=len(df_ruta)+1)
                    dist_nueva = st.number_input("Distancia a sig. parada (km):", min_value=0.0, value=1.5, step=0.1)

                    if st.button("Guardar Parada"):
                        try:
                            with engine.begin() as conn:
                                conn.execute(text("""
                                    INSERT INTO linea_estacion (id_linea, id_estacion, orden_estacion, distancia_siguiente_km)
                                    VALUES (:id_linea, :id_estacion, :orden, :dist);
                                """), {"id_linea": int(id_linea_sel), "id_estacion": int(id_est_nueva), "orden": int(orden_nuevo), "dist": float(dist_nueva)})
                            st.success("Parada agregada correctamente.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al agregar parada: {e}")

            with col_ag2:
                st.subheader("🚌 Asignar Bus a esta Línea")
                with engine.connect() as conn:
                    buses_disp = pd.read_sql("""
                        SELECT b.id_bus, b.numero_unidad, p.nombres || ' ' || p.apellidos as piloto
                        FROM bus b
                        JOIN piloto p ON p.id_bus_asociado = b.id_bus
                        WHERE b.id_linea IS NULL OR b.id_linea = :id_l;
                    """, conn, params={"id_l": int(id_linea_sel)})

                if not buses_disp.empty:
                    bus_sel = st.selectbox("Bus Disponible (Requiere Piloto):", buses_disp["numero_unidad"] + " - Piloto: " + buses_disp["piloto"])
                    id_bus_sel = buses_disp[buses_disp["numero_unidad"] == bus_sel.split(" - ")[0]]["id_bus"].values[0]

                    if st.button("Asignar Bus"):
                        with engine.begin() as conn:
                            conn.execute(text("UPDATE bus SET id_linea = :id_l WHERE id_bus = :id_b;"),
                                         {"id_l": int(id_linea_sel), "id_b": int(id_bus_sel)})
                        st.success("Bus asignado a la línea.")
                        st.rerun()
                else:
                    st.warning("No hay buses disponibles con piloto asignado.")

    with tab_crear_linea:
        st.subheader("➕ Registrar Nueva Línea de Transmetro")
        with engine.connect() as conn:
            munis = pd.read_sql("SELECT id_municipalidad, nombre FROM municipalidad;", conn)

        col_cl1, col_cl2 = st.columns(2)
        with col_cl1:
            nom_linea = st.text_input("Nombre de la Línea (ej. Línea 13):")
            color_linea = st.text_input("Color Identificador:", value="Verde")
        with col_cl2:
            muni_linea = st.selectbox("Municipalidad Administradora:", munis["nombre"])
            id_muni_linea = munis[munis["nombre"] == muni_linea]["id_municipalidad"].values[0]

        if st.button("Guardar Nueva Línea"):
            if nom_linea:
                try:
                    with engine.begin() as conn:
                        conn.execute(text("""
                            INSERT INTO linea (nombre_linea, color_identificador, id_municipalidad)
                            VALUES (:nom, :col, :id_m);
                        """), {"nom": nom_linea, "col": color_linea, "id_m": int(id_muni_linea)})
                    st.success(f"Línea '{nom_linea}' creada exitosamente.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al crear línea: {e}")

# -----------------------------------------------------------------------------
# MÓDULO 2: FLOTA DE BUSES & PILOTOS
# -----------------------------------------------------------------------------
elif menu == "🚌 Flota de Buses & Pilotos":
    st.markdown('<p class="main-header">Gestión de Flota de Buses y Registro de Pilotos</p>', unsafe_allow_html=True)

    tab_flota, tab_crear_bus, tab_crear_piloto = st.tabs(["🚌 Ver Flota", "➕ Registrar Bus", "👨‍✈️ Registrar Piloto"])

    with tab_flota:
        with engine.connect() as conn:
            df_flota = pd.read_sql("""
                SELECT b.numero_unidad, b.placa, b.capacidad_pasajeros,
                       p.nombre_parqueo as parqueo_asignado,
                       COALESCE(pi.nombres || ' ' || pi.apellidos, '⚠️ SIN PILOTO') as piloto_asignado,
                       COALESCE(l.nombre_linea, 'Sin Línea') as linea_actual
                FROM bus b
                JOIN parqueo p ON b.id_parqueo = p.id_parqueo
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
            if num_unidad:
                try:
                    with engine.begin() as conn:
                        conn.execute(text("""
                            INSERT INTO bus (placa, numero_unidad, capacidad_pasajeros, id_parqueo)
                            VALUES (:placa, :num, :cap, :id_p);
                        """), {"placa": placa_bus, "num": num_unidad, "cap": int(cap_bus), "id_p": int(id_parq_bus)})
                    st.success(f"Bus '{num_unidad}' registrado correctamente.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al registrar bus: {e}")

    with tab_crear_piloto:
        st.subheader("👨‍✈️ Registrar Nuevo Piloto")
        with engine.connect() as conn:
            buses_sin_piloto = pd.read_sql("""
                SELECT b.id_bus, b.numero_unidad
                FROM bus b LEFT JOIN piloto p ON p.id_bus_asociado = b.id_bus
                WHERE p.id_piloto IS NULL;
            """, conn)

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
                    id_b_asoc = None
                    if bus_asoc != "Sin Asignar":
                        id_b_asoc = int(buses_sin_piloto[buses_sin_piloto["numero_unidad"] == bus_asoc]["id_bus"].values[0])

                    with engine.begin() as conn:
                        conn.execute(text("""
                            INSERT INTO piloto (dpi, nombres, apellidos, historial_educativo, direccion_residencia, telefono, id_bus_asociado)
                            VALUES (:dpi, :nom, :ape, :edu, :dir, :tel, :id_b);
                        """), {"dpi": dpi_piloto, "nom": nom_piloto, "ape": ape_piloto, "edu": educacion_piloto, "dir": residencia_piloto, "tel": tel_piloto, "id_b": id_b_asoc})
                    st.success("Piloto registrado exitosamente.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar piloto: {e}")

# -----------------------------------------------------------------------------
# MÓDULO 3: ESTACIONES & PARQUEOS
# -----------------------------------------------------------------------------
elif menu == "🏢 Estaciones & Parqueos":
    st.markdown('<p class="main-header">Gestión de Estaciones y Parqueos</p>', unsafe_allow_html=True)
    with engine.connect() as conn:
        df_estaciones = pd.read_sql("""
            SELECT e.nombre as estacion, e.capacidad_maxima_pasajeros, m.nombre as municipalidad,
                   COALESCE(p.nombre_parqueo, 'Sin Parqueo') as parqueo
            FROM estacion e
            JOIN municipalidad m ON e.id_municipalidad = m.id_municipalidad
            LEFT JOIN parqueo p ON p.id_estacion = e.id_estacion;
        """, conn)
    st.dataframe(df_estaciones, use_container_width=True)

# -----------------------------------------------------------------------------
# MÓDULO 4: ACCESOS & GUARDIAS
# -----------------------------------------------------------------------------
elif menu == "🛡️ Accesos & Guardias":
    st.markdown('<p class="main-header">Control de Seguridad en Accesos</p>', unsafe_allow_html=True)
    with engine.connect() as conn:
        df_guardias = pd.read_sql("""
            SELECT e.nombre as estacion, a.nombre_acceso, STRING_AGG(g.nombres || ' ' || g.apellidos, ', ') as guardias
            FROM acceso a
            JOIN estacion e ON a.id_estacion = e.id_estacion
            LEFT JOIN guardia g ON g.id_acceso = a.id_acceso
            GROUP BY e.nombre, a.nombre_acceso;
        """, conn)
    st.dataframe(df_guardias, use_container_width=True)

# -----------------------------------------------------------------------------
# MÓDULO 5: OPERADOR DE ESTACIÓN
# -----------------------------------------------------------------------------
elif menu == "🚨 Operador de Estación":
    st.markdown('<p class="main-header">Puesto de Trabajo del Operador</p>', unsafe_allow_html=True)
    with engine.connect() as conn:
        estaciones_op = pd.read_sql("SELECT id_estacion, nombre, capacidad_maxima_pasajeros, aforo_actual_pasajeros FROM estacion ORDER BY nombre;", conn)

    if not estaciones_op.empty:
        est_sel = st.selectbox("Seleccionar Estación:", estaciones_op["nombre"])
        datos_est = estaciones_op[estaciones_op["nombre"] == est_sel].iloc[0]

        col_o1, col_o2 = st.columns(2)
        with col_o1:
            nuevo_aforo = st.number_input("Ocupación Actual:", min_value=0, value=int(datos_est["aforo_actual_pasajeros"]))
            if st.button("Actualizar Ocupación"):
                with engine.begin() as conn:
                    conn.execute(text("UPDATE estacion SET aforo_actual_pasajeros = :a WHERE id_estacion = :id;"),
                                 {"a": int(nuevo_aforo), "id": int(datos_est["id_estacion"])})
                st.success("Aforo actualizado.")
                st.rerun()

        with col_o2:
            cap = datos_est["capacidad_maxima_pasajeros"]
            aforo = datos_est["aforo_actual_pasajeros"]
            pct = (aforo / cap) * 100
            st.metric("Ocupación", f"{aforo} / {cap}", f"{pct:.1f}%")
            if aforo >= (cap * 1.5):
                st.error("🚨 ALERTA DE SATURACIÓN (≥ 150%)")
            elif aforo >= cap:
                st.warning("⚠️️ Capacidad nominal alcanzada")
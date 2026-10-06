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
# NAVEGACIÓN PRINCIPAL
# -----------------------------------------------------------------------------
st.sidebar.image("https://img.icons8.com/color/96/bus.png", width=70)
st.sidebar.title("Transmetro Control")

# Definición exacta de las opciones del menú
OPCION_LINEAS = "🗺️ Gestión de Líneas & Rutas"
OPCION_BUSES = "🚌 Flota de Buses & Pilotos"
OPCION_ESTACIONES = "🏢 Estaciones & Parqueos"
OPCION_GUARDIAS = "🛡️ Accesos & Guardias"
OPCION_OPERADOR = "🚨 Operador de Estación"

menu = st.sidebar.radio(
    "Módulos Principales:",
    [
        OPCION_LINEAS,
        OPCION_BUSES,
        OPCION_ESTACIONES,
        OPCION_GUARDIAS,
        OPCION_OPERADOR
    ]
)

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
        else:
            st.warning("⚠️ No existen líneas registradas en la base de datos. Utiliza la pestaña '➕ Crear Nueva Línea' para registrar la primera.")

    with tab_crear_linea:
        st.subheader("➕ Registrar Nueva Línea de Transmetro")
        try:
            with engine.connect() as conn:
                munis = pd.read_sql("SELECT id_municipalidad, nombre FROM municipalidad;", conn)
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
        else:
            st.error("No hay municipalidades registradas. Ejecuta el script de datos iniciales (`seed_data.sql`).")

# -----------------------------------------------------------------------------
# MÓDULO 2: FLOTA DE BUSES & PILOTOS
# -----------------------------------------------------------------------------
elif menu == OPCION_BUSES:
    st.markdown('<p class="main-header">Gestión de Flota de Buses y Registro de Pilotos</p>', unsafe_allow_html=True)
    st.info("Módulo de Flota activado correctamente.")

# -----------------------------------------------------------------------------
# MÓDULO 3: ESTACIONES & PARQUEOS
# -----------------------------------------------------------------------------
elif menu == OPCION_ESTACIONES:
    st.markdown('<p class="main-header">Gestión de Estaciones y Parqueos</p>', unsafe_allow_html=True)
    st.info("Módulo de Estaciones activado correctamente.")

# -----------------------------------------------------------------------------
# MÓDULO 4: ACCESOS & GUARDIAS
# -----------------------------------------------------------------------------
elif menu == OPCION_GUARDIAS:
    st.markdown('<p class="main-header">Control de Seguridad en Accesos</p>', unsafe_allow_html=True)
    st.info("Módulo de Guardias activado correctamente.")

# -----------------------------------------------------------------------------
# MÓDULO 5: OPERADOR DE ESTACIÓN
# -----------------------------------------------------------------------------
elif menu == OPCION_OPERADOR:
    st.markdown('<p class="main-header">Puesto de Trabajo del Operador</p>', unsafe_allow_html=True)
    st.info("Módulo Operador activado correctamente.")
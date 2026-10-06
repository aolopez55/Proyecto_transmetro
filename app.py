import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor

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
# CONEXIÓN A LA BASE DE DATOS POSTGRESQL (Local o Cloud como Neon/Supabase)
# -----------------------------------------------------------------------------
def get_db_connection():
    # Obtener credenciales desde secretos o valores por defecto para pruebas locales
    db_config = st.secrets.get("postgres", {
        "host": "ep-tiny-cloud-b4h9eg0r-pooler.c-6.us-east-2.aws.neon.tech",
        "database": "transmetro_db",
        "user": "transmetro_db_owner",
        "password": "   ",
        "port": 5432
    })
    try:
        conn = psycopg2.connect(**db_config, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        st.error(f"Error al conectar con la Base de Datos PostgreSQL: {e}")
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
        "🏢 Estaciones & Parqueos",
        "🚌 Flota de Buses & Pilotos",
        "🛡️ Accesos & Guardias de Seguridad",
        "🚨 Operador de Estación (Aforo & Alertas)"
    ]
)

# -----------------------------------------------------------------------------
# MÓDULO 1: GESTIÓN DE LÍNEAS & RUTAS
# -----------------------------------------------------------------------------
if menu == "🗺️ Gestión de Líneas & Rutas":
    st.markdown('<p class="main-header">Gestión de Líneas, Secuencia de Estaciones y Distancias</p>', unsafe_allow_html=True)

    with engine.connect() as conn:
        lineas = pd.read_sql("SELECT id_linea, nombre_linea FROM linea ORDER BY nombre_linea;", conn)

    if not lineas.empty:
        linea_seleccionada = st.selectbox("Seleccione la Línea a Gestionar:", lineas["nombre_linea"])
        id_linea_sel = lineas[lineas["nombre_linea"] == linea_seleccionada]["id_linea"].values[0]

        # Consultar datos de la línea seleccionada
        with engine.connect() as conn:
            # Distancia Total y Paradas
            query_ruta = text("""
                SELECT le.orden_estacion, e.id_estacion, e.nombre as estacion, m.nombre as municipalidad,
                       le.distancia_siguiente_km
                FROM linea_estacion le
                JOIN estacion e ON le.id_estacion = e.id_estacion
                JOIN municipalidad m ON e.id_municipalidad = m.id_municipalidad
                WHERE le.id_linea = :id_linea
                ORDER BY le.orden_estacion;
            """)
            df_ruta = pd.read_sql(query_ruta, conn, params={"id_linea": int(id_linea_sel)})

            # Distancia Total
            distancia_total = df_ruta["distancia_siguiente_km"].sum() if not df_ruta.empty else 0.0

            # Buses Asignados a la Línea
            query_buses = text("""
                SELECT b.id_bus, b.numero_unidad, b.placa, p.nombres || ' ' || p.apellidos as piloto
                FROM bus b
                LEFT JOIN piloto p ON p.id_bus_asociado = b.id_bus
                WHERE b.id_linea = :id_linea;
            """)
            df_buses_linea = pd.read_sql(query_buses, conn, params={"id_linea": int(id_linea_sel)})

        # Dashboard Metricas
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Estaciones en Ruta", len(df_ruta))
        col_m2.metric("Distancia Total de Línea", f"{distancia_total:.2f} km")
        col_m3.metric("Buses Asignados", len(df_buses_linea))

        st.divider()

        tab_rutas, tab_buses_linea = st.tabs(["📌 Secuencia de Estaciones y Distancias", "🚌 Buses Asignados a esta Línea"])

        with tab_rutas:
            st.subheader(f"Orden de Recorrido: {linea_seleccionada}")
            if not df_ruta.empty:
                st.dataframe(df_ruta, use_container_width=True)
            else:
                st.warning("Esta línea aún no tiene estaciones configuradas.")

            # Formulario para Agregar Estación a la Ruta
            st.subheader("➕ Agregar Estación a la Ruta")
            with engine.connect() as conn:
                estaciones_todas = pd.read_sql("SELECT id_estacion, nombre FROM estacion ORDER BY nombre;", conn)

            col_a1, col_a2, col_a3 = st.columns(3)
            with col_a1:
                est_nueva = st.selectbox("Seleccionar Estación:", estaciones_todas["nombre"])
                id_est_nueva = estaciones_todas[estaciones_todas["nombre"] == est_nueva]["id_estacion"].values[0]
            with col_a2:
                orden_nuevo = st.number_input("Orden de Parada (1, 2, 3...):", min_value=1, value=len(df_ruta)+1)
            with col_a3:
                dist_nueva = st.number_input("Distancia a la sig. estación (km):", min_value=0.0, value=1.5, step=0.1)

            if st.button("Guardar Estación en Ruta"):
                try:
                    with engine.begin() as conn:
                        conn.execute(text("""
                            INSERT INTO linea_estacion (id_linea, id_estacion, orden_estacion, distancia_siguiente_km)
                            VALUES (:id_linea, :id_estacion, :orden, :dist);
                        """), {"id_linea": int(id_linea_sel), "id_estacion": int(id_est_nueva), "orden": int(orden_nuevo), "dist": float(dist_nueva)})
                    st.success("Estación agregada a la línea correctamente.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al agregar estación: {e}")

        with tab_buses_linea:
            st.subheader("Buses Activos en esta Línea")
            st.dataframe(df_buses_linea, use_container_width=True)

            st.subheader("➕ Asignar Bus a esta Línea")
            # Buscar buses que TENGAN PILOTO asignado y que no estén en otra línea (o estén en esta)
            with engine.connect() as conn:
                query_buses_disponibles = text("""
                    SELECT b.id_bus, b.numero_unidad, p.nombres || ' ' || p.apellidos as piloto
                    FROM bus b
                    JOIN piloto p ON p.id_bus_asociado = b.id_bus
                    WHERE b.id_linea IS NULL OR b.id_linea = :id_linea;
                """)
                buses_disp = pd.read_sql(query_buses_disponibles, conn, params={"id_linea": int(id_linea_sel)})

            if not buses_disp.empty:
                bus_sel = st.selectbox("Seleccionar Bus (Solo con Piloto Asignado):", buses_disp["numero_unidad"] + " - Piloto: " + buses_disp["piloto"])
                id_bus_sel = buses_disp[buses_disp["numero_unidad"] == bus_sel.split(" - ")[0]]["id_bus"].values[0]

                if st.button("Asignar Bus a esta Línea"):
                    with engine.begin() as conn:
                        conn.execute(text("UPDATE bus SET id_linea = :id_linea WHERE id_bus = :id_bus;"),
                                     {"id_linea": int(id_linea_sel), "id_bus": int(id_bus_sel)})
                    st.success("Bus asignado a la línea correctamente.")
                    st.rerun()
            else:
                st.error("⚠️ **No hay buses disponibles con piloto asignado.** Primero debe asignar un piloto al bus en el módulo de 'Flota de Buses & Pilotos'.")

# -----------------------------------------------------------------------------
# MÓDULO 2: ESTACIONES, PARQUEOS & MUNICIPALIDADES
# -----------------------------------------------------------------------------
elif menu == "🏢 Estaciones & Parqueos":
    st.markdown('<p class="main-header">Administración de Estaciones, Municipalidades y Parqueos</p>', unsafe_allow_html=True)

    with engine.connect() as conn:
        df_estaciones_full = pd.read_sql("""
            SELECT e.id_estacion, e.nombre as estacion, e.capacidad_maxima_pasajeros,
                   m.nombre as municipalidad, COALESCE(p.nombre_parqueo, 'Sin Parqueo') as parqueo_asociado,
                   COALESCE(p.capacidad_buses, 0) as capacidad_parqueo_buses
            FROM estacion e
            JOIN municipalidad m ON e.id_municipalidad = m.id_municipalidad
            LEFT JOIN parqueo p ON p.id_estacion = e.id_estacion;
        """, conn)

    st.dataframe(df_estaciones_full, use_container_width=True)

    st.divider()
    st.subheader("➕ Registrar Nueva Estación de Bus")

    with engine.connect() as conn:
        munis = pd.read_sql("SELECT id_municipalidad, nombre FROM municipalidad;", conn)

    col_e1, col_e2 = st.columns(2)
    with col_e1:
        nombre_estacion = st.text_input("Nombre de la Estación:")
        capacidad_estacion = st.number_input("Capacidad Máxima de Pasajeros:", min_value=50, value=500, step=50)
        muni_sel = st.selectbox("Municipalidad a la que pertenece (Obligatorio):", munis["nombre"])
        id_muni_sel = munis[munis["nombre"] == muni_sel]["id_municipalidad"].values[0]

    with col_e2:
        tiene_parqueo = st.checkbox("¿Esta estación cuenta con parqueo de buses?")
        if tiene_parqueo:
            nombre_parqueo = st.text_input("Nombre del Parqueo:", value=f"Parqueo {nombre_estacion}")
            capacidad_buses_parqueo = st.number_input("Capacidad de Buses en Parqueo:", min_value=1, value=15)
        else:
            nombre_parqueo = None
            capacidad_buses_parqueo = 0

    if st.button("Guardar Nueva Estación"):
        if nombre_estacion:
            try:
                with engine.begin() as conn:
                    # Insertar Estación
                    res = conn.execute(text("""
                        INSERT INTO estacion (nombre, capacidad_maxima_pasajeros, aforo_actual_pasajeros, id_municipalidad)
                        VALUES (:nombre, :cap, 0, :id_muni) RETURNING id_estacion;
                    """), {"nombre": nombre_estacion, "cap": capacidad_estacion, "id_muni": int(id_muni_sel)})
                    id_est_creada = res.fetchone()[0]

                    # Insertar Parqueo si aplica
                    if tiene_parqueo and nombre_parqueo:
                        conn.execute(text("""
                            INSERT INTO parqueo (nombre_parqueo, capacidad_buses, id_estacion)
                            VALUES (:nom_p, :cap_p, :id_e);
                        """), {"nom_p": nombre_parqueo, "cap_p": capacidad_buses_parqueo, "id_e": id_est_creada})

                st.success(f"Estación '{nombre_estacion}' registrada exitosamente.")
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar: {e}")
        else:
            st.warning("Ingrese el nombre de la estación.")

# -----------------------------------------------------------------------------
# MÓDULO 3: FLOTA DE BUSES & PILOTOS
# -----------------------------------------------------------------------------
elif menu == "🚌 Flota de Buses & Pilotos":
    st.markdown('<p class="main-header">Gestión de Flota, Parqueos Obligatorios y Pilotos</p>', unsafe_allow_html=True)

    with engine.connect() as conn:
        df_flota = pd.read_sql("""
            SELECT b.id_bus, b.numero_unidad, b.placa, b.capacidad_pasajeros,
                   p.nombre_parqueo as parqueo_asignado,
                   COALESCE(pi.nombres || ' ' || pi.apellidos, '⚠️ SIN PILOTO') as piloto_asignado,
                   COALESCE(l.nombre_linea, 'Sin Línea') as linea_actual
            FROM bus b
            JOIN parqueo p ON b.id_parqueo = p.id_parqueo
            LEFT JOIN piloto pi ON pi.id_bus_asociado = b.id_bus
            LEFT JOIN linea l ON b.id_linea = l.id_linea;
        """, conn)

    st.dataframe(df_flota, use_container_width=True)

    st.divider()
    col_b1, col_b2 = st.columns(2)

    with col_b1:
        st.subheader("🔄 Reasignar Parqueo a un Bus")
        st.caption("Un bus puede cambiar de parqueo pero NUNCA quedar sin parqueo.")

        with engine.connect() as conn:
            parqueos_todos = pd.read_sql("SELECT id_parqueo, nombre_parqueo FROM parqueo;", conn)

        bus_reasi = st.selectbox("Seleccionar Bus a Reasignar Parqueo:", df_flota["numero_unidad"])
        id_bus_reasi = df_flota[df_flota["numero_unidad"] == bus_reasi]["id_bus"].values[0]

        parqueo_nuevo = st.selectbox("Seleccionar Nuevo Parqueo:", parqueos_todos["nombre_parqueo"])
        id_parq_nuevo = parqueos_todos[parqueos_todos["nombre_parqueo"] == parqueo_nuevo]["id_parqueo"].values[0]

        if st.button("Cambiar Parqueo"):
            with engine.begin() as conn:
                conn.execute(text("UPDATE bus SET id_parqueo = :id_p WHERE id_bus = :id_b;"),
                             {"id_p": int(id_parq_nuevo), "id_b": int(id_bus_reasi)})
            st.success("Parqueo reasignado correctamente.")
            st.rerun()

    with col_b2:
        st.subheader("👨‍✈️ Asignar / Cambiar Piloto de Bus")
        with engine.connect() as conn:
            pilotos_libres = pd.read_sql("SELECT id_piloto, nombres || ' ' || apellidos as nombre_completo FROM piloto;", conn)

        piloto_sel = st.selectbox("Seleccionar Piloto:", pilotos_libres["nombre_completo"])
        id_piloto_sel = pilotos_libres[pilotos_libres["nombre_completo"] == piloto_sel]["id_piloto"].values[0]

        bus_para_piloto = st.selectbox("Seleccionar Bus para el Piloto:", df_flota["numero_unidad"])
        id_bus_para_piloto = df_flota[df_flota["numero_unidad"] == bus_para_piloto]["id_bus"].values[0]

        if st.button("Asignar Piloto a Bus"):
            with engine.begin() as conn:
                conn.execute(text("UPDATE piloto SET id_bus_asociado = :id_b WHERE id_piloto = :id_p;"),
                             {"id_b": int(id_bus_para_piloto), "id_p": int(id_piloto_sel)})
            st.success("Piloto asignado al bus exitosamente.")
            st.rerun()

# -----------------------------------------------------------------------------
# MÓDULO 4: ACCESOS & GUARDIAS DE SEGURIDAD
# -----------------------------------------------------------------------------
elif menu == "🛡️ Accesos & Guardias de Seguridad":
    st.markdown('<p class="main-header">Control de Accesos y Guardias de Seguridad</p>', unsafe_allow_html=True)
    st.info("Cada estación cuenta con por lo menos un guardia de seguridad por acceso.")

    with engine.connect() as conn:
        df_guardias = pd.read_sql("""
            SELECT e.nombre as estacion, a.nombre_acceso,
                   COUNT(g.id_guardia) as total_guardias,
                   STRING_AGG(g.nombres || ' ' || g.apellidos, ', ') as guardias_asignados
            FROM acceso a
            JOIN estacion e ON a.id_estacion = e.id_estacion
            LEFT JOIN guardia g ON g.id_acceso = a.id_acceso
            GROUP BY e.nombre, a.nombre_acceso;
        """, conn)

    st.dataframe(df_guardias, use_container_width=True)

    st.divider()
    st.subheader("➕ Asignar Guardia a un Acceso")

    with engine.connect() as conn:
        accesos_lista = pd.read_sql("""
            SELECT a.id_acceso, e.nombre || ' - ' || a.nombre_acceso as acceso_completo
            FROM acceso a JOIN estacion e ON a.id_estacion = e.id_estacion;
        """, conn)

    col_g1, col_g2 = st.columns(2)
    with col_g1:
        dpi_guardia = st.text_input("DPI Guardia:")
        nombres_guardia = st.text_input("Nombres Guardia:")
        apellidos_guardia = st.text_input("Apellidos Guardia:")
    with col_g2:
        acceso_sel = st.selectbox("Acceso a Asignar:", accesos_lista["acceso_completo"])
        id_acc_sel = accesos_lista[accesos_lista["acceso_completo"] == acceso_sel]["id_acceso"].values[0]

    if st.button("Registrar Guardia en Acceso"):
        if dpi_guardia and nombres_guardia:
            try:
                with engine.begin() as conn:
                    conn.execute(text("""
                        INSERT INTO guardia (dpi, nombres, apellidos, id_acceso)
                        VALUES (:dpi, :nom, :ape, :id_acc);
                    """), {"dpi": dpi_guardia, "nom": nombres_guardia, "ape": apellidos_guardia, "id_acc": int(id_acc_sel)})
                st.success("Guardia registrado y asignado al acceso.")
                st.rerun()
            except Exception as e:
                st.error(f"Error al registrar guardia: {e}")

# -----------------------------------------------------------------------------
# MÓDULO 5: OPERADOR DE ESTACIÓN (AFORO & ALERTAS)
# -----------------------------------------------------------------------------
elif menu == "🚨 Operador de Estación (Aforo & Alertas)":
    st.markdown('<p class="main-header">Módulo de Trabajo del Operador de Estación</p>', unsafe_allow_html=True)

    with engine.connect() as conn:
        estaciones_op = pd.read_sql("SELECT id_estacion, nombre, capacidad_maxima_pasajeros, aforo_actual_pasajeros FROM estacion ORDER BY nombre;", conn)

    est_seleccionada = st.selectbox("Seleccionar Estación donde trabaja:", estaciones_op["nombre"])
    datos_est = estaciones_op[estaciones_op["nombre"] == est_seleccionada].iloc[0]

    col_o1, col_o2 = st.columns([1, 2])

    with col_o1:
        st.subheader("Actualizar Aforo")
        nuevo_aforo = st.number_input("Cantidad de Pasajeros en Estación:", min_value=0, value=int(datos_est["aforo_actual_pasajeros"]))
        if st.button("Actualizar Ocupación"):
            with engine.begin() as conn:
                conn.execute(text("UPDATE estacion SET aforo_actual_pasajeros = :aforo WHERE id_estacion = :id_e;"),
                             {"aforo": int(nuevo_aforo), "id_e": int(datos_est["id_estacion"])})
            st.success("Aforo actualizado.")
            st.rerun()

    with col_o2:
        st.subheader("Monitoreo de Capacidad")
        cap = datos_est["capacidad_maxima_pasajeros"]
        aforo = datos_est["aforo_actual_pasajeros"]
        pct = (aforo / cap) * 100

        st.metric(label=f"Ocupación en {est_seleccionada}", value=f"{aforo} / {cap} Pasajeros", delta=f"{pct:.1f}%")

        if aforo >= (cap * 1.5):
            st.error("🚨 **ALERTA DE SATURACIÓN (≥ 150% Capacidad):** Se ha generado una alerta automática a la central para enviar un bus de refuerzo inmediatamente.")
        elif aforo >= cap:
            st.warning("⚠️ **ESTACIÓN A SU MÁXIMA CAPACIDAD nominal.**")
        else:
            st.success("🟢 **Aforo Operativo Normal.**")
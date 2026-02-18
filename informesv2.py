import streamlit as st
import pandas as pd
import plotly.express as px


# -----------------------------
# Configuración básica
# -----------------------------
st.set_page_config(
    page_title="Dashboard Comercial - Consolido",
    layout="wide"
)

st.title("📊 Dashboard Comercial – Consolido")
st.caption("Versión 2 · armado desde cero")

import os

st.sidebar.header("📂 Distribuidor")

DATA_PATH = "data"

archivos = sorted([
    f for f in os.listdir(DATA_PATH)
    if f.endswith(".xlsx")
])

if not archivos:
    st.error("No hay archivos Excel en la carpeta data/")
    st.stop()

archivo_sel = st.sidebar.selectbox(
    "Seleccionar distribuidor",
    archivos
)

ruta_archivo = os.path.join(DATA_PATH, archivo_sel)

# -----------------------------
# Carga de datos
# -----------------------------
@st.cache_data
def cargar_datos(ruta_archivo):
    return pd.read_excel(ruta_archivo)

df = cargar_datos(ruta_archivo)

# -----------------------------
# Normalización de columnas
# -----------------------------
df.columns = (
    df.columns
      .str.lower()
      .str.strip()
      .str.replace(" ", "_")
      .str.replace("á", "a")
      .str.replace("é", "e")
      .str.replace("í", "i")
      .str.replace("ó", "o")
      .str.replace("ú", "u")
      .str.replace("ñ", "n")
      .str.replace("(", "")
      .str.replace(")", "")
)

# -----------------------------
# Conversión de fecha (robusta)
# -----------------------------
col_fecha = None

if "fecha" in df.columns:
    col_fecha = "fecha"
elif "dia" in df.columns:
    col_fecha = "dia"

if col_fecha is None:
    st.error("No se encontró columna de fecha (fecha o dia)")
    st.write("Columnas detectadas:", df.columns)
    st.stop()

# Conversión inteligente
if pd.api.types.is_datetime64_any_dtype(df[col_fecha]):
    df["fecha"] = df[col_fecha]

elif pd.api.types.is_numeric_dtype(df[col_fecha]):
    df["fecha"] = pd.to_datetime(df[col_fecha], origin="1899-12-30", unit="D")

else:
    df["fecha"] = pd.to_datetime(df[col_fecha], dayfirst=True, errors="coerce")

df = df.dropna(subset=["fecha"])

# Aseguramos formato datetime limpio
df["fecha"] = pd.to_datetime(df["fecha"])


# =========================================================
# 🔵 FILTRO SEMANAL PROFESIONAL
# =========================================================
st.sidebar.subheader("📅 Filtro semanal")

df["anio"] = df["fecha"].dt.year
df["semana"] = df["fecha"].dt.isocalendar().week

# Generamos combinaciones únicas año-semana disponibles
semanas_disponibles = (
    df[["anio", "semana"]]
    .drop_duplicates()
    .sort_values(["anio", "semana"])
)

opciones = [
    f"{row.anio} - Semana {row.semana}"
    for _, row in semanas_disponibles.iterrows()
]

semana_sel = st.sidebar.selectbox(
    "Seleccionar semana",
    opciones,
    key=f"semana_{archivo_sel}"
)

# Extraemos año y semana seleccionados
anio_sel, semana_sel_num = semana_sel.split(" - Semana ")
anio_sel = int(anio_sel)
semana_sel_num = int(semana_sel_num)

df = df[
    (df["anio"] == anio_sel) &
    (df["semana"] == semana_sel_num)
]

# Botones rápidos
# -----------------------------
# Botones rápidos (modo semanal)
# -----------------------------
col1, col2, col3 = st.sidebar.columns(3)

with col1:
    btn_semana_actual = st.button("Semana actual")

with col2:
    btn_ult7 = st.button("Últimos 7d")

with col3:
    btn_todo = st.button("Todo")


# -----------------------------
# Lógica de filtrado
# -----------------------------
if btn_todo:
    df_filtrado = df.copy()

elif btn_ult7:
    fecha_fin = df["fecha"].max()
    fecha_inicio = fecha_fin - pd.Timedelta(days=7)
    df_filtrado = df[
        (df["fecha"] >= fecha_inicio) &
        (df["fecha"] <= fecha_fin)
    ]

elif btn_semana_actual:
    hoy = pd.Timestamp.today()
    semana_actual = hoy.isocalendar().week
    anio_actual = hoy.year

    df_filtrado = df[
        (df["anio"] == anio_actual) &
        (df["semana"] == semana_actual)
    ]

else:
    df_filtrado = df[
        (df["anio"] == anio_sel) &
        (df["semana"] == semana_sel_num)
    ]

# Reemplazamos el dataframe original por el filtrado
df = df_filtrado
# -----------------------------
# Vista inicial
# -----------------------------
with st.expander("🔍 Ver datos crudos (Excel completo)"):
    st.write(f"Filas: {df.shape[0]} · Columnas: {df.shape[1]}")
    st.dataframe(df)

col1, col2, col3 = st.columns(3)

col1.metric("Bultos totales", int(df["cantidad_total_bultos"].sum()))
col2.metric("Visitas planeadas", int(df["visitas_planeadas"].sum()))
col3.metric("Visitas realizadas", int(df["visitados"].sum()))

# -----------------------------
# Filtrado de días válidos de ruta
# Vacío = no corresponde al día
# 0 = mostrador (se incluye)
# -----------------------------
df_rutas_validas = df[
    df["visitas_planeadas"].notna()
]

# -----------------------------
# Asegurar columnas como texto
# -----------------------------
df_rutas_validas["ruta"] = df_rutas_validas["ruta"].astype(str)
df_rutas_validas["vendedor"] = df_rutas_validas["vendedor"].astype(str)
df_rutas_validas["localidad"] = df_rutas_validas["localidad"].astype(str)

# -----------------------------
# Vista por localidad
# -----------------------------
st.divider()
st.header("📍 Visitas por localidad")

tabla_localidad_visitas = (
    df_rutas_validas
    .groupby("localidad")
    .agg(
        visitas_planeadas=("visitas_planeadas", "sum"),
        visitas_realizadas=("visitados", "sum"),

        
        cantidad_rutas=("ruta", "nunique"),

        
        cantidad_vendedores=("vendedor", "nunique"),
    )
    .reset_index()
    .sort_values("visitas_planeadas", ascending=False)
)


st.dataframe(tabla_localidad_visitas, use_container_width=True)

st.divider()
st.header("📦 Volumen vendido por localidad")

tabla_volumen_localidad = (
    df_rutas_validas
    .groupby("localidad")
    .agg(
        bultos_vendidos=("cantidad_total_bultos", "sum"),
        visitas_planeadas=("visitas_planeadas", "sum"),
        visitas_realizadas=("visitados", "sum"),
        rutas=("ruta", "nunique"),
        vendedores=("vendedor", "nunique"),
    )
    .reset_index()
    .sort_values("bultos_vendidos", ascending=False)
)

st.dataframe(tabla_volumen_localidad, use_container_width=True)



st.divider()
st.header("🧾 Planificación, ejecución y ventas por ruta")

# -----------------------------
# Selector de vendedor
# -----------------------------
vendedor_sel = st.selectbox(
    "Seleccionar vendedor",
    sorted(df_rutas_validas["vendedor"].unique())
)

df_vendedor = df_rutas_validas[
    df_rutas_validas["vendedor"] == vendedor_sel
]

# -----------------------------
# Agregar día de la semana (según semana filtrada)
# -----------------------------
df_vendedor["dia_semana"] = (
    df_vendedor["fecha"]
    .dt.day_name()
    .replace({
        "Monday": "Lunes",
        "Tuesday": "Martes",
        "Wednesday": "Miércoles",
        "Thursday": "Jueves",
        "Friday": "Viernes",
        "Saturday": "Sábado",
        "Sunday": "Domingo"
    })
)

# -----------------------------
# Agrupación por ruta
# -----------------------------
tabla_clientes_compra = (
    df_vendedor
    .groupby("ruta")
    .agg(
        dia=("dia_semana", lambda x: ", ".join(sorted(x.unique()))),

        visitas_planeadas=("visitas_planeadas", "sum"),
        visitas_realizadas=("visitados", "sum"),

        clientes_con_compra_en_ruta=("venta_en_el_pdv", "sum"),
        clientes_con_compra_fuera_ruta=("venta_a_distancia", "sum"),

        bultos_vendidos=("cantidad_total_bultos", "sum"),
    )
    .reset_index()
)

# -----------------------------
# Totales y métricas derivadas
# -----------------------------
tabla_clientes_compra["clientes_con_compra_total"] = (
    tabla_clientes_compra["clientes_con_compra_en_ruta"] +
    tabla_clientes_compra["clientes_con_compra_fuera_ruta"]
)

tabla_clientes_compra["%_fuera_de_ruta"] = (
    tabla_clientes_compra["clientes_con_compra_fuera_ruta"] /
    tabla_clientes_compra["clientes_con_compra_total"]
).fillna(0).round(2)

tabla_clientes_compra = tabla_clientes_compra.sort_values(
    "clientes_con_compra_total",
    ascending=False
)

st.dataframe(tabla_clientes_compra, use_container_width=True)

st.subheader("📊 Planeado vs Realizado por ruta")

df_grafico = tabla_clientes_compra.melt(
    id_vars="ruta",
    value_vars=["visitas_planeadas", "visitas_realizadas"],
    var_name="tipo",
    value_name="cantidad"
)

# RUTA = CATEGORÍA
df_grafico["ruta"] = df_grafico["ruta"].astype(str)

df_grafico["tipo"] = df_grafico["tipo"].replace({
    "visitas_planeadas": "Planeadas",
    "visitas_realizadas": "Realizadas"
})

fig = px.bar(
    df_grafico,
    x="ruta",
    y="cantidad",
    color="tipo",
    barmode="group",
    labels={
        "ruta": "Ruta",
        "cantidad": "Visitas",
        "tipo": ""
    }
)

# 🔥 CLAVE ABSOLUTA: forzar eje categórico
fig.update_xaxes(
    type="category",
    categoryorder="array",
    categoryarray=sorted(df_grafico["ruta"].unique())
)

st.plotly_chart(fig, use_container_width=True)




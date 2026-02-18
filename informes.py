import pandas as pd
import streamlit as st

st.title("Informe de Fuerza de Ventas")

# ======================================================
# CONFIGURACIÓN
# ======================================================
EMPRESA_ACTUAL = "Aloma DISTRIBUIDORES OFICIALES"

# ======================================================
# CARGA DE ARCHIVOS
# ======================================================
general = pd.read_excel("General.xlsx")
visitas = pd.read_excel("visitas_aloma_2025_12.xlsx")
fuera = pd.read_excel("fuera_de_ruta_aloma_2025_12.xlsx")


# ======================================================
# NORMALIZAR COLUMNAS
# ======================================================
for df in [general, visitas, fuera]:
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

# ======================================================
# RENOMBRAR COLUMNAS CLAVE
# ======================================================
general = general.rename(columns={
    "ruta": "id_ruta",
    "cliente": "id_cliente_erp"
})

visitas = visitas.rename(columns={
    "sector": "vendedor",
    "f/h_foto": "fh_foto",
    "descripción_cliente": "descripcion_cliente"
})

fuera = fuera.rename(columns={
    "cliente": "id_cliente_erp"
})


# ======================================================
# LIMPIEZAS MENORES
# ======================================================
if "unnamed:_0" in visitas.columns:
    visitas = visitas.drop(columns=["unnamed:_0"])

if "unnamed:_0" in fuera.columns:
    fuera = fuera.drop(columns=["unnamed:_0"])

# ======================================================
# PREPARAR FECHAS
# ======================================================
visitas["fecha"] = pd.to_datetime(visitas["fecha"], errors="coerce")
fuera["fecha"] = pd.to_datetime(fuera["fecha"], errors="coerce")


# ======================================================
# FILTRAR GENERAL POR EMPRESA (CLAVE)
# ======================================================
general_empresa = general[general["empresa"] == EMPRESA_ACTUAL]

# ======================================================
# MAPA CLIENTE → VENDEDOR / RUTA (FUENTE DE VERDAD)
# ======================================================
mapa_cliente_vendedor = general_empresa[
    ["id_cliente_erp", "vendedor", "id_ruta"]
].drop_duplicates()

# ======================================================
# ---- VISITAS: FLAG DE ACCIÓN
# ======================================================
visitas["flag_visita"] = visitas["visitado"].str.lower() == "si"
visitas["flag_venta"] = visitas["hora_venta"].notna()
visitas["flag_motivo"] = visitas["hora_motivo"].notna()
visitas["flag_foto"] = visitas["fh_foto"].notna()

visitas["tiene_accion"] = (
    visitas["flag_visita"]
    | visitas["flag_venta"]
    | visitas["flag_motivo"]
    | visitas["flag_foto"]
)

acciones_visitas = (
    visitas
    .groupby(["id_cliente_erp", "vendedor"])
    .agg(accion_mes=("tiene_accion", "any"))
    .reset_index()
)

# ======================================================
# ---- FUERA DE RUTA: NORMALIZAR VENDEDOR POR RUTA
# ======================================================
fuera = fuera.merge(
    mapa_cliente_vendedor,
    on="id_cliente_erp",
    how="left"
)

fuera["accion_mes"] = True

acciones_fuera = fuera[
    ["id_cliente_erp", "vendedor", "accion_mes"]
].drop_duplicates()

# ======================================================
# UNIFICAR TODAS LAS ACCIONES DEL MES
# ======================================================
acciones_mes = pd.concat(
    [acciones_visitas, acciones_fuera],
    ignore_index=True
)

acciones_mes = (
    acciones_mes
    .groupby(["id_cliente_erp", "vendedor"])
    .agg(accion_mes=("accion_mes", "any"))
    .reset_index()
)

# ======================================================
# CRUZAR CONTRA CARTERA (GENERAL)
# ======================================================
base = general_empresa.merge(
    acciones_mes,
    on=["id_cliente_erp", "vendedor"],
    how="left"
)

base["accion_mes"] = base["accion_mes"].fillna(False)
base["estado"] = base["accion_mes"].map(
    lambda x: "ACTIVO" if x else "INACTIVO"
)

# ======================================================
# =======================
# VISUALIZACIONES
# =======================

st.subheader("Resumen por vendedor")

resumen_vendedor = (
    base
    .groupby("vendedor")
    .agg(
        rutas=("id_ruta", "nunique"),
        clientes_totales=("id_cliente_erp", "nunique"),
        clientes_inactivos=("estado", lambda x: (x == "INACTIVO").sum())
    )
    .reset_index()
)

st.dataframe(resumen_vendedor)

st.subheader("Clientes INACTIVOS (abandono real)")
st.dataframe(
    base[base["estado"] == "INACTIVO"][
        ["vendedor", "id_ruta", "id_cliente_erp"]
    ]
)
st.subheader("Detalle por vendedor y ruta")


resumen_ruta = (
    base
    .groupby(["vendedor", "id_ruta"])
    .agg(
        puntos_totales=("id_cliente_erp", "nunique"),
        puntos_activos=("estado", lambda x: (x == "ACTIVO").sum()),
        puntos_inactivos=("estado", lambda x: (x == "INACTIVO").sum()),
    )
    .reset_index()
)

st.markdown("### Filtro por vendedor")

vendedores = sorted(resumen_ruta["vendedor"].dropna().unique())
vendedor_sel = st.selectbox("Seleccionar vendedor", ["Todos"] + vendedores)

if vendedor_sel != "Todos":
    resumen_ruta = resumen_ruta[resumen_ruta["vendedor"] == vendedor_sel]


st.dataframe(
    resumen_ruta.sort_values(
        ["vendedor", "id_ruta"]
    ),
    use_container_width=True
)


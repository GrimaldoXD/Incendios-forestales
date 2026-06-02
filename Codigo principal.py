import geopandas as gpd
import folium
from folium.plugins import HeatMap
from datetime import datetime
import pandas as pd
import os

# ==============================
# CONFIG
# ==============================

SHP_PATH = "fire_archive_M-C61_738491.shp"

# ==============================
# 1. CARGAR SHAPEFILE
# ==============================

gdf = gpd.read_file(SHP_PATH)

print("Columnas disponibles:")
print(gdf.columns)

# ==============================
# 2. FILTRO COLOMBIA
# ==============================

gdf = gdf[
    (gdf.geometry.y >= -5) & (gdf.geometry.y <= 13) &
    (gdf.geometry.x >= -79) & (gdf.geometry.x <= -66)
]

# ==============================
# 3. DESCARGAR MUNICIPIOS SI NO EXISTEN
# ==============================

if not os.path.exists("gadm41_COL_2.shp"):

    import requests
    import zipfile

    print("Descargando municipios de Colombia...")

    url = "https://geodata.ucdavis.edu/gadm/gadm4.1/shp/gadm41_COL_shp.zip"

    r = requests.get(url)

    with open("municipios.zip", "wb") as f:
        f.write(r.content)

    with zipfile.ZipFile("municipios.zip", 'r') as zip_ref:
        zip_ref.extractall(".")

# ==============================
# 4. CARGAR MUNICIPIOS
# ==============================

municipios = gpd.read_file("gadm41_COL_2.shp")

municipios = municipios.to_crs(gdf.crs)

# ==============================
# 5. UNIÓN ESPACIAL
# ==============================

gdf = gpd.sjoin(
    gdf,
    municipios,
    how="left",
    predicate="within"
)

# ==============================
# 6. CREAR COLUMNAS
# ==============================

gdf["municipio"] = gdf["NAME_2"]
gdf["departamento"] = gdf["NAME_1"]

# ==============================
# 7. FILTRO CUNDINAMARCA
# ==============================

gdf = gdf[gdf["departamento"] == "Cundinamarca"]

print("Total incendios encontrados:", len(gdf))

# ==============================
# 8. DETECTAR COLUMNA CONFIANZA
# ==============================

col_conf = None

for c in gdf.columns:
    if "conf" in c.lower():
        col_conf = c
        break

print("Campo confianza detectado:", col_conf)

# ==============================
# 9. CLASIFICACIÓN DE RIESGO
# ==============================

def riesgo(row):

    if col_conf is None:
        return "Desconocido", "gray"

    val = row[col_conf]

    # SI ES TEXTO
    if isinstance(val, str):

        val = val.lower()

        if "low" in val:
            return "Bajo", "green"

        elif "nominal" in val:
            return "Medio", "orange"

        elif "high" in val:
            return "Alto", "red"

    # SI ES NUMÉRICO
    try:

        val = float(val)

        if val < 40:
            return "Bajo", "green"

        elif val < 70:
            return "Medio", "orange"

        else:
            return "Alto", "red"

    except:
        return "Desconocido", "gray"

# Aplicar clasificación
gdf[["riesgo", "color"]] = gdf.apply(
    lambda r: pd.Series(riesgo(r)),
    axis=1
)

# ==============================
# 10. CONTADORES
# ==============================

conteo = gdf["riesgo"].value_counts()

bajo = conteo.get("Bajo", 0)
medio = conteo.get("Medio", 0)
alto = conteo.get("Alto", 0)

# ==============================
# 11. CREAR MAPA
# ==============================

mapa = folium.Map(
    location=[4.7, -74.1],
    zoom_start=8
)

# ==============================
# 12. CAPA SATELITAL
# ==============================

folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    name="Satelital",
    attr="Esri"
).add_to(mapa)

# ==============================
# 13. HEATMAP
# ==============================

coords = [
    (geom.y, geom.x)
    for geom in gdf.geometry
]

heat = folium.FeatureGroup(
    name="Mapa térmico"
)

if coords:

    HeatMap(
        coords,
        radius=12,
        blur=15
    ).add_to(heat)

heat.add_to(mapa)

# ==============================
# 14. CAPAS POR RIESGO
# ==============================

grupo_bajo = folium.FeatureGroup(
    name=f"Bajo ({bajo})"
)

grupo_medio = folium.FeatureGroup(
    name=f"Medio ({medio})"
)

grupo_alto = folium.FeatureGroup(
    name=f"Alto ({alto})"
)

# ==============================
# 15. MARCADORES
# ==============================

for _, row in gdf.iterrows():

    popup_text = f"""
    <b>Municipio:</b> {row['municipio']}<br>
    <b>Departamento:</b> {row['departamento']}<br>
    <b>Riesgo:</b> {row['riesgo']}<br>
    """

    if col_conf is not None:
        popup_text += f"<b>Confianza:</b> {row[col_conf]}<br>"

    marker = folium.CircleMarker(
        location=[row.geometry.y, row.geometry.x],
        radius=6,
        color=row["color"],
        fill=True,
        fill_color=row["color"],
        fill_opacity=0.7,
        popup=popup_text
    )

    if row["riesgo"] == "Bajo":
        marker.add_to(grupo_bajo)

    elif row["riesgo"] == "Medio":
        marker.add_to(grupo_medio)

    elif row["riesgo"] == "Alto":
        marker.add_to(grupo_alto)

# Agregar grupos
grupo_bajo.add_to(mapa)
grupo_medio.add_to(mapa)
grupo_alto.add_to(mapa)

# ==============================
# 16. LEYENDA
# ==============================

legend = f"""
<div style="
position: fixed;
bottom: 50px;
left: 50px;
width: 230px;
background-color: white;
padding: 12px;
border:2px solid grey;
z-index:9999;
font-size:14px;
">

<b>🔥 Riesgo de incendios</b><br><br>

🟢 Bajo: {bajo}<br>
🟠 Medio: {medio}<br>
🔴 Alto: {alto}<br>

<hr>

<b>Total:</b> {len(gdf)}

</div>
"""

mapa.get_root().html.add_child(
    folium.Element(legend)
)

# ==============================
# 17. CONTROLES
# ==============================

folium.LayerControl().add_to(mapa)

# ==============================
# 18. EXPORTAR EXCEL
# ==============================

excel_df = pd.DataFrame({

    "Municipio": gdf["municipio"],
    "Departamento": gdf["departamento"],
    "Latitud": gdf.geometry.y,
    "Longitud": gdf.geometry.x,
    "Riesgo": gdf["riesgo"]

})

# Agregar confianza
if col_conf is not None:
    excel_df["Confianza"] = gdf[col_conf]

# Buscar fecha
for c in gdf.columns:

    if "date" in c.lower():

        excel_df["Fecha"] = gdf[c]
        break

# Nombre Excel
excel_nombre = f"analisis_incendios_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

# Guardar Excel
excel_df.to_excel(
    excel_nombre,
    index=False
)

print("Excel generado:", excel_nombre)

# ==============================
# 19. GUARDAR MAPA
# ==============================

nombre = f"mapa_cundinamarca_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"

mapa.save(nombre)

print("Mapa generado:", nombre)
print("Proceso finalizado correctamente.")
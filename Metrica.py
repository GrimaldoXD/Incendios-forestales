import geopandas as gpd
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix
)

# ==========================
# CARGAR SHAPEFILE
# ==========================

gdf = gpd.read_file("fire_archive_M-C61_738491.shp")

# ==========================
# CREAR CLASES DE RIESGO
# ==========================

def clasificar_riesgo(conf):

    if conf < 40:
        return 0   # Bajo

    elif conf < 70:
        return 1   # Medio

    else:
        return 2   # Alto

gdf["RIESGO"] = gdf["CONFIDENCE"].apply(clasificar_riesgo)

# ==========================
# VARIABLES DE ENTRADA
# ==========================

X = gdf[
    [
        "BRIGHTNESS",
        "SCAN",
        "TRACK",
        "BRIGHT_T31",
        "FRP"
    ]
]

y = gdf["RIESGO"]

# ==========================
# ENTRENAMIENTO / PRUEBA
# ==========================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42
)

# ==========================
# RANDOM FOREST
# ==========================

modelo = RandomForestClassifier(
    n_estimators=100,
    random_state=42
)

modelo.fit(X_train, y_train)

# ==========================
# PREDICCIÓN
# ==========================

y_pred = modelo.predict(X_test)

# ==========================
# MÉTRICAS
# ==========================

accuracy = accuracy_score(y_test, y_pred)

precision = precision_score(
    y_test,
    y_pred,
    average="weighted"
)

recall = recall_score(
    y_test,
    y_pred,
    average="weighted"
)

f1 = f1_score(
    y_test,
    y_pred,
    average="weighted"
)

print("\n===== MÉTRICAS =====\n")

print("Accuracy :", round(accuracy,4))
print("Precision:", round(precision,4))
print("Recall   :", round(recall,4))
print("F1 Score :", round(f1,4))

print("\n===== MATRIZ DE CONFUSIÓN =====\n")
print(confusion_matrix(y_test, y_pred))

print("\n===== REPORTE =====\n")
print(classification_report(y_test, y_pred))
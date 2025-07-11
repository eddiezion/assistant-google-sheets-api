from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.openapi.utils import get_openapi
from fastapi import Query
from typing import List

import gspread
from google.oauth2.service_account import Credentials
from unidecode import unidecode

app = FastAPI()

# === CONFIGURATION GOOGLE SHEETS ===
SPREADSHEET_KEY = "1hao5XqJ9MTY-tYVu7YKwwodf5AD0K_ezGLVuv7GJf54"  # ID exact du fichier
CREDENTIALS_FILE = "/etc/secrets/credentials.json"

scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
client = gspread.authorize(creds)

# === UTILS ===
def normalize(text: str) -> str:
    return unidecode(text.strip().lower())

def get_worksheet(nom_feuille: str):
    try:
        return client.open_by_key(SPREADSHEET_KEY).worksheet(nom_feuille)
    except Exception:
        raise ValueError(f"Feuille '{nom_feuille}' introuvable dans le fichier.")
        
# === MODELES ===
class Entry(BaseModel):
    valeur: str
    feuille: str = "Sheet1"

class UpdateEntry(BaseModel):
    ancienne_valeur: str
    nouvelle_valeur: str
    feuille: str = "Sheet1"

class UpdateCell(BaseModel):
    nom: str
    colonne: str
    valeur: str
    feuille: str = "Sheet1"
    colonne_reference: str = "Nom"

# === ROUTES ===

@app.get("/")
def home():
    return {"message": "API connectée à Google Sheets ✅"}

@app.get("/preview")
def preview(feuille: str = "Sheet1"):
    try:
        ws = get_worksheet(feuille)
        data = ws.get_all_records()
        return {"extrait": data[:5]}
    except Exception as e:
        return {"error": str(e)}

@app.get("/list-sheets")
def list_sheets():
    try:
        spreadsheet = client.open(SHEET_NAME)
        spreadsheet._sheet_list = None  # force refresh
        feuilles = spreadsheet.worksheets()
        noms = [ws.title for ws in feuilles]
        return {
            "feuilles_accessibles": noms,
            "message": f"Feuilles disponibles : {', '.join(noms)}"
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/get-lines")
def get_lines(feuille: str = "Sheet1", start: int = 6, end: int = 20):
    try:
        ws = get_worksheet(feuille)
        data = ws.get_all_values()
        headers = data[0]
        selected_rows = data[start - 1:end]  # 1-based → 0-indexed
        result = [dict(zip(headers, row)) for row in selected_rows if any(row)]
        return {
            "plage": f"Lignes {start} à {end}",
            "données": result
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/add-entry")
def add_entry(entry: Entry):
    try:
        ws = get_worksheet(entry.feuille)
        valeur = normalize(entry.valeur)
        lignes = [normalize(v) for v in ws.col_values(1)]
        if valeur in lignes:
            return {"status": "success", "message": "Déjà présente"}
        ws.append_row([entry.valeur])
        return {"status": "success", "message": "Ajoutée avec succès"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/update-entry")
def update_entry(update: UpdateEntry):
    try:
        ws = get_worksheet(update.feuille)
        ancienne = normalize(update.ancienne_valeur)
        nouvelle = update.nouvelle_valeur.strip()
        lignes = [normalize(v) for v in ws.col_values(1)]
        if ancienne not in lignes:
            return {"status": "error", "message": "Ancienne valeur introuvable"}
        index = lignes.index(ancienne) + 1
        ws.update_cell(index, 1, nouvelle)
        return {"status": "success", "message": f"{update.ancienne_valeur} remplacée par {nouvelle}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/update-cell")
def update_cell(data: UpdateCell):
    try:
        ws = get_worksheet(data.feuille)
        headers = ws.row_values(1)

        if data.colonne not in headers:
            return {"status": "error", "message": f"Colonne à modifier '{data.colonne}' introuvable"}
        if data.colonne_reference not in headers:
            return {"status": "error", "message": f"Colonne de recherche '{data.colonne_reference}' introuvable"}

        col_modif_index = headers.index(data.colonne) + 1
        col_ref_index = headers.index(data.colonne_reference) + 1

        valeurs_ref = ws.col_values(col_ref_index)
        valeurs_ref_normalisées = [normalize(v) for v in valeurs_ref]
        nom_normalise = normalize(data.nom)

        if nom_normalise not in valeurs_ref_normalisées:
            return {
                "status": "error",
                "message": f"'{data.nom}' introuvable dans la colonne '{data.colonne_reference}'"
            }

        row_index = valeurs_ref_normalisées.index(nom_normalise) + 1
        ws.update_cell(row_index, col_modif_index, data.valeur.strip())

        return {
            "status": "success",
            "message": f"✅ Cellule modifiée : {data.colonne} de '{data.nom}' → {data.valeur}"
        }

    except Exception as e:
        return {"status": "error", "message": f"Erreur : {str(e)}"}

# === OPENAPI POUR GPT ===
def custom_openapi():
    openapi_schema = get_openapi(
        title="Assistant Google Sheets API",
        version="1.0.0",
        description="API pour manipuler dynamiquement des feuilles Google Sheets via GPT",
        routes=app.routes,
    )
    openapi_schema["servers"] = [
        {"url": "https://assistant-google-sheets-api.onrender.com"}
    ]
    return openapi_schema

app.openapi = custom_openapi

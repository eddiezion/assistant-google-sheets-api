from fastapi import FastAPI
from pydantic import BaseModel
import gspread
from google.oauth2.service_account import Credentials
from unidecode import unidecode
from fastapi.openapi.utils import get_openapi

app = FastAPI()

# === CONFIGURATION GOOGLE SHEETS ===
SHEET_NAME = "Chatgpt_Freelances"
CREDENTIALS_FILE = "/etc/secrets/credentials.json"

scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
client = gspread.authorize(creds)

# === UTILITAIRES ===
def normalize(text: str) -> str:
    return unidecode(text.strip().lower())

def get_worksheet(nom_feuille: str):
    try:
        return client.open(SHEET_NAME).worksheet(nom_feuille)
    except Exception:
        raise ValueError(f"Feuille '{nom_feuille}' introuvable.")

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
        feuilles = client.open(SHEET_NAME).worksheets()
        return {"feuilles_accessibles": [ws.title for ws in feuilles]}
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
            return {"status": "error", "message": f"Colonne '{data.colonne}' introuvable"}
        col_index = headers.index(data.colonne) + 1
        noms_originaux = ws.col_values(1)
        noms_normalises = [normalize(n) for n in noms_originaux]
        nom_normalise = normalize(data.nom)
        if nom_normalise not in noms_normalises:
            return {"status": "error", "message": f"Nom '{data.nom}' introuvable dans la colonne A"}
        row_index = noms_normalises.index(nom_normalise) + 1
        ws.update_cell(row_index, col_index, data.valeur.strip())
        return {"status": "success", "message": f"Cellule mise à jour pour '{data.nom}' → {data.colonne} = {data.valeur}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# === SCHEMA OPENAPI POUR GPT ===
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

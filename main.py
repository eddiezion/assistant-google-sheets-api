from fastapi import FastAPI
from pydantic import BaseModel
import gspread
from google.oauth2.service_account import Credentials
from unidecode import unidecode
from fastapi.openapi.utils import get_openapi

app = FastAPI()

# === CONFIGURATION ===
SHEET_NAME = "Chatgpt_Freelances"
CREDENTIALS_FILE = "/etc/secrets/credentials.json"

# === GOOGLE SHEETS AUTHENTIFICATION ===
scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).sheet1

# === UTILITAIRES ===
def normalize(text: str) -> str:
    return unidecode(text.strip().lower())

def get_headers():
    return sheet.row_values(1)

def get_col_index(col_name: str) -> int:
    headers = get_headers()
    if col_name not in headers:
        raise ValueError(f"Colonne '{col_name}' introuvable")
    return headers.index(col_name) + 1

def get_row_index_by_name(nom_normalise: str) -> int:
    noms = sheet.col_values(1)
    noms_normalises = [normalize(n) for n in noms]
    if nom_normalise not in noms_normalises:
        return -1
    return noms_normalises.index(nom_normalise) + 1

# === MODELES ===
class Entry(BaseModel):
    valeur: str

class UpdateEntry(BaseModel):
    ancienne_valeur: str
    nouvelle_valeur: str

class UpdateCell(BaseModel):
    nom: str
    colonne: str
    valeur: str

# === ROUTES ===
@app.get("/")
def home():
    return {"message": "API connectée à Google Sheets ✅"}

@app.get("/preview")
def preview():
    data = sheet.get_all_records()
    return {"extrait": data[:5]}

@app.get("/list-sheets")
def list_sheets():
    try:
        spreadsheets = client.openall()
        return {"feuilles_accessibles": [s.title for s in spreadsheets]}
    except Exception as e:
        return {"error": str(e)}

@app.post("/add-entry")
def add_entry(entry: Entry):
    valeur = normalize(entry.valeur)
    existants = [normalize(v) for v in sheet.col_values(1)]
    if valeur in existants:
        return {"status": "success", "message": "Déjà présente"}
    sheet.append_row([entry.valeur])
    return {"status": "success", "message": "Ajoutée avec succès"}

@app.post("/update-entry")
def update_entry(update: UpdateEntry):
    ancienne = normalize(update.ancienne_valeur)
    nouvelle = update.nouvelle_valeur.strip()
    existants = [normalize(v) for v in sheet.col_values(1)]

    if ancienne not in existants:
        return {"status": "error", "message": "Ancienne valeur introuvable"}

    index = existants.index(ancienne) + 1
    sheet.update_cell(index, 1, nouvelle)

    return {
        "status": "success",
        "message": f"{update.ancienne_valeur} remplacée par {nouvelle}"
    }

@app.post("/update-cell")
def update_cell(data: UpdateCell):
    try:
        nom = normalize(data.nom)
        col_index = get_col_index(data.colonne)
        row_index = get_row_index_by_name(nom)

        if row_index == -1:
            return {
                "status": "error",
                "message": f"Nom '{data.nom}' introuvable dans la première colonne"
            }

        sheet.update_cell(row_index, col_index, data.valeur.strip())

        return {
            "status": "success",
            "message": f"Cellule mise à jour pour '{data.nom}' → {data.colonne} = {data.valeur}"
        }

    except ValueError as ve:
        return {"status": "error", "message": str(ve)}

    except Exception as e:
        return {"status": "error", "message": f"Erreur interne : {str(e)}"}
    
@app.get("/openapi.json", include_in_schema=False)
def custom_openapi():
    openapi_schema = get_openapi(
        title="Assistant Google Sheets API",
        version="1.0.0",
        description="API pour manipuler des données Google Sheets via GPT",
        routes=app.routes,
    )
    openapi_schema["servers"] = [
        {"url": "https://assistant-google-sheets-api.onrender.com"}
    ]
    return openapi_schema
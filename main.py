from fastapi import FastAPI
from pydantic import BaseModel
import gspread
from google.oauth2.service_account import Credentials
from unidecode import unidecode  # 🔄 pour normaliser les noms

app = FastAPI()

SHEET_NAME = "Chatgpt_Freelances"
CREDENTIALS_FILE = "/etc/secrets/credentials.json"

# Connexion Google Sheets
scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).sheet1

# Modèles
class Entry(BaseModel):
    valeur: str

class UpdateEntry(BaseModel):
    ancienne_valeur: str
    nouvelle_valeur: str

class UpdateCell(BaseModel):
    nom: str
    colonne: str
    valeur: str

def normalize(text: str) -> str:
    return unidecode(text.strip().lower())

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
        noms = [s.title for s in spreadsheets]
        return {"feuilles_accessibles": noms}
    except Exception as e:
        return {"error": str(e)}

@app.post("/add-entry")
def add_entry(entry: Entry):
    valeur = entry.valeur.strip().lower()
    lignes = [v.strip().lower() for v in sheet.col_values(1)]
    if valeur in lignes:
        return {"status": "success", "message": "Déjà présente"}
    sheet.append_row([valeur])
    return {"status": "success", "message": "Ajoutée avec succès"}

@app.post("/update-entry")
def update_entry(update: UpdateEntry):
    ancienne = update.ancienne_valeur.strip().lower()
    nouvelle = update.nouvelle_valeur.strip().lower()
    lignes = [v.strip().lower() for v in sheet.col_values(1)]
    if ancienne not in lignes:
        return {"status": "error", "message": "Ancienne valeur introuvable"}
    index = lignes.index(ancienne) + 1
    sheet.update_cell(index, 1, nouvelle)
    return {"status": "success", "message": f"{ancienne} remplacée par {nouvelle}"}

@app.post("/update-cell")
def update_cell(data: UpdateCell):
    nom = normalize(data.nom)
    col_name = data.colonne.strip()
    nouvelle_valeur = data.valeur.strip()

    # Récupérer les en-têtes
    headers = sheet.row_values(1)
    if col_name not in headers:
        return {"status": "error", "message": f"Colonne '{col_name}' introuvable"}

    col_index = headers.index(col_name) + 1

    noms_originaux = sheet.col_values(1)
    noms_normalises = [normalize(n) for n in noms_originaux]

    if nom not in noms_normalises:
        return {"status": "error", "message": f"Nom '{data.nom}' introuvable dans la colonne A"}

    row_index = noms_normalises.index(nom) + 1
    sheet.update_cell(row_index, col_index, nouvelle_valeur)

    return {
        "status": "success",
        "message": f"Cellule mise à jour pour '{data.nom}' → {col_name} = {nouvelle_valeur}"
    }

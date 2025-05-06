from fastapi import FastAPI
from pydantic import BaseModel
import gspread
from google.oauth2.service_account import Credentials

app = FastAPI()

# 🔑 Authentification Google Sheets
SHEET_NAME = "Chatgpt_Freelances"  # <-- Mets ici le nom exact de ta feuille Google Sheets
CREDENTIALS_FILE = "credentials.json"

scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).sheet1

# 📦 Modèles de données
class Entry(BaseModel):
    valeur: str

class UpdateEntry(BaseModel):
    ancienne_valeur: str
    nouvelle_valeur: str

@app.get("/")
def home():
    return {"message": "API connectée à Google Sheets ✅"}

@app.get("/preview")
def preview():
    data = sheet.get_all_records()
    return {"extrait": data[:5]}

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
    
    index = lignes.index(ancienne) + 1  # gspread est 1-indexé
    sheet.update_cell(index, 1, nouvelle)
    return {"status": "success", "message": f"{ancienne} remplacée par {nouvelle}"}


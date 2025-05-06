from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Entry(BaseModel):
    valeur: str

@app.get("/")
def home():
    return {"message": "API opérationnelle"}

@app.post("/add-entry")
def add_entry(entry: Entry):
    valeur = entry.valeur.strip().lower()
    if valeur == "test@example.com":
        return {"status": "success", "message": "Déjà présente"}
    return {"status": "success", "message": "Ajoutée avec succès"}

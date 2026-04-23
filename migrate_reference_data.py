import os
import pickle
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient, UpdateOne

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "immopro")

if not MONGO_URI:
    raise ValueError("MONGO_URI est manquante dans l'environnement.")

BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"


def to_python_types(record: dict) -> dict:
    clean = {}
    for key, value in record.items():
        if hasattr(value, "item"):
            clean[key] = value.item()
        else:
            clean[key] = value
    return clean


def import_properties(db):
    path = MODELS_DIR / "df_reference.pkl"
    with open(path, "rb") as f:
        df = pickle.load(f)

    records = df.to_dict(orient="records")
    records = [to_python_types(r) for r in records]

    col = db["properties"]
    col.delete_many({})

    batch_size = 5000
    total = len(records)

    for i in range(0, total, batch_size):
        batch = records[i:i + batch_size]
        col.insert_many(batch)
        print(f"[properties] {min(i + batch_size, total)}/{total} insérés")

    print(f"[properties] import terminé : {total} documents")


def import_communes(db):
    path = MODELS_DIR / "df_communes.pkl"
    with open(path, "rb") as f:
        df = pickle.load(f)

    df = df.reset_index()  # récupère code_commune depuis l'index
    records = df.to_dict(orient="records")
    records = [to_python_types(r) for r in records]

    col = db["communes"]
    col.delete_many({})

    operations = []
    for record in records:
        code_commune = record["code_commune"]
        operations.append(
            UpdateOne(
                {"code_commune": code_commune},
                {"$set": record},
                upsert=True
            )
        )

    if operations:
        col.bulk_write(operations)

    print(f"[communes] import terminé : {len(records)} documents")


def main():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    db = client[DB_NAME]

    print(f"Connecté à MongoDB : {DB_NAME}")

    import_properties(db)
    import_communes(db)

    print("Migration terminée.")


if __name__ == "__main__":
    main()
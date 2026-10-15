"""Tiny NoSQL document store. MongoDB if MONGO_URI is set, else JSON files (zero-setup dev)."""
import json, os, re
from pathlib import Path

class FileStore:
    def __init__(self, root): self.root = Path(root)
    def _p(self, coll, key):
        d = self.root / coll; d.mkdir(parents=True, exist_ok=True)
        return d / (re.sub(r"[^\w.\-]", "_", key) + ".json")
    def get(self, coll, key):
        p = self._p(coll, key)
        return json.loads(p.read_text()) if p.exists() else None
    def put(self, coll, key, doc):
        p = self._p(coll, key); tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(doc)); tmp.replace(p)

class MongoStore:
    def __init__(self, uri):
        from pymongo import MongoClient
        self.db = MongoClient(uri, serverSelectionTimeoutMS=5000)[os.getenv("MONGO_DB", "climate")]
    def get(self, coll, key): return self.db[coll].find_one({"_id": key})
    def put(self, coll, key, doc):
        self.db[coll].replace_one({"_id": key}, {**doc, "_id": key}, upsert=True)

def get_store():
    uri = os.getenv("MONGO_URI")
    return MongoStore(uri) if uri else FileStore(os.getenv("DATA_DIR", "./data"))

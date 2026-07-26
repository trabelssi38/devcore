# qdrant_server.py -- DEV_CORE v10.0 Native Python Qdrant Vector Engine
# Port : 6333 (Fallthrough/Native Qdrant replacement without Docker)

import http.server
import json
import os
import math
import sys
from pathlib import Path

DEV_CORE_DATA = os.environ.get("DEVCORE_DATA_ROOT", str(Path(__file__).resolve().parents[3] / "DEV_CORE_DATA"))
STORAGE_FILE = Path(DEV_CORE_DATA) / "Runtime" / "qdrant_storage.json"

DEFAULT_COLLECTIONS = ["decisions", "lessons", "patterns", "codebase", "rules"]

class QdrantStore:
    def __init__(self):
        self.collections = {}
        self.load()

    def load(self):
        if STORAGE_FILE.exists():
            try:
                data = json.loads(STORAGE_FILE.read_text(encoding="utf-8"))
                self.collections = data.get("collections", {})
            except Exception:
                self.collections = {}
        for col in DEFAULT_COLLECTIONS:
            if col not in self.collections:
                self.collections[col] = {
                    "vector_size": 768,
                    "distance": "Cosine",
                    "points": {}
                }
        self.save()

    def save(self):
        try:
            os.makedirs(STORAGE_FILE.parent, exist_ok=True)
            STORAGE_FILE.write_text(json.dumps({"collections": self.collections}, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[QdrantServer] Save failed: {e}")

    def create_collection(self, name, size=768, distance="Cosine"):
        if name not in self.collections:
            self.collections[name] = {
                "vector_size": size,
                "distance": distance,
                "points": {}
            }
        else:
            self.collections[name]["vector_size"] = size
            self.collections[name]["distance"] = distance
        self.save()

    def delete_collection(self, name):
        if name in self.collections:
            del self.collections[name]
            self.save()

    def upsert_points(self, collection_name, points_list):
        if collection_name not in self.collections:
            self.create_collection(collection_name)
        col = self.collections[collection_name]
        for p in points_list:
            pid = str(p.get("id"))
            col["points"][pid] = {
                "id": p.get("id"),
                "vector": p.get("vector", []),
                "payload": p.get("payload", {})
            }
        self.save()

    def search(self, collection_name, query_vector, limit=10, with_payload=True):
        if collection_name not in self.collections:
            return []
        col = self.collections[collection_name]
        results = []
        
        def cosine_similarity(v1, v2):
            if not v1 or not v2 or len(v1) != len(v2):
                return 0.0
            dot = sum(a * b for a, b in zip(v1, v2))
            norm1 = math.sqrt(sum(a * a for a in v1))
            norm2 = math.sqrt(sum(b * b for b in v2))
            if norm1 == 0 or norm2 == 0:
                return 0.0
            return dot / (norm1 * norm2)

        for pid, pdata in col["points"].items():
            vec = pdata.get("vector", [])
            score = cosine_similarity(query_vector, vec)
            item = {"id": pdata["id"], "score": score}
            if with_payload:
                item["payload"] = pdata.get("payload", {})
            results.append(item)
            
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

store = QdrantStore()

class QdrantHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Quiet logs

    def send_json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0].rstrip("/")
        if path == "" or path == "/":
            return self.send_json({"title": "qdrant - vector search engine", "version": "1.8.0"})
        if path == "/collections":
            colls = [{"name": c} for c in store.collections.keys()]
            return self.send_json({"result": {"collections": colls}, "status": "ok", "time": 0.001})
        if path.startswith("/collections/"):
            col_name = path[len("/collections/"):]
            if col_name not in store.collections:
                store.create_collection(col_name, size=768, distance="Cosine")
            col = store.collections[col_name]
            pts = col["points"]
            return self.send_json({
                "result": {
                    "status": "green",
                    "vectors_count": len(pts),
                    "indexed_vectors_count": len(pts),
                    "points_count": len(pts),
                    "segments_count": 1,
                    "config": {
                        "params": {
                            "vectors": {
                                "size": col.get("vector_size", 768),
                                "distance": col.get("distance", "Cosine")
                            }
                        }
                    }
                },
                "status": "ok"
            })
        return self.send_json({"status": "error", "error": "Not found"}, 404)

    def do_PUT(self):
        path = self.path.split("?")[0].rstrip("/")
        content_length = int(self.headers.get("Content-Length", 0))
        body_data = {}
        if content_length > 0:
            try:
                body_data = json.loads(self.rfile.read(content_length).decode("utf-8"))
            except Exception:
                pass

        if path.startswith("/collections/") and path.endswith("/points"):
            parts = path.split("/")
            col_name = parts[2]
            points = body_data.get("points", [])
            store.upsert_points(col_name, points)
            return self.send_json({"result": {"operation_id": 1, "status": "completed"}, "status": "ok"})
            
        if path.startswith("/collections/"):
            col_name = path[len("/collections/"):]
            vectors_cfg = body_data.get("vectors", {})
            size = 768
            distance = "Cosine"
            if isinstance(vectors_cfg, dict):
                size = vectors_cfg.get("size", 768)
                distance = vectors_cfg.get("distance", "Cosine")
            store.create_collection(col_name, size, distance)
            return self.send_json({"result": True, "status": "ok"})

        return self.send_json({"status": "error", "error": "Not found"}, 404)

    def do_POST(self):
        path = self.path.split("?")[0].rstrip("/")
        content_length = int(self.headers.get("Content-Length", 0))
        body_data = {}
        if content_length > 0:
            try:
                body_data = json.loads(self.rfile.read(content_length).decode("utf-8"))
            except Exception:
                pass

        if path.startswith("/collections/") and (path.endswith("/points/search") or path.endswith("/points/scroll")):
            parts = path.split("/")
            col_name = parts[2]
            vec = body_data.get("vector", [])
            limit = body_data.get("limit", 10)
            with_payload = body_data.get("with_payload", True)
            res = store.search(col_name, vec, limit, with_payload)
            if path.endswith("/points/scroll"):
                return self.send_json({"result": {"points": res}, "status": "ok"})
            return self.send_json({"result": res, "status": "ok"})

        if path.startswith("/collections/") and path.endswith("/points"):
            parts = path.split("/")
            col_name = parts[2]
            points = body_data.get("points", [])
            store.upsert_points(col_name, points)
            return self.send_json({"result": {"operation_id": 1, "status": "completed"}, "status": "ok"})

        return self.send_json({"status": "error", "error": "Not found"}, 404)

    def do_DELETE(self):
        path = self.path.split("?")[0].rstrip("/")
        if path.startswith("/collections/"):
            col_name = path[len("/collections/"):]
            store.delete_collection(col_name)
            return self.send_json({"result": True, "status": "ok"})
        return self.send_json({"status": "error", "error": "Not found"}, 404)

if __name__ == "__main__":
    bind_host = os.environ.get("DEVCORE_QDRANT_BIND", "127.0.0.1")
    port = 6333
    print(f"Demarrage du service Qdrant natif Python sur {bind_host}:{port}...")
    server_class = http.server.HTTPServer
    if hasattr(http.server, "ThreadingHTTPServer"):
        server_class = http.server.ThreadingHTTPServer
    server = server_class((bind_host, port), QdrantHandler)
    server.serve_forever()

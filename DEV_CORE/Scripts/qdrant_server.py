# qdrant_server.py -- DEV_CORE v10.0 Native Python Qdrant Vector Engine
# Port : 6333 (Fallthrough/Native Qdrant replacement without Docker)

import http.server
import json
import os
import math
import sys
import copy
import tempfile
import threading
from functools import wraps
from pathlib import Path

DEV_CORE_DATA = os.environ.get("DEVCORE_DATA_ROOT", str(Path(__file__).resolve().parents[3] / "DEV_CORE_DATA"))
STORAGE_FILE = Path(DEV_CORE_DATA) / "Runtime" / "qdrant_storage.json"

DEFAULT_COLLECTIONS = ["decisions", "lessons", "patterns", "codebase", "rules"]

STORE_LOCK = threading.RLock()


def guarded(operation):
    @wraps(operation)
    def call(*args, **kwargs):
        with STORE_LOCK:
            return operation(*args, **kwargs)
    return call


def normalized_vector(vector, size):
    """Reject incompatible vectors; normalize before multiplication to avoid overflow."""
    try:
        if not isinstance(vector, list) or len(vector) != size:
            raise ValueError("invalid_vector")
        if any(type(value) not in (int, float) or not math.isfinite(value) for value in vector):
            raise ValueError("invalid_vector")
        norm = math.hypot(*vector)
        if not math.isfinite(norm) or norm == 0:
            raise ValueError("invalid_vector")
        return [value / norm for value in vector]
    except (OverflowError, TypeError):
        raise ValueError("invalid_vector") from None

class QdrantStore:
    def __init__(self, storage_file=None):
        self.storage_file = Path(storage_file) if storage_file is not None else STORAGE_FILE
        self.collections = {}
        self.load_error = False
        self.load()

    @guarded
    def load(self):
        if self.storage_file.exists():
            try:
                data = json.loads(self.storage_file.read_text(encoding="utf-8"))
                collections = data["collections"]
                if not isinstance(collections, dict):
                    raise ValueError("invalid_store")
                for name, col in collections.items():
                    self.validate_config(name, col["vector_size"], col["distance"])
                    if not isinstance(col["points"], dict):
                        raise ValueError("invalid_store")
                self.collections = collections
                self.load_error = False
            except (OSError, ValueError, KeyError, TypeError, RecursionError):
                self.load_error = True
                return  # Keep the file intact; never reset a corrupt store.
        for col in DEFAULT_COLLECTIONS:
            if col not in self.collections:
                self.collections[col] = {
                    "vector_size": 768,
                    "distance": "Cosine",
                    "points": {}
                }

    def ensure_available(self):
        if self.load_error:
            raise RuntimeError("storage_unavailable")

    @staticmethod
    def validate_config(name, size, distance):
        if not isinstance(name, str) or not name or type(size) is not int or not 1 <= size <= 4096 or distance != "Cosine":
            raise ValueError("unsupported_collection_config")

    def save(self, collections):
        self.ensure_available()
        temporary = None
        try:
            self.storage_file.parent.mkdir(parents=True, exist_ok=True)
            content = json.dumps({"collections": collections}, indent=2, allow_nan=False)
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.storage_file.parent, delete=False) as handle:
                temporary = Path(handle.name)
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.storage_file)
            self.collections = collections
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    @guarded
    def create_collection(self, name, size=768, distance="Cosine"):
        self.ensure_available()
        self.validate_config(name, size, distance)
        collections = copy.deepcopy(self.collections)
        if name not in collections:
            collections[name] = {
                "vector_size": size,
                "distance": distance,
                "points": {}
            }
        else:
            existing = collections[name]
            if existing["vector_size"] == size and existing["distance"] == distance:
                return
            if existing["points"]:
                raise ValueError("collection_config_conflict")
            existing["vector_size"] = size
            existing["distance"] = distance
        self.save(collections)

    @guarded
    def delete_collection(self, name):
        self.ensure_available()
        if name in self.collections:
            collections = copy.deepcopy(self.collections)
            del collections[name]
            self.save(collections)

    @guarded
    def upsert_points(self, collection_name, points_list):
        self.ensure_available()
        if collection_name not in self.collections:
            raise KeyError("collection_not_found")
        if not isinstance(points_list, list):
            raise ValueError("invalid_points")
        collections = copy.deepcopy(self.collections)
        col = collections[collection_name]
        for p in points_list:
            if not isinstance(p, dict) or type(p.get("id")) not in (str, int) or not isinstance(p.get("payload", {}), dict):
                raise ValueError("invalid_point")
            normalized_vector(p.get("vector"), col["vector_size"])
            pid = str(p.get("id"))
            col["points"][pid] = {
                "id": p.get("id"),
                "vector": p.get("vector", []),
                "payload": p.get("payload", {})
            }
        self.save(collections)

    @guarded
    def search(self, collection_name, query_vector, limit=10, with_payload=True):
        self.ensure_available()
        if collection_name not in self.collections:
            raise KeyError("collection_not_found")
        if type(limit) is not int or not 1 <= limit <= 1000 or type(with_payload) is not bool:
            raise ValueError("invalid_search_arguments")
        col = self.collections[collection_name]
        query = normalized_vector(query_vector, col["vector_size"])
        results = []

        for pid, pdata in col["points"].items():
            try:
                vec = normalized_vector(pdata["vector"], col["vector_size"])
                if type(pdata["id"]) not in (str, int) or not isinstance(pdata.get("payload", {}), dict):
                    raise ValueError("invalid_point")
            except (ValueError, KeyError, TypeError):
                raise RuntimeError("stored_vector_invalid") from None
            score = max(-1.0, min(1.0, math.fsum(a * b for a, b in zip(query, vec))))
            item = {"id": pdata["id"], "score": score}
            if with_payload:
                item["payload"] = pdata.get("payload", {})
            results.append(item)
            
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    @guarded
    def scroll(self, collection_name, limit=10, with_payload=True):
        self.ensure_available()
        if type(limit) is not int or not 1 <= limit <= 1000 or type(with_payload) is not bool:
            raise ValueError("invalid_scroll_arguments")
        col = self.collections[collection_name]
        if len(col["points"]) > limit:
            raise ValueError("scroll_pagination_unsupported")
        return [{"id": point["id"], **({"payload": point.get("payload", {})} if with_payload else {})}
                for point in list(col["points"].values())[:limit]]

store = QdrantStore()


def api_guard(operation):
    @wraps(operation)
    def call(handler):
        try:
            with STORE_LOCK:
                store.ensure_available()
                return operation(handler)
        except (ValueError, RecursionError):
            return handler.send_json({"status": "error", "error": "invalid_request"}, 400)
        except KeyError:
            return handler.send_json({"status": "error", "error": "collection_not_found"}, 404)
        except (RuntimeError, OSError):
            return handler.send_json({"status": "error", "error": "storage_unavailable"}, 503)
    return call

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

    @api_guard
    def do_GET(self):
        path = self.path.split("?")[0].rstrip("/")
        if path == "" or path == "/":
            return self.send_json({"title": "DevCore local vector simulator", "simulator": True})
        if path == "/collections":
            colls = [{"name": c} for c in store.collections.keys()]
            return self.send_json({"result": {"collections": colls}, "status": "ok", "time": 0.001})
        if path.startswith("/collections/"):
            col_name = path[len("/collections/"):]
            if col_name not in store.collections:
                return self.send_json({"status": "error", "error": "collection_not_found"}, 404)
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

    def read_body(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if not 0 < content_length <= 2 * 1024 * 1024:
            raise ValueError("invalid_body_size")
        body = json.loads(self.rfile.read(content_length).decode("utf-8"))
        if not isinstance(body, dict):
            raise ValueError("invalid_body")
        return body

    @api_guard
    def do_PUT(self):
        path = self.path.split("?")[0].rstrip("/")
        body_data = self.read_body()

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

    @api_guard
    def do_POST(self):
        path = self.path.split("?")[0].rstrip("/")
        body_data = self.read_body()

        if path.startswith("/collections/") and (path.endswith("/points/search") or path.endswith("/points/scroll")):
            if set(body_data) - {"vector", "limit", "with_payload"}:
                raise ValueError("unsupported_search_options")
            parts = path.split("/")
            col_name = parts[2]
            vec = body_data.get("vector", [])
            limit = body_data.get("limit", 10)
            with_payload = body_data.get("with_payload", True)
            if path.endswith("/points/scroll"):
                return self.send_json({"result": {"points": store.scroll(col_name, limit, with_payload), "next_page_offset": None}, "status": "ok"})
            res = store.search(col_name, vec, limit, with_payload)
            return self.send_json({"result": res, "status": "ok"})

        if path.startswith("/collections/") and path.endswith("/points"):
            parts = path.split("/")
            col_name = parts[2]
            points = body_data.get("points", [])
            store.upsert_points(col_name, points)
            return self.send_json({"result": {"operation_id": 1, "status": "completed"}, "status": "ok"})

        return self.send_json({"status": "error", "error": "Not found"}, 404)

    @api_guard
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

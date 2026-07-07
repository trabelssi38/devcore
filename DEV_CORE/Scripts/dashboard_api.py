import http.server
import socketserver
import urllib.parse
import json
import subprocess
from pathlib import Path
import os
import sys
from datetime import datetime
import time
import random

PORT = 20129
PLATFORM_ROOT = os.getenv("DEVCORE_PLATFORM_ROOT", "C:/devcore/DEV_CORE")
DATA_ROOT = os.getenv("DEVCORE_DATA_ROOT", "C:/devcore/DEV_CORE_DATA")

def read_json_with_retry(file_path, retries=5, delay=0.05):
    for attempt in range(retries):
        try:
            with open(file_path, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        except (IOError, PermissionError) as e:
            print(f"[DashboardAPI] Read attempt {attempt+1}/{retries} failed for {file_path}: {e}")
            if attempt < retries - 1:
                time.sleep(delay + random.uniform(0.01, 0.05))
            else:
                raise
        except json.JSONDecodeError as e:
            print(f"[DashboardAPI] JSON decode failed: {e}")
            if attempt < retries - 1:
                time.sleep(delay + random.uniform(0.01, 0.05))
            else:
                raise

def write_json_with_retry(file_path, data, retries=5, delay=0.05):
    for attempt in range(retries):
        try:
            temp_path = Path(file_path).with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            if Path(file_path).exists():
                os.replace(str(temp_path), str(file_path))
            else:
                temp_path.rename(file_path)
            return
        except (IOError, PermissionError, OSError) as e:
            print(f"[DashboardAPI] Write attempt {attempt+1}/{retries} failed for {file_path}: {e}")
            if attempt < retries - 1:
                time.sleep(delay + random.uniform(0.01, 0.05))
            else:
                raise

class DashboardAPIHandler(http.server.BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'X-Requested-With, Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        try:
            self.send_response(200)
            self.end_headers()
        except ConnectionError:
            pass

    def log_message(self, format, *args):
        # Silence standard HTTP logs in the background terminal unless needed
        pass

    def get_settings(self):
        settings_file = Path(PLATFORM_ROOT) / "Config" / "settings.json"
        if not settings_file.exists():
            defaults = {
                "active_client": "antigravity",
                "auto_refresh_seconds": 15,
                "gemini_api_key": "",
                "anthropic_api_key": "",
                "services": {
                    "qdrant": True,
                    "gemini_router": True,
                    "dashboard_api": True,
                    "headroom": True,
                    "hermes_daemon": True,
                    "repowise": True
                }
            }
            return defaults
        try:
            return read_json_with_retry(settings_file)
        except Exception:
            return {}

    def save_settings(self, data):
        settings_file = Path(PLATFORM_ROOT) / "Config" / "settings.json"
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        write_json_with_retry(settings_file, data)
        
        # Sync active client file
        active_client = data.get("active_client")
        if active_client:
            client_file = Path(PLATFORM_ROOT) / "Config" / "active_client.txt"
            with open(client_file, "w", encoding="utf-8") as f:
                f.write(active_client)

    def do_GET(self):
        try:
            self._handle_get()
        except ConnectionError:
            # Silence tracebacks if the client disconnected prematurely
            pass

    def _handle_get(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)

        if path == "/api/settings":
            try:
                settings = self.get_settings()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(settings, indent=4).encode("utf-8"))
            except Exception as e:
                self.send_error_response(str(e))
            return


        if path == "/api/done":
            project = query.get("project", [""])[0]
            task_id = query.get("id", [""])[0]
            if not project or not task_id:
                self.send_error_response("Missing project or id")
                return

            success, msg = self.complete_task(project, task_id)
            if success:
                self.send_success_response(msg)
            else:
                self.send_error_response(msg)

        elif path == "/api/delete":
            project = query.get("project", [""])[0]
            task_id = query.get("id", [""])[0]
            if not project or not task_id:
                self.send_error_response("Missing project or id")
                return

            success, msg = self.delete_task(project, task_id)
            if success:
                self.send_success_response(msg)
            else:
                self.send_error_response(msg)

        elif path in ["/", "/index.html"]:
            try:
                index_path = Path(PLATFORM_ROOT) / "Dashboard" / "index.html"
                if index_path.exists():
                    with open(index_path, "r", encoding="utf-8") as f:
                        html_content = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(html_content.encode("utf-8"))
                else:
                    self.send_error_response("index.html not found")
            except ConnectionError:
                pass
            except Exception as e:
                self.send_error_response(str(e))
        elif path == "/api/status":
            self.send_success_response("API Server Active")
        elif path == "/api/refresh":
            try:
                cmd = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", 
                       f"{PLATFORM_ROOT}/Scripts/gen_dashboard.ps1"]
                print(f"[DashboardAPI] Running gen_dashboard.ps1 (timeout=15s)...")
                subprocess.run(cmd, capture_output=True, timeout=15.0)
                
                index_path = Path(PLATFORM_ROOT) / "Dashboard" / "index.html"
                if index_path.exists():
                    with open(index_path, "r", encoding="utf-8") as f:
                        html_content = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(html_content.encode("utf-8"))
                else:
                    self.send_error_response("index.html not found after regeneration")
            except ConnectionError:
                # Connection was aborted by client; do not try to send an error response
                pass
            except subprocess.TimeoutExpired as te:
                print(f"[DashboardAPI] Timeout calling gen_dashboard.ps1: {te}")
                self.send_error_response("Dashboard regeneration timed out after 15s")
            except Exception as e:
                self.send_error_response(str(e))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        try:
            self._handle_post()
        except ConnectionError:
            pass

    def _handle_post(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if path == "/api/settings":
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode('utf-8'))
                self.save_settings(data)
                self.send_success_response("Settings saved successfully")
            except Exception as e:
                self.send_error_response(str(e))
        else:
            self.send_response(404)
            self.end_headers()

    def send_success_response(self, message):
        try:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "message": message}).encode("utf-8"))
        except ConnectionError:
            pass

    def send_error_response(self, error):
        try:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": False, "error": error}).encode("utf-8"))
        except ConnectionError:
            pass

    def complete_task(self, project, task_id):
        tasks_file = Path(DATA_ROOT) / "Memory" / project / "tasks.json"
        if not tasks_file.exists():
            return False, f"Project board not found: {tasks_file}"

        try:
            print(f"[DashboardAPI] Completing task {task_id} on project {project}...")
            board = read_json_with_retry(tasks_file)

            task_found = False
            is_active = False
            for task in board.get("tasks", []):
                if task.get("id") == task_id:
                    task_found = True
                    is_active = (task.get("status") == "active")
                    task["status"] = "done"
                    task["steps_done"] = task.get("steps_total", 1)
                    task["completed_at"] = datetime.now().isoformat()
                    break

            if not task_found:
                return False, f"Task {task_id} not found in project {project}"

            # Write the file first with retries
            write_json_with_retry(tasks_file, board)
            print(f"[DashboardAPI] Successfully saved completed task status in tasks.json.")

            # If it was the active task, run the official task_done.ps1 to execute hooks
            if is_active:
                cmd = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", 
                       f"{PLATFORM_ROOT}/Scripts/task_done.ps1", "-Force"]
                print(f"[DashboardAPI] Running task_done.ps1 for active task completion (timeout=15s)...")
                subprocess.run(cmd, capture_output=True, timeout=15.0)
                return True, f"Active task {task_id} completed successfully via task_done.ps1"
            else:
                # Regenerate the dashboard
                cmd = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", 
                       f"{PLATFORM_ROOT}/Scripts/gen_dashboard.ps1"]
                print(f"[DashboardAPI] Running gen_dashboard.ps1 for dashboard refresh (timeout=15s)...")
                subprocess.run(cmd, capture_output=True, timeout=15.0)
                return True, f"Task {task_id} completed successfully"

        except subprocess.TimeoutExpired as te:
            print(f"[DashboardAPI] Timeout expired executing completion script: {te}")
            return True, f"Task {task_id} completed but post-completion command timed out"
        except Exception as e:
            print(f"[DashboardAPI] Error completing task: {e}")
            return False, str(e)

    def delete_task(self, project, task_id):
        tasks_file = Path(DATA_ROOT) / "Memory" / project / "tasks.json"
        if not tasks_file.exists():
            return False, f"Project board not found: {tasks_file}"

        try:
            print(f"[DashboardAPI] Deleting task {task_id} on project {project}...")
            board = read_json_with_retry(tasks_file)

            original_count = len(board.get("tasks", []))
            board["tasks"] = [t for t in board.get("tasks", []) if t.get("id") != task_id]

            if len(board["tasks"]) == original_count:
                return False, f"Task {task_id} not found in project {project}"

            if board.get("current_task") == task_id:
                board["current_task"] = None

            write_json_with_retry(tasks_file, board)
            print(f"[DashboardAPI] Successfully saved deleted task in tasks.json.")

            # Regenerate the dashboard
            cmd = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", 
                   f"{PLATFORM_ROOT}/Scripts/gen_dashboard.ps1"]
            print(f"[DashboardAPI] Running gen_dashboard.ps1 for dashboard refresh (timeout=15s)...")
            subprocess.run(cmd, capture_output=True, timeout=15.0)
            return True, f"Task {task_id} deleted successfully"

        except subprocess.TimeoutExpired as te:
            print(f"[DashboardAPI] Timeout expired executing delete refresh script: {te}")
            return True, f"Task {task_id} deleted but dashboard refresh timed out"
        except Exception as e:
            print(f"[DashboardAPI] Error deleting task: {e}")
            return False, str(e)

def main():
    server_class = http.server.HTTPServer
    if hasattr(http.server, "ThreadingHTTPServer"):
        server_class = http.server.ThreadingHTTPServer

    socketserver.TCPServer.allow_reuse_address = True
    
    with server_class(("", PORT), DashboardAPIHandler) as httpd:
        print(f"DEV_CORE Dashboard API Server listening on port {PORT}...")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down API Server.")
            sys.exit(0)

if __name__ == "__main__":
    main()

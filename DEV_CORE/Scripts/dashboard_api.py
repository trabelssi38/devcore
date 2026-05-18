import http.server
import socketserver
import urllib.parse
import json
import subprocess
from pathlib import Path
import os
import sys

PORT = 20129
PLATFORM_ROOT = os.getenv("DEVCORE_PLATFORM_ROOT", "C:/devcore/DEV_CORE")
DATA_ROOT = os.getenv("DEVCORE_DATA_ROOT", "C:/devcore/DEV_CORE_DATA")

class DashboardAPIHandler(http.server.BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'X-Requested-With, Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        # Silence standard HTTP logs in the background terminal unless needed
        pass

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)

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

        elif path == "/api/status":
            self.send_success_response("API Server Active")
        else:
            self.send_response(404)
            self.end_headers()

    def send_success_response(self, message):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"success": True, "message": message}).encode("utf-8"))

    def send_error_response(self, error):
        self.send_response(400)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"success": False, "error": error}).encode("utf-8"))

    def complete_task(self, project, task_id):
        tasks_file = Path(DATA_ROOT) / "Memory" / project / "tasks.json"
        if not tasks_file.exists():
            return False, f"Project board not found: {tasks_file}"

        try:
            with open(tasks_file, "r", encoding="utf-8") as f:
                board = json.load(f)

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

            # Write the file first
            with open(tasks_file, "w", encoding="utf-8") as f:
                json.dump(board, f, indent=4, ensure_ascii=False)

            # If it was the active task, run the official task_done.ps1 to execute hooks
            if is_active:
                cmd = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", 
                       f"{PLATFORM_ROOT}/Scripts/task_done.ps1", "-Force"]
                subprocess.run(cmd, capture_output=True)
                return True, f"Active task {task_id} completed successfully via task_done.ps1"
            else:
                # Regenerate the dashboard
                cmd = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", 
                       f"{PLATFORM_ROOT}/Scripts/gen_dashboard.ps1"]
                subprocess.run(cmd, capture_output=True)
                return True, f"Task {task_id} completed successfully"

        except Exception as e:
            return False, str(e)

    def delete_task(self, project, task_id):
        tasks_file = Path(DATA_ROOT) / "Memory" / project / "tasks.json"
        if not tasks_file.exists():
            return False, f"Project board not found: {tasks_file}"

        try:
            with open(tasks_file, "r", encoding="utf-8") as f:
                board = json.load(f)

            original_count = len(board.get("tasks", []))
            board["tasks"] = [t for t in board.get("tasks", []) if t.get("id") != task_id]

            if len(board["tasks"]) == original_count:
                return False, f"Task {task_id} not found in project {project}"

            if board.get("current_task") == task_id:
                board["current_task"] = None

            with open(tasks_file, "w", encoding="utf-8") as f:
                json.dump(board, f, indent=4, ensure_ascii=False)

            # Regenerate the dashboard
            cmd = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", 
                   f"{PLATFORM_ROOT}/Scripts/gen_dashboard.ps1"]
            subprocess.run(cmd, capture_output=True)
            return True, f"Task {task_id} deleted successfully"

        except Exception as e:
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
    from datetime import datetime
    main()

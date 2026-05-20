import os
import json
import re
import subprocess
from datetime import datetime

def get_active_project(dev_core, dev_core_data):
    env_name = os.environ.get("DEVCORE_ACTIVE_PROJECT_NAME")
    if env_name:
        return env_name
        
    try:
        git_dir = subprocess.check_output(
            "git rev-parse --git-common-dir",
            stderr=subprocess.DEVNULL,
            shell=True
        ).decode("utf-8").strip()
        if git_dir:
            abs_git_dir = os.path.abspath(git_dir)
            if abs_git_dir.endswith(".git") or abs_git_dir.endswith(".git/"):
                projectName = os.path.basename(os.path.dirname(abs_git_dir))
            else:
                projectName = os.path.basename(abs_git_dir)
            if projectName:
                return re.sub(r'[\\/:*?"<>|]', '_', projectName)
    except:
        pass
        
    try:
        parent_name = os.path.basename(os.path.dirname(dev_core))
        if parent_name:
            return re.sub(r'[\\/:*?"<>|]', '_', parent_name)
    except:
        pass
        
    return "devcore"

def clean_title(title):
    # Strip at first newline
    title = title.split("\n")[0]
    # Strip at XML brackets/tags
    title = title.split("<")[0].split("</")[0]
    # Remove excessive whitespace
    title = re.sub(r'\s+', ' ', title).strip()
    return title

def main():
    dev_core = os.environ.get("DEVCORE_PLATFORM_ROOT", "C:\\devcore\\DEV_CORE")
    dev_core_data = os.environ.get("DEVCORE_DATA_ROOT", "C:\\devcore\\DEV_CORE_DATA")
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    active_proj = get_active_project(dev_core, dev_core_data)
    
    queue_dir = os.path.join(dev_core_data, "Memory", active_proj)
    if not os.path.exists(queue_dir):
        os.makedirs(queue_dir)
        
    queue_path = os.path.join(queue_dir, "task_prompt_queue.jsonl")
    log_dir = os.path.join(dev_core_data, "Logs", "scripts")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    log_path = os.path.join(log_dir, f"task_prompt_analyzer_{today_str}.log")

    def log(msg, level="INFO"):
        time_str = datetime.now().strftime("%H:%M:%S")
        line = f"[{time_str}] [{level}] {msg}\n"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line)
        try:
            print(f"    {line.strip()}")
        except UnicodeEncodeError:
            safe_line = line.encode('ascii', errors='replace').decode('ascii').strip()
            print(f"    {safe_line}")

    log(f"Starting Dynamic Prompt Analyzer for project: '{active_proj}'", "INIT")

    # Load dynamic registry
    registry_path = os.path.join(dev_core, "Config", "intent_patterns.json")
    if not os.path.exists(registry_path):
        log(f"Intent patterns registry not found: {registry_path}", "ERROR")
        return
        
    try:
        with open(registry_path, "r", encoding="utf-8-sig") as rf:
            intent_registry = json.load(rf)
        log(f"Successfully loaded intent patterns registry ({len(intent_registry)} categories)", "SUCCESS")
    except Exception as e:
        log(f"Error reading registry: {e}", "ERROR")
        return

    # 2. Build dynamic regexes
    patterns = {}
    for mode, verbs in intent_registry.items():
        participles = []
        actives = []
        for v in verbs:
            if v.endswith("é") or v.endswith("dé") or v.endswith("sé") or v.endswith("ué") or v.endswith("té") or v.endswith("ré") or v.endswith("i") or v.endswith("u") or v.endswith("t"):
                participles.append(v)
            else:
                actives.append(v)
                
        patterns[mode] = []
        if actives:
            actives_escaped = "|".join(re.escape(x) for x in actives)
            patterns[mode].append(r"(?i)\b(?:" + actives_escaped + r")\s+([^.?!,;]{10,80})")
        if participles:
            participles_escaped = "|".join(re.escape(x) for x in participles)
            patterns[mode].append(r"(?i)j[e'\s]+ai\s+(?:" + participles_escaped + r")\s+([^.?!,;]{10,80})")

    brain_dir = r"C:\Users\trb_m\.gemini\antigravity\brain"
    if not os.path.exists(brain_dir):
        log(f"Brain folder not found: {brain_dir}", "WARNING")
        return

    # 3. Find top 3 most recently modified session folders
    sessions = []
    for d in os.listdir(brain_dir):
        path = os.path.join(brain_dir, d)
        if os.path.isdir(path) and d != "tempmediaStorage":
            overview_path = os.path.join(path, ".system_generated", "logs", "overview.txt")
            if os.path.exists(overview_path):
                sessions.append((overview_path, os.path.getmtime(overview_path)))

    sessions.sort(key=lambda x: x[1], reverse=True)
    recent_sessions = sessions[:3]

    if not recent_sessions:
        log("No active Antigravity sessions found", "INFO")
        return

    todo_patterns = [
        r"(?i)\b(?:TODO|FIXME|NEXT|ENSUITE|A FAIRE)\s*:\s*([^.?!,;\n]{8,80})"
    ]

    candidates = []

    # 4. Scan the overview logs
    for s_path, _ in recent_sessions:
        parts = s_path.split(os.sep)
        try:
            brain_idx = parts.index("brain")
            s_id = parts[brain_idx + 1]
        except:
            s_id = "unknown_session"
            
        log(f"Scanning active session logs: {s_id}", "SCAN")
        
        try:
            with open(s_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                
            for line in lines:
                try:
                    data = json.loads(line)
                    content = data.get("content", "")
                    source = data.get("source")
                    type_ = data.get("type")
                    
                    # Only parse actual user chat inputs
                    if not content or type_ != "USER_INPUT":
                        continue
                        
                    # Standard intent matching
                    for mode, regexes in patterns.items():
                        for regex in regexes:
                            for match in re.finditer(regex, content):
                                title = clean_title(match.group(0))
                                if len(title) > 10:
                                    candidates.append({
                                        "title": title,
                                        "mode": mode,
                                        "source": s_id,
                                        "source_type": "antigravity_live_chat",
                                        "detected": today_str
                                    })
                                    
                    # TODO comment matching
                    for regex in todo_patterns:
                        for match in re.finditer(regex, content):
                            title = clean_title(match.group(1))
                            candidates.append({
                                "title": f"TODO: {title}",
                                "mode": "coding",
                                "source": s_id,
                                "source_type": "antigravity_todo_kw",
                                "detected": today_str
                            })
                except:
                    pass
        except Exception as e:
            log(f"Error parsing session {s_id}: {e}", "ERROR")

    # 5. Deduplicate and save to queue
    if candidates:
        seen = set()
        unique_candidates = []
        for c in candidates:
            k = c["title"].lower()
            if k not in seen:
                seen.add(k)
                unique_candidates.append(c)
                
        # Write to JSONL
        with open(queue_path, "w", encoding="utf-8") as q: # Overwrite queue to keep it clean
            for uc in unique_candidates:
                q.write(json.dumps(uc, ensure_ascii=False) + "\n")
                log(f"Registered autonomous task suggestion: [{uc['mode']}] {uc['title']}", "AUTOTASK")
                
        log(f"Successfully loaded {len(unique_candidates)} tasks into DevCore queue.", "SUCCESS")
    else:
        log("No task intents detected in recent live logs.", "CLEAN")

if __name__ == "__main__":
    main()

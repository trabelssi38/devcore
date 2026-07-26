import os
import json
import re
import subprocess
from datetime import datetime

def clean_word(word):
    cleaned = re.sub(r"[^\wáàâäéèêëíìîïóòôöúùûüç\-]", "", word)
    return cleaned.strip().lower()

def decline_french_verb(verb):
    variations = {verb}
    
    if verb.endswith("er"):
        base = verb[:-2]
        variations.add(base + "e")
        variations.add(base + "ez")
        variations.add(base + "é")
    elif verb.endswith("ez"):
        base = verb[:-2]
        variations.add(base + "er")
        variations.add(base + "e")
        variations.add(base + "é")
    elif verb.endswith("e"):
        base = verb[:-1]
        variations.add(base + "er")
        variations.add(base + "ez")
        variations.add(base + "é")
    elif verb.endswith("é"):
        base = verb[:-1]
        variations.add(base + "er")
        variations.add(base + "e")
        variations.add(base + "ez")
        
    return list(variations)

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

def main():
    dev_core = os.environ.get("DEVCORE_PLATFORM_ROOT", str(Path(__file__).resolve().parents[4] / "DEV_CORE"))
    dev_core_data = os.environ.get("DEVCORE_DATA_ROOT", str(Path(__file__).resolve().parents[4] / "DEV_CORE_DATA"))
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    log_dir = os.path.join(dev_core_data, "Logs", "scripts")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    log_path = os.path.join(log_dir, f"intent_learner_{today_str}.log")

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

    # 1. Get active project name dynamically
    active_proj = get_active_project(dev_core, dev_core_data)
    log(f"Starting DevCore Intent Learning Loop for project: '{active_proj}'", "INIT")

    tasks_file = os.path.join(dev_core_data, "Memory", active_proj, "tasks.json")
    if not os.path.exists(tasks_file):
        log(f"Tasks database not found: {tasks_file}", "WARNING")
        return

    # 2. Load patterns registry
    registry_path = os.path.join(dev_core, "Config", "intent_patterns.json")
    if not os.path.exists(registry_path):
        log(f"Registry not found at: {registry_path}", "ERROR")
        return
        
    try:
        with open(registry_path, "r", encoding="utf-8-sig") as f:
            registry = json.load(f)
    except Exception as e:
        log(f"Error loading registry: {e}", "ERROR")
        return

    # 3. Read tasks and extract verbs
    try:
        with open(tasks_file, "r", encoding="utf-8-sig") as f:
            tasks_data = json.load(f)
    except Exception as e:
        log(f"Error loading tasks file: {e}", "ERROR")
        return

    tasks_list = tasks_data.get("tasks", [])
    if not tasks_list:
        log("No tasks found in the database. Learning skipped.", "INFO")
        return

    new_learnings = 0
    
    for t in tasks_list:
        title = t.get("title", "").strip()
        mode = t.get("mode", "coding")
        
        if not title:
            continue
            
        words = title.split()
        if not words:
            continue
            
        first_word = clean_word(words[0])
        if len(first_word) <= 3 or first_word in ["avec", "pour", "dans", "chez", "sous", "vers", "sans", "tout"]:
            continue
            
        if mode not in registry:
            mode = "coding"
            
        covered = False
        for m_verbs in registry.values():
            if first_word in m_verbs:
                covered = True
                break
                
        if not covered:
            log(f"Detected new task verb: '{first_word}' in task '{title}' [Category: {mode}]", "LEARN")
            
            variations = decline_french_verb(first_word)
            log(f"Generated linguistic variations: {variations}", "LISP")
            
            for v in variations:
                if v not in registry[mode]:
                    registry[mode].append(v)
                    log(f"Enriched registry category '{mode}' with word: '{v}'", "ADD")
                    new_learnings += 1

    # 4. Save back registry if enriched
    if new_learnings > 0:
        try:
            with open(registry_path, "w", encoding="utf-8") as f:
                json.dump(registry, f, indent=2, ensure_ascii=False)
            log(f"Successfully saved enriched registry! Added {new_learnings} new verbal variations.", "SUCCESS")
        except Exception as e:
            log(f"Error saving registry: {e}", "ERROR")
    else:
        log("Registry is already fully saturated and up-to-date with active task history.", "CLEAN")

if __name__ == "__main__":
    main()

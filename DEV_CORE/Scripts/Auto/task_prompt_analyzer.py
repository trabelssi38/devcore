import os
import json
import re
import subprocess
from datetime import datetime
import time
import random

def read_file_with_retry(file_path, errors="ignore", retries=5, delay=0.05):
    for attempt in range(retries):
        try:
            with open(file_path, "r", encoding="utf-8-sig", errors=errors) as f:
                return f.read()
        except (IOError, PermissionError) as e:
            if attempt < retries - 1:
                time.sleep(delay + random.uniform(0.01, 0.05))
            else:
                raise

def read_lines_with_retry(file_path, errors="ignore", retries=5, delay=0.05):
    for attempt in range(retries):
        try:
            with open(file_path, "r", encoding="utf-8-sig", errors=errors) as f:
                return f.readlines()
        except (IOError, PermissionError) as e:
            if attempt < retries - 1:
                time.sleep(delay + random.uniform(0.01, 0.05))
            else:
                raise

def write_file_with_retry(file_path, content, mode="w", retries=5, delay=0.05):
    for attempt in range(retries):
        try:
            with open(file_path, mode, encoding="utf-8") as f:
                f.write(content)
            return
        except (IOError, PermissionError) as e:
            if attempt < retries - 1:
                time.sleep(delay + random.uniform(0.01, 0.05))
            else:
                raise

def get_active_project(dev_core, dev_core_data):
    system_dirs = {"documents", "desktop", "downloads", "onedrive", "system32", "users", "windows", "temp", "appdata", "local"}
    
    env_name = os.environ.get("DEVCORE_ACTIVE_PROJECT_NAME")
    if env_name and env_name.lower() not in system_dirs:
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
            if projectName and projectName.lower() not in system_dirs:
                return re.sub(r'[\\/:*?"<>|]', '_', projectName)
    except:
        pass
        
    try:
        parent_name = os.path.basename(os.path.dirname(dev_core))
        if parent_name and parent_name.lower() not in system_dirs:
            return re.sub(r'[\\/:*?"<>|]', '_', parent_name)
    except:
        pass
        
    return "devcore"

def clean_accomplishment(text):
    text = text.strip().rstrip(".?!,;*:\n").strip()
    text = re.sub(r'\s+', ' ', text)
    if text:
        text = text[0].upper() + text[1:]
    return text

def balance_and_clean(text):
    text = text.strip()
    
    # Remove unbalanced opening quotes, parentheses, brackets, or backticks at the very end
    text = re.sub(r'[\s\(\[\{`"\-,]+$', '', text)
    
    # Ensure quotes are balanced (double quotes and backticks only, NOT single quotes/apostrophes)
    for char in ['"', "`"]:
        if text.count(char) % 2 != 0:
            if text.endswith(char):
                text = text[:-1]
            else:
                text += char
                
    # Balance parentheses
    open_p = text.count('(')
    close_p = text.count(')')
    if open_p > close_p:
        text += ')' * (open_p - close_p)
    elif close_p > open_p:
        text = text.replace(')', '', close_p - open_p)
        
    return text

def formulate_title(accomplishment):
    text = accomplishment.strip()
    
    # 1. Premium Order-Independent Concept Mapping (elegant French titles matching Fr/En keywords in any order)
    concept_mappings = [
        (r'(?i)(?:token|jeton).*?report|report.*?(?:token|jeton)', "Optimisation des rapports de tokens quotidiens"),
        (r'(?i)(?:task|tâche).*?(?:sync|synchroni)|(?:sync|synchroni).*?(?:task|tâche)', "Restructuration et synchronisation des tâches système"),
        (r'(?i)(?:task|tâche).*?(?:detect|analyzer|prompt|détect|analyz)|(?:detect|analyzer|prompt|détect|analyz).*?(?:task|tâche)', "Optimisation de l'analyseur de détection autonome des tâches"),
        (r'(?i)intent.*pattern|intention', "Mise à jour de la base de données d'intentions de tâches"),
        (r'(?i)(?:diagnose|diagnostic).*syst|syst.*(?:diagnose|diagnostic)', "Développement et enrichissement du script de diagnostic système"),
        (r'(?i)(cockpit|dashboard|tableau.*bord)', "Amélioration et réorganisation ergonomique du Cockpit"),
        (r'(?i)(hook|commit)', "Intégration de la synchronisation dans le hook global de commit"),
        (r'(?i)toon', "Nettoyage et suppression des anciennes tâches obsolètes"),
        (r'(?i)dbSwitchService', "Analyse technique du service d'aiguillage de base de données"),
        (r'(?i)méthodologie.*devcore', "Harmonisation méthodologique du cycle de vie des tâches DevCore"),
        (r'(?i)architecture.*hybride', "Déploiement d'une architecture hybride de détection autonome"),
        (r'(?i)(?:dépôt|repository).*github|github.*(?:dépôt|repository)', "Mise à jour et déploiement du dépôt distant GitHub"),
        (r'(?i)base.*données.*verbe|verb.*database', "Création d'une base de données externe pour les verbes de détection"),
    ]
    
    for pattern, premium_title in concept_mappings:
        if re.search(pattern, text):
            return premium_title

    # 2. Advanced French Verb-to-Noun replacements for fallbacks
    verb_mappings = [
        (r'^(?:j\'ai|nous\s+avons|i\s+have|we\s+have)\s+(?:successfully\s+)?(?:trouvé\s+la\s+solution\s+idéale\s+pour\s+)?rétablir\s+', "Rétablissement de "),
        (r'^(?:j\'ai|nous\s+avons|i\s+have|we\s+have)\s+(?:successfully\s+)?(?:mené\s+à\s+bien\s+la\s+)?restructuration\s+', "Restructuration de "),
        (r'^(?:j\'ai|nous\s+avons|i\s+have|we\s+have)\s+(?:successfully\s+)?(?:finalisé\s+la\s+)?synchronisation\s+', "Synchronisation de "),
        (r'^(?:j\'ai|nous\s+avons|i\s+have|we\s+have)\s+(?:successfully\s+)?effectué\s+toutes\s+les\s+modifications\s+', "Application des modifications système "),
        (r'^(?:j\'ai|nous\s+avons|i\s+have|we\s+have)\s+(?:successfully\s+)?(?:créé\s+et\s+associé|créé\s+et\s+associé)\s+', "Création et association "),
        (r'^(?:j\'ai|nous\s+avons|i\s+have|we\s+have)\s+(?:successfully\s+)?(?:formalisé\s+et\s+consolidé)\s+', "Formalisation et consolidation "),
        (r'^(?:j\'ai|nous\s+avons|i\s+have|we\s+have)\s+(?:successfully\s+)?(?:exécuté|run)\s+', "Exécution de "),
        (r'^(?:j\'ai|nous\s+avons|i\s+have|we\s+have)\s+(?:successfully\s+)?(?:rendu|rendue)\s+', "Amélioration visuelle de "),
        (r'^(?:j\'ai|nous\s+avons|i\s+have|we\s+have)\s+(?:successfully\s+)?(?:écrit|rédigé)\s+', "Rédaction de "),
        (r'^(?:j\'ai|nous\s+avons|i\s+have|we\s+have)\s+(?:successfully\s+)?(?:ajouté\s+avec\s+succès)\s+', "Ajout réussi de "),
    ]

    for pattern, replacement in verb_mappings:
        match = re.match(pattern, text, re.IGNORECASE)
        if match:
            remaining = text[match.end():].strip()
            if remaining:
                remaining = remaining[0].lower() + remaining[1:]
            title = replacement + remaining
            
            # Post-processing grammar corrections
            title = re.sub(r'\bde\s+le\b', 'du', title, flags=re.I)
            title = re.sub(r'\bde\s+les\b', 'des', title, flags=re.I)
            title = re.sub(r'\bde\s+un\b', "d'un", title, flags=re.I)
            title = re.sub(r'\bde\s+une\b', "d'une", title, flags=re.I)
            title = re.sub(r'\bde\s+l\'\b', "de l'", title, flags=re.I)
            title = re.sub(r'\bà\s+le\b', 'au', title, flags=re.I)
            title = re.sub(r'\bà\s+les\b', 'aux', title, flags=re.I)
            title = re.sub(r'pertinantes', 'pertinentes', title, flags=re.I)
            title = re.sub(r'incompletes', 'incomplètes', title, flags=re.I)
            return balance_and_clean(title[0].upper() + title[1:])

    # 3. Standard verb prefixes
    prefixes = [
        (r'^(?:j\'ai|nous\s+avons|i\s+have|we\s+have)\s+(?:successfully\s+)?(?:corrigé|résolu|fixé|corrigé\s+et\s+mis\s+à\s+jour|corrected|fixed)\s+', "Correction de "),
        (r'^(?:j\'ai|nous\s+avons|i\s+have|we\s+have)\s+(?:successfully\s+)?(?:implémenté|développé|réalisé|mis\s+en\s+place|implemented|developed)\s+', "Implémentation de "),
        (r'^(?:j\'ai|nous\s+avons|i\s+have|we\s+have)\s+(?:successfully\s+)?(?:ajouté|inséré|intégré|added|integrated)\s+', "Ajout de "),
        (r'^(?:j\'ai|nous\s+avons|i\s+have|we\s+have)\s+(?:successfully\s+)?(?:supprimé|retiré|effacé|removed|deleted)\s+', "Suppression de "),
        (r'^(?:j\'ai|nous\s+avons|i\s+have|we\s+have)\s+(?:successfully\s+)?(?:mis\s+à\s+jour|actualisé|upgradé|updated|upgraded)\s+', "Mise à jour de "),
        (r'^(?:j\'ai|nous\s+avons|i\s+have|we\s+have)\s+(?:successfully\s+)?(?:créé|généré|conçu|created|designed|generated)\s+', "Création de "),
        (r'^(?:j\'ai|nous\s+avons|i\s+have|we\s+have)\s+(?:successfully\s+)?(?:configuré|paramétré|setup|configured)\s+', "Configuration de "),
        (r'^(?:j\'ai|nous\s+avons|i\s+have|we\s+have)\s+(?:successfully\s+)?(?:testé|validé|vérifié|tested|validated|verified)\s+', "Validation de "),
        (r'^(?:j\'ai|nous\s+avons|i\s+have|we\s+have)\s+(?:successfully\s+)?(?:nettoyé|optimisé|cleané|cleaned|optimized)\s+', "Optimisation/Nettoyage de "),
        (r'^(?:j\'ai|nous\s+avons|i\s+have|we\s+have)\s+(?:successfully\s+)?(?:analysé|recherché|investigué|analyzed|researched|investigated)\s+', "Analyse de "),
        (r'^(?:j\'ai|nous\s+avons|i\s+have|we\s+have)\s+(?:successfully\s+)?(?:documenté|rédigé|documented|written)\s+', "Documentation de "),
        (r'^(?:j\'ai|nous\s+avons|i\s+have|we\s+have)\s+(?:successfully\s+)?(?:formalisé|consolidé|formalized|consolidated)\s+', "Formalisation de "),
    ]

    for pattern, prefix in prefixes:
        match = re.match(pattern, text, re.IGNORECASE)
        if match:
            remaining = text[match.end():].strip()
            if remaining:
                remaining = remaining[0].lower() + remaining[1:]
            title = prefix + remaining
            
            # Post-processing grammar corrections
            title = re.sub(r'\bde\s+le\b', 'du', title, flags=re.I)
            title = re.sub(r'\bde\s+les\b', 'des', title, flags=re.I)
            title = re.sub(r'\bde\s+un\b', "d'un", title, flags=re.I)
            title = re.sub(r'\bde\s+une\b', "d'une", title, flags=re.I)
            title = re.sub(r'\bde\s+l\'\b', "de l'", title, flags=re.I)
            title = re.sub(r'\bà\s+le\b', 'au', title, flags=re.I)
            title = re.sub(r'\bà\s+les\b', 'aux', title, flags=re.I)
            title = re.sub(r'pertinantes', 'pertinentes', title, flags=re.I)
            title = re.sub(r'incompletes', 'incomplètes', title, flags=re.I)
            return balance_and_clean(title[0].upper() + title[1:])
            
    # Fallback: remove pronoun prefixes
    text = re.sub(r'^(?:j\'ai|nous\s+avons|i\s+have|we\s+have|successfully)\s+', '', text, flags=re.I).strip()
    if text:
        text = text[0].upper() + text[1:]
    if len(text) > 75:
        text = text[:72] + "..."
    return balance_and_clean(text)

def choose_title_for_session(accomplishments, files):
    if accomplishments:
        # Prioritize accomplishments that match concept mappings first
        for acc in accomplishments:
            t = formulate_title(acc)
            # If it mapped to a custom beautiful title instead of simple noun prefixing fallback, return it!
            if any(t.startswith(x) for x in ["Optimisation", "Restructuration", "Mise à jour", "Développement", "Amélioration", "Intégration", "Nettoyage", "Analyse", "Harmonisation", "Création", "Déploiement"]):
                return t
        # Otherwise return the formulation of the first accomplishment
        return formulate_title(accomplishments[0])
    elif files:
        basenames = [os.path.basename(f) for f in files[:2]]
        files_str = " et ".join(basenames)
        if len(files) > 2:
            files_str += " et d'autres fichiers"
        return f"Mise à jour de {files_str}"
    return "Mise à jour système autonome"

def formulate_details(accomplishments, files):
    details_lines = []
    if accomplishments:
        details_lines.append("**Actions réalisées par l'agent :**")
        for acc in accomplishments:
            details_lines.append(f"- {acc}")
    if files:
        if accomplishments:
            details_lines.append("")
        details_lines.append("**Fichiers modifiés :**")
        for f in files:
            details_lines.append(f"- `{f}`")
    return "\n".join(details_lines)

def parse_task_md(file_path):
    tasks = []
    if not os.path.exists(file_path):
        return tasks
        
    try:
        lines = read_lines_with_retry(file_path, errors="ignore")
    except Exception as e:
        return tasks

    current_task = None
    
    for line in lines:
        stripped = line.strip()
        match = re.match(r'^(\s*)-\s*\[\s*([ xX/])\s*\]\s*(.+)', line)
        if not match:
            continue
            
        indent = len(match.group(1))
        status_char = match.group(2).lower()
        content = match.group(3).strip()
        
        content = re.sub(r'^\*\*+(.*?)\*\*+$', r'\1', content)
        content = re.sub(r'^#+\s*', '', content)
        content = re.sub(r'^\d+(\.\d+)*\s*[\.\-:]?\s*', '', content)
        content = content.strip()
        
        status = "done" if status_char == 'x' else "todo"
        
        if indent < 2:
            current_task = {
                "title": content,
                "status": status,
                "steps": [],
                "steps_total": 0,
                "steps_done": 0,
                "details": f"**Planifié dans la checklist de session :**\n- {content}"
            }
            tasks.append(current_task)
        else:
            step = {
                "title": content,
                "done": status == "done"
            }
            if current_task is not None:
                step["id"] = len(current_task["steps"]) + 1
                current_task["steps"].append(step)
                current_task["steps_total"] += 1
                if step["done"]:
                    current_task["steps_done"] += 1
            else:
                tasks.append({
                    "title": content,
                    "status": status,
                    "steps": [],
                    "steps_total": 1,
                    "steps_done": 1 if status == "done" else 0,
                    "details": f"**Planifié dans la checklist de session :**\n- {content}"
                })
                
    for t in tasks:
        if t["steps"]:
            if t["steps_done"] == t["steps_total"]:
                t["status"] = "done"
            else:
                t["status"] = "todo"
        else:
            t["steps"] = None
            t["steps_total"] = 1
            t["steps_done"] = 1 if t["status"] == "done" else 0
            
    return tasks

def parse_implementation_plan_md(file_path):
    tasks = []
    if not os.path.exists(file_path):
        return tasks
        
    try:
        content = read_file_with_retry(file_path, errors="ignore")
    except Exception as e:
        return tasks
        
    pattern = r'####\s*\[\s*(MODIFY|NEW|DELETE)\s*\]\s*\[\s*([^\]]+)\s*\]\s*\(\s*([^\)]+)\s*\)'
    matches = re.findall(pattern, content, re.IGNORECASE)
    
    for action, filename, link in matches:
        action = action.upper()
        title = f"{action}: {filename}"
        details = f"**Modification planifiée dans le plan d'implémentation :**\n- Action: {action}\n- Fichier: `{filename}`\n- Lien: [{filename}]({link})"
        tasks.append({
            "title": title,
            "status": "todo",
            "steps": None,
            "steps_total": 1,
            "steps_done": 0,
            "details": details
        })
        
    return tasks

def main():
    dev_core = os.environ.get("DEVCORE_PLATFORM_ROOT", str(Path(__file__).resolve().parents[4] / "DEV_CORE"))
    dev_core_data = os.environ.get("DEVCORE_DATA_ROOT", str(Path(__file__).resolve().parents[4] / "DEV_CORE_DATA"))
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

    log(f"Starting Dynamic Agent-Action Analyzer for project: '{active_proj}'", "INIT")

    # Read existing sources and titles from tasks.json to avoid duplicates
    existing_sources = set()
    existing_titles = set()
    tasks_file = os.path.join(queue_dir, "tasks.json")
    try:
        content = read_file_with_retry(tasks_file, errors="ignore")
        board = json.loads(content)
        for t in board.get("tasks", []):
            src = t.get("source")
            if src:
                existing_sources.add(src)
            title = t.get("title")
            if title:
                existing_titles.add(title.lower().strip())
        log(f"Loaded {len(existing_sources)} existing task sources and {len(existing_titles)} titles to prevent duplicates.", "INIT")
    except Exception as e:
        log(f"Error reading tasks.json to deduplicate: {e}", "WARNING")

    brain_dir = r"C:\Users\trb_m\.gemini\antigravity\brain"
    if not os.path.exists(brain_dir):
        log(f"Brain folder not found: {brain_dir}", "WARNING")
        return

    # Find top 3 most recently modified session folders, considering overview.txt, task.md, and implementation_plan.md
    sessions = []
    for d in os.listdir(brain_dir):
        path = os.path.join(brain_dir, d)
        if os.path.isdir(path) and d != "tempmediaStorage":
            overview_path = os.path.join(path, ".system_generated", "logs", "overview.txt")
            task_path = os.path.join(path, "task.md")
            plan_path = os.path.join(path, "implementation_plan.md")
            
            mtimes = []
            if os.path.exists(overview_path):
                mtimes.append(os.path.getmtime(overview_path))
            if os.path.exists(task_path):
                mtimes.append(os.path.getmtime(task_path))
            if os.path.exists(plan_path):
                mtimes.append(os.path.getmtime(plan_path))
                
            if mtimes:
                sessions.append((path, max(mtimes), d))

    sessions.sort(key=lambda x: x[1], reverse=True)
    recent_sessions = sessions[:3]

    if not recent_sessions:
        log("No active Antigravity sessions found", "INFO")
        return

    candidates = []

    for s_path, s_mtime, s_id in recent_sessions:
        if s_id in existing_sources:
            log(f"Session {s_id} has already been registered in tasks.json. Skipping to avoid duplicate suggestions.", "SKIP")
            continue

        overview_path = os.path.join(s_path, ".system_generated", "logs", "overview.txt")
        task_path = os.path.join(s_path, "task.md")
        plan_path = os.path.join(s_path, "implementation_plan.md")
        
        # Read files to check for project name and security isolation
        session_text = ""
        for fp in [overview_path, task_path, plan_path]:
            if os.path.exists(fp):
                try:
                    session_text += read_file_with_retry(fp, errors="ignore")
                except:
                    pass
                    
        # Check if this session contains references to our active project
        if active_proj.lower() not in session_text.lower():
            log(f"Session {s_id} does not refer to active project '{active_proj}'. Skipping to avoid cross-contamination.", "SKIP")
            continue
            
        # If active_proj is "devcore" or "default", verify that no more specific project name appears in the text
        if active_proj.lower() in ["devcore", "default"]:
            other_projects = []
            try:
                for d in os.listdir(os.path.join(dev_core_data, "Memory")):
                    if os.path.isdir(os.path.join(dev_core_data, "Memory", d)) and d.lower() != active_proj.lower():
                        other_projects.append(d.lower())
            except:
                pass
                
            has_more_specific = False
            for op in other_projects:
                if op in session_text.lower():
                    has_more_specific = True
                    break
            if has_more_specific:
                log(f"Session {s_id} refers to a more specific project than '{active_proj}'. Skipping to avoid cross-contamination.", "SKIP")
                continue

        log(f"Scanning active session plans and checklists: {s_id}", "SCAN")
        
        session_candidates = []
        from datetime import timedelta
        
        # Attempt to parse task.md (checklist)
        checklist_tasks = parse_task_md(task_path)
        if checklist_tasks:
            log(f"Extracted {len(checklist_tasks)} tasks from task.md checklist", "CHECKLIST")
            for t in checklist_tasks:
                mode_test_str = (t["title"] + " " + (t["details"] or "")).lower()
                mode = "coding"
                if any(x in mode_test_str for x in ["plan", "analyse", "recherche", "investig", "document"]):
                    mode = "reasoning"
                elif any(x in mode_test_str for x in ["test", "optimis", "déploy", "build"]):
                    mode = "bulk"
                    
                dt_comp = datetime.fromtimestamp(s_mtime).astimezone()
                dt_start = dt_comp - timedelta(hours=1)
                z = dt_comp.strftime('%z')
                z_fmt = f"{z[:3]}:{z[3:]}" if z else "+01:00"
                
                started_at = dt_start.strftime('%Y-%m-%dT%H:%M:%S') + f".0000000" + z_fmt
                completed_at = dt_comp.strftime('%Y-%m-%dT%H:%M:%S') + f".0000000" + z_fmt
                
                session_candidates.append({
                    "title": t["title"],
                    "details": t["details"],
                    "mode": mode,
                    "status": t["status"],
                    "steps_total": t["steps_total"],
                    "steps_done": t["steps_done"],
                    "source": s_id,
                    "source_type": "plan_checklist_extracted",
                    "detected": today_str,
                    "started_at": None if t["status"] == "todo" else started_at,
                    "completed_at": None if t["status"] == "todo" else completed_at,
                    "steps": t["steps"]
                })
        
        # Fallback to implementation_plan.md if no checklist tasks found
        if not session_candidates:
            plan_tasks = parse_implementation_plan_md(plan_path)
            if plan_tasks:
                log(f"Extracted {len(plan_tasks)} tasks from implementation_plan.md proposed changes", "PLAN")
                for t in plan_tasks:
                    session_candidates.append({
                        "title": t["title"],
                        "details": t["details"],
                        "mode": "coding",
                        "status": "todo",
                        "steps_total": 1,
                        "steps_done": 0,
                        "source": s_id,
                        "source_type": "plan_proposed_changes_extracted",
                        "detected": today_str,
                        "started_at": None,
                        "completed_at": None,
                        "steps": None
                    })
                    
        # Extract explicit user task creation requests (always check)
        user_tasks = []
        task_creation_patterns = [
            r"(?i)(?:c'est\s+)?(?:une?\s+)?(?:nouvelle?|nouveau?|nouvel)\s+(?:tâche|tache|task)\s*[:\-,]?\s*(.+)",
            r"(?i)cr[ée]er?\s+(?:une?|un?|des?)\s+(?:nouvelle?|nouveau?|nouvel)\s+(?:tâche|tache|task)\s*[:\-,]?\s*(.+)",
            r"(?i)(?:it's\s+a\s+)?new\s+task\s*[:\-,]?\s*(.+)",
            r"(?i)create\s+(?:a\s+)?new\s+task\s*[:\-,]?\s*(.+)"
        ]
        
        if os.path.exists(overview_path):
            try:
                lines = read_lines_with_retry(overview_path, errors="ignore")
                for line in lines:
                        try:
                            data = json.loads(line)
                            source = data.get("source")
                            type_ = data.get("type")
                            content = data.get("content", "")
                            
                            if source == "USER_EXPLICIT" and type_ == "USER_INPUT" and content:
                                for pattern in task_creation_patterns:
                                    match = re.search(pattern, content)
                                    if match:
                                        raw_title = match.group(1).strip()
                                        cleaned_title = raw_title.strip().rstrip(".?!,;*:\n").strip()
                                        cleaned_title = re.sub(r'^\s*["\'`]+|["\'`]+\s*$', '', cleaned_title)
                                        cleaned_title = cleaned_title.strip()
                                        
                                        if cleaned_title and len(cleaned_title) >= 5:
                                            task_mode = "coding"
                                            mode_test = cleaned_title.lower()
                                            if any(x in mode_test for x in ["plan", "analyse", "recherche", "investig", "document"]):
                                                task_mode = "reasoning"
                                            elif any(x in mode_test for x in ["test", "optimis", "déploy"]):
                                                task_mode = "bulk"
                                                
                                            user_tasks.append({
                                                "title": cleaned_title,
                                                "details": f"**Tâche créée à partir de la demande utilisateur :**\n- \"{content}\"",
                                                "mode": task_mode,
                                                "status": "todo",
                                                "steps_total": 1,
                                                "steps_done": 0,
                                                "source": s_id,
                                                "source_type": "user_prompt_detected",
                                                "detected": today_str,
                                                "started_at": None,
                                                "completed_at": None,
                                                "steps": None
                                            })
                                            log(f"Detected explicit user task request: [{task_mode}] {cleaned_title}", "USERTASK")
                                        break
                        except:
                            pass
            except Exception as e:
                pass
                
        # If neither checklist nor plan was found, fallback to default agent accomplishments scan
        if not session_candidates:
            modified_files = set()
            accomplishments = []
            
            if os.path.exists(overview_path):
                try:
                    lines = read_lines_with_retry(overview_path, errors="ignore")
                    for line in lines:
                            try:
                                data = json.loads(line)
                                source = data.get("source")
                                type_ = data.get("type")
                                content = data.get("content", "")
                                tool_calls = data.get("tool_calls", [])
                                
                                for tc in tool_calls:
                                    name = tc.get("name")
                                    if name in ["write_to_file", "replace_file_content", "multi_replace_file_content"]:
                                        args = tc.get("args", {})
                                        if isinstance(args, str):
                                            try:
                                                args = json.loads(args)
                                            except:
                                                match = re.search(r'"TargetFile"\s*:\s*"([^"]+)"', args)
                                                if match:
                                                    args = {"TargetFile": match.group(1)}
                                                else:
                                                    args = {}
                                                    
                                        target_file = args.get("TargetFile")
                                        if target_file:
                                            target_file = target_file.replace("\\\\", "\\").replace('"', '')
                                            if target_file.lower().startswith(str(Path(__file__).resolve().parents[4])):
                                                rel = os.path.relpath(target_file, str(Path(__file__).resolve().parents[4]))
                                                if not any(x in rel.lower() for x in [".git", "scratch", "logs", ".gemini", "tempmediastorage"]):
                                                    modified_files.add(rel)
                                                    
                                for source_mod, type_mod, content_mod in [(data.get("source"), data.get("type"), data.get("content", ""))]:
                                    if source_mod == "MODEL" and type_mod == "PLANNER_RESPONSE" and content_mod:
                                        sentences = re.split(r'[.!?\n]+', content_mod)
                                        for sent in sentences:
                                            sent = sent.strip()
                                            if not sent:
                                                continue
                                            match = re.search(r'(?i)\b(j\'ai|nous\s+avons|i\s+have|we\s+have)\b', sent)
                                            if match:
                                                start_idx = match.start()
                                                accomplishment = sent[start_idx:].strip()
                                                if len(accomplishment) >= 15:
                                                    if len(accomplishment) > 120:
                                                        accomplishment = accomplishment[:117].rstrip()
                                                        accomplishment = re.sub(r'\s+\S+$', '', accomplishment)
                                                        accomplishment += "..."
                                                        
                                                    cleaned = clean_accomplishment(accomplishment)
                                                    if cleaned and cleaned not in accomplishments:
                                                        low = cleaned.lower()
                                                        if not any(x in low for x in ["j'ai lu", "j'ai vérifié", "i checked", "i read", "i verified", "j'ai vu"]):
                                                            accomplishments.append(cleaned)
                            except:
                                pass
                except Exception as e:
                    pass
                    
            if modified_files or accomplishments:
                files_list = sorted(list(modified_files))
                title = choose_title_for_session(accomplishments, files_list)
                details = formulate_details(accomplishments, files_list)
                
                mode = "coding"
                mode_test_str = (title + " " + details).lower()
                if any(x in mode_test_str for x in ["plan", "analyse", "recherche", "investig", "document"]):
                    mode = "reasoning"
                elif any(x in mode_test_str for x in ["test", "optimis", "déploy"]):
                    mode = "bulk"
                    
                dt_comp = datetime.fromtimestamp(s_mtime).astimezone()
                dt_start = dt_comp - timedelta(hours=1)
                z = dt_comp.strftime('%z')
                z_fmt = f"{z[:3]}:{z[3:]}" if z else "+01:00"
                
                started_at = dt_start.strftime('%Y-%m-%dT%H:%M:%S') + f".0000000" + z_fmt
                completed_at = dt_comp.strftime('%Y-%m-%dT%H:%M:%S') + f".0000000" + z_fmt
                
                session_candidates.append({
                    "title": title,
                    "details": details,
                    "mode": mode,
                    "status": "done",
                    "steps_total": 1,
                    "steps_done": 1,
                    "source": s_id,
                    "source_type": "agent_action_detected",
                    "detected": today_str,
                    "started_at": started_at,
                    "completed_at": completed_at,
                    "steps": None
                })
                
        # Append all parsed tasks and user tasks for this session to global candidates
        for sc in session_candidates:
            candidates.append(sc)
        for ut in user_tasks:
            candidates.append(ut)

    # Save to queue (with deduplication)
    if candidates:
        seen = set()
        unique_candidates = []
        for c in candidates:
            k = c["title"].lower().strip()
            if k not in seen and k not in existing_titles:
                seen.add(k)
                unique_candidates.append(c)
                
        try:
            content = "".join(json.dumps(uc, ensure_ascii=False) + "\n" for uc in unique_candidates)
            write_file_with_retry(queue_path, content, mode="w")
            for uc in unique_candidates:
                log(f"Registered agent-action task suggestion: {uc['title']}", "AUTOTASK")
        except Exception as e:
            log(f"Error writing queue_path: {e}", "ERROR")
                
        log(f"Successfully loaded {len(unique_candidates)} agent-action tasks into DevCore queue.", "SUCCESS")
    else:
        log("No agent actions detected in recent sessions.", "CLEAN")

if __name__ == "__main__":
    main()

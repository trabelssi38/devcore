import os
import json
import re
import subprocess
from datetime import datetime

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

    log(f"Starting Dynamic Agent-Action Analyzer for project: '{active_proj}'", "INIT")

    # Read existing sources from tasks.json to avoid duplicates
    existing_sources = set()
    tasks_file = os.path.join(queue_dir, "tasks.json")
    if os.path.exists(tasks_file):
        try:
            with open(tasks_file, "r", encoding="utf-8-sig") as tf:
                board = json.load(tf)
                for t in board.get("tasks", []):
                    src = t.get("source")
                    if src:
                        existing_sources.add(src)
            log(f"Loaded {len(existing_sources)} existing task sources to prevent duplicates.", "INIT")
        except Exception as e:
            log(f"Error reading tasks.json to deduplicate: {e}", "WARNING")

    brain_dir = r"C:\Users\trb_m\.gemini\antigravity\brain"
    if not os.path.exists(brain_dir):
        log(f"Brain folder not found: {brain_dir}", "WARNING")
        return

    # Find top 3 most recently modified session folders
    sessions = []
    for d in os.listdir(brain_dir):
        path = os.path.join(brain_dir, d)
        if os.path.isdir(path) and d != "tempmediaStorage":
            overview_path = os.path.join(path, ".system_generated", "logs", "overview.txt")
            if os.path.exists(overview_path):
                sessions.append((path, os.path.getmtime(overview_path), d))

    sessions.sort(key=lambda x: x[1], reverse=True)
    recent_sessions = sessions[:3]

    if not recent_sessions:
        log("No active Antigravity sessions found", "INFO")
        return

    candidates = []

    for s_path, s_mtime, s_id in recent_sessions:
        if s_id in existing_sources:
            log(f"Session {s_id} already exists in tasks.json. Skipping scan.", "SKIP")
            continue
            
        overview_path = os.path.join(s_path, ".system_generated", "logs", "overview.txt")
        log(f"Scanning active session accomplishments: {s_id}", "SCAN")
        
        modified_files = set()
        accomplishments = []
        user_tasks = []
        
        task_creation_patterns = [
            r"(?i)(?:c'est\s+)?(?:une?\s+)?(?:nouvelle?|nouveau?|nouvel)\s+(?:tâche|tache|task)\s*[:\-,]?\s*(.+)",
            r"(?i)cr[ée]er?\s+(?:une?|un?|des?)\s+(?:nouvelle?|nouveau?|nouvel)\s+(?:tâche|tache|task)\s*[:\-,]?\s*(.+)",
            r"(?i)(?:it's\s+a\s+)?new\s+task\s*[:\-,]?\s*(.+)",
            r"(?i)create\s+(?:a\s+)?new\s+task\s*[:\-,]?\s*(.+)"
        ]
        
        try:
            with open(overview_path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        source = data.get("source")
                        type_ = data.get("type")
                        content = data.get("content", "")
                        tool_calls = data.get("tool_calls", [])
                        
                        # Capture modified files from tool calls
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
                                    if target_file.lower().startswith("c:\\devcore"):
                                        rel = os.path.relpath(target_file, "C:\\devcore")
                                        if not any(x in rel.lower() for x in [".git", "scratch", "logs", ".gemini", "tempmediastorage"]):
                                            modified_files.add(rel)
                                            
                        # Capture accomplishments by splitting on sentence boundaries
                        if source == "MODEL" and type_ == "PLANNER_RESPONSE" and content:
                            sentences = re.split(r'[.!?\n]+', content)
                            for sent in sentences:
                                sent = sent.strip()
                                if not sent:
                                    continue
                                # Find starting pronoun/verb
                                match = re.search(r'(?i)\b(j\'ai|nous\s+avons|i\s+have|we\s+have)\b', sent)
                                if match:
                                    start_idx = match.start()
                                    accomplishment = sent[start_idx:].strip()
                                    if len(accomplishment) >= 15:
                                        # Truncate at space boundary if very long
                                        if len(accomplishment) > 120:
                                            accomplishment = accomplishment[:117].rstrip()
                                            accomplishment = re.sub(r'\s+\S+$', '', accomplishment)
                                            accomplishment += "..."
                                            
                                        cleaned = clean_accomplishment(accomplishment)
                                        if cleaned and cleaned not in accomplishments:
                                            low = cleaned.lower()
                                            if not any(x in low for x in ["j'ai lu", "j'ai vérifié", "i checked", "i read", "i verified", "j'ai vu"]):
                                                accomplishments.append(cleaned)
                                                
                        # Capture explicit user task creation requests
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
                                            "completed_at": None
                                        })
                                        log(f"Detected explicit user task request: [{task_mode}] {cleaned_title}", "USERTASK")
                                    break
                    except:
                        pass
        except Exception as e:
            log(f"Error reading session {s_id}: {e}", "ERROR")
            continue
            
        if not modified_files and not accomplishments and not user_tasks:
            log(f"No actions, accomplishments or user tasks in session {s_id}", "SKIP")
            continue
            
        if modified_files or accomplishments:
            files_list = sorted(list(modified_files))
            title = choose_title_for_session(accomplishments, files_list)
            details = formulate_details(accomplishments, files_list)
            
            # Decide mode based on title/details content
            mode = "coding"
            mode_test_str = (title + " " + details).lower()
            if any(x in mode_test_str for x in ["plan", "analyse", "recherche", "investig", "document"]):
                mode = "reasoning"
            elif any(x in mode_test_str for x in ["test", "optimis", "déploy"]):
                mode = "bulk"
                
            # Compute dynamic start and completed times from session folder modification time
            from datetime import timedelta
            dt_comp = datetime.fromtimestamp(s_mtime).astimezone()
            dt_start = dt_comp - timedelta(hours=1)
            z = dt_comp.strftime('%z')
            z_fmt = f"{z[:3]}:{z[3:]}" if z else "+01:00"
            
            started_at = dt_start.strftime('%Y-%m-%dT%H:%M:%S') + f".{dt_start.microsecond:06d}0" + z_fmt
            completed_at = dt_comp.strftime('%Y-%m-%dT%H:%M:%S') + f".{dt_comp.microsecond:06d}0" + z_fmt

            candidates.append({
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
                "completed_at": completed_at
            })
            log(f"Formulated task: [{mode}] {title}", "FORMULATION")
            
        if user_tasks:
            for ut in user_tasks:
                candidates.append(ut)

    # Save to queue (with deduplication)
    if candidates:
        seen = set()
        unique_candidates = []
        for c in candidates:
            k = c["title"].lower()
            if k not in seen:
                seen.add(k)
                unique_candidates.append(c)
                
        with open(queue_path, "w", encoding="utf-8") as q:
            for uc in unique_candidates:
                q.write(json.dumps(uc, ensure_ascii=False) + "\n")
                log(f"Registered agent-action task suggestion: {uc['title']}", "AUTOTASK")
                
        log(f"Successfully loaded {len(unique_candidates)} agent-action tasks into DevCore queue.", "SUCCESS")
    else:
        log("No agent actions detected in recent sessions.", "CLEAN")

if __name__ == "__main__":
    main()

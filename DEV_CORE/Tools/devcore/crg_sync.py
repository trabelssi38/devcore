import os
import ast
import json
import re
import time
import glob

def resolve_files(repo_root):
    target_globs = [
        "DEV_CORE/Scripts/*.ps1",
        "DEV_CORE/Scripts/Auto/*.ps1",
        "DEV_CORE/Tools/devcore/*.py",
        "DEV_CORE/MCP/devcore-scripts/*.py"
    ]
    files = []
    for g in target_globs:
        pattern = os.path.join(repo_root, g.replace("/", os.sep))
        files.extend(glob.glob(pattern))
    return [os.path.relpath(f, repo_root).replace("\\", "/") for f in files]

def parse_python(file_rel_path, file_abs_path):
    nodes = []
    edges = []
    try:
        with open(file_abs_path, 'r', encoding='utf-8') as f:
            content = f.read()
            tree = ast.parse(content)
    except Exception:
        return nodes, edges

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            node_id = f"function:{file_rel_path}/{node.name}"
            nodes.append({
                "id": node_id,
                "type": "function",
                "label": node.name,
                "properties": {"file": file_rel_path}
            })
            edges.append({
                "from": file_rel_path,
                "to": node_id,
                "type": "file_function",
                "properties": {"confidence": "EXTRACTED"}
            })

            # Detect function calls inside this function
            for child in ast.walk(node):
                if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                    edges.append({
                        "from": node_id,
                        "to": f"function:UNKNOWN/{child.func.id}",
                        "type": "function_calls",
                        "properties": {"confidence": "AMBIGUOUS"}
                    })

        elif isinstance(node, ast.ClassDef):
            node_id = f"class:{file_rel_path}/{node.name}"
            nodes.append({
                "id": node_id,
                "type": "class",
                "label": node.name,
                "properties": {"file": file_rel_path}
            })
            for base in node.bases:
                if isinstance(base, ast.Name):
                    edges.append({
                        "from": node_id,
                        "to": f"class:UNKNOWN/{base.id}",
                        "type": "class_inherits",
                        "properties": {"confidence": "EXTRACTED"}
                    })
                    
        elif isinstance(node, ast.Import):
            for alias in node.names:
                node_id = f"import:{file_rel_path}/{alias.name}"
                nodes.append({
                    "id": node_id,
                    "type": "import",
                    "label": alias.name,
                    "properties": {"file": file_rel_path}
                })
                edges.append({
                    "from": file_rel_path,
                    "to": node_id,
                    "type": "file_imports",
                    "properties": {"confidence": "EXTRACTED"}
                })
                
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                for alias in node.names:
                    label = f"{node.module}.{alias.name}"
                    node_id = f"import:{file_rel_path}/{label}"
                    nodes.append({
                        "id": node_id,
                        "type": "import",
                        "label": label,
                        "properties": {"file": file_rel_path}
                    })
                    edges.append({
                        "from": file_rel_path,
                        "to": node_id,
                        "type": "file_imports",
                        "properties": {"confidence": "EXTRACTED"}
                    })

    return nodes, edges

def parse_powershell(file_rel_path, file_abs_path):
    nodes = []
    edges = []
    try:
        with open(file_abs_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return nodes, edges

    func_pattern = re.compile(r'function\s+([a-zA-Z0-9_-]+)', re.IGNORECASE)
    for match in func_pattern.finditer(content):
        func_name = match.group(1)
        node_id = f"function:{file_rel_path}/{func_name}"
        nodes.append({
            "id": node_id,
            "type": "function",
            "label": func_name,
            "properties": {"file": file_rel_path}
        })
        edges.append({
            "from": file_rel_path,
            "to": node_id,
            "type": "file_function",
            "properties": {"confidence": "INFERRED"}
        })

    return nodes, edges

def get_crg_nodes_edges():
    repo_root = r"C:\devcore"
    data_dir = os.path.join(repo_root, "DEV_CORE_DATA", "Knowledge")
    graph_path = os.path.join(data_dir, "crg_graph.json")
    if os.path.exists(graph_path):
        try:
            with open(graph_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("nodes", []), data.get("edges", [])
        except:
            return [], []
    return [], []

def main():
    repo_root = r"C:\devcore"
    data_dir = os.path.join(repo_root, "DEV_CORE_DATA", "Knowledge")
    graph_path = os.path.join(data_dir, "crg_graph.json")
    os.makedirs(data_dir, exist_ok=True)
    
    existing_nodes, existing_edges = get_crg_nodes_edges()
    last_sync = 0
    if os.path.exists(graph_path):
        try:
            with open(graph_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                last_sync = data.get("last_sync", 0)
        except:
            pass

    current_sync = time.time()
    files = resolve_files(repo_root)
    
    files_to_parse = []
    for rel_f in files:
        abs_f = os.path.join(repo_root, rel_f)
        if os.path.exists(abs_f):
            mtime = os.path.getmtime(abs_f)
            if mtime > last_sync:
                files_to_parse.append(rel_f)
                
    if not files_to_parse:
        print("No files modified. Skipping parse.")
        return
        
    print(f"Parsing {len(files_to_parse)} files...")
    
    updated_nodes = [n for n in existing_nodes if n.get("properties", {}).get("file") not in files_to_parse]
    updated_edges = [e for e in existing_edges if e.get("from") not in files_to_parse]
    
    for rel_f in files_to_parse:
        abs_f = os.path.join(repo_root, rel_f)
        if rel_f.endswith('.py'):
            n, e = parse_python(rel_f, abs_f)
            updated_nodes.extend(n)
            updated_edges.extend(e)
        elif rel_f.endswith('.ps1'):
            n, e = parse_powershell(rel_f, abs_f)
            updated_nodes.extend(n)
            updated_edges.extend(e)
            
    graph_data = {
        "last_sync": current_sync,
        "nodes": updated_nodes,
        "edges": updated_edges
    }
    
    with open(graph_path, 'w', encoding='utf-8') as f:
        json.dump(graph_data, f, indent=2)
        
    print(f"CRG Graph saved. Nodes: {len(updated_nodes)}, Edges: {len(updated_edges)}")

if __name__ == "__main__":
    main()

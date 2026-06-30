# init_conversations_db.py -- DEV_CORE v8.0
# Initialise la base de données SQLite L0 conversations.db
import sqlite3
import os
import sys

devcore_data = os.environ.get("DEVCORE_DATA_ROOT", "C:\\devcore\\DEV_CORE_DATA")
memory_dir = os.path.join(devcore_data, "Memory")
db_path = os.path.join(memory_dir, "conversations.db")

print(f"Initialisation de SQLite conversations.db à {db_path}...")

if not os.path.exists(memory_dir):
    os.makedirs(memory_dir, exist_ok=True)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Créer la table principale
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_date TEXT NOT NULL,
        project TEXT NOT NULL,
        task_id TEXT,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        tokens_estimate INTEGER,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # Créer les index
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_conv_date ON conversations(session_date);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_conv_project ON conversations(project);")
    
    # Créer la table virtuelle FTS5 pour recherche textuelle rapide si supportée
    try:
        cursor.execute("CREATE VIRTUAL TABLE IF NOT EXISTS conversations_fts USING fts5(content, project, task_id);")
        # Trigger de sync FTS5
        cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS after_conversations_insert AFTER INSERT ON conversations BEGIN
            INSERT INTO conversations_fts(content, project, task_id) VALUES (new.content, new.project, new.task_id);
        END;
        """)
        print("Table FTS5 de recherche plein texte configurée.")
    except sqlite3.OperationalError as e:
        print(f"FTS5 non supporté par cette version de SQLite ({e}), fallback sans FTS.")
        
    conn.commit()
    conn.close()
    print("Initialisation de conversations.db terminée avec succès.")
    sys.exit(0)
except Exception as e:
    print(f"Erreur d'initialisation de conversations.db : {e}")
    sys.exit(1)

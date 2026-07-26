# init_conversations_db.py -- DEV_CORE v9.0
# Initialise la base de données SQLite L0 conversations.db
import sqlite3
import os
import sys

devcore_data = os.environ.get("DEVCORE_DATA_ROOT", str(Path(__file__).resolve().parents[3] / "DEV_CORE_DATA"))
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
        # Triggers de sync FTS5
        cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS after_conversations_insert AFTER INSERT ON conversations BEGIN
            INSERT INTO conversations_fts(rowid, content, project, task_id) VALUES (new.id, new.content, new.project, new.task_id);
        END;
        """)
        cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS after_conversations_update AFTER UPDATE ON conversations BEGIN
            UPDATE conversations_fts SET content = new.content, project = new.project, task_id = new.task_id WHERE rowid = new.id;
        END;
        """)
        cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS after_conversations_delete AFTER DELETE ON conversations BEGIN
            DELETE FROM conversations_fts WHERE rowid = old.id;
        END;
        """)
        print("Table FTS5 et triggers de synchronisation configurés avec succès.")
    except sqlite3.OperationalError as e:
        print(f"Erreur de configuration FTS5 SQLite : {e}")
        sys.exit(1)
        
    conn.commit()
    conn.close()
    print("Initialisation de conversations.db terminée avec succès.")
    sys.exit(0)
except Exception as e:
    print(f"Erreur d'initialisation de conversations.db : {e}")
    sys.exit(1)

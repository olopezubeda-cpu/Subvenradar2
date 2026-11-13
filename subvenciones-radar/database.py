import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "radar.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # User Profile table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_profile (
        id INTEGER PRIMARY KEY,
        region TEXT NOT NULL,
        age_bracket TEXT NOT NULL,
        user_types TEXT NOT NULL, -- JSON array: ["autonomo", "pyme", "estudiante"]
        interests TEXT NOT NULL,  -- JSON array: ["digitalizacion", "subvenciones", "formacion"]
        email TEXT DEFAULT '',
        notify_weekly INTEGER DEFAULT 1,
        smtp_host TEXT DEFAULT '',
        smtp_port INTEGER DEFAULT 587,
        smtp_user TEXT DEFAULT '',
        smtp_password TEXT DEFAULT '',
        smtp_sender TEXT DEFAULT '',
        last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Grants / Subsidies table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS grants (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        entity TEXT NOT NULL,
        scope TEXT NOT NULL, -- 'Autonómica', 'Estatal', 'Europea'
        region TEXT NOT NULL, -- e.g. 'Comunitat Valenciana', 'Nacional', 'Unión Europea'
        amount TEXT NOT NULL,
        summary TEXT NOT NULL,
        requirements TEXT NOT NULL,
        target_audience TEXT NOT NULL,
        category TEXT NOT NULL, -- 'Emprendimiento y Autónomos', 'Digitalización e Innovación', 'Formación y Becas'
        deadline TEXT NOT NULL,
        deadline_date TEXT,
        official_url TEXT NOT NULL,
        bdns_code TEXT DEFAULT '',
        source_name TEXT NOT NULL,
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Bookmarks / Saved grants
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bookmarks (
        grant_id TEXT PRIMARY KEY,
        status TEXT DEFAULT 'Guardada', -- 'Guardada', 'En preparación', 'Solicitada', 'Concedida'
        notes TEXT DEFAULT '',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(grant_id) REFERENCES grants(id)
    );
    """)

    # Digest logs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS digest_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        recipient TEXT NOT NULL,
        grants_count INTEGER NOT NULL,
        subject TEXT NOT NULL,
        status TEXT NOT NULL, -- 'Simulado / Vista previa', 'Enviado con éxito', 'Error'
        error_message TEXT DEFAULT '',
        html_preview TEXT NOT NULL
    );
    """)

    # Populate initial default user profile (Comunitat Valenciana, >45 años)
    cursor.execute("SELECT COUNT(*) FROM user_profile")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO user_profile (id, region, age_bracket, user_types, interests, email, notify_weekly)
        VALUES (
            1,
            'Comunitat Valenciana',
            'Más de 45 años',
            ?,
            ?,
            'usuario@ejemplo.com',
            1
        )
        """, (
            json.dumps(["autonomo", "emprendedor", "pyme", "estudiante"]),
            json.dumps(["digitalizacion", "subvenciones a fondo perdido", "innovacion", "formacion continua", "idiomas", "recualificacion"])
        ))

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Base de datos inicializada correctamente.")

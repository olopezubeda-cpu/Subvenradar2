import os
import json
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from pydantic import BaseModel
from typing import List, Optional

from database import init_db, get_connection
from sources import get_all_grants
from matcher import calculate_match
from notifier import send_or_preview_digest

app = FastAPI(title="SubvenRadar - Becas y Ayudas")

# Inicializar DB al arranque
init_db()

# Cargar subvenciones iniciales en SQLite si está vacío
def seed_grants_if_empty():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM grants")
    count = cursor.fetchone()[0]
    if count == 0:
        grants = get_all_grants()
        for g in grants:
            cursor.execute("""
            INSERT OR REPLACE INTO grants 
            (id, title, entity, scope, region, amount, summary, requirements, target_audience, category, deadline, deadline_date, official_url, bdns_code, source_name, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                g["id"], g["title"], g["entity"], g["scope"], g["region"], g["amount"],
                g["summary"], g["requirements"], g["target_audience"], g["category"],
                g["deadline"], g.get("deadline_date"), g["official_url"], g.get("bdns_code", ""),
                g["source_name"]
            ))
        conn.commit()
    conn.close()

seed_grants_if_empty()

# Montar estáticos
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def read_root():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return HTMLResponse("<h1>SubvenRadar Activo</h1>")

@app.get("/sw.js")
def read_service_worker():
    sw_file = os.path.join(static_dir, "sw.js")
    return FileResponse(sw_file, media_type="application/javascript")

@app.get("/api/profile")
def get_user_profile():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_profile WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")
    
    p = dict(row)
    try:
        p["user_types"] = json.loads(p["user_types"])
    except Exception:
        p["user_types"] = []
    try:
        p["interests"] = json.loads(p["interests"])
    except Exception:
        p["interests"] = []
    # Ocultar contraseña SMTP por seguridad
    if p.get("smtp_password"):
        p["has_smtp_password"] = True
        p["smtp_password"] = "******"
    else:
        p["has_smtp_password"] = False
    return p

class ProfileUpdate(BaseModel):
    region: str
    age_bracket: str
    user_types: List[str]
    interests: List[str]
    email: Optional[str] = ""
    notify_weekly: Optional[int] = 1
    smtp_host: Optional[str] = ""
    smtp_port: Optional[int] = 587
    smtp_user: Optional[str] = ""
    smtp_password: Optional[str] = None
    smtp_sender: Optional[str] = ""

@app.post("/api/profile")
def update_user_profile(profile_data: ProfileUpdate):
    conn = get_connection()
    cursor = conn.cursor()
    
    # Manejar contraseña sin sobreescribir si viene oculta
    if profile_data.smtp_password == "******" or profile_data.smtp_password is None:
        cursor.execute("""
        UPDATE user_profile SET
            region = ?,
            age_bracket = ?,
            user_types = ?,
            interests = ?,
            email = ?,
            notify_weekly = ?,
            smtp_host = ?,
            smtp_port = ?,
            smtp_user = ?,
            smtp_sender = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = 1
        """, (
            profile_data.region,
            profile_data.age_bracket,
            json.dumps(profile_data.user_types),
            json.dumps(profile_data.interests),
            profile_data.email,
            profile_data.notify_weekly,
            profile_data.smtp_host,
            profile_data.smtp_port,
            profile_data.smtp_user,
            profile_data.smtp_sender
        ))
    else:
        cursor.execute("""
        UPDATE user_profile SET
            region = ?,
            age_bracket = ?,
            user_types = ?,
            interests = ?,
            email = ?,
            notify_weekly = ?,
            smtp_host = ?,
            smtp_port = ?,
            smtp_user = ?,
            smtp_password = ?,
            smtp_sender = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = 1
        """, (
            profile_data.region,
            profile_data.age_bracket,
            json.dumps(profile_data.user_types),
            json.dumps(profile_data.interests),
            profile_data.email,
            profile_data.notify_weekly,
            profile_data.smtp_host,
            profile_data.smtp_port,
            profile_data.smtp_user,
            profile_data.smtp_password,
            profile_data.smtp_sender
        ))
        
    conn.commit()
    conn.close()
    return {"success": True, "message": "Perfil actualizado correctamente"}

@app.get("/api/grants")
def list_grants(
    scope: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    min_score: int = 0
):
    conn = get_connection()
    cursor = conn.cursor()
    
    # Obtener perfil para scoring
    cursor.execute("SELECT * FROM user_profile WHERE id = 1")
    profile = dict(cursor.fetchone())
    
    # Obtener bookmarks para saber cuáles están guardadas
    cursor.execute("SELECT grant_id, status FROM bookmarks")
    bookmarks_map = {row["grant_id"]: row["status"] for row in cursor.fetchall()}
    
    cursor.execute("SELECT * FROM grants WHERE is_active = 1")
    rows = cursor.fetchall()
    conn.close()

    results = []
    search_term = (search or "").lower().strip()

    for r in rows:
        g = dict(r)
        # Filtro de ámbito
        if scope and scope != "Todas" and g["scope"].lower() != scope.lower():
            continue
        # Filtro de categoría
        if category and category != "Todas" and category.lower() not in g["category"].lower():
            continue
        # Búsqueda por texto
        if search_term:
            matchable_text = f"{g['title']} {g['entity']} {g['summary']} {g['requirements']}".lower()
            if search_term not in matchable_text:
                continue

        # Calcular scoring de coincidencia
        match_info = calculate_match(g, profile)
        if match_info["score"] < min_score:
            continue

        g["match"] = match_info
        g["bookmarked"] = g["id"] in bookmarks_map
        g["bookmark_status"] = bookmarks_map.get(g["id"], None)
        results.append(g)

    # Ordenar por afinidad descendente
    results.sort(key=lambda x: x["match"]["score"], reverse=True)
    return results

@app.post("/api/bookmarks/{grant_id}")
def toggle_bookmark(grant_id: str, action: dict = Body(...)):
    status = action.get("status", "Guardada") # 'Guardada' o 'Eliminar'
    notes = action.get("notes", "")
    conn = get_connection()
    cursor = conn.cursor()
    
    if status == "Eliminar":
        cursor.execute("DELETE FROM bookmarks WHERE grant_id = ?", (grant_id,))
    else:
        cursor.execute("""
        INSERT INTO bookmarks (grant_id, status, notes, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(grant_id) DO UPDATE SET
            status = excluded.status,
            notes = excluded.notes,
            updated_at = CURRENT_TIMESTAMP
        """, (grant_id, status, notes))
        
    conn.commit()
    conn.close()
    return {"success": True, "grant_id": grant_id, "status": status}

@app.get("/api/bookmarks")
def get_bookmarks():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT b.grant_id, b.status as bookmark_status, b.notes, b.updated_at,
           g.title, g.entity, g.scope, g.region, g.amount, g.deadline, g.official_url, g.category
    FROM bookmarks b
    JOIN grants g ON b.grant_id = g.id
    ORDER BY b.updated_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/grants/sync")
def sync_grants():
    """Vuelve a sincronizar con las fuentes y actualiza la base de datos."""
    new_grants = get_all_grants()
    conn = get_connection()
    cursor = conn.cursor()
    count = 0
    for g in new_grants:
        cursor.execute("""
        INSERT OR REPLACE INTO grants 
        (id, title, entity, scope, region, amount, summary, requirements, target_audience, category, deadline, deadline_date, official_url, bdns_code, source_name, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (
            g["id"], g["title"], g["entity"], g["scope"], g["region"], g["amount"],
            g["summary"], g["requirements"], g["target_audience"], g["category"],
            g["deadline"], g.get("deadline_date"), g["official_url"], g.get("bdns_code", ""),
            g["source_name"]
        ))
        count += 1
    conn.commit()
    conn.close()
    return {"success": True, "synced_count": count, "message": f"{count} convocatorias verificadas y sincronizadas."}

@app.post("/api/digest/send")
def trigger_digest(force_email: bool = False):
    """Genera el boletín semanal filtrado y lo emite o guarda para previsualización."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_profile WHERE id = 1")
    profile = dict(cursor.fetchone())
    conn.close()

    # Obtener las subvenciones ordenadas por compatibilidad
    grants = list_grants(min_score=60)
    result = send_or_preview_digest(grants, profile, force_live_email=force_email)
    return result

@app.get("/api/digest/latest")
def get_latest_digest():
    """Devuelve el HTML del último boletín generado."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM digest_logs ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if not row:
        # Generar uno nuevo si no existe todavía
        grants = list_grants(min_score=60)
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_profile WHERE id = 1")
        profile = dict(cursor.fetchone())
        conn.close()
        send_or_preview_digest(grants, profile)
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM digest_logs ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()

    return HTMLResponse(content=row["html_preview"])

@app.get("/api/stats")
def get_stats():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM grants WHERE is_active = 1")
    total_grants = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM grants WHERE scope = 'Autonómica'")
    cv_grants = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM bookmarks")
    saved_count = cursor.fetchone()[0]
    conn.close()
    return {
        "total_grants": total_grants,
        "cv_grants": cv_grants,
        "saved_count": saved_count
    }

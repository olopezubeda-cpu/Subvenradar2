import time
import sys
import os
from datetime import datetime

# Asegurar import de módulos del proyecto
sys.path.append(os.path.dirname(__file__))

from database import init_db, get_connection
from sources import get_all_grants
from matcher import calculate_match
from notifier import send_or_preview_digest

def run_weekly_check(force_live_email: bool = False):
    """
    Ejecución del ciclo semanal:
    1. Sincroniza fuentes oficiales (BDNS, BOE, GVA, UE)
    2. Carga el perfil del usuario (Comunitat Valenciana, >45 años, intereses)
    3. Filtra convocatorias afines
    4. Emite el boletín semanal por correo o genera la entrega
    """
    print(f"[{datetime.now().isoformat()}] Iniciando comprobación periódica de subvenciones y becas...")
    init_db()

    # 1. Sincronizar catálogo
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_profile WHERE id = 1")
    profile_row = cursor.fetchone()
    if not profile_row:
        print("Perfil no encontrado. Abortando.")
        conn.close()
        return
    profile = dict(profile_row)

    grants = get_all_grants()
    updated_count = 0
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
        updated_count += 1
    conn.commit()

    # 2. Filtrar por compatibilidad
    cursor.execute("SELECT * FROM grants WHERE is_active = 1")
    all_active = [dict(r) for r in cursor.fetchall()]
    conn.close()

    matched_grants = []
    for g in all_active:
        m = calculate_match(g, profile)
        if m["score"] >= 60:
            g["match"] = m
            matched_grants.append(g)

    matched_grants.sort(key=lambda x: x["match"]["score"], reverse=True)
    print(f"Convocatorias analizadas: {len(all_active)}. Convocatorias de alta compatibilidad encontradas: {len(matched_grants)}")

    # 3. Emitir boletín
    result = send_or_preview_digest(matched_grants, profile, force_live_email=force_live_email)
    print(f"Resultado del boletín: {result['status']} | Destinatario: {result['recipient']}")
    return result

if __name__ == "__main__":
    run_weekly_check()

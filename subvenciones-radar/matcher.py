import json
import re

def calculate_match(grant: dict, profile: dict) -> dict:
    """
    Evalúa la afinidad entre el perfil del usuario y una convocatoria específica.
    Devuelve un diccionario con score (0-100), compatibilidad cualitativa y motivos clave.
    """
    user_region = profile.get("region", "Comunitat Valenciana").strip().lower()
    user_age = profile.get("age_bracket", "Más de 45 años").strip().lower()
    
    # Manejar user_types e interests si vienen como string JSON o lista
    user_types = profile.get("user_types", [])
    if isinstance(user_types, str):
        try:
            user_types = json.loads(user_types)
        except Exception:
            user_types = [user_types]
            
    interests = profile.get("interests", [])
    if isinstance(interests, str):
        try:
            interests = json.loads(interests)
        except Exception:
            interests = [interests]

    score = 0
    reasons = []

    grant_title = grant.get("title", "").lower()
    grant_summary = grant.get("summary", "").lower()
    grant_reqs = grant.get("requirements", "").lower()
    grant_target = grant.get("target_audience", "").lower()
    grant_scope = grant.get("scope", "").lower()
    grant_region = grant.get("region", "").lower()
    grant_cat = grant.get("category", "").lower()
    full_text = f"{grant_title} {grant_summary} {grant_reqs} {grant_target} {grant_cat}"

    # 1. Filtro y afinidad geográfica (Máx 35 pts)
    if user_region in grant_region or "valencian" in grant_region or "gva" in grant_text_entity(grant):
        score += 35
        reasons.append("🎯 Específica de la Comunitat Valenciana")
    elif "estatal" in grant_scope or "nacional" in grant_region or "españa" in grant_region:
        score += 30
        reasons.append("🇪🇸 Ámbito Nacional (aplicable en toda España)")
    elif "europea" in grant_scope or "unión europea" in grant_region or "eu" in grant_region:
        score += 25
        reasons.append("🇪🇺 Fondos y Programas de la Unión Europea")
    else:
        # Si es de otra CCAA específica sin ser la del usuario, penalizar
        score += 5

    # 2. Filtro y afinidad de edad (>45 años) (Máx 25 pts)
    is_senior = "45" in user_age or "senior" in user_age
    youth_patterns = ["menor de 30", "menores de 30", "hasta 29 años", "garantía juvenil", "menores de 25"]
    
    # Comprobar si exige exclusivamente ser joven
    exclusively_youth = any(p in grant_reqs or p in grant_target for p in youth_patterns)
    if exclusively_youth and not ("45" in full_text or "cualquier edad" in full_text):
        score -= 50 # Descartar o penalizar drásticamente ayudas juveniles incompatibles
    elif is_senior:
        senior_patterns = ["45", "mayores de 45", "senior", "sénior", "adultos", "recualificación", "formación permanente", "consolidación"]
        if any(p in full_text for p in senior_patterns):
            score += 25
            reasons.append("⭐ Ventaja / Tramo prioritario para mayores de 45 años")
        else:
            # Es de acceso universal para adultos/autónomos
            score += 15

    # 3. Afinidad de Intereses (Máx 40 pts)
    # A) Emprendimiento, Pymes, Autónomos
    biz_keywords = ["autónomo", "autónomos", "pyme", "empresa", "emprendedor", "negocio", "autoempleo", "reta"]
    if any(k in full_text for k in biz_keywords):
        score += 20
        if "a fondo perdido" in full_text or "subvención directa" in full_text or "bonificación" in full_text:
            reasons.append("💰 Subvención a fondo perdido / Ahorro de cuota")
        else:
            reasons.append("🏢 Financiación para autónomos y pymes")

    # B) Digitalización e Innovación
    tech_keywords = ["digitaliza", "digital", "kit digital", "ia", "inteligencia artificial", "innovación", "tecnolog"]
    if any(k in full_text for k in tech_keywords):
        score += 15
        reasons.append("🚀 Enfoque en digitalización y modernización")

    # C) Formación, Becas y Estudios
    study_keywords = ["beca", "formación", "curso", "master", "máster", "idioma", "competencias", "microcrédito", "erasmus"]
    if any(k in full_text for k in study_keywords):
        score += 15
        reasons.append("🎓 Beca de formación / Cualificación profesional")

    # Normalización del score (entre 20 y 99)
    final_score = max(min(score, 99), 20)

    # Nivel de compatibilidad
    if final_score >= 85:
        level = "Alta compatibilidad"
        badge_color = "green"
    elif final_score >= 65:
        level = "Buena opción"
        badge_color = "blue"
    else:
        level = "Oportunidad general"
        badge_color = "gray"

    return {
        "score": final_score,
        "level": level,
        "badge_color": badge_color,
        "reasons": reasons[:3] # Los 3 motivos más destacados
    }

def grant_text_entity(grant: dict) -> str:
    return (grant.get("entity", "") + " " + grant.get("source_name", "")).lower()

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import json
import sqlite3
from database import get_connection

def build_digest_html(grants: list, profile: dict) -> str:
    """Genera la plantilla HTML responsive y moderna para el boletín semanal."""
    user_region = profile.get("region", "Comunitat Valenciana")
    user_age = profile.get("age_bracket", "Más de 45 años")
    email_target = profile.get("email", "tu-correo@ejemplo.com")
    today_str = datetime.now().strftime("%d de %B de %Y")

    items_html = ""
    for g in grants[:7]: # Top 7 mejores convocatorias
        match_info = g.get("match", {})
        score = match_info.get("score", 85)
        reasons = match_info.get("reasons", [])
        reasons_tags = "".join([f'<span style="display:inline-block;background:#ecfdf5;color:#065f46;font-size:12px;font-weight:600;padding:3px 8px;border-radius:12px;margin-right:6px;margin-bottom:6px;">{r}</span>' for r in reasons])

        scope_badge_color = "#3b82f6" if g.get("scope") == "Autonómica" else ("#10b981" if g.get("scope") == "Estatal" else "#8b5cf6")
        
        items_html += f"""
        <div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:12px;padding:20px;margin-bottom:20px;box-shadow:0 1px 3px rgba(0,0,0,0.05);">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px;">
                <span style="background:{scope_badge_color};color:#ffffff;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;padding:3px 8px;border-radius:6px;">
                    {g.get("scope", "Oficial")} &bull; {g.get("region", "")}
                </span>
                <span style="background:#fef3c7;color:#92400e;font-size:12px;font-weight:700;padding:3px 10px;border-radius:12px;">
                    ⚡ {score}% Afinidad
                </span>
            </div>
            
            <h3 style="color:#0f172a;font-size:18px;font-weight:700;margin:0 0 8px 0;line-height:1.3;">
                {g.get("title", "")}
            </h3>
            
            <p style="color:#64748b;font-size:13px;margin:0 0 12px 0;">
                <strong>Organismo:</strong> {g.get("entity", "")}
            </p>

            <div style="background:#f8fafc;border-left:4px solid #10b981;padding:10px 14px;border-radius:0 8px 8px 0;margin-bottom:14px;">
                <span style="color:#0f172a;font-weight:700;font-size:15px;display:block;">
                    💵 Cuantía: {g.get("amount", "Consultar bases")}
                </span>
                <span style="color:#475569;font-size:12px;display:block;margin-top:2px;">
                    ⏳ Plazo: {g.get("deadline", "Abierta")}
                </span>
            </div>

            <p style="color:#334155;font-size:14px;line-height:1.5;margin:0 0 14px 0;">
                {g.get("summary", "")}
            </p>

            <div style="margin-bottom:16px;">
                {reasons_tags}
            </div>

            <div>
                <a href="{g.get('official_url', '#')}" target="_blank" style="display:inline-block;background:#2563eb;color:#ffffff;text-decoration:none;font-size:13px;font-weight:600;padding:10px 18px;border-radius:8px;">
                    Ver bases y tramitar solicitud &rarr;
                </a>
            </div>
        </div>
        """

    full_html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Boletín Semanal de Subvenciones y Becas</title>
    </head>
    <body style="margin:0;padding:0;background-color:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
        <div style="max-width:640px;margin:0 auto;background:#f8fafc;padding:24px 16px;">
            
            <!-- Header -->
            <div style="background:linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);padding:28px 24px;border-radius:16px;color:#ffffff;text-align:center;margin-bottom:24px;">
                <span style="background:rgba(255,255,255,0.2);padding:4px 12px;border-radius:20px;font-size:12px;text-transform:uppercase;letter-spacing:1px;font-weight:600;">
                    SubvenRadar Semanal
                </span>
                <h1 style="font-size:24px;font-weight:800;margin:12px 0 6px 0;">
                    Novedades de Subvenciones y Becas
                </h1>
                <p style="font-size:14px;opacity:0.9;margin:0;">
                    Convocatorias seleccionadas a tu medida para la <strong>{user_region}</strong>, España y Europa.
                </p>
            </div>

            <!-- Profile Summary Card -->
            <div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:12px;padding:14px 18px;margin-bottom:20px;font-size:13px;color:#475569;">
                <strong style="color:#0f172a;">Tu perfil activo:</strong> {user_region} &bull; Rango: {user_age} &bull; Áreas: Autónomos/Pymes, Innovación y Formación continua.
            </div>

            <!-- Grants List -->
            {items_html}

            <!-- Footer -->
            <div style="text-align:center;padding:24px 12px;color:#94a3b8;font-size:12px;line-height:1.5;">
                <p style="margin:0 0 6px 0;">
                    Has recibido este resumen porque está activado el boletín semanal en tu <strong>SubvenRadar</strong>.
                </p>
                <p style="margin:0;">
                    Fuentes oficiales: BDNS, BOE, DOGV, LABORA, IVACE y Comisión Europea.
                </p>
            </div>

        </div>
    </body>
    </html>
    """
    return full_html

def send_or_preview_digest(grants: list, profile: dict, force_live_email: bool = False) -> dict:
    """
    Envía el correo si las credenciales SMTP están configuradas o genera un registro
    de vista previa interactiva listo para abrir en el móvil o navegador.
    """
    html_content = build_digest_html(grants, profile)
    recipient = profile.get("email", "").strip() or "usuario@ejemplo.com"
    subject = f"📋 Resumen semanal: {len(grants)} subvenciones y becas para ti ({profile.get('region', 'CV')})"

    smtp_host = profile.get("smtp_host", "").strip()
    smtp_port = profile.get("smtp_port", 587)
    smtp_user = profile.get("smtp_user", "").strip()
    smtp_pass = profile.get("smtp_password", "").strip()
    smtp_sender = profile.get("smtp_sender", "").strip() or smtp_user

    status = "Vista previa generada"
    error_msg = ""

    if force_live_email and smtp_host and smtp_user and smtp_pass:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = smtp_sender
            msg["To"] = recipient
            msg.attach(MIMEText(html_content, "html"))

            with smtplib.SMTP(smtp_host, int(smtp_port), timeout=10) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
            status = "Enviado con éxito por correo"
        except Exception as e:
            status = "Error al enviar SMTP"
            error_msg = str(e)
    else:
        status = "Boletín semanal generado (Modo simulación / Vista previa listo)"

    # Guardar en base de datos el registro del envío
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO digest_logs (recipient, grants_count, subject, status, error_message, html_preview)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (recipient, len(grants), subject, status, error_msg, html_content))
    conn.commit()
    log_id = cursor.lastrowid
    conn.close()

    return {
        "success": True,
        "status": status,
        "recipient": recipient,
        "subject": subject,
        "grants_count": len(grants),
        "log_id": log_id,
        "error_message": error_msg,
        "html_preview": html_content
    }

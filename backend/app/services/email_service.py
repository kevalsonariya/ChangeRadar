"""Asynchronous and synchronous email delivery service for ChangeRadar.

Handles user email verification and personalized change detection alerts.
Implements bounded timeouts, secure credential handling, and graceful failure isolation.
"""

import asyncio
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger("changeradar.email")

# Timeout in seconds for SMTP operations
SMTP_TIMEOUT = 10


def _load_env_file():
    """Load configuration from .env file into os.environ if present."""
    candidates = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parent.parent.parent / ".env",
        Path(__file__).resolve().parent.parent.parent.parent / ".env",
    ]
    for env_path in candidates:
        if env_path.is_file():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip("'\"")
                            if k not in os.environ or not os.environ[k]:
                                os.environ[k] = v
                break
            except Exception:
                pass


_load_env_file()


def is_smtp_configured() -> bool:
    """Check if SMTP credentials and configuration are provided."""
    _load_env_file()
    enabled = os.getenv("EMAIL_NOTIFICATIONS_ENABLED", "true").lower() in ("true", "1", "yes")
    host = os.getenv("SMTP_HOST", "").strip()
    username = os.getenv("SMTP_USERNAME", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()
    return bool(enabled and host and username and password)


def get_smtp_config():
    """Retrieve SMTP settings from environment securely."""
    return {
        "enabled": os.getenv("EMAIL_NOTIFICATIONS_ENABLED", "true").lower() in ("true", "1", "yes"),
        "host": os.getenv("SMTP_HOST", "smtp.gmail.com").strip(),
        "port": int(os.getenv("SMTP_PORT", "587")),
        "username": os.getenv("SMTP_USERNAME", "").strip(),
        "password": os.getenv("SMTP_PASSWORD", "").strip(),
        "from_email": os.getenv("SMTP_FROM_EMAIL", os.getenv("SMTP_USERNAME", "no-reply@changeradar.local")).strip(),
        "frontend_url": os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/"),
    }


def _send_email_sync(recipient_email: str, subject: str, html_body: str, text_body: str) -> Tuple[bool, Optional[str]]:
    """Synchronous worker that connects to SMTP, executes STARTTLS, logs in, and delivers email."""
    config = get_smtp_config()
    if not config["enabled"]:
        return False, "Email delivery is disabled in server configuration (EMAIL_NOTIFICATIONS_ENABLED=false)."

    if not config["host"] or not config["username"] or not config["password"]:
        return False, "SMTP configuration is incomplete. Please set SMTP_HOST, SMTP_USERNAME, and SMTP_PASSWORD."

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"ChangeRadar Alerts <{config['from_email']}>"
    msg["To"] = recipient_email

    # Attach both plain text and rich HTML alternatives
    part1 = MIMEText(text_body, "plain", "utf-8")
    part2 = MIMEText(html_body, "html", "utf-8")
    msg.attach(part1)
    msg.attach(part2)

    try:
        if config["port"] == 465:
            server = smtplib.SMTP_SSL(config["host"], config["port"], timeout=SMTP_TIMEOUT)
        else:
            server = smtplib.SMTP(config["host"], config["port"], timeout=SMTP_TIMEOUT)
            server.ehlo()
            server.starttls()
            server.ehlo()

        server.login(config["username"], config["password"])
        server.send_message(msg)
        server.quit()
        logger.info(f"Successfully sent email '{subject}' to {recipient_email}")
        return True, None
    except Exception as exc:
        err_msg = f"Failed to send email to {recipient_email}: {str(exc)}"
        logger.warning(err_msg)
        return False, err_msg


async def send_email(recipient_email: str, subject: str, html_body: str, text_body: str) -> Tuple[bool, Optional[str]]:
    """Send email asynchronously in a background thread to avoid blocking the asyncio event loop."""
    return await asyncio.to_thread(_send_email_sync, recipient_email, subject, html_body, text_body)


async def send_verification_email(recipient_name: str, recipient_email: str, token: str) -> Tuple[bool, Optional[str]]:
    """Send an account verification email containing a secure single-use link."""
    config = get_smtp_config()
    verification_link = f"{config['frontend_url']}?verify_token={token}"

    subject = "Verify your ChangeRadar account"
    text_body = f"""Hello {recipient_name},

Thank you for registering with ChangeRadar.

Please verify your email address to enable personalized email alert delivery by visiting the link below:
{verification_link}

This link will expire in 24 hours. If you did not create this account, please ignore this email.

Best regards,
ChangeRadar Team
"""

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #0b1120; color: #f8fafc; padding: 24px;">
      <div style="max-width: 560px; margin: 0 auto; background-color: #0f172a; border: 1px solid #1e293b; border-radius: 12px; padding: 32px; box-shadow: 0 10px 25px rgba(0,0,0,0.5);">
        <div style="margin-bottom: 24px; display: flex; align-items: center;">
          <h2 style="color: #14b8a6; margin: 0; font-size: 24px; font-weight: 700; letter-spacing: -0.5px;">ChangeRadar</h2>
        </div>
        <h3 style="color: #f1f5f9; margin-top: 0;">Verify your email address</h3>
        <p style="color: #94a3b8; font-size: 15px; line-height: 1.6;">Hello <strong>{recipient_name}</strong>,</p>
        <p style="color: #94a3b8; font-size: 15px; line-height: 1.6;">Welcome to ChangeRadar! Please verify your email address so we can deliver timely notifications when monitored webpages or deadlines change.</p>
        <div style="margin: 32px 0;">
          <a href="{verification_link}" style="display: inline-block; background-color: #0d9488; color: #ffffff; text-decoration: none; padding: 12px 24px; border-radius: 8px; font-weight: 600; font-size: 15px; box-shadow: 0 4px 12px rgba(13, 148, 136, 0.3);">
            Verify Email Address
          </a>
        </div>
        <p style="color: #64748b; font-size: 13px; line-height: 1.5;">Or copy and paste this verification code/link into your browser:<br>
          <code style="display: block; margin-top: 8px; padding: 8px; background-color: #090d16; border-radius: 6px; color: #38bdf8; word-break: break-all; font-size: 12px;">{verification_link}</code>
        </p>
        <p style="color: #64748b; font-size: 12px; margin-top: 32px; border-top: 1px solid #1e293b; padding-top: 16px;">This link expires in 24 hours. If you did not create a ChangeRadar account, you can safely ignore this message.</p>
      </div>
    </body>
    </html>
    """

    if not is_smtp_configured():
        logger.info(f"[DEV MODE] SMTP not configured. Verification link for {recipient_email}: {verification_link}")
        return False, "SMTP is not fully configured on server. In development, use the manual verification token or configure SMTP credentials."

    return await send_email(recipient_email, subject, html_body, text_body)


async def send_change_alert_email(
    recipient_name: str,
    recipient_email: str,
    website_name: str,
    website_url: str,
    summary: str,
    additions_count: int,
    deletions_count: int,
    change_type: str = "modification"
) -> Tuple[bool, Optional[str]]:
    """Send website change notification email to verified owner."""
    if not is_smtp_configured():
        return False, "SMTP not configured."

    config = get_smtp_config()
    subject = f"ChangeRadar Alert: '{website_name}' updated"

    text_body = f"""Hello {recipient_name},

A change was detected on a webpage in your ChangeRadar watchlist:

Website: {website_name} ({website_url})
Change Type: {change_type.upper()}
Summary: {summary}
Diff stats: +{additions_count} additions, -{deletions_count} deletions

View your dashboard: {config['frontend_url']}

To adjust your email alert preferences, log into your ChangeRadar Settings.
"""

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #0b1120; color: #f8fafc; padding: 24px;">
      <div style="max-width: 560px; margin: 0 auto; background-color: #0f172a; border: 1px solid #1e293b; border-radius: 12px; padding: 32px; box-shadow: 0 10px 25px rgba(0,0,0,0.5);">
        <div style="margin-bottom: 24px;">
          <span style="display: inline-block; background-color: rgba(20, 184, 166, 0.15); color: #2dd4bf; padding: 4px 10px; border-radius: 9999px; font-size: 12px; font-weight: 600; text-transform: uppercase;">Change Detected</span>
        </div>
        <h3 style="color: #f1f5f9; margin-top: 8px;">Content Update on {website_name}</h3>
        <p style="color: #94a3b8; font-size: 14px; margin-bottom: 20px;">
          <strong>Target URL:</strong> <a href="{website_url}" style="color: #38bdf8; text-decoration: none;">{website_url}</a>
        </p>
        <div style="background-color: #090d16; border-left: 4px solid #14b8a6; padding: 14px 18px; border-radius: 4px; margin-bottom: 20px;">
          <p style="color: #e2e8f0; font-size: 14px; margin: 0; line-height: 1.5;">{summary}</p>
        </div>
        <div style="display: flex; gap: 16px; margin-bottom: 24px; font-size: 13px;">
          <span style="color: #10b981; font-weight: 600;">+{additions_count} additions</span> &bull; 
          <span style="color: #ef4444; font-weight: 600;">-{deletions_count} deletions</span>
        </div>
        <div style="margin: 28px 0 16px 0;">
          <a href="{config['frontend_url']}" style="display: inline-block; background-color: #0d9488; color: #ffffff; text-decoration: none; padding: 10px 20px; border-radius: 8px; font-weight: 600; font-size: 14px;">
            Open Dashboard
          </a>
        </div>
        <p style="color: #64748b; font-size: 12px; border-top: 1px solid #1e293b; padding-top: 16px; margin-top: 24px;">
          You received this email because you enabled ChangeRadar alerts for this website. You can turn off email alerts anytime in Settings.
        </p>
      </div>
    </body>
    </html>
    """

    return await send_email(recipient_email, subject, html_body, text_body)


async def send_deadline_created_email(
    recipient_name: str,
    recipient_email: str,
    title: str,
    due_date: str,
    priority: str = "medium",
    category: str = "Academic",
    source_url: Optional[str] = None,
    description: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """Send confirmation email to user when a new deadline is added."""
    if not is_smtp_configured():
        return False, "SMTP not configured."

    config = get_smtp_config()
    subject = f"ChangeRadar: Deadline '{title}' Added"

    priority_color = {
        "high": "#ef4444",
        "medium": "#f59e0b",
        "low": "#64748b"
    }.get(priority.lower(), "#f59e0b")

    text_body = f"""Hello {recipient_name},

A new deadline has been added to your ChangeRadar dashboard:

Title: {title}
Due Date: {due_date}
Priority: {priority.upper()}
Category: {category}
{f"Source: {source_url}" if source_url else ""}
{f"Details: {description}" if description else ""}

ChangeRadar will monitor this deadline and automatically notify you before 48 hours, 24 hours, and 12 hours of the due date.

View your dashboard: {config['frontend_url']}
"""

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #0b1120; color: #f8fafc; padding: 24px;">
      <div style="max-width: 560px; margin: 0 auto; background-color: #0f172a; border: 1px solid #1e293b; border-radius: 12px; padding: 32px; box-shadow: 0 10px 25px rgba(0,0,0,0.5);">
        <div style="margin-bottom: 20px;">
          <span style="display: inline-block; background-color: rgba(20, 184, 166, 0.15); color: #2dd4bf; padding: 5px 12px; border-radius: 9999px; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">Deadline Added</span>
        </div>
        <h3 style="color: #f1f5f9; margin-top: 0; font-size: 20px;">{title}</h3>
        <p style="color: #94a3b8; font-size: 14px; margin-bottom: 20px;">
          Hello <strong>{recipient_name}</strong>, this deadline is now being tracked in your ChangeRadar account.
        </p>

        <div style="background-color: #090d16; border: 1px solid #1e293b; border-radius: 8px; padding: 18px; margin-bottom: 24px;">
          <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
            <span style="color: #64748b; font-size: 13px; text-transform: uppercase;">Due Date</span>
            <strong style="color: #f8fafc; font-size: 15px;">{due_date}</strong>
          </div>
          <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
            <span style="color: #64748b; font-size: 13px; text-transform: uppercase;">Priority</span>
            <span style="display: inline-block; background-color: {priority_color}; color: #ffffff; padding: 2px 10px; border-radius: 6px; font-size: 12px; font-weight: 700; text-transform: uppercase;">
              {priority.upper()}
            </span>
          </div>
          <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
            <span style="color: #64748b; font-size: 13px; text-transform: uppercase;">Category</span>
            <span style="color: #38bdf8; font-size: 14px; font-weight: 600;">{category}</span>
          </div>
          {f'''<div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid #1e293b; font-size: 13px; color: #94a3b8;">
            <strong>Details:</strong> {description}
          </div>''' if description else ""}
          {f'''<div style="margin-top: 8px; font-size: 12px; color: #64748b; word-break: break-all;">
            <strong>Source URL:</strong> <a href="{source_url}" style="color: #38bdf8; text-decoration: none;">{source_url}</a>
          </div>''' if source_url else ""}
        </div>

        <p style="color: #94a3b8; font-size: 13px; line-height: 1.5; margin-bottom: 24px;">
          ChangeRadar will automatically send you alert reminders <strong>48 hours, 24 hours, and 12 hours</strong> before the due date.
        </p>

        <div style="margin-bottom: 20px;">
          <a href="{config['frontend_url']}" style="display: inline-block; background-color: #0d9488; color: #ffffff; text-decoration: none; padding: 10px 22px; border-radius: 8px; font-weight: 600; font-size: 14px;">
            View Deadlines Dashboard
          </a>
        </div>

        <p style="color: #64748b; font-size: 12px; border-top: 1px solid #1e293b; padding-top: 16px; margin-top: 24px;">
          You received this email because you created or subscribed to this deadline in ChangeRadar. You can manage notifications in Settings.
        </p>
      </div>
    </body>
    </html>
    """

    return await send_email(recipient_email, subject, html_body, text_body)


async def send_deadline_reminder_email(
    recipient_name: str,
    recipient_email: str,
    title: str,
    due_date: str,
    hours_label: str,
    priority: str = "high",
    category: str = "Academic",
    source_url: Optional[str] = None,
    description: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """Send reminder alert email before 48 hours, 24 hours, or 12 hours of deadline due date."""
    if not is_smtp_configured():
        return False, "SMTP not configured."

    config = get_smtp_config()
    badge_color = "#ef4444" if "12" in hours_label else ("#f97316" if "24" in hours_label else "#f59e0b")
    urgency_tag = "FINAL NOTICE: 12 HOURS REMAINING" if "12" in hours_label else (
        "URGENT: 24 HOURS REMAINING" if "24" in hours_label else "REMINDER: 48 HOURS REMAINING"
    )

    subject = f"[{urgency_tag}] Deadline '{title}' is due in {hours_label}"

    text_body = f"""Hello {recipient_name},

This is an urgent reminder that your deadline is due in {hours_label}:

Title: {title}
Due Date: {due_date}
Remaining: {hours_label}
Priority: {priority.upper()}
Category: {category}
{f"Source: {source_url}" if source_url else ""}
{f"Details: {description}" if description else ""}

Please ensure all necessary actions and submissions are completed before the due date.

View and manage this deadline: {config['frontend_url']}
"""

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #0b1120; color: #f8fafc; padding: 24px;">
      <div style="max-width: 560px; margin: 0 auto; background-color: #0f172a; border: 1px solid #1e293b; border-radius: 12px; padding: 32px; box-shadow: 0 10px 25px rgba(0,0,0,0.5);">
        <div style="margin-bottom: 20px;">
          <span style="display: inline-block; background-color: {badge_color}; color: #ffffff; padding: 6px 14px; border-radius: 9999px; font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px;">
            {urgency_tag}
          </span>
        </div>
        <h3 style="color: #f1f5f9; margin-top: 0; font-size: 22px;">{title}</h3>
        <p style="color: #94a3b8; font-size: 15px; margin-bottom: 20px;">
          Hello <strong>{recipient_name}</strong>, this is an automated alert that this deadline ends in <strong>{hours_label}</strong>.
        </p>

        <div style="background-color: #090d16; border-left: 4px solid {badge_color}; border-radius: 4px; padding: 18px; margin-bottom: 24px;">
          <div style="font-size: 16px; font-weight: 700; color: #f8fafc; margin-bottom: 8px;">
            Due Date: <span style="color: {badge_color};">{due_date}</span>
          </div>
          <div style="font-size: 13px; color: #94a3b8; margin-bottom: 6px;">
            <strong>Category:</strong> {category} &bull; <strong>Priority:</strong> {priority.upper()}
          </div>
          {f'''<div style="margin-top: 10px; font-size: 13px; color: #cbd5e1;">
            {description}
          </div>''' if description else ""}
          {f'''<div style="margin-top: 8px; font-size: 12px; color: #64748b; word-break: break-all;">
            <strong>Source URL:</strong> <a href="{source_url}" style="color: #38bdf8; text-decoration: none;">{source_url}</a>
          </div>''' if source_url else ""}
        </div>

        <div style="margin-bottom: 24px;">
          <a href="{config['frontend_url']}" style="display: inline-block; background-color: #0d9488; color: #ffffff; text-decoration: none; padding: 12px 24px; border-radius: 8px; font-weight: 700; font-size: 15px; box-shadow: 0 4px 12px rgba(13, 148, 136, 0.3);">
            Open ChangeRadar Dashboard
          </a>
        </div>

        <p style="color: #64748b; font-size: 12px; border-top: 1px solid #1e293b; padding-top: 16px; margin-top: 24px;">
          You received this email because you have deadline reminder alerts enabled. You can adjust alert settings anytime in ChangeRadar Settings.
        </p>
      </div>
    </body>
    </html>
    """

    return await send_email(recipient_email, subject, html_body, text_body)


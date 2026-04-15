"""
Shared utilities for Raph's Intel System.
Handles: Claude API calls, Notion database delivery, Gmail delivery.
"""

import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import anthropic
from notion_client import Client as NotionClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


# ─── CLAUDE API ──────────────────────────────────────────────────────────────

def call_claude(system_prompt: str, user_prompt: str, max_tokens: int = 4096, use_web_search: bool = False) -> str:
    """Call Claude API with optional web search tool."""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    kwargs = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
    }

    if use_web_search:
        kwargs["tools"] = [{"type": "web_search_20250305", "name": "web_search"}]

    response = client.messages.create(**kwargs)

    text_parts = [block.text for block in response.content if hasattr(block, "text") and block.text is not None]
    return "\n".join(text_parts).strip()


# ─── NOTION DATABASE DELIVERY ────────────────────────────────────────────────

def post_to_notion_database(database_id: str, title: str, properties: dict, content_blocks: list) -> str:
    """Create a new entry in a Notion database."""
    notion = NotionClient(auth=os.environ["NOTION_API_KEY"])

    today = datetime.now().strftime("%d %b %Y")
    page_title = f"{title} — {today}"

    notion_properties = {
        "Name": {
            "title": [{"type": "text", "text": {"content": page_title}}]
        },
        "Date": {
            "date": {"start": datetime.now().strftime("%Y-%m-%d")}
        }
    }
    notion_properties.update(properties)

    new_page = notion.pages.create(
        parent={"database_id": database_id},
        properties=notion_properties,
        children=content_blocks[:100],
    )

    log.info(f"Notion database entry created: {page_title} ({new_page['id']})")
    return new_page.get("url", "")


def ensure_database_has_date_property(database_id: str) -> None:
    """Check if the Notion database has a Date property. If not, add it."""
    notion = NotionClient(auth=os.environ["NOTION_API_KEY"])
    try:
        db = notion.databases.retrieve(database_id=database_id)
        properties = db.get("properties", {})
        if "Date" not in properties:
            notion.databases.update(
                database_id=database_id,
                properties={"Date": {"date": {}}}
            )
            log.info(f"Added Date property to database {database_id}")
    except Exception as e:
        log.warning(f"Could not check/update database properties: {e}")


def build_notion_blocks(brief_text: str) -> list:
    """Convert markdown brief text into Notion block objects."""
    blocks = []
    for line in brief_text.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("# "):
            blocks.append(_heading(line[2:], 1))
        elif line.startswith("## "):
            blocks.append(_heading(line[3:], 2))
        elif line.startswith("### "):
            blocks.append(_heading(line[4:], 3))
        elif line == "---":
            blocks.append({"object": "block", "type": "divider", "divider": {}})
        elif line.startswith("**") and line.endswith("**") and line.count("**") == 2:
            blocks.append(_paragraph(line.replace("**", ""), bold=True))
        else:
            blocks.append(_paragraph(line))
    return blocks


def _heading(text: str, level: int) -> dict:
    key = f"heading_{level}"
    return {
        "object": "block",
        "type": key,
        key: {
            "rich_text": [{"type": "text", "text": {"content": text[:2000]}}],
            "color": "default",
        },
    }


def _paragraph(text: str, bold: bool = False) -> dict:
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": text[:2000]},
                    "annotations": {"bold": bold},
                }
            ]
        },
    }


# ─── GMAIL DELIVERY ──────────────────────────────────────────────────────────

def send_email(subject: str, html_body: str, to_address: str) -> None:
    """Send HTML email via Gmail SMTP using an App Password."""
    gmail_address = os.environ["GMAIL_ADDRESS"]
    gmail_password = os.environ["GMAIL_APP_PASSWORD"]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Intelligence Briefing <{gmail_address}>"
    msg["To"] = to_address
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_address, gmail_password)
        server.sendmail(gmail_address, to_address, msg.as_string())

    log.info(f"Email sent to {to_address}: {subject}")

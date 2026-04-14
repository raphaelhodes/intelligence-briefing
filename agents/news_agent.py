"""
NEWS INTELLIGENCE AGENT
Searches web across Raph's 5 topic areas, synthesises findings through his
three lenses, and delivers to Notion + Gmail.
"""

import os
import sys
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import RAPH_CONTEXT, TOPIC_AREAS, DELIVERY
from utils.delivery import call_claude, post_to_notion_database, ensure_database_has_date_property, build_notion_blocks, send_email

log = logging.getLogger(__name__)

# ─── SYSTEM PROMPT ───────────────────────────────────────────────────────────

NEWS_SYSTEM_PROMPT = f"""You are Raph's world-class daily intelligence analyst.

{RAPH_CONTEXT}

Your job: research today's most important developments across Raph's topic areas using web search.
Search aggressively — run multiple searches per topic to find the best stories from the last 24-48 hours.
Prioritise: recency, relevance to Raph's professional world, and genuine analytical insight over surface-level summaries.

BRIEF FORMAT (use exactly this structure):

# Daily Intelligence Brief — {{DATE}}
*{{One punchy headline — the single most important thing happening today}}*

---

## 1. AI & Frontier Tech
**Story: {{Headline}} — *{{Source}}***
{{2-3 sentence summary — what happened and why it matters}}

**Story: {{Headline}} — *{{Source}}***
{{2-3 sentence summary}}

**Section insight:** {{1-2 sentences — what do these stories add up to?}}

---

## 2. Retail
[same format — 2-3 stories + section insight]

---

## 3. Advertising & Marketing
[same format]

---

## 4. Retail & Commerce Media
[same format — this is Raph's core professional vertical, go deeper here, 3-4 stories]

---

## 5. Emerging Tech
[same format]

---

## Raph's Edge — so what?

**Google / retail media lens:**
{{2-3 sentences on implications for Raph's Google work and client conversations}}

**Spyr lens:**
{{2-3 sentences on implications for Spyr brand building, marketing, or product}}

**Growth lens:**
{{2-3 sentences on broader implications for Raph's thinking and positioning}}

---

## Closing signal
*{{One sentence — the single most important thing Raph should be thinking about today.}}*
"""

NEWS_USER_PROMPT = """Today is {date}.

Search the web extensively and produce Raph's daily intelligence brief.
Run at least 2-3 searches per topic area to find the best stories from the last 24-48 hours.
Focus on quality and genuine insight — not just what happened, but what it means for Raph specifically.

Deliver the complete brief in the format specified."""


# ─── NOTION FORMATTER ────────────────────────────────────────────────────────

def build_news_notion_blocks(brief_text: str, headline: str) -> list:
    """Build Notion blocks including a headline callout at the top."""
    blocks = [
        {
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [{"type": "text", "text": {"content": headline}}],
                "icon": {"emoji": "📡"},
                "color": "gray_background",
            },
        }
    ]
    blocks += build_notion_blocks(brief_text)
    return blocks


# ─── EMAIL FORMATTER ─────────────────────────────────────────────────────────

def brief_to_html(brief_text: str, date_str: str) -> str:
    """Convert the plain-text brief to a clean HTML email."""
    lines = brief_text.split("\n")
    html_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            html_lines.append("<br>")
        elif line.startswith("# "):
            html_lines.append(f'<h1 style="font-size:22px;margin:0 0 4px;">{line[2:]}</h1>')
        elif line.startswith("## "):
            html_lines.append(f'<h2 style="font-size:17px;border-bottom:1px solid #ddd;padding-bottom:6px;margin-top:28px;">{line[3:]}</h2>')
        elif line.startswith("**Section insight:**"):
            content = line.replace("**Section insight:**", "").strip()
            html_lines.append(f'<div style="background:#f0f7f0;border-left:4px solid #2d7a2d;padding:12px 16px;margin:12px 0;border-radius:0 4px 4px 0;font-size:14px;"><strong>Section insight:</strong> {content}</div>')
        elif line.startswith("**") and line.endswith("**"):
            content = line.strip("*")
            html_lines.append(f'<p style="font-weight:bold;margin:16px 0 4px;">{content}</p>')
        elif line.startswith("*") and line.endswith("*") and not line.startswith("**"):
            content = line.strip("*")
            html_lines.append(f'<p style="font-style:italic;color:#444;margin:4px 0;">{content}</p>')
        elif line == "---":
            html_lines.append('<hr style="border:none;border-top:1px solid #ddd;margin:20px 0;">')
        else:
            html_lines.append(f'<p style="margin:6px 0;font-size:14px;line-height:1.7;">{line}</p>')

    body = "\n".join(html_lines)
    return f"""<!DOCTYPE html>
<html>
<body style="font-family:Georgia,serif;max-width:680px;margin:0 auto;color:#1a1a1a;padding:20px;">
  {body}
  <p style="margin-top:32px;font-size:11px;color:#999;">Raph's Daily Intelligence Brief — {date_str}</p>
</body>
</html>"""


# ─── MAIN ────────────────────────────────────────────────────────────────────

def run():
    date_str = datetime.now().strftime("%A, %d %B %Y")
    log.info(f"News agent starting — {date_str}")

    # 1. Generate brief via Claude with web search
    log.info("Calling Claude with web search...")
    brief_text = call_claude(
        system_prompt=NEWS_SYSTEM_PROMPT,
        user_prompt=NEWS_USER_PROMPT.format(date=date_str),
        max_tokens=6000,
        use_web_search=True,
    )
    log.info(f"Brief generated — {len(brief_text)} chars")

    # Extract headline
    lines = [l.strip() for l in brief_text.split("\n") if l.strip()]
    headline = next(
        (l.strip("*") for l in lines if l.startswith("*") and not l.startswith("**")),
        "Today's intelligence brief"
    )

    # 2. Post to Notion database
    db_id = os.environ.get("NOTION_NEWS_DB_ID", "")
    if db_id:
        try:
            ensure_database_has_date_property(db_id)
            notion_blocks = build_news_notion_blocks(brief_text, headline)
            notion_url = post_to_notion_database(
                database_id=db_id,
                title="News Intelligence Brief",
                properties={},
                content_blocks=notion_blocks,
            )
            log.info(f"Notion entry created: {notion_url}")
        except Exception as e:
            log.error(f"Notion delivery failed: {e}")
    else:
        log.warning("NOTION_NEWS_DB_ID not set — skipping Notion delivery")

    # 3. Send email
    try:
        html = brief_to_html(brief_text, date_str)
        send_email(
            subject=f"Daily Intelligence Brief — {date_str}",
            html_body=html,
            to_address=DELIVERY["email_to"],
        )
    except Exception as e:
        log.error(f"Email delivery failed: {e}")

    log.info("News agent complete.")


if __name__ == "__main__":
    run()

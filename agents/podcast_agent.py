"""
PODCAST INTELLIGENCE AGENT
Checks RSS feeds for new episodes, scrapes transcripts, runs deep analysis
per episode through Claude, and delivers to Notion + Gmail.
"""

import os
import sys
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus

import requests
import feedparser
from bs4 import BeautifulSoup
from dateutil import parser as dateparser

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import RAPH_CONTEXT, PODCAST_SOURCES, DELIVERY, TRANSCRIPT_SOURCES
from utils.delivery import call_claude, post_to_notion_database, ensure_database_has_date_property, build_notion_blocks, send_email

log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"
}
LOOKBACK_HOURS = 36


# ─── SYSTEM PROMPT ───────────────────────────────────────────────────────────

PODCAST_SYSTEM_PROMPT = f"""You are Raph's world-class podcast intelligence analyst.

{RAPH_CONTEXT}

Your job: analyse a podcast episode transcript or description and produce a deep intelligence brief.

FORMAT:
# Podcast Intelligence: {{Episode Title}}
**{{Podcast Name}}** | {{Date}} | {{Duration if known}}

## Core thesis
{{2-3 sentences — the central argument}}

## Key perspectives
**{{Theme 1}}**
{{2-3 sentences}}

**{{Theme 2}}**
{{2-3 sentences}}

## Notable moments
{{What was surprising, contrarian, or memorable?}}

## Critical analysis
{{Your honest assessment — what's right, what's overstated, what's missing?}}

## Implications for Raph

**Google / retail media lens:**
{{2-3 sentences}}

**Spyr lens:**
{{2-3 sentences}}

**Growth lens:**
{{2-3 sentences}}

## Bottom line
*{{One sentence — what Raph should actually do or think differently.}}*
"""


# ─── RSS FEED CHECKER ────────────────────────────────────────────────────────

def get_new_episodes(source: dict, lookback_hours: int = LOOKBACK_HOURS) -> list:
    """Check a podcast RSS feed for episodes published in the last N hours."""
    import time
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    episodes = []

    rss_url = source.get("rss", "")
    if not rss_url:
        log.info(f"No RSS for {source['name']} — searching web")
        return search_web_for_episodes(source, lookback_hours)

    try:
        feed = feedparser.parse(rss_url)
        for entry in feed.entries[:10]:
            pub_date = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                pub_date = datetime.fromtimestamp(time.mktime(entry.published_parsed), tz=timezone.utc)
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                pub_date = datetime.fromtimestamp(time.mktime(entry.updated_parsed), tz=timezone.utc)

            if pub_date and pub_date > cutoff:
                episodes.append({
                    "podcast": source["name"],
                    "host": source.get("host", ""),
                    "title": entry.get("title", "Unknown episode"),
                    "description": entry.get("summary", entry.get("description", "")),
                    "link": entry.get("link", ""),
                    "published": pub_date.strftime("%d %b %Y"),
                    "duration": entry.get("itunes_duration", ""),
                    "transcript_sources": source.get("transcript_sources", []),
                    "website": source.get("website", ""),
                })
                log.info(f"New episode: {source['name']} — {entry.get('title', '')}")

    except Exception as e:
        log.warning(f"RSS fetch failed for {source['name']}: {e}")

    return episodes


def search_web_for_episodes(source: dict, lookback_hours: int) -> list:
    """Use Claude web search to find new episodes when no RSS is available."""
    query_prompt = f"""Search for the most recent episode of the podcast "{source['name']}" released in the last {lookback_hours} hours.
If you find a new episode, return a JSON object with: title, description, link, published_date.
If no new episode found, return {{"found": false}}.
Return ONLY the JSON, no other text."""

    try:
        result = call_claude(
            system_prompt="You are a podcast research assistant. Search the web and return ONLY valid JSON.",
            user_prompt=query_prompt,
            max_tokens=500,
            use_web_search=True,
        )
        result = re.sub(r"```json|```", "", result).strip()
        data = json.loads(result)
        if data.get("found") is False:
            return []
        return [{
            "podcast": source["name"],
            "host": source.get("host", ""),
            "title": data.get("title", "Unknown"),
            "description": data.get("description", ""),
            "link": data.get("link", ""),
            "published": data.get("published_date", datetime.now().strftime("%d %b %Y")),
            "duration": "",
            "transcript_sources": source.get("transcript_sources", []),
            "website": source.get("website", ""),
        }]
    except Exception as e:
        log.warning(f"Web search for {source['name']} episodes failed: {e}")
        return []


# ─── TRANSCRIPT FETCHING ─────────────────────────────────────────────────────

def get_transcript(episode: dict) -> str:
    """Try multiple sources to get a transcript."""
    transcript = ""

    for source_type in episode.get("transcript_sources", []):
        if source_type == "podscripts":
            transcript = try_podscripts(episode)
        elif source_type == "website":
            transcript = try_episode_website(episode)
        elif source_type == "youtube":
            transcript = try_youtube_transcript(episode)

        if transcript and len(transcript) > 500:
            log.info(f"Transcript obtained from {source_type} ({len(transcript)} chars)")
            break

    if not transcript:
        log.info(f"No transcript found — using description for {episode['title']}")
        transcript = episode.get("description", "")

    max_chars = TRANSCRIPT_SOURCES["max_transcript_chars"]
    if len(transcript) > max_chars:
        transcript = transcript[:max_chars] + "\n\n[Transcript truncated for length]"

    return transcript


def try_podscripts(episode: dict) -> str:
    """Try to get transcript from podscripts.co."""
    try:
        search_url = f"https://podscripts.co/search?q={quote_plus(episode['title'])}"
        resp = requests.get(search_url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "lxml")

        links = soup.find_all("a", href=True)
        ep_link = None
        for link in links:
            href = link.get("href", "")
            title_text = link.get_text(strip=True).lower()
            if episode["podcast"].lower().split("/")[0].strip() in title_text or \
               episode["title"].lower()[:20] in title_text:
                if "/podcasts/" in href:
                    ep_link = "https://podscripts.co" + href if href.startswith("/") else href
                    break

        if not ep_link:
            return ""

        resp2 = requests.get(ep_link, headers=HEADERS, timeout=10)
        soup2 = BeautifulSoup(resp2.text, "lxml")
        transcript_div = soup2.find("div", class_=re.compile(r"transcript|content|episode", re.I))
        if transcript_div:
            return transcript_div.get_text(separator=" ", strip=True)

    except Exception as e:
        log.debug(f"Podscripts failed: {e}")

    return ""


def try_episode_website(episode: dict) -> str:
    """Try to scrape the episode webpage for a transcript or show notes."""
    link = episode.get("link", "")
    if not link:
        return ""
    try:
        resp = requests.get(link, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "lxml")

        for tag in soup(["nav", "footer", "script", "style", "header"]):
            tag.decompose()

        for selector in ["transcript", "show-notes", "episode-notes", "content", "entry-content"]:
            el = soup.find(class_=re.compile(selector, re.I)) or soup.find(id=re.compile(selector, re.I))
            if el:
                text = el.get_text(separator=" ", strip=True)
                if len(text) > 300:
                    return text

        article = soup.find("article") or soup.find("main")
        if article:
            return article.get_text(separator=" ", strip=True)

    except Exception as e:
        log.debug(f"Website scrape failed for {link}: {e}")

    return ""


def try_youtube_transcript(episode: dict) -> str:
    """Try to get YouTube auto-captions."""
    try:
        search_query = f"{episode['podcast']} {episode['title']}"
        search_url = f"https://www.youtube.com/results?search_query={quote_plus(search_query)}"
        resp = requests.get(search_url, headers=HEADERS, timeout=10)

        video_ids = re.findall(r'"videoId":"([^"]{11})"', resp.text)
        if not video_ids:
            return ""

        video_id = video_ids[0]
        transcript_url = f"https://www.youtube.com/watch?v={video_id}"
        resp2 = requests.get(transcript_url, headers=HEADERS, timeout=10)

        desc_match = re.search(r'"description":{"simpleText":"([^"]+)"', resp2.text)
        if desc_match:
            return desc_match.group(1).replace("\\n", "\n").replace("\\u0026", "&")

    except Exception as e:
        log.debug(f"YouTube transcript failed: {e}")

    return ""


# ─── ANALYSIS ────────────────────────────────────────────────────────────────

def analyse_episode(episode: dict, transcript: str) -> str:
    """Run Claude analysis on a podcast episode."""
    has_transcript = len(transcript) > 500

    user_prompt = f"""Analyse this podcast episode for Raph's intelligence brief.

EPISODE: {episode['title']}
PODCAST: {episode['podcast']}
HOST(S): {episode['host']}
DATE: {episode['published']}
DURATION: {episode['duration']}

{'FULL TRANSCRIPT:' if has_transcript else 'SHOW NOTES / DESCRIPTION (no full transcript available):'}
{transcript}

{'Analyse based on the full transcript above.' if has_transcript else 'Analyse based on the show notes and description. Note this is based on limited information.'}

Also use web search to find any additional context, discussion, or reaction to this episode online.

Produce the complete intelligence analysis in the format specified."""

    return call_claude(
        system_prompt=PODCAST_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        max_tokens=4096,
        use_web_search=True,
    )


# ─── FORMATTERS ──────────────────────────────────────────────────────────────

def build_podcast_notion_blocks(analyses: list) -> list:
    """Build Notion blocks for all podcast analyses."""
    blocks = [
        {
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [{"type": "text", "text": {
                    "content": f"{len(analyses)} new episode(s) analysed — {datetime.now().strftime('%d %b %Y')}"
                }}],
                "icon": {"emoji": "🎙️"},
                "color": "blue_background",
            }
        }
    ]
    for item in analyses:
        blocks += build_notion_blocks(item["analysis"])
        blocks.append({"object": "block", "type": "divider", "divider": {}})
    return blocks


def build_podcast_email(analyses: list, date_str: str) -> str:
    """Build HTML email for podcast brief."""
    episode_sections = ""
    for item in analyses:
        ep = item["episode"]
        analysis_html = ""
        for line in item["analysis"].split("\n"):
            line = line.strip()
            if not line:
                analysis_html += "<br>"
            elif line.startswith("## "):
                analysis_html += f'<h3 style="font-size:15px;margin-top:20px;margin-bottom:4px;color:#333;">{line[3:]}</h3>'
            elif line.startswith("**") and line.endswith("**"):
                analysis_html += f'<p style="font-weight:bold;margin:12px 0 2px;">{line.strip("*")}</p>'
            elif line.startswith("*") and line.endswith("*"):
                analysis_html += f'<p style="font-style:italic;background:#f5f5f5;padding:10px 14px;border-radius:4px;">{line.strip("*")}</p>'
            else:
                analysis_html += f'<p style="font-size:14px;line-height:1.7;margin:4px 0;">{line}</p>'

        episode_sections += f"""
        <div style="border:1px solid #e0e0e0;border-radius:8px;padding:20px;margin-bottom:24px;">
          <h2 style="font-size:17px;margin:0 0 4px;">{ep['title']}</h2>
          <p style="color:#666;font-size:13px;margin:0 0 16px;">{ep['podcast']} — {ep['published']}</p>
          {analysis_html}
        </div>"""

    return f"""<!DOCTYPE html>
<html>
<body style="font-family:Georgia,serif;max-width:680px;margin:0 auto;color:#1a1a1a;padding:20px;">
  <div style="border-bottom:3px solid #1a1a1a;padding-bottom:16px;margin-bottom:24px;">
    <h1 style="font-size:22px;margin:0 0 4px;">Podcast Intelligence Brief</h1>
    <p style="margin:0;color:#666;font-size:14px;">{date_str} — {len(analyses)} new episode(s)</p>
  </div>
  {episode_sections}
  <p style="margin-top:24px;font-size:11px;color:#999;">Raph's Podcast Intelligence — {date_str}</p>
</body>
</html>"""


# ─── MAIN ────────────────────────────────────────────────────────────────────

def run():
    date_str = datetime.now().strftime("%A, %d %B %Y")
    log.info(f"Podcast agent starting — {date_str}")

    # 1. Check all sources for new episodes
    all_episodes = []
    for source in PODCAST_SOURCES:
        log.info(f"Checking {source['name']}...")
        episodes = get_new_episodes(source)
        all_episodes.extend(episodes)

    log.info(f"Total new episodes found: {len(all_episodes)}")

    if not all_episodes:
        log.info("No new episodes in the last 36 hours. Skipping delivery.")
        return

    # 2. Fetch transcripts and analyse each episode
    analyses = []
    for episode in all_episodes:
        log.info(f"Processing: {episode['podcast']} — {episode['title']}")
        transcript = get_transcript(episode)
        analysis = analyse_episode(episode, transcript)
        analyses.append({"episode": episode, "analysis": analysis})

    # 3. Post to Notion database
    db_id = os.environ.get("NOTION_PODCAST_DB_ID", "")
    if db_id and analyses:
        try:
            ensure_database_has_date_property(db_id)
            notion_blocks = build_podcast_notion_blocks(analyses)
            notion_url = post_to_notion_database(
                database_id=db_id,
                title="Podcast Intelligence Brief",
                properties={},
                content_blocks=notion_blocks,
            )
            log.info(f"Notion entry created: {notion_url}")
        except Exception as e:
            log.error(f"Notion delivery failed: {e}")

    # 4. Send email
    try:
        html = build_podcast_email(analyses, date_str)
        send_email(
            subject=f"Podcast Intelligence Brief — {date_str} ({len(analyses)} episodes)",
            html_body=html,
            to_address=DELIVERY["email_to"],
        )
    except Exception as e:
        log.error(f"Email delivery failed: {e}")

    log.info(f"Podcast agent complete — {len(analyses)} episodes processed.")


if __name__ == "__main__":
    run()

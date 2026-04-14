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
            transcript = tr

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
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus

import requests
import feedparser
from bs4 import BeautifulSoup

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
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    episodes = []

    rss_url = source.get("rss", "")
    if not rss_url:
        log.info(f"No RSS for {source['name']} — skipping")
        return []

    try:
        feed = feedparser.parse(rss_url)
        for entry in feed.entries[:10]:
            pub_date = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                pub_date = datetime.fromtimestamp(
                    time.mktime(entry.published_parsed), tz=timezone.utc
                )
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                pub_date = datetime.fromtimestamp(
                    time.mktime(entry.updated_parsed), tz=timezone.utc
                )

            if pub_date and pub_date > cutoff:
                episodes.append({
                    "podcast": source["name"],
                    "host": source.get("host", ""),
                    "relevance": source.get("relevance", ""),
                    "title": entry.get("title", "Unknown episode"),
                    "description": entry.get("summary", entry.get("description", "")),
                    "link": entry.get("link", ""),
                    "published": pub_date.strftime("%d %b %Y"),
                    "duration": entry.get("itunes_duration", ""),
                    "website": source.get("website", ""),
                })
                log.info(f"New episode: {source['name']} — {entry.get('title', '')}")

    except Exception as e:
        log.warning(f"RSS fetch failed for {source['name']}: {e}")

    return episodes


# ─── TRANSCRIPT FETCHING ─────────────────────────────────────────────────────

def get_transcript(episode: dict) -> str:
    """Try multiple sources to get a transcript. Falls back to description."""
    transcript = ""

    # Try the episode's own webpage first
    transcript = try_episode_website(episode.get("link", ""))
    if transcript and len(transcript) > 500:
        log.info(f"Transcript from episode page ({len(transcript)} chars)")
        return truncate(transcript)

    # Try podscripts.co
    transcript = try_podscripts(episode)
    if transcript and len(transcript) > 500:
        log.info(f"Transcript from podscripts ({len(transcript)} chars)")
        return truncate(transcript)

    # Fall back to RSS description
    log.info(f"Using RSS description for {episode['title']}")
    return episode.get("description", "")


def truncate(text: str) -> str:
    max_chars = TRANSCRIPT_SOURCES["max_transcript_chars"]
    if len(text) > max_chars:
        return text[:max_chars] + "\n\n[Transcript truncated for length]"
    return text


def try_episode_website(url: str) -> str:
    """Scrape the episode webpage for transcript or show notes."""
    if not url:
        return ""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "lxml")

        for tag in soup(["nav", "footer", "script", "style", "header"]):
            tag.decompose()

        for selector in ["transcript", "show-notes", "episode-notes", "content", "entry-content"]:
            el = soup.find(class_=re.compile(selector, re.I)) or \
                 soup.find(id=re.compile(selector, re.I))
            if el:
                text = el.get_text(separator=" ", strip=True)
                if len(text) > 300:
                    return text

        article = soup.find("article") or soup.find("main")
        if article:
            return article.get_text(separator=" ", strip=True)

    except Exception as e:
        log.debug(f"Website scrape failed for {url}: {e}")

    return ""


def try_podscripts(episode: dict) -> str:
    """Try to get transcript from podscripts.co."""
    try:
        search_url = f"https://podscripts.co/search?q={quote_plus(episode['title'])}"
        resp = requests.get(search_url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "lxml")

        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            title_text = link.get_text(strip=True).lower()
            podcast_name = episode["podcast"].lower().split("/")[0].strip()
            if podcast_name in title_text or episode["title"].lower()[:20] in title_text:
                if "/podcasts/" in href:
                    ep_link = "https://podscripts.co" + href if href.startswith("/") else href
                    resp2 = requests.get(ep_link, headers=HEADERS, timeout=10)
                    soup2 = BeautifulSoup(resp2.text, "lxml")
                    div = soup2.find("div", class_=re.compile(r"transcript|content|episode", re.I))
                    if div:
                        return div.get_text(separator=" ", strip=True)

    except Exception as e:
        log.debug(f"Podscripts failed: {e}")

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
WHY THIS PODCAST MATTERS TO RAPH: {episode['relevance']}

{'FULL TRANSCRIPT:' if has_transcript else 'SHOW NOTES / DESCRIPTION (no full transcript available):'}
{transcript}

{'Analyse based on the full transcript above.' if has_transcript else 'Note: no full transcript available — analyse based on show notes. Use web search to find additional context about this episode.'}

Use web search to find any reaction, discussion, or additional context about this episode online.

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

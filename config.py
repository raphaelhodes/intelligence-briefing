"""
Central config for Raph's Daily Intelligence Brief system.
Update this file to change topics, podcasts, or delivery settings.
"""

# ─── RAPH'S CONTEXT ──────────────────────────────────────────────────────────

RAPH_CONTEXT = """
Raphael (Raph) Hodes is:
- Senior sales executive at Google, focused on retail media clients including Cartology and Coles 360
- Co-founder of Spyr — a premium Australian DTC performance supplement brand targeting the "executive athlete"
- An executive athlete himself: completed Ironman New Zealand 2026, father, builder

RAPH'S THREE ANALYTICAL LENSES:
1. Google lens: implications for Raph's retail media clients (Cartology, Coles 360) and his sales conversations
2. Spyr lens: implications for building a DTC supplement brand — marketing, positioning, performance media
3. Growth lens: implications for Raph's thinking as an executive, entrepreneur, and thought leader

KEY PROFESSIONAL CONTEXT:
- Google's retail media products: AI Mode, Performance Max, Demand Gen, UCP, AI Max, Commerce Media Suite
- Retail media competitive landscape: Amazon DSP, Criteo, The Trade Desk, Instacart Ads, Walmart Connect
- Spyr's market: premium DTC supplements, executive athlete segment, Australian market primary
"""

# ─── TOPIC AREAS FOR NEWS AGENT ──────────────────────────────────────────────

TOPIC_AREAS = [
    {
        "id": "ai_tech",
        "title": "AI & Frontier Tech",
        "description": "New models, releases, capabilities, AGI developments, key commentary from thought leaders",
    },
    {
        "id": "retail",
        "title": "Retail",
        "description": "Industry moves, consumer behaviour, AI's impact on retail operations and experience",
    },
    {
        "id": "advertising",
        "title": "Advertising & Marketing",
        "description": "AI in brand, creative, media buying, measurement, performance marketing",
    },
    {
        "id": "retail_media",
        "title": "Retail & Commerce Media",
        "description": "Retail media networks, commerce media innovation, advertiser strategies, platform moves",
    },
    {
        "id": "emerging_tech",
        "title": "Emerging Tech",
        "description": "Broader innovation signals, startups, platform shifts, robotics, spatial computing",
    },
]

# ─── PODCAST SOURCES ─────────────────────────────────────────────────────────
# To add a new podcast: find its RSS on podcastindex.org and add an entry below.
# Only "name" and "rss" are required. "relevance" helps Claude with analysis context.

PODCAST_SOURCES = [
    {
        "name": "Stratechery",
        "host": "Ben Thompson",
        "rss": "https://stratechery.passport.online/feed/rss/CKPwHHB83gxmWo7eJuybr",
        "website": "https://stratechery.com",
        "relevance": "Deep tech strategy, AI business models, platform economics, aggregation theory"
    },
    {
        "name": "Sharp Tech with Ben Thompson",
        "host": "Ben Thompson & Andrew Sharp",
        "rss": "https://sharptech.fm/feed/podcast",
        "website": "https://stratechery.com",
        "relevance": "Tech strategy analysis, AI industry dynamics, platform shifts"
    },
    {
        "name": "All In Podcast",
        "host": "Chamath, Jason, Sacks, Friedberg",
        "rss": "https://allinchamathjason.libsyn.com/rss",
        "website": "https://allin.com",
        "relevance": "Tech, AI, venture capital, macro trends, enterprise software"
    },
    {
        "name": "Moonshots with Peter Diamandis",
        "host": "Peter Diamandis",
        "rss": "https://feeds.megaphone.fm/DVVTS2890392624",
        "website": "https://moonshots.com",
        "relevance": "Exponential technology, innovation, future of business"
    },
    {
        "name": "Lex Fridman Podcast",
        "host": "Lex Fridman",
        "rss": "https://lexfridman.com/feed/podcast/",
        "website": "https://lexfridman.com",
        "relevance": "Deep AI and tech interviews, frontier research, key industry figures"
    },
    {
        "name": "Retailgentic",
        "host": "Scot Wingo",
        "rss": "https://retailgentic.transistor.fm/",
        "website": "https://retailgentic.com",
        "relevance": "AI in retail, agentic commerce, retail transformation"
    },
    {
        "name": "Retail Media Breakfast Club",
        "host": "Kiri Masters",
        "rss": "https://feeds.transistor.fm/retail-media-breakfast-club",
        "website": "https://retailmediabreakfastclub.com",
        "relevance": "Retail media industry news, network strategies, advertiser perspectives"
    },
    {
        "name": "Commerce Media Matters",
        "host": "Nick Morgan & Paul Blackburn",
        "rss": "https://rss.buzzsprout.com/2372482.rss",
        "website": "https://commercemediamatters.buzzsprout.com",
        "relevance": "Commerce media ecosystem, brand strategies, technology, Australian market"
    },
]

# ─── DELIVERY SETTINGS ───────────────────────────────────────────────────────

DELIVERY = {
    "email_to": "raphael.hodes@gmail.com",
    "email_from_name": "Intelligence Briefing",
    "lookback_hours": 36,
}

# ─── TRANSCRIPT SETTINGS ─────────────────────────────────────────────────────

TRANSCRIPT_SOURCES = {
    "max_transcript_chars": 60000,
}

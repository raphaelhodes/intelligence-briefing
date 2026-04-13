"""
Central config for Raph's Daily Intelligence Brief system.
Update this file to change topics, podcasts, or delivery settings.
"""

# ─── RAPH'S CONTEXT (used in all prompts) ───────────────────────────────────

RAPH_CONTEXT = """
Raphael (Raph) Hodes is:
- Senior sales executive at Google, focused on retail media clients including Cartology and Coles 360
- Co-founder of Spyr — a premium Australian DTC performance supplement brand targeting the "executive athlete"
- An executive athlete himself: serious endurance athlete (completed Ironman New Zealand 2026), father, builder

RAPH'S THREE ANALYTICAL LENSES:
1. Google lens: implications for Raph's retail media clients (Cartology, Coles 360) and his sales conversations
2. Spyr lens: implications for building a DTC supplement brand — marketing, positioning, performance media
3. Growth lens: implications for Raph's thinking as an executive, entrepreneur, and thought leader

KEY PROFESSIONAL CONTEXT:
- Google's retail media products: AI Mode, Performance Max, Demand Gen, UCP, AI Max, Commerce Media Suite
- Retail media competitive landscape: Amazon DSP, Criteo, The Trade Desk, Instacart Ads, Walmart Connect
- Spyr's market: premium DTC supplements, executive athlete segment, Australian market primary
"""

# ─── TOPIC AREAS FOR NEWS AGENT ─────────────────────────────────────────────

TOPIC_AREAS = [
    {
        "id": "ai_tech",
        "title": "AI & Frontier Tech",
        "description": "New models, releases, capabilities, AGI developments, key commentary from thought leaders",
        "search_queries": [
            "AI news today new model release",
            "artificial intelligence frontier development announcement",
            "OpenAI Anthropic Google DeepMind news",
            "large language model LLM update",
        ]
    },
    {
        "id": "retail",
        "title": "Retail",
        "description": "Industry moves, consumer behaviour, AI's impact on retail operations and experience",
        "search_queries": [
            "retail industry news AI today",
            "retail technology consumer behaviour",
            "ecommerce retail innovation announcement",
            "grocery retail news Australia",
        ]
    },
    {
        "id": "advertising",
        "title": "Advertising & Marketing",
        "description": "AI in brand, creative, media buying, measurement, performance marketing",
        "search_queries": [
            "advertising marketing AI news today",
            "programmatic advertising adtech news",
            "performance marketing measurement update",
            "brand marketing innovation AI",
        ]
    },
    {
        "id": "retail_media",
        "title": "Retail & Commerce Media",
        "description": "Retail media networks, commerce media innovation, advertiser strategies, platform moves",
        "search_queries": [
            "retail media commerce media news",
            "retail media network announcement",
            "Google shopping ads retail media update",
            "Amazon advertising Criteo commerce media",
        ]
    },
    {
        "id": "emerging_tech",
        "title": "Emerging Tech",
        "description": "Broader innovation signals, startups, platform shifts, robotics, spatial computing",
        "search_queries": [
            "emerging technology innovation news today",
            "tech startup funding announcement",
            "platform shift technology disruption",
        ]
    },
]

# ─── PODCAST SOURCES ─────────────────────────────────────────────────────────

PODCAST_SOURCES = [
    {
        "name": "Stratechery / Sharp Tech",
        "host": "Ben Thompson & Andrew Sharp",
        "rss": "https://stratechery.com/feed/podcast/",
        "website": "https://stratechery.com",
        "transcript_sources": ["podscripts", "website"],
        "relevance": "Deep tech strategy analysis, AI business models, platform economics"
    },
    {
        "name": "All In Podcast",
        "host": "Chamath, Jason, Sacks, Friedberg",
        "rss": "https://allinchamathjason.libsyn.com/rss",
        "website": "https://allin.com",
        "transcript_sources": ["podscripts", "youtube"],
        "youtube_channel": "UCESLZhusAkFfsNsApnjF_Cg",
        "relevance": "Tech, AI, venture capital, macro trends, enterprise software"
    },
    {
        "name": "Moonshots",
        "host": "Peter Diamandis",
        "rss": "https://feeds.simplecast.com/54nAGcIl",
        "website": "https://moonshots.com",
        "transcript_sources": ["podscripts", "youtube"],
        "relevance": "Exponential technology, innovation, future of business"
    },
    {
        "name": "Lex Fridman Podcast",
        "host": "Lex Fridman",
        "rss": "https://lexfridman.com/feed/podcast/",
        "website": "https://lexfridman.com",
        "transcript_sources": ["website", "youtube"],
        "youtube_channel": "UCSHZKyawb77ixDdsGog4iWA",
        "relevance": "Deep AI/tech interviews, frontier research, key industry figures"
    },
    {
        "name": "Retailgentic",
        "host": "",
        "rss": "",
        "website": "https://retailgentic.com",
        "transcript_sources": ["website", "podscripts"],
        "relevance": "AI in retail, agentic commerce, retail transformation"
    },
    {
        "name": "Retail Media Breakfast Club",
        "host": "",
        "rss": "",
        "website": "https://retailmediabreakfastclub.com",
        "transcript_sources": ["website", "podscripts"],
        "relevance": "Retail media industry news, network strategies, advertiser perspectives"
    },
    {
        "name": "Commerce Media Matters",
        "host": "",
        "rss": "",
        "website": "",
        "transcript_sources": ["podscripts"],
        "relevance": "Commerce media ecosystem, brand strategies, technology"
    },
]

# ─── DELIVERY SETTINGS ───────────────────────────────────────────────────────

DELIVERY = {
    "email_to": "raphael.hodes@gmail.com",
    "email_from_name": "Raph's Intel System",
    "lookback_hours": 30,  # How far back to look for new content (slightly > 24hr to catch stragglers)
}

# ─── TRANSCRIPT SCRAPING ─────────────────────────────────────────────────────

TRANSCRIPT_SOURCES = {
    "podscripts_base": "https://podscripts.co/podcasts/",
    "youtube_transcript_api": True,
    "max_transcript_chars": 80000,  # Truncate very long transcripts before sending to Claude
}

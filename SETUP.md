# Raph's Daily Intelligence Brief — Setup Guide

## What this system does

Two agents run automatically at 6:00 AM Sydney time every day:

1. **News Agent** — searches the web across your 5 topic areas, synthesises findings through your three lenses (Google, Spyr, Growth), delivers to Gmail + Notion
2. **Podcast Agent** — checks RSS feeds for new episodes, scrapes transcripts, produces deep per-episode analysis, delivers to Gmail + Notion

---

## What you need

- A **GitHub account** (free)
- An **Anthropic API key** — get one at console.anthropic.com
- A **Notion account** with two pages created (News Brief parent, Podcast Brief parent)
- A **Gmail App Password** (not your regular Gmail password)

Estimated setup time: **30-45 minutes**

---

## Step 1: Create your GitHub repo

1. Go to github.com → New repository
2. Name it `raph-intel` (or anything you like)
3. Set to **Private**
4. Don't initialise with README
5. Clone it to your computer or upload the files via the GitHub web interface

Upload all files from this folder, maintaining the folder structure:
```
raph-intel/
├── .github/
│   └── workflows/
│       └── daily-brief.yml
├── agents/
│   ├── news_agent.py
│   └── podcast_agent.py
├── utils/
│   └── delivery.py
├── config.py
├── requirements.txt
└── SETUP.md
```

---

## Step 2: Get your Anthropic API key

1. Go to **console.anthropic.com**
2. Sign in → API Keys → Create Key
3. Copy the key (starts with `sk-ant-...`)
4. You'll need credits — top up at least $20 to start

---

## Step 3: Set up Notion

### Create your two parent pages
1. In Notion, create a new page called **"News Intelligence Briefs"**
2. Create another new page called **"Podcast Intelligence Briefs"**

### Get the Notion Integration token
1. Go to **notion.so/my-integrations** → New Integration
2. Name it "Raph Intel System"
3. Select your workspace
4. Copy the **Internal Integration Token** (starts with `ntn_...` or `secret_...`)

### Get the Notion page IDs
1. Open each parent page in Notion
2. Click Share → Copy link
3. The page ID is the long string at the end of the URL:
   `https://notion.so/Your-Page-Name-**abc123def456...**`
4. Copy the ID portion (32 characters)

### Connect the integration to your pages
1. Open each Notion page
2. Click `...` menu → Add connections → Select "Raph Intel System"
3. Do this for BOTH pages

---

## Step 4: Get Gmail App Password

1. Go to your Google Account → Security
2. Enable **2-Step Verification** if not already on
3. Go to **App Passwords** (search in the Security section)
4. Select app: Mail, Select device: Other → type "Raph Intel"
5. Copy the 16-character app password generated

---

## Step 5: Add GitHub Secrets

In your GitHub repo → Settings → Secrets and variables → Actions → New repository secret

Add these 6 secrets:

| Secret name | Value |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key |
| `NOTION_API_KEY` | Your Notion integration token |
| `NOTION_NEWS_PAGE_ID` | ID of your "News Intelligence Briefs" page |
| `NOTION_PODCAST_PAGE_ID` | ID of your "Podcast Intelligence Briefs" page |
| `GMAIL_ADDRESS` | The Gmail address sending the email (e.g. raphael@spyr.com.au) |
| `GMAIL_APP_PASSWORD` | The 16-char app password from Step 4 |

---

## Step 6: Test it manually

1. In your GitHub repo → Actions tab
2. Click "Raph's Daily Intelligence Brief"
3. Click "Run workflow" → choose `both` → Run
4. Watch the logs to confirm both agents complete successfully
5. Check your Gmail and Notion

---

## Step 7: Confirm the schedule

The system runs at **8:00 PM UTC** daily, which equals:
- **6:00 AM AEDT** (Sydney daylight saving, Oct–Apr)
- **6:00 AM AEST** (Sydney standard time, Apr–Oct) — actually 6am UTC+10, so 8pm UTC is correct year-round for 6am AEST, and 7am AEDT

> Note: If you want exactly 6am year-round in Sydney, you'd need to manually adjust the cron between `0 20 * * *` (for UTC+10) and `0 19 * * *` (for UTC+11 daylight saving). The current setting is `0 20 * * *` which gives you 6am AEST and 7am AEDT — close enough for most purposes.

---

## Customising the system

### Add a new podcast
Edit `config.py` → `PODCAST_SOURCES` list → add a new entry:
```python
{
    "name": "Podcast Name",
    "host": "Host Name",
    "rss": "https://...",  # RSS feed URL (find via Spotify, Apple Podcasts)
    "website": "https://...",
    "transcript_sources": ["podscripts", "website"],
    "relevance": "Why this podcast matters to Raph"
}
```

### Change delivery email
Edit `config.py` → `DELIVERY["email_to"]`

### Change the brief depth or format
Edit the system prompts in `agents/news_agent.py` and `agents/podcast_agent.py`

### Run only one agent
In GitHub Actions → Run workflow → choose `news` or `podcasts`

---

## Estimated monthly cost

- **GitHub Actions**: Free (well within free tier limits)
- **Anthropic API**: ~$8-15/month depending on brief length and number of podcast episodes
- **Notion**: Free tier is sufficient
- **Gmail**: Free

Total: **~$10-15 AUD/month**

---

## Troubleshooting

**Agent fails silently** → Check Actions logs, expand each step to see the error

**Notion page not created** → Confirm the integration is connected to both parent pages, and the page IDs are correct (no hyphens)

**Email not arriving** → Check spam folder, confirm App Password is correct, confirm GMAIL_ADDRESS is the sending account

**No podcast episodes found** → The RSS feed URL may be wrong or paywalled. Check config.py RSS URLs against the actual feed (Google "[podcast name] RSS feed")

**Transcript too short** → Some podcasts don't publish transcripts publicly. The agent will fall back to show notes, which still produces useful analysis.

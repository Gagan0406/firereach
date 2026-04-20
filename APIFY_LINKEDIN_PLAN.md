# Apify + LinkedIn/X Integration Plan

## Current Status

### ✅ What's Working
- **Tavily Search**: Fetches web search results with title, URL, content
- **Apify Google Search**: Uses `apify/google-search-scraper` actor
- **LLM Signal Extraction**: Processes snippets into structured signals
- **DeduplicationL Removes duplicate snippets

### ❌ What Needs Improvement

#### 1. **Apify Issues**
- Currently only uses Google Search Scraper (limited to search results)
- No LinkedIn profile extraction
- No X/Twitter data extraction
- Results may contain only headers (no detailed <p> tag content)

#### 2. **Tavily Limitations**
- Returns only summary snippets
- Missing <p> tag content from actual websites
- No web scraping capability

#### 3. **Missing Features**
- No real-time progress updates to frontend
- No streaming/async updates
- No LinkedIn company page data
- No X/Twitter mentions or posts

---

## Solution Approach (Step by Step)

### **Phase 1: Fix Apify + Add LinkedIn** ⏳
Goal: Enable LinkedIn company profile extraction

**Apify LinkedIn Actor Options:**
1. `apify/linkedin-company-scraper` - Company profile data
2. `apify/linkedin-profile-scraper` - Individual profiles
3. Generic web scraper with LinkedIn URLs

**What we'll extract:**
- Company size / employee growth
- Recent job postings
- Company description
- Location / industries
- Company news

---

### **Phase 2: Add X/Twitter Extraction** ⏳
Goal: Get latest company mentions and announcements

**Apify Twitter Actor:**
- `apify/twitter-search-scraper` - Search for company mentions
- Extract: tweets, engagement, sentiment, recent news

---

### **Phase 3: Enhance Tavily with Web Scraping** ⏳
Goal: Extract actual <p> tag content from websites

**Implementation:**
- After Tavily returns URLs, scrape each URL for <p> tags
- Use async to avoid blocking
- Extract full article content (not just summary)

---

### **Phase 4: Add Streaming UI** ⏳
Goal: Show real-time progress to user

**Frontend Changes:**
- WebSocket or Server-Sent Events (SSE)
- Show: "Searching Tavily...", "Scraping LinkedIn...", "Extracting X data..."
- Real-time signal count updates

**Backend Changes:**
- Emit progress events during signal harvesting
- Support async/await with streaming

---

## Technical Stack

### Apify Actors to Use
```
apify/google-search-scraper    ✅ (already using)
apify/linkedin-company-scraper  🔨 (to add)
apify/twitter-search-scraper    🔨 (to add)
apify/website-content-crawler   🔨 (for web scraping)
```

### APIs & Libraries
```
apify_client        ✅ (installed)
tavily             ✅ (installed)
beautifulsoup4     (for <p> tag extraction)
requests           (for website scraping)
asyncio            (for parallel requests)
```

---

## Implementation Order

1. **First**: Test current Apify + add LinkedIn company scraper
2. **Second**: Add X/Twitter scraper
3. **Third**: Enhance Tavily with web scraping
4. **Fourth**: Add streaming UI to frontend

---

## Questions to Answer First

1. **Apify Token**: Is it active? Check at https://console.apify.com/account/integrations
2. **Apify Rate Limits**: How many calls per month? (Free tier = 2,000 credits/month)
3. **LinkedIn Legality**: Can we scrape LinkedIn? (Check Apify Terms)
4. **Frontend Preference**: WebSocket or SSE for streaming?

---

## Next Step

Let's start with **Phase 1: Apify LinkedIn Setup**

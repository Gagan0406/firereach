"""
FireReach – Apify LinkedIn Company Scraper
Uses harvestapi/linkedin-company actor to extract rich company profile data.
"""
from __future__ import annotations

import re
from typing import Any

from apify_client import ApifyClient

try:
    from utils.logger import get_logger
except ImportError:
    def get_logger(name):
        class _L:
            def info(self, *a, **k): pass
            def error(self, *a, **k): pass
            def warning(self, *a, **k): pass
        return _L()


def _company_name_to_linkedin_slug(company_name: str) -> str:
    """Convert company name to likely LinkedIn URL slug."""
    slug = company_name.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)        # remove special chars except hyphen
    slug = re.sub(r'\s+', '-', slug)             # spaces to hyphens
    slug = re.sub(r'-+', '-', slug).strip('-')   # collapse multiple hyphens
    return slug


def _extract_linkedin_signals(company_name: str, apify_token: str, session_id: str) -> dict[str, Any]:
    """
    Fetch LinkedIn company profile via harvestapi/linkedin-company.
    Returns rich structured data: employee count, industries, locations, funding, etc.
    """
    logger = get_logger(session_id)

    try:
        client = ApifyClient(apify_token)
        slug = _company_name_to_linkedin_slug(company_name)
        linkedin_url = f"https://www.linkedin.com/company/{slug}/"

        logger.info("linkedin_scrape_started", company=company_name, url=linkedin_url)

        run = client.actor("harvestapi/linkedin-company").call(
            run_input={
                "companies": [linkedin_url],
                "maxItems": 1,
            },
            timeout_secs=120,
        )

        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())

        if not items:
            logger.warning("linkedin_no_results", company=company_name, url=linkedin_url)
            return {"error": f"No LinkedIn data found for {company_name}"}

        data = items[0]
        logger.info("linkedin_scrape_success", company=data.get("name", company_name))
        return data

    except Exception as e:
        logger.error("linkedin_scrape_failed", error=str(e))
        return {"error": str(e)}


def format_linkedin_signals(data: dict[str, Any]) -> list[str]:
    """
    Convert LinkedIn company profile data into human-readable signal strings for LLM.
    """
    if data.get("error"):
        return []

    signals = []

    # Company size
    employee_count = data.get("employeeCount")
    if employee_count:
        signals.append(f"LinkedIn shows {employee_count:,} employees")

    # Follower count (social proof)
    follower_count = data.get("followerCount")
    if follower_count:
        signals.append(f"{follower_count:,} followers on LinkedIn")

    # Tagline
    tagline = data.get("tagline")
    if tagline:
        signals.append(f"Company tagline: \"{tagline}\"")

    # Industries
    industries = data.get("industries") or []
    if industries:
        industry_names = [i.get("title") or i.get("name", "") for i in industries if i]
        industry_str = ", ".join(filter(None, industry_names[:3]))
        if industry_str:
            signals.append(f"Industry: {industry_str}")

    # Locations
    locations = data.get("locations") or []
    if len(locations) > 1:
        cities = []
        for loc in locations[:3]:
            city = loc.get("city") or loc.get("country") or ""
            if city:
                cities.append(city)
        if cities:
            signals.append(f"Global offices in: {', '.join(cities)}")
    elif len(locations) == 1:
        loc = locations[0]
        city = loc.get("city") or loc.get("country", "")
        if city:
            signals.append(f"Headquartered in {city}")

    # Funding data
    funding = data.get("fundingData")
    if funding:
        last_round = funding.get("lastFundingRound") or {}
        if last_round:
            round_type = last_round.get("fundingType", "")
            amount = last_round.get("moneyRaised", {}) or {}
            amount_str = ""
            if amount.get("amount"):
                currency = amount.get("currencyCode", "USD")
                amt = int(amount["amount"])
                amount_str = f" – {currency} {amt:,}"
            if round_type:
                signals.append(f"Last funding round: {round_type}{amount_str}")
        total = funding.get("fundingTotal", {}) or {}
        if total.get("amount"):
            currency = total.get("currencyCode", "USD")
            signals.append(f"Total funding: {currency} {int(total['amount']):,}")

    # People stats: engineering function count
    people_stats = data.get("peopleStats") or []
    for stat in people_stats:
        if stat.get("statTitle") == "Current Function":
            values = stat.get("values") or []
            eng = next((v for v in values if "Engineering" in v.get("title", "")), None)
            if eng:
                signals.append(f"{eng['count']} engineering employees on LinkedIn")
            break

    # Company description
    description = data.get("description")
    if description:
        signals.append(f"Company description: {description[:200]}")

    # Announcement
    announcement = data.get("announcement")
    if announcement:
        title = announcement.get("title", "")
        if title:
            signals.append(f"Recent LinkedIn announcement: {title[:150]}")

    return signals

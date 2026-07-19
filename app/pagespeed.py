import logging

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Monitor, PageSpeedResult

logger = logging.getLogger(__name__)

API_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

_CATEGORY_TO_FIELD = {
    "performance": "performance_score",
    "accessibility": "accessibility_score",
    "best-practices": "best_practices_score",
    "seo": "seo_score",
}


async def measure_pagespeed(db: AsyncSession, monitor: Monitor) -> PageSpeedResult | None:
    settings = get_settings()
    if not settings.pagespeed_api_key:
        logger.info("PAGESPEED_API_KEY not set; skipping PageSpeed check for monitor %s", monitor.id)
        return None

    url = monitor.config.get("url")
    if not url:
        return None

    params = {
        "url": url,
        "key": settings.pagespeed_api_key,
        "category": ["PERFORMANCE", "ACCESSIBILITY", "BEST_PRACTICES", "SEO"],
    }
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(API_URL, params=params)
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError:
        logger.exception("PageSpeed Insights request failed for monitor %s", monitor.id)
        return None

    categories = data.get("lighthouseResult", {}).get("categories", {})
    scores = {}
    for category_key, field_name in _CATEGORY_TO_FIELD.items():
        category = categories.get(category_key)
        score = category.get("score") if category else None
        scores[field_name] = round(score * 100) if score is not None else None

    result = PageSpeedResult(monitor_id=monitor.id, raw=data, **scores)
    db.add(result)
    await db.commit()
    return result

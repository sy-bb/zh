"""
Antpool 观察者链接采集器
策略：
  1. Playwright 打开页面，同时拦截所有 XHR/Fetch 请求
  2. 自动点击各统计标签，触发更多数据加载
  3. 从 API 响应中递归提取目标字段
  4. 把原始响应存入 raw_data，便于后续调试 / 修正解析逻辑
"""

import asyncio
import json
import logging
from datetime import date
from playwright.async_api import async_playwright, Page
from utils import deep_search, dump_captured

logger = logging.getLogger(__name__)

OBSERVER_URL = (
    "https://www.antpool.com/observer"
    "?accessKey=sByU3qnXEXJCYGk6ATfC"
    "&coinType=BTC"
    "&observerUserId=AMEE11"
)

TAB_TEXTS = [
    "收益统计", "收益", "Earnings", "算力统计", "算力", "Hashrate",
    "矿工", "Workers", "历史", "History", "统计", "Statistics",
]


async def fetch_antpool_stats() -> dict:
    api_data: list[dict] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
            locale="zh-CN",
        )
        page = await context.new_page()

        async def on_response(response):
            if response.request.resource_type not in ("xhr", "fetch"):
                return
            try:
                body = await response.json()
                api_data.append({"url": response.url, "data": body})
            except Exception:
                pass

        page.on("response", on_response)

        logger.info("[Antpool] 打开观察者页面...")
        await page.goto(OBSERVER_URL, wait_until="networkidle", timeout=60_000)
        await page.wait_for_timeout(4_000)

        await _click_tabs(page)
        await page.wait_for_timeout(3_000)
        await browser.close()

    dump_captured(api_data, "antpool")
    return _build_result(api_data)


async def _click_tabs(page: Page) -> None:
    for text in TAB_TEXTS:
        try:
            el = page.get_by_text(text, exact=False).first
            if await el.is_visible(timeout=1_500):
                await el.click()
                await page.wait_for_timeout(2_000)
                logger.info(f"[Antpool] 点击标签: {text}")
        except Exception:
            pass


def _build_result(api_data: list) -> dict:
    result = {
        "date": date.today().isoformat(),
        "pool": "antpool",
        "hashrate_th": None,
        "transferred_hashrate_th": None,
        "own_hashrate_th": None,
        "fpps_earnings_btc": None,
        "rewards_btc": None,
        "total_earnings_btc": None,
        "raw_data": api_data,  # 原始数据，存入 DB 便于调试
    }

    for item in api_data:
        deep_search(item["data"], result)

    # 推算缺失字段
    if result["own_hashrate_th"] is None and result["hashrate_th"] is not None:
        transferred = result["transferred_hashrate_th"] or 0
        result["own_hashrate_th"] = result["hashrate_th"] - transferred

    if result["total_earnings_btc"] is None:
        fpps = result["fpps_earnings_btc"] or 0
        reward = result["rewards_btc"] or 0
        if fpps or reward:
            result["total_earnings_btc"] = fpps + reward

    logger.info(f"[Antpool] 解析结果: {json.dumps(result, default=str, ensure_ascii=False)}")
    return result

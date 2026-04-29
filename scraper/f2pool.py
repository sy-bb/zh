"""
F2Pool 观察者链接采集器
策略：
  1. 先尝试 F2Pool 公开 API（无需浏览器，速度最快）
  2. 如果公开 API 字段不够，用 Playwright 打开观察者页面补全
"""

import asyncio
import json
import logging
from datetime import date
import urllib.request
from playwright.async_api import async_playwright, Page
from utils import deep_search, normalize_hashrate_to_th, to_float, dump_captured

logger = logging.getLogger(__name__)

OBSERVER_URL = (
    "https://www.f2pool.com/mining-user/"
    "4865ad31e0790a5ac70ab26ddfca8ecc"
    "?user_name=amee11f2pool"
)
PUBLIC_API_URL = "https://api.f2pool.com/bitcoin/amee11f2pool"

TAB_TEXTS = [
    "收益", "Earnings", "算力", "Hashrate",
    "矿工", "Workers", "历史", "History",
]


async def fetch_f2pool_stats() -> dict:
    result = {
        "date": date.today().isoformat(),
        "pool": "f2pool",
        "hashrate_th": None,
        "transferred_hashrate_th": None,
        "own_hashrate_th": None,
        "fpps_earnings_btc": None,
        "rewards_btc": None,
        "total_earnings_btc": None,
        "raw_data": [],
    }

    # 1. 尝试公开 API
    pub = _try_public_api()
    if pub:
        result["raw_data"].append({"url": PUBLIC_API_URL, "data": pub})
        _parse_public_api(pub, result)
        logger.info("[F2Pool] 公开 API 获取成功")

    # 2. Playwright 补全（页面可能有更多字段）
    api_data = await _playwright_scrape()
    result["raw_data"].extend(api_data)
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

    logger.info(f"[F2Pool] 解析结果: {json.dumps(result, default=str, ensure_ascii=False)}")
    return result


def _try_public_api() -> dict | None:
    """尝试直接调用 F2Pool 公开 API"""
    try:
        req = urllib.request.Request(
            PUBLIC_API_URL,
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        logger.warning(f"[F2Pool] 公开 API 失败: {e}")
        return None


def _parse_public_api(data: dict, result: dict) -> None:
    """解析 F2Pool 公开 API 已知字段"""
    # 算力：hashrate_info 对象 或 hashrate 字段（单位 H/s）
    hashrate_info = data.get("hashrate_info", {})
    raw_hr = (
        hashrate_info.get("hashrate_last24h")
        or data.get("hashrate_last24h")
        or data.get("hashrate")
    )
    if raw_hr is not None:
        # F2Pool 公开 API 返回的是 H/s，需转为 TH/s
        val = to_float(raw_hr)
        if val:
            result["hashrate_th"] = val / 1e12

    # 余额 / 收益
    bal = to_float(data.get("balance"))
    paid = to_float(data.get("paid"))
    if paid:
        result["total_earnings_btc"] = paid
    if bal:
        result["fpps_earnings_btc"] = bal  # 当日未支付部分作为当日收益估算


async def _playwright_scrape() -> list:
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

        logger.info("[F2Pool] 打开观察者页面...")
        await page.goto(OBSERVER_URL, wait_until="networkidle", timeout=60_000)
        await page.wait_for_timeout(4_000)

        for text in TAB_TEXTS:
            try:
                el = page.get_by_text(text, exact=False).first
                if await el.is_visible(timeout=1_500):
                    await el.click()
                    await page.wait_for_timeout(2_000)
                    logger.info(f"[F2Pool] 点击标签: {text}")
            except Exception:
                pass

        await page.wait_for_timeout(3_000)
        await browser.close()

    dump_captured(api_data, "f2pool")
    return api_data

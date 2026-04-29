"""
Phase 1: 打开观察者页面，拦截所有 XHR/Fetch 请求，找出后台 API 接口
运行后会打印出所有捕获的接口及响应内容，供 Phase 2 使用
"""

import asyncio
import json
from playwright.async_api import async_playwright

OBSERVER_LINKS = {
    "antpool": "https://www.antpool.com/observer?accessKey=sByU3qnXEXJCYGk6ATfC&coinType=BTC&observerUserId=AMEE11",
    "f2pool":  "https://www.f2pool.com/mining-user/4865ad31e0790a5ac70ab26ddfca8ecc?user_name=amee11f2pool",
}

KEYWORDS = ["hash", "earn", "payment", "revenue", "stat", "worker", "coin", "daily", "history", "output"]

captured = []

async def run_discovery(pool_name: str, url: str):
    print(f"\n{'='*60}")
    print(f"  正在分析: {pool_name.upper()}")
    print(f"{'='*60}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        async def on_response(response):
            req = response.request
            if req.resource_type not in ("xhr", "fetch"):
                return
            req_url = req.url
            lower_url = req_url.lower()
            if not any(k in lower_url for k in KEYWORDS):
                return
            try:
                body = await response.json()
            except Exception:
                return

            entry = {
                "pool":      pool_name,
                "method":    req.method,
                "url":       req_url,
                "post_data": req.post_data,
                "response":  body,
            }
            captured.append(entry)
            print(f"\n[{req.method}] {req_url}")
            if req.post_data:
                print(f"  POST body : {req.post_data[:300]}")
            print(f"  Response  : {json.dumps(body, ensure_ascii=False)[:600]}")

        page.on("response", on_response)

        print(f"\n>>> 打开页面，等待数据加载…")
        await page.goto(url, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(5000)

        # 尝试点击页面内常见标签（收益、算力、历史等）
        tab_selectors = [
            "text=Earnings", "text=收益", "text=Hashrate", "text=算力",
            "text=Workers", "text=矿工", "text=History", "text=历史",
            "text=Payment", "text=支付", "text=Daily", "text=Statistics",
        ]
        for sel in tab_selectors:
            try:
                el = page.locator(sel).first
                if await el.is_visible(timeout=1500):
                    await el.click()
                    await page.wait_for_timeout(2000)
                    print(f"  [点击] {sel}")
            except Exception:
                pass

        await page.wait_for_timeout(3000)
        await browser.close()

    print(f"\n>>> {pool_name.upper()} 共捕获 {sum(1 for c in captured if c['pool']==pool_name)} 个相关接口")


async def main():
    for name, link in OBSERVER_LINKS.items():
        await run_discovery(name, link)

    print(f"\n\n{'='*60}")
    print("  汇总：所有捕获接口")
    print(f"{'='*60}")
    for i, c in enumerate(captured, 1):
        print(f"\n[{i}] [{c['pool'].upper()}] {c['method']} {c['url']}")
        if c["post_data"]:
            print(f"    POST: {c['post_data'][:200]}")

    with open("discovered_apis.json", "w", encoding="utf-8") as f:
        json.dump(captured, f, ensure_ascii=False, indent=2)
    print("\n>>> 完整结果已保存到 discovered_apis.json")


if __name__ == "__main__":
    asyncio.run(main())

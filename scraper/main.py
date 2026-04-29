"""
入口脚本：采集 Antpool + F2Pool 数据，写入 Supabase
"""
import asyncio
import logging
import sys
from antpool import fetch_antpool_stats
from f2pool import fetch_f2pool_stats
from db import upsert_stats

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


async def main():
    errors = []

    for name, coro in [("Antpool", fetch_antpool_stats()), ("F2Pool", fetch_f2pool_stats())]:
        try:
            data = await coro
            upsert_stats(data)
            logger.info(f"[{name}] 完成")
        except Exception as e:
            logger.error(f"[{name}] 失败: {e}", exc_info=True)
            errors.append(name)

    if errors:
        logger.error(f"以下矿池采集失败: {errors}")
        sys.exit(1)
    else:
        logger.info("所有矿池数据采集完成")


if __name__ == "__main__":
    asyncio.run(main())

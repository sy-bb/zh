import re
import json
import logging

logger = logging.getLogger(__name__)


def to_float(val) -> float | None:
    if val is None:
        return None
    try:
        return float(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def normalize_hashrate_to_th(val, unit_hint: str = "") -> float | None:
    """将各种单位的算力统一转换为 TH/s"""
    num = to_float(val)
    if num is None:
        return None
    unit = unit_hint.upper()
    if "PH" in unit:
        return num * 1000
    if "EH" in unit:
        return num * 1_000_000
    if "GH" in unit:
        return num / 1000
    if "MH" in unit:
        return num / 1_000_000
    # 默认假设 TH/s（BTC 矿池最常见单位）
    return num


def deep_search(obj, result: dict, path="", depth=0):
    """递归搜索 JSON 对象，按字段名模式提取值"""
    if depth > 6 or not isinstance(obj, (dict, list)):
        return

    if isinstance(obj, list):
        for item in obj:
            deep_search(item, result, path, depth + 1)
        return

    for key, val in obj.items():
        k = key.lower()
        full_path = f"{path}.{key}" if path else key

        logger.debug(f"  field: {full_path} = {str(val)[:80]}")

        # 算力 -------------------------------------------------------
        if "hash" in k or "hashrate" in k:
            # 转出算力
            if any(w in k for w in ("transfer", "out", "输出", "转出")):
                if result.get("transferred_hashrate_th") is None:
                    result["transferred_hashrate_th"] = normalize_hashrate_to_th(val)
            # 自有算力
            elif any(w in k for w in ("own", "real", "local", "self", "自有")):
                if result.get("own_hashrate_th") is None:
                    result["own_hashrate_th"] = normalize_hashrate_to_th(val)
            # 日算力（总）
            elif result.get("hashrate_th") is None and isinstance(val, (int, float, str)):
                result["hashrate_th"] = normalize_hashrate_to_th(val)

        # 收益 -------------------------------------------------------
        elif "fpps" in k:
            if result.get("fpps_earnings_btc") is None:
                result["fpps_earnings_btc"] = to_float(val)

        elif any(w in k for w in ("reward", "bonus", "奖励")):
            if result.get("rewards_btc") is None:
                result["rewards_btc"] = to_float(val)

        elif any(w in k for w in ("total", "sum")) and any(
            w in k for w in ("earn", "income", "revenue", "profit", "收益")
        ):
            if result.get("total_earnings_btc") is None:
                result["total_earnings_btc"] = to_float(val)

        # 递归嵌套
        if isinstance(val, (dict, list)):
            deep_search(val, result, full_path, depth + 1)


def dump_captured(api_data: list, pool: str) -> None:
    """把捕获的原始接口输出到日志，方便调试"""
    logger.info(f"\n{'='*60}")
    logger.info(f"[{pool.upper()}] 共捕获 {len(api_data)} 个 API 响应")
    for i, item in enumerate(api_data, 1):
        logger.info(f"  [{i}] {item['url']}")
        logger.info(f"       {json.dumps(item['data'], ensure_ascii=False)[:300]}")
    logger.info("=" * 60)

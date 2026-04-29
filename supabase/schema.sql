-- 在 Supabase SQL Editor 中运行此文件

CREATE TABLE IF NOT EXISTS daily_mining_stats (
    id          BIGSERIAL PRIMARY KEY,
    date        DATE        NOT NULL,
    pool        TEXT        NOT NULL CHECK (pool IN ('antpool', 'f2pool')),

    -- 算力 (TH/s)
    hashrate_th              NUMERIC(20, 4),
    transferred_hashrate_th  NUMERIC(20, 4),
    own_hashrate_th          NUMERIC(20, 4),

    -- 收益 (BTC)
    fpps_earnings_btc  NUMERIC(20, 8),
    rewards_btc        NUMERIC(20, 8),
    total_earnings_btc NUMERIC(20, 8),

    -- 调试用：存储原始 API 响应
    raw_data   JSONB,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE (date, pool)
);

-- 允许匿名读取（前端看板用）
ALTER TABLE daily_mining_stats ENABLE ROW LEVEL SECURITY;
CREATE POLICY "public_read" ON daily_mining_stats FOR SELECT USING (true);

-- 加速查询的索引
CREATE INDEX IF NOT EXISTS idx_dms_date ON daily_mining_stats (date DESC);
CREATE INDEX IF NOT EXISTS idx_dms_pool ON daily_mining_stats (pool);

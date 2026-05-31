-- airflow_db는 POSTGRES_DB 환경변수로 자동 생성됨
-- auction 서비스용 DB를 추가로 생성
CREATE DATABASE auction_db;
GRANT ALL PRIVILEGES ON DATABASE auction_db TO auction_admin;

\c auction_db

-- ── item_info ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS item_info (
    item_id             INT             PRIMARY KEY,
    item_name           VARCHAR(255)    NOT NULL,
    item_type           VARCHAR(20)     NOT NULL
                            CHECK (item_type IN ('equipment', 'consumable', 'etc')),
    category_major      VARCHAR(100),
    category_mid        VARCHAR(100),
    category_sub        VARCHAR(100),
    icon_url            TEXT,

    req_level           SMALLINT        DEFAULT 0,
    req_str             SMALLINT        DEFAULT 0,
    req_dex             SMALLINT        DEFAULT 0,
    req_int             SMALLINT        DEFAULT 0,
    req_luk             SMALLINT        DEFAULT 0,
    req_pop             SMALLINT,
    req_job             VARCHAR(100),
    gender              VARCHAR(20),
    equipped_img_url    TEXT,
    base_effects        JSONB,
    upgrade_slots       SMALLINT,

    description         TEXT
);

CREATE INDEX idx_item_info_type     ON item_info (item_type);
CREATE INDEX idx_item_info_category ON item_info (category_sub);
CREATE INDEX idx_item_info_effects  ON item_info USING GIN (base_effects);

-- ── users ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    user_id     UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    username    VARCHAR(50) NOT NULL UNIQUE,
    meso        BIGINT      NOT NULL DEFAULT 0 CHECK (meso >= 0),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── auction_listings ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS auction_listings (
    listing_id  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    instance_id VARCHAR(24) NOT NULL,
    item_id     INT         NOT NULL REFERENCES item_info (item_id),
    seller_id   UUID        NOT NULL REFERENCES users (user_id),
    buyer_id    UUID        REFERENCES users (user_id),
    price       BIGINT      NOT NULL CHECK (price > 0),
    status      VARCHAR(20) NOT NULL DEFAULT 'listed'
                    CHECK (status IN ('listed', 'sold', 'cancelled')),
    listed_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sold_at     TIMESTAMPTZ
);

CREATE INDEX idx_auction_listed_item  ON auction_listings (item_id)    WHERE status = 'listed';
CREATE INDEX idx_auction_listed_price ON auction_listings (price)      WHERE status = 'listed';
CREATE INDEX idx_auction_listed_at    ON auction_listings (listed_at DESC);
CREATE INDEX idx_auction_seller       ON auction_listings (seller_id);
CREATE INDEX idx_auction_instance     ON auction_listings (instance_id);

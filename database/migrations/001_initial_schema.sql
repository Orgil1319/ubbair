-- 001: PostgreSQL + PostGIS үндсэн схем
-- Улаанбаатарын үл хөдлөх хөрөнгийн зөвлөх системийн өгөгдлийн сан

-- PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- Хэсэгчилсэн хайлтад

-- ==========================================
-- БАЙРНЫ МЭДЭЭЛЭЛ
-- ==========================================
CREATE TABLE properties (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title           TEXT,
    address         TEXT NOT NULL,
    district        TEXT,
    price           BIGINT,              -- ₮
    area_sqm        NUMERIC(8, 2),
    floor           SMALLINT,
    total_floors    SMALLINT,
    build_year      SMALLINT,
    rooms           SMALLINT,
    property_type   TEXT DEFAULT 'apartment',
    permit_id       TEXT,
    developer_name  TEXT,
    geom            GEOMETRY(POINT, 4326),  -- WGS84 солбицол
    risk_score      SMALLINT,              -- 0–100
    risk_level      TEXT,
    source_url      TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_properties_geom ON properties USING GIST(geom);
CREATE INDEX idx_properties_district ON properties(district);
CREATE INDEX idx_properties_risk ON properties(risk_score);

-- ==========================================
-- ЭРСДЭЛИЙН БҮСҮҮД (GIS)
-- ==========================================
CREATE TABLE flood_zones (
    zone_id         SERIAL PRIMARY KEY,
    area_name       TEXT,
    risk_level      TEXT NOT NULL,  -- 'high', 'medium', 'low'
    description_mn  TEXT,
    season          TEXT,
    geom            GEOMETRY(MULTIPOLYGON, 4326) NOT NULL,
    source          TEXT DEFAULT 'ОБЕГ',
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_flood_zones_geom ON flood_zones USING GIST(geom);

CREATE TABLE landslide_zones (
    zone_id         SERIAL PRIMARY KEY,
    area_name       TEXT,
    risk_level      TEXT NOT NULL,
    slope_degree    NUMERIC(5, 2),
    soil_type       TEXT,
    geom            GEOMETRY(MULTIPOLYGON, 4326) NOT NULL,
    source          TEXT DEFAULT 'ОБЕГ',
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_landslide_zones_geom ON landslide_zones USING GIST(geom);

CREATE TABLE earthquake_faults (
    fault_id        SERIAL PRIMARY KEY,
    fault_name      TEXT,
    activity_level  TEXT,   -- 'active', 'potentially_active', 'inactive'
    geom            GEOMETRY(MULTILINESTRING, 4326) NOT NULL,
    source          TEXT DEFAULT 'Геологийн хүрээлэн',
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_earthquake_faults_geom ON earthquake_faults USING GIST(geom);

-- ==========================================
-- ХАР ЖАГСААЛТ
-- ==========================================
CREATE TABLE blacklisted_companies (
    id                  SERIAL PRIMARY KEY,
    company_name        TEXT NOT NULL,
    normalized_name     TEXT NOT NULL UNIQUE,  -- Хайлтад ашиглана
    reason              TEXT,
    source              TEXT,  -- 'НХБХГ', 'МХГ', 'Шүүх'
    blacklisted_date    DATE,
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_blacklist_normalized ON blacklisted_companies(normalized_name);
-- Хэсэгчилсэн хайлтад (trigram index)
CREATE INDEX idx_blacklist_trgm ON blacklisted_companies
    USING GIN(normalized_name gin_trgm_ops);

-- ==========================================
-- БАРИЛГЫН ЗӨВШӨӨРӨЛ
-- ==========================================
CREATE TABLE building_permits (
    permit_id       TEXT PRIMARY KEY,
    company_name    TEXT,
    address         TEXT,
    status          TEXT NOT NULL,
    -- 'authorized', 'unauthorized', 'not_accepted', 'expired'
    issued_date     DATE,
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE blacklisted_buildings (
    id          SERIAL PRIMARY KEY,
    permit_id   TEXT REFERENCES building_permits(permit_id),
    reason      TEXT,
    listed_date DATE,
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ==========================================
-- ЗАХ ЗЭЭЛИЙН ҮНЭ
-- ==========================================
CREATE TABLE market_prices (
    id              SERIAL PRIMARY KEY,
    district        TEXT NOT NULL,
    price           BIGINT NOT NULL,
    area_sqm        NUMERIC(8, 2) NOT NULL,
    price_per_sqm   INT NOT NULL,
    property_type   TEXT DEFAULT 'apartment',
    floor           SMALLINT,
    build_year      SMALLINT,
    source          TEXT DEFAULT 'unegui.mn',
    scraped_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_market_prices_district ON market_prices(district, scraped_at DESC);

-- ==========================================
-- ГЭРЭЭ
-- ==========================================
CREATE TABLE contracts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_number TEXT UNIQUE,
    owner_name      TEXT NOT NULL,
    owner_register  TEXT NOT NULL,
    tenant_name     TEXT NOT NULL,
    tenant_register TEXT NOT NULL,
    property_address TEXT NOT NULL,
    monthly_rent    BIGINT NOT NULL,
    deposit         BIGINT NOT NULL,
    start_date      DATE NOT NULL,
    end_date        DATE NOT NULL,
    notice_days     SMALLINT DEFAULT 30,
    status          TEXT DEFAULT 'draft',
    -- 'draft', 'signed', 'registered', 'expired', 'terminated'
    pdf_path        TEXT,
    signed_at       TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_contracts_tenant ON contracts(tenant_register);
CREATE INDEX idx_contracts_end_date ON contracts(end_date);

-- ==========================================
-- САНУУЛГА
-- ==========================================
CREATE TABLE notifications (
    id              SERIAL PRIMARY KEY,
    contract_id     UUID REFERENCES contracts(id),
    type            TEXT NOT NULL,
    -- 'lease_expiry_30d', 'lease_expiry_7d', 'payment_due'
    sent_at         TIMESTAMPTZ,
    scheduled_for   TIMESTAMPTZ NOT NULL,
    status          TEXT DEFAULT 'pending'
);

-- ==========================================
-- ДАТА ШИНЭЧЛЭЛТИЙН ЛОГ
-- ==========================================
CREATE TABLE data_refresh_log (
    id          SERIAL PRIMARY KEY,
    started_at  TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    results     TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ==========================================
-- ДҮҮРГИЙН ХИЛ (GIS)
-- ==========================================
CREATE TABLE districts (
    id          SERIAL PRIMARY KEY,
    name_mn     TEXT NOT NULL UNIQUE,
    name_en     TEXT,
    geom        GEOMETRY(MULTIPOLYGON, 4326)
);

CREATE INDEX idx_districts_geom ON districts USING GIST(geom);

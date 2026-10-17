-- 002: User authentication and advertisement approval tables

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           TEXT NOT NULL UNIQUE,
    name            TEXT,
    password_hash   TEXT NOT NULL,
    is_admin        BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);

CREATE TABLE ads (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    title           TEXT NOT NULL,
    description     TEXT NOT NULL,
    address         TEXT NOT NULL,
    price           BIGINT NOT NULL,
    area_sqm        NUMERIC(8, 2) NOT NULL,
    rooms           SMALLINT NOT NULL,
    property_type   TEXT DEFAULT 'apartment',
    status          TEXT DEFAULT 'pending',
    admin_comment   TEXT,
    approved_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ads_status ON ads(status);
CREATE INDEX idx_ads_user_id ON ads(user_id);

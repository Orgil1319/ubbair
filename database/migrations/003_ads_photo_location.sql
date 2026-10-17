-- 003: Add photo and geo-location support to ads

ALTER TABLE ads
    ADD COLUMN photo_url TEXT,
    ADD COLUMN latitude NUMERIC(10, 6),
    ADD COLUMN longitude NUMERIC(10, 6);

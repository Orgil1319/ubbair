import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Request

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/properties")
async def list_properties(
    request: Request,
    q: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
    risk: Optional[str] = Query(None),
    min_price: Optional[int] = Query(None),
    max_price: Optional[int] = Query(None),
):
    """Байрны жагсаалт DB-аас буцаана."""
    try:
        pool = request.app.state.db
        conditions = []
        params = []
        idx = 1

        if q:
            conditions.append(f"(title ILIKE ${idx} OR address ILIKE ${idx})")
            params.append(f"%{q}%")
            idx += 1

        if district:
            conditions.append(f"address ILIKE ${idx}")
            params.append(f"%{district}%")
            idx += 1

        if risk:
            risk_map = {"Аюулгүй": "low", "Дунд": "medium", "Өндөр": "high"}
            conditions.append(f"risk_level = ${idx}")
            params.append(risk_map.get(risk, risk.lower()))
            idx += 1

        if min_price is not None:
            conditions.append(f"price >= ${idx}")
            params.append(min_price)
            idx += 1

        if max_price is not None:
            conditions.append(f"price <= ${idx}")
            params.append(max_price)
            idx += 1

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        async with pool.acquire() as conn:
            rows = await conn.fetch(f"""
                SELECT
                    id::text,
                    title,
                    address,
                    price,
                    area_sqm        AS area,
                    rooms,
                    floor,
                    total_floors    AS "totalFloors",
                    build_year      AS "builtYear",
                    property_type   AS "buildingType",
                    developer_name  AS developer,
                    risk_level      AS "riskLevel",
                    source_url      AS description,
                    ST_Y(geom::geometry) AS lat,
                    ST_X(geom::geometry) AS lng
                FROM properties
                {where}
                ORDER BY created_at DESC
                LIMIT 200
            """, *params)

        return [dict(r) for r in rows]

    except Exception as exc:
        logger.error(f"Property list error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/properties/{property_id}")
async def get_property(request: Request, property_id: str):
    """Нэг байрны дэлгэрэнгүй мэдээлэл буцаана."""
    try:
        pool = request.app.state.db
        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT
                    id::text,
                    title,
                    address,
                    price,
                    area_sqm        AS area,
                    rooms,
                    floor,
                    total_floors    AS "totalFloors",
                    build_year      AS "builtYear",
                    property_type   AS "buildingType",
                    developer_name  AS developer,
                    risk_level      AS "riskLevel",
                    source_url      AS description,
                    ST_Y(geom::geometry) AS lat,
                    ST_X(geom::geometry) AS lng
                FROM properties
                WHERE id::text = $1
            """, property_id)

        if not row:
            raise HTTPException(status_code=404, detail="Property not found")
        return dict(row)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Property get error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

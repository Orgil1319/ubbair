import os
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status
from pydantic import BaseModel

from app.api.auth import get_current_user

router = APIRouter()


class AdStatusPayload(BaseModel):
    admin_comment: Optional[str] = None


def get_uploads_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    uploads = root / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    return uploads


def row_to_ad(row) -> dict:
    return {
        "id": str(row["id"]),
        "userId": str(row["user_id"]),
        "title": row["title"],
        "description": row["description"],
        "address": row["address"],
        "price": row["price"],
        "area": float(row["area_sqm"]),
        "rooms": row["rooms"],
        "propertyType": row["property_type"],
        "photoUrl": row.get("photo_url"),
        "latitude": row.get("latitude"),
        "longitude": row.get("longitude"),
        "status": row["status"],
        "adminComment": row["admin_comment"],
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
        "approvedAt": row["approved_at"],
    }


@router.get("")
@router.get("/", include_in_schema=False)
async def list_ads(request: Request, q: Optional[str] = None):
    """Approved ads for public listing."""
    try:
        pool = request.app.state.db
        conditions = ["status = 'approved'"]
        params = []
        idx = 1

        if q:
            conditions.append(f"(title ILIKE ${idx} OR description ILIKE ${idx} OR address ILIKE ${idx})")
            params.append(f"%{q}%")
            idx += 1

        where = "WHERE " + " AND ".join(conditions)

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT id, user_id, title, description, address, price, area_sqm, rooms, property_type,                       photo_url, latitude, longitude,                       status, admin_comment, created_at, updated_at, approved_at
                FROM ads
                {where}
                ORDER BY created_at DESC
                LIMIT 200
                """,
                *params,
            )

        return [row_to_ad(r) for r in rows]

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/me")
async def get_my_ads(request: Request):
    user = await get_current_user(request)
    try:
        pool = request.app.state.db
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, user_id, title, description, address, price, area_sqm, rooms, property_type,
                       photo_url, latitude, longitude,
                       status, admin_comment, created_at, updated_at, approved_at
                FROM ads
                WHERE user_id::text = $1
                ORDER BY created_at DESC
                """,
                user["id"],
            )
        return [row_to_ad(r) for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/pending")
async def list_pending_ads(request: Request):
    user = await get_current_user(request)
    if not user.get("is_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    try:
        pool = request.app.state.db
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, user_id, title, description, address, price, area_sqm, rooms, property_type,
                       photo_url, latitude, longitude,
                       status, admin_comment, created_at, updated_at, approved_at
                FROM ads
                WHERE status = 'pending'
                ORDER BY created_at ASC
                """
            )
        return [row_to_ad(r) for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/admin/stats")
async def get_admin_stats(request: Request):
    user = await get_current_user(request)
    if not user.get("is_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    try:
        pool = request.app.state.db
        async with pool.acquire() as conn:
            stats = await conn.fetchrow(
                """
                SELECT
                    (SELECT COUNT(*) FROM ads WHERE status = 'pending') AS pending_count,
                    (SELECT COUNT(*) FROM ads WHERE status = 'approved') AS approved_count,
                    (SELECT COUNT(*) FROM ads WHERE status = 'rejected') AS rejected_count,
                    (SELECT COUNT(*) FROM ads) AS total_ads,
                    (SELECT COUNT(*) FROM users) AS total_users
                """
            )
        return {
            "pendingCount": int(stats["pending_count"]),
            "approvedCount": int(stats["approved_count"]),
            "rejectedCount": int(stats["rejected_count"]),
            "totalAds": int(stats["total_ads"]),
            "totalUsers": int(stats["total_users"]),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("")
@router.post("/", include_in_schema=False)
async def create_ad(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    address: str = Form(...),
    price: int = Form(...),
    area_sqm: float = Form(...),
    rooms: int = Form(...),
    property_type: str = Form("apartment"),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    photo: Optional[UploadFile] = File(None),
):
    user = await get_current_user(request)
    photo_url = None
    try:
        if photo is not None:
            uploads_dir = get_uploads_dir()
            filename = f"{uuid4().hex}_{photo.filename}"
            file_path = uploads_dir / filename
            with file_path.open("wb") as buffer:
                buffer.write(await photo.read())
            photo_url = f"/uploads/{filename}"

        pool = request.app.state.db
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO ads (user_id, title, description, address, price, area_sqm, rooms, property_type, photo_url, latitude, longitude)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                RETURNING id::text AS id
                """,
                user["id"],
                title,
                description,
                address,
                price,
                area_sqm,
                rooms,
                property_type,
                photo_url,
                latitude,
                longitude,
            )
        return {"id": row["id"], "status": "pending"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/{ad_id}/approve")
async def approve_ad(request: Request, ad_id: str, payload: AdStatusPayload):
    user = await get_current_user(request)
    if not user.get("is_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    try:
        pool = request.app.state.db
        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE ads
                SET status = 'approved', admin_comment = $1, approved_at = NOW(), updated_at = NOW()
                WHERE id::text = $2
                """,
                payload.admin_comment,
                ad_id,
            )
        if result == "UPDATE 0":
            raise HTTPException(status_code=404, detail="Ad not found")
        return {"status": "approved", "adId": ad_id}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/{ad_id}/reject")
async def reject_ad(request: Request, ad_id: str, payload: AdStatusPayload):
    user = await get_current_user(request)
    if not user.get("is_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    try:
        pool = request.app.state.db
        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE ads
                SET status = 'rejected', admin_comment = $1, updated_at = NOW()
                WHERE id::text = $2
                """,
                payload.admin_comment,
                ad_id,
            )
        if result == "UPDATE 0":
            raise HTTPException(status_code=404, detail="Ad not found")
        return {"status": "rejected", "adId": ad_id}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

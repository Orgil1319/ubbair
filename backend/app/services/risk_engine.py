"""
Эрсдэлийн үнэлгээний гол логик.
Үер, хөрсний нуралт, барилгын зөвшөөрөл, хар жагсаалт — бүгдийг нэгтгэж
0–100 оноо болон хэрэглэгчдэд ойлгомжтой тайлбар гаргана.
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    CRITICAL = "critical"   # 🔴 Яаралтай анхааруулга
    HIGH = "high"           # 🔴 Өндөр эрсдэл
    MEDIUM = "medium"       # 🟡 Дунд эрсдэл
    LOW = "low"             # 🟢 Бага эрсдэл
    UNKNOWN = "unknown"     # ⚪ Мэдэгдэхгүй


@dataclass
class RiskFactor:
    type: str           # "flood", "landslide", "permit", "blacklist", "earthquake"
    level: RiskLevel
    score: int          # 0–100
    title_mn: str       # Монгол тайлбар
    description_mn: str
    source: str         # Дата эх сурвалж
    last_updated: Optional[str] = None


@dataclass
class RiskAssessment:
    property_id: str
    overall_score: int              # 0–100 (0 = аюулгүй, 100 = маш аюултай)
    overall_level: RiskLevel
    factors: list[RiskFactor] = field(default_factory=list)
    summary_mn: str = ""
    data_freshness_warning: bool = False
    assessed_at: str = ""


# Эрсдэлийн оноо тооцох жин
RISK_WEIGHTS = {
    "blacklist":   40,  # Хар жагсаалтад орсон → хамгийн аюултай
    "permit":      30,  # Зөвшөөрөлгүй барилга
    "flood":       20,  # Үерийн бүс
    "landslide":   15,  # Хөрсний нуралт
    "earthquake":  10,  # Газар хөдлөлтийн хагарал
}


class RiskEngine:
    def __init__(self, gis_service, blacklist_checker, db_session):
        self.gis = gis_service
        self.blacklist = blacklist_checker
        self.db = db_session

    async def assess(
        self,
        lat: float,
        lng: float,
        permit_id: Optional[str] = None,
        developer_name: Optional[str] = None,
    ) -> RiskAssessment:
        """
        Байрны байршил болон барилгын мэдээллийг үндэслэн
        бүрэн эрсдэлийн үнэлгээ гаргана.
        """
        factors: list[RiskFactor] = []

        # 1. Хар жагсаалт — хамгийн чухал шалгалт
        if developer_name:
            bl_result = await self.blacklist.check(developer_name)
            if bl_result["found"]:
                factors.append(RiskFactor(
                    type="blacklist",
                    level=RiskLevel.CRITICAL,
                    score=100,
                    title_mn="⚠️ Хар жагсаалтад бүртгэлтэй компани",
                    description_mn=(
                        f"'{developer_name}' компани НХБХГ буюу Мэргэжлийн "
                        f"Хяналтын хар жагсаалтад орсон байна. "
                        f"Шалтгаан: {bl_result.get('reason', 'тодорхойгүй')}. "
                        f"Энэ байрыг худалдан авахаас татгалзахыг зөвлөж байна."
                    ),
                    source="НХБХГ / Мэргэжлийн Хяналт",
                    last_updated=bl_result.get("updated_at"),
                ))

        # 2. Барилгын зөвшөөрөл
        if permit_id:
            permit = await self._check_permit(permit_id)
            if permit["status"] == "unauthorized":
                factors.append(RiskFactor(
                    type="permit",
                    level=RiskLevel.HIGH,
                    score=85,
                    title_mn="🚫 Зөвшөөрөлгүй барилга",
                    description_mn=(
                        "Энэ барилга НХБХГ-ын мэдээллийн санд зөвшөөрөлгүй "
                        "баригдсан обьектуудын жагсаалтад байна. "
                        "Хуулийн маргаан, нураах эрсдэл бий."
                    ),
                    source="НХБХГ нээлттэй дата",
                    last_updated=permit.get("updated_at"),
                ))
            elif permit["status"] == "not_accepted":
                factors.append(RiskFactor(
                    type="permit",
                    level=RiskLevel.MEDIUM,
                    score=60,
                    title_mn="⏳ Ашиглалтад хүлээн аваагүй",
                    description_mn=(
                        "Барилга баригдсан боловч албан ёсоор ашиглалтад "
                        "хүлээн аваагүй байна. Инженерийн шугам сүлжээ, "
                        "нийтийн үйлчилгээ холбогдоогүй байж болно."
                    ),
                    source="НХБХГ нээлттэй дата",
                    last_updated=permit.get("updated_at"),
                ))

        # 3. GIS эрсдэлийн шалгалт
        gis_risks = await self.gis.check_all_risks(lat, lng)

        if gis_risks.get("flood_zone"):
            zone = gis_risks["flood_zone"]
            score = 80 if zone["level"] == "high" else 50
            factors.append(RiskFactor(
                type="flood",
                level=RiskLevel.HIGH if zone["level"] == "high" else RiskLevel.MEDIUM,
                score=score,
                title_mn=f"🌊 Үерийн эрсдэлтэй бүс ({zone['level']})",
                description_mn=(
                    f"Энэ байршил ОБЕГ-ын үерийн эрсдэлтэй бүсийн зурагт "
                    f"орж байна. Хур борооны улиралд ({zone.get('season', '7–8 сар')}) "
                    f"үерт автах магадлалтай."
                ),
                source="ОБЕГ GIS дата",
                last_updated=zone.get("updated_at"),
            ))

        if gis_risks.get("landslide_zone"):
            zone = gis_risks["landslide_zone"]
            factors.append(RiskFactor(
                type="landslide",
                level=RiskLevel.HIGH,
                score=75,
                title_mn="⛰️ Хөрсний нуралтын бүс",
                description_mn=(
                    "Байршил нь хөрсний нуралт, гулгалтын эрсдэлтэй "
                    f"бүсэд ({zone.get('area_name', 'тодорхойгүй')}) оршиж байна. "
                    "Хавар, зун инженер-геологийн үнэлгээ авахыг зөвлөж байна."
                ),
                source="ОБЕГ / Геологийн газар",
                last_updated=zone.get("updated_at"),
            ))

        if gis_risks.get("earthquake_fault"):
            factors.append(RiskFactor(
                type="earthquake",
                level=RiskLevel.MEDIUM,
                score=45,
                title_mn="🏔️ Газар хөдлөлтийн хагарлын ойролцоо",
                description_mn=(
                    "Байршил нь идэвхтэй тектоникийн хагарлын ойролцоо байна. "
                    "Барилгын газар хөдлөлтийн тэсвэрлэх чадварыг шалгаарай."
                ),
                source="Геологи, геофизикийн хүрээлэн",
                last_updated=gis_risks["earthquake_fault"].get("updated_at"),
            ))

        # Нийт оноо тооцох
        overall_score = self._calculate_overall_score(factors)
        overall_level = self._score_to_level(overall_score)
        summary = self._generate_summary(factors, overall_level)

        # Дата хуучирсан эсэх шалгах
        data_freshness_warning = any(
            f.last_updated is None for f in factors
        )

        from datetime import datetime
        return RiskAssessment(
            property_id=str(id(lat)),
            overall_score=overall_score,
            overall_level=overall_level,
            factors=factors,
            summary_mn=summary,
            data_freshness_warning=data_freshness_warning,
            assessed_at=datetime.utcnow().isoformat(),
        )

    def _calculate_overall_score(self, factors: list[RiskFactor]) -> int:
        if not factors:
            return 0
        # Хамгийн өндөр оноотой хүчин зүйлд давуу жин өгнө
        scores = sorted([f.score for f in factors], reverse=True)
        if len(scores) == 1:
            return scores[0]
        # Хамгийн өндөр оноо + бусдын дундаж / 2
        weighted = scores[0] * 0.6 + sum(scores[1:]) / len(scores[1:]) * 0.4
        return min(100, int(weighted))

    def _score_to_level(self, score: int) -> RiskLevel:
        if score >= 80:
            return RiskLevel.CRITICAL
        elif score >= 60:
            return RiskLevel.HIGH
        elif score >= 35:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def _generate_summary(self, factors: list[RiskFactor], level: RiskLevel) -> str:
        if not factors:
            return (
                "Бидний мэдээллийн санд энэ байрны эрсдэлийн тэмдэглэл "
                "олдсонгүй. Гэхдээ заавал мэргэжлийн үнэлгээ авахыг зөвлөж байна."
            )
        critical = [f for f in factors if f.level == RiskLevel.CRITICAL]
        if critical:
            return (
                f"АНХААРУУЛГА: {len(critical)} чухал эрсдэлийн хүчин зүйл илэрлээ. "
                f"Энэ байрыг худалдан авахаасаа өмнө хуулийн зөвлөх болон "
                f"мэргэжлийн инженерээр үнэлгээ хийлгэхийг зөвлөж байна."
            )
        return (
            f"Нийт {len(factors)} эрсдэлийн хүчин зүйл илэрлээ. "
            f"Бидний мэдээллээр одоогоор {level.value} түвшний эрсдэлтэй байна. "
            f"Эцсийн шийдвэр гаргахаасаа өмнө мэргэжлийн үнэлгээ авахыг зөвлөж байна."
        )

    async def _check_permit(self, permit_id: str) -> dict:
        """
        НХБХГ-ын мэдээллийн сангаас барилгын зөвшөөрлийн статус шалгана.
        """
        try:
            result = await self.db.execute(
                "SELECT status, updated_at FROM building_permits WHERE permit_id = $1",
                permit_id
            )
            row = result.fetchone()
            if not row:
                return {"status": "not_found"}
            return {"status": row["status"], "updated_at": str(row["updated_at"])}
        except Exception as e:
            logger.error(f"Зөвшөөрөл шалгахад алдаа: {e}")
            return {"status": "unknown"}

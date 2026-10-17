"""
Гэрээ үүсгэгч.
Монгол Улсын Иргэний хуулийн 318-р зүйлд нийцсэн
орон сууцны түрээсийн гэрээний PDF үүсгэнэ.
"""

import io
import logging
from datetime import datetime, date
from dataclasses import dataclass
from typing import Optional
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

logger = logging.getLogger(__name__)


@dataclass
class ContractParty:
    full_name: str
    register_id: str       # РД
    phone: str
    email: Optional[str]
    address: str


@dataclass
class LeaseContractData:
    owner: ContractParty
    tenant: ContractParty
    property_address: str
    property_area_sqm: float
    monthly_rent: int             # Сарын түрээс ₮
    deposit: int                  # Барьцаа мөнгө ₮
    start_date: date
    end_date: date
    payment_day: int = 1          # Сарын хэдэнд төлөх
    notice_days: int = 30         # Урьдчилан мэдэгдэх хоног
    contract_id: Optional[str] = None


class ContractGenerator:
    def __init__(self):
        self._register_fonts()

    def _register_fonts(self):
        """
        Монгол үсгийн фонт бүртгэх.
        Серверт /fonts/ хавтсанд байршуулсан байх боломжтой.
        Хэрэв тэнд фонт байхгүй бол системийн DejaVu Sans фонт руу буух болно.
        """
        font_paths = [
            "/fonts/NotoSansMongolian.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf",
        ]

        for path in font_paths:
            try:
                pdfmetrics.registerFont(TTFont("MongolFont", path))
                logger.info("Registered MongolFont using %s", path)
                return
            except Exception as exc:
                logger.warning("Фонт бүртгэхэд алдаа: %s", exc)

        logger.warning(
            "Монгол фонт олдсонгүй, Кирилл дэмждэг фонт шаардлагатай. PDF дээрх текст дөрвөлжин хэвээр байх болно."
        )

    def generate(self, data: LeaseContractData) -> bytes:
        """
        Гэрээний PDF үүсгэж bytes буцаана.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        styles = self._build_styles()
        story = []

        # Гарчиг
        story.append(Paragraph("ОРОН СУУЦНЫ ТҮРЭЭСИЙН ГЭРЭЭ", styles["title"]))
        story.append(Spacer(1, 0.3 * cm))

        if data.contract_id:
            story.append(Paragraph(f"Дугаар: {data.contract_id}", styles["subtitle"]))

        story.append(Paragraph(
            f"Улаанбаатар хот, {data.start_date.strftime('%Y оны %m дугаар сарын %d-ний өдөр')}",
            styles["subtitle"],
        ))
        story.append(Spacer(1, 0.5 * cm))

        # Талуудын мэдээлэл
        story.append(Paragraph("НЭГ. ТАЛУУДЫН МЭДЭЭЛЭЛ", styles["section"]))
        story.extend(self._build_parties_section(data, styles))
        story.append(Spacer(1, 0.3 * cm))

        # Байрны мэдээлэл
        story.append(Paragraph("ХОЁР. БАЙРНЫ МЭДЭЭЛЭЛ", styles["section"]))
        story.append(Paragraph(
            f"2.1. Түрээслүүлэх орон сууц: <b>{data.property_address}</b>",
            styles["body"],
        ))
        story.append(Paragraph(
            f"2.2. Нийт талбай: <b>{data.property_area_sqm} м²</b>",
            styles["body"],
        ))
        story.append(Spacer(1, 0.3 * cm))

        # Санхүүгийн нөхцөл
        story.append(Paragraph("ГУРАВ. САНХҮҮГИЙН НӨХЦӨЛ", styles["section"]))
        story.extend(self._build_financial_section(data, styles))
        story.append(Spacer(1, 0.3 * cm))

        # Хугацаа
        story.append(Paragraph("ДӨРӨВ. ГЭРЭЭНИЙ ХУГАЦАА", styles["section"]))
        story.append(Paragraph(
            f"4.1. Гэрээ {data.start_date.strftime('%Y.%m.%d')}-ээс "
            f"{data.end_date.strftime('%Y.%m.%d')} хүртэл хүчинтэй.",
            styles["body"],
        ))
        story.append(Spacer(1, 0.3 * cm))

        # Эрт гарах нөхцөл — хуулийн заалт
        story.append(Paragraph("ТАВ. ЭРТ ГАРАХ НӨХЦӨЛ", styles["section"]))
        story.extend(self._build_early_termination_section(data, styles))
        story.append(Spacer(1, 0.3 * cm))

        # Барьцаа мөнгө
        story.append(Paragraph("ЗУРГАА. БАРЬЦАА МӨНГӨ", styles["section"]))
        story.extend(self._build_deposit_section(data, styles))
        story.append(Spacer(1, 0.3 * cm))

        # Хуулийн анхааруулга
        story.extend(self._build_legal_notice(styles))
        story.append(Spacer(1, 0.5 * cm))

        # Гарын үсэг
        story.extend(self._build_signature_section(data, styles))

        doc.build(story)
        return buffer.getvalue()

    def _build_parties_section(self, data: LeaseContractData, styles) -> list:
        items = []
        items.append(Paragraph("Түрээслүүлэгч (Байрны эзэн):", styles["label"]))
        items.extend(self._party_lines(data.owner, styles))
        items.append(Spacer(1, 0.2 * cm))
        items.append(Paragraph("Түрээслэгч:", styles["label"]))
        items.extend(self._party_lines(data.tenant, styles))
        return items

    def _party_lines(self, party: ContractParty, styles) -> list:
        return [
            Paragraph(f"Овог нэр: <b>{party.full_name}</b>", styles["body"]),
            Paragraph(f"РД: {party.register_id}", styles["body"]),
            Paragraph(f"Утас: {party.phone}", styles["body"]),
            Paragraph(f"Хаяг: {party.address}", styles["body"]),
        ]

    def _build_financial_section(self, data: LeaseContractData, styles) -> list:
        return [
            Paragraph(
                f"3.1. Сарын түрээсийн төлбөр: <b>{data.monthly_rent:,} ₮</b> "
                f"(сарын {data.payment_day}-нд төлнө).",
                styles["body"],
            ),
            Paragraph(
                f"3.2. Барьцаа мөнгө: <b>{data.deposit:,} ₮</b>. "
                "Гэрээ дуусмагц 7 хоногийн дотор бүрэн буцаана.",
                styles["body"],
            ),
            Paragraph(
                "3.3. Нийтийн үйлчилгээ (цахилгаан, ус, халаалт)-ний төлбөрийг "
                "түрээслэгч тус тусад нь хариуцна.",
                styles["body"],
            ),
        ]

    def _build_early_termination_section(self, data: LeaseContractData, styles) -> list:
        """
        Иргэний хуулийн 204-р зүйлд тулгуурлан эрт гарах нөхцөл.
        """
        return [
            Paragraph(
                f"5.1. Түрээслэгч хугацаанаас өмнө гарах бол системийн мэдэгдлийн "
                f"функцээр {data.notice_days}-аас доошгүй хоногийн өмнө бичгээр мэдэгдэх үүрэгтэй. "
                "(Иргэний хуулийн 204.1)",
                styles["body"],
            ),
            Paragraph(
                f"5.2. Мэдэгдэлгүй гарсан тохиолдолд 1 сарын түрээсийн "
                f"({data.monthly_rent:,} ₮) нөхөн төлбөр төлнө.",
                styles["body"],
            ),
            Paragraph(
                "5.3. Байрны эзний буруутай үйлдлээс (засвар хийгдэхгүй, ус/цахилгаан/халаалт "
                "тасарсан) болж гарсан тохиолдолд 5.2-т заасан нөхөн төлбөр хамаарахгүй.",
                styles["body"],
            ),
            Paragraph(
                f"5.4. Байрны эзэн хугацаанаас өмнө гарахыг шаардвал "
                f"{data.notice_days}-аас доошгүй хоногийн өмнө мэдэгдэж, "
                "барьцаа мөнгийг 7 хоногийн дотор бүрэн буцаана.",
                styles["body"],
            ),
        ]

    def _build_deposit_section(self, data: LeaseContractData, styles) -> list:
        return [
            Paragraph(
                f"6.1. Байрны эзэн гэрээ байгуулахдаа {data.deposit:,} ₮ барьцаа мөнгө авна.",
                styles["body"],
            ),
            Paragraph(
                "6.2. Барьцаа мөнгийг дараах тохиолдолд суутгаж болно: "
                "байранд гэмтэл учруулсан (элэгдэл бус), "
                "мэдэгдэлгүй гарсан, төлбөр хоцорсон.",
                styles["body"],
            ),
            Paragraph(
                "6.3. Суутгалыг баримтаар нотолж, дүнг тодорхойлно. "
                "Нотолгоогүйгээр суутгахыг хориглоно.",
                styles["body"],
            ),
        ]

    def _build_legal_notice(self, styles) -> list:
        notice_style = ParagraphStyle(
            "notice",
            parent=styles["body"],
            backColor=colors.HexColor("#FFF9C4"),
            borderPadding=8,
            borderWidth=1,
            borderColor=colors.HexColor("#F9A825"),
        )
        return [
            Paragraph(
                "⚠️ ЧУХАЛ: Монгол Улсын Иргэний хуулийн 318.4-т зааснаар энэхүү гэрээг "
                "Үл хөдлөх хөрөнгийн улсын бүртгэлд бүртгүүлэхгүй бол хүчин төгөлдөр бус "
                "гэж үзнэ. Гарын үсэг зурсны дараа заавал Нийслэлийн УБЕГ-т бүртгүүлнэ үү.",
                styles["body"],
            ),
        ]

    def _build_signature_section(self, data: LeaseContractData, styles) -> list:
        items = [Paragraph("ГАРЫН ҮСЭ ЗУРАХ ХЭСЭГ", styles["section"])]
        table_data = [
            ["ТҮРЭЭСЛҮҮЛЭГЧ", "ТҮРЭЭСЛЭГЧ"],
            [
                f"{data.owner.full_name}\nРД: {data.owner.register_id}\n\n\nГарын үсэг: ____________",
                f"{data.tenant.full_name}\nРД: {data.tenant.register_id}\n\n\nГарын үсэг: ____________",
            ],
            [f"Огноо: {datetime.now().strftime('%Y.%m.%d')}", f"Огноо: {datetime.now().strftime('%Y.%m.%d')}"],
        ]
        table = Table(table_data, colWidths=[8.5 * cm, 8.5 * cm])
        table.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F5F5F5")),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        items.append(table)
        return items

    def _build_styles(self) -> dict:
        base = getSampleStyleSheet()
        return {
            "title": ParagraphStyle(
                "title", parent=base["Heading1"],
                fontName="MongolFont",
                alignment=TA_CENTER, fontSize=14, spaceAfter=6,
            ),
            "subtitle": ParagraphStyle(
                "subtitle", parent=base["Normal"],
                fontName="MongolFont",
                alignment=TA_CENTER, fontSize=10, textColor=colors.grey,
            ),
            "section": ParagraphStyle(
                "section", parent=base["Heading2"],
                fontName="MongolFont",
                fontSize=11, spaceBefore=10, spaceAfter=4,
                textColor=colors.HexColor("#1A237E"),
            ),
            "label": ParagraphStyle(
                "label", parent=base["Normal"],
                fontName="MongolFont",
                fontSize=10,
            ),
            "body": ParagraphStyle(
                "body", parent=base["Normal"],
                fontName="MongolFont",
                fontSize=10, alignment=TA_JUSTIFY,
                spaceAfter=4, leading=14,
            ),
        }

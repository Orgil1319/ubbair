import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/lease")
async def lease_info():
    """Түрээслэхтэй холбоотой үндсэн мэдээлэл буцаана."""
    return {
        "rights": [
            "Түрээслэгчид гэрээний нөхцөлийг тодорхой бичгээр баталгаажуулах",
            "Барьцаа мөнгө буцаалт, буулгах хугацааг шалгах",
        ]
    }

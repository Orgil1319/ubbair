"""
Монгол Улсын Иргэний хуулийн холбогдох заалтуудыг
ChromaDB vector database-д index хийнэ.
Нэг удаа ажиллуулж дараа нь RAGService ашиглана.
"""

import chromadb
from chromadb.utils import embedding_functions
import logging

logger = logging.getLogger(__name__)

# Системд хамааралтай Иргэний хуулийн заалтууд
# legalinfo.mn-ээс татсан
LEGAL_DOCUMENTS = [
    {
        "id": "civil_318_1",
        "content": (
            "Иргэний хуулийн 318.1: Орон сууц болон бусад үл хөдлөх хөрөнгийг "
            "түрээслэх гэрээг бичгээр байгуулна."
        ),
        "metadata": {
            "article": "318.1",
            "chapter": "Орон сууц түрээслэх",
            "category": "lease",
            "law": "Иргэний хууль",
        },
    },
    {
        "id": "civil_318_4",
        "content": (
            "Иргэний хуулийн 318.4: Орон сууц болон бусад үл хөдлөх хөрөнгийг "
            "түрээслэх гэрээг үл хөдлөх хөрөнгийн улсын бүртгэлд бүртгүүлнэ. "
            "Бүртгэлгүй гэрээ нь хүчин төгөлдөр бус байна."
        ),
        "metadata": {
            "article": "318.4",
            "chapter": "Орон сууц түрээслэх",
            "category": "lease",
            "law": "Иргэний хууль",
        },
    },
    {
        "id": "civil_204_1",
        "content": (
            "Иргэний хуулийн 204.1: Аль нэг тал нь гэрээнээс татгалзах, "
            "гэрээг цуцлах бол нөгөө талдаа урьдчилан мэдэгдэх үүрэгтэй. "
            "Мэдэгдэхэд хуулиар хэлбэрийн шаардлага тавиагүй тул "
            "мэдэгдсэн байдлыг нотолгооны хүрээнд дүгнэлт өгнө."
        ),
        "metadata": {
            "article": "204.1",
            "chapter": "Гэрээ цуцлах",
            "category": "eviction",
            "law": "Иргэний хууль",
        },
    },
    {
        "id": "civil_318_tenant_rights",
        "content": (
            "Түрээслэгч нь гэрээний хугацаанд орон сууцыг эзэмшиж, "
            "ашиглах эрхтэй. Түрээслүүлэгч нь түрээслэгчийн зөвшөөрөлгүйгээр "
            "орон сууцад орох эрхгүй. Засвар үйлчилгээний шаардлага гарсан "
            "тохиолдолд урьдчилан мэдэгдэж, тохирсон цагт орно."
        ),
        "metadata": {
            "article": "318 холбогдох",
            "chapter": "Түрээслэгчийн эрх",
            "category": "tenant_rights",
            "law": "Иргэний хууль",
        },
    },
    {
        "id": "civil_318_deposit",
        "content": (
            "Барьцаа мөнгийг гэрээ дуусгавар болсны дараа ажлын 7-14 хоногийн "
            "дотор буцаана. Орон сууцад гэмтэл учруулсан бол баримтаар нотолж "
            "суутгаж болно. Хэвийн элэгдэл хорогдлыг суутгалд тооцохгүй."
        ),
        "metadata": {
            "article": "318 холбогдох",
            "chapter": "Барьцаа мөнгө",
            "category": "deposit",
            "law": "Иргэний хууль",
        },
    },
    {
        "id": "civil_60_notary",
        "content": (
            "Иргэний хуулийн 60: Хэлцлийг нотариатаар гэрчлүүлэх. "
            "Үл хөдлөх хөрөнгийн гэрээ болон бусад хуульд заасан тохиолдолд "
            "хэлцлийг нотариатаар гэрчлүүлнэ. Нотариатаар гэрчлүүлээгүй "
            "гэрээ хүчин төгөлдөр бус болно."
        ),
        "metadata": {
            "article": "60",
            "chapter": "Хэлцлийн хэлбэр",
            "category": "contract",
            "law": "Иргэний хууль",
        },
    },
    {
        "id": "civil_early_exit",
        "content": (
            "Байрны эзний буруутай үйлдлээс болж (ус, цахилгаан, дулаан "
            "тасарсан, засвар хийгдэхгүй орхисон, хэлцлийн нөхцөл зөрчсөн) "
            "түрээслэгч гэрээг нөхөн төлбөрgүйгээр цуцлах эрхтэй. "
            "Нотолгоо цуглуулах нь маргааныг шийдвэрлэхэд чухал."
        ),
        "metadata": {
            "article": "318 / 204 холбогдох",
            "chapter": "Гэрээ эрт цуцлах",
            "category": "eviction",
            "law": "Иргэний хууль",
        },
    },
]


def index_all():
    """
    Бүх хуулийн баримт бичгийг ChromaDB-д index хийнэ.
    """
    client = chromadb.PersistentClient(path="/data/chromadb")
    embedding_fn = embedding_functions.DefaultEmbeddingFunction()

    try:
        client.delete_collection("mongolian_civil_law")
    except Exception:
        pass

    collection = client.create_collection(
        name="mongolian_civil_law",
        embedding_function=embedding_fn,
    )

    ids = [doc["id"] for doc in LEGAL_DOCUMENTS]
    contents = [doc["content"] for doc in LEGAL_DOCUMENTS]
    metadatas = [doc["metadata"] for doc in LEGAL_DOCUMENTS]

    collection.add(ids=ids, documents=contents, metadatas=metadatas)
    logger.info(f"✓ {len(LEGAL_DOCUMENTS)} хуулийн заалт index хийгдлээ")
    return len(LEGAL_DOCUMENTS)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    count = index_all()
    print(f"Index дууслаа: {count} баримт бичиг")

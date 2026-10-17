"""
RAG (Retrieval-Augmented Generation) үйлчилгээ.
Монгол Улсын Иргэний хуулийн холбогдох заалтуудыг
PostgreSQL (pgvector) вектор баазаас хайж Claude/Groq-д контекст болгон өгнө.
LangChain ашиглан RAG бүтэц рүү хөрвүүлэв.
"""

import logging
import os
from typing import Optional

from langchain_postgres import PGVector
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document

from app.config import settings

logger = logging.getLogger(__name__)

# Хайлтын категори → холбогдох хуулийн сэдвүүд
LEGAL_TOPICS = {
    "lease":        ["түрээс", "түрээслэгч", "түрээслүүлэгч", "318", "гэрээ"],
    "permit":       ["барилгын зөвшөөрөл", "ашиглалтад", "хяналт"],
    "eviction":     ["гарах", "цуцлах", "204", "мэдэгдэл"],
    "deposit":      ["барьцаа", "буцаах"],
    "flood":        ["байгалийн гамшиг", "эрсдэл", "хариуцлага"],
    "contract":     ["гэрээ", "бичгээр", "бүртгэл", "318.4"],
}


class RAGService:
    def __init__(self, collection_name: str = "mongolian_civil_law"):
        self.collection_name = collection_name
        
        # OpenAI Embeddings
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY олдсонгүй, embedding хийх үед алдаа гарч болзошгүй.")
            
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        
        # PostgreSQL холболтын стринг (asyncpg -> psycopg)
        self.connection_string = settings.DATABASE_URL.replace("+asyncpg", "+psycopg")
        
        try:
            self.vector_store = PGVector(
                embeddings=self.embeddings,
                collection_name=self.collection_name,
                connection=self.connection_string,
                use_jsonb=True,
            )
            logger.info(f"PGVector collection '{collection_name}' холбогдлоо")
        except Exception as e:
            logger.error(f"PGVector холболт үүсгэхэд алдаа: {e}")
            self.vector_store = None

    async def retrieve(
        self,
        query: str,
        top_k: int = 3,
        category: Optional[str] = None,
    ) -> list[dict]:
        """
        Хуулийн баримт бичгээс холбогдох хэсгийг хайна (LangChain Retriever).
        """
        try:
            if not self.vector_store:
                return self._fallback_legal_context(query)
                
            # Категорийн фильтр
            filter_dict = {"category": category} if category else None
            
            # LangChain as_retriever ашиглан хайлт хийх
            retriever = self.vector_store.as_retriever(
                search_kwargs={"k": top_k, "filter": filter_dict}
            )
            
            # Хайлт хийх
            # invoke нь synchronous учир async wrapper эсвэл ainvoke ашиглана
            results = await retriever.ainvoke(query)
            
            docs = []
            for doc in results:
                docs.append({
                    "content": doc.page_content,
                    "article": doc.metadata.get("article", ""),
                    "chapter": doc.metadata.get("chapter", ""),
                    "relevance": 1.0,  # Одоогийн as_retriever зайг буцаадаггүй тул шууд 1.0 гэе
                })

            return docs

        except Exception as e:
            logger.error(f"RAG хайлт алдаа: {e}")
            return self._fallback_legal_context(query)

    def index_document(self, doc_id: str, content: str, metadata: dict):
        """
        Хуулийн баримт бичгийн хэсгийг index-д нэмнэ.
        """
        try:
            if not self.vector_store:
                logger.error("PGVector вектор бааз холбогдоогүй байна.")
                return
                
            doc = Document(
                page_content=content,
                metadata=metadata,
                id=doc_id
            )
            self.vector_store.add_documents([doc])
            logger.info(f"Баримт амжилттай нэмэгдлээ: {doc_id}")
        except Exception as e:
            logger.error(f"RAG index нэмэхэд алдаа: {e}")

    def _fallback_legal_context(self, query: str) -> list[dict]:
        """
        Бааз ажиллахгүй үед хатуу кодлосон үндсэн заалтуудыг буцаана.
        """
        fallbacks = [
            {
                "content": (
                    "Иргэний хуулийн 318.4: Түрээсийн гэрээг бичгээр байгуулж, "
                    "үл хөдлөх хөрөнгийн улсын бүртгэлд бүртгүүлээгүй бол "
                    "хүчин төгөлдөр бус гэж үзнэ."
                ),
                "article": "318.4",
                "chapter": "Орон сууц түрээслэх",
                "relevance": 0.9,
            },
            {
                "content": (
                    "Иргэний хуулийн 204.1: Аль нэг тал гэрээнээс татгалзах буюу "
                    "гэрээг цуцлах бол нөгөө талдаа урьдчилан мэдэгдэх үүрэгтэй."
                ),
                "article": "204.1",
                "chapter": "Гэрээ цуцлах",
                "relevance": 0.85,
            },
        ]

        query_lower = query.lower()
        if "барьцаа" in query_lower or "deposit" in query_lower:
            fallbacks.append({
                "content": (
                    "Барьцаа мөнгийг гэрээ дуусмагц хохирол байхгүй бол "
                    "бүрэн буцааж өгөх үүрэгтэй. Суутгал хийхэд нотолгоо шаардлагатай."
                ),
                "article": "318 холбогдох",
                "chapter": "Барьцаа мөнгө",
                "relevance": 0.8,
            })

        return fallbacks

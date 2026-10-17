"""
Claude/Groq API wrapper LangChain ашиглан ReAct Agent болгон шинэчлэв.
Байрны эрсдэлийн тайланг хүнд ойлгомжтой монгол хэлээр тайлбарлана.
RAG: Монгол Улсын Иргэний хуулийн зохих заалтуудыг vector DB-ээс татаж
    AI-д контекст болгон өгнө.
"""

import json
import logging
from typing import Optional, List, Dict, Any

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor
from langchain.agents.format_scratchpad.tools import format_to_tool_messages
from langchain.agents.output_parsers.tools import ToolsAgentOutputParser
from langchain_core.agents import AgentActionMessageLog, AgentFinish
from langchain_core.tools import tool
from langchain.memory import ConversationBufferMemory
from langchain_core.runnables import RunnablePassthrough
import asyncpg
import uuid
import re

from app.config import settings
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)

# System Prompting + Role-based
SYSTEM_PROMPT = """Чи бол Үл хөдлөх хөрөнгийн салбарт 10 жил ажилласан, мэргэжлийн, найрсаг Монгол зөвлөх Агент байна.
Хэрэглэгчийн асуултад маш тодорхой, соёлтой, цэвэр Монгол хэлний найруулгаар хариул.
Мэдээлэл байхгүй бол өөрөөсөө бүү зохио. Интернэтээс (Wikipedia гэх мэт) мэдээлэл хайх шаардлагагүй, зөвхөн өөрийн Tools-ийг ашигла.

Таны үүрэг:
- Иргэдэд байрны эрсдэлийг энгийн, ойлгомжтой монгол хэлээр тайлбарлах.
- Компанийн найдвартай байдлыг асуувал `check_company_status` tool-ийг ашиглаж заавал шалгах. (Хэрэглэгч нэр буруу бичсэн ч tool дотор fuzzy хайлт ажиллана).
- Мэргэжлийн нэр томьёог тайлбарлах, айлгахгүй байх.
- Аливаа мэдээллийн эх сурвалжийг дурдах.
- Хариултын төгсгөлд "Санамж: Энэхүү систем нь зөвхөн зөвлөх зорилготой бөгөөд хуулийн баталгаа болохгүй." гэсэн анхааруулгыг заавал оруулна.
"""

@tool
async def search_properties_db(district: str = "", max_price: int = 0) -> str:
    """Баазаас үл хөдлөх хөрөнгө, байрны мэдээлэл хайх. district нь дүүргийн нэр, max_price нь төгрөгөөр хамгийн их үнэ."""
    try:
        db_url = settings.DATABASE_URL.replace("+asyncpg", "")
        conn = await asyncpg.connect(db_url)

        try:
            sql = "SELECT title, address, district, price, area, rooms FROM properties WHERE 1=1"
            args = []
            if district and district.lower() != "бүгд":
                sql += f" AND district ILIKE ${len(args)+1}"
                args.append(f"%{district}%")
            if max_price and max_price > 0:
                sql += f" AND price <= ${len(args)+1}"
                args.append(max_price)
            sql += " LIMIT 5"

            rows = await conn.fetch(sql, *args)
        except asyncpg.exceptions.UndefinedTableError:
            rows = []
        finally:
            await conn.close()

        if not rows:
            return "Баазад тохирох байр олдсонгүй."

        res = "Олдсон байрууд (Баазаас):\n"
        for r in rows:
            res += f"- {r['title']} | {r['district']} | Үнэ: {r['price']:,.0f} ₮ | Талбай: {r['area']} м²\n"
        return res

    except Exception as e:
        logger.error(f"DB Error in AI: {e}")
        return "Мэдээллийн сантай холбогдож чадсангүй."

@tool
async def search_legal_documents(query: str) -> str:
    """Монгол улсын иргэний хуулийн баримт бичиг болон түрээсийн гэрээтэй холбоотой заалтуудаас хайх."""
    rag = RAGService()
    docs = await rag.retrieve(query=query, top_k=3)
    if not docs:
        return "Холбогдох хуулийн заалт олдсонгүй."

    return "\n\n".join([f"Хуулийн заалт ({d['article']}): {d['content']}" for d in docs])

class DummyRedis:
    async def get(self, key): return None
    async def setex(self, key, time, val): pass

@tool
async def check_company_status(company_name: str) -> str:
    """Компанийн нэрээр хайж, тусгай зөвшөөрлийн хугацаа болон хар жагсаалтад орсон эсэхийг шалгах."""
    from app.services.blacklist_checker import BlacklistChecker
    db_url = settings.DATABASE_URL.replace("+asyncpg", "")
    try:
        conn = await asyncpg.connect(db_url)
        class DummyPool:
            def acquire(self):
                class DummyAcquire:
                    async def __aenter__(self): return conn
                    async def __aexit__(self, exc_type, exc, tb): pass
                return DummyAcquire()
                
        checker = BlacklistChecker(DummyPool(), DummyRedis())
        res = await checker.check(company_name)
        await conn.close()
        
        if res.get("found"):
            info = f"'{company_name}' хайлтад олдсон илэрцүүд:\n"
            info += f"Ерөнхий төлөв: {res.get('license_status')}\n"
            info += f"Хар жагсаалтад: {'ТИЙМ' if res.get('blacklisted') else 'ҮГҮЙ'}\n"
            if res.get('matches'):
                info += "Дэлгэрэнгүй:\n"
                for m in res['matches']:
                    info += f"- Нэр: {m['company_name']} | Хугацаа: {m['expiry_date']} | Эх сурвалж: {m['source']} | Тохирох магадлал: {m['match_score']}\n"
            return info
        else:
            return f"'{company_name}' компани тусгай зөвшөөрлийн санд болон хар жагсаалтад олдсонгүй."
    except Exception as e:
        logger.error(f"Error checking company: {e}")
        return "Системийн алдаа гарлаа. Шалгаж чадсангүй."


class ClaudeService:
    def __init__(self):
        self.provider = (settings.LLM_PROVIDER or "groq").lower()
        self.rag = RAGService()

        # Initialize LangChain LLM
        if self.provider == "groq":
            self.llm = ChatGroq(
                api_key=settings.GROQ_API_KEY,
                model_name=settings.GROQ_MODEL or "llama-3.3-70b-versatile",
                temperature=0.0
            )
        elif self.provider == "openai":
            self.llm = ChatOpenAI(
                model="gpt-4o",
                temperature=0.0
            )
        else:
            # Fallback to Groq
            self.llm = ChatGroq(
                api_key=settings.GROQ_API_KEY,
                model_name=settings.GROQ_MODEL or "llama-3.3-70b-versatile",
                temperature=0.0
            )

        # Initialize Agent Tools
        self.tools = [search_properties_db, search_legal_documents, check_company_status]

        # Agent Prompt with memory
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        # Memory
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )

        # Custom Output Parser to intercept Groq's raw XML tool calls (<function=...>)
        class GroqLlamaOutputParser(ToolsAgentOutputParser):
            def parse_result(self, result: list, *, partial: bool = False):
                # IMPORTANT FIX:
                # result[0] is a ChatGeneration (or similar Generation) object,
                # NOT an AIMessage directly. The actual AIMessage lives on
                # `generation.message`. The original code checked
                # `isinstance(result[0], AIMessage)` which was always False,
                # so this custom XML-tool-call interception never ran and
                # raw "<function=...>" text leaked straight to the user.
                generation = result[0]
                message = getattr(generation, "message", generation)

                if not isinstance(message, AIMessage):
                    return super().parse_result(result, partial=partial)

                # 1. Native tool calls (model used proper function-calling format)
                if message.tool_calls:
                    return super().parse_result(result, partial=partial)

                # 2. Check for raw XML tag <function=...> in content
                #    (Groq/Llama models sometimes emit this instead of a
                #    native tool_call when tool-calling isn't perfectly
                #    triggered)
                if isinstance(message.content, str):
                    match = re.search(r"<function=([^>]+)>(.*?)</function>", message.content, re.DOTALL)
                    if match:
                        tool_name = match.group(1).strip()
                        try:
                            tool_input = json.loads(match.group(2))
                        except Exception:
                            tool_input = {"query": match.group(2)}  # Fallback

                        tool_call_id = str(uuid.uuid4())

                        # Fix the message to look like a native tool call
                        message.tool_calls = [{
                            "name": tool_name,
                            "args": tool_input,
                            "id": tool_call_id
                        }]

                        return [AgentActionMessageLog(
                            tool=tool_name,
                            tool_input=tool_input,
                            log=message.content,
                            message_log=[message],
                            tool_call_id=tool_call_id
                        )]

                # 3. Otherwise, return as Finish
                return AgentFinish(return_values={"output": message.content}, log=str(message.content))

        # Create Agent explicitly with our parser
        llm_with_tools = self.llm.bind_tools(self.tools)

        self.agent = (
            RunnablePassthrough.assign(
                agent_scratchpad=lambda x: format_to_tool_messages(x["intermediate_steps"])
            )
            | self.prompt
            | llm_with_tools
            | GroqLlamaOutputParser()
        )

        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True
        )

    async def _generate_text(self, system_prompt: str, user_prompt: str) -> str:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        response = await self.llm.ainvoke(messages)
        return response.content

    async def explain_risk(
        self,
        risk_assessment: dict,
        property_info: dict,
        user_question: Optional[str] = None,
    ) -> str:
        """Эрсдэлийн үнэлгээг хүнд ойлгомжтой монгол тайлбар болгоно (Zero-shot / Context)."""
        legal_context = ""
        if risk_assessment.get("factors"):
            factor_types = [f["type"] for f in risk_assessment["factors"]]
            legal_docs = await self.rag.retrieve(
                query=f"эрсдэл {' '.join(factor_types)} барилгын хууль",
                top_k=3,
            )
            if legal_docs:
                legal_context = "\n\nХолбогдох хуулийн заалтууд:\n" + "\n".join(
                    [f"- {doc['content'][:200]}..." for doc in legal_docs]
                )

        prompt = f"""Дараах байрны эрсдэлийн үнэлгээг иргэдэд ойлгомжтойгоор тайлбарла.

Байрны мэдээлэл:
{json.dumps(property_info, ensure_ascii=False, indent=2)}

Эрсдэлийн үнэлгээ:
{json.dumps(risk_assessment, ensure_ascii=False, indent=2)}
{legal_context}

{f'Хэрэглэгчийн асуулт: {user_question}' if user_question else 'Ерөнхий тайлбар өг.'}

Хариулт дараах бүтэцтэй байх:
1. Нийт дүгнэлт (1-2 өгүүлбэр)
2. Тус бүр эрсдэлийн тайлбар
3. Санал болгох дараагийн алхмууд"""

        return await self._generate_text(SYSTEM_PROMPT, prompt)

    async def explain_legal_rights(self, situation: str) -> str:
        """Түрээслэгчийн эрх, хуулийн мэдээлэл тайлбарлана (Few-shot/RAG)."""
        legal_docs = await self.rag.retrieve(
            query=f"түрээслэгчийн эрх {situation} иргэний хууль",
            top_k=5,
        )
        legal_context = "\n".join([doc["content"] for doc in legal_docs])

        prompt = f"""Та үл хөдлөх хөрөнгийн хуулийн зөвлөх байна. Дараах нөхцөл байдалд түрээслэгчийн эрхийг тайлбарла.

Жишээ: "Байрны эзэн урьдчилж хэлэлгүйгээр гэрээ цуцална гэсэн."
Хариулт нь хуулийн дагуу (ИХ-ийн 204.1) урьдчилан мэдэгдэх үүрэгтэйг дурдаж, эрхийг хамгаалсан байх ёстой.

Одоогийн Нөхцөл байдал: {situation}

Монгол Улсын Иргэний хуулийн холбогдох заалтууд:
{legal_context}

Хариулт дараах бүтэцтэй байх:
1. Таны эрх (хуулийн заалтад тулгуурлан)
2. Байрны эзний үүрэг
3. Та яах ёстой вэ — алхам алхмаар
4. Шаардлагатай бол хаана хандах вэ"""

        return await self._generate_text(SYSTEM_PROMPT, prompt)

    async def analyze_price_fairness(
        self,
        property_price: float,
        area_sqm: float,
        district: str,
        market_data: dict,
    ) -> str:
        """Байрны үнэ хөөсөрсөн эсэхийг тайлбарлана (Chain-of-Thought)."""
        price_per_sqm = property_price / area_sqm if area_sqm else 0
        avg_price = market_data.get("avg_price_per_sqm", 0)
        diff_pct = ((price_per_sqm - avg_price) / avg_price * 100) if avg_price else 0

        prompt = f"""Үл хөдлөх хөрөнгийн үнийг зах зээлтэй харьцуулан үнэлгээ хийх шаардлагатай байна.
Алхам алхмаар бодож (Chain of Thought), үнийн зөрүүний шалтгааныг логиктойгоор тайлбарла.

Байрны мэдээлэл:
- Байршил: {district} дүүрэг
- Нийт талбай: {area_sqm} м²
- Нийт үнэ: {property_price:,.0f} ₮
- м² үнэ: {price_per_sqm:,.0f} ₮

Зах зээлийн мэдээлэл ({district} дүүрэг):
- Дундаж м² үнэ: {avg_price:,.0f} ₮
- Хамгийн бага: {market_data.get('min_price', 0):,.0f} ₮
- Хамгийн өндөр: {market_data.get('max_price', 0):,.0f} ₮
- Зах зээлийн дунджаас: {diff_pct:+.1f}%
- Мэдээлэл: {market_data.get('sample_count', 0)} байрны дундаж

Алхам 1: Үнийн зөрүү хэр зэрэг бодит байна вэ?
Алхам 2: Зах зээлийн дундажтай харьцуулахад хэт үнэтэй эсвэл хямд байна уу?
Алхам 3: Хэрэглэгчид ямар дүгнэлт өгөх вэ?

Эцсийн хариулт богино, тодорхой бөгөөд зөвхөн дүгнэлтээс бүрдэнэ."""

        return await self._generate_text(SYSTEM_PROMPT, prompt)

    async def chat(
        self, messages: list[dict], property_context: Optional[dict] = None
    ) -> str:
        """Хэрэглэгчтэй чат хэлбэрээр харилцана. ReAct Agent ашигласан."""

        # Системд нэмэлт контекст өгөх шаардлагатай бол prompt-г өөрчилж болно.
        input_text = messages[-1]["content"] if messages else ""

        # Update memory context with user history
        # (For stateful chat API we should ideally use ConversationBufferMemory
        # but since messages are passed entirely, we'll sync it)
        self.memory.clear()
        for msg in messages[:-1]:
            if msg["role"] == "user":
                self.memory.chat_memory.add_user_message(msg["content"])
            else:
                self.memory.chat_memory.add_ai_message(msg["content"])

        context_str = ""
        if property_context:
            context_str = f"\n[Одоогийн байрны мэдээлэл: {json.dumps(property_context, ensure_ascii=False)}]"
            input_text += context_str

        try:
            # ReAct Agent ажиллуулах
            response = await self.agent_executor.ainvoke(
                {"input": input_text, "chat_history": self.memory.chat_memory.messages}
            )
            return response.get("output", "Уучлаарай, хариулахад алдаа гарлаа.")
        except Exception as e:
            logger.error(f"LangChain Agent алдаа: {e}")
            return "Уучлаарай, алдаа гарлаа. Дахин оролдоно уу."
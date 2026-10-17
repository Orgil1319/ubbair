import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  const { propertyId, messages } = await req.json();

  // Fetch property context from backend
  let propertyContext = "";
  try {
    const res = await fetch(
      `${process.env.API_URL ?? "http://localhost:8000"}/properties/${propertyId}/context`,
    );
    if (res.ok) {
      const ctx = await res.json();
      propertyContext = `
Байрны мэдээлэл:
- Хаяг: ${ctx.address}
- Эрсдэлийн оноо: ${ctx.riskScore}/100
- Барилгын зөвшөөрөл: ${ctx.permitStatus}
- Үерийн эрсдэл: ${ctx.floodRisk}
- Хар жагсаалт: ${ctx.blacklisted ? "Тийм ⚠️" : "Үгүй ✅"}
- Дүүргийн дундаж м² үнэтэй харьцуулалт: ${ctx.priceDiffPercent}%
      `.trim();
    }
  } catch {
    // Fallback if context fetch fails
  }

  const systemPrompt = `Та Монгол Улсын үл хөдлөх хөрөнгийн аюулгүй байдлын зөвлөгч.
Иргэдэд байрны эрсдэл, хуулийн мэдээллийг монгол хэлээр тодорхой, хялбар ойлгомжтойгоор тайлбарлана.

Дүрмүүд:
- Техникийн нэр томьёогоос зайлсхий
- Санхүүгийн баталгаа биш, эрсдэлийн мэдэгдэл өгнө
- Монгол Улсын Иргэний хуулийн холбогдох заалтуудад тулгуурла
- Хариулт богино, тодорхой байна
- "Баталгаа" гэхгүй, "мэдэгдэл", "зөвлөгөө" гэсэн үгс ашигла
- Шаардлагатай бол мэргэжлийн зөвлөгч авахыг санал болго

${propertyContext ? `\n${propertyContext}` : ""}`;

  try {
    const response = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-api-key": process.env.ANTHROPIC_API_KEY ?? "",
        "anthropic-version": "2023-06-01",
      },
      body: JSON.stringify({
        model: "claude-sonnet-4-20250514",
        max_tokens: 600,
        system: systemPrompt,
        messages,
      }),
    });

    const data = await response.json();
    const reply = data.content?.[0]?.text ?? "Алдаа гарлаа.";

    return NextResponse.json({ reply });
  } catch {
    return NextResponse.json({ reply: "Сервертэй холбогдоход алдаа гарлаа." }, { status: 500 });
  }
}

import { NextResponse } from "next/server";

export async function POST(req) {
  try {
    const body = await req.json();
    const { query } = body;

    return NextResponse.json({
      success: true,
      message: "LangChain Agent route working!",
      query,
    });
  } catch (error) {
    return NextResponse.json({ success: false, error: error.message }, { status: 500 });
  }
}

export async function GET() {
  return NextResponse.json({
    status: "ok",
    message: "LangChain Agent API is live 🚀",
  });
}

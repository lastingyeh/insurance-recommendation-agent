import { NextRequest, NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

const getBaseUrl = () =>
  process.env.FASTAPI_BASE_URL ?? 'http://127.0.0.1:8080';

export async function GET() {
  try {
    const baseUrl = getBaseUrl();
    const upstreamUrl = `${baseUrl.replace(/\/$/, '')}/api/agent/sessions`;

    const response = await fetch(upstreamUrl, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      cache: 'no-store',
    });

    if (!response.ok) {
      return NextResponse.json(
        { error: 'FastAPI backend unavailable' },
        { status: 502 },
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json(
      { error: 'FastAPI backend unavailable' },
      { status: 502 },
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as {
      sessionId: string;
      state?: Record<string, string>;
    };

    if (!body.sessionId?.trim()) {
      return NextResponse.json(
        { error: 'sessionId is required' },
        { status: 400 },
      );
    }

    const baseUrl = getBaseUrl();
    const upstreamUrl = `${baseUrl.replace(/\/$/, '')}/api/agent/sessions`;

    const response = await fetch(upstreamUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    const data = await response.json().catch(() => ({}));
    return NextResponse.json(data, {
      status: response.ok ? 200 : response.status,
    });
  } catch {
    return NextResponse.json(
      { error: 'FastAPI backend unavailable' },
      { status: 502 },
    );
  }
}

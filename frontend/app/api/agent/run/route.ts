import { NextRequest, NextResponse } from 'next/server';

export const runtime = 'nodejs';

export const dynamic = 'force-dynamic';

const getBaseUrl = () =>
  process.env.FASTAPI_BASE_URL ?? 'http://127.0.0.1:8080';

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as {
      prompt?: string;
      sessionId?: string;
      userId?: string;
      sessionState?: Record<string, string>;
    };

    if (!body.prompt?.trim() || !body.sessionId?.trim()) {
      return NextResponse.json(
        { error: 'prompt and sessionId are required' },
        { status: 400 },
      );
    }

    const baseUrl = getBaseUrl();
    const upstreamUrl = `${baseUrl.replace(/\/$/, '')}/api/agent/run`;

    const upstreamResponse = await fetch(upstreamUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
      },
      body: JSON.stringify(body),
    });

    if (!upstreamResponse.ok) {
      const text = await upstreamResponse.text();
      return NextResponse.json(
        { error: text || 'FastAPI /api/agent/run failed' },
        { status: upstreamResponse.status },
      );
    }

    if (!upstreamResponse.body) {
      return NextResponse.json(
        { error: 'FastAPI did not return a response body' },
        { status: 502 },
      );
    }

    return new NextResponse(upstreamResponse.body, {
      headers: {
        'Content-Type': 'text/event-stream; charset=utf-8',
        'Cache-Control': 'no-cache, no-transform',
        Connection: 'keep-alive',
      },
    });
  } catch (error) {
    return NextResponse.json(
      {
        error:
          error instanceof Error
            ? error.message
            : 'Unable to reach FastAPI backend',
      },
      { status: 502 },
    );
  }
}

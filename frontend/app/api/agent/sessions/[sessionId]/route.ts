import { NextRequest, NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

const getBaseUrl = () =>
  process.env.FASTAPI_BASE_URL ?? 'http://127.0.0.1:8080';

export async function DELETE(
  _: NextRequest,
  { params }: { params: { sessionId: string } },
) {
  try {
    const { sessionId } = params;

    if (!sessionId?.trim()) {
      return NextResponse.json(
        { error: 'sessionId is required' },
        { status: 400 },
      );
    }

    const baseUrl = getBaseUrl();
    const upstreamUrl = `${baseUrl.replace(/\/$/, '')}/api/agent/sessions/${encodeURIComponent(sessionId)}`;

    const response = await fetch(upstreamUrl, {
      method: 'DELETE',
      headers: { Accept: 'application/json' },
    });

    if (response.ok || response.status === 404) {
      return NextResponse.json({ ok: true });
    }

    return NextResponse.json(
      { error: 'Failed to delete session' },
      { status: 502 },
    );
  } catch {
    return NextResponse.json(
      { error: 'FastAPI backend unavailable' },
      { status: 502 },
    );
  }
}

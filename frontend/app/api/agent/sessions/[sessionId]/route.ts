import { NextRequest, NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

const getBaseUrl = () =>
  process.env.FASTAPI_BASE_URL ?? 'http://127.0.0.1:8080';

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ sessionId: string }> },
) {
  try {
    const { sessionId } = await params;

    if (!sessionId?.trim()) {
      return NextResponse.json(
        { error: 'sessionId is required' },
        { status: 400 },
      );
    }

    const userId = request.nextUrl.searchParams.get('userId');
    const baseUrl = getBaseUrl();
    const upstreamUrl = new URL(
      `${baseUrl.replace(/\/$/, '')}/api/agent/sessions/${encodeURIComponent(sessionId)}`,
    );
    if (userId) upstreamUrl.searchParams.set('userId', userId);

    const response = await fetch(upstreamUrl.toString(), {
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

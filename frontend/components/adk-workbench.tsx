'use client';

import {
  Dispatch,
  FormEvent,
  SetStateAction,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';

import {
  initialSessions,
  simulateAgentTurn,
  type ChatMessage,
  type SessionRecord,
  type TimelineEvent,
} from '../lib/mock-data';

type InspectorTab = 'events' | 'state';

const LS_PREFIX = 'ins-agent:history:';

function saveSessionHistory(
  sessionId: string,
  messages: ChatMessage[],
  events: TimelineEvent[],
) {
  try {
    localStorage.setItem(
      LS_PREFIX + sessionId,
      JSON.stringify({
        messages: messages.filter((m) => m.status === 'final'),
        events,
        updatedTs: Date.now(),
      }),
    );
  } catch {
    // localStorage 不可用時靜默忽略
  }
}

function loadSessionHistory(sessionId: string): {
  messages: ChatMessage[];
  events: TimelineEvent[];
  updatedTs: number;
} | null {
  try {
    const raw = localStorage.getItem(LS_PREFIX + sessionId);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as {
      messages: ChatMessage[];
      events: TimelineEvent[];
      updatedTs?: number;
    };
    return {
      messages: parsed.messages,
      events: parsed.events,
      updatedTs: parsed.updatedTs ?? 0,
    };
  } catch {
    return null;
  }
}

function removeSessionHistory(sessionId: string) {
  try {
    localStorage.removeItem(LS_PREFIX + sessionId);
  } catch {
    // 靜默忽略
  }
}

function getOrCreateUserId(): string {
  const key = 'ins-agent:userId';
  try {
    const stored = localStorage.getItem(key);
    if (stored) return stored;
    const id = `user-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`;
    localStorage.setItem(key, id);
    return id;
  } catch {
    return 'anonymous';
  }
}

type ChatItem =
  | { kind: 'message'; message: ChatMessage }
  | { kind: 'tool-event'; event: TimelineEvent };

interface ProxyRunResponse {
  events: TimelineEvent[];
  finalText: string;
  state: Record<string, string>;
}

type ProxyStreamEnvelope =
  | {
      type: 'meta';
      transport: 'proxy';
      notice: string;
    }
  | {
      type: 'timeline';
      event: TimelineEvent;
    }
  | {
      type: 'state';
      patch: Record<string, string>;
    }
  | {
      type: 'message';
      text: string;
      mode: 'append' | 'replace';
      final: boolean;
    }
  | {
      type: 'done';
      finalText: string;
      state: Record<string, string>;
    }
  | {
      type: 'error';
      message: string;
    };

export function AdkWorkbench() {
  const [sessions, setSessions] = useState(initialSessions);
  const [activeSessionId, setActiveSessionId] = useState(initialSessions[0].id);
  const [selectedEventId, setSelectedEventId] = useState(
    initialSessions[0].events[0].id,
  );
  const [draft, setDraft] = useState('');
  const [inspectorTab, setInspectorTab] = useState<InspectorTab>('events');
  const [pending, setPending] = useState(false);
  const [transportMode, setTransportMode] = useState<
    'proxy' | 'mock' | 'standby'
  >('standby');
  const [runtimeNotice, setRuntimeNotice] = useState<string | null>(null);

  const [sidebarW, setSidebarW] = useState(240);
  const [inspectorW, setInspectorW] = useState(320);

  const [userId, setUserId] = useState('anonymous');

  useEffect(() => {
    setUserId(getOrCreateUserId());
  }, []);

  useEffect(() => {
    setSidebarW(
      Math.round(Math.max(180, Math.min(400, window.innerWidth * 0.18))),
    );
    setInspectorW(
      Math.round(Math.max(200, Math.min(480, window.innerWidth * 0.24))),
    );
  }, []);

  // 從 ADK 載入 session 清單，合併 localStorage 的歷史訊息
  useEffect(() => {
    if (userId === 'anonymous') return;
    fetch(`/api/agent/sessions?userId=${encodeURIComponent(userId)}`, {
      cache: 'no-store',
    })
      .then((res) => (res.ok ? res.json() : Promise.reject()))
      .then((data: { sessions: SessionRecord[] }) => {
        if (!Array.isArray(data.sessions) || data.sessions.length === 0) return;
        const merged = data.sessions.map((s) => {
          const history = loadSessionHistory(s.id);
          return history
            ? {
                ...s,
                messages: history.messages,
                events: history.events,
                _lsTs: history.updatedTs,
              }
            : { ...s, _lsTs: 0 };
        });
        // 以 localStorage updatedTs 重新排序（同為 0 時保持後端順序）
        merged.sort((a, b) => b._lsTs - a._lsTs);
        const sorted = merged.map(
          ({ _lsTs: _, ...rest }) => rest,
        ) as SessionRecord[];
        setSessions(sorted);
        setActiveSessionId(sorted[0].id);
        setSelectedEventId(sorted[0].events.at(-1)?.id ?? '');
      })
      .catch(() => {
        // ADK 離線 — 保留 initialSessions 作為示範資料
      });
  }, [userId]);

  // sessions 更新且非處理中時，自動持久化歷史訊息到 localStorage
  useEffect(() => {
    if (pending) return;
    sessions.forEach((s) => {
      if (s.messages.length > 0 || s.events.length > 0) {
        saveSessionHistory(s.id, s.messages, s.events);
      }
    });
  }, [sessions, pending]);
  const dragging = useRef<'left' | 'right' | null>(null);
  const startX = useRef(0);
  const startW = useRef(0);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const onDragStart = useCallback(
    (side: 'left' | 'right') => (e: React.MouseEvent) => {
      e.preventDefault();
      dragging.current = side;
      startX.current = e.clientX;
      startW.current = side === 'left' ? sidebarW : inspectorW;

      const onMove = (ev: MouseEvent) => {
        const delta = ev.clientX - startX.current;
        if (dragging.current === 'left') {
          setSidebarW(Math.max(180, Math.min(500, startW.current + delta)));
        } else {
          setInspectorW(Math.max(200, Math.min(600, startW.current - delta)));
        }
      };

      const onUp = () => {
        dragging.current = null;
        window.removeEventListener('mousemove', onMove);
        window.removeEventListener('mouseup', onUp);
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
      };

      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
      window.addEventListener('mousemove', onMove);
      window.addEventListener('mouseup', onUp);
    },
    [sidebarW, inspectorW],
  );

  const activeSession = useMemo(
    () =>
      sessions.find((session) => session.id === activeSessionId) ?? sessions[0],
    [activeSessionId, sessions],
  );

  const selectedEvent =
    activeSession.events.find((event) => event.id === selectedEventId) ??
    activeSession.events.at(-1) ??
    null;

  const chatItems = useMemo((): ChatItem[] => {
    const toolEvents = activeSession.events.filter(
      (e) => e.kind === 'tool-call' || e.kind === 'tool-result',
    );

    if (toolEvents.length === 0) {
      return activeSession.messages.map((m) => ({
        kind: 'message' as const,
        message: m,
      }));
    }

    const items: ChatItem[] = [];
    const turnTools: TimelineEvent[][] = [];
    let currentTools: TimelineEvent[] = [];
    let userEventCount = 0;

    for (const evt of activeSession.events) {
      if (evt.kind === 'user') {
        if (userEventCount > 0) {
          turnTools.push(currentTools);
          currentTools = [];
        }
        userEventCount++;
      } else if (evt.kind === 'tool-call' || evt.kind === 'tool-result') {
        currentTools.push(evt);
      }
    }
    turnTools.push(currentTools);

    let turnIdx = 0;

    for (const msg of activeSession.messages) {
      if (msg.role === 'agent' && turnIdx < turnTools.length) {
        for (const evt of turnTools[turnIdx]) {
          items.push({ kind: 'tool-event', event: evt });
        }
        turnIdx++;
      }
      items.push({ kind: 'message', message: msg });
    }

    while (turnIdx < turnTools.length) {
      for (const evt of turnTools[turnIdx]) {
        items.push({ kind: 'tool-event', event: evt });
      }
      turnIdx++;
    }

    return items;
  }, [activeSession.messages, activeSession.events]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatItems, pending]);

  function handleNewSession() {
    const seed = Date.now();
    const newSession: SessionRecord = {
      id: `session-${seed}`,
      title: '新對話',
      subtitle: '開始新的對話',
      status: 'idle',
      updatedAt: '剛剛',
      messages: [],
      events: [],
      state: {},
    };
    setSessions((prev) => [newSession, ...prev]);
    setActiveSessionId(newSession.id);
    setSelectedEventId('');
    // 在 ADK 建立 session（fire and forget）
    fetch('/api/agent/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sessionId: newSession.id,
        userId,
        state: {
          _ui_title: newSession.title,
          _ui_subtitle: newSession.subtitle,
        },
      }),
    }).catch(() => {
      /* ADK 離線，靜默忽略 */
    });
  }

  function handleSessionChange(sessionId: string) {
    const nextSession = sessions.find((session) => session.id === sessionId);

    if (!nextSession) {
      return;
    }

    // 若 in-memory 是空的，嘗試從 localStorage 還原歷史訊息
    if (nextSession.messages.length === 0) {
      const history = loadSessionHistory(sessionId);
      if (history && history.messages.length > 0) {
        setSessions((prev) =>
          prev.map((s) =>
            s.id === sessionId
              ? { ...s, messages: history.messages, events: history.events }
              : s,
          ),
        );
        setActiveSessionId(sessionId);
        setSelectedEventId(history.events.at(-1)?.id ?? '');
        return;
      }
    }

    setActiveSessionId(sessionId);
    setSelectedEventId(
      nextSession.events.at(-1)?.id ?? nextSession.events[0]?.id ?? '',
    );
  }

  function handleDeleteSession(e: React.MouseEvent, sessionId: string) {
    e.stopPropagation();
    setSessions((prev) => {
      const next = prev.filter((s) => s.id !== sessionId);
      if (next.length === 0) return prev; // keep at least one session
      if (sessionId === activeSessionId) {
        const fallback = next[0];
        setActiveSessionId(fallback.id);
        setSelectedEventId(
          fallback.events.at(-1)?.id ?? fallback.events[0]?.id ?? '',
        );
      }
      return next;
    });
    // 清除 localStorage 歷史紀錄
    removeSessionHistory(sessionId);
    // 從 ADK 刪除 session（fire and forget）
    fetch(
      `/api/agent/sessions/${encodeURIComponent(sessionId)}?userId=${encodeURIComponent(userId)}`,
      {
        method: 'DELETE',
      },
    ).catch(() => {
      /* ADK 離線，靜默忽略 */
    });
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const prompt = draft.trim();

    if (!prompt || pending) {
      return;
    }

    const seed = Date.now();
    const timestamp = formatClock();

    const userMessage: ChatMessage = {
      id: `msg-user-${seed}`,
      role: 'user',
      text: prompt,
      timestamp,
      status: 'final',
    };

    const userEvent: TimelineEvent = {
      id: `evt-user-${seed}`,
      kind: 'user',
      title: 'user_message',
      summary: prompt,
      timestamp,
      payload: ['author: user', `invocation_id: inv-${seed}`],
    };

    setDraft('');
    setPending(true);
    setRuntimeNotice(null);

    setSessions((currentSessions) =>
      currentSessions.map((session) => {
        if (session.id !== activeSessionId) {
          return session;
        }

        return {
          ...session,
          status: 'pending',
          updatedAt: '剛剛',
          subtitle: prompt.length > 40 ? `${prompt.slice(0, 40)}…` : prompt,
          messages: [...session.messages, userMessage],
          events: [...session.events, userEvent],
        };
      }),
    );
    setSelectedEventId(userEvent.id);

    let streamedAnyEnvelope = false;

    try {
      const response = await fetch('/api/agent/run', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          prompt,
          sessionId: activeSessionId,
          userId,
          sessionState: {
            ...activeSession.state,
            _ui_title: activeSession.title,
            _ui_subtitle:
              prompt.length > 40 ? `${prompt.slice(0, 40)}…` : prompt,
          },
        }),
      });

      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as {
          error?: string;
        } | null;

        throw new Error(payload?.error ?? 'ADK proxy request failed');
      }

      const contentType = response.headers.get('content-type') ?? '';

      if (!contentType.includes('text/event-stream') || !response.body) {
        const payload = (await response.json()) as ProxyRunResponse;
        const agentEvent = payload.events.at(-1);

        setSessions((currentSessions) =>
          currentSessions.map((session) => {
            if (session.id !== activeSessionId) {
              return session;
            }

            return {
              ...session,
              status: 'live',
              updatedAt: '剛剛',
              state: {
                ...session.state,
                ...payload.state,
              },
              messages: [
                ...session.messages,
                {
                  id: `msg-agent-${seed}`,
                  role: 'agent',
                  text:
                    payload.finalText ||
                    'ADK runtime 已完成執行，請查看右側 event history。',
                  timestamp: formatClock(),
                  status: 'final',
                },
              ],
              events: [...session.events, ...payload.events],
            };
          }),
        );

        setTransportMode('proxy');
        setRuntimeNotice('目前由 Next.js API route 代理到 ADK API server。');
        setSelectedEventId(agentEvent?.id ?? userEvent.id);
        setPending(false);
        return;
      }

      setTransportMode('proxy');
      await consumeProxyStream({
        response,
        seed,
        sessionId: activeSessionId,
        fallbackEventId: userEvent.id,
        setSessions,
        setSelectedEventId,
        setRuntimeNotice,
        onEnvelope: () => {
          streamedAnyEnvelope = true;
        },
      });

      setPending(false);
      return;
    } catch (error) {
      if (streamedAnyEnvelope) {
        setPending(false);
        setRuntimeNotice(
          error instanceof Error
            ? `SSE 串流中途中斷，已保留目前收到的事件。${error.message}`
            : 'SSE 串流中途中斷，已保留目前收到的事件。',
        );
        return;
      }

      setTransportMode('mock');
      setRuntimeNotice(
        error instanceof Error
          ? `ADK proxy 無法連線，已改用 mock fallback。${error.message}`
          : 'ADK proxy 無法連線，已改用 mock fallback。',
      );
    }

    const simulated = simulateAgentTurn(prompt, activeSession.state);
    const toolCallEvent: TimelineEvent = {
      id: `evt-call-${seed}`,
      kind: 'tool-call',
      title: simulated.toolName,
      summary: `Agent 以結構化方式請求 ${simulated.toolName}`,
      timestamp,
      payload: [`args: ${JSON.stringify(simulated.toolArgs)}`],
    };

    const streamMessageId = `msg-agent-stream-${seed}`;
    const streamEventId = `evt-stream-${seed}`;
    const resultEventId = `evt-result-${seed}`;
    const stateEventId = `evt-state-${seed}`;
    const finalEventId = `evt-final-${seed}`;

    setSessions((currentSessions) =>
      currentSessions.map((session) => {
        if (session.id !== activeSessionId) {
          return session;
        }

        return {
          ...session,
          status: 'pending',
          updatedAt: '剛剛',
          events: [...session.events, toolCallEvent],
        };
      }),
    );
    setSelectedEventId(toolCallEvent.id);

    window.setTimeout(() => {
      setSessions((currentSessions) =>
        currentSessions.map((session) => {
          if (session.id !== activeSessionId) {
            return session;
          }

          return {
            ...session,
            status: 'pending',
            messages: [
              ...session.messages,
              {
                id: streamMessageId,
                role: 'agent',
                text: simulated.streamText,
                timestamp: formatClock(),
                status: 'streaming',
              },
            ],
            events: [
              ...session.events,
              {
                id: resultEventId,
                kind: 'tool-result',
                title: `${simulated.toolName} result`,
                summary: simulated.toolSummary,
                timestamp: formatClock(),
                payload: [
                  `top_product: ${simulated.productName}`,
                  `state_patch_keys: ${Object.keys(simulated.statePatch).join(', ')}`,
                ],
              },
              {
                id: streamEventId,
                kind: 'stream',
                title: 'partial_response',
                summary: '模型開始串流回覆內容',
                timestamp: formatClock(),
                payload: ['partial: true', simulated.streamText],
              },
            ],
          };
        }),
      );
      setSelectedEventId(streamEventId);
    }, 420);

    window.setTimeout(() => {
      setSessions((currentSessions) =>
        currentSessions.map((session) => {
          if (session.id !== activeSessionId) {
            return session;
          }

          return {
            ...session,
            status: 'live',
            updatedAt: '剛剛',
            state: {
              ...session.state,
              ...simulated.statePatch,
            },
            messages: session.messages.map((message) =>
              message.id === streamMessageId
                ? {
                    ...message,
                    text: simulated.finalText,
                    status: 'final',
                    timestamp: formatClock(),
                  }
                : message,
            ),
            events: [
              ...session.events,
              {
                id: stateEventId,
                kind: 'state',
                title: 'state_delta',
                summary: '將本輪整理出的條件與最近一次推薦寫回 session',
                timestamp: formatClock(),
                payload: Object.entries(simulated.statePatch).map(
                  ([key, value]) => `${key}: ${value}`,
                ),
              },
              {
                id: finalEventId,
                kind: 'agent',
                title: 'final_response',
                summary: '完成可顯示的 agent response',
                timestamp: formatClock(),
                payload: ['is_final_response: true', 'turn_complete: true'],
              },
            ],
          };
        }),
      );

      setSelectedEventId(finalEventId);
      setPending(false);
    }, 980);
  }

  return (
    <main className='workbench'>
      <div className='workbench__frame'>
        <aside
          className='pane sidebar'
          style={{ width: sidebarW, minWidth: sidebarW }}
        >
          <div className='brand'>
            <div className='brand__logo' aria-hidden='true'>
              <svg
                viewBox='0 0 24 24'
                fill='none'
                xmlns='http://www.w3.org/2000/svg'
              >
                <path
                  d='M12 2L3 6.5v5c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12v-5L12 2z'
                  fill='currentColor'
                  opacity='0.18'
                />
                <path
                  d='M12 2L3 6.5v5c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12v-5L12 2z'
                  stroke='currentColor'
                  strokeWidth='1.5'
                  strokeLinejoin='round'
                />
                <path
                  d='M9 12l2 2 4-4'
                  stroke='currentColor'
                  strokeWidth='1.5'
                  strokeLinecap='round'
                  strokeLinejoin='round'
                />
              </svg>
            </div>
            <h1>保險智能顧問</h1>
          </div>

          <div
            style={{
              flex: 1,
              minHeight: 0,
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            <div className='section-label'>
              <span>對話列表 ({sessions.length})</span>
              <button
                type='button'
                className='new-session-btn'
                onClick={handleNewSession}
                title='新增對話'
                aria-label='新增對話'
              >
                <svg
                  viewBox='0 0 16 16'
                  fill='none'
                  xmlns='http://www.w3.org/2000/svg'
                  aria-hidden='true'
                  className='new-session-btn__icon'
                >
                  <path
                    d='M8 2v12M2 8h12'
                    stroke='currentColor'
                    strokeWidth='1.8'
                    strokeLinecap='round'
                  />
                </svg>
                新增對話
              </button>
            </div>
            <div className='session-list'>
              {sessions.map((session) => (
                <div key={session.id} className='session-card-wrap'>
                  <button
                    type='button'
                    className={`session-card ${session.id === activeSessionId ? 'session-card--active' : ''}`}
                    onClick={() => handleSessionChange(session.id)}
                  >
                    <div className='session-card__header'>
                      <h3 className='session-card__title'>{session.title}</h3>
                      <span className={`badge badge--${session.status}`}>
                        {session.status === 'live'
                          ? '進行中'
                          : session.status === 'pending'
                            ? '處理中'
                            : '閒置'}
                      </span>
                    </div>
                    <p className='session-card__subtitle'>{session.subtitle}</p>
                    <div className='section-label'>
                      <span>更新</span>
                      <span>{session.updatedAt}</span>
                    </div>
                  </button>
                  <button
                    type='button'
                    className='session-delete-btn'
                    onClick={(e) => handleDeleteSession(e, session.id)}
                    title='刪除對話'
                    aria-label='刪除對話'
                    disabled={sessions.length <= 1}
                  >
                    <svg
                      viewBox='0 0 14 14'
                      fill='none'
                      xmlns='http://www.w3.org/2000/svg'
                      aria-hidden='true'
                    >
                      <path
                        d='M2.5 3.5h9M5.5 3.5V2.5h3v1M6 6v4M8 6v4M3.5 3.5l.5 8h6l.5-8'
                        stroke='currentColor'
                        strokeWidth='1.3'
                        strokeLinecap='round'
                        strokeLinejoin='round'
                      />
                    </svg>
                  </button>
                </div>
              ))}
            </div>
          </div>

          <footer className='sidebar__footer'>
            <div className='section-label'>
              <span>
                {transportMode === 'proxy'
                  ? '代理模式'
                  : transportMode === 'mock'
                    ? '模擬模式'
                    : '待機中'}
              </span>
              <span className='sidebar__footer-env'>開發環境</span>
            </div>
            <p className='section-copy'>
              {runtimeNotice ??
                '若 ADK API server 可用，將自動切換為代理模式。'}
            </p>
          </footer>
        </aside>

        <div className='drag-handle' onMouseDown={onDragStart('left')} />

        <section className='pane main'>
          <header className='header'>
            <div className='header__topline'>
              <div>
                <h3 className='header__title'>{activeSession.title}</h3>
                <p className='header__subtext'>{activeSession.subtitle}</p>
              </div>
              <div className='header__pills'>
                <span className='pill pill--ok'>
                  session: {activeSession.id}
                </span>
                <span
                  className={`pill ${
                    transportMode === 'proxy'
                      ? 'pill--ok'
                      : transportMode === 'mock'
                        ? 'pill--signal'
                        : 'pill--soft'
                  }`}
                >
                  {transportMode === 'proxy'
                    ? '代理模式'
                    : transportMode === 'mock'
                      ? '模擬模式'
                      : '待機中'}
                </span>
                <span className='pill pill--soft'>
                  {activeSession.events.length} 個事件
                </span>
                <span className='pill pill--soft'>
                  {activeSession.messages.length} 則訊息
                </span>
              </div>
            </div>
          </header>

          <div className='chat'>
            {chatItems.length === 0 && !pending && (
              <div className='chat-empty'>
                <div className='chat-empty__icon' aria-hidden='true'>
                  <svg
                    viewBox='0 0 48 48'
                    fill='none'
                    xmlns='http://www.w3.org/2000/svg'
                  >
                    <path
                      d='M24 4L6 13v10c0 11.1 7.68 21.48 18 24 10.32-2.52 18-12.9 18-24V13L24 4z'
                      fill='currentColor'
                      opacity='0.1'
                    />
                    <path
                      d='M24 4L6 13v10c0 11.1 7.68 21.48 18 24 10.32-2.52 18-12.9 18-24V13L24 4z'
                      stroke='currentColor'
                      strokeWidth='1.8'
                      strokeLinejoin='round'
                    />
                    <path
                      d='M17 24l5 5 9-9'
                      stroke='currentColor'
                      strokeWidth='2'
                      strokeLinecap='round'
                      strokeLinejoin='round'
                    />
                  </svg>
                </div>
                <h2 className='chat-empty__title'>新對話開始</h2>
                <p className='chat-empty__hint'>
                  描述你的保障需求，例如年齡、預算與保障目標，智能顧問將為你分析並推薦適合的保障方案。
                </p>
                <div className='chat-empty__prompts'>
                  {[
                    '我 30 歲，年預算 15000，想加強醫療保障',
                    '有家庭要負擔，想了解家庭責任保障',
                    '月收六萬，想評估失能風險覆蓋的空間',
                  ].map((prompt) => (
                    <button
                      key={prompt}
                      type='button'
                      className='chat-empty__prompt-btn'
                      onClick={() => setDraft(prompt)}
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {chatItems.map((item) => {
              if (item.kind === 'message') {
                const message = item.message;
                return (
                  <article
                    key={message.id}
                    className={`message message--${message.role} ${message.status === 'streaming' ? 'message--streaming' : ''}`}
                  >
                    <div className='message__meta'>
                      {message.role === 'user' ? 'user' : 'agent'} •{' '}
                      {message.timestamp}
                      {message.status === 'streaming' ? ' • partial' : ''}
                    </div>
                    {message.role === 'agent' ? (
                      <div
                        className='message__text message__markdown'
                        dangerouslySetInnerHTML={{
                          __html: renderMarkdown(message.text),
                        }}
                      />
                    ) : (
                      <p className='message__text'>{message.text}</p>
                    )}
                  </article>
                );
              }

              const evt = item.event;
              return (
                <details key={evt.id} className='tool-event'>
                  <summary className='tool-event__summary'>
                    <span className={`event__kind event__kind--${evt.kind}`}>
                      {evt.kind}
                    </span>
                    <span className='tool-event__title'>{evt.title}</span>
                    <span className='event__timestamp'>{evt.timestamp}</span>
                  </summary>
                  <pre className='tool-event__payload'>
                    {evt.payload.join('\n')}
                  </pre>
                </details>
              );
            })}

            {pending && (
              <article className='message message--agent typing-indicator'>
                <div className='message__meta'>agent • thinking</div>
                <div className='typing-dots'>
                  <span />
                  <span />
                  <span />
                </div>
              </article>
            )}
            <div ref={chatEndRef} />
          </div>

          <div className='composer'>
            <form onSubmit={handleSubmit}>
              <textarea
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (
                    event.key === 'Enter' &&
                    !event.shiftKey &&
                    !event.nativeEvent.isComposing
                  ) {
                    event.preventDefault();
                    const form = event.currentTarget.form;
                    if (form) form.requestSubmit();
                  }
                }}
                placeholder='輸入保險需求，例如：我 30 歲，年預算 15000，想加強醫療保障（Shift+Enter 換行）'
              />
              <div className='composer__footer'>
                <div className='composer__hint'>
                  {transportMode === 'proxy'
                    ? 'Proxy 模式，實時串流回覆'
                    : 'ADK 離線，使用模擬資料'}
                </div>
                <button className='button' type='submit' disabled={pending}>
                  {pending ? '回覆中…' : '傳送'}
                </button>
              </div>
            </form>
          </div>
        </section>

        <div className='drag-handle' onMouseDown={onDragStart('right')} />

        <aside
          className='pane inspector'
          style={{ width: inspectorW, minWidth: inspectorW }}
        >
          <div className='inspector__header'>
            <div className='section-label'>
              <span>Inspector</span>
              <span className='inspector__updated'>
                {activeSession.updatedAt}
              </span>
            </div>
            <div className='tab-group'>
              <button
                type='button'
                className={`tab ${inspectorTab === 'events' ? 'tab--active' : ''}`}
                onClick={() => setInspectorTab('events')}
              >
                <svg
                  viewBox='0 0 14 14'
                  fill='none'
                  xmlns='http://www.w3.org/2000/svg'
                  aria-hidden='true'
                  className='tab__icon'
                >
                  <circle cx='2' cy='4' r='1.2' fill='currentColor' />
                  <line
                    x1='5'
                    y1='4'
                    x2='12'
                    y2='4'
                    stroke='currentColor'
                    strokeWidth='1.4'
                    strokeLinecap='round'
                  />
                  <circle cx='2' cy='8' r='1.2' fill='currentColor' />
                  <line
                    x1='5'
                    y1='8'
                    x2='12'
                    y2='8'
                    stroke='currentColor'
                    strokeWidth='1.4'
                    strokeLinecap='round'
                  />
                  <circle cx='2' cy='12' r='1.2' fill='currentColor' />
                  <line
                    x1='5'
                    y1='12'
                    x2='9'
                    y2='12'
                    stroke='currentColor'
                    strokeWidth='1.4'
                    strokeLinecap='round'
                  />
                </svg>
                事件歷程
              </button>
              <button
                type='button'
                className={`tab ${inspectorTab === 'state' ? 'tab--active' : ''}`}
                onClick={() => setInspectorTab('state')}
              >
                <svg
                  viewBox='0 0 14 14'
                  fill='none'
                  xmlns='http://www.w3.org/2000/svg'
                  aria-hidden='true'
                  className='tab__icon'
                >
                  <rect
                    x='1'
                    y='1'
                    width='5'
                    height='5'
                    rx='1.2'
                    stroke='currentColor'
                    strokeWidth='1.3'
                  />
                  <rect
                    x='8'
                    y='1'
                    width='5'
                    height='5'
                    rx='1.2'
                    stroke='currentColor'
                    strokeWidth='1.3'
                  />
                  <rect
                    x='1'
                    y='8'
                    width='5'
                    height='5'
                    rx='1.2'
                    stroke='currentColor'
                    strokeWidth='1.3'
                  />
                  <rect
                    x='8'
                    y='8'
                    width='5'
                    height='5'
                    rx='1.2'
                    stroke='currentColor'
                    strokeWidth='1.3'
                  />
                </svg>
                User State
              </button>
            </div>
          </div>

          <div className='inspector__body'>
            {inspectorTab === 'events' ? (
              <div className='timeline'>
                {groupStreamEvents(activeSession.events).map((node) => {
                  if (node.kind === 'stream-group') {
                    return (
                      <StreamGroupNode
                        key={node.events[0].id}
                        events={node.events}
                        isLast={node.isLast}
                      />
                    );
                  }
                  const event = node.event;
                  return (
                    <details key={event.id} className='timeline__node'>
                      <summary className='timeline__header'>
                        <span
                          className='timeline__dot'
                          data-kind={event.kind}
                        />
                        {!node.isLast && <span className='timeline__line' />}
                        <span
                          className={`event__kind event__kind--${event.kind}`}
                        >
                          {event.kind}
                        </span>
                        <span className='timeline__title'>{event.title}</span>
                        <span className='event__timestamp'>
                          {event.timestamp}
                        </span>
                      </summary>
                      <div className='timeline__detail'>
                        <p className='timeline__summary'>{event.summary}</p>
                        {event.payload.length > 0 && (
                          <ul className='timeline__payload'>
                            {event.payload.map((line) => (
                              <li key={line}>{line}</li>
                            ))}
                          </ul>
                        )}
                      </div>
                    </details>
                  );
                })}
                {activeSession.events.length === 0 && (
                  <div className='empty-state'>尚無事件紀錄。</div>
                )}
              </div>
            ) : (
              <div className='state-tree'>
                {(() => {
                  const entries = Object.entries(activeSession.state).filter(
                    ([k]) => !k.startsWith('_ui_'),
                  );
                  return entries.length > 0 ? (
                    entries.map(([key, value]) => (
                      <StateTreeNode
                        key={key}
                        nodeKey={key}
                        value={parseStateValue(value)}
                        depth={0}
                      />
                    ))
                  ) : (
                    <div className='empty-state'>尚無 state 資料。</div>
                  );
                })()}
              </div>
            )}
          </div>
        </aside>
      </div>
    </main>
  );
}

function renderMarkdown(text: string): string {
  let html = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  // fenced code blocks (protect from further processing)
  const codeBlocks: string[] = [];
  html = html.replace(/```[\s\S]*?```/g, (match) => {
    const inner = match.slice(3, -3);
    codeBlocks.push(`<pre><code>${inner}</code></pre>`);
    return `\x02CODE${codeBlocks.length - 1}\x03`;
  });

  // inline code
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
  // headings
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
  // bold & italic
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
  // horizontal rule
  html = html.replace(/^---$/gm, '<hr/>');

  // process lists line-by-line to correctly separate ul / ol
  const lines = html.split('\n');
  const resultLines: string[] = [];
  let listType: 'ul' | 'ol' | null = null;
  let listItems: string[] = [];

  const flushList = () => {
    if (listType && listItems.length > 0) {
      const items = listItems.map((i) => `<li>${i}</li>`).join('');
      resultLines.push(`<${listType}>${items}</${listType}>`);
      listType = null;
      listItems = [];
    }
  };

  for (const line of lines) {
    const ulMatch = line.match(/^[\-\*] (.+)$/);
    const olMatch = line.match(/^\d+\. (.+)$/);

    if (ulMatch) {
      if (listType === 'ol') flushList();
      listType = 'ul';
      listItems.push(ulMatch[1]);
    } else if (olMatch) {
      if (listType === 'ul') flushList();
      listType = 'ol';
      listItems.push(olMatch[1]);
    } else {
      flushList();
      resultLines.push(line);
    }
  }
  flushList();
  html = resultLines.join('\n');

  // restore code blocks
  html = html.replace(/\x02CODE(\d+)\x03/g, (_, i) => codeBlocks[Number(i)]);

  // line breaks: double newline → paragraph break, single → <br>
  html = html.replace(/\n\n/g, '</p><p>');
  html = html.replace(/\n/g, '<br/>');
  html = `<p>${html}</p>`;

  // cleanup: unwrap block-level elements from <p>
  const blocks = ['h1', 'h2', 'h3', 'ul', 'ol', 'pre', 'hr/'];
  for (const tag of blocks) {
    const open = tag === 'hr/' ? '<hr/>' : `<${tag}>`;
    const close = tag === 'hr/' ? '' : `</${tag}>`;
    html = html.replace(new RegExp(`<p>(${escRe(open)})`, 'g'), '$1');
    if (close)
      html = html.replace(new RegExp(`(${escRe(close)})</p>`, 'g'), '$1');
  }
  html = html.replace(/<p><\/p>/g, '');
  return html;
}

function escRe(s: string) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// ── User State tree view ──────────────────────────────────────────────────────

function parseStateValue(raw: unknown): unknown {
  if (typeof raw !== 'string') return raw;
  const trimmed = raw.trim();
  if (
    (trimmed.startsWith('{') && trimmed.endsWith('}')) ||
    (trimmed.startsWith('[') && trimmed.endsWith(']'))
  ) {
    try {
      return JSON.parse(trimmed);
    } catch {
      // keep as string
    }
  }
  return raw;
}

function StateTreeNode({
  nodeKey,
  value,
  depth = 0,
}: {
  nodeKey: string;
  value: unknown;
  depth?: number;
}) {
  const [expanded, setExpanded] = useState(depth < 1);

  const isArray = Array.isArray(value);
  const isObject = value !== null && typeof value === 'object' && !isArray;
  const isCollection = isArray || isObject;

  if (isCollection) {
    const entries: [string, unknown][] = isArray
      ? (value as unknown[]).map((v, i) => [String(i), v])
      : Object.entries(value as Record<string, unknown>);
    const badge = isArray ? `[${entries.length}]` : `{${entries.length}}`;

    return (
      <div className='tree-node' data-depth={depth}>
        <button
          type='button'
          className='tree-node__toggle'
          onClick={() => setExpanded((e) => !e)}
          aria-expanded={expanded}
        >
          <span
            className={`tree-node__arrow ${expanded ? 'tree-node__arrow--open' : ''}`}
          />
          <span className='tree-node__key'>{nodeKey}</span>
          <span className='tree-node__badge'>{badge}</span>
        </button>
        {expanded && (
          <div className='tree-node__children'>
            {entries.map(([k, v]) => (
              <StateTreeNode key={k} nodeKey={k} value={v} depth={depth + 1} />
            ))}
          </div>
        )}
      </div>
    );
  }

  const displayValue =
    value === null ? 'null' : value === undefined ? 'undefined' : String(value);
  const valueType =
    value === null
      ? 'null'
      : typeof value === 'boolean'
        ? 'boolean'
        : typeof value === 'number'
          ? 'number'
          : 'string';

  return (
    <div className='tree-node' data-depth={depth}>
      <div className='tree-node__leaf'>
        <span className='tree-node__dot' />
        <span className='tree-node__key'>{nodeKey}</span>
        <span className={`tree-node__value tree-node__value--${valueType}`}>
          {displayValue}
        </span>
      </div>
    </div>
  );
}

// ── Timeline stream-group helpers ─────────────────────────────────────────────

type TimelineDisplayNode =
  | { kind: 'single'; event: TimelineEvent; isLast: boolean }
  | { kind: 'stream-group'; events: TimelineEvent[]; isLast: boolean };

function groupStreamEvents(events: TimelineEvent[]): TimelineDisplayNode[] {
  const nodes: TimelineDisplayNode[] = [];
  let i = 0;
  while (i < events.length) {
    if (events[i].kind === 'stream') {
      const group: TimelineEvent[] = [];
      while (i < events.length && events[i].kind === 'stream') {
        group.push(events[i]);
        i++;
      }
      nodes.push({ kind: 'stream-group', events: group, isLast: false });
    } else {
      nodes.push({ kind: 'single', event: events[i], isLast: false });
      i++;
    }
  }
  if (nodes.length > 0) {
    nodes[nodes.length - 1] = { ...nodes[nodes.length - 1], isLast: true };
  }
  return nodes;
}

function StreamGroupNode({
  events,
  isLast,
}: {
  events: TimelineEvent[];
  isLast: boolean;
}) {
  const first = events[0];
  const last = events[events.length - 1];
  return (
    <details className='timeline__node'>
      <summary className='timeline__header'>
        <span className='timeline__dot' data-kind='stream' />
        {!isLast && <span className='timeline__line' />}
        <span className='event__kind event__kind--stream'>stream</span>
        <span className='timeline__title'>partial_response</span>
        <span className='timeline__group-badge'>×{events.length}</span>
        <span className='event__timestamp'>{last.timestamp}</span>
      </summary>
      <div className='timeline__detail'>
        <p className='timeline__summary'>
          串流 {events.length} 個片段，首段於 {first.timestamp}
        </p>
        <ol className='timeline__group-chunks'>
          {events.map((evt, chunkIdx) => (
            <li key={evt.id} className='timeline__chunk'>
              <span className='timeline__chunk-idx'>{chunkIdx + 1}</span>
              <span className='timeline__chunk-text'>
                {evt.payload[0] ?? evt.summary}
              </span>
            </li>
          ))}
        </ol>
      </div>
    </details>
  );
}

// ─────────────────────────────────────────────────────────────────────────────

function formatClock() {
  return new Intl.DateTimeFormat('zh-TW', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(new Date());
}

async function consumeProxyStream({
  response,
  seed,
  sessionId,
  fallbackEventId,
  setSessions,
  setSelectedEventId,
  setRuntimeNotice,
  onEnvelope,
}: {
  response: Response;
  seed: number;
  sessionId: string;
  fallbackEventId: string;
  setSessions: Dispatch<SetStateAction<SessionRecord[]>>;
  setSelectedEventId: Dispatch<SetStateAction<string>>;
  setRuntimeNotice: Dispatch<SetStateAction<string | null>>;
  onEnvelope: () => void;
}) {
  const streamMessageId = `msg-agent-stream-${seed}`;
  const decoder = new TextDecoder();
  const reader = response.body?.getReader();

  if (!reader) {
    throw new Error('Proxy stream body is unavailable');
  }

  let buffer = '';
  let latestEventId = fallbackEventId;
  let sawDone = false;

  setSessions((currentSessions) =>
    currentSessions.map((session) => {
      if (session.id !== sessionId) {
        return session;
      }

      const hasPlaceholder = session.messages.some(
        (message) => message.id === streamMessageId,
      );

      return {
        ...session,
        status: 'pending',
        messages: hasPlaceholder
          ? session.messages
          : [
              ...session.messages,
              {
                id: streamMessageId,
                role: 'agent',
                text: '',
                timestamp: formatClock(),
                status: 'streaming',
              },
            ],
      };
    }),
  );

  try {
    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        buffer += decoder.decode();
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const frames = buffer.split(/\r?\n\r?\n/);
      buffer = frames.pop() ?? '';

      for (const frame of frames) {
        const envelope = parseProxyEnvelope(frame);

        if (!envelope) {
          continue;
        }

        onEnvelope();

        if (envelope.type === 'meta') {
          setRuntimeNotice(envelope.notice);
          continue;
        }

        if (envelope.type === 'timeline') {
          latestEventId = envelope.event.id;
          setSessions((currentSessions) =>
            currentSessions.map((session) => {
              if (session.id !== sessionId) {
                return session;
              }

              if (
                session.events.some((event) => event.id === envelope.event.id)
              ) {
                return session;
              }

              return {
                ...session,
                updatedAt: '剛剛',
                events: [...session.events, envelope.event],
              };
            }),
          );
          setSelectedEventId(envelope.event.id);
          continue;
        }

        if (envelope.type === 'state') {
          setSessions((currentSessions) =>
            currentSessions.map((session) => {
              if (session.id !== sessionId) {
                return session;
              }

              return {
                ...session,
                updatedAt: '剛剛',
                state: {
                  ...session.state,
                  ...envelope.patch,
                },
              };
            }),
          );
          continue;
        }

        if (envelope.type === 'message') {
          setSessions((currentSessions) =>
            currentSessions.map((session) => {
              if (session.id !== sessionId) {
                return session;
              }

              return {
                ...session,
                updatedAt: '剛剛',
                messages: session.messages.map((message) => {
                  if (message.id !== streamMessageId) {
                    return message;
                  }

                  return {
                    ...message,
                    text:
                      envelope.mode === 'append'
                        ? `${message.text}${envelope.text}`
                        : envelope.text,
                    timestamp: formatClock(),
                    status: envelope.final ? 'final' : 'streaming',
                  };
                }),
              };
            }),
          );
          continue;
        }

        if (envelope.type === 'error') {
          setRuntimeNotice(`SSE proxy 發生錯誤：${envelope.message}`);
          continue;
        }

        if (envelope.type === 'done') {
          sawDone = true;
          setSessions((currentSessions) =>
            currentSessions.map((session) => {
              if (session.id !== sessionId) {
                return session;
              }

              return {
                ...session,
                status: 'live',
                updatedAt: '剛剛',
                state: {
                  ...session.state,
                  ...envelope.state,
                },
                messages: session.messages.map((message) =>
                  message.id === streamMessageId
                    ? {
                        ...message,
                        text: message.text || envelope.finalText,
                        timestamp: formatClock(),
                        status: 'final',
                      }
                    : message,
                ),
              };
            }),
          );
          setSelectedEventId(latestEventId);
        }
      }
    }

    if (buffer.trim()) {
      const envelope = parseProxyEnvelope(buffer);

      if (envelope?.type === 'done') {
        sawDone = true;
        setSessions((currentSessions) =>
          currentSessions.map((session) => {
            if (session.id !== sessionId) {
              return session;
            }

            return {
              ...session,
              status: 'live',
              updatedAt: '剛剛',
              state: {
                ...session.state,
                ...envelope.state,
              },
              messages: session.messages.map((message) =>
                message.id === streamMessageId
                  ? {
                      ...message,
                      text: message.text || envelope.finalText,
                      timestamp: formatClock(),
                      status: 'final',
                    }
                  : message,
              ),
            };
          }),
        );
      }
    }

    if (!sawDone) {
      setSessions((currentSessions) =>
        currentSessions.map((session) => {
          if (session.id !== sessionId) {
            return session;
          }

          return {
            ...session,
            status: 'live',
            updatedAt: '剛剛',
            messages: session.messages.map((message) =>
              message.id === streamMessageId
                ? {
                    ...message,
                    timestamp: formatClock(),
                    status: 'final',
                  }
                : message,
            ),
          };
        }),
      );
      setSelectedEventId(latestEventId);
    }
  } finally {
    reader.releaseLock();
  }
}

function parseProxyEnvelope(frame: string) {
  const dataLines = frame
    .split(/\r?\n/)
    .filter((line) => line.startsWith('data:'))
    .map((line) => line.slice(5).trimStart())
    .filter(Boolean);

  if (dataLines.length === 0) {
    return null;
  }

  try {
    return JSON.parse(dataLines.join('\n')) as ProxyStreamEnvelope;
  } catch {
    return null;
  }
}

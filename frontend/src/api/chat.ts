import client from './client';

export interface Session {
  id: number;
  title?: string;
  created_at: string;
  updated_at?: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
}

export function createSession() {
  return client.post<{ session_id: number }>('/chat/session');
}

export function getSessions() {
  return client.get<{ sessions: Session[] }>('/chat/sessions');
}

export function getHistory(sessionId: string) {
  return client.get<{ messages: ChatMessage[] }>(`/chat/session/${sessionId}/history`);
}

export interface SSEEvent {
  event: 'thinking' | 'token' | 'tool_call' | 'tool_result' | 'trip_plan' | 'done' | 'error';
  data: string;
}

export async function sendMessage(
  sessionId: string,
  content: string,
  onEvent: (evt: SSEEvent) => void,
) {
  const token = localStorage.getItem('token');
  const response = await fetch('/api/chat/message', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ session_id: sessionId, content }),
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error('No response body');

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';

    let currentEvent = 'token';
    const dataLines: string[] = [];

    const flushEvent = () => {
      if (dataLines.length === 0) return;
      const data = dataLines.join('\n');
      dataLines.length = 0;
      onEvent({ event: currentEvent as SSEEvent['event'], data });
    };

    for (const line of lines) {
      if (line.startsWith('event:')) {
        flushEvent();
        currentEvent = line.slice(6).trim();
      } else if (line.startsWith('data:')) {
        // SSE 规范：`data:` 后的第一个空格是可选分隔符，应跳过
        const payload = line.charAt(5) === ' ' ? line.slice(6) : line.slice(5);
        dataLines.push(payload);
      } else if (line.trim() === '') {
        flushEvent();
      }
    }
    flushEvent();
  }
}
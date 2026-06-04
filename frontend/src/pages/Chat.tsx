import { useState, useEffect, useRef, useCallback } from 'react';
import { Button, Input, List, Typography, Spin, Collapse, Card, Empty, Tag, message } from 'antd';
import { PlusOutlined, SendOutlined, RobotOutlined, UserOutlined, BulbOutlined, SaveOutlined } from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { createSession, getSessions, getHistory, sendMessage, type Session, type SSEEvent } from '@/api/chat';
import { createTrip, type TripPlanData } from '@/api/trips';

const { Text } = Typography;

interface DisplayMessage {
  role: 'user' | 'assistant';
  content: string;
  thinking?: string;
  toolCalls?: { name: string; result: string }[];
  tripPlan?: string;
}

export default function Chat() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSession, setActiveSession] = useState<number | null>(null);
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [loadingSessions, setLoadingSessions] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => { scrollToBottom(); }, [messages, scrollToBottom]);

  useEffect(() => {
    getSessions()
      .then((res) => setSessions(res.data.sessions))
      .finally(() => setLoadingSessions(false));
  }, []);

  const loadHistory = useCallback(async (sessionId: number) => {
    setActiveSession(sessionId);
    const res = await getHistory(String(sessionId));
    setMessages(res.data.messages.map((m) => ({ role: m.role, content: m.content })));
  }, []);

  const handleNewSession = async () => {
    const res = await createSession();
    const newSession: Session = { id: res.data.session_id, title: '新对话', created_at: new Date().toISOString() };
    setSessions((prev) => [newSession, ...prev]);
    setActiveSession(res.data.session_id);
    setMessages([]);
  };

  const handleSend = async () => {
    if (!input.trim() || !activeSession || streaming) return;
    const userMsg = input.trim();
    setInput('');
    setMessages((prev) => [...prev, { role: 'user', content: userMsg }]);
    setStreaming(true);

    let assistantContent = '';
    let thinkingContent = '';
    const toolCalls: { name: string; result: string }[] = [];
    let currentToolName = '';
    let tripPlan = '';

    setMessages((prev) => [...prev, { role: 'assistant', content: '' }]);

    const updateLastMessage = () => {
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: 'assistant',
          content: assistantContent,
          thinking: thinkingContent || undefined,
          toolCalls: toolCalls.length > 0 ? [...toolCalls] : undefined,
          tripPlan: tripPlan || undefined,
        };
        return updated;
      });
    };

    try {
      await sendMessage(String(activeSession), userMsg, (evt: SSEEvent) => {
        switch (evt.event) {
          case 'thinking':
            thinkingContent = evt.data;
            updateLastMessage();
            break;
          case 'token':
            assistantContent += evt.data;
            updateLastMessage();
            break;
          case 'tool_call':
            try {
              const parsed = JSON.parse(evt.data);
              currentToolName = parsed.tool || evt.data;
            } catch {
              currentToolName = evt.data;
            }
            break;
          case 'tool_result':
            toolCalls.push({ name: currentToolName || 'tool', result: evt.data });
            updateLastMessage();
            break;
          case 'trip_plan':
            tripPlan = evt.data;
            updateLastMessage();
            break;
          case 'error':
            assistantContent += `\n> ⚠️ 错误: ${evt.data}`;
            updateLastMessage();
            break;
        }
      });
    } finally {
      setStreaming(false);
    }
  };

  const toolNameMap: Record<string, string> = {
    find_spots_tool: '🔍 景点搜索',
    plan_route_tool: '🗺️ 路线规划',
    check_weather_tool: '🌤️ 天气查询',
    estimate_budget_tool: '💰 预算估算',
    find_spots_agent: '🔍 景点搜索 Agent',
    plan_route_agent: '🗺️ 路线规划 Agent',
    check_weather_agent: '🌤️ 天气查询 Agent',
    estimate_budget_agent: '💰 预算估算 Agent',
    get_current_time_tool: '🕐 获取当前时间',
  };

  const [savingTrip, setSavingTrip] = useState(false);
  const [savedTripIds, setSavedTripIds] = useState<Set<string>>(new Set());

  const handleSaveTrip = async (planJson: string) => {
    try {
      setSavingTrip(true);
      const data = JSON.parse(planJson) as TripPlanData;
      await createTrip(data);
      setSavedTripIds((prev) => new Set([...prev, planJson]));
      message.success('行程已保存！可在"我的行程"中查看');
    } catch {
      message.error('保存失败，请重试');
    } finally {
      setSavingTrip(false);
    }
  };

  const renderTripPlan = (plan: string) => {
    try {
      const data = JSON.parse(plan) as {
        title?: string;
        destination?: string;
        budget_total?: number;
        start_date?: string;
        end_date?: string;
        days?: { day_index: number; date?: string; weather?: string; activities?: { order_index: number; spot_name: string; time_slot?: string; transport?: string; estimated_cost?: number }[] }[]
      };
      const isSaved = savedTripIds.has(plan);
      return (
        <Card
          size="small"
          title={`📋 ${data.title ?? '行程规划'}`}
          extra={
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              {data.budget_total ? <Tag color="green">预算 ¥{data.budget_total}</Tag> : null}
              <Button
                type="primary"
                size="small"
                icon={<SaveOutlined />}
                loading={savingTrip}
                disabled={isSaved}
                onClick={() => handleSaveTrip(plan)}
              >
                {isSaved ? '已保存' : '保存到我的行程'}
              </Button>
            </div>
          }
          style={{ marginTop: 12, background: '#f6ffed', borderColor: '#b7eb8f' }}
        >
          {data.start_date && data.end_date && (
            <div style={{ marginBottom: 8, color: '#888' }}>
              📅 {data.start_date} ~ {data.end_date} · {data.destination || ''}
            </div>
          )}
          {data.days?.map((day) => (
            <div key={day.day_index} style={{ marginBottom: 12 }}>
              <Text strong>第 {day.day_index} 天 {day.date || ''} {day.weather ? `| ${day.weather}` : ''}</Text>
              <div style={{ paddingLeft: 16, marginTop: 4 }}>
                {day.activities?.map((act) => (
                  <div key={act.order_index} style={{ marginBottom: 4, color: '#555' }}>
                    <Text code>{act.time_slot || '--'}</Text>{' '}
                    <Text strong>{act.spot_name}</Text>
                    {act.transport && <Text type="secondary"> ({act.transport})</Text>}
                    {act.estimated_cost != null && <Tag color="orange" style={{ marginLeft: 8 }}>¥{act.estimated_cost}</Tag>}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </Card>
      );
    } catch {
      return <Card size="small" style={{ marginTop: 8, background: '#f6ffed' }}><pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{plan}</pre></Card>;
    }
  };

  return (
    <div style={{ display: 'flex', height: 'calc(100vh - 112px)' }}>
      {/* 左侧会话列表 */}
      <div style={{ width: 260, borderRight: '1px solid #f0f0f0', display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: 16 }}>
          <Button type="primary" icon={<PlusOutlined />} block onClick={handleNewSession}>
            新建对话
          </Button>
        </div>
        <div style={{ flex: 1, overflow: 'auto' }}>
          {loadingSessions ? (
            <div style={{ textAlign: 'center', padding: 24 }}><Spin /></div>
          ) : (
            <List
              dataSource={sessions}
              renderItem={(s) => (
                <List.Item
                  onClick={() => loadHistory(s.id)}
                  style={{
                    padding: '12px 16px',
                    cursor: 'pointer',
                    background: activeSession === s.id ? '#e6f4ff' : undefined,
                  }}
                >
                  <Text ellipsis style={{ width: '100%' }}>
                    {s.title || `对话 ${s.id}`}
                  </Text>
                </List.Item>
              )}
            />
          )}
        </div>
      </div>

      {/* 右侧消息区域 */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {!activeSession ? (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Empty description="选择或新建一个对话开始聊天" />
          </div>
        ) : (
          <>
            <div style={{ flex: 1, overflow: 'auto', padding: 24 }}>
              {messages.map((msg, i) => (
                <div
                  key={i}
                  style={{
                    display: 'flex',
                    justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                    marginBottom: 16,
                  }}
                >
                  <div style={{ maxWidth: '75%', display: 'flex', gap: 8, flexDirection: msg.role === 'user' ? 'row-reverse' : 'row' }}>
                    <div style={{
                      width: 36, height: 36, borderRadius: '50%', flexShrink: 0,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      background: msg.role === 'user' ? '#1677ff' : '#f0f0f0',
                      color: msg.role === 'user' ? '#fff' : '#666',
                    }}>
                      {msg.role === 'user' ? <UserOutlined /> : <RobotOutlined />}
                    </div>
                    <div style={{ minWidth: 0 }}>
                      {/* 思考过程 */}
                      {msg.thinking && (
                        <Collapse
                          size="small"
                          style={{ marginBottom: 8 }}
                          items={[{
                            key: 'thinking',
                            label: <span><BulbOutlined /> Agent 思考过程</span>,
                            children: <div style={{ fontSize: 13, color: '#888', whiteSpace: 'pre-wrap' }}>{msg.thinking}</div>,
                          }]}
                        />
                      )}

                      {/* 工具调用 */}
                      {msg.toolCalls && msg.toolCalls.length > 0 && (
                        <Collapse
                          size="small"
                          style={{ marginBottom: 8 }}
                          items={msg.toolCalls.map((tc, j) => ({
                            key: j,
                            label: toolNameMap[tc.name] || `🔧 ${tc.name}`,
                            children: <pre style={{ fontSize: 12, maxHeight: 200, overflow: 'auto', margin: 0, whiteSpace: 'pre-wrap' }}>{tc.result}</pre>,
                          }))}
                        />
                      )}

                      {/* 消息内容 */}
                      {msg.role === 'user' ? (
                        <div style={{
                          padding: '10px 16px',
                          borderRadius: 12,
                          background: '#1677ff',
                          color: '#fff',
                          whiteSpace: 'pre-wrap',
                          wordBreak: 'break-word',
                        }}>
                          {msg.content}
                        </div>
                      ) : (
                        <div style={{
                          padding: '10px 16px',
                          borderRadius: 12,
                          background: '#f5f5f5',
                          color: '#333',
                          wordBreak: 'break-word',
                        }}>
                          {msg.content ? (
                            <div className="markdown-body">
                              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                {msg.content}
                              </ReactMarkdown>
                            </div>
                          ) : (
                            streaming && i === messages.length - 1 ? <Spin size="small" /> : null
                          )}
                        </div>
                      )}

                      {/* 行程卡片 */}
                      {msg.tripPlan && renderTripPlan(msg.tripPlan)}
                    </div>
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
            <div style={{ padding: '16px 24px', borderTop: '1px solid #f0f0f0' }}>
              <Input.Search
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="输入您的旅行问题，例如：帮我规划一个北京三日游"
                enterButton={<Button type="primary" icon={<SendOutlined />} loading={streaming}>发送</Button>}
                onSearch={handleSend}
                size="large"
                disabled={streaming}
              />
            </div>
          </>
        )}
      </div>
    </div>
  );
}

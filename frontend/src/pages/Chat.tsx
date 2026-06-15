import { useState, useEffect, useRef, useCallback } from 'react';
import { Button, Input, List, Typography, Spin, Collapse, Card, Empty, Tag, message, Popconfirm } from 'antd';
import { PlusOutlined, SendOutlined, RobotOutlined, UserOutlined, BulbOutlined, SaveOutlined, DeleteOutlined } from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { createSession, getSessions, getHistory, sendMessage, deleteSession, type Session, type SSEEvent } from '@/api/chat';
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
  const tokenRafRef = useRef<number | null>(null);

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

  const handleDeleteSession = async (sessionId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await deleteSession(sessionId);
      setSessions((prev) => {
        const remaining = prev.filter((s) => s.id !== sessionId);
        if (activeSession === sessionId) {
          if (remaining.length > 0) {
            loadHistory(remaining[0].id);
          } else {
            setActiveSession(null);
            setMessages([]);
          }
        }
        return remaining;
      });
      message.success('会话已删除');
    } catch {
      message.error('删除失败');
    }
  };

  // 客户端备用：从文本中提取 TripPlan JSON（后端 extract_trip_plan 的纯 JS 实现）
  const extractTripPlanFromText = (text: string): string | null => {
    const patterns = [
      /```json\s*(\{[\s\S]*?\})\s*```/,
      /```\s*(\{"title"[\s\S]*?\})\s*```/,
      /(\{"title"[\s\S]*?\})\s*$/,
    ];
    for (const pattern of patterns) {
      const match = text.match(pattern);
      if (match) {
        try {
          JSON.parse(match[1]);
          return match[1];
        } catch {
          continue;
        }
      }
    }
    return null;
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
    let rawTextForExtraction = '';  // 后端返回的原始文本，含 TripPlan JSON，供兜底提取

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

    // 客户端兜底提取 + 最终落地
    const finalizeTripPlan = () => {
      if (!tripPlan) {
        // 优先从后端返回的原始文本提取
        if (rawTextForExtraction) {
          const extracted = extractTripPlanFromText(rawTextForExtraction);
          if (extracted) {
            tripPlan = extracted;
          }
        }
        // 最后尝试从清洗后的展示文本提取（备用）
        if (!tripPlan && assistantContent) {
          const extracted = extractTripPlanFromText(assistantContent);
          if (extracted) {
            tripPlan = extracted;
          }
        }
      }
      updateLastMessage();
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
            // 用 RAF 节流，避免每个 token chunk 都触发 ReactMarkdown 重解析
            if (tokenRafRef.current === null) {
              tokenRafRef.current = requestAnimationFrame(() => {
                updateLastMessage();
                tokenRafRef.current = null;
              });
            }
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
          case 'done':
            try {
              const doneData = JSON.parse(evt.data);
              // 自动生成的标题更新到会话列表
              if (doneData.title) {
                setSessions((prev) =>
                  prev.map((s) =>
                    s.id === activeSession ? { ...s, title: doneData.title } : s
                  )
                );
              }
              // 保存后端返回的原始文本，供兜底提取 TripPlan JSON
              if (doneData.raw_text) {
                rawTextForExtraction = String(doneData.raw_text);
              }
              // 用清洗后的展示文本（已去除 TripPlan JSON 代码块和中间推理步骤）替换累积内容
              if (doneData.text != null && doneData.text !== '') {
                assistantContent = String(doneData.text);
              }
              // 兜底：若后端未推送 trip_plan 事件，从原始文本中提取
              if (!tripPlan && rawTextForExtraction) {
                const extracted = extractTripPlanFromText(rawTextForExtraction);
                if (extracted) {
                  tripPlan = extracted;
                }
              }
              updateLastMessage();
            } catch { /* ignore */ }
            break;
        }
      });
    } finally {
      // 先结束 streaming 状态，确保最终渲染走 ReactMarkdown
      setStreaming(false);
      // 刷新最后一个 RAF 中待渲染的 token
      if (tokenRafRef.current !== null) {
        cancelAnimationFrame(tokenRafRef.current);
        tokenRafRef.current = null;
      }
      // 最终落地：若后端未推送 trip_plan，从消息内容中提取
      finalizeTripPlan();
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
          style={{ marginTop: 12, background: '#FDF0E8', borderColor: '#F0D5C0', borderRadius: 12 }}
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
      <div style={{
        width: 270,
        borderRight: '1px solid #F0EAE2',
        display: 'flex',
        flexDirection: 'column',
        background: '#FAF7F2',
      }}>
        <div style={{ padding: '16px 14px' }}>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            block
            onClick={handleNewSession}
            style={{
              height: 42,
              borderRadius: 10,
              fontSize: 14,
              fontWeight: 500,
              background: 'linear-gradient(135deg, #C25430 0%, #9E3F20 100%)',
              border: 'none',
              boxShadow: '0 2px 8px rgba(194,84,48,0.2)',
            }}
          >
            新建对话
          </Button>
        </div>
        <div style={{ flex: 1, overflow: 'auto', padding: '0 8px' }}>
          {loadingSessions ? (
            <div style={{ textAlign: 'center', padding: 24 }}><Spin /></div>
          ) : (
            <List
              dataSource={sessions}
              split={false}
              renderItem={(s) => (
                <List.Item
                  onClick={() => loadHistory(s.id)}
                  style={{
                    padding: '10px 12px',
                    cursor: 'pointer',
                    background: activeSession === s.id ? '#FDF0E8' : 'transparent',
                    borderRadius: 10,
                    marginBottom: 4,
                    border: 'none',
                    transition: 'background 200ms ease',
                  }}
                >
                  <Text
                    ellipsis
                    style={{
                      flex: 1,
                      minWidth: 0,
                      fontSize: 14,
                      color: activeSession === s.id ? '#C25430' : '#2C2420',
                      fontWeight: activeSession === s.id ? 500 : 400,
                    }}
                  >
                    {s.title || `对话 ${s.id}`}
                  </Text>
                  <Popconfirm
                    title="确定删除该对话？"
                    onConfirm={(e) => handleDeleteSession(s.id, e as unknown as React.MouseEvent)}
                    onCancel={(e) => (e as unknown as React.MouseEvent).stopPropagation()}
                    okText="删除"
                    cancelText="取消"
                  >
                    <Button
                      type="text"
                      size="small"
                      danger
                      icon={<DeleteOutlined />}
                      onClick={(e) => e.stopPropagation()}
                      style={{ flexShrink: 0, marginLeft: 4, opacity: 0.5 }}
                    />
                  </Popconfirm>
                </List.Item>
              )}
            />
          )}
        </div>
      </div>

      {/* 右侧消息区域 */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', background: '#FFF' }}>
        {!activeSession ? (
          <div style={{
            flex: 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: '#FAF7F2',
          }}>
            <Empty
              description={
                <span style={{ color: '#9B8E85', fontSize: 15 }}>
                  选择或新建一个对话开始聊天
                </span>
              }
            />
          </div>
        ) : (
          <>
            <div style={{ flex: 1, overflow: 'auto', padding: 24, background: '#FAF7F2' }}>
              {messages.map((msg, i) => (
                <div
                  key={i}
                  style={{
                    display: 'flex',
                    justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                    marginBottom: 20,
                  }}
                >
                  <div style={{ maxWidth: '75%', display: 'flex', gap: 10, flexDirection: msg.role === 'user' ? 'row-reverse' : 'row' }}>
                    <div style={{
                      width: 36, height: 36, borderRadius: 12, flexShrink: 0,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      background: msg.role === 'user' ? 'linear-gradient(135deg, #C25430, #9E3F20)' : '#FDF0E8',
                      color: msg.role === 'user' ? '#FFF' : '#C25430',
                      fontSize: 15,
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
                          borderRadius: 14,
                          background: 'linear-gradient(135deg, #C25430 0%, #B04A28 100%)',
                          color: '#FFF',
                          whiteSpace: 'pre-wrap',
                          wordBreak: 'break-word',
                          boxShadow: '0 2px 8px rgba(194,84,48,0.2)',
                          fontSize: 14,
                          lineHeight: 1.7,
                        }}>
                          {msg.content}
                        </div>
                      ) : (
                        <div style={{
                          padding: '12px 18px',
                          borderRadius: 14,
                          background: '#F9F6F1',
                          color: '#2C2420',
                          wordBreak: 'break-word',
                          border: '1px solid #F0EAE2',
                          fontSize: 14,
                          lineHeight: 1.7,
                        }}>
                          {msg.content ? (
                            streaming && i === messages.length - 1 ? (
                              /* 流式传输期间用纯文本，ReactMarkdown 频繁重解析会导致空格和渲染碎片 */
                              <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.8 }}>
                                {msg.content}
                              </div>
                            ) : (
                              <div className="markdown-body">
                                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                  {msg.content}
                                </ReactMarkdown>
                              </div>
                            )
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
            <div style={{
              padding: '16px 24px',
              borderTop: '1px solid #F0EAE2',
              display: 'flex',
              gap: 12,
              alignItems: 'flex-end',
              background: '#FFF',
            }}>
              <Input.TextArea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="输入您的旅行问题（Enter 发送，Shift+Enter 换行）"
                autoSize={{ minRows: 1, maxRows: 4 }}
                disabled={streaming}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    if (input.trim() && !streaming) handleSend();
                  }
                }}
                style={{
                  flex: 1,
                  borderRadius: 12,
                  borderColor: '#F0EAE2',
                  fontSize: 14,
                }}
              />
              <Button
                type="primary"
                icon={<SendOutlined />}
                loading={streaming}
                onClick={handleSend}
                disabled={!input.trim() || streaming}
                style={{
                  height: 42,
                  borderRadius: 10,
                  background: 'linear-gradient(135deg, #C25430, #9E3F20)',
                  border: 'none',
                  boxShadow: '0 2px 8px rgba(194,84,48,0.25)',
                  fontWeight: 500,
                }}
              >
                发送
              </Button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

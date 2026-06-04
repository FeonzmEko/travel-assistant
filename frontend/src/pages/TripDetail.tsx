import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Typography, Timeline, Card, Spin, Button, Statistic, Row, Col, Empty, Tag, message } from 'antd';
import { ArrowLeftOutlined, DollarOutlined, CalendarOutlined, EnvironmentOutlined, FilePdfOutlined } from '@ant-design/icons';
import { getTrip, exportTripPdf } from '@/api/trips';

const { Title, Text } = Typography;

interface TripActivityData {
  id: number;
  order_index: number;
  spot_name: string;
  time_slot?: string;
  transport?: string;
  notes?: string;
  estimated_cost?: number;
}

interface TripDayData {
  id: number;
  day_index: number;
  date: string;
  weather?: string;
  activities: TripActivityData[];
}

interface TripData {
  id: number;
  title: string;
  destination: string;
  start_date: string;
  end_date: string;
  budget_total?: number;
  budget_breakdown?: string;
  days: TripDayData[];
}

export default function TripDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [trip, setTrip] = useState<TripData | null>(null);
  const [loading, setLoading] = useState(true);
  const [messageApi, contextHolder] = message.useMessage();

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    getTrip(Number(id))
      .then((res) => setTrip(res.data as TripData))
      .catch(() => messageApi.error('获取行程详情失败'))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div style={{ padding: 48, textAlign: 'center' }}><Spin size="large" /></div>;
  if (!trip) return <Empty description="行程不存在" />;

  const totalCost = trip.days.reduce((sum, day) =>
    sum + day.activities.reduce((s, a) => s + (a.estimated_cost ?? 0), 0), 0);

  return (
    <div style={{ padding: 24 }}>
      {contextHolder}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/trips')}>返回列表</Button>
        <Button type="primary" icon={<FilePdfOutlined />} onClick={() => exportTripPdf(trip.id)}>导出 PDF</Button>
      </div>

      <Title level={3}>{trip.title}</Title>

      <Row gutter={24} style={{ marginBottom: 24 }}>
        <Col><Statistic title="目的地" value={trip.destination} prefix={<EnvironmentOutlined />} /></Col>
        <Col><Statistic title="日期" value={`${trip.start_date} ~ ${trip.end_date}`} prefix={<CalendarOutlined />} /></Col>
        <Col><Statistic title="预估总费用" value={trip.budget_total ?? totalCost} prefix={<DollarOutlined />} suffix="元" /></Col>
      </Row>

      {trip.days.length > 0 ? (
        trip.days
          .sort((a, b) => a.day_index - b.day_index)
          .map((day) => (
            <Card
              key={day.id}
              title={
                <span>
                  第 {day.day_index} 天 · {day.date}
                  {day.weather && <Tag color="blue" style={{ marginLeft: 8 }}>{day.weather}</Tag>}
                </span>
              }
              style={{ marginBottom: 16 }}
            >
              <Timeline
                items={day.activities
                  .sort((a, b) => a.order_index - b.order_index)
                  .map((act) => ({
                    key: act.id,
                    children: (
                      <div>
                        <Text strong>{act.time_slot && `${act.time_slot} · `}{act.spot_name}</Text>
                        {act.transport && <div style={{ color: '#888' }}>🚗 {act.transport}</div>}
                        {act.notes && <div style={{ color: '#666', marginTop: 4 }}>{act.notes}</div>}
                        {act.estimated_cost != null && act.estimated_cost > 0 && (
                          <Tag color="orange" style={{ marginTop: 4 }}>¥{act.estimated_cost}</Tag>
                        )}
                      </div>
                    ),
                  }))}
              />
            </Card>
          ))
      ) : (
        <Empty description="暂无详细行程安排" />
      )}
    </div>
  );
}

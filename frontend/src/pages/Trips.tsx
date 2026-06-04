import { useState, useEffect } from 'react';
import { Card, Row, Col, Button, Empty, Spin, Popconfirm, Typography, message } from 'antd';
import { DeleteOutlined, EyeOutlined, FilePdfOutlined, EnvironmentOutlined, CalendarOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { getTrips, deleteTrip, exportTripPdf, type TripSummary } from '@/api/trips';

const { Text } = Typography;

export default function Trips() {
  const [items, setItems] = useState<TripSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const [messageApi, contextHolder] = message.useMessage();

  const fetchTrips = async () => {
    setLoading(true);
    try {
      const res = await getTrips();
      setItems(res.data.items);
    } catch {
      messageApi.error('获取行程失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchTrips(); }, []);

  const handleDelete = async (id: number) => {
    try {
      await deleteTrip(id);
      messageApi.success('删除成功');
      fetchTrips();
    } catch {
      messageApi.error('删除失败');
    }
  };

  const handleExport = async (id: number) => {
    try {
      await exportTripPdf(id);
      messageApi.success('导出成功');
    } catch {
      messageApi.error('导出失败');
    }
  };

  return (
    <div style={{ padding: 24 }}>
      {contextHolder}
      <Spin spinning={loading}>
        {items.length === 0 && !loading ? (
          <Empty description="暂无行程，去对话页面让 AI 为你规划吧！" />
        ) : (
          <Row gutter={[16, 16]}>
            {items.map((trip) => (
              <Col xs={24} sm={12} lg={8} key={trip.id}>
                <Card
                  hoverable
                  actions={[
                    <Button type="link" icon={<EyeOutlined />} onClick={() => navigate(`/trips/${trip.id}`)} key="view">详情</Button>,
                    <Button type="link" icon={<FilePdfOutlined />} onClick={() => handleExport(trip.id)} key="export">导出</Button>,
                    <Popconfirm title="确定删除此行程？" onConfirm={() => handleDelete(trip.id)} key="delete">
                      <Button type="link" danger icon={<DeleteOutlined />}>删除</Button>
                    </Popconfirm>,
                  ]}
                >
                  <Card.Meta
                    title={trip.title}
                    description={
                      <>
                        {trip.destination && <div><EnvironmentOutlined /> {trip.destination}</div>}
                        {trip.start_date && trip.end_date && (
                          <div style={{ marginTop: 4 }}>
                            <CalendarOutlined /> <Text type="secondary">{trip.start_date} ~ {trip.end_date}</Text>
                          </div>
                        )}
                      </>
                    }
                  />
                </Card>
              </Col>
            ))}
          </Row>
        )}
      </Spin>
    </div>
  );
}

import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Typography, Spin, Button, Descriptions, Tag, Rate, Empty, Card, message } from 'antd';
import { ArrowLeftOutlined, EnvironmentOutlined, PhoneOutlined, ClockCircleOutlined } from '@ant-design/icons';
import { getSpot, type Spot } from '@/api/spots';
import AMapView from '@/components/AMapView';

const { Title, Paragraph } = Typography;

export default function SpotDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [spot, setSpot] = useState<Spot | null>(null);
  const [loading, setLoading] = useState(true);
  const [messageApi, contextHolder] = message.useMessage();

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    getSpot(id)
      .then((res) => setSpot(res.data))
      .catch(() => messageApi.error('获取景点详情失败'))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div style={{ padding: 48, textAlign: 'center' }}><Spin size="large" /></div>;
  if (!spot) return <Empty description="景点不存在" />;

  const mapSpots = spot.longitude && spot.latitude
    ? [{ name: spot.name, longitude: spot.longitude, latitude: spot.latitude }]
    : [];

  return (
    <div style={{ padding: 24 }}>
      {contextHolder}
      <Button
        icon={<ArrowLeftOutlined />}
        onClick={() => navigate('/spots')}
        style={{ marginBottom: 16 }}
      >
        返回搜索
      </Button>

      <Card>
        {spot.image_url && (
          <img
            src={spot.image_url}
            alt={spot.name}
            style={{ width: '100%', maxHeight: 400, objectFit: 'cover', borderRadius: 8, marginBottom: 24 }}
          />
        )}

        <Title level={3}>{spot.name}</Title>

        <Descriptions column={{ xs: 1, sm: 2 }} style={{ marginBottom: 24 }}>
          {spot.city && (
            <Descriptions.Item label={<span><EnvironmentOutlined /> 所在城市</span>}>
              {spot.city}
            </Descriptions.Item>
          )}
          {spot.address && (
            <Descriptions.Item label={<span><EnvironmentOutlined /> 详细地址</span>}>
              {spot.address}
            </Descriptions.Item>
          )}
          {spot.type && (
            <Descriptions.Item label="类型">
              {spot.type.split(';').map((t) => (
                <Tag key={t} color="volcano">{t}</Tag>
              ))}
            </Descriptions.Item>
          )}
          {spot.rating != null && (
            <Descriptions.Item label="评分">
              <Rate disabled value={spot.rating} allowHalf />
              <span style={{ marginLeft: 8 }}>{spot.rating} 分</span>
            </Descriptions.Item>
          )}
          {spot.open_time && (
            <Descriptions.Item label={<span><ClockCircleOutlined /> 开放时间</span>}>
              {spot.open_time}
            </Descriptions.Item>
          )}
          {spot.ticket_price != null && (
            <Descriptions.Item label="门票价格">
              <Tag color="orange">¥{spot.ticket_price}</Tag>
            </Descriptions.Item>
          )}
          {spot.tel && (
            <Descriptions.Item label={<span><PhoneOutlined /> 联系电话</span>}>
              {spot.tel}
            </Descriptions.Item>
          )}
        </Descriptions>

        {spot.description && (
          <div style={{ marginBottom: 24 }}>
            <Title level={5}>景点介绍</Title>
            <Paragraph>{spot.description}</Paragraph>
          </div>
        )}

        {mapSpots.length > 0 && (
          <div>
            <Title level={5}>地图位置</Title>
            <AMapView
              spots={mapSpots}
              style={{ width: '100%', height: 350, borderRadius: 8 }}
              zoom={15}
            />
          </div>
        )}
      </Card>
    </div>
  );
}

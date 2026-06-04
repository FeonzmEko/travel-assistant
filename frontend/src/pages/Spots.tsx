import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Form, Input, Select, Button, Card, Row, Col, Pagination, Rate, Empty, Spin, message } from 'antd';
import { SearchOutlined, EnvironmentOutlined } from '@ant-design/icons';
import { searchSpots, type Spot } from '@/api/spots';
import AMapView, { type MapSpot } from '@/components/AMapView';

const { Meta } = Card;

const spotTypes = [
  { value: '', label: '全部类型' },
  { value: '景点', label: '景点' },
  { value: '美食', label: '美食' },
  { value: '酒店', label: '酒店' },
  { value: '购物', label: '购物' },
];

export default function Spots() {
  const navigate = useNavigate();
  const [items, setItems] = useState<Spot[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [searchParams, setSearchParams] = useState<{ keyword?: string; city?: string; type?: string }>({});
  const [messageApi, contextHolder] = message.useMessage();

  const doSearch = async (params: typeof searchParams, p = 1) => {
    setLoading(true);
    try {
      const res = await searchSpots({ ...params, page: p, size: 12 });
      setItems(res.data.items);
      setTotal(res.data.total);
      setPage(p);
      setSearchParams(params);
    } catch {
      messageApi.error('搜索失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: 24 }}>
      {contextHolder}
      <Form layout="inline" onFinish={(v: typeof searchParams) => doSearch(v)} style={{ marginBottom: 24, flexWrap: 'wrap', gap: 8 }}>
        <Form.Item name="keyword">
          <Input placeholder="关键词" prefix={<SearchOutlined />} allowClear />
        </Form.Item>
        <Form.Item name="city">
          <Input placeholder="城市" prefix={<EnvironmentOutlined />} allowClear />
        </Form.Item>
        <Form.Item name="type">
          <Select placeholder="类型" options={spotTypes} style={{ width: 120 }} allowClear />
        </Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit" icon={<SearchOutlined />}>搜索</Button>
        </Form.Item>
      </Form>

      {items.length > 0 && items.some((s) => s.latitude && s.longitude) && (
        <div style={{ marginBottom: 24 }}>
          <AMapView
            spots={items.filter((s): s is Spot & { latitude: number; longitude: number } => !!(s.latitude && s.longitude)).map((s) => ({
              name: s.name,
              longitude: s.longitude,
              latitude: s.latitude,
            } as MapSpot))}
            style={{ width: '100%', height: 300, borderRadius: 8 }}
            onSpotClick={(ms) => {
              const found = items.find((s) => s.name === ms.name);
              if (found) navigate(`/spots/${found.id}`);
            }}
          />
        </div>
      )}

      <Spin spinning={loading}>
        {items.length === 0 && !loading ? (
          <Empty description="搜索景点、美食、酒店..." />
        ) : (
          <>
            <Row gutter={[16, 16]}>
              {items.map((spot) => (
                <Col xs={24} sm={12} md={8} lg={6} key={spot.id}>
                  <Card
                    hoverable
                    cover={
                      spot.image_url
                        ? <img alt={spot.name} src={spot.image_url} style={{ height: 180, objectFit: 'cover' }} />
                        : <div style={{ height: 180, background: '#f0f5ff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 48 }}>🏞️</div>
                    }
                    onClick={() => navigate(`/spots/${spot.id}`)}
                  >
                    <Meta
                      title={spot.name}
                      description={
                        <>
                          {spot.city && <div><EnvironmentOutlined /> {spot.city}</div>}
                          {spot.rating != null && <Rate disabled defaultValue={spot.rating} allowHalf style={{ fontSize: 14 }} />}
                        </>
                      }
                    />
                  </Card>
                </Col>
              ))}
            </Row>
            <div style={{ marginTop: 24, textAlign: 'center' }}>
              <Pagination current={page} total={total} pageSize={12} onChange={(p) => doSearch(searchParams, p)} showTotal={(t) => `共 ${t} 条`} />
            </div>
          </>
        )}
      </Spin>

    </div>
  );
}

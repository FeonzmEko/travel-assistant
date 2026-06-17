import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Form, Input, Select, Button, Card, Row, Col, Pagination, Rate, Tag, Empty, Spin, message } from 'antd';
import { SearchOutlined, EnvironmentOutlined } from '@ant-design/icons';
import { searchSpots, type Spot } from '@/api/spots';
import AMapView, { type MapSpot } from '@/components/AMapView';
import SpotImage from '@/components/SpotImage';

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
  const [urlParams, setUrlParams] = useSearchParams();

  const urlKeyword = urlParams.get('keyword') || '';
  const urlCity = urlParams.get('city') || '';
  const urlType = urlParams.get('type') || '';
  const urlPage = parseInt(urlParams.get('page') || '1', 10);

  const [items, setItems] = useState<Spot[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(urlPage);
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();
  const [messageApi, contextHolder] = message.useMessage();

  const doSearch = useCallback(async (params: { keyword?: string; city?: string; type?: string }, p = 1) => {
    setLoading(true);
    const q: Record<string, string> = {};
    if (params.keyword) q.keyword = params.keyword;
    if (params.city) q.city = params.city;
    if (params.type) q.type = params.type;
    q.page = String(p);
    setUrlParams(q, { replace: true });

    try {
      const res = await searchSpots({ ...params, page: p, size: 12 });
      setItems(res.data.items);
      setTotal(res.data.total);
      setPage(p);
    } catch {
      messageApi.error('搜索失败');
    } finally {
      setLoading(false);
    }
  }, [setUrlParams, messageApi]);

  // 页面挂载时，如果 URL 有搜索参数则自动搜索
  useEffect(() => {
    if (urlKeyword || urlCity || urlType) {
      form.setFieldsValue({ keyword: urlKeyword, city: urlCity, type: urlType || undefined });
      doSearch({ keyword: urlKeyword, city: urlCity, type: urlType || undefined }, urlPage);
    }
  }, []);

  return (
    <div style={{ padding: 24 }}>
      {contextHolder}
      <Form
        form={form}
        layout="inline"
        initialValues={{ keyword: urlKeyword, city: urlCity, type: urlType || undefined }}
        onFinish={(v: { keyword?: string; city?: string; type?: string }) => doSearch(v)}
        style={{ marginBottom: 24, flexWrap: 'wrap', gap: 8 }}
      >
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
                      <div style={{ position: 'relative' }}>
                        <SpotImage
                          src={spot.image_url}
                          seed={String(spot.id)}
                          name={spot.name}
                          style={{ height: 180 }}
                        />
                        {spot.type && (
                          <Tag
                            color="volcano"
                            style={{ position: 'absolute', top: 8, left: 8, margin: 0 }}
                          >
                            {spot.type.split(';')[0]}
                          </Tag>
                        )}
                      </div>
                    }
                    onClick={() => navigate(`/spots/${spot.id}`)}
                  >
                    <Meta
                      title={spot.name}
                      description={
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                          {(spot.city || spot.address) && (
                            <span
                              style={{ color: '#8c8c8c', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}
                              title={spot.address || spot.city}
                            >
                              <EnvironmentOutlined /> {spot.city}{spot.address ? ` · ${spot.address}` : ''}
                            </span>
                          )}
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            {spot.rating != null ? (
                              <span>
                                <Rate disabled defaultValue={spot.rating} allowHalf style={{ fontSize: 12 }} />
                                <span style={{ marginLeft: 6, color: '#fa8c16' }}>{spot.rating}</span>
                              </span>
                            ) : (
                              <span />
                            )}
                            {spot.ticket_price != null && (
                              <span style={{ color: '#C25430', fontWeight: 600 }}>
                                {spot.ticket_price > 0 ? `¥${spot.ticket_price}` : '免费'}
                              </span>
                            )}
                          </div>
                        </div>
                      }
                    />
                  </Card>
                </Col>
              ))}
            </Row>
            <div style={{ marginTop: 24, textAlign: 'center' }}>
              <Pagination current={page} total={total} pageSize={12} onChange={(p) => doSearch({ keyword: urlKeyword, city: urlCity, type: urlType || undefined }, p)} showTotal={(t) => `共 ${t} 条`} />
            </div>
          </>
        )}
      </Spin>

    </div>
  );
}

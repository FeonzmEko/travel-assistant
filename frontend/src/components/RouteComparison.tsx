import { Card, Table, Tag, Typography, Row, Col } from 'antd';
import { SwapOutlined, ClockCircleOutlined, DollarOutlined, EnvironmentOutlined } from '@ant-design/icons';

const { Text } = Typography;

export interface RouteOption {
  strategy: string;
  distance_km: number;
  duration_min: number;
  toll?: number;
  description?: string;
}

interface RouteComparisonProps {
  routes: RouteOption[];
  onSelect?: (route: RouteOption) => void;
  selectedIndex?: number;
  style?: React.CSSProperties;
}

const strategyMap: Record<string, { label: string; color: string }> = {
  '0': { label: '速度优先', color: 'green' },
  '1': { label: '费用优先', color: 'blue' },
  '2': { label: '距离优先', color: 'orange' },
  speed: { label: '速度优先', color: 'green' },
  cost: { label: '费用优先', color: 'blue' },
  distance: { label: '距离优先', color: 'orange' },
  '速度优先': { label: '速度优先', color: 'green' },
  '费用优先': { label: '费用优先', color: 'blue' },
  '距离优先': { label: '距离优先', color: 'orange' },
};

function formatDuration(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = Math.round(minutes % 60);
  if (h === 0) return `${m} 分钟`;
  return `${h} 小时 ${m} 分钟`;
}

export default function RouteComparison({ routes, onSelect, selectedIndex, style }: RouteComparisonProps) {
  if (!routes || routes.length === 0) return null;

  const columns = [
    {
      title: '路线方案',
      dataIndex: 'strategy',
      key: 'strategy',
      render: (val: string) => {
        const config = strategyMap[val] || { label: val, color: 'default' };
        return <Tag color={config.color}>{config.label}</Tag>;
      },
    },
    {
      title: '距离',
      dataIndex: 'distance_km',
      key: 'distance_km',
      render: (val: number) => (
        <span><EnvironmentOutlined /> {val.toFixed(1)} km</span>
      ),
      sorter: (a: RouteOption, b: RouteOption) => a.distance_km - b.distance_km,
    },
    {
      title: '预计时长',
      dataIndex: 'duration_min',
      key: 'duration_min',
      render: (val: number) => (
        <span><ClockCircleOutlined /> {formatDuration(val)}</span>
      ),
      sorter: (a: RouteOption, b: RouteOption) => a.duration_min - b.duration_min,
    },
    {
      title: '过路费',
      dataIndex: 'toll',
      key: 'toll',
      render: (val?: number) => val != null ? (
        <span><DollarOutlined /> ¥{val}</span>
      ) : '-',
    },
  ];

  return (
    <Card
      title={<span><SwapOutlined /> 路线对比</span>}
      size="small"
      style={{ marginBottom: 16, ...style }}
    >
      <Table
        dataSource={routes.map((r, i) => ({ ...r, key: i }))}
        columns={columns}
        pagination={false}
        size="small"
        onRow={(_, index) => ({
          onClick: () => onSelect && index !== undefined && onSelect(routes[index]),
          style: {
            cursor: onSelect ? 'pointer' : 'default',
            background: selectedIndex === index ? '#e6f4ff' : undefined,
          },
        })}
      />
      {routes.length > 1 && (
        <Row style={{ marginTop: 12 }}>
          <Col span={24}>
            <Text type="secondary">
              最快：{formatDuration(Math.min(...routes.map((r) => r.duration_min)))} |{' '}
              最短：{Math.min(...routes.map((r) => r.distance_km)).toFixed(1)} km
            </Text>
          </Col>
        </Row>
      )}
    </Card>
  );
}

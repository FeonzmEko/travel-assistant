import { Card, Typography, Progress, Row, Col, Statistic } from 'antd';
import {
  DollarOutlined,
  HomeOutlined,
  CoffeeOutlined,
  CarOutlined,
  IdcardOutlined,
  AppstoreOutlined,
} from '@ant-design/icons';

const { Text } = Typography;

interface BudgetItem {
  category: string;
  amount: number;
  color: string;
  icon: React.ReactNode;
}

interface BudgetBreakdownProps {
  breakdownStr?: string;
  total?: number;
  style?: React.CSSProperties;
}

const categoryConfig: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
  accommodation: { color: '#C25430', icon: <HomeOutlined />, label: '住宿' },
  meals: { color: '#4A8C5C', icon: <CoffeeOutlined />, label: '餐饮' },
  transport: { color: '#C8963E', icon: <CarOutlined />, label: '交通' },
  tickets: { color: '#D4744C', icon: <IdcardOutlined />, label: '门票' },
  other: { color: '#6B5F58', icon: <AppstoreOutlined />, label: '其他' },
  '住宿': { color: '#C25430', icon: <HomeOutlined />, label: '住宿' },
  '餐饮': { color: '#4A8C5C', icon: <CoffeeOutlined />, label: '餐饮' },
  '交通': { color: '#C8963E', icon: <CarOutlined />, label: '交通' },
  '门票': { color: '#D4744C', icon: <IdcardOutlined />, label: '门票' },
  '其他': { color: '#6B5F58', icon: <AppstoreOutlined />, label: '其他' },
};

function parseBreakdown(str: string): BudgetItem[] {
  const items: BudgetItem[] = [];
  const parts = str.split(',');
  for (const part of parts) {
    const match = part.trim().match(/(.+?)[：:]\s*(\d+(?:\.\d+)?)\s*元?/);
    if (match) {
      const key = match[1].trim();
      const amount = parseFloat(match[2]);
      const config = categoryConfig[key] || { color: '#6B5F58', icon: <AppstoreOutlined />, label: key };
      items.push({ category: config.label, amount, color: config.color, icon: config.icon });
    }
  }
  return items;
}

export default function BudgetBreakdown({ breakdownStr, total, style }: BudgetBreakdownProps) {
  if (!breakdownStr && !total) return null;

  const items = breakdownStr ? parseBreakdown(breakdownStr) : [];
  const computedTotal = total ?? items.reduce((sum, i) => sum + i.amount, 0);

  return (
    <Card
      title={<span><DollarOutlined style={{ color: '#C8963E' }} /> 预算明细</span>}
      size="small"
      style={{ marginBottom: 16, ...style }}
    >
      {computedTotal > 0 && (
        <div style={{ textAlign: 'center', marginBottom: 20 }}>
          <Statistic
            title="预估总费用"
            value={computedTotal}
            prefix="¥"
            valueStyle={{ color: '#C25430', fontSize: 28, fontWeight: 600 }}
          />
        </div>
      )}

      {items.length > 0 && (
        <Row gutter={[16, 12]}>
          {items.map((item) => {
            const percent = computedTotal > 0 ? (item.amount / computedTotal) * 100 : 0;
            return (
              <Col xs={12} sm={12} key={item.category}>
                <div style={{
                  padding: '10px 14px',
                  background: '#FAF7F2',
                  borderRadius: 10,
                  border: '1px solid #F0EAE2',
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, alignItems: 'center' }}>
                    <Text style={{ color: '#2C2420', fontSize: 13 }}>
                      <span style={{ color: item.color, marginRight: 4 }}>{item.icon}</span>
                      {' '}{item.category}
                    </Text>
                    <Text strong style={{ fontSize: 14, color: '#2C2420' }}>¥{item.amount}</Text>
                  </div>
                  <Progress
                    percent={Math.round(percent)}
                    size="small"
                    strokeColor={item.color}
                    trailColor="#F0EAE2"
                    showInfo={true}
                    format={(p) => `${p}%`}
                  />
                </div>
              </Col>
            );
          })}
        </Row>
      )}

      {items.length === 0 && computedTotal > 0 && (
        <Text type="secondary">暂无费用分类详情</Text>
      )}
    </Card>
  );
}

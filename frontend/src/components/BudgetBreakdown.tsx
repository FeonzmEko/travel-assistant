import { Card, Typography, Progress, Row, Col, Statistic } from 'antd';
import { DollarOutlined } from '@ant-design/icons';

const { Text } = Typography;

interface BudgetItem {
  category: string;
  amount: number;
  color: string;
  icon: string;
}

interface BudgetBreakdownProps {
  breakdownStr?: string;
  total?: number;
  style?: React.CSSProperties;
}

const categoryConfig: Record<string, { color: string; icon: string; label: string }> = {
  accommodation: { color: '#1677ff', icon: '🏨', label: '住宿' },
  meals: { color: '#52c41a', icon: '🍽️', label: '餐饮' },
  transport: { color: '#faad14', icon: '🚗', label: '交通' },
  tickets: { color: '#eb2f96', icon: '🎫', label: '门票' },
  other: { color: '#722ed1', icon: '📦', label: '其他' },
  '住宿': { color: '#1677ff', icon: '🏨', label: '住宿' },
  '餐饮': { color: '#52c41a', icon: '🍽️', label: '餐饮' },
  '交通': { color: '#faad14', icon: '🚗', label: '交通' },
  '门票': { color: '#eb2f96', icon: '🎫', label: '门票' },
  '其他': { color: '#722ed1', icon: '📦', label: '其他' },
};

function parseBreakdown(str: string): BudgetItem[] {
  const items: BudgetItem[] = [];
  const parts = str.split(',');
  for (const part of parts) {
    const match = part.trim().match(/(.+?)[：:]\s*(\d+(?:\.\d+)?)\s*元?/);
    if (match) {
      const key = match[1].trim();
      const amount = parseFloat(match[2]);
      const config = categoryConfig[key] || { color: '#999', icon: '💰', label: key };
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
      title={<span><DollarOutlined /> 预算明细</span>}
      size="small"
      style={{ marginBottom: 16, ...style }}
    >
      {computedTotal > 0 && (
        <div style={{ textAlign: 'center', marginBottom: 16 }}>
          <Statistic
            title="预估总费用"
            value={computedTotal}
            prefix="¥"
            valueStyle={{ color: '#1677ff', fontSize: 28 }}
          />
        </div>
      )}

      {items.length > 0 && (
        <Row gutter={[16, 12]}>
          {items.map((item) => {
            const percent = computedTotal > 0 ? (item.amount / computedTotal) * 100 : 0;
            return (
              <Col xs={12} sm={12} key={item.category}>
                <div style={{ padding: '8px 12px', background: '#fafafa', borderRadius: 8 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <Text>{item.icon} {item.category}</Text>
                    <Text strong>¥{item.amount}</Text>
                  </div>
                  <Progress
                    percent={Math.round(percent)}
                    size="small"
                    strokeColor={item.color}
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

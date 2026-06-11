import { Card, Tag, Typography, Row, Col } from 'antd';
import {
  CloudOutlined,
  SunOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';

const { Text } = Typography;

interface WeatherInfo {
  date: string;
  weather: string;
  temperature?: string;
}

interface WeatherCardProps {
  items: WeatherInfo[];
  style?: React.CSSProperties;
}

interface WeatherStyle {
  color: string;
  bg: string;
  textColor: string;
}

function getWeatherStyle(weather: string): WeatherStyle {
  if (weather.includes('暴雨') || weather.includes('大雨')) return { color: '#1D5652', bg: '#E8F5F4', textColor: '#1D5652' };
  if (weather.includes('雨') || weather.includes('雷')) return { color: '#2C7873', bg: '#E8F5F4', textColor: '#2C7873' };
  if (weather.includes('雪')) return { color: '#4A9D97', bg: '#E8F5F4', textColor: '#4A9D97' };
  if (weather.includes('多云') || weather.includes('阴')) return { color: '#9B8E85', bg: '#F2EDE5', textColor: '#6B5F58' };
  if (weather.includes('晴')) return { color: '#C8963E', bg: '#FDF5E6', textColor: '#C8963E' };
  return { color: '#6B5F58', bg: '#F2EDE5', textColor: '#6B5F58' };
}

function getWeatherLabel(weather: string): string {
  if (weather.includes('晴')) return '晴';
  if (weather.includes('多云')) return '多云';
  if (weather.includes('阴')) return '阴天';
  if (weather.includes('暴雨')) return '暴雨';
  if (weather.includes('大雨')) return '大雨';
  if (weather.includes('中雨')) return '中雨';
  if (weather.includes('小雨') || weather.includes('雨')) return '小雨';
  if (weather.includes('雷')) return '雷雨';
  if (weather.includes('雪')) return '降雪';
  if (weather.includes('雾')) return '雾';
  return weather;
}

export default function WeatherCard({ items, style }: WeatherCardProps) {
  if (!items || items.length === 0) return null;

  return (
    <Card
      title={<span><CloudOutlined style={{ color: '#2C7873' }} /> 天气预报</span>}
      size="small"
      style={{ marginBottom: 16, ...style }}
    >
      <Row gutter={[12, 12]}>
        {items.map((item) => {
          const ws = getWeatherStyle(item.weather);
          const label = getWeatherLabel(item.weather);
          return (
            <Col xs={12} sm={8} md={6} key={item.date}>
              <div style={{
                textAlign: 'center',
                padding: '14px 10px',
                background: ws.bg,
                borderRadius: 10,
                border: `1px solid ${ws.color}15`,
              }}>
                {item.weather.includes('雷') || item.weather.includes('雨') ? (
                  <ThunderboltOutlined style={{ fontSize: 22, color: ws.color, marginBottom: 4 }} />
                ) : (
                  <SunOutlined style={{ fontSize: 22, color: ws.color, marginBottom: 4 }} />
                )}
                <div style={{ fontSize: 12, color: '#9B8E85', marginTop: 2 }}>{item.date}</div>
                <Tag
                  style={{
                    marginTop: 6,
                    color: ws.textColor,
                    borderColor: ws.color + '40',
                    background: ws.bg,
                    borderRadius: 6,
                    fontWeight: 500,
                  }}
                >
                  {label}
                </Tag>
                {item.temperature && (
                  <Text style={{ fontSize: 12, color: '#6B5F58', display: 'block', marginTop: 4 }}>
                    {item.temperature}
                  </Text>
                )}
              </div>
            </Col>
          );
        })}
      </Row>
    </Card>
  );
}

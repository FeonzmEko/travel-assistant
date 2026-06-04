import { Card, Tag, Typography, Row, Col } from 'antd';
import { CloudOutlined } from '@ant-design/icons';

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

const weatherIconMap: Record<string, string> = {
  '晴': '☀️',
  '多云': '⛅',
  '阴': '☁️',
  '小雨': '🌦️',
  '中雨': '🌧️',
  '大雨': '⛈️',
  '暴雨': '🌊',
  '雷阵雨': '⛈️',
  '雪': '❄️',
  '小雪': '🌨️',
  '雾': '🌫️',
};

function getWeatherIcon(weather: string): string {
  for (const [key, icon] of Object.entries(weatherIconMap)) {
    if (weather.includes(key)) return icon;
  }
  return '🌤️';
}

function getWeatherColor(weather: string): string {
  if (weather.includes('雨') || weather.includes('雷')) return 'blue';
  if (weather.includes('雪')) return 'cyan';
  if (weather.includes('晴')) return 'orange';
  if (weather.includes('多云')) return 'geekblue';
  return 'default';
}

export default function WeatherCard({ items, style }: WeatherCardProps) {
  if (!items || items.length === 0) return null;

  return (
    <Card
      title={<span><CloudOutlined /> 天气预报</span>}
      size="small"
      style={{ marginBottom: 16, ...style }}
    >
      <Row gutter={[12, 12]}>
        {items.map((item) => (
          <Col xs={12} sm={8} md={6} key={item.date}>
            <div style={{
              textAlign: 'center',
              padding: '12px 8px',
              background: '#fafafa',
              borderRadius: 8,
            }}>
              <div style={{ fontSize: 24, marginBottom: 4 }}>
                {getWeatherIcon(item.weather)}
              </div>
              <Text type="secondary" style={{ fontSize: 12 }}>{item.date}</Text>
              <div>
                <Tag color={getWeatherColor(item.weather)} style={{ marginTop: 4 }}>
                  {item.weather}
                </Tag>
              </div>
              {item.temperature && (
                <Text style={{ fontSize: 12 }}>{item.temperature}</Text>
              )}
            </div>
          </Col>
        ))}
      </Row>
    </Card>
  );
}

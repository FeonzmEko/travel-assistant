import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { AuthProvider } from '@/store/AuthContext';
import AppRouter from '@/router';

export default function App() {
  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: '#C25430',
          colorSuccess: '#4A8C5C',
          colorWarning: '#D4943A',
          colorError: '#C04040',
          colorInfo: '#2C7873',
          colorTextBase: '#2C2420',
          colorBgBase: '#FFFFFF',
          colorBgContainer: '#FFFFFF',
          colorBgLayout: '#FAF7F2',
          colorBorder: '#E8DFD5',
          colorBorderSecondary: '#F0EAE2',
          borderRadius: 8,
          fontFamily:
            "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif",
          fontSize: 14,
          controlHeight: 38,
          lineHeight: 1.6,
        },
        components: {
          Menu: {
            itemBg: 'transparent',
            itemSelectedBg: '#FDF0E8',
            itemSelectedColor: '#C25430',
            itemHoverBg: '#F9F6F1',
            itemColor: '#6B5F58',
            itemBorderRadius: 8,
          },
          Button: {
            primaryShadow: '0 2px 8px rgba(194, 84, 48, 0.2)',
            defaultShadow: 'none',
            borderRadius: 8,
          },
          Card: {
            borderRadius: 12,
            padding: 20,
          },
          Input: {
            activeBorderColor: '#C25430',
            hoverBorderColor: '#D4744C',
            borderRadius: 8,
          },
          Table: {
            headerBg: '#FAF7F2',
            headerColor: '#6B5F58',
            rowHoverBg: '#FDF0E8',
            borderColor: '#F0EAE2',
          },
          Collapse: {
            contentPadding: '12px 16px',
            headerPadding: '10px 16px',
          },
          Tag: {
            borderRadius: 6,
          },
        },
      }}
    >
      <AuthProvider>
        <AppRouter />
      </AuthProvider>
    </ConfigProvider>
  );
}

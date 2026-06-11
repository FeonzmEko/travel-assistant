import { useState } from 'react';
import { Outlet, useNavigate, useLocation, Navigate } from 'react-router-dom';
import { Layout, Menu, Button, Avatar, Dropdown, Spin } from 'antd';
import {
  MessageOutlined,
  SearchOutlined,
  ScheduleOutlined,
  UserOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  GlobalOutlined,
} from '@ant-design/icons';
import { useAuth } from '@/store/AuthContext';

const { Header, Sider, Content } = Layout;

const menuItems = [
  { key: '/chat', icon: <MessageOutlined />, label: '智能对话' },
  { key: '/spots', icon: <SearchOutlined />, label: '景点搜索' },
  { key: '/trips', icon: <ScheduleOutlined />, label: '我的行程' },
  { key: '/profile', icon: <UserOutlined />, label: '个人中心' },
];

export default function MainLayout() {
  const { token, user, loading, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', background: '#FAF7F2' }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      {/* ── 侧边栏 ── */}
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        width={240}
        style={{
          background: '#FFF',
          borderRight: '1px solid #F0EAE2',
          boxShadow: '1px 0 8px rgba(44,36,32,0.04)',
        }}
      >
        {/* Logo 区域 */}
        <div style={{
          height: 68,
          display: 'flex',
          alignItems: 'center',
          justifyContent: collapsed ? 'center' : 'flex-start',
          padding: collapsed ? 0 : '0 20px',
          borderBottom: '1px solid #F0EAE2',
          gap: 10,
        }}>
          <div style={{
            width: 36,
            height: 36,
            borderRadius: 10,
            background: 'linear-gradient(135deg, #C25430 0%, #9E3F20 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}>
            <GlobalOutlined style={{ color: '#FFF', fontSize: 18 }} />
          </div>
          {!collapsed && (
            <span style={{
              fontFamily: "Georgia, 'Noto Serif SC', serif",
              fontWeight: 700,
              fontSize: 18,
              color: '#2C2420',
              letterSpacing: '0.02em',
            }}>
              旅 行 助 手
            </span>
          )}
        </div>

        <Menu
          mode="inline"
          selectedKeys={[location.pathname.startsWith('/spots') ? '/spots' : location.pathname.startsWith('/trips') ? '/trips' : location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{
            background: 'transparent',
            borderInlineEnd: 'none',
            padding: '8px 10px',
            marginTop: 4,
          }}
        />
      </Sider>

      <Layout>
        {/* ── 顶栏 ── */}
        <Header style={{
          background: '#FFF',
          padding: '0 24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid #F0EAE2',
          height: 56,
          boxShadow: '0 1px 4px rgba(44,36,32,0.03)',
        }}>
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
            style={{ color: '#6B5F58' }}
          />
          <Dropdown
            menu={{
              items: [
                {
                  key: 'profile',
                  icon: <UserOutlined />,
                  label: '个人中心',
                  onClick: () => navigate('/profile'),
                },
                {
                  key: 'logout',
                  icon: <LogoutOutlined />,
                  label: '退出登录',
                  onClick: () => {
                    logout();
                    navigate('/login');
                  },
                },
              ],
            }}
          >
            <div style={{
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '4px 12px',
              borderRadius: 8,
              transition: 'background 200ms ease',
            }}>
              <Avatar
                size={32}
                icon={<UserOutlined />}
                style={{ background: '#C25430', flexShrink: 0 }}
              />
              <span style={{ fontSize: 14, color: '#2C2420', fontWeight: 500 }}>
                {user?.username}
              </span>
            </div>
          </Dropdown>
        </Header>

        {/* ── 内容区 ── */}
        <Content style={{
          margin: 20,
          background: '#FFF',
          borderRadius: 14,
          overflow: 'auto',
          minHeight: 'calc(100vh - 96px)',
          boxShadow: '0 1px 6px rgba(44,36,32,0.04)',
        }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}

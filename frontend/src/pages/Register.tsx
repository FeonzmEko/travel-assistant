import { useState } from 'react';
import { Form, Input, Button, message, Typography } from 'antd';
import { UserOutlined, LockOutlined, MailOutlined, GlobalOutlined } from '@ant-design/icons';
import { useNavigate, Link } from 'react-router-dom';
import { register } from '@/api/auth';

const { Title, Text } = Typography;

export default function Register() {
  const navigate = useNavigate();
  const [messageApi, contextHolder] = message.useMessage();
  const [submitting, setSubmitting] = useState(false);

  const onFinish = async (values: { username: string; password: string; email: string }) => {
    setSubmitting(true);
    try {
      await register(values);
      messageApi.success('注册成功，请登录');
      navigate('/login');
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail;
      messageApi.error(detail || '注册失败');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: '#FAF7F2',
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* 背景装饰 */}
      <div style={{
        position: 'absolute',
        top: -100,
        left: -80,
        width: 500,
        height: 500,
        borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(44,120,115,0.10) 0%, transparent 70%)',
        pointerEvents: 'none',
      }} />
      <div style={{
        position: 'absolute',
        bottom: -80,
        right: -60,
        width: 400,
        height: 400,
        borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(212,116,76,0.10) 0%, transparent 70%)',
        pointerEvents: 'none',
      }} />

      {contextHolder}

      <div style={{
        width: 420,
        background: '#FFF',
        borderRadius: 18,
        padding: '44px 40px 36px',
        boxShadow: '0 8px 40px rgba(44,36,32,0.10), 0 1px 3px rgba(44,36,32,0.06)',
        position: 'relative',
        zIndex: 1,
      }}>
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <div style={{
            width: 52,
            height: 52,
            borderRadius: 14,
            background: 'linear-gradient(135deg, #2C7873 0%, #1D5652 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 16px',
            boxShadow: '0 4px 16px rgba(44,120,115,0.25)',
          }}>
            <GlobalOutlined style={{ color: '#FFF', fontSize: 24 }} />
          </div>
          <Title level={2} style={{
            margin: 0,
            fontFamily: "Georgia, 'Noto Serif SC', serif",
            fontWeight: 700,
            color: '#2C2420',
            letterSpacing: '0.04em',
            fontSize: 26,
          }}>
            旅行助手
          </Title>
          <Text style={{ color: '#9B8E85', fontSize: 14, marginTop: 4, display: 'block' }}>
            创建新账号
          </Text>
        </div>

        <Form onFinish={onFinish} size="large" layout="vertical">
          <Form.Item
            name="username"
            rules={[{ required: true, message: '请输入用户名' }]}
            style={{ marginBottom: 16 }}
          >
            <Input
              prefix={<UserOutlined style={{ color: '#9B8E85' }} />}
              placeholder="用户名"
              style={{ height: 44, borderRadius: 10, fontSize: 15 }}
            />
          </Form.Item>
          <Form.Item
            name="email"
            rules={[
              { required: true, message: '请输入邮箱' },
              { type: 'email', message: '邮箱格式不正确' },
            ]}
            style={{ marginBottom: 16 }}
          >
            <Input
              prefix={<MailOutlined style={{ color: '#9B8E85' }} />}
              placeholder="邮箱"
              style={{ height: 44, borderRadius: 10, fontSize: 15 }}
            />
          </Form.Item>
          <Form.Item
            name="password"
            rules={[
              { required: true, message: '请输入密码' },
              { min: 6, message: '密码至少6位' },
            ]}
            style={{ marginBottom: 16 }}
          >
            <Input.Password
              prefix={<LockOutlined style={{ color: '#9B8E85' }} />}
              placeholder="密码"
              style={{ height: 44, borderRadius: 10, fontSize: 15 }}
            />
          </Form.Item>
          <Form.Item
            name="confirm"
            dependencies={['password']}
            rules={[
              { required: true, message: '请确认密码' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('password') === value) return Promise.resolve();
                  return Promise.reject(new Error('两次密码不一致'));
                },
              }),
            ]}
            style={{ marginBottom: 24 }}
          >
            <Input.Password
              prefix={<LockOutlined style={{ color: '#9B8E85' }} />}
              placeholder="确认密码"
              style={{ height: 44, borderRadius: 10, fontSize: 15 }}
            />
          </Form.Item>
          <Form.Item style={{ marginBottom: 20 }}>
            <Button
              type="primary"
              htmlType="submit"
              block
              loading={submitting}
              style={{
                height: 46,
                borderRadius: 10,
                fontSize: 16,
                fontWeight: 600,
                background: 'linear-gradient(135deg, #2C7873 0%, #1D5652 100%)',
                border: 'none',
                boxShadow: '0 4px 14px rgba(44,120,115,0.3)',
              }}
            >
              注 册
            </Button>
          </Form.Item>
          <div style={{ textAlign: 'center' }}>
            <Text style={{ color: '#9B8E85', fontSize: 14 }}>
              已有账号？{' '}
              <Link to="/login" style={{ color: '#C25430', fontWeight: 500 }}>
                立即登录
              </Link>
            </Text>
          </div>
        </Form>
      </div>
    </div>
  );
}

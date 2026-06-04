import { useState, useEffect } from 'react';
import { Card, Form, Input, Button, Descriptions, Spin, Typography, message } from 'antd';
import { UserOutlined, MailOutlined } from '@ant-design/icons';
import { useAuth } from '@/store/AuthContext';
import { updateProfile } from '@/api/user';

const { Title } = Typography;

export default function Profile() {
  const { user, loading, refreshUser } = useAuth();
  const [editing, setEditing] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm();
  const [messageApi, contextHolder] = message.useMessage();

  useEffect(() => {
    if (user) {
      form.setFieldsValue({ username: user.username, email: user.email });
    }
  }, [user, form]);

  const onFinish = async (values: { username: string; email: string }) => {
    setSubmitting(true);
    try {
      await updateProfile(values);
      await refreshUser();
      messageApi.success('更新成功');
      setEditing(false);
    } catch {
      messageApi.error('更新失败');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <div style={{ padding: 48, textAlign: 'center' }}><Spin size="large" /></div>;

  return (
    <div style={{ padding: 24, maxWidth: 600, margin: '0 auto' }}>
      {contextHolder}
      <Title level={3}>个人中心</Title>
      <Card>
        {!editing ? (
          <>
            <Descriptions column={1} bordered>
              <Descriptions.Item label="用户名">{user?.username}</Descriptions.Item>
              <Descriptions.Item label="邮箱">{user?.email}</Descriptions.Item>
              <Descriptions.Item label="注册时间">{user?.created_at}</Descriptions.Item>
            </Descriptions>
            <Button type="primary" style={{ marginTop: 16 }} onClick={() => setEditing(true)}>
              编辑资料
            </Button>
          </>
        ) : (
          <Form form={form} layout="vertical" onFinish={onFinish}>
            <Form.Item name="username" label="用户名" rules={[{ required: true, message: '请输入用户名' }]}>
              <Input prefix={<UserOutlined />} />
            </Form.Item>
            <Form.Item name="email" label="邮箱" rules={[{ required: true, message: '请输入邮箱' }, { type: 'email', message: '邮箱格式不正确' }]}>
              <Input prefix={<MailOutlined />} />
            </Form.Item>
            <Form.Item>
              <Button type="primary" htmlType="submit" loading={submitting} style={{ marginRight: 8 }}>
                保存
              </Button>
              <Button onClick={() => setEditing(false)}>取消</Button>
            </Form.Item>
          </Form>
        )}
      </Card>
    </div>
  );
}

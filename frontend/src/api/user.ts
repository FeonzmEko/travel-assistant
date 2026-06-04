import client from './client';

export interface UserProfile {
  id: number;
  username: string;
  email: string;
  created_at: string;
}

export function getProfile() {
  return client.get<UserProfile>('/user/profile');
}

export function updateProfile(data: { username?: string; email?: string }) {
  return client.put('/user/profile', data);
}
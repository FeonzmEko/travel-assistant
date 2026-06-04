import client from './client';

export interface RegisterParams {
  username: string;
  password: string;
  email: string;
}

export interface LoginParams {
  username: string;
  password: string;
}

export interface LoginResult {
  access_token: string;
  token_type: string;
}

export function register(data: RegisterParams) {
  return client.post<{ user_id: number; username: string }>('/auth/register', data);
}

export function login(data: LoginParams) {
  return client.post<LoginResult>('/auth/login', data);
}

export function logout() {
  localStorage.removeItem('token');
}
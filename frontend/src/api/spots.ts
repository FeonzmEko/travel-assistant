import client from './client';

export interface Spot {
  id: string;
  name: string;
  city?: string;
  type?: string;
  address?: string;
  rating?: number;
  description?: string;
  image_url?: string;
  latitude?: number;
  longitude?: number;
}

export interface SpotSearchParams {
  keyword?: string;
  city?: string;
  type?: string;
  page?: number;
  size?: number;
}

export function searchSpots(params: SpotSearchParams) {
  return client.get<{ total: number; items: Spot[] }>('/spots/search', { params });
}

export function getSpot(id: string) {
  return client.get<Spot>(`/spots/${id}`);
}
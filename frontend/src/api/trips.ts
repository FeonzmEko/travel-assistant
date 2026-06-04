import client from './client';

export interface TripActivity {
  order_index: number;
  spot_name: string;
  time_slot?: string;
  transport?: string;
  notes?: string;
  estimated_cost?: number;
}

export interface TripDay {
  day_index: number;
  date: string;
  weather?: string;
  activities: TripActivity[];
}

export interface TripPlanData {
  title: string;
  destination: string;
  start_date: string;
  end_date: string;
  budget_total?: number;
  budget_breakdown?: string;
  days: TripDay[];
}

export interface TripSummary {
  id: number;
  title: string;
  destination: string;
  start_date: string;
  end_date: string;
}

export function createTrip(data: TripPlanData) {
  return client.post<{ trip_id: number }>('/trips', data);
}

export function getTrips() {
  return client.get<{ total: number; items: TripSummary[] }>('/trips');
}

export function getTrip(id: number) {
  return client.get(`/trips/${id}`);
}

export function deleteTrip(id: number) {
  return client.delete(`/trips/${id}`);
}

export async function exportTripPdf(id: number) {
  const response = await client.get(`/trips/${id}/export`, { responseType: 'blob' });
  const url = window.URL.createObjectURL(new Blob([response.data as BlobPart]));
  const a = document.createElement('a');
  a.href = url;
  a.download = `trip-${id}.pdf`;
  a.click();
  window.URL.revokeObjectURL(url);
}

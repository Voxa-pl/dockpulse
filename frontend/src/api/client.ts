import axios from 'axios';
import { Dock, Appointment, GoodsReceipt, Facility } from '../types';

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json'
  }
});

export const apiService = {
  // Facilities
  async getFacilities(): Promise<Facility[]> {
    const res = await api.get('/facilities');
    return res.data;
  },
  async createFacility(data: {
    name: string;
    code?: string;
    address?: string;
    latitude?: number;
    longitude?: number;
    geofence_radius_meters?: number;
    docks?: Array<{
      dock_number: string;
      dock_type: string;
      max_pallets: number;
      notes?: string;
    }>;
  }): Promise<Facility> {
    const res = await api.post('/facilities', data);
    return res.data;
  },
  async updateFacility(facilityId: string, data: Partial<Facility>): Promise<Facility> {
    const res = await api.patch(`/facilities/${facilityId}`, data);
    return res.data;
  },
  async deleteFacility(facilityId: string): Promise<any> {
    const res = await api.delete(`/facilities/${facilityId}`);
    return res.data;
  },

  // Docks
  async getDocks(): Promise<Dock[]> {
    const res = await api.get('/docks');
    return res.data;
  },
  async createDock(data: {
    facility_id?: string;
    dock_number: string;
    dock_type: string;
    max_pallets: number;
    notes?: string;
  }): Promise<Dock> {
    const res = await api.post('/docks', data);
    return res.data;
  },
  async deleteDock(dockId: string): Promise<any> {
    const res = await api.delete(`/docks/${dockId}`);
    return res.data;
  },
  async updateDockStatus(dockId: string, status: string, notes?: string): Promise<Dock> {
    const res = await api.patch(`/docks/${dockId}/status`, { status, notes });
    return res.data;
  },

  // Appointments
  async getAppointments(filters?: {
    status?: string;
    dock_id?: string;
    carrier?: string;
    date?: string;
    search?: string;
    sort_by?: string;
    sort_order?: string;
  }): Promise<Appointment[]> {
    const res = await api.get('/appointments', { params: filters });
    return res.data;
  },
  getExportUrl(filters?: Record<string, string>): string {
    const query = new URLSearchParams(filters || {}).toString();
    return `/api/v1/appointments/export${query ? `?${query}` : ''}`;
  },
  async createAppointment(data: any): Promise<Appointment> {
    const res = await api.post('/appointments', data);
    return res.data;
  },
  async callToDock(appointmentId: string, dockId: string): Promise<any> {
    const res = await api.post(`/appointments/${appointmentId}/call-to-dock`, { dock_id: dockId });
    return res.data;
  },
  async startOperation(appointmentId: string, coords?: { lat: number; lng: number }): Promise<any> {
    const res = await api.post(`/appointments/${appointmentId}/start-operation`, {
      driver_lat: coords?.lat,
      driver_lng: coords?.lng,
      bypass_geofence: !coords
    });
    return res.data;
  },
  async completeOperation(appointmentId: string, receiptData?: any): Promise<any> {
    const res = await api.post(`/appointments/${appointmentId}/complete-operation`, receiptData);
    return res.data;
  },
  async getDriverTracking(tokenOrPlate: string): Promise<any> {
    const res = await api.get(`/appointments/track/${encodeURIComponent(tokenOrPlate.trim())}`);
    return res.data;
  },

  // Gate
  async getTodayGate(): Promise<Appointment[]> {
    const res = await api.get('/gate/today');
    return res.data;
  },
  async gateCheckIn(plateOrToken: string): Promise<any> {
    const res = await api.post('/gate/check-in', { plate_or_token: plateOrToken });
    return res.data;
  },
  async gateOverride(data: any): Promise<any> {
    const res = await api.post('/gate/override', data);
    return res.data;
  },
  async gateCheckOut(appointmentId: string): Promise<any> {
    const res = await api.post('/gate/check-out', { appointment_id: appointmentId });
    return res.data;
  },

  // DocuLog Receipt
  async getReceiptDetails(appointmentId: string): Promise<GoodsReceipt> {
    const res = await api.get(`/doculog/receipt/${appointmentId}`);
    return res.data;
  }
};

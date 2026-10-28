import React, { useState, useEffect, useCallback } from 'react';
import { Navbar } from './components/Navbar';
import { DockCockpitView } from './components/DockCockpitView';
import { GateTabletView } from './components/GateTabletView';
import { DriverMobileView } from './components/DriverMobileView';
import { BookingWizardModal } from './components/BookingWizardModal';
import { FacilitySetupModal } from './components/FacilitySetupModal';
import { IoTTelemetryBar } from './components/IoTTelemetryBar';
import { Dock, Appointment, Facility, OperationLog } from './types';
import { apiService } from './api/client';
import { useWebSocket } from './hooks/useWebSocket';

export function App() {
  const [activeTab, setActiveTab] = useState<'cockpit' | 'gate' | 'driver' | 'booking'>('cockpit');
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [activeFacility, setActiveFacility] = useState<Facility | null>(null);
  const [docks, setDocks] = useState<Dock[]>([]);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(true);
  
  const [isBookingOpen, setIsBookingOpen] = useState(false);
  const [isFacilitySetupOpen, setIsFacilitySetupOpen] = useState(false);
  const [logs, setLogs] = useState<OperationLog[]>([]);

  // Add structured operation log
  const addLog = useCallback((
    eventType: string, 
    message: string, 
    severity: 'info' | 'success' | 'warn' | 'error' = 'info',
    plate?: string,
    dock?: string
  ) => {
    const timeStr = new Date().toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    const newLog: OperationLog = {
      id: Math.random().toString(36).substring(2, 9),
      timestamp: timeStr,
      event_type: eventType,
      message,
      severity,
      plate,
      dock
    };
    setLogs(prev => [newLog, ...prev.slice(0, 99)]);
  }, []);

  // Refresh facilities, docks and appointments
  const refreshData = useCallback(async () => {
    try {
      const [facs, docksData, appsData] = await Promise.all([
        apiService.getFacilities(),
        apiService.getDocks(),
        apiService.getAppointments()
      ]);

      setFacilities(facs);
      if (facs.length > 0) {
        setActiveFacility(facs[0]);
      } else {
        setActiveFacility(null);
        // If no facility is registered, prompt onboarding automatically
        setIsFacilitySetupOpen(true);
      }

      setDocks(docksData);
      setAppointments(appsData);
    } catch (err) {
      console.error('Veri yüklenirken hata oluştu:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Handle incoming real-time WebSocket events
  const handleWsEvent = useCallback((event: { event_type: string; payload: any }) => {
    console.log('WS Event received:', event.event_type, event.payload);
    
    // Map event to human-readable operation log
    const p = event.payload || {};
    if (event.event_type === 'APPOINTMENT_CREATED') {
      addLog('RANDEVU_ALINDI', `Yeni randevu oluşturuldu: ${p.carrier_name || ''}`, 'info', p.vehicle_plate);
    } else if (event.event_type === 'GATE_CHECKIN_SUCCESS') {
      addLog('KAPI_GİRİŞİ', `Nizamiye girişi onaylandı. Araç sahaya alındı.`, 'success', p.vehicle_plate, p.assigned_dock);
    } else if (event.event_type === 'DOCK_ASSIGNED' || event.event_type === 'DOCK_CALL') {
      addLog('RAMPA_ÇAĞRISI', `Araç rampaya çağrıldı. Şoföre SMS/ekran bildirimi iletildi.`, 'warn', p.vehicle_plate, p.dock_number);
    } else if (event.event_type === 'UNLOADING_STARTED') {
      addLog('BOŞALTMA_BAŞLADI', `Körük şişirildi ve forklift boşaltması başladı.`, 'info', p.vehicle_plate, p.dock_number);
    } else if (event.event_type === 'OPERATION_COMPLETED') {
      addLog('MAL_KABUL_TAMAM', `SAP 101/103 fişi kesildi, rampa serbest bırakıldı.`, 'success', p.vehicle_plate);
    } else if (event.event_type === 'GATE_CHECKOUT') {
      addLog('KAPI_ÇIKIŞI', `Güvenlik çıkış bariyeri açıldı, araç tesisten ayrıldı.`, 'info', p.vehicle_plate);
    } else if (event.event_type === 'FACILITY_CONFIG_CHANGED' || event.event_type === 'DOCK_CONFIG_CHANGED') {
      addLog('AYAR_GÜNCELLENDİ', `Tesis veya rampa altyapısı güncellendi.`, 'info');
    }

    refreshData();
  }, [refreshData, addLog]);

  const { connected: wsConnected } = useWebSocket(handleWsEvent);

  useEffect(() => {
    refreshData();
  }, [refreshData]);

  // Initial welcome log
  useEffect(() => {
    addLog('SİSTEM_BAŞLATILDI', 'DockPulse YMS işletim motoru çevrimiçi.', 'info');
  }, [addLog]);

  return (
    <div className="min-h-screen bg-[#0B0F19] text-slate-100 flex flex-col pb-24">
      {/* Top Navigation */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        wsConnected={wsConnected}
        facility={activeFacility}
        docks={docks}
        openBookingModal={() => setIsBookingOpen(true)}
        openFacilitySettings={() => setIsFacilitySetupOpen(true)}
      />

      {/* Main Content Area */}
      <main className="flex-1">
        {loading ? (
          <div className="flex items-center justify-center min-h-[60vh]">
            <div className="flex flex-col items-center space-y-3">
              <div className="w-10 h-10 border-4 border-cyan-500/30 border-t-cyan-500 rounded-full animate-spin"></div>
              <span className="text-xs text-slate-400 font-mono">Depo Yönetim Sistemleri Yükleniyor...</span>
            </div>
          </div>
        ) : (
          <>
            {activeTab === 'cockpit' && (
              <DockCockpitView
                docks={docks}
                appointments={appointments}
                onRefresh={refreshData}
                openBookingModal={() => setIsBookingOpen(true)}
              />
            )}

            {activeTab === 'gate' && (
              <GateTabletView
                todayAppointments={appointments}
                onRefresh={refreshData}
              />
            )}

            {activeTab === 'driver' && (
              <DriverMobileView facility={activeFacility} />
            )}
          </>
        )}
      </main>

      {/* Live Operation & Telemetry Audit Log Stream */}
      <IoTTelemetryBar
        docks={docks}
        appointments={appointments}
        onRefresh={refreshData}
        logs={logs}
      />

      {/* Booking Wizard Modal */}
      {isBookingOpen && (
        <BookingWizardModal
          docks={docks}
          onClose={() => setIsBookingOpen(false)}
          onSuccess={() => {
            refreshData();
            addLog('RANDEVU_OLUŞTURULDU', 'Yeni randevu kaydı başarıyla oluşturuldu.', 'success');
          }}
        />
      )}

      {/* Dynamic Facility & Dock Setup Modal */}
      <FacilitySetupModal
        isOpen={isFacilitySetupOpen}
        onClose={() => setIsFacilitySetupOpen(false)}
        facility={activeFacility}
        docks={docks}
        onSaved={() => {
          refreshData();
          addLog('TESİS_KAYDEDİLDİ', 'Tesis ve rampa altyapı ayarları güncellendi.', 'success');
        }}
      />
    </div>
  );
}

export default App;

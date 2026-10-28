import React, { useState } from 'react';
import { Dock, Appointment } from '../types';
import { 
  Truck, Clock, CheckCircle2, AlertTriangle, ArrowRight, FileText, 
  ExternalLink, Check, Sparkles, ChevronRight, RefreshCw, PhoneCall,
  Search, Filter, Download, LayoutGrid, List, Shield, Eye, Layers
} from 'lucide-react';
import { apiService } from '../api/client';

interface DockCockpitViewProps {
  docks: Dock[];
  appointments: Appointment[];
  onRefresh: () => void;
  openBookingModal: () => void;
}

export const DockCockpitView: React.FC<DockCockpitViewProps> = ({
  docks,
  appointments,
  onRefresh,
  openBookingModal
}) => {
  const [selectedApp, setSelectedApp] = useState<Appointment | null>(null);
  const [selectedDockId, setSelectedDockId] = useState<string>('');
  const [callingAppId, setCallingAppId] = useState<string | null>(null);
  const [receiptModalApp, setReceiptModalApp] = useState<Appointment | null>(null);
  const [receiptData, setReceiptData] = useState<any>(null);
  const [loadingReceipt, setLoadingReceipt] = useState(false);
  const [actionSuccessMsg, setActionSuccessMsg] = useState<string | null>(null);

  // View Mode: 'cards' (Touch Mobile Cards) | 'gantt' (Timeline Matrix) | 'table' (Data Grid)
  const [viewMode, setViewMode] = useState<'cards' | 'gantt' | 'table'>('cards');
  
  // Mobile Section Toggle: 'docks' (Rampalar) | 'yard' (Tır Parkı)
  const [mobileSection, setMobileSection] = useState<'docks' | 'yard'>('docks');

  // Filters State
  const [showFiltersMobile, setShowFiltersMobile] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [dockFilter, setDockFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [carrierFilter, setCarrierFilter] = useState('ALL');

  // Time slots for Gantt (08:00 to 20:00 - 12 hours)
  const timeHours = [
    '08:00', '09:00', '10:00', '11:00', '12:00', '13:00', 
    '14:00', '15:00', '16:00', '17:00', '18:00', '19:00', '20:00'
  ];

  // Distinct carriers for filter
  const carriers = Array.from(new Set(appointments.map(a => a.carrier_name))).filter(Boolean);

  // Filtered Appointments
  const filteredAppointments = appointments.filter(app => {
    if (dockFilter !== 'ALL' && app.dock_id !== dockFilter) return false;
    if (statusFilter !== 'ALL' && app.status !== statusFilter) return false;
    if (carrierFilter !== 'ALL' && app.carrier_name !== carrierFilter) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchPlate = app.vehicle_plate?.toLowerCase().includes(q);
      const matchTrailer = app.trailer_plate?.toLowerCase().includes(q);
      const matchCarrier = app.carrier_name?.toLowerCase().includes(q);
      const matchDriver = app.driver_name?.toLowerCase().includes(q);
      const matchPo = app.po_number?.toLowerCase().includes(q);
      const matchToken = app.tracking_token?.toLowerCase().includes(q);
      if (!matchPlate && !matchTrailer && !matchCarrier && !matchDriver && !matchPo && !matchToken) return false;
    }
    return true;
  });

  // Yard Counts
  const waitingInYard = appointments.filter(a => a.status === 'WAITING_LOT');
  const activeUnloading = appointments.filter(a => a.status === 'UNLOADING');
  const calledVehicles = appointments.filter(a => a.status === 'CALLED');
  const completedToday = appointments.filter(a => a.status === 'COMPLETED');

  // Proportional Gantt Coordinate Calculation
  const getSlotPosition = (slotStartStr: string, durationMin: number) => {
    try {
      const d = new Date(slotStartStr);
      const startMin = d.getHours() * 60 + d.getMinutes();
      const dayStart = 8 * 60; // 08:00
      const dayTotal = 12 * 60; // 12 hours
      let leftPct = ((startMin - dayStart) / dayTotal) * 100;
      let widthPct = (Math.max(durationMin || 45, 30) / dayTotal) * 100;

      if (leftPct < 0) {
        widthPct = Math.max(5, widthPct + leftPct);
        leftPct = 0;
      }
      if (leftPct > 95) leftPct = 92;
      if (leftPct + widthPct > 100) widthPct = 100 - leftPct;

      return {
        left: `${Math.max(0, leftPct).toFixed(2)}%`,
        width: `${Math.max(6, widthPct).toFixed(2)}%`
      };
    } catch {
      return { left: '0%', width: '15%' };
    }
  };

  // Current Time Marker (%)
  const getCurrentTimePct = () => {
    const now = new Date();
    const currentMins = now.getHours() * 60 + now.getMinutes();
    const dayStart = 8 * 60;
    const dayTotal = 12 * 60;
    const pct = ((currentMins - dayStart) / dayTotal) * 100;
    return pct >= 0 && pct <= 100 ? pct : null;
  };
  const currentTimePct = getCurrentTimePct();

  // Trigger Call to Dock
  const handleCallToDock = async (appId: string, dockId: string) => {
    if (!dockId) return;
    try {
      const res = await apiService.callToDock(appId, dockId);
      setActionSuccessMsg(res.message);
      setCallingAppId(null);
      setTimeout(() => setActionSuccessMsg(null), 4000);
      onRefresh();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Çağrı başarısız');
    }
  };

  // Start Operation
  const handleStartOperation = async (appId: string) => {
    try {
      await apiService.startOperation(appId);
      setActionSuccessMsg('Boşaltma işlemi başlatıldı. Süre sayacı ve forklift takip aktif.');
      setTimeout(() => setActionSuccessMsg(null), 3000);
      onRefresh();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'İşlem başlatılamadı');
    }
  };

  // Inspect Waybill Receipt
  const handleInspectAndComplete = async (app: Appointment) => {
    setReceiptModalApp(app);
    setLoadingReceipt(true);
    try {
      const data = await apiService.getReceiptDetails(app.id);
      setReceiptData(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingReceipt(false);
    }
  };

  // Finalize Receipt
  const handleFinalizeReceipt = async () => {
    if (!receiptModalApp) return;
    try {
      await apiService.completeOperation(receiptModalApp.id, receiptData);
      setReceiptModalApp(null);
      setActionSuccessMsg('Mal kabul onaylandı. SAP 101/103 hareket fişi oluşturuldu, rampa serbest bırakıldı.');
      setTimeout(() => setActionSuccessMsg(null), 4000);
      onRefresh();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Hata oluştu');
    }
  };

  // Calculate dwell time in minutes with SLA tracking
  const getDwellDisplay = (gateIn?: string, gateOut?: string) => {
    if (!gateIn) return { text: '-', isOverdue: false, isWarning: false };
    const start = new Date(gateIn).getTime();
    const end = gateOut ? new Date(gateOut).getTime() : Date.now();
    const mins = Math.max(0, Math.round((end - start) / 60000));
    return {
      text: `${mins} dk`,
      isOverdue: mins > 90,
      isWarning: mins > 50 && mins <= 90
    };
  };

  const calculateDwell = (gateIn?: string, gateOut?: string) => {
    return getDwellDisplay(gateIn, gateOut).text;
  };

  return (
    <div className="p-2.5 sm:p-4 max-w-[1920px] mx-auto space-y-3 sm:space-y-4">
      {/* Action Notification Banner */}
      {actionSuccessMsg && (
        <div className="bg-emerald-950/80 border border-emerald-500/50 text-emerald-300 px-3.5 py-2 rounded-lg flex items-center justify-between shadow-lg text-xs sm:text-sm font-semibold animate-in fade-in">
          <div className="flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
            <span>{actionSuccessMsg}</span>
          </div>
          <button onClick={() => setActionSuccessMsg(null)} className="text-xs text-slate-400 hover:text-white px-2">✕</button>
        </div>
      )}

      {/* Top Metrics Cards (Responsive Grid: 2 cols on mobile, 4 cols on tablet/desktop) */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 sm:gap-3">
        <div className="bg-charcoal-800 border border-charcoal-700 p-2.5 sm:p-3.5 rounded-xl flex items-center justify-between shadow-md">
          <div>
            <div className="text-[10px] sm:text-[11px] font-bold uppercase tracking-wider text-slate-400">Rampa Doluluk</div>
            <div className="text-xl sm:text-2xl font-black text-white mt-0.5">
              {docks.length ? Math.round((docks.filter(d => d.status === 'OCCUPIED' || d.status === 'CALLING').length / docks.length) * 100) : 0}%
            </div>
            <div className="text-[9px] sm:text-[10px] text-emerald-400 font-semibold">
              {docks.filter(d => d.status === 'OCCUPIED' || d.status === 'CALLING').length} / {docks.length} Rampa
            </div>
          </div>
          <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-lg bg-cyan-950/60 border border-cyan-800/50 flex items-center justify-center text-cyan-400 flex-shrink-0">
            <Truck className="w-4 h-4 sm:w-5 sm:h-5" />
          </div>
        </div>

        <div className="bg-charcoal-800 border border-charcoal-700 p-2.5 sm:p-3.5 rounded-xl flex items-center justify-between shadow-md">
          <div>
            <div className="text-[10px] sm:text-[11px] font-bold uppercase tracking-wider text-slate-400">Tır Parkında</div>
            <div className="text-xl sm:text-2xl font-black text-amber-400 mt-0.5">{waitingInYard.length} Araç</div>
            <div className="text-[9px] sm:text-[10px] text-slate-400 font-semibold">Sanal Kuyrukta</div>
          </div>
          <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-lg bg-amber-950/60 border border-amber-800/50 flex items-center justify-center text-amber-400 flex-shrink-0">
            <Clock className="w-4 h-4 sm:w-5 sm:h-5" />
          </div>
        </div>

        <div className="bg-charcoal-800 border border-charcoal-700 p-2.5 sm:p-3.5 rounded-xl flex items-center justify-between shadow-md">
          <div>
            <div className="text-[10px] sm:text-[11px] font-bold uppercase tracking-wider text-slate-400">Boşaltmada</div>
            <div className="text-xl sm:text-2xl font-black text-emerald-400 mt-0.5">{activeUnloading.length} Araç</div>
            <div className="text-[9px] sm:text-[10px] text-slate-400 font-semibold">Aktif Körük & Forklift</div>
          </div>
          <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-lg bg-emerald-950/60 border border-emerald-800/50 flex items-center justify-center text-emerald-400 flex-shrink-0">
            <CheckCircle2 className="w-4 h-4 sm:w-5 sm:h-5" />
          </div>
        </div>

        <div className="bg-charcoal-800 border border-charcoal-700 p-2.5 sm:p-3.5 rounded-xl flex items-center justify-between shadow-md">
          <div>
            <div className="text-[10px] sm:text-[11px] font-bold uppercase tracking-wider text-slate-400">Tamamlanan</div>
            <div className="text-xl sm:text-2xl font-black text-white mt-0.5">{completedToday.length} Araç</div>
            <div className="text-[9px] sm:text-[10px] text-cyan-400 font-semibold">SAP 101 Onaylı</div>
          </div>
          <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-lg bg-blue-950/60 border border-blue-800/50 flex items-center justify-center text-blue-400 flex-shrink-0">
            <FileText className="w-4 h-4 sm:w-5 sm:h-5" />
          </div>
        </div>
      </div>

      {/* Mobile Main Section Switcher: Rampalar vs Tır Parkı (visible on mobile screens) */}
      <div className="flex lg:hidden bg-charcoal-800 p-1 rounded-xl border border-charcoal-700">
        <button
          onClick={() => setMobileSection('docks')}
          className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all flex items-center justify-center space-x-1.5 cursor-pointer ${
            mobileSection === 'docks'
              ? 'bg-cyan-600 text-white shadow-md'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Layers className="w-4 h-4" />
          <span>Rampalar ({docks.length})</span>
        </button>
        <button
          onClick={() => setMobileSection('yard')}
          className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all flex items-center justify-center space-x-1.5 cursor-pointer ${
            mobileSection === 'yard'
              ? 'bg-amber-600 text-white shadow-md'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Clock className="w-4 h-4" />
          <span>Tır Parkı ({waitingInYard.length})</span>
        </button>
      </div>

      {/* Toolbar & Filter Bar */}
      <div className="bg-charcoal-800 border border-charcoal-700 p-2.5 sm:p-3 rounded-xl shadow-lg space-y-2.5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          {/* Quick Search */}
          <div className="relative flex-1 min-w-[180px]">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Plaka, şoför, irsaliye, PO..."
              className="w-full bg-charcoal-900 border border-charcoal-700 text-white text-xs rounded-lg pl-9 pr-3 py-1.5 sm:py-2 focus:outline-none focus:border-cyan-500 font-mono"
            />
            {searchQuery && (
              <button onClick={() => setSearchQuery('')} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white text-xs">
                ✕
              </button>
            )}
          </div>

          {/* View Mode Toggle: Cards (Mobile friendly), Gantt, Table */}
          <div className="flex items-center bg-charcoal-900 border border-charcoal-700 p-0.5 rounded-lg">
            <button
              onClick={() => setViewMode('cards')}
              className={`flex items-center space-x-1 px-2.5 py-1.5 rounded-md text-[11px] font-bold transition-all cursor-pointer ${
                viewMode === 'cards' ? 'bg-cyan-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Mobil Kartlar"
            >
              <Layers className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Kartlar</span>
            </button>
            <button
              onClick={() => setViewMode('gantt')}
              className={`flex items-center space-x-1 px-2.5 py-1.5 rounded-md text-[11px] font-bold transition-all cursor-pointer ${
                viewMode === 'gantt' ? 'bg-cyan-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Zaman Çizelgesi"
            >
              <LayoutGrid className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Gantt</span>
            </button>
            <button
              onClick={() => setViewMode('table')}
              className={`flex items-center space-x-1 px-2.5 py-1.5 rounded-md text-[11px] font-bold transition-all cursor-pointer ${
                viewMode === 'table' ? 'bg-cyan-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Detaylı Tablo"
            >
              <List className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Tablo</span>
            </button>
          </div>

          {/* Filter Toggle on Mobile */}
          <button
            onClick={() => setShowFiltersMobile(!showFiltersMobile)}
            className="sm:hidden px-2.5 py-1.5 rounded-lg bg-charcoal-900 border border-charcoal-700 text-slate-300 text-xs font-bold flex items-center space-x-1"
          >
            <Filter className="w-3.5 h-3.5 text-cyan-400" />
            <span>Filtre</span>
          </button>

          {/* Excel Export (Desktop and Mobile) */}
          <a
            href={apiService.getExportUrl({
              status: statusFilter !== 'ALL' ? statusFilter : '',
              dock_id: dockFilter !== 'ALL' ? dockFilter : '',
              carrier: carrierFilter !== 'ALL' ? carrierFilter : ''
            })}
            target="_blank"
            rel="noreferrer"
            className="flex items-center space-x-1 px-2.5 sm:px-3 py-1.5 rounded-lg bg-emerald-700 hover:bg-emerald-600 text-white text-[11px] sm:text-xs font-bold shadow-md transition-all cursor-pointer"
            title="Excel uyumlu CSV dökümü"
          >
            <Download className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Excel</span>
          </a>

          <button 
            onClick={onRefresh}
            className="p-1.5 sm:p-2 rounded-lg bg-charcoal-900 border border-charcoal-700 text-slate-400 hover:text-white transition-all cursor-pointer"
            title="Yenile"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Collapsible Dropdown Filters on Mobile, inline on sm+ */}
        <div className={`${showFiltersMobile ? 'flex' : 'hidden sm:flex'} flex-wrap items-center gap-2 pt-2 border-t border-charcoal-700/60 text-xs`}>
          <select
            value={dockFilter}
            onChange={(e) => setDockFilter(e.target.value)}
            className="bg-charcoal-900 border border-charcoal-700 text-slate-200 text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-cyan-500 font-semibold"
          >
            <option value="ALL">Tüm Rampalar (6)</option>
            {docks.map(d => (
              <option key={d.id} value={d.id}>{d.dock_number}</option>
            ))}
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-charcoal-900 border border-charcoal-700 text-slate-200 text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-cyan-500 font-semibold"
          >
            <option value="ALL">Tüm Durumlar</option>
            <option value="WAITING_LOT">Tır Parkında (Bekleyenler)</option>
            <option value="CALLED">Rampaya Çağrılanlar</option>
            <option value="UNLOADING">Boşaltma Devam Edenler</option>
            <option value="COMPLETED">Tamamlananlar</option>
            <option value="SCHEDULED">Planlı Randevular</option>
          </select>

          <select
            value={carrierFilter}
            onChange={(e) => setCarrierFilter(e.target.value)}
            className="bg-charcoal-900 border border-charcoal-700 text-slate-200 text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-cyan-500 font-semibold"
          >
            <option value="ALL">Tüm Taşıyıcılar ({carriers.length})</option>
            {carriers.map(c => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Main Split Layout: Desktop uses 8 / 4 split. Mobile switches between Docks and Yard based on mobileSection */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 sm:gap-4">
        {/* Primary Docks Section (Visible on desktop or when mobileSection === 'docks') */}
        <div className={`lg:col-span-8 bg-charcoal-800 border border-charcoal-700 rounded-xl p-3 sm:p-4 shadow-xl flex flex-col min-h-[500px] ${
          mobileSection === 'docks' ? 'flex' : 'hidden lg:flex'
        }`}>
          {/* Header Bar */}
          <div className="flex items-center justify-between pb-3 border-b border-charcoal-700">
            <div className="flex items-center space-x-2">
              <h2 className="text-xs sm:text-sm font-bold text-white tracking-wide">
                {viewMode === 'cards' ? 'RAMPA KONTROL KARTLARI' : viewMode === 'gantt' ? 'CANLI RAMPA ÇİZELGESİ (GANTT)' : 'OPERASYONEL RANDEVU TABLOSU'}
              </h2>
              <span className="text-[10px] bg-charcoal-700 text-slate-300 px-2 py-0.5 rounded font-mono">
                {filteredAppointments.length} Araç
              </span>
            </div>

            {viewMode === 'gantt' && (
              <div className="hidden sm:flex items-center space-x-2.5 text-[10px] text-slate-400">
                <span className="flex items-center space-x-1"><span className="w-2 h-2 rounded-sm bg-blue-500"></span><span>Planlı</span></span>
                <span className="flex items-center space-x-1"><span className="w-2 h-2 rounded-sm bg-purple-500"></span><span>Çağrıldı</span></span>
                <span className="flex items-center space-x-1"><span className="w-2 h-2 rounded-sm bg-emerald-500"></span><span>Boşaltmada</span></span>
              </div>
            )}
          </div>

          {/* VIEW MODE 1: MOBILE TOUCH CARDS (Responsive & Touch First) */}
          {viewMode === 'cards' && (
            docks.length === 0 ? (
              <div className="py-16 text-center text-slate-500 text-xs italic space-y-2 bg-charcoal-900/40 border border-charcoal-800 rounded-xl m-2">
                <div>Tesisinizde henüz tanımlı bir rampa bulunmuyor.</div>
                <div className="text-slate-400">Üst bardaki <strong>Tesis/Rampa Ayarları</strong> butonunu kullanarak yeni rampa tanımlayabilirsiniz.</div>
              </div>
            ) : (
            <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3 flex-1 overflow-y-auto">
              {docks
                .filter(d => dockFilter === 'ALL' || d.id === dockFilter)
                .map(dock => {
                  const activeApp = appointments.find(a => a.dock_id === dock.id && (a.status === 'UNLOADING' || a.status === 'CALLED'));
                  const scheduledApps = appointments.filter(a => a.dock_id === dock.id && a.status === 'SCHEDULED');

                  return (
                    <div 
                      key={dock.id} 
                      className={`rounded-xl border p-3 sm:p-4 transition-all flex flex-col justify-between shadow-md ${
                        dock.status === 'OCCUPIED' ? 'bg-charcoal-900 border-emerald-700/80' :
                        dock.status === 'CALLING' ? 'bg-charcoal-900 border-purple-600/80 animate-pulse' :
                        'bg-charcoal-900/60 border-charcoal-700'
                      }`}
                    >
                      {/* Dock Card Header */}
                      <div>
                        <div className="flex items-center justify-between pb-2 border-b border-charcoal-800">
                          <div>
                            <div className="font-bold text-sm sm:text-base text-white flex items-center space-x-2">
                              <span>{dock.dock_number}</span>
                              <span className="text-[10px] font-normal text-slate-400">({dock.notes || dock.dock_type})</span>
                            </div>
                          </div>

                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded font-mono uppercase ${
                            dock.status === 'OCCUPIED' ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' :
                            dock.status === 'CALLING' ? 'bg-purple-950 text-purple-300 border border-purple-800' :
                            'bg-charcoal-800 text-slate-400 border border-charcoal-700'
                          }`}>
                            {dock.status === 'OCCUPIED' ? 'Boşaltılıyor' : dock.status === 'CALLING' ? 'Yanaşıyor' : 'Boş / Hazır'}
                          </span>
                        </div>

                        {/* Active Vehicle Info */}
                        {activeApp ? (
                          <div className="mt-2.5 space-y-2">
                            <div className="flex items-center justify-between">
                              <div>
                                <span className="font-mono font-black text-base sm:text-lg text-white">
                                  {activeApp.vehicle_plate}
                                </span>
                                {activeApp.trailer_plate && (
                                  <span className="text-[11px] font-mono text-slate-400 ml-2">
                                    Dorse: {activeApp.trailer_plate}
                                  </span>
                                )}
                              </div>

                              {activeApp.doculog_status === 'MATCH_OK' && (
                                <span className="text-[10px] bg-cyan-950 text-cyan-300 border border-cyan-800 px-1.5 py-0.5 rounded font-bold font-mono">
                                  Waybill %99.4
                                </span>
                              )}
                            </div>

                            <div className="text-xs text-slate-300 font-semibold truncate">
                              {activeApp.carrier_name}
                            </div>

                            <div className="text-[11px] text-slate-400 flex items-center justify-between pt-1 border-t border-charcoal-800">
                              <span>Net Yük: <strong className="text-white">{activeApp.weighbridge_net_kg ? `${activeApp.weighbridge_net_kg.toLocaleString('tr-TR')} kg` : `${activeApp.estimated_pallets} Palet`}</strong></span>
                              {(() => {
                                const dwell = getDwellDisplay(activeApp.actual_gate_in, activeApp.actual_dock_out);
                                return (
                                  <span className={`font-mono text-[11px] ${
                                    dwell.isOverdue ? 'text-rose-400 font-bold bg-rose-950/60 px-1.5 py-0.5 rounded border border-rose-800/80' :
                                    dwell.isWarning ? 'text-amber-400 font-bold' :
                                    'text-cyan-400'
                                  }`}>
                                    Dwell: {dwell.text}
                                  </span>
                                );
                              })()}
                            </div>

                            {activeApp.e_waybill_uuid && (
                              <div className="text-[10px] text-slate-500 font-mono truncate">
                                ETTN: {activeApp.e_waybill_uuid}
                              </div>
                            )}
                          </div>
                        ) : (
                          <div className="py-6 text-center text-xs text-slate-500 italic">
                            Şu anda rampada araç yok.
                          </div>
                        )}
                      </div>

                      {/* Card Actions */}
                      <div className="pt-3 mt-2 border-t border-charcoal-800 flex items-center space-x-2">
                        {activeApp?.status === 'CALLED' && (
                          <button
                            onClick={() => handleStartOperation(activeApp.id)}
                            className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs py-2 rounded-lg shadow cursor-pointer transition-all flex items-center justify-center space-x-1.5"
                          >
                            <CheckCircle2 className="w-4 h-4" />
                            <span>Boşaltmayı Başlat</span>
                          </button>
                        )}

                        {activeApp?.status === 'UNLOADING' && (
                          <button
                            onClick={() => handleInspectAndComplete(activeApp)}
                            className="w-full bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs py-2 rounded-lg shadow cursor-pointer transition-all flex items-center justify-center space-x-1.5"
                          >
                            <FileText className="w-4 h-4" />
                            <span>Waybill Mal Kabul İncele</span>
                          </button>
                        )}

                        {!activeApp && waitingInYard.length > 0 && (
                          <button
                            onClick={() => {
                              setSelectedDockId(dock.id);
                              setCallingAppId(waitingInYard[0].id);
                              handleCallToDock(waitingInYard[0].id, dock.id);
                            }}
                            className="w-full bg-purple-600 hover:bg-purple-500 text-white font-bold text-xs py-2 rounded-lg shadow cursor-pointer transition-all flex items-center justify-center space-x-1.5"
                          >
                            <PhoneCall className="w-3.5 h-3.5" />
                            <span>Parktan Sıradaki Aracı Çağır ({waitingInYard[0].vehicle_plate})</span>
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
            </div>
            )
          )}

          {/* VIEW MODE 2: GANTT VIEW */}
          {viewMode === 'gantt' && (
            <div className="mt-3 overflow-x-auto flex-1 flex flex-col justify-between">
              <div className="min-w-[840px] relative">
                {/* Hours Header (12 Hours) */}
                <div className="flex border-b border-charcoal-700/80 pb-2 text-xs font-mono text-slate-400 pl-36">
                  {timeHours.map((hour) => (
                    <div key={hour} className="flex-1 text-left text-[11px] font-semibold">
                      {hour}
                    </div>
                  ))}
                </div>

                {/* Dock Rows */}
                <div className="divide-y divide-charcoal-700/50 mt-1 relative">
                  {/* Current Time Vertical Line */}
                  {currentTimePct !== null && (
                    <div 
                      className="absolute top-0 bottom-0 w-0.5 bg-rose-500 z-20 pointer-events-none shadow-[0_0_8px_rgba(244,63,94,0.9)]"
                      style={{ left: `calc(9rem + (100% - 9rem) * ${currentTimePct / 100})` }}
                    >
                      <div className="absolute -top-3.5 -translate-x-1/2 bg-rose-600 text-white text-[8px] font-mono font-bold px-1 rounded shadow">
                        ŞU AN
                      </div>
                    </div>
                  )}

                  {docks
                    .filter(d => dockFilter === 'ALL' || d.id === dockFilter)
                    .map(dock => {
                      const dockAppointments = filteredAppointments.filter(a => a.dock_id === dock.id);

                      return (
                        <div key={dock.id} className="py-2.5 flex items-center group hover:bg-charcoal-700/20 transition-all">
                          {/* Dock Label Column (9rem / 144px) */}
                          <div className="w-36 flex-shrink-0 pr-3">
                            <div className="flex items-center justify-between">
                              <span className="text-xs font-bold text-white group-hover:text-cyan-400 transition-colors">
                                {dock.dock_number}
                              </span>
                              <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded uppercase font-mono ${
                                dock.status === 'OCCUPIED' ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' :
                                dock.status === 'CALLING' ? 'bg-purple-950 text-purple-400 border border-purple-800 animate-pulse' :
                                'bg-charcoal-900 text-slate-400 border border-charcoal-700'
                              }`}>
                                {dock.status === 'OCCUPIED' ? 'Rampada' : dock.status === 'CALLING' ? 'Yanaşıyor' : 'Boş'}
                              </span>
                            </div>
                            <div className="text-[10px] text-slate-400 truncate mt-0.5">{dock.notes || dock.dock_type}</div>
                          </div>

                          {/* Mathematically Accurate Gantt Track */}
                          <div className="flex-1 relative h-12 bg-charcoal-900/90 rounded-lg border border-charcoal-700/60 p-1 overflow-hidden">
                            {/* Grid hour guides */}
                            <div className="absolute inset-0 flex pointer-events-none divide-x divide-charcoal-800/40 opacity-40">
                              {timeHours.map((_, i) => (
                                <div key={i} className="flex-1"></div>
                              ))}
                            </div>

                            {dockAppointments.length === 0 ? (
                              <div className="w-full h-full flex items-center justify-center text-[10px] text-slate-600 italic font-mono">
                                Boş (Slot Rezervasyonu Yok)
                              </div>
                            ) : (
                              dockAppointments.map(app => {
                                const pos = getSlotPosition(app.slot_start, app.calculated_duration_minutes);

                                let bgClass = "bg-blue-600/40 border-blue-500 text-blue-100 hover:bg-blue-600/60";
                                if (app.status === 'CALLED') bgClass = "bg-purple-600/50 border-purple-400 text-purple-100 animate-pulse";
                                if (app.status === 'UNLOADING') bgClass = "bg-emerald-600/50 border-emerald-400 text-emerald-100";
                                if (app.status === 'COMPLETED') bgClass = "bg-charcoal-700/90 border-slate-500 text-slate-300";

                                return (
                                  <div
                                    key={app.id}
                                    onClick={() => setSelectedApp(app)}
                                    style={{ position: 'absolute', left: pos.left, width: pos.width, minWidth: '85px' }}
                                    className={`top-1 bottom-1 px-2 rounded border text-xs font-semibold cursor-pointer shadow-md transition-all flex items-center justify-between overflow-hidden z-10 ${bgClass}`}
                                    title={`${app.vehicle_plate} - ${app.carrier_name} (${app.calculated_duration_minutes} dk)`}
                                  >
                                    <div className="flex items-center space-x-1.5 truncate">
                                      <Truck className="w-3 h-3 flex-shrink-0" />
                                      <span className="font-mono font-bold text-[11px] truncate">{app.vehicle_plate}</span>
                                    </div>
                                    {app.doculog_status === 'MATCH_OK' && (
                                      <span className="text-[8px] bg-cyan-950 text-cyan-300 px-1 rounded font-bold border border-cyan-800" title="Waybill OCR Eşleşti">
                                        AI
                                      </span>
                                    )}
                                  </div>
                                );
                              })
                            )}
                          </div>
                        </div>
                      );
                    })}
                </div>
              </div>
            </div>
          )}

          {/* VIEW MODE 3: TABLE VIEW */}
          {viewMode === 'table' && (
            <div className="mt-3 overflow-x-auto flex-1">
              <table className="w-full text-left text-xs">
                <thead className="bg-charcoal-900 text-slate-400 border-b border-charcoal-700 font-semibold font-mono">
                  <tr>
                    <th className="p-2.5">Slot</th>
                    <th className="p-2.5">Plaka / Dorse</th>
                    <th className="p-2.5">Taşıyıcı</th>
                    <th className="p-2.5">Rampa</th>
                    <th className="p-2.5">Durum</th>
                    <th className="p-2.5">Dwell</th>
                    <th className="p-2.5">Net Tonaj</th>
                    <th className="p-2.5">Waybill</th>
                    <th className="p-2.5 text-right">Aksiyon</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-charcoal-700/50">
                  {filteredAppointments.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="py-12 text-center text-slate-500 italic">
                        Filtreye uygun randevu kaydı bulunamadı.
                      </td>
                    </tr>
                  ) : (
                    filteredAppointments.map(app => {
                      const dockObj = docks.find(d => d.id === app.dock_id);

                      return (
                        <tr key={app.id} className="hover:bg-charcoal-700/30 transition-colors">
                          <td className="p-2.5 font-mono text-slate-300 font-semibold">
                            {new Date(app.slot_start).toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' })}
                          </td>
                          <td className="p-2.5">
                            <div className="font-mono font-bold text-white text-xs">{app.vehicle_plate}</div>
                            {app.trailer_plate && <div className="font-mono text-[10px] text-slate-400">{app.trailer_plate}</div>}
                          </td>
                          <td className="p-2.5">
                            <div className="font-semibold text-slate-200 truncate max-w-[140px]">{app.carrier_name}</div>
                            <div className="text-[10px] text-slate-400">{app.driver_name}</div>
                          </td>
                          <td className="p-2.5 font-semibold text-cyan-400">
                            {dockObj ? dockObj.dock_number : <span className="text-slate-500 italic">Atanmadı</span>}
                          </td>
                          <td className="p-2.5">
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase font-mono ${
                              app.status === 'COMPLETED' ? 'bg-slate-800 text-slate-300 border border-slate-700' :
                              app.status === 'UNLOADING' ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' :
                              app.status === 'CALLED' ? 'bg-purple-950 text-purple-300 border border-purple-800 animate-pulse' :
                              app.status === 'WAITING_LOT' ? 'bg-amber-950 text-amber-300 border border-amber-800' :
                              'bg-blue-950 text-blue-300 border border-blue-800'
                            }`}>
                              {app.status}
                            </span>
                          </td>
                          <td className="p-2.5 font-mono text-slate-300">
                            {calculateDwell(app.actual_gate_in, app.actual_dock_out)}
                          </td>
                          <td className="p-2.5 font-mono text-white">
                            {app.weighbridge_net_kg ? `${app.weighbridge_net_kg.toLocaleString('tr-TR')} kg` : `${app.estimated_pallets} Plt`}
                          </td>
                          <td className="p-2.5">
                            {app.doculog_status === 'MATCH_OK' ? (
                              <span className="text-[10px] bg-cyan-950 text-cyan-300 border border-cyan-800 px-1.5 py-0.5 rounded font-bold">
                                %99.4
                              </span>
                            ) : (
                              <span className="text-[10px] text-slate-500 font-mono">Bekliyor</span>
                            )}
                          </td>
                          <td className="p-2.5 text-right">
                            <button
                              onClick={() => setSelectedApp(app)}
                              className="px-2.5 py-1 bg-charcoal-700 hover:bg-charcoal-600 text-slate-200 text-xs font-semibold rounded cursor-pointer transition-all"
                            >
                              İncele
                            </button>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          )}

          {/* Selected Vehicle Quick Inspector Bar */}
          {selectedApp && (
            <div className="mt-4 p-3 bg-charcoal-900 border border-cyan-800/80 rounded-lg flex flex-wrap items-center justify-between text-xs animate-in fade-in gap-3">
              <div className="flex items-center space-x-3">
                <div className="w-9 h-9 rounded-lg bg-cyan-950 flex items-center justify-center text-cyan-400 font-bold font-mono border border-cyan-800">
                  {selectedApp.vehicle_plate.slice(0, 2)}
                </div>
                <div>
                  <div className="font-bold text-white flex items-center space-x-2">
                    <span className="font-mono text-sm">{selectedApp.vehicle_plate}</span>
                    <span className="text-slate-400 font-normal">({selectedApp.carrier_name})</span>
                    <span className="text-[10px] bg-charcoal-700 text-slate-300 px-1.5 py-0.5 rounded uppercase font-mono">
                      {selectedApp.status}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-400 flex items-center space-x-2 mt-0.5">
                    <span>Şoför: {selectedApp.driver_name} ({selectedApp.driver_phone})</span>
                    <span>•</span>
                    <span>{selectedApp.estimated_pallets} Palet</span>
                    <span>•</span>
                    <span className="text-cyan-400 font-mono">Token: {selectedApp.tracking_token}</span>
                  </div>
                </div>
              </div>

              <div className="flex items-center space-x-2">
                {selectedApp.status === 'CALLED' && (
                  <button
                    onClick={() => handleStartOperation(selectedApp.id)}
                    className="bg-emerald-600 hover:bg-emerald-500 text-white px-3 py-1.5 rounded text-xs font-bold shadow transition-all cursor-pointer"
                  >
                    Boşaltmayı Başlat
                  </button>
                )}

                {selectedApp.status === 'UNLOADING' && (
                  <button
                    onClick={() => handleInspectAndComplete(selectedApp)}
                    className="bg-cyan-600 hover:bg-cyan-500 text-white px-3 py-1.5 rounded text-xs font-bold shadow flex items-center space-x-1 cursor-pointer transition-all"
                  >
                    <FileText className="w-3.5 h-3.5" />
                    <span>Waybill İncele & Kabul Et</span>
                  </button>
                )}

                <button
                  onClick={() => setSelectedApp(null)}
                  className="text-slate-400 hover:text-white px-2 py-1 text-xs"
                >
                  Kapat
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Right Panel: Buffer Yard Queue (Tır Parkı) - Visible on desktop or when mobileSection === 'yard' */}
        <div className={`lg:col-span-4 bg-charcoal-800 border border-charcoal-700 rounded-xl p-3 sm:p-4 shadow-xl flex flex-col ${
          mobileSection === 'yard' ? 'flex' : 'hidden lg:flex'
        }`}>
          <div className="flex items-center justify-between pb-3 border-b border-charcoal-700">
            <div className="flex items-center space-x-2">
              <div className="w-2.5 h-2.5 rounded-full bg-amber-400 animate-pulse"></div>
              <h2 className="text-xs sm:text-sm font-bold text-white tracking-wide">TIR PARKI (BUFFER YARD)</h2>
            </div>
            <span className="text-xs bg-amber-950 text-amber-400 border border-amber-800 px-2 py-0.5 rounded font-bold font-mono">
              {waitingInYard.length} Araç Bekliyor
            </span>
          </div>

          <p className="text-[11px] text-slate-400 mt-2">
            Nizamiye kapısından içeri girmiş, sanal bekleme kuyruğundaki araçlar. Boş rampa seçerek şoförün cebine SMS çağrısı gönderin.
          </p>

          <div className="mt-3 space-y-2.5 flex-1 overflow-y-auto max-h-[560px]">
            {waitingInYard.length === 0 ? (
              <div className="py-16 text-center text-slate-500 text-xs italic">
                Tır parkında bekleyen araç bulunmuyor.
              </div>
            ) : (
              waitingInYard.map(app => (
                <div
                  key={app.id}
                  className="bg-charcoal-900 border border-charcoal-700 hover:border-amber-600/60 p-3 rounded-lg transition-all space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <span className="font-mono font-black text-sm text-white bg-charcoal-800 px-2 py-0.5 rounded border border-charcoal-700">
                        {app.vehicle_plate}
                      </span>
                      {app.trailer_plate && (
                        <span className="text-[10px] font-mono text-slate-400">/{app.trailer_plate}</span>
                      )}
                    </div>
                    <span className="text-[10px] text-amber-400 font-mono bg-amber-950/70 border border-amber-800/60 px-1.5 py-0.5 rounded">
                      {app.load_type} ({app.estimated_pallets} Plt)
                    </span>
                  </div>

                  <div className="text-xs text-slate-300 font-semibold truncate">
                    {app.carrier_name}
                  </div>

                  <div className="flex items-center justify-between text-[11px] text-slate-400">
                    <span>Şoför: {app.driver_name}</span>
                    <span className="font-mono text-cyan-400">
                      Kapı: {app.actual_gate_in ? new Date(app.actual_gate_in).toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' }) : 'Yeni'}
                    </span>
                  </div>

                  {/* Call to dock action box */}
                  <div className="pt-2 border-t border-charcoal-800 flex items-center space-x-2">
                    <select
                      className="bg-charcoal-800 border border-charcoal-700 text-white text-xs rounded px-2 py-1.5 flex-1 focus:outline-none focus:border-cyan-500 font-mono"
                      value={callingAppId === app.id ? selectedDockId : ''}
                      onChange={(e) => {
                        setCallingAppId(app.id);
                        setSelectedDockId(e.target.value);
                      }}
                    >
                      <option value="">Boş Rampa Seç...</option>
                      {docks.map(d => (
                        <option key={d.id} value={d.id}>
                          {d.dock_number} ({d.status === 'IDLE' ? 'Boş' : d.status})
                        </option>
                      ))}
                    </select>

                    <button
                      disabled={callingAppId !== app.id || !selectedDockId}
                      onClick={() => handleCallToDock(app.id, selectedDockId)}
                      className="bg-purple-600 hover:bg-purple-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-xs font-bold px-3 py-1.5 rounded flex items-center space-x-1 transition-all cursor-pointer"
                    >
                      <PhoneCall className="w-3.5 h-3.5" />
                      <span>Çağır</span>
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Waybill Split-Screen Inspection Modal (Mobile & Tablet Friendly) */}
      {receiptModalApp && (
        <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-sm flex items-center justify-center p-2 sm:p-4">
          <div className="bg-charcoal-900 border border-charcoal-700 rounded-2xl w-full max-w-5xl max-h-[94vh] overflow-hidden shadow-2xl flex flex-col">
            {/* Modal Header */}
            <div className="bg-charcoal-800 px-4 sm:px-6 py-3.5 sm:py-4 border-b border-charcoal-700 flex items-center justify-between">
              <div className="flex items-center space-x-2.5 sm:space-x-3">
                <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-lg bg-cyan-950 border border-cyan-800/80 flex items-center justify-center text-cyan-400 flex-shrink-0">
                  <Sparkles className="w-4 h-4 sm:w-5 sm:h-5" />
                </div>
                <div>
                  <h3 className="text-sm sm:text-base font-bold text-white flex items-center space-x-2">
                    <span>Waybill Workstation — Mal Kabul Teftişi</span>
                    <span className="hidden sm:inline text-xs bg-cyan-900 text-cyan-300 px-2 py-0.5 rounded font-mono">
                      Gemini 3.8 Flash Vision
                    </span>
                  </h3>
                  <p className="text-[11px] sm:text-xs text-slate-400 mt-0.5 truncate max-w-xs sm:max-w-none">
                    {receiptModalApp.vehicle_plate} • {receiptModalApp.carrier_name}
                  </p>
                </div>
              </div>
              <button 
                onClick={() => setReceiptModalApp(null)}
                className="text-slate-400 hover:text-white text-sm font-bold p-1 rounded hover:bg-charcoal-700"
              >
                ✕
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-3 sm:p-6 overflow-y-auto space-y-3 sm:space-y-4">
              {loadingReceipt ? (
                <div className="py-16 text-center text-slate-400 text-sm">
                  Waybill irsaliye verileri yükleniyor...
                </div>
              ) : receiptData ? (
                <>
                  {/* Waybill Header Card */}
                  <div className="bg-charcoal-800/90 border border-charcoal-700 p-3 sm:p-4 rounded-xl grid grid-cols-2 md:grid-cols-4 gap-2.5 sm:gap-3 text-xs">
                    <div>
                      <span className="text-slate-400">İrsaliye Seri-No:</span>
                      <div className="font-mono font-bold text-white mt-0.5">{receiptData.waybill_number}</div>
                    </div>
                    <div>
                      <span className="text-slate-400">Tedarikçi VKN:</span>
                      <div className="font-bold text-white mt-0.5 truncate">{receiptData.supplier_title || 'Ekol Dağıtım A.Ş.'}</div>
                    </div>
                    <div>
                      <span className="text-slate-400">GİB ETTN:</span>
                      <div className="font-mono text-[10px] sm:text-[11px] text-cyan-400 mt-0.5 truncate">{receiptData.e_waybill_uuid}</div>
                    </div>
                    <div>
                      <span className="text-slate-400">U-ETDS Ref:</span>
                      <div className="font-mono font-bold text-emerald-400 mt-0.5 truncate">{receiptData.uetds_reference_number}</div>
                    </div>
                  </div>

                  {/* Items Verification Table */}
                  <div className="bg-charcoal-800/80 border border-charcoal-700 rounded-xl overflow-hidden">
                    <div className="p-2.5 sm:p-3 bg-charcoal-800 border-b border-charcoal-700 flex items-center justify-between text-xs font-bold text-slate-300">
                      <span>İRSALİYE KALEMLERİ VE FİZİKİ SAYIM</span>
                      <span className="text-emerald-400 font-mono text-[11px]">Waybill: %99.2</span>
                    </div>

                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs min-w-[500px]">
                        <thead className="bg-charcoal-900/60 text-slate-400 border-b border-charcoal-700/60 font-semibold">
                          <tr>
                            <th className="p-2">Sıra</th>
                            <th className="p-2">Malzeme Tanımı</th>
                            <th className="p-2">Sevk</th>
                            <th className="p-2">Sağlam (101)</th>
                            <th className="p-2">Hasar (103)</th>
                            <th className="p-2">Birim</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-charcoal-700/50">
                          {receiptData.items?.map((item: any, idx: number) => (
                            <tr key={idx} className="hover:bg-charcoal-700/30">
                              <td className="p-2 font-mono text-slate-400">{item.line_number}</td>
                              <td className="p-2 font-semibold text-white">
                                <div>{item.description}</div>
                                <div className="text-[10px] font-mono text-slate-400">{item.material_code}</div>
                              </td>
                              <td className="p-2 font-mono text-slate-300">{item.dispatched_qty}</td>
                              <td className="p-2 font-mono font-bold text-emerald-400">{item.received_qty}</td>
                              <td className="p-2 font-mono font-bold text-amber-400">
                                {item.damaged_qty > 0 ? `${item.damaged_qty} Bloke` : '0'}
                              </td>
                              <td className="p-2 text-slate-400">{item.uom}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* Notes Field */}
                  <div className="bg-charcoal-800/50 border border-charcoal-700 p-2.5 sm:p-3 rounded-xl text-xs">
                    <span className="text-slate-400 font-semibold">Mühür ve Ambar Kabul Notu:</span>
                    <p className="text-slate-200 mt-0.5 italic text-[11px]">
                      {receiptData.warehouse_notes || 'Tüm paletler körükte açıldı, mühür teyit edildi, fiziki sayım tamamlandı.'}
                    </p>
                  </div>
                </>
              ) : null}
            </div>

            {/* Modal Footer */}
            <div className="bg-charcoal-800 px-4 sm:px-6 py-3 border-t border-charcoal-700 flex items-center justify-between gap-2">
              <div className="text-[10px] sm:text-xs text-slate-400 hidden sm:block">
                Onaylandığında SAP Mal Girişi (101) ve U-ETDS bildirimi tamamlanacaktır.
              </div>
              <div className="flex items-center space-x-2 sm:space-x-3 w-full sm:w-auto justify-end">
                <button
                  onClick={() => setReceiptModalApp(null)}
                  className="px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-300 hover:bg-charcoal-700 transition-all cursor-pointer"
                >
                  İptal
                </button>
                <button
                  onClick={handleFinalizeReceipt}
                  className="px-4 py-1.5 rounded-lg text-xs font-bold bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-600/30 transition-all cursor-pointer flex items-center space-x-1.5"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Onayla & Mal Kabulü Kapat</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

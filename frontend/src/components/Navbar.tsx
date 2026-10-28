import React from 'react';
import { 
  LayoutDashboard, ShieldCheck, Smartphone, PlusCircle, 
  Clock, Warehouse, Settings2, Truck
} from 'lucide-react';
import { Facility, Dock } from '../types';

interface NavbarProps {
  activeTab: 'cockpit' | 'gate' | 'driver' | 'booking';
  setActiveTab: (tab: 'cockpit' | 'gate' | 'driver' | 'booking') => void;
  wsConnected: boolean;
  facility: Facility | null;
  docks: Dock[];
  openBookingModal: () => void;
  openFacilitySettings: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  wsConnected,
  facility,
  docks,
  openBookingModal,
  openFacilitySettings
}) => {
  const currentTime = new Date().toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' });

  return (
    <header className="bg-charcoal-900 border-b border-charcoal-700 sticky top-0 z-50 px-3 sm:px-4 py-2">
      <div className="max-w-[1920px] mx-auto flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        {/* Top Row on Mobile: Brand + Dynamic Facility Info */}
        <div className="flex items-center justify-between w-full sm:w-auto">
          {/* Brand & Dynamic Facility Info */}
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-lg bg-blue-600 flex items-center justify-center text-white shadow-md shadow-blue-600/25 flex-shrink-0">
              <Truck className="w-4 h-4 sm:w-5 sm:h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-1.5">
                <h1 className="text-sm sm:text-base font-bold tracking-tight text-white">DockPulse</h1>
                <span className="text-[9px] uppercase font-bold tracking-wider px-1.5 py-0.2 rounded bg-blue-950 text-blue-400 border border-blue-800/60 font-mono">
                  YMS
                </span>
              </div>
              <div className="flex items-center space-x-1.5 text-[10px] sm:text-xs text-slate-400">
                <Warehouse className="w-3 h-3 text-cyan-400 flex-shrink-0" />
                <span className="font-semibold text-slate-200 truncate max-w-[150px] sm:max-w-[220px]">
                  {facility ? facility.name : 'Tesis Kurulmadı'}
                </span>
                <span className="text-[10px] text-cyan-300 bg-cyan-950/80 px-1 rounded font-mono">
                  {docks.length} Rampa
                </span>
              </div>
            </div>
          </div>

          {/* Mobile Right Quick Actions */}
          <div className="flex items-center space-x-2 sm:hidden">
            <button
              onClick={openFacilitySettings}
              className="text-slate-400 hover:text-white p-1 rounded hover:bg-charcoal-800"
              title="Tesis & Rampa Ayarları"
            >
              <Settings2 className="w-4 h-4" />
            </button>

            <span className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-emerald-400' : 'bg-red-400'}`} title={wsConnected ? 'Sistem Aktif' : 'Bağlantı Yok'} />
            
            <button
              onClick={openBookingModal}
              className="bg-cyan-600 hover:bg-cyan-500 text-white px-2.5 py-1 rounded-md text-[11px] font-bold shadow flex items-center space-x-1"
            >
              <PlusCircle className="w-3.5 h-3.5" />
              <span>Randevu</span>
            </button>
          </div>
        </div>

        {/* View Switcher Tabs (Responsive Segmented Control) */}
        <div className="flex items-center bg-charcoal-800 p-1 rounded-lg border border-charcoal-700 w-full sm:w-auto justify-between sm:justify-start">
          <button
            onClick={() => setActiveTab('cockpit')}
            className={`flex-1 sm:flex-none flex items-center justify-center space-x-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-all cursor-pointer ${
              activeTab === 'cockpit'
                ? 'bg-cyan-600 text-white shadow-md shadow-cyan-600/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <LayoutDashboard className="w-3.5 h-3.5 flex-shrink-0" />
            <span>Rampa Kokpiti</span>
          </button>

          <button
            onClick={() => setActiveTab('gate')}
            className={`flex-1 sm:flex-none flex items-center justify-center space-x-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-all cursor-pointer ${
              activeTab === 'gate'
                ? 'bg-amber-600 text-white shadow-md shadow-amber-600/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5 flex-shrink-0" />
            <span>Nizamiye</span>
          </button>

          <button
            onClick={() => setActiveTab('driver')}
            className={`flex-1 sm:flex-none flex items-center justify-center space-x-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-all cursor-pointer ${
              activeTab === 'driver'
                ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Smartphone className="w-3.5 h-3.5 flex-shrink-0" />
            <span>Şoför Ekranı</span>
          </button>
        </div>

        {/* Desktop Right Action Bar */}
        <div className="hidden sm:flex items-center space-x-2.5">
          {/* Facility & Dock Settings Button */}
          <button
            onClick={openFacilitySettings}
            className="flex items-center space-x-1 text-xs text-slate-300 hover:text-white bg-charcoal-800 hover:bg-charcoal-700 px-2.5 py-1.5 rounded-md border border-charcoal-700 transition-colors cursor-pointer"
            title="Tesis ve Rampa Ayarları"
          >
            <Settings2 className="w-3.5 h-3.5 text-cyan-400" />
            <span>Tesis/Rampa Ayarları</span>
          </button>

          {/* Status Dot */}
          <div className="flex items-center space-x-1.5 text-xs px-2.5 py-1.5 rounded-md bg-charcoal-800 border border-charcoal-700">
            <span className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-emerald-400' : 'bg-red-400'}`} />
            <span className="text-[11px] text-slate-300 font-medium">
              {wsConnected ? 'Sistem Aktif' : 'Bağlantı Yok'}
            </span>
          </div>

          {/* Time Clock */}
          <div className="hidden md:flex items-center space-x-1 text-xs text-slate-300 bg-charcoal-800 px-2.5 py-1.5 rounded-md border border-charcoal-700 font-mono">
            <Clock className="w-3.5 h-3.5 text-slate-400" />
            <span>{currentTime}</span>
          </div>

          {/* New Appointment Button */}
          <button
            onClick={openBookingModal}
            className="flex items-center space-x-1.5 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white px-3 py-1.5 rounded-md text-xs font-bold shadow-lg shadow-cyan-600/20 transition-all cursor-pointer"
          >
            <PlusCircle className="w-4 h-4" />
            <span>Randevu Al</span>
          </button>
        </div>
      </div>
    </header>
  );
};

export default Navbar;

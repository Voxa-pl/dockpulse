import React, { useState, useEffect } from 'react';
import { 
  Radio, ChevronUp, ChevronDown, RefreshCw, Terminal, 
  Clock, CheckCircle2, ShieldCheck, ArrowRight, Truck 
} from 'lucide-react';
import { Appointment, Dock, OperationLog } from '../types';

interface IoTTelemetryBarProps {
  docks: Dock[];
  appointments: Appointment[];
  onRefresh: () => void;
  logs: OperationLog[];
}

export const IoTTelemetryBar: React.FC<IoTTelemetryBarProps> = ({
  docks,
  appointments,
  onRefresh,
  logs
}) => {
  const [isOpen, setIsOpen] = useState(false);

  // Derive active system statistics
  const waitingCount = appointments.filter(a => a.status === 'WAITING_LOT').length;
  const activeUnloadingCount = appointments.filter(a => a.status === 'UNLOADING').length;
  const calledCount = appointments.filter(a => a.status === 'CALLED').length;
  const completedCount = appointments.filter(a => a.status === 'COMPLETED').length;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-40 bg-[#0B101B]/95 border-t border-slate-700/80 backdrop-blur-md shadow-2xl transition-all">
      {/* Mini Toggle Tab */}
      <div className="max-w-[1920px] mx-auto px-4 flex items-center justify-between h-9 text-xs border-b border-slate-800/80">
        <div className="flex items-center space-x-2">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          <span className="font-bold text-slate-200 tracking-wide flex items-center space-x-1.5">
            <Terminal className="w-3.5 h-3.5 text-cyan-400" />
            <span>CANLI OPERASYON & DONANIM LOGLARI</span>
          </span>
          <span className="hidden md:inline-block text-[10px] bg-slate-800 text-slate-400 px-2 py-0.5 rounded font-mono">
            {logs.length} Canlı Olay Kaydı • Aktif WebSocket
          </span>
        </div>

        <div className="flex items-center space-x-3">
          <div className="hidden sm:flex items-center space-x-2 text-[10px] text-slate-400 font-mono">
            <span>Park: {waitingCount}</span>
            <span>•</span>
            <span>Yanaşan: {calledCount}</span>
            <span>•</span>
            <span>Körük: {activeUnloadingCount}</span>
            <span>•</span>
            <span>Tamam: {completedCount}</span>
          </div>

          <button
            onClick={onRefresh}
            className="text-[11px] text-slate-400 hover:text-white flex items-center space-x-1 transition-colors cursor-pointer"
            title="Manuel Veri Yenile"
          >
            <RefreshCw className="w-3 h-3" />
            <span className="hidden sm:inline">Yenile</span>
          </button>

          <button
            onClick={() => setIsOpen(!isOpen)}
            className="text-slate-400 hover:text-white p-1 rounded hover:bg-slate-800 transition-colors flex items-center space-x-1 text-[11px] cursor-pointer"
          >
            <span>{isOpen ? 'Konsolu Gizle' : 'Logları Göster'}</span>
            {isOpen ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronUp className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* Expanded Real Operation Log Stream */}
      {isOpen && (
        <div className="max-w-[1920px] mx-auto px-4 py-3 max-h-56 overflow-y-auto space-y-1.5 font-mono text-[11px] animate-in fade-in slide-in-from-bottom-2">
          {logs.length === 0 ? (
            <div className="py-6 text-center text-slate-500 italic">
              Henüz bir operasyonel log kaydı bulunmuyor. Yeni randevu oluşturulduğunda, nizamiyeden araç girdiğinde veya rampa çağrısı yapıldığında olaylar burada zaman damgalı olarak akacaktır.
            </div>
          ) : (
            logs.map(log => (
              <div 
                key={log.id} 
                className="flex items-center space-x-2.5 py-1 px-2.5 rounded bg-black/40 border border-slate-800 hover:border-slate-700"
              >
                <span className="text-slate-500 text-[10px] flex-shrink-0">
                  {log.timestamp}
                </span>

                <span className={`px-1.5 py-0.2 rounded text-[9px] font-bold uppercase ${
                  log.severity === 'success' ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' :
                  log.severity === 'warn' ? 'bg-amber-950 text-amber-300 border border-amber-800' :
                  log.severity === 'error' ? 'bg-rose-950 text-rose-300 border border-rose-800' :
                  'bg-cyan-950 text-cyan-300 border border-cyan-800'
                }`}>
                  {log.event_type}
                </span>

                <span className="text-slate-200 truncate flex-1">
                  {log.message}
                </span>

                {log.plate && (
                  <span className="text-cyan-400 font-bold font-mono text-[10px] bg-slate-900 px-1.5 py-0.5 rounded border border-slate-800">
                    {log.plate}
                  </span>
                )}

                {log.dock && (
                  <span className="text-purple-300 text-[10px] bg-purple-950/70 px-1.5 py-0.5 rounded border border-purple-800">
                    {log.dock}
                  </span>
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};

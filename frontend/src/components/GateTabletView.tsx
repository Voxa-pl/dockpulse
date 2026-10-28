import React, { useState } from 'react';
import { Appointment } from '../types';
import { 
  ShieldCheck, Sun, Moon, Search, CheckCircle2, AlertTriangle, 
  Camera, ArrowRight, Truck, QrCode, Clock, KeyRound, LogOut 
} from 'lucide-react';
import { apiService } from '../api/client';

interface GateTabletViewProps {
  todayAppointments: Appointment[];
  onRefresh: () => void;
}

export const GateTabletView: React.FC<GateTabletViewProps> = ({
  todayAppointments,
  onRefresh
}) => {
  const [sunlightMode, setSunlightMode] = useState(false);
  const [inputPlate, setInputPlate] = useState('');
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  
  // Override state
  const [overrideModalApp, setOverrideModalApp] = useState<Appointment | null>(null);
  const [actualPlateInput, setActualPlateInput] = useState('');
  const [overrideReason, setOverrideReason] = useState('Plaka Değişimi (Taşeron Arızası)');

  const handleCheckIn = async (plateOrToken: string) => {
    if (!plateOrToken.trim()) return;
    setLoading(true);
    setFeedback(null);
    try {
      const res = await apiService.gateCheckIn(plateOrToken.trim());
      setFeedback({ type: 'success', message: res.message });
      setInputPlate('');
      onRefresh();
    } catch (err: any) {
      setFeedback({
        type: 'error',
        message: err.response?.data?.detail || err.message || 'Giriş reddedildi. Randevu veya plaka bulunamadı.'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleExecuteOverride = async () => {
    if (!overrideModalApp || !actualPlateInput.trim()) return;
    setLoading(true);
    try {
      const res = await apiService.gateOverride({
        appointment_id: overrideModalApp.id,
        actual_plate: actualPlateInput.trim(),
        override_reason: overrideReason
      });
      setFeedback({ type: 'success', message: res.message });
      setOverrideModalApp(null);
      setActualPlateInput('');
      onRefresh();
    } catch (err: any) {
      alert(err.response?.data?.detail || err.message || 'Override hatası');
    } finally {
      setLoading(false);
    }
  };

  const handleCheckOut = async (appId: string, plate: string) => {
    try {
      await apiService.gateCheckOut(appId);
      setFeedback({ type: 'success', message: `${plate} plakalı araç çıkış yaptı. Güvenlik çıkış bariyeri açıldı.` });
      onRefresh();
    } catch (err: any) {
      alert(err.response?.data?.detail || err.message || 'Çıkış yapılamadı');
    }
  };

  // Filter scheduled vehicles waiting to enter gate
  const pendingAtGate = todayAppointments.filter(a => a.status === 'SCHEDULED');
  const onSiteVehicles = todayAppointments.filter(a => 
    a.status === 'WAITING_LOT' || a.status === 'CALLED' || a.status === 'UNLOADING' || a.status === 'COMPLETED'
  );

  return (
    <div className={`p-4 max-w-5xl mx-auto space-y-4 transition-colors ${
      sunlightMode ? 'bg-amber-100 text-black min-h-screen' : 'text-slate-100'
    }`}>
      {/* Header with Sunlight Mode Toggle */}
      <div className={`p-4 rounded-2xl flex items-center justify-between border ${
        sunlightMode ? 'bg-white border-amber-300 shadow-md text-black' : 'bg-charcoal-800 border-charcoal-700 shadow-xl'
      }`}>
        <div className="flex items-center space-x-3">
          <div className="w-12 h-12 rounded-xl bg-amber-600 flex items-center justify-center text-white shadow-lg shadow-amber-600/30">
            <ShieldCheck className="w-7 h-7" />
          </div>
          <div>
            <h2 className="text-lg font-black tracking-tight">NİZAMİYE GÜVENLİK TABLETİ</h2>
            <p className={`text-xs ${sunlightMode ? 'text-slate-600' : 'text-slate-400'}`}>
              Canlı Plaka Kontrolü, Randevu Sorgulama ve Otomatik Kapı Giriş / Çıkış Modülü
            </p>
          </div>
        </div>

        {/* Sunlight High Contrast Mode Toggle */}
        <button
          onClick={() => setSunlightMode(!sunlightMode)}
          className={`flex items-center space-x-2 px-4 py-2.5 rounded-xl font-bold text-xs transition-all cursor-pointer shadow ${
            sunlightMode 
              ? 'bg-black text-white hover:bg-slate-800' 
              : 'bg-amber-500/20 text-amber-300 border border-amber-500/40 hover:bg-amber-500/30'
          }`}
        >
          {sunlightMode ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4 text-amber-400" />}
          <span>{sunlightMode ? 'Karanlık Moda Dön' : 'Güneş Işığı Modu (2500+ Lux)'}</span>
        </button>
      </div>

      {/* Feedback Banner */}
      {feedback && (
        <div className={`p-4 rounded-xl flex items-center justify-between font-bold text-sm shadow-lg animate-in fade-in ${
          feedback.type === 'success'
            ? sunlightMode ? 'bg-emerald-200 border-2 border-emerald-600 text-emerald-950' : 'bg-emerald-950 border border-emerald-500 text-emerald-300'
            : sunlightMode ? 'bg-red-200 border-2 border-red-600 text-red-950' : 'bg-red-950 border border-red-500 text-red-300'
        }`}>
          <div className="flex items-center space-x-2">
            {feedback.type === 'success' ? <CheckCircle2 className="w-5 h-5 flex-shrink-0" /> : <AlertTriangle className="w-5 h-5 flex-shrink-0" />}
            <span>{feedback.message}</span>
          </div>
          <button onClick={() => setFeedback(null)} className="text-sm font-black px-2">✕</button>
        </div>
      )}

      {/* Main Large Touch Action Panel */}
      <div className={`p-6 rounded-2xl border space-y-4 ${
        sunlightMode ? 'bg-white border-amber-300 shadow-md' : 'bg-charcoal-800 border-charcoal-700 shadow-xl'
      }`}>
        <div className="text-xs font-bold uppercase tracking-wider text-slate-400">
          PLAKA GİRİŞİ VEYA ŞOFÖR QR / TAKİP KODU
        </div>

        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <input
              type="text"
              value={inputPlate}
              onChange={(e) => setInputPlate(e.target.value.toUpperCase())}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleCheckIn(inputPlate);
              }}
              placeholder="Araç Plakası veya Takip Kodu (Örn: RR-XXXX)"
              className={`w-full h-16 text-xl sm:text-2xl font-black font-mono tracking-wider px-5 rounded-xl border-2 focus:outline-none transition-all uppercase ${
                sunlightMode 
                  ? 'bg-amber-50 border-amber-500 text-black focus:ring-4 focus:ring-amber-400' 
                  : 'bg-charcoal-900 border-charcoal-600 text-white focus:border-amber-500 focus:ring-2 focus:ring-amber-500/20'
              }`}
            />
          </div>

          <button
            disabled={loading || !inputPlate.trim()}
            onClick={() => handleCheckIn(inputPlate)}
            className="h-16 px-8 rounded-xl font-black text-base bg-amber-600 hover:bg-amber-500 text-white shadow-xl shadow-amber-600/30 flex items-center justify-center space-x-2 transition-all cursor-pointer disabled:opacity-50"
          >
            <Truck className="w-6 h-6" />
            <span>KONTROL ET & İÇERİ AL</span>
          </button>
        </div>
      </div>

      {/* Today's Gate Queue Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Waiting to enter (SCHEDULED) */}
        <div className={`p-4 rounded-2xl border space-y-3 ${
          sunlightMode ? 'bg-white border-amber-300' : 'bg-charcoal-800 border-charcoal-700'
        }`}>
          <div className="flex items-center justify-between border-b border-charcoal-700/60 pb-2">
            <h3 className="text-sm font-black flex items-center space-x-2">
              <Clock className="w-4 h-4 text-blue-500" />
              <span>KAPIYA GELMESİ BEKLENENLER</span>
            </h3>
            <span className="text-xs font-bold font-mono px-2 py-0.5 rounded bg-blue-950 text-blue-300 border border-blue-800">
              {pendingAtGate.length} Araç
            </span>
          </div>

          <div className="space-y-2 max-h-[420px] overflow-y-auto">
            {pendingAtGate.length === 0 ? (
              <div className="py-12 text-center text-xs text-slate-500 italic">
                Bekleyen planlı randevu bulunmuyor. Yeni randevu oluşturulduğunda buraya otomatik yansıyacaktır.
              </div>
            ) : (
              pendingAtGate.map(app => (
                <div
                  key={app.id}
                  className={`p-3 rounded-xl border flex items-center justify-between ${
                    sunlightMode ? 'bg-amber-50 border-amber-300' : 'bg-charcoal-900 border-charcoal-700'
                  }`}
                >
                  <div>
                    <div className="font-mono font-black text-base text-white">{app.vehicle_plate}</div>
                    <div className="text-xs text-slate-400">{app.carrier_name} • {app.driver_name}</div>
                    <div className="text-[11px] text-cyan-400 font-mono mt-0.5">
                      Randevu: {new Date(app.slot_start).toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' })} ({app.calculated_duration_minutes} dk) • Ref: {app.tracking_token}
                    </div>
                  </div>

                  <div className="flex items-center space-x-1.5">
                    <button
                      onClick={() => handleCheckIn(app.vehicle_plate)}
                      className="bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs px-3 py-2 rounded-lg flex items-center space-x-1 shadow transition-colors cursor-pointer"
                      title="Nizamiye Girişi Yap"
                    >
                      <CheckCircle2 className="w-4 h-4" />
                      <span>Kabul Et</span>
                    </button>

                    <button
                      onClick={() => {
                        setOverrideModalApp(app);
                        setActualPlateInput(app.vehicle_plate);
                      }}
                      className="text-slate-400 hover:text-white p-2 rounded hover:bg-charcoal-800"
                      title="Plaka Değişimi / Taşeron Override"
                    >
                      <KeyRound className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Currently inside yard/docks */}
        <div className={`p-4 rounded-2xl border space-y-3 ${
          sunlightMode ? 'bg-white border-amber-300' : 'bg-charcoal-800 border-charcoal-700'
        }`}>
          <div className="flex items-center justify-between border-b border-charcoal-700/60 pb-2">
            <h3 className="text-sm font-black flex items-center space-x-2">
              <Truck className="w-4 h-4 text-emerald-500" />
              <span>SAHA İÇİNDEKİ ARAÇLAR (PARK & RAMPA)</span>
            </h3>
            <span className="text-xs font-bold font-mono px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800">
              {onSiteVehicles.length} Araç Sahada
            </span>
          </div>

          <div className="space-y-2 max-h-[420px] overflow-y-auto">
            {onSiteVehicles.length === 0 ? (
              <div className="py-12 text-center text-xs text-slate-500 italic">
                Şu anda saha içinde veya tır parkında araç bulunmuyor.
              </div>
            ) : (
              onSiteVehicles.map(app => (
                <div
                  key={app.id}
                  className={`p-3 rounded-xl border flex items-center justify-between ${
                    sunlightMode ? 'bg-amber-50 border-amber-300' : 'bg-charcoal-900 border-charcoal-700'
                  }`}
                >
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="font-mono font-black text-base text-white">{app.vehicle_plate}</span>
                      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded font-mono ${
                        app.status === 'COMPLETED' ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' :
                        app.status === 'UNLOADING' ? 'bg-blue-950 text-blue-300 border border-blue-800' :
                        app.status === 'CALLED' ? 'bg-purple-950 text-purple-300 border border-purple-800' :
                        'bg-amber-950 text-amber-300 border border-amber-800'
                      }`}>
                        {app.status === 'COMPLETED' ? 'KABUL BİTTİ' :
                         app.status === 'UNLOADING' ? 'BOŞALTMADA' :
                         app.status === 'CALLED' ? 'YANAŞIYOR' : 'TIR PARKINDAN BEKLİYOR'}
                      </span>
                    </div>
                    <div className="text-xs text-slate-400 mt-0.5">{app.carrier_name}</div>
                  </div>

                  <div>
                    {app.status === 'COMPLETED' ? (
                      <button
                        onClick={() => handleCheckOut(app.id, app.vehicle_plate)}
                        className="bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs px-3 py-2 rounded-lg shadow transition-colors flex items-center space-x-1 cursor-pointer"
                      >
                        <LogOut className="w-4 h-4" />
                        <span>Bariyeri Aç (Çıkış)</span>
                      </button>
                    ) : (
                      <span className="text-[11px] text-slate-500 italic">İçeride İşlemde</span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Override Modal */}
      {overrideModalApp && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-charcoal-900 border border-charcoal-700 p-6 rounded-2xl w-full max-w-md space-y-4 shadow-2xl">
            <h3 className="text-base font-bold text-white flex items-center space-x-2">
              <KeyRound className="w-5 h-5 text-amber-400" />
              <span>Taşeron / Plaka Değişimi (Güvenlik Override)</span>
            </h3>

            <div className="text-xs text-slate-300 space-y-1">
              <div>Planlanan Randevu Plakası: <strong className="text-white font-mono">{overrideModalApp.vehicle_plate}</strong></div>
              <div>Taşıyıcı Firma: <strong className="text-white">{overrideModalApp.carrier_name}</strong></div>
            </div>

            <div>
              <label className="text-xs text-slate-400 block mb-1">Kapıya Fiilen Gelen Yeni Plaka:</label>
              <input
                type="text"
                value={actualPlateInput}
                onChange={(e) => setActualPlateInput(e.target.value.toUpperCase())}
                className="w-full bg-charcoal-800 border border-charcoal-700 rounded-lg p-2.5 text-white font-mono font-bold uppercase focus:outline-none focus:border-amber-500 text-lg"
              />
            </div>

            <div>
              <label className="text-xs text-slate-400 block mb-1">Değişim Gerekçesi:</label>
              <select
                value={overrideReason}
                onChange={(e) => setOverrideReason(e.target.value)}
                className="w-full bg-charcoal-800 border border-charcoal-700 rounded-lg p-2 text-xs text-white"
              >
                <option value="Plaka Değişimi (Taşeron Arızası)">Çekici Arızası / İkame Araç</option>
                <option value="Dorse Değişimi">Dorse Değişimi</option>
                <option value="Acil Sevkiyat Değişimi">Acil Sevkiyat Değişimi</option>
              </select>
            </div>

            <div className="flex items-center justify-end space-x-2 pt-2">
              <button
                onClick={() => setOverrideModalApp(null)}
                className="px-4 py-2 text-xs text-slate-400 hover:text-white"
              >
                İptal
              </button>
              <button
                onClick={handleExecuteOverride}
                disabled={loading || !actualPlateInput.trim()}
                className="bg-amber-600 hover:bg-amber-500 text-white font-bold text-xs px-4 py-2 rounded-lg shadow cursor-pointer disabled:opacity-50"
              >
                {loading ? 'İşleniyor...' : 'Onayla & İçeri Al'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

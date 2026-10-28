import React, { useState, useEffect, useRef } from 'react';
import { 
  Truck, MapPin, Clock, CheckCircle2, Navigation, Volume2, 
  ShieldCheck, AlertTriangle, MessageSquare, Search, Radio 
} from 'lucide-react';
import { apiService } from '../api/client';
import { Facility } from '../types';

interface DriverMobileViewProps {
  facility?: Facility | null;
}

export const DriverMobileView: React.FC<DriverMobileViewProps> = ({ facility }) => {
  const [tokenInput, setTokenInput] = useState('');
  const [driverData, setDriverData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [dockedAcknowledged, setDockedAcknowledged] = useState(false);
  const [audioPlayed, setAudioPlayed] = useState(false);
  const lastStatusRef = useRef<string>('');

  // Tesis Koordinatları (Dinamik)
  const targetCenter = {
    lat: facility?.latitude || 40.8524,
    lng: facility?.longitude || 29.3812
  };
  const geofenceRadius = facility?.geofence_radius_meters || 500;

  // Real Device Geolocation State
  const [gpsCoords, setGpsCoords] = useState<{ lat: number; lng: number } | null>(null);
  const [distanceToDc, setDistanceToDc] = useState<number | null>(null);
  const [isInsideGeofence, setIsInsideGeofence] = useState<boolean>(true);
  const [gpsStatus, setGpsStatus] = useState<string>('GPS Konumu Bekleniyor...');

  // Gerçek Haversine Mesafe Hesaplama Fonksiyonu
  const calculateHaversine = (lat1: number, lon1: number, lat2: number, lon2: number): number => {
    const R = 6371e3; // Metre cinsinden Dünya yarıçapı
    const p1 = (lat1 * Math.PI) / 180;
    const p2 = (lat2 * Math.PI) / 180;
    const dLat = ((lat2 - lat1) * Math.PI) / 180;
    const dLon = ((lon2 - lon1) * Math.PI) / 180;

    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(p1) * Math.cos(p2) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

    return Math.round(R * c);
  };

  // Gerçek Cihaz GPS Takibi (watchPosition)
  useEffect(() => {
    if (!('geolocation' in navigator)) {
      setGpsStatus('Cihazda GPS sensörü desteklenmiyor.');
      return;
    }

    const watchId = navigator.geolocation.watchPosition(
      (pos) => {
        const current = { lat: pos.coords.latitude, lng: pos.coords.longitude };
        setGpsCoords(current);
        const dist = calculateHaversine(current.lat, current.lng, targetCenter.lat, targetCenter.lng);
        setDistanceToDc(dist);
        const inside = dist <= geofenceRadius;
        setIsInsideGeofence(inside);
        setGpsStatus(
          inside 
            ? `Saha İçi Doğrulandı (${dist}m, Sapma: ±${Math.round(pos.coords.accuracy)}m)`
            : `Saha Dışındasınız (${dist}m uzakta)`
        );
      },
      (err) => {
        setGpsStatus(`GPS Hatası: ${err.message}. Varsayılan saha içi kabul ediliyor.`);
        // Fallback: don't lock driver out if browser denies permission
        setIsInsideGeofence(true);
      },
      { enableHighAccuracy: true, maximumAge: 10000, timeout: 20000 }
    );

    return () => {
      navigator.geolocation.clearWatch(watchId);
    };
  }, [targetCenter.lat, targetCenter.lng, geofenceRadius]);

  // Sesli Anons Fonksiyonu (Web Speech API)
  const triggerVoiceAnnouncement = (plate: string, dockName: string) => {
    try {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        const text = `Dikkat! ${plate} plakalı araç, lütfen derhal ${dockName} nolu rampaya yanaşınız.`;
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'tr-TR';
        utterance.rate = 0.95;
        window.speechSynthesis.speak(utterance);
      }
    } catch (e) {
      console.warn('Speech synthesis error:', e);
    }
  };

  // Randevu / Takip Bilgisini Sorgula
  const handleFetchDriverData = async (queryVal?: string) => {
    const q = (queryVal || tokenInput).trim();
    if (!q) {
      setErrorMessage('Lütfen takip kodunuzu (RR-XXXX) veya araç plakanızı giriniz.');
      return;
    }

    setLoading(true);
    setErrorMessage(null);
    try {
      const data = await apiService.getDriverTracking(q);
      setDriverData(data);

      // Auto-trigger announcement if CALLED
      if (data.status === 'CALLED' && lastStatusRef.current !== 'CALLED' && !audioPlayed) {
        triggerVoiceAnnouncement(data.vehicle_plate, data.assigned_dock || 'Atanan Rampa');
        setAudioPlayed(true);
      }
      lastStatusRef.current = data.status;
    } catch (err: any) {
      setDriverData(null);
      setErrorMessage(err.response?.data?.detail || 'Geçerli bir randevu veya plaka bulunamadı.');
    } finally {
      setLoading(false);
    }
  };

  // URL param token support (e.g. ?token=RR-XXXX)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get('token');
    if (token) {
      setTokenInput(token);
      handleFetchDriverData(token);
    }
  }, []);

  // Poll driver appointment updates every 8s if active appointment is open
  useEffect(() => {
    if (!driverData) return;
    const interval = setInterval(() => {
      handleFetchDriverData(tokenInput);
    }, 8000);
    return () => clearInterval(interval);
  }, [driverData, tokenInput]);

  const handleAcknowledgeDocked = async () => {
    if (!driverData) return;
    try {
      await apiService.startOperation(driverData.id, gpsCoords || undefined);
      setDockedAcknowledged(true);
      handleFetchDriverData(tokenInput);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Rampa yanaşması onaylanamadı');
    }
  };

  return (
    <div className="p-3 sm:p-4 max-w-md mx-auto space-y-4">
      {/* Search Bar: Clean input, no hardcoded default */}
      <div className="bg-charcoal-800 border border-charcoal-700 p-4 rounded-2xl shadow-xl space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span className="text-xs font-bold text-slate-200">
              {facility ? facility.name : 'Tesis Canlı Şoför Takip Sistemi'}
            </span>
          </div>
          <span className="text-[10px] text-slate-400 font-mono">Zero-App Web</span>
        </div>

        <form onSubmit={(e) => { e.preventDefault(); handleFetchDriverData(); }} className="flex gap-2">
          <input
            type="text"
            value={tokenInput}
            onChange={(e) => setTokenInput(e.target.value.toUpperCase())}
            placeholder="Takip Kodu (RR-XXXX) veya Plaka"
            className="flex-1 bg-charcoal-900 border border-charcoal-600 rounded-xl px-3 py-2.5 text-xs text-white placeholder-slate-500 font-mono font-bold uppercase focus:outline-none focus:border-cyan-500"
          />
          <button
            type="submit"
            disabled={loading || !tokenInput.trim()}
            className="bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs px-4 py-2.5 rounded-xl transition-colors cursor-pointer disabled:opacity-50 flex items-center space-x-1"
          >
            <Search className="w-3.5 h-3.5" />
            <span>{loading ? '...' : 'Sorgula'}</span>
          </button>
        </form>

        {errorMessage && (
          <div className="p-2.5 bg-rose-950/60 border border-rose-800 text-rose-300 text-xs rounded-lg flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}
      </div>

      {/* Driver Data Display */}
      {driverData ? (
        <div className="space-y-3 animate-in fade-in">
          {/* Carrier & Vehicle Header Card */}
          <div className="bg-charcoal-800 border border-charcoal-700 p-4 rounded-2xl shadow-lg flex items-center justify-between">
            <div>
              <div className="text-[10px] text-slate-400 font-semibold">{driverData.carrier_name}</div>
              <div className="text-xl font-black font-mono text-white tracking-wider">{driverData.vehicle_plate}</div>
            </div>
            <div className="text-right">
              <div className="text-[10px] text-slate-400">Şoför:</div>
              <div className="text-xs font-bold text-slate-200">{driverData.driver_name}</div>
            </div>
          </div>

          {/* Real Device GPS / Geofence Card (No fake simulation buttons) */}
          <div className={`p-3 rounded-2xl border flex items-center justify-between text-xs transition-all ${
            isInsideGeofence 
              ? 'bg-emerald-950/40 border-emerald-700/60 text-emerald-300' 
              : 'bg-rose-950/40 border-rose-700/60 text-rose-300'
          }`}>
            <div className="flex items-center space-x-2.5">
              <ShieldCheck className={`w-5 h-5 shrink-0 ${isInsideGeofence ? 'text-emerald-400' : 'text-rose-400 animate-pulse'}`} />
              <div>
                <div className="font-bold">
                  {isInsideGeofence ? 'Geofence: Saha İçi Doğrulandı' : 'Geofence: Saha Dışındasınız'}
                </div>
                <div className="text-[10px] opacity-80 font-mono mt-0.5">
                  {gpsStatus}
                </div>
              </div>
            </div>
            <div className="text-right font-mono text-[10px] text-slate-400">
              {gpsCoords ? `${gpsCoords.lat.toFixed(4)}°N` : ''}
            </div>
          </div>

          {/* Big High-Visibility Dashboard Card (Readable from 2-3 meters) */}
          <div className={`p-6 rounded-3xl border-2 text-center shadow-2xl transition-all ${
            driverData.status === 'CALLED'
              ? 'bg-purple-950/70 border-purple-500 shadow-purple-950/50'
              : driverData.status === 'UNLOADING'
              ? 'bg-emerald-950/70 border-emerald-500 shadow-emerald-950/50'
              : driverData.status === 'WAITING_LOT'
              ? 'bg-amber-950/70 border-amber-500 shadow-amber-950/50'
              : 'bg-charcoal-800 border-charcoal-700'
          }`}>
            <div className="text-[11px] font-bold uppercase tracking-wider text-slate-300">
              {driverData.status === 'CALLED'
                ? 'DERHAL RAMPAYA YANAŞINIZ'
                : driverData.status === 'UNLOADING'
                ? 'BOŞALTMA İŞLEMİ DEVAM EDİYOR'
                : driverData.status === 'WAITING_LOT'
                ? 'TIR PARKINDASINIZ — SIRA BEKLENİYOR'
                : 'PLANLI RANDEVU — HENÜZ KAPI GİRİŞİ YAPILMADI'}
            </div>

            {/* Giant 72pt Typography for Ramp Assignment */}
            <div className="text-5xl font-black tracking-tight font-mono my-3 text-white">
              {driverData.assigned_dock || `SIRA: ${driverData.queue_position || 1}`}
            </div>

            <p className="text-xs font-semibold text-slate-200 max-w-xs mx-auto">
              {driverData.instructions}
            </p>

            {/* Sesli Anons Butonu */}
            <div className="mt-3">
              <button
                type="button"
                onClick={() => triggerVoiceAnnouncement(driverData.vehicle_plate, driverData.assigned_dock || 'Rampa')}
                className="inline-flex items-center space-x-1.5 text-xs font-bold text-cyan-400 bg-charcoal-900/80 hover:bg-charcoal-800 px-3 py-1.5 rounded-lg border border-cyan-500/40 cursor-pointer shadow-sm transition-colors"
              >
                <Volume2 className="w-3.5 h-3.5 text-cyan-300" />
                <span>Sesli Anonsu Dinle</span>
              </button>
            </div>
          </div>

          {/* Action Button: RAMPAYA YANAŞTIM */}
          {driverData.status === 'CALLED' && (
            <button
              onClick={handleAcknowledgeDocked}
              disabled={dockedAcknowledged}
              className="w-full h-18 rounded-2xl font-black text-base bg-emerald-600 hover:bg-emerald-500 active:scale-95 text-white shadow-xl shadow-emerald-600/40 flex items-center justify-center space-x-3 transition-all cursor-pointer disabled:opacity-50"
            >
              <CheckCircle2 className="w-6 h-6" />
              <span>{dockedAcknowledged ? 'Körükte Boşaltma Başlatıldı' : 'RAMPAYA YANAŞTIM (Körüğü Başlat)'}</span>
            </button>
          )}

          {/* Tesis İçi Navigasyon ve WhatsApp İletişim */}
          <div className="p-3 bg-charcoal-800 border border-charcoal-700 rounded-2xl text-xs space-y-2">
            <div className="text-[10px] uppercase font-bold text-slate-400 flex items-center space-x-1.5">
              <Navigation className="w-3.5 h-3.5 text-cyan-400" />
              <span>Saha İçi Adımlar</span>
            </div>
            <div className="grid grid-cols-3 gap-1.5 text-center text-[11px] font-bold">
              <div className={`p-2 rounded-lg border ${
                driverData.status === 'SCHEDULED' ? 'bg-cyan-950 border-cyan-500 text-cyan-300' : 'bg-charcoal-900 border-charcoal-700 text-slate-400'
              }`}>
                1. Nizamiye
              </div>
              <div className={`p-2 rounded-lg border ${
                driverData.status === 'WAITING_LOT' ? 'bg-amber-950 border-amber-500 text-amber-300 animate-pulse' : 'bg-charcoal-900 border-charcoal-700 text-slate-400'
              }`}>
                2. Tır Parkı
              </div>
              <div className={`p-2 rounded-lg border ${
                driverData.status === 'CALLED' || driverData.status === 'UNLOADING' ? 'bg-purple-950 border-purple-500 text-purple-300 animate-pulse' : 'bg-charcoal-900 border-charcoal-700 text-slate-400'
              }`}>
                3. {driverData.assigned_dock || 'Rampa'}
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="p-8 text-center text-slate-500 text-xs italic bg-charcoal-800/40 border border-charcoal-800 rounded-2xl">
          Randevu takip kodunuzu (Örn: RR-XXXX) veya plakanızı girip 'Sorgula' butonuna basınız.
        </div>
      )}
    </div>
  );
};

import React, { useState } from 'react';
import { Dock } from '../types';
import { PlusCircle, Calculator, CheckCircle2, X, Sparkles, Copy, Check } from 'lucide-react';
import { apiService } from '../api/client';

interface BookingWizardModalProps {
  docks: Dock[];
  onClose: () => void;
  onSuccess: () => void;
}

export const BookingWizardModal: React.FC<BookingWizardModalProps> = ({
  docks,
  onClose,
  onSuccess
}) => {
  const [carrierName, setCarrierName] = useState('');
  const [vehiclePlate, setVehiclePlate] = useState('');
  const [trailerPlate, setTrailerPlate] = useState('');
  const [driverName, setDriverName] = useState('');
  const [driverPhone, setDriverPhone] = useState('');
  const [loadType, setLoadType] = useState('PALLET');
  const [cargoType, setCargoType] = useState('');
  const [palletCount, setPalletCount] = useState<number>(30);
  const [selectedDockId, setSelectedDockId] = useState<string>('');
  const [poNumber, setPoNumber] = useState('');
  const [hasWaybill, setHasWaybill] = useState(true);
  const [loading, setLoading] = useState(false);
  const [createdResult, setCreatedResult] = useState<any>(null);
  const [copied, setCopied] = useState(false);

  // Dynamic quantum duration preview
  const calculateDuration = () => {
    const docking = 10;
    const handling = loadType === 'BULK' ? palletCount * 2.5 : palletCount * 1.2;
    const inspection = loadType === 'REEFER' ? 15 : 5;
    const buffer = 5;
    const raw = docking + handling + inspection + buffer;
    return Math.max(30, Math.ceil(raw / 15) * 15);
  };

  const calculatedDuration = calculateDuration();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!carrierName.trim() || !vehiclePlate.trim() || !driverName.trim() || !driverPhone.trim()) {
      alert('Lütfen taşıyıcı, plaka, şoför ve telefon bilgilerini eksiksiz giriniz.');
      return;
    }

    setLoading(true);
    try {
      const now = new Date();
      const slotStart = new Date(now.getTime() + 15 * 60000);

      const created = await apiService.createAppointment({
        carrier_name: carrierName.trim(),
        vehicle_plate: vehiclePlate.toUpperCase().trim(),
        trailer_plate: trailerPlate.toUpperCase().trim() || undefined,
        driver_name: driverName.trim(),
        driver_phone: driverPhone.trim(),
        load_type: loadType,
        cargo_type: cargoType.trim() || undefined,
        estimated_pallets: Number(palletCount) || 1,
        dock_id: selectedDockId || undefined,
        po_number: poNumber.trim() || undefined,
        slot_start: slotStart.toISOString(),
        waybill_image_base64: hasWaybill ? 'WAYBILL_INGESTION_PENDING' : undefined
      });

      setCreatedResult(created);
      onSuccess();
    } catch (err: any) {
      alert(err.response?.data?.detail || err.message || 'Randevu oluşturulamadı');
    } finally {
      setLoading(false);
    }
  };

  const copyTracking = () => {
    if (!createdResult) return;
    const trackingUrl = `${window.location.origin}/?tab=driver&token=${createdResult.tracking_token}`;
    navigator.clipboard.writeText(trackingUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-sm flex items-center justify-center p-3 sm:p-5 overflow-y-auto">
      <div className="bg-charcoal-900 border border-charcoal-700 rounded-2xl w-full max-w-xl overflow-hidden shadow-2xl animate-in zoom-in-95 my-auto max-h-[94vh] flex flex-col">
        {/* Header */}
        <div className="bg-charcoal-800 px-5 py-4 border-b border-charcoal-700 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-white shadow-lg shadow-cyan-500/20">
              <PlusCircle className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">Yeni Rampa Randevusu Oluştur</h3>
              <p className="text-xs text-slate-400">15-Dakikalık Kuantum Tabanlı Dinamik Slotlama</p>
            </div>
          </div>
          <button 
            onClick={onClose} 
            className="text-slate-400 hover:text-white p-1 rounded hover:bg-charcoal-700 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 overflow-y-auto space-y-4">
          {createdResult ? (
            /* Success confirmation card with real tracking token */
            <div className="p-5 bg-emerald-950/40 border border-emerald-800/80 rounded-2xl text-center space-y-4">
              <div className="w-12 h-12 bg-emerald-600/20 border border-emerald-500 rounded-full flex items-center justify-center mx-auto text-emerald-400">
                <CheckCircle2 className="w-7 h-7" />
              </div>

              <div>
                <h4 className="text-base font-bold text-white">Randevu Başarıyla Oluşturuldu</h4>
                <p className="text-xs text-slate-300 mt-1">
                  Araç doğrudan Nizamiye <strong>"Kapıya Gelmesi Beklenenler"</strong> listesine aktarıldı.
                </p>
              </div>

              <div className="bg-charcoal-900 border border-charcoal-700 p-4 rounded-xl text-left space-y-2">
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-400">Araç Plakası:</span>
                  <span className="font-mono font-bold text-white text-sm">{createdResult.vehicle_plate}</span>
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-400">Taşıyıcı / Şoför:</span>
                  <span className="text-slate-200">{createdResult.carrier_name} • {createdResult.driver_name}</span>
                </div>
                <div className="flex justify-between items-center text-xs border-t border-charcoal-800 pt-2">
                  <span className="text-slate-400">Şoför Takip Kodu:</span>
                  <span className="font-mono font-black text-cyan-400 text-sm tracking-wider">{createdResult.tracking_token}</span>
                </div>
              </div>

              <div className="flex items-center space-x-2">
                <button
                  type="button"
                  onClick={copyTracking}
                  className="flex-1 bg-charcoal-800 hover:bg-charcoal-700 text-slate-200 border border-charcoal-700 font-semibold text-xs py-2 px-3 rounded-lg flex items-center justify-center space-x-1.5 transition-colors cursor-pointer"
                >
                  {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4 text-cyan-400" />}
                  <span>{copied ? 'Bağlantı Kopyalandı' : 'Şoför Takip Linkini Kopyala'}</span>
                </button>
                <button
                  type="button"
                  onClick={onClose}
                  className="bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs py-2 px-4 rounded-lg shadow transition-colors cursor-pointer"
                >
                  Tamamla
                </button>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div>
                  <label className="text-slate-300 font-semibold block mb-1">Nakliye / Taşıyıcı Firma *</label>
                  <input
                    type="text"
                    value={carrierName}
                    onChange={(e) => setCarrierName(e.target.value)}
                    placeholder="Örn: ABC Lojistik A.Ş."
                    required
                    className="w-full bg-charcoal-800 border border-charcoal-700 rounded-lg p-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                  />
                </div>

                <div>
                  <label className="text-slate-300 font-semibold block mb-1">Araç Çekici Plakası *</label>
                  <input
                    type="text"
                    value={vehiclePlate}
                    onChange={(e) => setVehiclePlate(e.target.value.toUpperCase())}
                    placeholder="Örn: 34 ABC 123"
                    required
                    className="w-full bg-charcoal-800 border border-charcoal-700 rounded-lg p-2.5 text-white placeholder-slate-500 font-mono font-bold uppercase focus:outline-none focus:border-cyan-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                <div>
                  <label className="text-slate-300 font-semibold block mb-1">Dorse Plakası (Opsiyonel)</label>
                  <input
                    type="text"
                    value={trailerPlate}
                    onChange={(e) => setTrailerPlate(e.target.value.toUpperCase())}
                    placeholder="Örn: 34 DOR 45"
                    className="w-full bg-charcoal-800 border border-charcoal-700 rounded-lg p-2.5 text-white placeholder-slate-500 font-mono uppercase focus:outline-none focus:border-cyan-500"
                  />
                </div>

                <div>
                  <label className="text-slate-300 font-semibold block mb-1">Şoför Adı Soyadı *</label>
                  <input
                    type="text"
                    value={driverName}
                    onChange={(e) => setDriverName(e.target.value)}
                    placeholder="Örn: Mehmet Özkan"
                    required
                    className="w-full bg-charcoal-800 border border-charcoal-700 rounded-lg p-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                  />
                </div>

                <div>
                  <label className="text-slate-300 font-semibold block mb-1">Şoför Telefonu *</label>
                  <input
                    type="tel"
                    value={driverPhone}
                    onChange={(e) => setDriverPhone(e.target.value)}
                    placeholder="Örn: 0532 555 12 34"
                    required
                    className="w-full bg-charcoal-800 border border-charcoal-700 rounded-lg p-2.5 text-white placeholder-slate-500 font-mono focus:outline-none focus:border-cyan-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                <div>
                  <label className="text-slate-300 font-semibold block mb-1">Yük Tipi:</label>
                  <select
                    value={loadType}
                    onChange={(e) => setLoadType(e.target.value)}
                    className="w-full bg-charcoal-800 border border-charcoal-700 rounded-lg p-2.5 text-white focus:outline-none focus:border-cyan-500"
                  >
                    <option value="PALLET">Standart Palet (Kuru)</option>
                    <option value="REEFER">Soğuk Zincir (Frigo)</option>
                    <option value="BULK">Dökme / Ağır Sanayi</option>
                    <option value="PARCEL">Koli Dağıtım</option>
                  </select>
                </div>

                <div>
                  <label className="text-slate-300 font-semibold block mb-1">Palet / Koli Adedi:</label>
                  <input
                    type="number"
                    min={1}
                    max={120}
                    value={palletCount}
                    onChange={(e) => setPalletCount(parseInt(e.target.value) || 1)}
                    className="w-full bg-charcoal-800 border border-charcoal-700 rounded-lg p-2.5 text-white font-mono focus:outline-none focus:border-cyan-500"
                  />
                </div>

                <div>
                  <label className="text-slate-300 font-semibold block mb-1">Tercih Rampa:</label>
                  <select
                    value={selectedDockId}
                    onChange={(e) => setSelectedDockId(e.target.value)}
                    className="w-full bg-charcoal-800 border border-charcoal-700 rounded-lg p-2.5 text-white focus:outline-none focus:border-cyan-500"
                  >
                    <option value="">Otomatik Rampa Ata</option>
                    {docks.map(d => (
                      <option key={d.id} value={d.id}>
                        {d.dock_number} ({d.dock_type})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div>
                  <label className="text-slate-300 font-semibold block mb-1">Yük Açıklaması / Malzeme</label>
                  <input
                    type="text"
                    value={cargoType}
                    onChange={(e) => setCargoType(e.target.value)}
                    placeholder="Örn: FMCG Kuru Gıda, Temizlik Malzemesi"
                    className="w-full bg-charcoal-800 border border-charcoal-700 rounded-lg p-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                  />
                </div>

                <div>
                  <label className="text-slate-300 font-semibold block mb-1">ERP Satınalma / PO No</label>
                  <input
                    type="text"
                    value={poNumber}
                    onChange={(e) => setPoNumber(e.target.value)}
                    placeholder="Örn: 4500891244"
                    className="w-full bg-charcoal-800 border border-charcoal-700 rounded-lg p-2.5 text-white placeholder-slate-500 font-mono focus:outline-none focus:border-cyan-500"
                  />
                </div>
              </div>

              {/* Quantum Slot Calculator Preview */}
              <div className="bg-charcoal-800/80 border border-charcoal-700 rounded-xl p-3 flex items-center justify-between text-xs">
                <div className="flex items-center space-x-2">
                  <Calculator className="w-4 h-4 text-cyan-400" />
                  <div>
                    <div className="text-white font-bold">Dinamik Slot Hesaplaması:</div>
                    <div className="text-[11px] text-slate-400">
                      {palletCount} Palet • {loadType} elleçleme + 10 dk yanaşma + kontrol
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-lg font-black font-mono text-cyan-400">{calculatedDuration} Dk</div>
                  <div className="text-[10px] text-slate-400 font-mono">({calculatedDuration / 15} Kuantum Blok)</div>
                </div>
              </div>

              {/* DocuLog Checkbox */}
              <label className="flex items-center justify-between p-3 bg-charcoal-800/50 border border-charcoal-700 rounded-xl cursor-pointer hover:border-cyan-500/50 transition-colors">
                <div className="flex items-center space-x-2">
                  <Sparkles className="w-4 h-4 text-cyan-400" />
                  <div>
                    <div className="text-xs font-bold text-white">Waybill Vision AI İrsaliye Ön-Ayrıştırma</div>
                    <div className="text-[11px] text-slate-400">Yoldayken irsaliye taranacak ve ERP PO ile eşlenecek.</div>
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={hasWaybill}
                  onChange={(e) => setHasWaybill(e.target.checked)}
                  className="w-4 h-4 text-cyan-600 rounded bg-charcoal-900 border-charcoal-700"
                />
              </label>

              {/* Action Buttons */}
              <div className="flex items-center justify-end space-x-3 pt-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 rounded-lg text-xs font-semibold text-slate-400 hover:text-white transition-colors cursor-pointer"
                >
                  Vazgeç
                </button>

                <button
                  type="submit"
                  disabled={loading}
                  className="flex items-center space-x-1.5 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white px-5 py-2 rounded-lg text-xs font-bold shadow-lg shadow-cyan-600/20 transition-all cursor-pointer disabled:opacity-50"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  <span>{loading ? 'Randevu Kaydediliyor...' : 'Randevuyu Onayla & Slotu Kilitle'}</span>
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};

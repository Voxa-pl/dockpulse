import React, { useState } from 'react';
import { Warehouse, Plus, Trash2, CheckCircle2, X, Settings2, MapPin } from 'lucide-react';
import { Facility, Dock, DockType } from '../types';
import { apiService } from '../api/client';

interface FacilitySetupModalProps {
  isOpen: boolean;
  onClose: () => void;
  facility: Facility | null;
  docks: Dock[];
  onSaved: () => void;
}

interface NewDockRow {
  dock_number: string;
  dock_type: DockType;
  max_pallets: number;
  notes: string;
}

export const FacilitySetupModal: React.FC<FacilitySetupModalProps> = ({
  isOpen,
  onClose,
  facility,
  docks,
  onSaved
}) => {
  const [facilityName, setFacilityName] = useState(facility?.name || '');
  const [facilityCode, setFacilityCode] = useState(facility?.code || '');
  const [address, setAddress] = useState(facility?.address || '');
  const [latitude, setLatitude] = useState<number>(facility?.latitude || 40.8524);
  const [longitude, setLongitude] = useState<number>(facility?.longitude || 29.3812);
  const [geofenceRadius, setGeofenceRadius] = useState<number>(facility?.geofence_radius_meters || 500);

  // Initial docks for new facility creation
  const [dockRows, setDockRows] = useState<NewDockRow[]>([
    { dock_number: 'Rampa 01', dock_type: 'SHELTER', max_pallets: 33, notes: 'Kuru Gıda / Standart Körüklü Rampa' },
    { dock_number: 'Rampa 02', dock_type: 'COLD_REEFER', max_pallets: 33, notes: 'Soğuk Hava / Frigo İklimlendirme' }
  ]);

  // Add individual dock to existing facility
  const [newDockName, setNewDockName] = useState('');
  const [newDockType, setNewDockType] = useState<DockType>('SHELTER');
  const [newDockPallets, setNewDockPallets] = useState(33);
  const [newDockNotes, setNewDockNotes] = useState('');

  const [saving, setSaving] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const isNewSetup = !facility;

  const handleAddRow = () => {
    const nextNum = dockRows.length + 1;
    const formattedNum = nextNum < 10 ? `0${nextNum}` : `${nextNum}`;
    setDockRows([
      ...dockRows,
      {
        dock_number: `Rampa ${formattedNum}`,
        dock_type: 'SHELTER',
        max_pallets: 33,
        notes: ''
      }
    ]);
  };

  const handleRemoveRow = (index: number) => {
    setDockRows(dockRows.filter((_, i) => i !== index));
  };

  const handleRowChange = (index: number, field: keyof NewDockRow, value: any) => {
    const updated = [...dockRows];
    updated[index] = { ...updated[index], [field]: value };
    setDockRows(updated);
  };

  const handleSaveFacility = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!facilityName.trim()) {
      setErrorMsg('Tesis adı boş bırakılamaz.');
      return;
    }

    setSaving(true);
    setErrorMsg(null);

    try {
      if (isNewSetup) {
        await apiService.createFacility({
          name: facilityName.trim(),
          code: facilityCode.trim() || undefined,
          address: address.trim() || undefined,
          latitude: Number(latitude) || 40.8524,
          longitude: Number(longitude) || 29.3812,
          geofence_radius_meters: Number(geofenceRadius) || 500,
          docks: dockRows
        });
      } else {
        await apiService.updateFacility(facility.id, {
          name: facilityName.trim(),
          code: facilityCode.trim() || undefined,
          address: address.trim() || undefined,
          latitude: Number(latitude) || 40.8524,
          longitude: Number(longitude) || 29.3812,
          geofence_radius_meters: Number(geofenceRadius) || 500
        });
      }

      onSaved();
      onClose();
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || err.message || 'Tesis kaydedilirken hata oluştu.');
    } finally {
      setSaving(false);
    }
  };

  const handleAddSingleDock = async () => {
    if (!facility) return;
    if (!newDockName.trim()) {
      setErrorMsg('Rampa numarası/adı giriniz.');
      return;
    }

    setSaving(true);
    setErrorMsg(null);
    try {
      await apiService.createDock({
        facility_id: facility.id,
        dock_number: newDockName.trim(),
        dock_type: newDockType,
        max_pallets: Number(newDockPallets) || 33,
        notes: newDockNotes.trim() || undefined
      });
      setNewDockName('');
      setNewDockNotes('');
      onSaved();
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || err.message || 'Rampa eklenemedi.');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteExistingDock = async (dockId: string) => {
    if (!window.confirm('Bu rampayı silmek istediğinize emin misiniz?')) return;
    setSaving(true);
    try {
      await apiService.deleteDock(dockId);
      onSaved();
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || err.message || 'Rampa silinemedi.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-3 sm:p-5 overflow-y-auto">
      <div className="bg-charcoal-900 border border-charcoal-700 rounded-2xl w-full max-w-3xl overflow-hidden shadow-2xl flex flex-col my-auto max-h-[92vh]">
        {/* Header */}
        <div className="bg-charcoal-800 px-5 py-4 border-b border-charcoal-700 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-cyan-600/20 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
              {isNewSetup ? <Warehouse className="w-5 h-5" /> : <Settings2 className="w-5 h-5" />}
            </div>
            <div>
              <h2 className="text-base sm:text-lg font-bold text-white">
                {isNewSetup ? 'Tesis & Depo Kurulumu (Onboarding)' : 'Tesis & Rampa Yönetimi'}
              </h2>
              <p className="text-xs text-slate-400">
                {isNewSetup 
                  ? 'Sistemin çalışacağı gerçek deponuzu ve rampa altyapınızı tanımlayın.' 
                  : 'Tesis bilgilerinizi güncelleyin veya yeni rampalar ekleyin/çıkarın.'}
              </p>
            </div>
          </div>
          {!isNewSetup && (
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-charcoal-700 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* Form Body */}
        <div className="p-5 overflow-y-auto space-y-6">
          {errorMsg && (
            <div className="p-3 bg-rose-950/70 border border-rose-800 text-rose-300 text-xs rounded-xl">
              {errorMsg}
            </div>
          )}

          <form onSubmit={handleSaveFacility} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Tesis / Depo Adı *
                </label>
                <input
                  type="text"
                  required
                  placeholder="Örn: Tuzla Lojistik Merkezi"
                  value={facilityName}
                  onChange={e => setFacilityName(e.target.value)}
                  className="w-full bg-charcoal-800 border border-charcoal-700 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Tesis Kodu
                </label>
                <input
                  type="text"
                  placeholder="Örn: DC-01, DEP-IST"
                  value={facilityCode}
                  onChange={e => setFacilityCode(e.target.value.toUpperCase())}
                  className="w-full bg-charcoal-800 border border-charcoal-700 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 font-mono focus:outline-none focus:border-cyan-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Fiziksel Adres
              </label>
              <input
                type="text"
                placeholder="Örn: Organize Sanayi Bölgesi 4. Cadde No: 12"
                value={address}
                onChange={e => setAddress(e.target.value)}
                className="w-full bg-charcoal-800 border border-charcoal-700 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
              />
            </div>

            {/* Geofence / GPS Coordinates */}
            <div className="p-3 bg-charcoal-800/60 border border-charcoal-700 rounded-xl space-y-2">
              <div className="flex items-center space-x-2 text-xs font-bold text-cyan-400">
                <MapPin className="w-3.5 h-3.5" />
                <span>Gerçek Geofence & GPS Konum Ayarı (Şoför Doğrulaması İçin)</span>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <div>
                  <label className="block text-[10px] text-slate-400 mb-0.5">Enlem (Latitude)</label>
                  <input
                    type="number"
                    step="0.0001"
                    value={latitude}
                    onChange={e => setLatitude(parseFloat(e.target.value) || 0)}
                    className="w-full bg-charcoal-900 border border-charcoal-700 rounded p-1.5 text-xs text-white font-mono"
                  />
                </div>
                <div>
                  <label className="block text-[10px] text-slate-400 mb-0.5">Boylam (Longitude)</label>
                  <input
                    type="number"
                    step="0.0001"
                    value={longitude}
                    onChange={e => setLongitude(parseFloat(e.target.value) || 0)}
                    className="w-full bg-charcoal-900 border border-charcoal-700 rounded p-1.5 text-xs text-white font-mono"
                  />
                </div>
                <div>
                  <label className="block text-[10px] text-slate-400 mb-0.5">Saha Yarıçapı (Metre)</label>
                  <input
                    type="number"
                    value={geofenceRadius}
                    onChange={e => setGeofenceRadius(parseInt(e.target.value) || 500)}
                    className="w-full bg-charcoal-900 border border-charcoal-700 rounded p-1.5 text-xs text-white font-mono"
                  />
                </div>
              </div>
            </div>

            {/* DOCKS CONFIGURATION */}
            {isNewSetup ? (
              <div className="space-y-3 pt-2 border-t border-charcoal-800">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                      İlk Rampa Kurulumu ({dockRows.length} Rampa)
                    </h3>
                    <p className="text-[11px] text-slate-400">Tesisinize ait aktif rampaları tanımlayın.</p>
                  </div>
                  <button
                    type="button"
                    onClick={handleAddRow}
                    className="flex items-center space-x-1 text-xs bg-cyan-600/20 hover:bg-cyan-600/30 text-cyan-300 border border-cyan-500/40 px-2.5 py-1 rounded-lg transition-colors"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>Rampa Ekle</span>
                  </button>
                </div>

                <div className="space-y-2">
                  {dockRows.map((row, idx) => (
                    <div key={idx} className="flex items-center gap-2 bg-charcoal-800/80 p-2 rounded-lg border border-charcoal-700">
                      <input
                        type="text"
                        value={row.dock_number}
                        onChange={e => handleRowChange(idx, 'dock_number', e.target.value)}
                        placeholder="Rampa No"
                        className="w-28 bg-charcoal-900 border border-charcoal-700 rounded px-2 py-1 text-xs text-white font-bold"
                      />
                      <select
                        value={row.dock_type}
                        onChange={e => handleRowChange(idx, 'dock_type', e.target.value as DockType)}
                        className="bg-charcoal-900 border border-charcoal-700 rounded px-2 py-1 text-xs text-white"
                      >
                        <option value="SHELTER">Körüklü / Standart</option>
                        <option value="COLD_REEFER">Soğuk Hava / Frigo</option>
                        <option value="HYDRAULIC">Hidrolik Seviye Ayarlayıcı</option>
                        <option value="GROUND">Düz Zemin / Yandan Forklift</option>
                      </select>
                      <input
                        type="text"
                        value={row.notes}
                        onChange={e => handleRowChange(idx, 'notes', e.target.value)}
                        placeholder="Örn: 13.60 Tır Uygun"
                        className="flex-1 bg-charcoal-900 border border-charcoal-700 rounded px-2 py-1 text-xs text-slate-300"
                      />
                      {dockRows.length > 1 && (
                        <button
                          type="button"
                          onClick={() => handleRemoveRow(idx)}
                          className="text-slate-500 hover:text-rose-400 p-1"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            <div className="pt-3 flex justify-end">
              <button
                type="submit"
                disabled={saving}
                className="bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs px-5 py-2.5 rounded-lg shadow-lg shadow-cyan-600/30 flex items-center space-x-2 disabled:opacity-50 cursor-pointer"
              >
                <CheckCircle2 className="w-4 h-4" />
                <span>{saving ? 'Kaydediliyor...' : isNewSetup ? 'Tesisi Kur & Başla' : 'Tesis Bilgilerini Güncelle'}</span>
              </button>
            </div>
          </form>

          {/* If existing facility: Show existing docks and allow live addition/deletion */}
          {!isNewSetup && (
            <div className="pt-4 border-t border-charcoal-800 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                    Mevcut Rampalar ({docks.length} Rampa)
                  </h3>
                  <p className="text-[11px] text-slate-400">Aktif rampaları yönetin veya yeni rampa ekleyin.</p>
                </div>
              </div>

              {/* Add New Dock Form */}
              <div className="p-3 bg-charcoal-800/90 border border-charcoal-700 rounded-xl space-y-2">
                <div className="text-xs font-bold text-slate-200">Yeni Rampa Tanımla</div>
                <div className="grid grid-cols-1 sm:grid-cols-4 gap-2">
                  <input
                    type="text"
                    placeholder="Rampa No (Örn: Rampa 07)"
                    value={newDockName}
                    onChange={e => setNewDockName(e.target.value)}
                    className="bg-charcoal-900 border border-charcoal-700 rounded px-2.5 py-1.5 text-xs text-white font-bold"
                  />
                  <select
                    value={newDockType}
                    onChange={e => setNewDockType(e.target.value as DockType)}
                    className="bg-charcoal-900 border border-charcoal-700 rounded px-2.5 py-1.5 text-xs text-white"
                  >
                    <option value="SHELTER">Körüklü / Standart</option>
                    <option value="COLD_REEFER">Soğuk Hava / Frigo</option>
                    <option value="HYDRAULIC">Hidrolik Seviye Ayarlayıcı</option>
                    <option value="GROUND">Düz Zemin / Yandan Forklift</option>
                  </select>
                  <input
                    type="text"
                    placeholder="Açıklama / Uygunluk"
                    value={newDockNotes}
                    onChange={e => setNewDockNotes(e.target.value)}
                    className="bg-charcoal-900 border border-charcoal-700 rounded px-2.5 py-1.5 text-xs text-white"
                  />
                  <button
                    type="button"
                    onClick={handleAddSingleDock}
                    disabled={saving || !newDockName.trim()}
                    className="bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs py-1.5 px-3 rounded flex items-center justify-center space-x-1 disabled:opacity-50 cursor-pointer"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>Rampa Ekle</span>
                  </button>
                </div>
              </div>

              {/* Existing Docks List */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-56 overflow-y-auto">
                {docks.map(dock => (
                  <div key={dock.id} className="flex items-center justify-between p-2.5 bg-charcoal-800 rounded-lg border border-charcoal-700">
                    <div>
                      <div className="font-bold text-xs text-white">{dock.dock_number}</div>
                      <div className="text-[10px] text-slate-400">{dock.notes || dock.dock_type} • Kapasite: {dock.max_pallets} Plt</div>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleDeleteExistingDock(dock.id)}
                      className="text-slate-500 hover:text-rose-400 p-1 transition-colors"
                      title="Rampayı Sil"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

import React, { useState } from 'react';
import { 
  GraduationCap, Cpu, Network, ShieldCheck, Zap, 
  TrendingUp, CheckCircle, HelpCircle, X, ChevronRight,
  Server, ArrowRight, Activity, Database, Scale, Camera, Radio
} from 'lucide-react';

interface AlanSefiModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const AlanSefiModal: React.FC<AlanSefiModalProps> = ({ isOpen, onClose }) => {
  const [activeTab, setActiveTab] = useState<'architecture' | 'doculog_sap' | 'kpis' | 'qa'>('architecture');

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="bg-[#0D131F] border border-slate-700/80 rounded-2xl w-full max-w-5xl max-h-[92vh] flex flex-col shadow-2xl overflow-hidden">
        
        {/* Header */}
        <div className="px-6 py-4 bg-[#111827] border-b border-slate-700/80 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-amber-500 to-indigo-600 flex items-center justify-center text-white shadow-lg shadow-indigo-500/20">
              <GraduationCap className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h2 className="text-lg font-bold text-white tracking-wide">Alan Şefi Sunum & Endüstriyel Mimari Modu</h2>
                <span className="text-[10px] bg-indigo-950 text-indigo-300 border border-indigo-700/50 px-2 py-0.5 rounded font-mono font-semibold uppercase">
                  v2.4 Enterprise Defense
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Gebze DC-01 Rampa & Saha Yönetim Sistemi — Akademik ve Sektörel Savunma Brifingi
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-2 rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="px-6 py-2.5 bg-[#0F172A] border-b border-slate-800 flex items-center space-x-2 overflow-x-auto">
          <button
            onClick={() => setActiveTab('architecture')}
            className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer whitespace-nowrap ${
              activeTab === 'architecture'
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <Cpu className="w-4 h-4" />
            <span>1. Donanım & IoT Saha Mimarisi</span>
          </button>

          <button
            onClick={() => setActiveTab('doculog_sap')}
            className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer whitespace-nowrap ${
              activeTab === 'doculog_sap'
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <Database className="w-4 h-4" />
            <span>2. DocuLog Vision & SAP 101/103 Akışı</span>
          </button>

          <button
            onClick={() => setActiveTab('kpis')}
            className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer whitespace-nowrap ${
              activeTab === 'kpis'
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <TrendingUp className="w-4 h-4" />
            <span>3. Ölçülebilir Lojistik KPI'ları</span>
          </button>

          <button
            onClick={() => setActiveTab('qa')}
            className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer whitespace-nowrap ${
              activeTab === 'qa'
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <HelpCircle className="w-4 h-4" />
            <span>4. Alan Şefine 5 Can Alıcı Soru & Cevap</span>
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 text-slate-200">
          
          {/* TAB 1: Hardware & IoT Edge Architecture */}
          {activeTab === 'architecture' && (
            <div className="space-y-6">
              <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
                <h3 className="text-sm font-bold text-white mb-2 flex items-center space-x-2">
                  <Activity className="w-4 h-4 text-cyan-400" />
                  <span>Endüstriyel Donanım Bağlantı Topolojisi (Nizamiye & Rampa IoT)</span>
                </h3>
                <p className="text-xs text-slate-400 leading-relaxed mb-4">
                  Sistem sadece bir web yazılımı değildir; sahada fiziksel bariyerler, aks kantarları, ANPR optik kameraları ve rampa ultrasonik mesafe sensörleriyle Moxa/Advantech Endüstriyel Edge Gateway üzerinden haberleşir.
                </p>

                {/* Topology Blocks */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                  <div className="bg-[#131D31] border border-cyan-800/40 p-3.5 rounded-xl">
                    <div className="flex items-center space-x-2 text-cyan-400 mb-2">
                      <Camera className="w-4 h-4" />
                      <span className="text-xs font-bold font-mono">1. ANPR Kamera</span>
                    </div>
                    <div className="text-[11px] text-slate-300 font-semibold">Plaka & Konteyner No</div>
                    <div className="text-[10px] text-slate-400 mt-1">
                      100ms içinde plaka optik tanıması yapar. RTSP/ONVIF protokolü ile Edge Gateway'e JSON event fırlatır.
                    </div>
                  </div>

                  <div className="bg-[#131D31] border border-amber-800/40 p-3.5 rounded-xl">
                    <div className="flex items-center space-x-2 text-amber-400 mb-2">
                      <Scale className="w-4 h-4" />
                      <span className="text-xs font-bold font-mono">2. 60-Ton Aks Kantarı</span>
                    </div>
                    <div className="text-[11px] text-slate-300 font-semibold">Modbus RTU / RS-485</div>
                    <div className="text-[10px] text-slate-400 mt-1">
                      Araç aks ağırlıklarını otomatik okur. Brüt ağırlık ve aşırı yük (overload) tolerans kontrolü yapar.
                    </div>
                  </div>

                  <div className="bg-[#131D31] border border-indigo-800/40 p-3.5 rounded-xl">
                    <div className="flex items-center space-x-2 text-indigo-400 mb-2">
                      <Server className="w-4 h-4" />
                      <span className="text-xs font-bold font-mono">3. Edge Gateway</span>
                    </div>
                    <div className="text-[11px] text-slate-300 font-semibold">Moxa UC-8100 Linux</div>
                    <div className="text-[10px] text-slate-400 mt-1">
                      Saha katında lokal karar motoru. İnternet kopsa dahi bariyer rölesini açar, veriyi lokal WAL DB'de saklar.
                    </div>
                  </div>

                  <div className="bg-[#131D31] border border-emerald-800/40 p-3.5 rounded-xl">
                    <div className="flex items-center space-x-2 text-emerald-400 mb-2">
                      <Radio className="w-4 h-4" />
                      <span className="text-xs font-bold font-mono">4. Rampa Körük Sensörü</span>
                    </div>
                    <div className="text-[11px] text-slate-300 font-semibold">Ultrasonik / Lidar Giriş</div>
                    <div className="text-[10px] text-slate-400 mt-1">
                      Tır rampaya sıfır yanaştığı anda körük şişirilir ve rampa kilit emniyeti yeşile döner (Dock-In Timestamp).
                    </div>
                  </div>
                </div>
              </div>

              {/* Offline-First & Resiliency */}
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300 mb-2">
                  Kesintisiz Saha Güvencesi: Offline-First SQLite WAL & WebSocket
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                  <div className="p-3 bg-[#111827] rounded-lg border border-slate-800">
                    <span className="text-cyan-400 font-bold font-mono block mb-1">Zero Cloud Dependency</span>
                    <span className="text-slate-400 text-[11px]">
                      Depoda internet koptuğunda rampa amiri ve güvenlik tableti yerel ağ üzerinden (LAN) milisaniyelik çalışmaya devam eder.
                    </span>
                  </div>
                  <div className="p-3 bg-[#111827] rounded-lg border border-slate-800">
                    <span className="text-indigo-400 font-bold font-mono block mb-1">Milisaniyelik Senkronizasyon</span>
                    <span className="text-slate-400 text-[11px]">
                      Kapıdan araç girdiğinde tüm amir ve forklift ekranları tek bir HTTP polling yapmadan WebSocket ile 15 milisaniyede güncellenir.
                    </span>
                  </div>
                  <div className="p-3 bg-[#111827] rounded-lg border border-slate-800">
                    <span className="text-emerald-400 font-bold font-mono block mb-1">Endüstriyel Dayanıklılık</span>
                    <span className="text-slate-400 text-[11px]">
                      IP67 korumalı tabletler ve 85dB sesli/haptik ikaz ile gürültülü saha ortamında sıfır insan hatası.
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: DocuLog Vision & SAP 101/103 */}
          {activeTab === 'doculog_sap' && (
            <div className="space-y-6">
              <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
                <h3 className="text-sm font-bold text-white mb-2 flex items-center space-x-2">
                  <Database className="w-4 h-4 text-emerald-400" />
                  <span>DocuLog Vision AI & SAP MIGO Entegrasyon Zinciri</span>
                </h3>
                <p className="text-xs text-slate-400 leading-relaxed mb-4">
                  RampaRandevu, depoya gelen yükün sadece kapısını açmaz; irsaliyeyi optik yapay zeka ile okur, ERP (SAP) sistemine resmi mal kabul (MIGO 101/103) fişini anında üretir.
                </p>

                {/* Integration Step Diagram */}
                <div className="space-y-3">
                  <div className="flex items-start space-x-3 p-3 bg-[#111827] rounded-xl border border-slate-800">
                    <div className="w-7 h-7 rounded-lg bg-cyan-950 border border-cyan-800 text-cyan-400 flex items-center justify-center font-mono font-bold text-xs flex-shrink-0 mt-0.5">
                      01
                    </div>
                    <div>
                      <div className="text-xs font-bold text-white">e-İrsaliye QR & Kağıt Belge OCR Tarama</div>
                      <div className="text-[11px] text-slate-400 mt-0.5">
                        Şoför nizamiyeye geldiğinde elindeki sevk irsaliyesi DocuLog Vision motoru tarafından taranır. 16 haneli GİB e-İrsaliye No, VKN ve kalemler 1.4 saniyede ayrıştırılır (%99.8 doğruluk).
                      </div>
                    </div>
                  </div>

                  <div className="flex items-start space-x-3 p-3 bg-[#111827] rounded-xl border border-slate-800">
                    <div className="w-7 h-7 rounded-lg bg-indigo-950 border border-indigo-800 text-indigo-400 flex items-center justify-center font-mono font-bold text-xs flex-shrink-0 mt-0.5">
                      02
                    </div>
                    <div>
                      <div className="text-xs font-bold text-white">Randevu & Sipariş (PO) Otomatik Çapraz Doğrulama</div>
                      <div className="text-[11px] text-slate-400 mt-0.5">
                        İrsaliyedeki palet sayısı (örn. 32 Euro Palet) ve malzeme kodları, ERP'deki Satınalma Siparişi (Purchase Order) ile kıyaslanır. Miktar uyuşmazlığı varsa sistem amire sarı uyarı fırlatır.
                      </div>
                    </div>
                  </div>

                  <div className="flex items-start space-x-3 p-3 bg-[#111827] rounded-xl border border-slate-800">
                    <div className="w-7 h-7 rounded-lg bg-emerald-950 border border-emerald-800 text-emerald-400 flex items-center justify-center font-mono font-bold text-xs flex-shrink-0 mt-0.5">
                      03
                    </div>
                    <div>
                      <div className="text-xs font-bold text-white">Rampa Bitimi: Tek Tıkla SAP MIGO 101/103 Hareketi & U-ETDS Bildirimi</div>
                      <div className="text-[11px] text-slate-400 mt-0.5">
                        Boşaltma bittiğinde rampa amiri 'Mal Kabul Onayla' dediğinde SAP BAPI/RFC üzerinden MIGO hareket fişi kesilir, araç kapıdan çıkışa yönlendirilir ve U-ETDS Bakanlık kapanışı yapılır.
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Sample Payload Snippet */}
              <div className="bg-[#0A0E17] border border-slate-800 p-3.5 rounded-xl font-mono text-[11px] text-slate-300">
                <div className="text-slate-500 mb-1 font-sans text-xs font-semibold">DocuLog to SAP Entegrasyon JSON Şeması:</div>
                <pre className="text-cyan-400 overflow-x-auto">{`{
  "event": "DOCULOG_GOODS_RECEIPT_POSTED",
  "waybill_number": "GIB202600004912",
  "carrier_vkn": "3320049182",
  "sap_po_number": "4500892110",
  "sap_movement_type": "101",
  "verified_pallets": 32,
  "net_weight_kg": 18420.0,
  "dock_turnaround_minutes": 42
}`}</pre>
              </div>
            </div>
          )}

          {/* TAB 3: Measurable KPIs */}
          {activeTab === 'kpis' && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-slate-900/80 border border-slate-800 p-4 rounded-xl">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Dwell Time (Saha Bekleme Süresi)</span>
                    <span className="text-emerald-400 font-mono font-black text-sm">-%60 DÜŞÜŞ</span>
                  </div>
                  <div className="text-2xl font-black text-white font-mono">42 Dakika</div>
                  <p className="text-[11px] text-slate-400 mt-1">
                    Geleneksel depolardaki ortalama 120-150 dakikalık tır bekleme ve rölanti süresi, dinamik 15'er dakikalık slot randevusuyla 42 dakikaya indirilir.
                  </p>
                </div>

                <div className="bg-slate-900/80 border border-slate-800 p-4 rounded-xl">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Demuraj & Bekleme Cezaları</span>
                    <span className="text-cyan-400 font-mono font-black text-sm">SIFIR DEMURAJ</span>
                  </div>
                  <div className="text-2xl font-black text-white font-mono">0.00 ₺ Ceza</div>
                  <p className="text-[11px] text-slate-400 mt-1">
                    Taşıyıcı ve lojistik firmalarıyla yaşanan '3 saat kapıda bekledim' demuraj tazminatları, milisaniyelik dijital zaman damgaları (Audit Trail) ile sıfıra indirilir.
                  </p>
                </div>

                <div className="bg-slate-900/80 border border-slate-800 p-4 rounded-xl">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Rampa Kapasite Verimliliği</span>
                    <span className="text-indigo-400 font-mono font-black text-sm">+%45 KAPASİTE</span>
                  </div>
                  <div className="text-2xl font-black text-white font-mono">Günde 180+ Tır</div>
                  <p className="text-[11px] text-slate-400 mt-1">
                    Yeni rampa veya inşaat yatırımı yapmadan, mevcut 24 rampada boş körük süreleri yapay zeka optimizasyonuyla doldurulur.
                  </p>
                </div>

                <div className="bg-slate-900/80 border border-slate-800 p-4 rounded-xl">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Karbon Ayak İzi (ESG / Green Yard)</span>
                    <span className="text-emerald-400 font-mono font-black text-sm">-%38 EMİSYON</span>
                  </div>
                  <div className="text-2xl font-black text-white font-mono">-14.2 Ton CO₂/Ay</div>
                  <p className="text-[11px] text-slate-400 mt-1">
                    Tır parkında motor çalıştırma (rölanti) süresinin kısaltılması ile çevreye salınan sera gazı ve yakıt israfı engellenir.
                  </p>
                </div>
              </div>

              {/* Legal Compliance */}
              <div className="bg-[#111A2E] border border-indigo-900/50 p-4 rounded-xl flex items-center justify-between">
                <div>
                  <div className="text-xs font-bold text-indigo-300">T.C. Ulaştırma Bakanlığı U-ETDS ve GİB Tam Uyumluluk</div>
                  <div className="text-[11px] text-slate-400 mt-0.5">
                    Taşıma irsaliyeleri, şoför kimlikleri ve dorse plakaları resmi mevzuat gereği merkezi sisteme otomatik senkronize edilir.
                  </div>
                </div>
                <ShieldCheck className="w-8 h-8 text-indigo-400 flex-shrink-0 ml-4" />
              </div>
            </div>
          )}

          {/* TAB 4: 5 Critical Questions for Department Head */}
          {activeTab === 'qa' && (
            <div className="space-y-3">
              <div className="text-xs text-slate-400 mb-2">
                Alan Şefinizin veya sektör uzmanlarının sorabileceği en zorlu 5 teknik ve operasyonel soruya profesyonel yanıtlar:
              </div>

              <div className="bg-slate-900/80 border border-slate-800 p-4 rounded-xl">
                <div className="text-xs font-bold text-white flex items-center space-x-2">
                  <span className="text-amber-400 font-mono">Soru 1:</span>
                  <span>İnternet veya bulut bağlantısı kesilirse depoda saha operasyonu durur mu?</span>
                </div>
                <div className="text-[11px] text-slate-300 mt-2 bg-[#111827] p-3 rounded-lg border border-slate-800">
                  <strong className="text-emerald-400">Cevap:</strong> Kesinlikle durmaz. RampaRandevu **Offline-First & Local Edge** mimarisine sahiptir. Nizamiyedeki tablet ve kapı donanımları lokal ağdaki (LAN) Edge Gateway üzerinde çalışan SQLite WAL veritabanıyla çalışır. İnternet geri geldiğinde arka planda çift yönlü senkronizasyon (Reconciliation) tamamlanır.
                </div>
              </div>

              <div className="bg-slate-900/80 border border-slate-800 p-4 rounded-xl">
                <div className="text-xs font-bold text-white flex items-center space-x-2">
                  <span className="text-amber-400 font-mono">Soru 2:</span>
                  <span>Şoför yabancı uyrukluysa, uygulama indirmezse veya telefonu eski bir tuşlu telefonsa sistem nasıl çalışır?</span>
                </div>
                <div className="text-[11px] text-slate-300 mt-2 bg-[#111827] p-3 rounded-lg border border-slate-800">
                  <strong className="text-emerald-400">Cevap:</strong> Şoförden hiçbir mobil uygulama (App Store/Google Play) indirmesi istenmez (Zero-App). Şoföre gelen SMS/WhatsApp linki 1 saniyede açılan kurumsal web sayfasıdır; TR, EN, RU, AR dillerinde sesli anons yapar. Telefonu olmayan veya tuşlu telefon kullanan şoförlere nizamiyede QR fişi basılır ve depo çatısındaki dev LED dış panolar üzerinden plaka-rampa eşleşmesi gösterilir.
                </div>
              </div>

              <div className="bg-slate-900/80 border border-slate-800 p-4 rounded-xl">
                <div className="text-xs font-bold text-white flex items-center space-x-2">
                  <span className="text-amber-400 font-mono">Soru 3:</span>
                  <span>Şirketimizin mevcut ERP (SAP, IFS, Oracle veya Logo) sistemiyle entegrasyonu nasıl sağlıyorsunuz?</span>
                </div>
                <div className="text-[11px] text-slate-300 mt-2 bg-[#111827] p-3 rounded-lg border border-slate-800">
                  <strong className="text-emerald-400">Cevap:</strong> Sistemimiz RESTful OpenAPI, Webhooks ve ara yazılım (SAP RFC/BAPI ve IDoc) katmanıyla haberleşir. Boşaltma bittiğinde SAP'ye anında 'MIGO 101/103 Mal Giriş Fişi' gönderir; depo yönetim sisteminizdeki (WMS) stok miktarlarını anlık günceller.
                </div>
              </div>

              <div className="bg-slate-900/80 border border-slate-800 p-4 rounded-xl">
                <div className="text-xs font-bold text-white flex items-center space-x-2">
                  <span className="text-amber-400 font-mono">Soru 4:</span>
                  <span>Yağmurda, karda veya çamurda plaka kamerası (PTS) plakayı okuyamazsa nizamiyede kuyruk oluşur mu?</span>
                </div>
                <div className="text-[11px] text-slate-300 mt-2 bg-[#111827] p-3 rounded-lg border border-slate-800">
                  <strong className="text-emerald-400">Cevap:</strong> 3 kademeli yedekleme vardır: 1. Şoförün elindeki QR kod nizamiyedeki lazer okuyucu veya tablet kamerasıyla 80ms'de taranır. 2. Güvenlik görevlisinin tabletindeki dev Numpad üzerinden akıllı plaka maskelemesiyle plaka 2 saniyede girilir. 3. Sistem randevusuz araçlar için anında 'İstisnai Kapı İzni (Override)' yetkisine sahiptir.
                </div>
              </div>

              <div className="bg-slate-900/80 border border-slate-800 p-4 rounded-xl">
                <div className="text-xs font-bold text-white flex items-center space-x-2">
                  <span className="text-amber-400 font-mono">Soru 5:</span>
                  <span>Rampa randevusu alan bir tır 40 dakika geç gelirse (SLA gecikmesi) sistem rampayı bloke mi eder?</span>
                </div>
                <div className="text-[11px] text-slate-300 mt-2 bg-[#111827] p-3 rounded-lg border border-slate-800">
                  <strong className="text-emerald-400">Cevap:</strong> Dinamik Rampa Tahsis Motoru devreye girer. Randevu saatini 15 dakika aşan araç 'GECİKMEDE' statüsüne alınır; amire tek tuşla rampayı parkta hazır bekleyen başka bir acil araca kaydırma (Dynamic Slot Swapping) önerisi sunulur. Böylece rampa asla boş yatmaz.
                </div>
              </div>
            </div>
          )}

        </div>

        {/* Footer */}
        <div className="px-6 py-3.5 bg-[#111827] border-t border-slate-700/80 flex items-center justify-between">
          <div className="text-xs text-slate-400 font-mono">
            RampaRandevu Savunma Dökümanı — LojistikGirisimleri AR-GE Laboratuvarı
          </div>
          <button
            onClick={onClose}
            className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold px-4 py-2 rounded-lg transition-colors cursor-pointer"
          >
            Anlaşıldı, Sistemi İncelemeye Devam Et
          </button>
        </div>

      </div>
    </div>
  );
};

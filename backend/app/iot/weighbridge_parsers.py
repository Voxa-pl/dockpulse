"""
Kantar İndikatörleri (Baykon, Esit, Tunaylar) için RS232 / RS485 Seri Port Okuyucu ve ASCII Ayrıştırıcı Servisi.
Desteklenen İndikatör Aileleri:
- Baykon BX Serisi (BX21, BX22, BX23, BX30)
- Esit Serisi (ART, ECI, PWI)
- Tunaylar Serisi (LPi, Baster)
- Generic ASCII & Moxa NPort Seri-TCP Dönüştürücü Akışları
"""

import re
from typing import Optional, Dict, Any, Tuple, List
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger("ramparandevu.iot.weighbridge")

@dataclass
class AxleWeights:
    steer_axle_kg: float          # Ön yönlendirme dingili (azami 10.000 kg)
    drive_axle_kg: float          # Tahrikli çeker dingil (azami 11.500 kg)
    trailer_axle_group_kg: float  # Yarı römork üçlü dingil grubu (tridem - azami 24.000 kg)
    total_gross_kg: float         # Toplam brüt katar ağırlığı (azami 40.000 kg)

@dataclass
class AxleComplianceResult:
    is_compliant: bool
    steer_overload_kg: float = 0.0
    drive_overload_kg: float = 0.0
    trailer_overload_kg: float = 0.0
    total_overload_kg: float = 0.0
    violations: List[str] = field(default_factory=list)
    rebalance_recommendation: Optional[str] = None

@dataclass
class ParsedWeight:
    vendor: str
    weight_kg: float
    unit: str  # kg, ton
    is_stable: bool
    weight_type: str  # GROSS (Brüt), TARE (Dara), NET (Net), UNKNOWN
    gross_kg: Optional[float] = None
    tare_kg: Optional[float] = None
    net_kg: Optional[float] = None
    raw_frame: str = ""
    status_flags: Optional[Dict[str, Any]] = None
    axle_weights: Optional[AxleWeights] = None
    axle_compliance: Optional[AxleComplianceResult] = None

class WeighbridgeParser:
    """
    Endüstriyel kantar seri port veri ayrıştırıcısı ve tolerans denetleyicisi.
    """

    # Yasal Karayolu & Lojistik Ağırlık Toleransı (±%3)
    DEFAULT_TOLERANCE_PERCENT: float = 3.0

    # Karayolları Genel Müdürlüğü (KGM Md. 128) Yasal Dingil ve Katar Sınırları
    KGM_STEER_AXLE_MAX_KG: float = 10000.0   # Ön yönlendirme dingili: 10 ton
    KGM_DRIVE_AXLE_MAX_KG: float = 11500.0   # Çeker tahrik dingili: 11.5 ton
    KGM_TRIDEM_AXLE_MAX_KG: float = 24000.0  # Römork 3'lü dingil grubu: 24 ton
    KGM_GROSS_MAX_KG: float = 40000.0        # Azami yüklü ağırlık (5 dingil katar): 40 ton

    @classmethod
    def calculate_axle_compliance(
        cls,
        steer_kg: float,
        drive_kg: float,
        trailer_kg: float,
        total_gross_kg: Optional[float] = None
    ) -> AxleComplianceResult:
        """
        KGM Madde 128 aks ağırlığı ve yük dağılımı yasal denetimini yapar.
        Toplam tonaj 40t altı olsa bile çeker aksın 11.5 tonu aşmasını tespit eder.
        """
        calculated_total = (steer_kg + drive_kg + trailer_kg) if total_gross_kg is None else total_gross_kg
        violations = []

        steer_overload = max(0.0, steer_kg - cls.KGM_STEER_AXLE_MAX_KG)
        if steer_overload > 0:
            violations.append(
                f"Ön yönlendirme aksı ({steer_kg:,.0f} kg) KGM yasal sınırını (10.000 kg) {steer_overload:,.0f} kg aşıyor!"
            )

        drive_overload = max(0.0, drive_kg - cls.KGM_DRIVE_AXLE_MAX_KG)
        if drive_overload > 0:
            violations.append(
                f"Çeker tahrik dingili ({drive_kg:,.0f} kg) KGM yasal sınırını (11.500 kg) {drive_overload:,.0f} kg aşıyor!"
            )

        trailer_overload = max(0.0, trailer_kg - cls.KGM_TRIDEM_AXLE_MAX_KG)
        if trailer_overload > 0:
            violations.append(
                f"Römork üçlü dingil grubu ({trailer_kg:,.0f} kg) KGM yasal sınırını (24.000 kg) {trailer_overload:,.0f} kg aşıyor!"
            )

        allowed_gross = cls.KGM_GROSS_MAX_KG * (1.0 + cls.DEFAULT_TOLERANCE_PERCENT / 100.0) # 41.200 kg
        total_overload = max(0.0, calculated_total - allowed_gross)
        if total_overload > 0:
            violations.append(
                f"Toplam katar ağırlığı ({calculated_total:,.0f} kg) Karayolları azami yasal sınırını (40.000 kg + %3 tolerans = {allowed_gross:,.0f} kg) {total_overload:,.0f} kg aşıyor!"
            )

        rebalance_rec = None
        if drive_overload > 0 and total_overload == 0:
            rebalance_rec = (
                f"DİKKAT: Toplam katar ağırlığı ({calculated_total:,.0f} kg) yasal sınırda olmasına rağmen yük öne yığılmış! "
                f"Çeker aks KGM kantarında ceza yer. Rampa amiri aracı derhal rampaya geri çağırarak ön paletleri arkaya kaydırmalıdır (Weight Re-distribution)."
            )
        elif violations:
            rebalance_rec = "Aks ve tonaj aşımı nedeniyle araç sahadan çıkarılamaz. Yük boşaltma veya dengeleme zorunludur."

        is_compliant = len(violations) == 0

        return AxleComplianceResult(
            is_compliant=is_compliant,
            steer_overload_kg=steer_overload,
            drive_overload_kg=drive_overload,
            trailer_overload_kg=trailer_overload,
            total_overload_kg=total_overload,
            violations=violations,
            rebalance_recommendation=rebalance_rec
        )

    @classmethod
    def parse_axle_frame(cls, raw_ascii: str) -> Optional[AxleWeights]:
        """
        Çoklu aks kantarından (Baykon BW / Tunaylar AKS / Esit Aks) gelen
        aks dökümünü çözümler.
        Örnek: "AXLES: 6200, 11400, 21800" veya "STEER:6200 DRIVE:11400 TRAILER:21800"
        """
        clean = raw_ascii.upper()
        # Format 1: AXLES: 6200, 11400, 21800
        match_axles = re.search(r"AXLES?:\s*([0-9.,\s]+)", clean)
        if match_axles:
            parts = [float(p.strip()) for p in match_axles.group(1).split(",") if p.strip()]
            if len(parts) >= 3:
                steer, drive, trailer = parts[0], parts[1], sum(parts[2:])
                return AxleWeights(
                    steer_axle_kg=steer,
                    drive_axle_kg=drive,
                    trailer_axle_group_kg=trailer,
                    total_gross_kg=steer + drive + trailer
                )

        # Format 2: STEER:... DRIVE:... TRAILER:...
        s_m = re.search(r"STEER:\s*([0-9]+)", clean)
        d_m = re.search(r"DRIVE:\s*([0-9]+)", clean)
        t_m = re.search(r"TRAILER:\s*([0-9]+)", clean)
        if s_m and d_m and t_m:
            steer = float(s_m.group(1))
            drive = float(d_m.group(1))
            trailer = float(t_m.group(1))
            return AxleWeights(
                steer_axle_kg=steer,
                drive_axle_kg=drive,
                trailer_axle_group_kg=trailer,
                total_gross_kg=steer + drive + trailer
            )

        return None

    @classmethod
    def parse_frame(cls, raw_ascii: str, vendor_hint: Optional[str] = None) -> ParsedWeight:
        """
        Gelen ASCII seri port çerçevesini indikatör modeline göre çözümler.
        """
        if not raw_ascii:
            raise ValueError("Seri port ASCII verisi boş olamaz.")

        clean_text = raw_ascii.strip()
        vendor = (vendor_hint or "").lower()

        # Otomatik İndikatör Modeli Tespiti
        if "baykon" in vendor or "bx" in vendor:
            parsed = cls._parse_baykon(raw_ascii)
        elif "esit" in vendor or "art" in vendor or "eci" in vendor:
            parsed = cls._parse_esit(raw_ascii)
        elif "tunaylar" in vendor or "lpi" in vendor:
            parsed = cls._parse_tunaylar(raw_ascii)
        else:
            # Akış içeriğinden tespit
            if "WB:" in raw_ascii or "WN:" in raw_ascii or "WD:" in raw_ascii:
                parsed = cls._parse_baykon(raw_ascii)
            elif re.search(r"[\x02]?[BNDT]\s*[+-]?\d+", raw_ascii):
                parsed = cls._parse_esit(raw_ascii)
            elif "NET:" in raw_ascii or "BRUT:" in raw_ascii or "DARA:" in raw_ascii:
                parsed = cls._parse_tunaylar(raw_ascii)
            else:
                parsed = cls._parse_generic(raw_ascii)

        # Aks Tartımı Varsa Ayrıştır ve Uyumluluğu Denetle
        axles = cls.parse_axle_frame(raw_ascii)
        if axles:
            parsed.axle_weights = axles
            parsed.axle_compliance = cls.calculate_axle_compliance(
                steer_kg=axles.steer_axle_kg,
                drive_kg=axles.drive_axle_kg,
                trailer_kg=axles.trailer_axle_group_kg,
                total_gross_kg=axles.total_gross_kg
            )
            if parsed.gross_kg is None:
                parsed.gross_kg = axles.total_gross_kg

        return parsed

    @classmethod
    def _parse_baykon(cls, raw: str) -> ParsedWeight:
        """
        Baykon BX Serisi ASCII Protokolü:
        Format A (Multi-field): "WB: 41240 kg  WD: 16820 kg  WN: 24420 kg"
        Format B (Continuous):  "\x02+041240 kg G\r\n" veya "\x02100+041240kg\r\n"
        Format C (Net only):    "WN:  24420 kg"
        """
        # Format A: WB / WD / WN aynı anda
        if "WB:" in raw and "WD:" in raw:
            wb_match = re.search(r"WB:\s*([+-]?\d+(?:\.\d+)?)", raw)
            wd_match = re.search(r"WD:\s*([+-]?\d+(?:\.\d+)?)", raw)
            wn_match = re.search(r"WN:\s*([+-]?\d+(?:\.\d+)?)", raw)

            gross = float(wb_match.group(1)) if wb_match else None
            tare = float(wd_match.group(1)) if wd_match else None
            net = float(wn_match.group(1)) if wn_match else None

            if gross is not None and tare is not None and net is None:
                net = abs(gross - tare)

            return ParsedWeight(
                vendor="baykon",
                weight_kg=gross if gross is not None else (net or 0.0),
                unit="kg",
                is_stable=True,
                weight_type="GROSS" if gross else "NET",
                gross_kg=gross,
                tare_kg=tare,
                net_kg=net,
                raw_frame=raw
            )

        # Format B: Sürekli mod (\x02+041240 kg G veya N)
        # STX (opsiyonel), işaret, ağırlık rakamları, kg, G/N
        match = re.search(r"([+-]?\d+(?:\.\d+)?)\s*(?:kg)?\s*([GN])?", raw.replace("\x02", "").replace("\r", "").replace("\n", ""))
        if match:
            val = float(match.group(1))
            type_flag = match.group(2)
            w_type = "NET" if type_flag == "N" else "GROSS"
            is_stable = "M" not in raw and "US" not in raw

            return ParsedWeight(
                vendor="baykon",
                weight_kg=val,
                unit="kg",
                is_stable=is_stable,
                weight_type=w_type,
                gross_kg=val if w_type == "GROSS" else None,
                net_kg=val if w_type == "NET" else None,
                raw_frame=raw
            )

        return cls._parse_generic(raw, vendor_name="baykon")

    @classmethod
    def _parse_esit(cls, raw: str) -> ParsedWeight:
        """
        Esit ART/ECI/PWI Serisi ASCII Protokolü:
        Format: STX + [Durum: B=Brüt, N=Net, T/D=Dara] + [İşaret & 7 hane ağırlık] + [Birim: kg] + CR
        Örnek: "\x02B+041240kg\r" veya "B +041240 kg\r"
        """
        clean = raw.replace("\x02", "").replace("\r", "").replace("\n", "").strip()
        match = re.search(r"([BNDT])\s*([+-]?\d+(?:\.\d+)?)\s*(?:kg)?", clean, re.IGNORECASE)
        if match:
            type_char = match.group(1).upper()
            val = float(match.group(2))

            if type_char == "B":
                w_type = "GROSS"
                gross, tare, net = val, None, None
            elif type_char in ["T", "D"]:
                w_type = "TARE"
                gross, tare, net = None, val, None
            else:
                w_type = "NET"
                gross, tare, net = None, None, val

            # Kararlılık kontrolü
            is_stable = "MOT" not in clean and "US" not in clean

            return ParsedWeight(
                vendor="esit",
                weight_kg=val,
                unit="kg",
                is_stable=is_stable,
                weight_type=w_type,
                gross_kg=gross,
                tare_kg=tare,
                net_kg=net,
                raw_frame=raw
            )

        return cls._parse_generic(raw, vendor_name="esit")

    @classmethod
    def _parse_tunaylar(cls, raw: str) -> ParsedWeight:
        """
        Tunaylar LPi / Baster Serisi ASCII Protokolü:
        Format A: "\x02T+041240 kg\r\n" veya "ST,+041240 kg\r\n"
        Format B: "BRUT: 41240 kg\r\n" / "DARA: 16820 kg\r\n" / "NET: 24420 kg\r\n"
        """
        clean = raw.replace("\x02", "").strip()

        # Format B (Anahtar kelimeli)
        if "BRUT:" in clean or "GROSS:" in clean:
            val = float(re.search(r"(?:BRUT|GROSS):\s*([+-]?\d+(?:\.\d+)?)", clean).group(1))
            return ParsedWeight(vendor="tunaylar", weight_kg=val, unit="kg", is_stable=True, weight_type="GROSS", gross_kg=val, raw_frame=raw)
        elif "DARA:" in clean or "TARE:" in clean:
            val = float(re.search(r"(?:DARA|TARE):\s*([+-]?\d+(?:\.\d+)?)", clean).group(1))
            return ParsedWeight(vendor="tunaylar", weight_kg=val, unit="kg", is_stable=True, weight_type="TARE", tare_kg=val, raw_frame=raw)
        elif "NET:" in clean:
            val = float(re.search(r"NET:\s*([+-]?\d+(?:\.\d+)?)", clean).group(1))
            return ParsedWeight(vendor="tunaylar", weight_kg=val, unit="kg", is_stable=True, weight_type="NET", net_kg=val, raw_frame=raw)

        # Format A
        is_stable = not clean.startswith("US") and not clean.startswith("M")
        match = re.search(r"([+-]?\d+(?:\.\d+)?)\s*(?:kg)?", clean)
        if match:
            val = float(match.group(1))
            return ParsedWeight(
                vendor="tunaylar",
                weight_kg=val,
                unit="kg",
                is_stable=is_stable,
                weight_type="GROSS",
                gross_kg=val,
                raw_frame=raw
            )

        return cls._parse_generic(raw, vendor_name="tunaylar")

    @classmethod
    def _parse_generic(cls, raw: str, vendor_name: str = "generic") -> ParsedWeight:
        """
        Generic ASCII Sayı Ayıklayıcı.
        """
        clean = raw.replace("\x02", "").strip()
        match = re.search(r"([+-]?\d+(?:\.\d+)?)", clean)
        if not match:
            raise ValueError(f"Seri port kantar verisinde sayısal ağırlık bulunamadı: {raw}")

        val = float(match.group(1))
        # Ton kontrolü
        if "t" in clean.lower() and "kg" not in clean.lower() and val < 100:
            val = val * 1000.0

        w_type = "GROSS"
        if "net" in clean.lower():
            w_type = "NET"
        elif "dara" in clean.lower() or "tare" in clean.lower():
            w_type = "TARE"

        return ParsedWeight(
            vendor=vendor_name,
            weight_kg=val,
            unit="kg",
            is_stable=True,
            weight_type=w_type,
            gross_kg=val if w_type == "GROSS" else None,
            tare_kg=val if w_type == "TARE" else None,
            net_kg=val if w_type == "NET" else None,
            raw_frame=raw
        )

    @classmethod
    def calculate_net_and_tolerance(
        cls,
        gross_kg: Optional[float],
        tare_kg: Optional[float],
        expected_net_kg: Optional[float] = None,
        tolerance_pct: float = DEFAULT_TOLERANCE_PERCENT
    ) -> Tuple[Optional[float], bool, Optional[float], Optional[str]]:
        """
        Net tonajı ve yasal/sipariş tolerans kontrolünü hesaplar.
        Dönüş: (net_kg, within_tolerance, discrepancy_percentage, warning_message)
        """
        if gross_kg is None or tare_kg is None:
            return None, True, None, None

        # Net = |Brüt - Dara|
        net_kg = round(abs(gross_kg - tare_kg), 2)

        # Karayolları 40 Ton Yasal Katar Ağırlığı Denetimi (Türkiye Yönetmeliği)
        warning_msg = None
        if gross_kg > 42000.0:
            warning_msg = f"DİKKAT: Brüt ağırlık ({gross_kg:,.0f} kg) Karayolları yasal azami yüklü ağırlık limitini (40.000 kg + %3 = 41.200 kg) aşıyor!"

        # Eğer beklenen net yük (irsaliye / sipariş) girilmişse tolerans sapmasını kontrol et
        if expected_net_kg and expected_net_kg > 0:
            diff = abs(net_kg - expected_net_kg)
            dev_pct = round((diff / expected_net_kg) * 100.0, 2)
            within_tol = dev_pct <= tolerance_pct
            if not within_tol:
                discrepancy_note = f"Net tonaj ({net_kg} kg) beklenen miktardan ({expected_net_kg} kg) %{dev_pct} saptı. Yasal limit: ±%{tolerance_pct}"
                warning_msg = f"{warning_msg} | {discrepancy_note}" if warning_msg else discrepancy_note
            return net_kg, within_tol, dev_pct, warning_msg

        return net_kg, True, 0.0, warning_msg

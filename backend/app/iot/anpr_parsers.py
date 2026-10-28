"""
PTS / ANPR Kamera Webhook Ayrıştırıcıları ve Doğrulama Servisleri
Desteklenen Donanımlar: Hikvision DS-2CD serisi ISAPI, Dahua ITC/IPC serisi, Generic ANPR Edge.
"""

import re
import json
import xml.etree.ElementTree as ET
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger("dockpulse.iot.anpr")

@dataclass
class ParsedANPR:
    plate_number: str
    clean_plate: str
    confidence: float
    direction: str  # ENTRY, EXIT, UNKNOWN
    camera_vendor: str
    device_id: str
    vehicle_type: Optional[str] = None
    vehicle_color: Optional[str] = None
    capture_time: Optional[datetime] = None
    image_base64: Optional[str] = None
    raw_metadata: Optional[Dict[str, Any]] = None

class ANPRParser:
    """
    Endüstriyel PTS (Plaka Tanıma Sistemi) Kameraları Webhook İşleyicisi.
    Hikvision ISAPI XML/JSON ve Dahua TrafficCar formatlarını otomatik algılar ve ayrıştırır.
    """

    # Türkiye Standart Plaka Regex Formülasyonu
    # 01-81 il kodu, ardından 1-3 harf, ardından 2-4 rakam
    TR_PLATE_REGEX = re.compile(r"^([0-8][0-9])\s*([A-ZÇĞİÖŞÜ]{1,3})\s*([0-9]{2,4})$")

    @classmethod
    def normalize_plate(cls, raw_plate: str) -> Tuple[str, str]:
        """
        Plakayı temizler ve standartlaştırır.
        Dönüş: (formatted_plate, compact_plate)
        Örnek: " 34-vr.8902 " -> ("34 VR 8902", "34VR8902")
        """
        if not raw_plate:
            return "", ""

        # Türkçe karakterleri büyük harfe çevir ve boşlukları/noktalama işaretlerini ayıkla
        cleaned = raw_plate.upper().strip()
        # Türkçe i/ı dönüşümü
        cleaned = cleaned.replace("i", "İ").upper()
        # Noktalama işaretlerini boşluğa çevir
        cleaned = re.sub(r"[\.\-_\/\\:]", " ", cleaned)
        # Birden fazla boşluğu teke indir
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        compact = cleaned.replace(" ", "")

        # Türkiye plaka formatına uyarlama denemesi
        match = cls.TR_PLATE_REGEX.match(compact)
        if match:
            province, letters, numbers = match.groups()
            formatted = f"{province} {letters} {numbers}"
            return formatted, compact

        # Format dışı (örneğin yabancı tır plakası: B 1234 AA, BG-982-TR vb.)
        return cleaned, compact

    @classmethod
    def parse(
        cls,
        raw_payload: Optional[str] = None,
        vendor_hint: Optional[str] = None,
        direct_plate: Optional[str] = None,
        confidence: Optional[float] = None,
        direction: Optional[str] = None,
        device_id: Optional[str] = None
    ) -> ParsedANPR:
        """
        Gelen webhook verisini uygun ayrıştırıcıya yönlendirir.
        """
        # 1. Eğer doğrudan plaka parametresi verilmişse
        if direct_plate and not raw_payload:
            formatted, compact = cls.normalize_plate(direct_plate)
            return ParsedANPR(
                plate_number=formatted,
                clean_plate=compact,
                confidence=confidence or 95.0,
                direction=(direction or "ENTRY").upper(),
                camera_vendor=(vendor_hint or "generic").lower(),
                device_id=device_id or "CAM-GATE-IN-01",
                capture_time=datetime.now()
            )

        if not raw_payload:
            raise ValueError("ANPR payload verisi boş olamaz.")

        raw_str = raw_payload.strip()

        # Otomatik format tespiti: XML mi, JSON mu?
        if raw_str.startswith("<") or (vendor_hint and vendor_hint.lower() == "hikvision" and "<" in raw_str):
            return cls._parse_hikvision_xml(raw_str, device_id)
        
        # JSON denemesi
        try:
            data = json.loads(raw_str)
            # Dahua formatı kontrolü
            if "Events" in data or "TrafficCar" in raw_str or (vendor_hint and vendor_hint.lower() == "dahua"):
                return cls._parse_dahua_json(data, device_id)
            # Hikvision JSON formatı kontrolü
            if "EventNotificationAlert" in data or "ANPR" in data:
                return cls._parse_hikvision_json(data, device_id)
            # Standart Generic JSON
            return cls._parse_generic_json(data, device_id)
        except json.JSONDecodeError:
            # Düz metin plaka aktarımı
            formatted, compact = cls.normalize_plate(raw_str)
            return ParsedANPR(
                plate_number=formatted,
                clean_plate=compact,
                confidence=confidence or 90.0,
                direction=(direction or "ENTRY").upper(),
                camera_vendor=(vendor_hint or "generic").lower(),
                device_id=device_id or "CAM-GATE-IN-01",
                capture_time=datetime.now()
            )

    @classmethod
    def _parse_hikvision_xml(cls, xml_text: str, default_device: Optional[str]) -> ParsedANPR:
        """
        Hikvision ISAPI ANPR XML formatını ayrıştırır.
        Örnek:
        <EventNotificationAlert>
            <channelID>1</channelID>
            <dateTime>2026-10-27T14:30:00+03:00</dateTime>
            <ipAddress>192.168.1.101</ipAddress>
            <ANPR>
                <licensePlate>34 VR 8902</licensePlate>
                <confidenceLevel>98</confidenceLevel>
                <direction>reverse</direction>
                <vehicleType>truck</vehicleType>
            </ANPR>
        </EventNotificationAlert>
        """
        # Namespace kaldırma kolaylığı için regex veya etree
        try:
            # Strip all xmlns namespaces to avoid xpath prefix friction
            clean_xml = re.sub(r'\sxmlns(?::\w+)?="[^"]*"', '', xml_text)
            root = ET.fromstring(clean_xml)

            def _find_first(paths):
                for p in paths:
                    el = root.find(p)
                    if el is not None and el.text is not None:
                        return el
                return None

            # Plaka arama
            plate_el = _find_first([".//licensePlate", ".//plateNumber", ".//PlateNumber", ".//license", ".//plate"])
            raw_plate = plate_el.text.strip() if plate_el is not None else "UNKNOWN"

            # Güven skoru
            conf_el = _find_first([".//confidenceLevel", ".//confidence", ".//Confidence"])
            confidence = float(conf_el.text.strip()) if conf_el is not None else 95.0

            # Yön
            dir_el = _find_first([".//direction", ".//Direction"])
            direction_raw = (dir_el.text or "in").strip().lower() if dir_el is not None else "in"
            direction = "ENTRY" if direction_raw in ["in", "forward", "entry", "reverse", "0"] else "EXIT"

            # Araç tipi & renk
            vtype_el = _find_first([".//vehicleType", ".//VehicleType"])
            vehicle_type = vtype_el.text.strip() if vtype_el is not None else "TRUCK"

            # Cihaz & Zaman
            dev_el = _find_first([".//ipAddress", ".//channelID", ".//deviceIndex"])
            dev_id = default_device or (f"HIK-{dev_el.text.strip()}" if dev_el is not None else "HIK-ISAPI-01")

            formatted, compact = cls.normalize_plate(raw_plate)
            return ParsedANPR(
                plate_number=formatted,
                clean_plate=compact,
                confidence=confidence,
                direction=direction,
                camera_vendor="hikvision",
                device_id=dev_id,
                vehicle_type=vehicle_type,
                capture_time=datetime.now(),
                raw_metadata={"protocol": "ISAPI_XML"}
            )
        except Exception as e:
            logger.error(f"Hikvision XML ayrıştırma hatası: {e}")
            raise ValueError(f"Hikvision ISAPI XML verisi okunamadı: {e}")

    @classmethod
    def _parse_hikvision_json(cls, data: Dict[str, Any], default_device: Optional[str]) -> ParsedANPR:
        """
        Hikvision JSON formatını ayrıştırır.
        """
        anpr_data = data.get("ANPR", data)
        raw_plate = (
            anpr_data.get("licensePlate") or 
            anpr_data.get("plateNumber") or 
            data.get("licensePlate", "UNKNOWN")
        )
        confidence = float(anpr_data.get("confidenceLevel", anpr_data.get("confidence", 95.0)))
        direction_raw = str(anpr_data.get("direction", "in")).lower()
        direction = "ENTRY" if direction_raw in ["in", "forward", "entry", "0"] else "EXIT"
        vehicle_type = anpr_data.get("vehicleType", "TRUCK")
        dev_id = default_device or data.get("ipAddress", "HIK-IP-01")

        formatted, compact = cls.normalize_plate(raw_plate)
        return ParsedANPR(
            plate_number=formatted,
            clean_plate=compact,
            confidence=confidence,
            direction=direction,
            camera_vendor="hikvision",
            device_id=dev_id,
            vehicle_type=vehicle_type,
            capture_time=datetime.now(),
            raw_metadata=data
        )

    @classmethod
    def _parse_dahua_json(cls, data: Dict[str, Any], default_device: Optional[str]) -> ParsedANPR:
        """
        Dahua TrafficCar alarm/webhook JSON formatını ayrıştırır.
        """
        # Dahua format 1: {"Events": [{"Code": "TrafficCar", "Data": {"PlateNumber": "41 ABC 710", ...}}]}
        event_obj = None
        if "Events" in data and isinstance(data["Events"], list) and len(data["Events"]) > 0:
            event_obj = data["Events"][0].get("Data", data["Events"][0])
        elif "Data" in data and isinstance(data["Data"], dict):
            event_obj = data["Data"]
        else:
            event_obj = data

        raw_plate = (
            event_obj.get("PlateNumber") or 
            event_obj.get("plateNumber") or 
            event_obj.get("Plate", "UNKNOWN")
        )
        confidence = float(event_obj.get("Confidence", 95.0))
        # Dahua yön kodları: 0: Yaklaşan (inbound/entry), 1: Uzaklaşan (outbound/exit)
        dir_val = str(event_obj.get("Direction", "0")).lower()
        direction = "ENTRY" if dir_val in ["0", "in", "inbound", "approach"] else "EXIT"

        v_type = event_obj.get("VehicleType", "HeavyTruck")
        v_color = event_obj.get("VehicleColor")
        dev_id = default_device or data.get("DeviceAddress", "DAHUA-ITC-01")

        formatted, compact = cls.normalize_plate(raw_plate)
        return ParsedANPR(
            plate_number=formatted,
            clean_plate=compact,
            confidence=confidence,
            direction=direction,
            camera_vendor="dahua",
            device_id=dev_id,
            vehicle_type=v_type,
            vehicle_color=v_color,
            capture_time=datetime.now(),
            raw_metadata=data
        )

    @classmethod
    def _parse_generic_json(cls, data: Dict[str, Any], default_device: Optional[str]) -> ParsedANPR:
        """
        Standart Generic IoT Edge ANPR JSON formatı.
        """
        raw_plate = (
            data.get("plate_number") or 
            data.get("plate") or 
            data.get("licensePlate", "UNKNOWN")
        )
        confidence = float(data.get("confidence", 95.0))
        direction = (data.get("direction", "ENTRY")).upper()
        vendor = data.get("vendor", data.get("camera_vendor", "generic")).lower()
        dev_id = default_device or data.get("device_id", "EDGE-ANPR-01")

        formatted, compact = cls.normalize_plate(raw_plate)
        return ParsedANPR(
            plate_number=formatted,
            clean_plate=compact,
            confidence=confidence,
            direction=direction,
            camera_vendor=vendor,
            device_id=dev_id,
            vehicle_type=data.get("vehicle_type"),
            image_base64=data.get("image_base64"),
            capture_time=datetime.now(),
            raw_metadata=data
        )

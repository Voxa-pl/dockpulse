from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any, Optional

from app.core.database import get_db
from app.models.appointment import Appointment
from app.models.goods_receipt import GoodsReceipt, GoodsReceiptItem
from app.services.ws_hub import ws_hub

router = APIRouter(prefix="/doculog", tags=["DocuLog Integration"])

@router.post("/callback")
async def doculog_webhook_callback(
    payload: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """
    DocuLog Vision AI işlemi tamamlandığında buraya Webhook gönderir.
    RampaRandevu appointment kaydını 'MATCH_OK' yapar ve WebSocket ile yayınlar.
    """
    appointment_id = payload.get("appointment_id")
    if not appointment_id:
        raise HTTPException(status_code=400, detail="appointment_id missing")

    res = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
    app = res.scalars().first()
    if not app:
        raise HTTPException(status_code=404, detail="Appointment not found")

    app.doculog_status = "MATCH_OK"
    app.doculog_document_id = payload.get("doculog_document_id", f"DOC-{app.id[:6]}")
    app.doculog_summary = payload.get("summary", "DocuLog Vision ile tam mutabakat sağlandı.")

    await db.commit()

    await ws_hub.broadcast_event("DOCULOG_WAYBILL_MATCHED", {
        "appointment_id": app.id,
        "doculog_document_id": app.doculog_document_id,
        "summary": app.doculog_summary
    })

    return {"status": "ACK", "message": "Webhook processed successfully"}

from app.models.appointment import Appointment

def generate_dynamic_waybill_preview(app: Appointment) -> dict:
    """Randevunun yük tipine ve taşıyıcısına göre gerçekçi dinamik irsaliye kalemleri üretir."""
    c_type = (app.cargo_type or "").lower()
    l_type = (app.load_type or "").upper()
    pallets = app.estimated_pallets or 30
    sap_code = "101"

    if "süt" in c_type or "soğuk" in c_type or "frigo" in c_type or l_type == "REEFER":
        supplier = "Sütaş Süt Ürünleri A.Ş."
        vkn = "7840039211"
        temp = app.measured_temperature_celsius if app.measured_temperature_celsius is not None else 3.6
        if temp > 4.0:
            notes = f"KRİTİK HACCP İHLALİ: İzotermal Frigo Sıcaklığı: +{temp}°C (Limit: +4°C aşıldı!). Soğuk zincir kırıldı, mal kabul SAP 103 ile karantinaya alındı."
            sap_code = "103"
        else:
            notes = f"İzotermal Frigo Sıcaklığı: +{temp}°C (Soğuk zincir onaylandı). Mühür No: ST-{app.vehicle_plate.replace(' ', '')} sağlam teyit edildi."
            sap_code = "101"

        items = [
            {"line_number": 1, "material_code": "SUT-1001", "description": "Taze Kaşar Peyniri 1KG Blok", "dispatched_qty": pallets * 25.0, "received_qty": pallets * 25.0, "damaged_qty": 0.0, "missing_qty": 0.0, "uom": "KOLİ"},
            {"line_number": 2, "material_code": "YOG-2040", "description": "Doğal Tava Yoğurt 2KG Kova", "dispatched_qty": pallets * 20.0, "received_qty": pallets * 20.0 - 1.0, "damaged_qty": 1.0, "missing_qty": 0.0, "uom": "KOLİ"},
            {"line_number": 3, "material_code": "SUT-3010", "description": "Tam Yağlı Pastörize Süt 1L (12'li)", "dispatched_qty": pallets * 30.0, "received_qty": pallets * 30.0, "damaged_qty": 0.0, "missing_qty": 0.0, "uom": "KOLİ"}
        ]
    elif "sac" in c_type or "çelik" in c_type or "demir" in c_type or l_type == "BULK":
        supplier = "Borusan Mannesmann Boru Yatırım A.Ş."
        vkn = "1800049120"
        notes = f"Ağır sanayi yükü: Tavan vinci ve hidrolik seviye ayarlayıcı ile indirildi. Net kantar: {app.weighbridge_net_kg or 24000:,.0f} kg."
        items = [
            {"line_number": 1, "material_code": "SAC-5501", "description": "Sıcak Haddelenmiş Rulo Sac 2.5mm", "dispatched_qty": 3.0, "received_qty": 3.0, "damaged_qty": 0.0, "missing_qty": 0.0, "uom": "RULO"},
            {"line_number": 2, "material_code": "SAC-8812", "description": "Galvanizli Çelik Sanayi Profili 6m", "dispatched_qty": 12.0, "received_qty": 12.0, "damaged_qty": 0.0, "missing_qty": 0.0, "uom": "BAĞ"}
        ]
    elif "oto" in c_type or "yedek" in c_type:
        supplier = "Ekol Otomotiv ve Yan Sanayi Tedarik A.Ş."
        vkn = "3320049182"
        notes = "Otomotiv parça kasaları barkod taramasıyla teyit edildi. SAP 101 tam mutabakat sağlandı."
        items = [
            {"line_number": 1, "material_code": "OTO-FR-01", "description": "Havalandırmalı Ön Fren Diski Takımı", "dispatched_qty": pallets * 15.0, "received_qty": pallets * 15.0, "damaged_qty": 0.0, "missing_qty": 0.0, "uom": "KUTU"},
            {"line_number": 2, "material_code": "OTO-AM-04", "description": "Gazlı Ön Amortisör Sol/Sağ Kiti", "dispatched_qty": pallets * 10.0, "received_qty": pallets * 10.0, "damaged_qty": 0.0, "missing_qty": 0.0, "uom": "KUTU"},
            {"line_number": 3, "material_code": "OTO-FL-08", "description": "Yağ Filtresi Kartuş Seti (Orijinal)", "dispatched_qty": pallets * 20.0, "received_qty": pallets * 20.0, "damaged_qty": 0.0, "missing_qty": 0.0, "uom": "KOLİ"}
        ]
    else:
        supplier = app.carrier_name or "Mars Lojistik FMCG Dağıtım A.Ş."
        vkn = app.carrier_tax_id or "6120058890"
        notes = f"Gebze DC Mal Kabul Rampa kontrolü: {pallets} palet fiziki sayım ve VUK 509 karekod mutabakatı tamamlandı."
        items = [
            {"line_number": 1, "material_code": "FMCG-101", "description": "Sıvı Bulaşık Deterjanı 4L Bidon", "dispatched_qty": pallets * 18.0, "received_qty": pallets * 18.0, "damaged_qty": 0.0, "missing_qty": 0.0, "uom": "KOLİ"},
            {"line_number": 2, "material_code": "FMCG-204", "description": "Çok Amaçlı Temizlik Spreyi 750ml", "dispatched_qty": pallets * 24.0, "received_qty": pallets * 24.0, "damaged_qty": 0.0, "missing_qty": 0.0, "uom": "KOLİ"},
            {"line_number": 3, "material_code": "FMCG-309", "description": "Doğal Çamaşır Yumuşatıcısı 3L", "dispatched_qty": pallets * 15.0, "received_qty": pallets * 15.0 - 1.0, "damaged_qty": 1.0, "missing_qty": 0.0, "uom": "KOLİ"}
        ]

    return {
        "waybill_number": app.waybill_number or f"IRS-2026-{app.vehicle_plate.replace(' ', '')[-4:]}01",
        "e_waybill_uuid": app.e_waybill_uuid or "48b7f83a-1290-449e-b12e-991204859218",
        "supplier_vkn": vkn,
        "supplier_title": supplier,
        "sap_movement_code": sap_code,
        "uetds_reference_number": f"UETDS-2026-TR-{app.vehicle_plate.replace(' ', '')[-4:]}",
        "status": "BLOCKED" if sap_code == "103" else "APPROVED",
        "warehouse_notes": notes,
        "items": items
    }

@router.get("/receipt/{appointment_id}")
async def get_goods_receipt_details(appointment_id: str, db: AsyncSession = Depends(get_db)):
    """Rampa amiri split-screen incelemesi için irsaliye ve kalem detayları."""
    res = await db.execute(select(GoodsReceipt).where(GoodsReceipt.appointment_id == appointment_id))
    gr = res.scalars().first()
    if not gr:
        app_res = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
        app = app_res.scalars().first()
        if app:
            return generate_dynamic_waybill_preview(app)
        # Fallback if no appointment found
        return {
            "waybill_number": "IRS-2026-904128",
            "e_waybill_uuid": "48b7f83a-1290-449e-b12e-991204859218",
            "supplier_vkn": "3880491204",
            "supplier_title": "Ekol Gıda & Endüstriyel Dağıtım A.Ş.",
            "sap_movement_code": "101",
            "uetds_reference_number": "UETDS-2026-TR-84912",
            "status": "APPROVED",
            "warehouse_notes": "Gebze DC Mal Kabul 4 Nolu Rampa teslimi sağlamdır.",
            "items": [
                {"line_number": 1, "material_code": "STK-8492-A", "description": "Endüstriyel Sıvı Yağ 18L Teneke", "dispatched_qty": 400.0, "received_qty": 400.0, "damaged_qty": 0.0, "missing_qty": 0.0, "uom": "ADET"}
            ]
        }

    # Fetch items
    items_res = await db.execute(select(GoodsReceiptItem).where(GoodsReceiptItem.goods_receipt_id == gr.id))
    items = items_res.scalars().all()

    return {
        "waybill_number": gr.waybill_number,
        "e_waybill_uuid": gr.e_waybill_uuid,
        "supplier_vkn": gr.supplier_vkn,
        "supplier_title": gr.supplier_title,
        "sap_movement_code": gr.sap_movement_code,
        "uetds_reference_number": gr.uetds_reference_number,
        "status": gr.status,
        "warehouse_notes": gr.warehouse_notes,
        "items": [
            {
                "line_number": it.line_number,
                "material_code": it.material_code,
                "description": it.description,
                "dispatched_qty": it.dispatched_qty,
                "received_qty": it.received_qty,
                "damaged_qty": it.damaged_qty,
                "missing_qty": it.missing_qty,
                "uom": it.uom
            }
            for it in items
        ]
    }

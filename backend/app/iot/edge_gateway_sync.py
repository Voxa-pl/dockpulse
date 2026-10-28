"""
Offline Store-and-Forward Edge Gateway Mimarisi.
Tesis interneti (WAN / Metro Ethernet / 4G) koptuğunda:
1. Donanım olaylarını (ANPR geçişi, Kantar tartımı, Bariyer açılışı) yerel dayanıklı kuyrukta (SQLite Edge Store) saklar.
2. Yerel randevu beyaz listesi (Offline Whitelist) ile internet olmadan da geçiş kararı verir.
3. İnternet geri geldiğinde birikmiş olayları merkezi sisteme otomatik senkronize eder (Store-and-Forward).
"""

import sqlite3
import json
import uuid
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger("ramparandevu.iot.edge_sync")

class EdgeStoreAndForward:
    """
    Yerel Edge Gateway Çevrimdışı Dayanıklı Kuyruk ve Senkronizasyon Yöneticisi.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            base_dir = Path(__file__).resolve().parent.parent.parent
            self.db_path = str(base_dir / "edge_offline_store.db")
        else:
            self.db_path = db_path
            
        self._init_sqlite()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_sqlite(self):
        """Yerel SQLite tablolarını kurar."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 1. Çevrimdışı Olay Kuyruğu
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS offline_event_queue (
                    id TEXT PRIMARY KEY,
                    idempotency_key TEXT UNIQUE,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    status TEXT DEFAULT 'PENDING',  -- PENDING, SYNCED, FAILED
                    synced_at TEXT,
                    retry_count INTEGER DEFAULT 0,
                    error_message TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON offline_event_queue(status)")

            # 2. Yerel Randevu Beyaz Listesi (Günün İndirilmiş Randevuları - Offline Whitelist)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS offline_appointment_whitelist (
                    plate_number TEXT PRIMARY KEY,
                    compact_plate TEXT NOT NULL,
                    appointment_id TEXT NOT NULL,
                    carrier_name TEXT,
                    driver_name TEXT,
                    slot_start TEXT,
                    slot_end TEXT,
                    assigned_dock TEXT,
                    authorized_status TEXT DEFAULT 'SCHEDULED',
                    cached_at TEXT NOT NULL
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_compact_plate ON offline_appointment_whitelist(compact_plate)")
            conn.commit()

    def enqueue_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        idempotency_key: Optional[str] = None
    ) -> str:
        """
        İnternet yokken veya asenkron tamponlama için olayı yerel kuyruğa ekler.
        """
        event_id = str(uuid.uuid4())
        idem_key = idempotency_key or f"EDGE-{uuid.uuid4().hex[:12].upper()}"
        now_str = datetime.now().isoformat()
        payload_json = json.dumps(payload, default=str)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO offline_event_queue (id, idempotency_key, event_type, payload, created_at, status)
                    VALUES (?, ?, ?, ?, ?, 'PENDING')
                """, (event_id, idem_key, event_type, payload_json, now_str))
                conn.commit()
                logger.info(f"[Store-and-Forward] Olay yerel kuyruğa yazıldı: {event_type} (Key: {idem_key})")
                return idem_key
            except sqlite3.IntegrityError:
                logger.warning(f"[Store-and-Forward] Mükerrer Idempotency Key ({idem_key}), işlem tekrarlandı sayıldı.")
                return idem_key

    def get_pending_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Merkeze gönderilmeyi bekleyen olayları getirir.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, idempotency_key, event_type, payload, created_at, retry_count
                FROM offline_event_queue
                WHERE status = 'PENDING'
                ORDER BY created_at ASC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            results = []
            for r in rows:
                results.append({
                    "id": r["id"],
                    "idempotency_key": r["idempotency_key"],
                    "event_type": r["event_type"],
                    "payload": json.loads(r["payload"]),
                    "created_at": r["created_at"],
                    "retry_count": r["retry_count"]
                })
            return results

    def mark_event_synced(self, event_id: str):
        """
        Merkeze başarıyla iletilen olayı SYNCED olarak işaretler.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now_str = datetime.now().isoformat()
            cursor.execute("""
                UPDATE offline_event_queue
                SET status = 'SYNCED', synced_at = ?
                WHERE id = ?
            """, (now_str, event_id))
            conn.commit()

    def mark_event_failed(self, event_id: str, error: str):
        """
        Merkeze iletilemeyen olayın yeniden deneme sayısını artırır.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE offline_event_queue
                SET retry_count = retry_count + 1, error_message = ?
                WHERE id = ?
            """, (error, event_id))
            conn.commit()

    def get_queue_metrics(self) -> Dict[str, Any]:
        """
        Kuyruk istatistiklerini döner.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT count(*) as cnt FROM offline_event_queue WHERE status = 'PENDING'")
            pending = cursor.fetchone()["cnt"]

            cursor.execute("SELECT count(*) as cnt FROM offline_event_queue WHERE status = 'SYNCED'")
            synced = cursor.fetchone()["cnt"]

            cursor.execute("SELECT count(*) as cnt FROM offline_appointment_whitelist")
            whitelist_count = cursor.fetchone()["cnt"]

            # DB dosya boyutu
            file_size = 0
            try:
                file_size = Path(self.db_path).stat().st_size
            except Exception:
                pass

            return {
                "pending_events": pending,
                "synced_events": synced,
                "whitelist_cached_records": whitelist_count,
                "db_file_bytes": file_size,
                "storage_healthy": True,
                "store_path": self.db_path
            }

    # ----------------- Offline Randevu Beyaz Listesi Yönetimi -----------------
    def cache_whitelist(self, appointments: List[Dict[str, Any]]):
        """
        Günün randevularını yerel SQLite beyaz listesine kopyalar.
        """
        now_str = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM offline_appointment_whitelist")
            for app in appointments:
                plate = app.get("vehicle_plate", "")
                compact = plate.replace(" ", "").upper()
                cursor.execute("""
                    INSERT OR REPLACE INTO offline_appointment_whitelist (
                        plate_number, compact_plate, appointment_id, carrier_name, driver_name,
                        slot_start, slot_end, assigned_dock, authorized_status, cached_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    plate,
                    compact,
                    app.get("id", ""),
                    app.get("carrier_name", ""),
                    app.get("driver_name", ""),
                    str(app.get("slot_start", "")),
                    str(app.get("slot_end", "")),
                    app.get("assigned_dock", ""),
                    app.get("status", "SCHEDULED"),
                    now_str
                ))
            conn.commit()
            logger.info(f"[Store-and-Forward] {len(appointments)} randevu yerel beyaz listeye önbelleklendi.")

    def check_offline_whitelist(self, plate_number: str) -> Optional[Dict[str, Any]]:
        """
        Tesis interneti yokken gelen plakanın bugün için randevusu olup olmadığını yerel DB'den sorgular.
        """
        compact = plate_number.replace(" ", "").upper()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM offline_appointment_whitelist
                WHERE compact_plate = ? OR plate_number = ?
            """, (compact, plate_number.upper().strip()))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

# Global Singleton Edge Store Örneği
edge_store = EdgeStoreAndForward()

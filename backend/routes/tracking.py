import logging
import re
import time
from datetime import datetime, timezone

import requests
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from ..auth import get_current_user, require_permission
from ..database import SessionLocal
from ..models import Sale, Transporter, User
from ..schemas import LRTrackingIn

router = APIRouter(tags=["tracking"])

logger = logging.getLogger("raksha-erp")

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False
    class BeautifulSoup:
        def __init__(self, *a, **kw): pass
        def get_text(self): return ""
        def select(self, *a, **kw): return []


TRACKING_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

TRACKING_CONFIG = {
    "vrl": {"url": "https://vrlgroup.in/Track/LRNumber/{lr_no}", "source": "VRL Logistics", "mode": "table"},
    "dtdc": {"url": "https://www.dtdc.in/tracking/dtdc-tracking-results.asp?Lrnos={lr_no}", "source": "DTDC", "mode": "table"},
    "safexpress": {"url": "https://www.safexpress.com/track-trace/{lr_no}", "source": "Safexpress", "mode": "keyword",
                   "keywords": ["Picked Up", "In Transit", "Out for Delivery", "Delivered", "Exception", "Not Delivered"]},
    "gati": {"url": "https://www.gati.com/shipmentTracking/{lr_no}", "source": "Gati", "mode": "keyword",
             "keywords": ["Picked Up", "In Transit", "Out for Delivery", "Delivered", "Reached Destination", "Dispatched"]},
    "professional": {"url": "https://www.professional.couriers.in/tracking/{lr_no}", "source": "Professional Couriers", "mode": "keyword",
                     "keywords": ["Picked Up", "In Transit", "Out for Delivery", "Delivered", "Exception"]},
    "ecom": {"url": "https://www.ecomexpress.in/tracking/{lr_no}", "source": "Ecom Express", "mode": "keyword",
             "keywords": ["Picked", "In Transit", "Out for Delivery", "Delivered", "Reached"]},
    "delhivery": {"url": "https://www.delhivery.com/tracking/package/{lr_no}", "source": "Delhivery", "mode": "keyword",
                  "keywords": ["Picked Up", "In Transit", "Out for Delivery", "Delivered", "Reached Destination Hub"]},
}

TRANSPORTER_TRACKER_KEYS = {
    "vrl": "vrl", "vrl logistics": "vrl", "vrl group": "vrl", "v trans": "vrl", "v xpress": "vrl",
    "dtdc": "dtdc", "dtdc courier": "dtdc", "dtdc express": "dtdc",
    "safexpress": "safexpress", "saf express": "safexpress",
    "gati": "gati", "gati courier": "gati",
    "professional": "professional", "professional couriers": "professional", "professional courier": "professional",
    "ecom": "ecom", "ecom express": "ecom",
    "delhivery": "delhivery",
}


def _fetch_tracking(lr_no, config):
    try:
        url = config["url"].format(lr_no=lr_no)
        r = requests.get(url, headers=TRACKING_HEADERS, timeout=15, verify=True, allow_redirects=True)
        if r.status_code != 200:
            return {"status": "", "message": f"Tracking service returned status {r.status_code}"}
        soup = BeautifulSoup(r.text, 'html.parser')
        if config["mode"] == "table":
            rows = soup.select('table tr')
            statuses = []
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 3:
                    date_text = cells[0].get_text(strip=True)
                    location = cells[1].get_text(strip=True)
                    status = cells[2].get_text(strip=True)
                    if status and (date_text or config["source"] != "DTDC"):
                        statuses.append({"date": date_text, "location": location, "status": status})
            if statuses:
                latest = statuses[-1]
                return {"status": latest["status"], "location": latest["location"], "date": latest["date"], "history": statuses, "source": config["source"]}
        else:
            text = soup.get_text()
            keywords = config.get("keywords", ["Picked Up", "In Transit", "Out for Delivery", "Delivered"])
            found = [kw for kw in keywords if kw.lower() in text.lower()]
            if found:
                return {"status": found[-1], "location": "", "date": "", "history": [], "source": config["source"]}
        return {"status": "", "message": "No tracking data found"}
    except Exception as e:
        return {"status": "", "message": f"Failed to fetch: {str(e)}"}


def get_tracker_for_transporter(transporter_name):
    name_lower = (transporter_name or "").lower().strip()
    for key, tracker_key in TRANSPORTER_TRACKER_KEYS.items():
        if key in name_lower:
            return tracker_key
    return None


def fetch_tracking_by_key(lr_no, tracker_key):
    config = TRACKING_CONFIG.get(tracker_key)
    if not config:
        return {"status": "", "message": f"Unknown tracker: {tracker_key}"}
    return _fetch_tracking(lr_no, config)


def fetch_generic_tracking(lr_no, tracking_url_pattern):
    try:
        if not tracking_url_pattern:
            return {"status": "", "message": "No tracking URL pattern configured"}
        url = tracking_url_pattern.replace("{lr_no}", lr_no).replace("{LR_NO}", lr_no)
        r = requests.get(url, headers=TRACKING_HEADERS, timeout=15, verify=True, allow_redirects=True)
        soup = BeautifulSoup(r.text, 'html.parser')
        text = soup.get_text().lower()
        statuses = []
        for keyword in ["delivered", "out for delivery", "in transit", "picked up", "dispatched", "reached destination", "arrived", "exception", "delayed", "not delivered"]:
            if keyword in text:
                statuses.append(keyword.title())
        if statuses:
            return {"status": statuses[0], "location": "", "date": "", "history": [], "source": "Web", "url": url}
        return {"status": "", "message": "Could not parse tracking status from page", "url": url}
    except Exception as e:
        return {"status": "", "message": f"Failed to fetch: {str(e)}"}


@router.put("/api/sales/{sid}/lr-tracking")
def update_lr_tracking(sid: int, body: LRTrackingIn, user: User = Depends(require_permission("sales", "edit"))):
    db = SessionLocal()
    try:
        s = db.query(Sale).filter(Sale.id == sid).first()
        if not s:
            raise HTTPException(404, "Sale not found")
        if body.lr_no:
            s.lr_no = body.lr_no
        if body.tracking_url:
            s.lr_tracking_url = body.tracking_url
        s.lr_last_checked = datetime.now(timezone.utc)
        db.commit()
        return {"message": "LR tracking updated"}
    finally:
        db.close()


@router.post("/api/sales/{sid}/generate-tracking-url")
def generate_tracking_url(sid: int, user: User = Depends(require_permission("sales", "edit"))):
    db = SessionLocal()
    try:
        s = db.query(Sale).filter(Sale.id == sid).first()
        if not s:
            raise HTTPException(404, "Sale not found")
        if not s.transporter_name or not s.lr_no:
            return {"tracking_url": "", "message": "No transporter or LR number found"}
        t = db.query(Transporter).filter(Transporter.name.ilike(s.transporter_name)).first()
        if t and t.tracking_url_pattern:
            tracking_url = t.tracking_url_pattern.replace("{lr_no}", s.lr_no).replace("{LR_NO}", s.lr_no)
            s.lr_tracking_url = tracking_url
            s.lr_last_checked = datetime.now(timezone.utc)
            db.commit()
            return {"tracking_url": tracking_url}
        name_lower = s.transporter_name.lower()
        default_patterns = {
            "vrl": "https://vrlgroup.in/Track/LRNumber/{lr_no}",
            "v trans": "https://vrlgroup.in/Track/LRNumber/{lr_no}",
            "dtdc": "https://www.dtdc.in/tracking/dtdc-tracking-results.asp?Lrnos={lr_no}",
            "safexpress": "https://www.safexpress.com/track-trace/{lr_no}",
            "gati": "https://www.gati.com/shipmentTracking/{lr_no}",
            "professional": "https://www.professional.couriers.in/tracking/{lr_no}",
            "ecom": "https://www.ecomexpress.in/tracking/{lr_no}",
            "delhivery": "https://www.delhivery.com/tracking/package/{lr_no}",
        }
        for key, pattern in default_patterns.items():
            if key in name_lower:
                tracking_url = pattern.replace("{lr_no}", s.lr_no)
                s.lr_tracking_url = tracking_url
                s.lr_last_checked = datetime.now(timezone.utc)
                db.commit()
                return {"tracking_url": tracking_url}
        return {"tracking_url": "", "message": "No tracking URL pattern configured for this transporter. Add one in Transporter settings."}
    finally:
        db.close()


@router.get("/api/sales/{sid}/lr-tracking")
def get_lr_tracking(sid: int, user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        s = db.query(Sale).filter(Sale.id == sid).first()
        if not s:
            raise HTTPException(404, "Sale not found")
        return {
            "lr_tracking_status": s.lr_tracking_status or "",
            "lr_tracking_url": s.lr_tracking_url or "",
            "lr_last_checked": s.lr_last_checked.isoformat() if s.lr_last_checked else None,
            "transporter_name": s.transporter_name or "",
            "lr_no": s.lr_no or "",
        }
    finally:
        db.close()


@router.post("/api/auto-generate-tracking-urls")
def auto_generate_tracking_urls(user: User = Depends(require_permission("sales", "edit"))):
    db = SessionLocal()
    try:
        updated = 0
        sales = db.query(Sale).filter(Sale.lr_no != "", Sale.lr_no != None).all()
        transporters = {t.name.lower(): t for t in db.query(Transporter).all()}
        for s in sales:
            if s.lr_tracking_url:
                continue
            t = transporters.get((s.transporter_name or "").lower())
            if t and t.tracking_url_pattern:
                url = t.tracking_url_pattern.replace("{lr_no}", s.lr_no or "").replace("{LR_NO}", s.lr_no or "")
                s.lr_tracking_url = url
                updated += 1
        db.commit()
        return {"message": f"Generated tracking URLs for {updated} sales", "updated": updated}
    finally:
        db.close()


@router.post("/api/fetch-tracking/{sid}")
def fetch_tracking_status(sid: int, user: User = Depends(require_permission("sales", "edit"))):
    db = SessionLocal()
    try:
        s = db.query(Sale).filter(Sale.id == sid).first()
        if not s:
            raise HTTPException(404, "Sale not found")
        if not s.lr_no:
            return {"status": "", "message": "No LR number set for this sale"}
        tracker = get_tracker_for_transporter(s.transporter_name)
        if tracker:
            result = fetch_tracking_by_key(s.lr_no, tracker)
        else:
            t = db.query(Transporter).filter(Transporter.name.ilike(s.transporter_name)).first()
            if t and t.tracking_url_pattern:
                result = fetch_generic_tracking(s.lr_no, t.tracking_url_pattern)
            else:
                return {"status": "", "message": f"No auto-tracking available for transporter: {s.transporter_name}. Add a tracking URL pattern in Transporter settings."}
        if result.get("status"):
            status = result["status"]
            if "deliver" in status.lower():
                s.lr_tracking_status = "Delivered"
            elif "transit" in status.lower():
                s.lr_tracking_status = "In Transit"
            elif "out for delivery" in status.lower():
                s.lr_tracking_status = "Out for Delivery"
            elif "delay" in status.lower() or "exception" in status.lower():
                s.lr_tracking_status = "Delayed"
            else:
                s.lr_tracking_status = status
            s.lr_last_checked = datetime.now(timezone.utc)
        if result.get("url") and not s.lr_tracking_url:
            s.lr_tracking_url = result["url"]
        db.commit()
        return result
    finally:
        db.close()


@router.post("/api/fetch-tracking-bulk")
def fetch_tracking_bulk(user: User = Depends(require_permission("sales", "bulk_edit"))):
    db = SessionLocal()
    try:
        sales = db.query(Sale).filter(Sale.lr_no != "", Sale.lr_no != None, Sale.lr_tracking_status != "Delivered").all()
        updated = 0
        results = []
        for s in sales:
            tracker = get_tracker_for_transporter(s.transporter_name)
            if tracker:
                result = fetch_tracking_by_key(s.lr_no, tracker)
            else:
                t = db.query(Transporter).filter(Transporter.name.ilike(s.transporter_name)).first()
                if t and t.tracking_url_pattern:
                    result = fetch_generic_tracking(s.lr_no, t.tracking_url_pattern)
                else:
                    continue
            try:
                if result.get("status"):
                    status = result["status"]
                    if "deliver" in status.lower():
                        s.lr_tracking_status = "Delivered"
                    elif "transit" in status.lower():
                        s.lr_tracking_status = "In Transit"
                    elif "out for delivery" in status.lower():
                        s.lr_tracking_status = "Out for Delivery"
                    elif "delay" in status.lower() or "exception" in status.lower():
                        s.lr_tracking_status = "Delayed"
                    else:
                        s.lr_tracking_status = status
                    s.lr_last_checked = datetime.now(timezone.utc)
                    if result.get("url") and not s.lr_tracking_url:
                        s.lr_tracking_url = result["url"]
                    updated += 1
                    results.append({"sale_id": s.id, "lr_no": s.lr_no, "status": s.lr_tracking_status})
            except Exception as ex:
                logger.warning(f"Bulk tracking update failed for sale {s.id}: {ex}")
                continue
        db.commit()
        return {"message": f"Updated {updated} shipments", "updated": updated, "results": results}
    finally:
        db.close()

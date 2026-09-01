import os
import ssl
import urllib.request
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from auth import get_current_user, require_permission
from database import SessionLocal
from models import Transporter, TransporterQuote, ProformaOrder, User
from schemas import TransporterIn

router = APIRouter(tags=["transporters"])


@router.get("/api/transporters")
def list_transporters(user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        rows = db.query(Transporter).all()
        return [{"id": t.id, "transporter_id": t.transporter_id, "name": t.name,
                 "phone": t.phone, "email": t.email, "address": t.address,
                 "state": t.state, "district": t.district, "city": t.city, "pincode": t.pincode,
                 "gst_number": t.gst_number, "pan_number": t.pan_number,
                 "gst_certificate": t.gst_certificate, "pan_card": t.pan_card,
                 "contact_person": t.contact_person, "contact_number": t.contact_number,
                 "tracking_url_pattern": t.tracking_url_pattern or "",
                 "blacklisted": t.blacklisted}
                for t in rows]
    finally:
        db.close()


@router.post("/api/transporters")
def create_transporter(inp: TransporterIn, user: User = Depends(require_permission("transporters", "create"))):
    db = SessionLocal()
    try:
        t = Transporter(**inp.dict())
        db.add(t)
        db.commit()
        db.refresh(t)
        return {"id": t.id, "message": "Transporter created"}
    finally:
        db.close()


@router.put("/api/transporters/{tid}")
def update_transporter(tid: int, inp: TransporterIn, user: User = Depends(require_permission("transporters", "edit"))):
    db = SessionLocal()
    try:
        t = db.query(Transporter).filter(Transporter.id == tid).first()
        if not t:
            raise HTTPException(404, "Not found")
        for k, v in inp.dict().items():
            setattr(t, k, v)
        db.commit()
        return {"message": "Updated"}
    finally:
        db.close()


@router.delete("/api/transporters/{tid}")
def delete_transporter(tid: int, user: User = Depends(require_permission("transporters", "delete"))):
    db = SessionLocal()
    try:
        t = db.query(Transporter).filter(Transporter.id == tid).first()
        if not t:
            raise HTTPException(404, "Not found")
        db.delete(t)
        db.commit()
        return {"message": "Transporter deleted"}
    finally:
        db.close()


@router.post("/api/fix-urls")
def fix_urls(user: User = Depends(require_permission("transporters", "edit"))):
    db = SessionLocal()
    try:
        rows = db.query(Transporter).all()
        fixed = 0
        for t in rows:
            changed = False
            for field in ["gst_certificate", "pan_card"]:
                url = getattr(t, field, "")
                if url and "/image/upload/" in url and url.endswith(".pdf"):
                    setattr(t, field, url.replace("/image/upload/", "/raw/upload/"))
                    changed = True
            if changed:
                fixed += 1
        db.commit()
        return {"fixed": fixed}
    finally:
        db.close()


@router.get("/api/view-file")
async def view_file(url: str = Query(...), user: User = Depends(get_current_user)):
    try:
        parsed = urlparse(url)
        allowed_hosts = ["res.cloudinary.com", "cloudinary.com"]
        if parsed.scheme not in ("https", "http") or parsed.hostname not in allowed_hosts:
            raise HTTPException(400, "URL not allowed. Only Cloudinary URLs are permitted.")
        ctx = ssl.create_default_context()
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, context=ctx) as resp:
            data = resp.read()
            if data[:4] == b'%PDF':
                content_type = 'application/pdf'
            elif data[:2] == b'\xff\xd8':
                content_type = 'image/jpeg'
            elif data[:8] == b'\x89PNG\r\n\x1a\n':
                content_type = 'image/png'
            else:
                content_type = resp.headers.get("Content-Type", "application/octet-stream")
            return Response(content=data, media_type=content_type, headers={
                "Content-Disposition": "inline",
            })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to load file: {str(e)}")


@router.post("/api/transporters/dedup")
def dedup_transporters(user: User = Depends(require_permission("transporters", "edit"))):
    db = SessionLocal()
    try:
        transporters = db.query(Transporter).order_by(Transporter.id).all()
        seen = {}
        removed = 0
        for t in transporters:
            key = (t.name.strip().lower(),) if t.name and t.name.strip() else (t.transporter_id.strip(),)
            if key in seen:
                keep = seen[key]
                for po in db.query(ProformaOrder).filter(ProformaOrder.transporter_id == t.id).all():
                    po.transporter_id = keep.id
                for tq in db.query(TransporterQuote).filter(TransporterQuote.transporter_id == t.id).all():
                    tq.transporter_id = keep.id
                db.delete(t)
                removed += 1
            else:
                seen[key] = t
        db.commit()
        return {"removed": removed, "remaining": len(seen), "message": f"Removed {removed} duplicate transporters"}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Dedup failed: {str(e)}")
    finally:
        db.close()

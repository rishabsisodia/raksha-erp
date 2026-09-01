import os
import re
import time
import logging
import tempfile
import threading

import requests
from fpdf import FPDF
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from ..models import ProformaOrder, ProformaOrderItem, Customer, BillingSite
from ..schemas import WhatsAppSendIn, WhatsAppSendPIIn, WhatsAppSendPOIn, WhatsAppTestIn
from ..auth import get_current_user, require_permission
from ..database import SessionLocal
from ..config import WHATSAPP_TOKEN, WHATSAPP_PHONE_ID, WHATSAPP_BUSINESS_ACCOUNT_ID, WHATSAPP_API_URL
from ..services.pdf import generate_pi_html, generate_po_html, _billing_site_header

logger = logging.getLogger("raksha-erp")

router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp"])

# Temp PDF storage for WhatsApp (no Cloudinary dependency)
_TEMP_PDFS = {}
_TEMP_PDFS_MAX_AGE = 3600  # 1 hour
_TEMP_PDFS_MAX_SIZE = 100  # max entries
_TEMP_PDFS_LOCK = threading.Lock()


def upload_whatsapp_media(file_bytes, filename):
    """Upload a file to WhatsApp media endpoint, returns media_id"""
    url = f"{WHATSAPP_API_URL}/{WHATSAPP_PHONE_ID}/media"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
    files = {"file": (filename, file_bytes, "application/pdf")}
    data = {"messaging_product": "whatsapp", "type": "application/pdf"}
    try:
        resp = requests.post(url, headers=headers, files=files, data=data, timeout=30)
        result = resp.json()
        if resp.status_code == 200:
            return result.get("id")
    except Exception as e:
        logger.error("WhatsApp media upload failed: %s", e)
    return None


def send_whatsapp_message(phone_number, message, media_url=None, doc_url=None, doc_filename=None, doc_media_id=None):
    """Send a WhatsApp message using Meta Cloud API"""
    url = f"{WHATSAPP_API_URL}/{WHATSAPP_PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    # Format phone number (remove spaces, dashes, + sign)
    phone = phone_number.replace(" ", "").replace("-", "").replace("+", "")
    if not phone.startswith("91") and len(phone) == 10:
        phone = "91" + phone

    # Validate phone number
    if len(phone) < 12:
        return {"success": False, "error": "Invalid phone number. Use 10-digit Indian number."}

    # Send document (PDF) via media_id (preferred - no external URL needed)
    if doc_media_id:
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "document",
            "document": {
                "id": doc_media_id,
                "filename": doc_filename or "document.pdf"
            }
        }
    # Send document (PDF) via URL
    elif doc_url:
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "document",
            "document": {
                "link": doc_url,
                "filename": doc_filename or "document.pdf"
            }
        }
    # Send image
    elif media_url:
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "image",
            "image": {"link": media_url}
        }
    # Send text
    else:
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "text",
            "text": {"body": message}
        }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        result = resp.json()
        if resp.status_code == 200:
            return {"success": True, "message_id": result.get("messages", [{}])[0].get("id")}
        else:
            error_msg = result.get("error", {}).get("message", "Unknown error")
            error_code = result.get("error", {}).get("code", 0)

            # Provide helpful error messages
            if error_code == 131047:
                error_msg = "Recipient hasn't messaged yet. Send a message to this number first, then try again."
            elif error_code == 131026:
                error_msg = "Message undeliverable. Check phone number and try again."

            return {"success": False, "error": error_msg, "error_code": error_code}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/temp-pdf/{pdf_id}")
def serve_temp_pdf(pdf_id: str, user=Depends(get_current_user)):
    # Cleanup old entries on access
    now = time.time()
    with _TEMP_PDFS_LOCK:
        expired = [k for k, v in _TEMP_PDFS.items() if now - v.get("created_at", 0) > _TEMP_PDFS_MAX_AGE]
        for k in expired:
            del _TEMP_PDFS[k]

        data = _TEMP_PDFS.get(pdf_id)
        if not data:
            raise HTTPException(404, "PDF expired or not found")
        del _TEMP_PDFS[pdf_id]
    safe_filename = re.sub(r'[^\w\-.]', '_', data["filename"])
    return Response(content=data["bytes"], media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{safe_filename}"'})


@router.post("/send")
def whatsapp_send(inp: WhatsAppSendIn, user=Depends(require_permission("proforma_orders", "edit"))):
    """Send a WhatsApp message"""
    phone = inp.phone
    message = inp.message

    if not phone or not message:
        raise HTTPException(400, "Phone and message are required")

    result = send_whatsapp_message(phone, message)
    return result


@router.post("/send-pi/{oid}")
def whatsapp_send_pi(oid: int, inp: WhatsAppSendPIIn, user=Depends(require_permission("proforma_orders", "edit"))):
    """Send PI PDF to a phone number via WhatsApp"""
    db = SessionLocal()
    try:
        order = db.query(ProformaOrder).filter(ProformaOrder.id == oid).first()
        if not order:
            raise HTTPException(404, "Order not found")

        customer = db.query(Customer).filter(Customer.id == order.customer_id).first()
        items = db.query(ProformaOrderItem).filter(ProformaOrderItem.proforma_order_id == oid).all()
        phone = inp.phone
        if not phone and customer:
            phone = customer.contact_number

        if not phone:
            raise HTTPException(400, "Phone number required")

        # Get billing site
        billing_site = None
        if order.billing_site:
            try:
                billing_site = db.query(BillingSite).filter(BillingSite.id == int(order.billing_site)).first()
            except (ValueError, TypeError):
                logger.warning("Invalid billing_site ID '%s' for order %s", order.billing_site, order.id)

        # Generate PI PDF
        pi_date = order.pi_date.strftime("%d-%b-%Y") if order.pi_date else ""

        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        # Header
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, "Raksha Pipes Pvt. Ltd.", 0, 1, 'C')
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 8, f"Proforma Invoice - {order.pi_no}", 0, 1, 'C')
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 6, f"Date: {pi_date}", 0, 1, 'L')
        pdf.cell(0, 6, f"Customer: {customer.contact_name if customer else '-'}", 0, 1, 'L')
        pdf.ln(5)

        # Items table
        pdf.set_font('Arial', 'B', 9)
        pdf.cell(15, 7, 'S.No', 1, 0, 'C')
        pdf.cell(30, 7, 'Part No', 1, 0, 'C')
        pdf.cell(50, 7, 'Description', 1, 0, 'C')
        pdf.cell(20, 7, 'Qty', 1, 0, 'C')
        pdf.cell(30, 7, 'Rate', 1, 0, 'C')
        pdf.cell(35, 7, 'Amount', 1, 1, 'C')

        pdf.set_font('Arial', '', 9)
        for i, item in enumerate(items, 1):
            pdf.cell(15, 6, str(i), 1, 0, 'C')
            pdf.cell(30, 6, str(item.part_no or '')[:15], 1, 0, 'C')
            pdf.cell(50, 6, str(item.description or '')[:25], 1, 0, 'L')
            pdf.cell(20, 6, str(item.final_qty or 0), 1, 0, 'C')
            pdf.cell(30, 6, f"Rs.{item.net_rate:,.2f}", 1, 0, 'R')
            pdf.cell(35, 6, f"Rs.{item.basic_amount:,.2f}", 1, 1, 'R')

        # Totals
        pdf.ln(3)
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(115, 7, 'Total:', 0, 0, 'R')
        pdf.cell(35, 7, f"Rs.{order.value_excl_gst:,.2f}", 0, 1, 'R')
        pdf.cell(115, 7, 'GST (18%):', 0, 0, 'R')
        pdf.cell(35, 7, f"Rs.{order.gst_amount:,.2f}", 0, 1, 'R')
        pdf.cell(115, 7, 'Freight:', 0, 0, 'R')
        pdf.cell(35, 7, f"Rs.{order.freight_amount:,.2f}", 0, 1, 'R')
        pdf.cell(115, 7, 'Grand Total:', 0, 0, 'R')
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(35, 7, f"Rs.{order.total_amount:,.2f}", 0, 1, 'R')

        # Generate PDF
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        tmp_path = tmp.name
        tmp.close()
        pdf.output(tmp_path)

        with open(tmp_path, "rb") as f:
            pdf_bytes = f.read()

        # Method 1: Try WhatsApp media upload (works for permanent tokens)
        media_id = upload_whatsapp_media(pdf_bytes, f"PI_{order.pi_no}.pdf")
        if media_id:
            os.unlink(tmp_path)
            result = send_whatsapp_message(phone, "", doc_media_id=media_id, doc_filename=f"PI_{order.pi_no}.pdf")
        else:
            # Method 2: Try Cloudinary URL
            pdf_url = None
            try:
                import cloudinary.uploader
                upload_result = cloudinary.uploader.upload(tmp_path, resource_type="raw", folder="whatsapp_pi")
                pdf_url = upload_result.get("secure_url")
            except Exception as e:
                logger.error("Cloudinary upload failed for WhatsApp PI: %s", e)
            os.unlink(tmp_path)

            if pdf_url:
                result = send_whatsapp_message(phone, "", doc_url=pdf_url, doc_filename=f"PI_{order.pi_no}.pdf")
            else:
                return {"success": False, "error": "PDF upload failed. Check CLOUDINARY_URL env var on Render."}

        # Update whatsapp_status
        if result["success"]:
            order.whatsapp_status = "sent"
            db.commit()

        return result
    finally:
        db.close()


@router.post("/send-po/{oid}")
def whatsapp_send_po(oid: int, inp: WhatsAppSendPOIn, user=Depends(require_permission("proforma_orders", "edit"))):
    """Send PO PDF to a phone number via WhatsApp"""
    db = SessionLocal()
    try:
        order = db.query(ProformaOrder).filter(ProformaOrder.id == oid).first()
        if not order:
            raise HTTPException(404, "Order not found")

        customer = db.query(Customer).filter(Customer.id == order.customer_id).first()
        items = db.query(ProformaOrderItem).filter(ProformaOrderItem.proforma_order_id == oid).all()
        phone = inp.phone
        if not phone and customer:
            phone = customer.contact_number

        if not phone:
            raise HTTPException(400, "Phone number required")

        # Get billing site
        billing_site = None
        if order.billing_site:
            try:
                billing_site = db.query(BillingSite).filter(BillingSite.id == int(order.billing_site)).first()
            except (ValueError, TypeError):
                logger.warning("Invalid billing_site ID '%s' for order %s", order.billing_site, order.id)

        # Generate PO PDF
        pi_date = order.pi_date.strftime("%d-%b-%Y") if order.pi_date else ""

        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        # Header
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, "Raksha Pipes Pvt. Ltd.", 0, 1, 'C')
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 8, f"Purchase Order - {order.po_no or order.pi_no}", 0, 1, 'C')
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 6, f"Date: {pi_date}", 0, 1, 'L')
        pdf.cell(0, 6, f"Party: {customer.contact_name if customer else '-'}", 0, 1, 'L')
        pdf.ln(5)

        # Items table
        pdf.set_font('Arial', 'B', 9)
        pdf.cell(15, 7, 'S.No', 1, 0, 'C')
        pdf.cell(30, 7, 'Part No', 1, 0, 'C')
        pdf.cell(50, 7, 'Description', 1, 0, 'C')
        pdf.cell(20, 7, 'Qty', 1, 0, 'C')
        pdf.cell(30, 7, 'Rate', 1, 0, 'C')
        pdf.cell(35, 7, 'Amount', 1, 1, 'C')

        pdf.set_font('Arial', '', 9)
        for i, item in enumerate(items, 1):
            pdf.cell(15, 6, str(i), 1, 0, 'C')
            pdf.cell(30, 6, str(item.part_no or '')[:15], 1, 0, 'C')
            pdf.cell(50, 6, str(item.description or '')[:25], 1, 0, 'L')
            pdf.cell(20, 6, str(item.final_qty or 0), 1, 0, 'C')
            pdf.cell(30, 6, f"Rs.{item.net_rate:,.2f}", 1, 0, 'R')
            pdf.cell(35, 6, f"Rs.{item.basic_amount:,.2f}", 1, 1, 'R')

        # Totals
        pdf.ln(3)
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(115, 7, 'Total:', 0, 0, 'R')
        pdf.cell(35, 7, f"Rs.{order.value_excl_gst:,.2f}", 0, 1, 'R')
        pdf.cell(115, 7, 'GST (18%):', 0, 0, 'R')
        pdf.cell(35, 7, f"Rs.{order.gst_amount:,.2f}", 0, 1, 'R')
        pdf.cell(115, 7, 'Freight:', 0, 0, 'R')
        pdf.cell(35, 7, f"Rs.{order.freight_amount:,.2f}", 0, 1, 'R')
        pdf.cell(115, 7, 'Grand Total:', 0, 0, 'R')
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(35, 7, f"Rs.{order.total_amount:,.2f}", 0, 1, 'R')

        # Generate PDF
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        tmp_path = tmp.name
        tmp.close()
        pdf.output(tmp_path)

        with open(tmp_path, "rb") as f:
            pdf_bytes = f.read()
        os.unlink(tmp_path)

        # Upload to WhatsApp media (no Cloudinary needed)
        media_id = upload_whatsapp_media(pdf_bytes, f"PO_{order.po_no or order.pi_no}.pdf")

        if media_id:
            result = send_whatsapp_message(phone, "", doc_media_id=media_id, doc_filename=f"PO_{order.po_no or order.pi_no}.pdf")
        else:
            result = {"success": False, "error": "Failed to upload PO PDF to WhatsApp"}

        # Update whatsapp_status
        if result["success"]:
            order.whatsapp_status = "sent"
            db.commit()

        return result
    finally:
        db.close()


@router.get("/config")
def get_whatsapp_config(user=Depends(get_current_user)):
    """Get WhatsApp configuration status"""
    return {
        "configured": bool(WHATSAPP_TOKEN and WHATSAPP_PHONE_ID),
        "phone_id": WHATSAPP_PHONE_ID[:10] + "..." if WHATSAPP_PHONE_ID else None,
        "business_account_id": WHATSAPP_BUSINESS_ACCOUNT_ID[:10] + "..." if WHATSAPP_BUSINESS_ACCOUNT_ID else None,
        "token_set": bool(WHATSAPP_TOKEN)
    }


@router.post("/test")
def whatsapp_test(inp: WhatsAppTestIn, user=Depends(get_current_user)):
    """Send a simple test text message"""
    phone = inp.phone
    if not phone:
        raise HTTPException(400, "Phone number required")

    message = "Test message from Raksha ERP. If you received this, WhatsApp is working!"
    result = send_whatsapp_message(phone, message)
    return result

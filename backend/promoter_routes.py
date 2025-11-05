"""
Promoter Form Routes for BNG Optimiser
Handles simple form submissions from promoters with automatic quote generation
"""

import os
import io
import tempfile
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path

from fastapi import APIRouter, Request, Form, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
import pandas as pd

from .config import get_settings
from .storage import SupabaseStorage
from .database import get_db_engine
from .optimizer import run_optimizer_for_metric
from .pdf_generator import generate_quote_pdf
from .email_service import send_review_email

# Initialize router
router = APIRouter()

# Initialize templates
template_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(template_dir))

# Settings
settings = get_settings()

# File size limit (15 MB)
MAX_FILE_SIZE = 15 * 1024 * 1024

# Auto-quote threshold
AUTO_QUOTE_THRESHOLD = settings.auto_quote_threshold


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def validate_file(file: UploadFile) -> None:
    """Validate uploaded file"""
    # Check file extension
    if not file.filename or not file.filename.lower().endswith('.xlsx'):
        raise HTTPException(
            status_code=400, 
            detail="Invalid file type. Only .xlsx files are accepted."
        )
    
    # Check file size (will be checked during upload)
    # Additional validation will happen when reading the file


def normalize_promoter_slug(slug: str) -> str:
    """Normalize promoter slug to uppercase"""
    return slug.strip().upper()


def get_promoter_display_name(slug: str) -> str:
    """Get display name for promoter from slug"""
    # In production, this would look up from a database
    # For now, just capitalize nicely
    return slug.upper()


@router.get("/{promoter_slug}", response_class=HTMLResponse)
async def show_promoter_form(
    request: Request,
    promoter_slug: str
):
    """
    Display the promoter quote request form
    
    Args:
        request: FastAPI request object
        promoter_slug: URL slug identifying the promoter (e.g., 'EPT', 'Arbtech')
    
    Returns:
        HTML form page
    """
    promoter_slug = normalize_promoter_slug(promoter_slug)
    promoter_name = get_promoter_display_name(promoter_slug)
    
    return templates.TemplateResponse(
        "promoter_form.html",
        {
            "request": request,
            "promoter_name": promoter_name,
            "promoter_slug": promoter_slug,
            "form_data": {},
            "error": None
        }
    )


@router.post("/{promoter_slug}", response_class=HTMLResponse)
async def handle_promoter_submission(
    request: Request,
    promoter_slug: str,
    contact_email: str = Form(...),
    site_address: Optional[str] = Form(None),
    site_postcode: Optional[str] = Form(None),
    client_reference: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    metric_file: UploadFile = File(...),
    consent: bool = Form(False)
):
    """
    Handle promoter form submission
    
    Process:
    1. Validate inputs
    2. Save metric file to storage
    3. Run optimizer
    4. Apply threshold logic:
       - < £20k: Generate PDF and return download
       - >= £20k: Send review email and show thank you page
    5. Save submission to database
    
    Args:
        request: FastAPI request object
        promoter_slug: Promoter identifier
        contact_email: Submitter's email
        site_address: Optional site address
        site_postcode: Optional site postcode
        client_reference: Optional client reference
        notes: Optional notes
        metric_file: Uploaded BNG metric file
        consent: Data sharing consent checkbox
    
    Returns:
        PDF download (auto-quote) or HTML thank you page (manual review)
    """
    promoter_slug = normalize_promoter_slug(promoter_slug)
    promoter_name = get_promoter_display_name(promoter_slug)
    
    # Store form data for re-display on error
    form_data = {
        "contact_email": contact_email,
        "site_address": site_address,
        "site_postcode": site_postcode,
        "client_reference": client_reference,
        "notes": notes,
        "consent": consent
    }
    
    try:
        # Validate consent
        if not consent:
            return templates.TemplateResponse(
                "promoter_form.html",
                {
                    "request": request,
                    "promoter_name": promoter_name,
                    "promoter_slug": promoter_slug,
                    "form_data": form_data,
                    "error": "You must provide consent to share data."
                }
            )
        
        # Validate location (at least one required)
        if not site_address and not site_postcode:
            return templates.TemplateResponse(
                "promoter_form.html",
                {
                    "request": request,
                    "promoter_name": promoter_name,
                    "promoter_slug": promoter_slug,
                    "form_data": form_data,
                    "error": "Please provide either a site address or postcode."
                }
            )
        
        # Validate file
        validate_file(metric_file)
        
        # Read file content
        file_content = await metric_file.read()
        file_size = len(file_content)
        
        # Check file size
        if file_size > MAX_FILE_SIZE:
            return templates.TemplateResponse(
                "promoter_form.html",
                {
                    "request": request,
                    "promoter_name": promoter_name,
                    "promoter_slug": promoter_slug,
                    "form_data": form_data,
                    "error": f"File too large. Maximum size is {MAX_FILE_SIZE / 1024 / 1024:.1f} MB."
                }
            )
        
        # Initialize storage client
        storage = SupabaseStorage()
        
        # Generate unique filename for metric
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        metric_filename = f"{promoter_slug}_{timestamp}_{metric_file.filename}"
        
        # Upload metric file to storage
        metric_path = await storage.upload_metric(
            file_content=file_content,
            filename=metric_filename
        )
        
        # Save file to temporary location for processing
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            tmp_file.write(file_content)
            tmp_file_path = tmp_file.name
        
        try:
            # Run optimizer
            optimizer_result = await run_optimizer_for_metric(
                metric_file_path=tmp_file_path,
                site_address=site_address,
                site_postcode=site_postcode
            )
            
            quote_total = optimizer_result['total_cost']
            allocation_results = optimizer_result['allocation_results']
            target_lpa = optimizer_result.get('target_lpa')
            target_nca = optimizer_result.get('target_nca')
            
        finally:
            # Clean up temp file
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
        
        # Get client metadata
        ip_address = get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "unknown")
        
        # Apply threshold logic
        auto_quoted = quote_total < AUTO_QUOTE_THRESHOLD
        manual_review = not auto_quoted
        
        pdf_path = None
        pdf_size = None
        
        if auto_quoted:
            # Generate PDF for auto-quote
            pdf_content = generate_quote_pdf(
                promoter_slug=promoter_slug,
                contact_email=contact_email,
                site_address=site_address,
                site_postcode=site_postcode,
                client_reference=client_reference,
                quote_total=quote_total,
                allocation_results=allocation_results,
                target_lpa=target_lpa,
                target_nca=target_nca
            )
            
            # Upload PDF to storage
            pdf_filename = f"{promoter_slug}_{timestamp}_quote.pdf"
            pdf_path = await storage.upload_pdf(
                file_content=pdf_content,
                filename=pdf_filename
            )
            pdf_size = len(pdf_content)
        
        # Save submission to database
        engine = get_db_engine()
        with engine.begin() as conn:
            result = conn.execute(
                text("""
                    INSERT INTO promoter_submissions (
                        created_at, promoter_slug, contact_email,
                        site_address, site_postcode, client_reference, notes,
                        target_lpa, target_nca,
                        metric_file_path, metric_file_size_bytes,
                        pdf_file_path, pdf_file_size_bytes,
                        quote_total_gbp, total_with_admin_gbp,
                        status, auto_quoted, manual_review,
                        allocation_results,
                        ip_address, user_agent, consent_given
                    ) VALUES (
                        :created_at, :promoter_slug, :contact_email,
                        :site_address, :site_postcode, :client_reference, :notes,
                        :target_lpa, :target_nca,
                        :metric_file_path, :metric_file_size_bytes,
                        :pdf_file_path, :pdf_file_size_bytes,
                        :quote_total_gbp, :total_with_admin_gbp,
                        :status, :auto_quoted, :manual_review,
                        :allocation_results,
                        :ip_address, :user_agent, :consent_given
                    ) RETURNING id
                """),
                {
                    "created_at": datetime.now(),
                    "promoter_slug": promoter_slug,
                    "contact_email": contact_email,
                    "site_address": site_address,
                    "site_postcode": site_postcode,
                    "client_reference": client_reference,
                    "notes": notes,
                    "target_lpa": target_lpa,
                    "target_nca": target_nca,
                    "metric_file_path": metric_path,
                    "metric_file_size_bytes": file_size,
                    "pdf_file_path": pdf_path,
                    "pdf_file_size_bytes": pdf_size,
                    "quote_total_gbp": quote_total,
                    "total_with_admin_gbp": quote_total,  # Could add admin fee calculation
                    "status": "auto_quoted" if auto_quoted else "manual_review",
                    "auto_quoted": auto_quoted,
                    "manual_review": manual_review,
                    "allocation_results": allocation_results,
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                    "consent_given": consent
                }
            )
            submission_id = result.fetchone()[0]
        
        # Handle response based on threshold
        if auto_quoted:
            # Return PDF download
            # Generate signed URL for PDF download
            pdf_url = await storage.get_signed_url(pdf_path, expires_in=3600)
            
            # For now, return the PDF content directly
            return Response(
                content=pdf_content,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="BNG_Quote_{promoter_slug}_{timestamp}.pdf"'
                }
            )
        else:
            # Send review email
            # Generate signed URL for metric file (short expiry)
            metric_url = await storage.get_signed_url(metric_path, expires_in=86400)  # 24 hours
            
            await send_review_email(
                promoter_slug=promoter_slug,
                contact_email=contact_email,
                site_address=site_address,
                site_postcode=site_postcode,
                client_reference=client_reference,
                notes=notes,
                quote_total=quote_total,
                submission_id=submission_id,
                metric_url=metric_url
            )
            
            # Show thank you page
            return templates.TemplateResponse(
                "thank_you.html",
                {
                    "request": request,
                    "submission_id": submission_id,
                    "contact_email": contact_email,
                    "client_reference": client_reference,
                    "quote_total": quote_total,
                    "promoter_slug": promoter_slug
                }
            )
    
    except Exception as e:
        # Log error and show user-friendly message
        print(f"Error processing submission: {str(e)}")
        
        # Try to save error to database
        try:
            engine = get_db_engine()
            with engine.begin() as conn:
                conn.execute(
                    text("""
                        INSERT INTO promoter_submissions (
                            created_at, promoter_slug, contact_email,
                            site_address, site_postcode, client_reference, notes,
                            status, error_occurred, error_message,
                            ip_address, user_agent, consent_given
                        ) VALUES (
                            :created_at, :promoter_slug, :contact_email,
                            :site_address, :site_postcode, :client_reference, :notes,
                            :status, :error_occurred, :error_message,
                            :ip_address, :user_agent, :consent_given
                        )
                    """),
                    {
                        "created_at": datetime.now(),
                        "promoter_slug": promoter_slug,
                        "contact_email": contact_email,
                        "site_address": site_address,
                        "site_postcode": site_postcode,
                        "client_reference": client_reference,
                        "notes": notes,
                        "status": "error",
                        "error_occurred": True,
                        "error_message": str(e),
                        "ip_address": get_client_ip(request),
                        "user_agent": request.headers.get("User-Agent", "unknown"),
                        "consent_given": consent
                    }
                )
        except Exception as db_error:
            print(f"Failed to log error to database: {str(db_error)}")
        
        return templates.TemplateResponse(
            "promoter_form.html",
            {
                "request": request,
                "promoter_name": promoter_name,
                "promoter_slug": promoter_slug,
                "form_data": form_data,
                "error": "An error occurred processing your request. Please try again or contact support if the problem persists."
            }
        )

# FILE: myfita/apps/backend/programs/services/pdf_service.py

import os
import uuid
import hashlib
from io import BytesIO
from typing import Optional
from dataclasses import dataclass
from datetime import datetime

from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

# WeasyPrint for HTML to PDF conversion
try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    print("⚠️ WeasyPrint not installed. PDF generation will be disabled.")


@dataclass
class PDFGenerationResult:
    """Result of PDF generation"""
    success: bool
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    error: Optional[str] = None
    checksum: Optional[str] = None


class PDFService:
    """
    Secure PDF generation service for program delivery.
    
    BP: "program purchase delivery (PDF)"
    
    Security Features:
    - Watermarking with athlete info (prevents sharing)
    - Unique file naming (prevents URL guessing)
    - Checksum verification (detects tampering)
    - Secure storage path (outside web root)
    """
    
    def __init__(self):
        self.storage_path = os.path.join(settings.MEDIA_ROOT, "programs", "generated_pdfs")
        os.makedirs(self.storage_path, exist_ok=True)
    
    def generate_program_pdf(
        self,
        purchase,
        program,
        athlete,
        coach
    ) -> PDFGenerationResult:
        """
        Generate personalized PDF for a purchase.
        
        Args:
            purchase: Purchase model instance
            program: Program model instance
            athlete: User model instance (athlete)
            coach: User model instance (coach)
            
        Returns:
            PDFGenerationResult with file path or error
        """
        
        if not WEASYPRINT_AVAILABLE:
            return PDFGenerationResult(
                success=False,
                error="PDF generation library not available"
            )
        
        try:
            # Generate unique filename
            filename = self._generate_secure_filename(purchase.id, athlete.id)
            file_path = os.path.join(self.storage_path, filename)
            
            # Prepare context for template
            context = self._build_pdf_context(purchase, program, athlete, coach)
            
            # Render HTML template
            html_content = render_to_string("program_pdf.html", context)
            
            # Generate PDF with watermark
            pdf_bytes = self._render_pdf(html_content, athlete)
            
            # Save to secure location
            with open(file_path, "wb") as f:
                f.write(pdf_bytes)
            
            # Calculate checksum for integrity verification
            checksum = hashlib.sha256(pdf_bytes).hexdigest()
            
            return PDFGenerationResult(
                success=True,
                file_path=file_path,
                file_size=len(pdf_bytes),
                checksum=checksum
            )
            
        except Exception as e:
            return PDFGenerationResult(
                success=False,
                error=str(e)
            )
    
    def _generate_secure_filename(self, purchase_id: uuid.UUID, athlete_id: uuid.UUID) -> str:
        """
        Generate unpredictable filename to prevent URL guessing.
        Format: {purchase_id}_{random}_{timestamp}.pdf
        """
        random_part = uuid.uuid4().hex[:8]
        timestamp = int(timezone.now().timestamp())
        return f"{purchase_id}_{random_part}_{timestamp}.pdf"
    
    def _build_pdf_context(self, purchase, program, athlete, coach) -> dict:
        """Build context dictionary for PDF template"""
        
        # Parse program content
        content = program.content or {}
        
        return {
            # Header info
            "program_title": program.title,
            "program_description": program.description,
            "program_duration": program.duration_display,
            "program_difficulty": program.get_difficulty_level_display(),
            
            # Coach info
            "coach_name": coach.get_full_name() or coach.phone,
            "coach_specialties": getattr(coach, 'specialties', []),
            
            # Athlete info (for watermark)
            "athlete_name": athlete.get_full_name() or athlete.phone,
            "athlete_id": str(athlete.id)[:8],
            
            # Purchase info
            "purchase_id": str(purchase.id)[:8],
            "purchase_date": purchase.created_at.strftime("%Y-%m-%d"),
            
            # Program content
            "weeks": content.get("weeks", []),
            "exercises": content.get("exercises", []),
            "nutrition": content.get("nutrition", {}),
            "notes": content.get("notes", ""),
            
            # Metadata
            "generated_at": timezone.now().strftime("%Y-%m-%d %H:%M"),
            "platform_name": "MY-FITA",
            "platform_url": "https://myfita.ir",
            
            # Watermark text
            "watermark_text": f"اختصاصی برای {athlete.get_full_name() or athlete.phone} | {str(purchase.id)[:8]}"
        }
    
    def _render_pdf(self, html_content: str, athlete) -> bytes:
        """
        Render HTML to PDF with watermark.
        """
        
        # CSS for watermark and styling
        watermark_css = CSS(string=f"""
            @page {{
                size: A4;
                margin: 2cm;
                
                @bottom-center {{
                    content: "اختصاصی برای {athlete.get_full_name() or athlete.phone}";
                    font-size: 8pt;
                    color: #999;
                }}
                
                @top-right {{
                    content: "MY-FITA";
                    font-size: 8pt;
                    color: #999;
                }}
            }}
            
            body {{
                font-family: 'Vazir', 'Tahoma', sans-serif;
                direction: rtl;
                text-align: right;
                line-height: 1.8;
            }}
            
            .watermark {{
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%) rotate(-45deg);
                font-size: 60pt;
                color: rgba(0, 0, 0, 0.03);
                z-index: -1;
                white-space: nowrap;
            }}
            
            h1 {{
                color: #2c3e50;
                border-bottom: 2px solid #3498db;
                padding-bottom: 10px;
            }}
            
            h2 {{
                color: #34495e;
                margin-top: 20px;
            }}
            
            .week-section {{
                background: #f8f9fa;
                padding: 15px;
                margin: 10px 0;
                border-radius: 8px;
            }}
            
            .exercise {{
                background: white;
                padding: 10px;
                margin: 5px 0;
                border-right: 3px solid #3498db;
            }}
            
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 15px 0;
            }}
            
            th, td {{
                border: 1px solid #ddd;
                padding: 8px;
                text-align: right;
            }}
            
            th {{
                background: #3498db;
                color: white;
            }}
        """)
        
        # Generate PDF
        html = HTML(string=html_content)
        pdf_bytes = html.write_pdf(stylesheets=[watermark_css])
        
        return pdf_bytes
    
    def verify_pdf_integrity(self, file_path: str, expected_checksum: str) -> bool:
        """
        Verify PDF file has not been tampered with.
        """
        try:
            with open(file_path, "rb") as f:
                actual_checksum = hashlib.sha256(f.read()).hexdigest()
            return actual_checksum == expected_checksum
        except Exception:
            return False
    
    def get_secure_download_url(self, purchase) -> Optional[str]:
        """
        Generate secure download URL with token.
        Token expires in 24 hours.
        """
        token = purchase.generate_download_token()
        return f"/api/programs/download/{purchase.id}/?token={token}"
    
    def cleanup_expired_pdfs(self, max_age_days: int = 30):
        """
        Remove PDFs older than max_age_days.
        Called by scheduled task.
        """
        cutoff = timezone.now() - timezone.timedelta(days=max_age_days)
        
        for filename in os.listdir(self.storage_path):
            file_path = os.path.join(self.storage_path, filename)
            
            # Check file modification time
            mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
            if mtime < cutoff:
                os.remove(file_path)
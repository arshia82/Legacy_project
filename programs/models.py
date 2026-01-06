# FILE: myfita/apps/backend/programs/models.py

import uuid
import hashlib
import secrets
from datetime import timedelta
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator, FileExtensionValidator


def program_pdf_upload_path(instance, filename):
    """Generate secure upload path for program PDFs"""
    ext = filename.split('.')[-1]
    new_filename = f"{uuid.uuid4()}.{ext}"
    return f"programs/{instance.coach_id}/pdfs/{new_filename}"


def program_preview_upload_path(instance, filename):
    """Generate upload path for preview images"""
    ext = filename.split('.')[-1]
    new_filename = f"{uuid.uuid4()}.{ext}"
    return f"programs/{instance.coach_id}/previews/{new_filename}"


class Program(models.Model):
    """
    Training program created by a coach.
    
    BP: "program purchase delivery (PDF)"
    """
    
    class Category(models.TextChoices):
        WEIGHT_LOSS = 'weight_loss', 'کاهش وزن'
        MUSCLE_GAIN = 'muscle_gain', 'عضله‌سازی'
        STRENGTH = 'strength', 'قدرتی'
        ENDURANCE = 'endurance', 'استقامت'
        FLEXIBILITY = 'flexibility', 'انعطاف‌پذیری'
        COMPETITION_PREP = 'competition_prep', 'آمادگی مسابقه'
        GENERAL_FITNESS = 'general_fitness', 'تناسب اندام عمومی'
        REHABILITATION = 'rehabilitation', 'توانبخشی'
        NUTRITION = 'nutrition', 'تغذیه'
        HYBRID = 'hybrid', 'ترکیبی'
    
    class Difficulty(models.TextChoices):
        BEGINNER = 'beginner', 'مبتدی'
        INTERMEDIATE = 'intermediate', 'متوسط'
        ADVANCED = 'advanced', 'پیشرفته'
        PROFESSIONAL = 'professional', 'حرفه‌ای'
    
    class Status(models.TextChoices):
        DRAFT = 'draft', 'پیش‌نویس'
        PENDING_REVIEW = 'pending_review', 'در انتظار بررسی'
        PUBLISHED = 'published', 'منتشر شده'
        ARCHIVED = 'archived', 'آرشیو شده'
        REJECTED = 'rejected', 'رد شده'

    class Meta:
        db_table = 'programs_program'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['coach', 'status']),
            models.Index(fields=['category', 'difficulty']),
            models.Index(fields=['price_toman']),
            models.Index(fields=['status', 'is_featured']),
            models.Index(fields=['created_at']),
        ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Coach relationship
    coach = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='coach_programs'
    )
    
    # Program details
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    short_description = models.CharField(max_length=500)
    long_description = models.TextField()
    
    # Classification
    category = models.CharField(max_length=50, choices=Category.choices)
    difficulty = models.CharField(max_length=20, choices=Difficulty.choices)
    tags = models.JSONField(default=list, blank=True)
    
    # Duration and structure
    duration_weeks = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(52)]
    )
    sessions_per_week = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(7)],
        default=3
    )
    
    # Pricing (in Toman)
    price_toman = models.BigIntegerField(
        validators=[MinValueValidator(0)]
    )
    original_price_toman = models.BigIntegerField(
        null=True, blank=True,
        help_text="Original price before discount"
    )
    
    # Program content - SECURE PDF
    pdf_file = models.FileField(
        upload_to=program_pdf_upload_path,
        null=True,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])]
    )
    pdf_file_hash = models.CharField(max_length=64, blank=True)  # SHA-256 for integrity
    pdf_page_count = models.PositiveIntegerField(default=0)
    
    # Preview content (public)
    preview_images = models.JSONField(default=list, blank=True)
    preview_video_url = models.URLField(blank=True)
    
    # Status and visibility
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.DRAFT
    )
    is_featured = models.BooleanField(default=False)
    is_bestseller = models.BooleanField(default=False)
    
    # Statistics (denormalized for performance)
    total_purchases = models.PositiveIntegerField(default=0)
    average_rating = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    total_reviews = models.PositiveIntegerField(default=0)
    total_views = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.title} by {self.coach}"

    def save(self, *args, **kwargs):
        # Generate slug if not exists
        if not self.slug:
            from django.utils.text import slugify
            base_slug = slugify(self.title, allow_unicode=True)
            self.slug = f"{base_slug}-{str(self.id)[:8]}"
        
        # Calculate PDF hash for integrity
        if self.pdf_file and not self.pdf_file_hash:
            self.pdf_file_hash = self._calculate_file_hash()
        
        # Set published_at when publishing
        if self.status == self.Status.PUBLISHED and not self.published_at:
            self.published_at = timezone.now()
        
        super().save(*args, **kwargs)

    def _calculate_file_hash(self):
        """Calculate SHA-256 hash of PDF file"""
        if not self.pdf_file:
            return ""
        
        sha256 = hashlib.sha256()
        for chunk in self.pdf_file.chunks():
            sha256.update(chunk)
        return sha256.hexdigest()

    @property
    def is_published(self):
        return self.status == self.Status.PUBLISHED

    @property
    def discount_percentage(self):
        if self.original_price_toman and self.original_price_toman > self.price_toman:
            return int((1 - self.price_toman / self.original_price_toman) * 100)
        return 0


class Purchase(models.Model):
    """
    Record of an athlete purchasing a program.
    
    Links to TrustToken for payment verification.
    BP: "Transaction commission: platform take on program sales average 12%"
    """
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'در انتظار پرداخت'
        PAID = 'paid', 'پرداخت شده'
        DELIVERED = 'delivered', 'تحویل داده شده'
        REFUNDED = 'refunded', 'بازپرداخت شده'
        CANCELLED = 'cancelled', 'لغو شده'
        EXPIRED = 'expired', 'منقضی شده'

    class Meta:
        db_table = 'programs_purchase'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['athlete', 'program'],
                condition=models.Q(status__in=['pending', 'paid', 'delivered']),
                name='unique_active_purchase'
            )
        ]
        indexes = [
            models.Index(fields=['athlete', 'status']),
            models.Index(fields=['program', 'status']),
            models.Index(fields=['created_at']),
        ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationships
    athlete = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='athlete_purchases'
    )
    program = models.ForeignKey(
        Program,
        on_delete=models.PROTECT,
        related_name='purchases'
    )
    trust_token = models.OneToOneField(
        'billing.TrustToken',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='program_purchase'
    )
    
    # Price snapshot (in case program price changes)
    price_paid_toman = models.BigIntegerField()
    commission_amount = models.BigIntegerField(default=0)
    net_amount = models.BigIntegerField(default=0)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0.12)
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Delivery tracking - SECURE
    download_count = models.PositiveIntegerField(default=0)
    max_downloads = models.PositiveIntegerField(default=5)  # Limit downloads
    last_downloaded_at = models.DateTimeField(null=True, blank=True)
    last_download_ip = models.GenericIPAddressField(null=True, blank=True)

    def __str__(self):
        return f"{self.athlete} purchased {self.program.title}"

    def save(self, *args, **kwargs):
        # Set expiry for pending purchases (24 hours)
        if self.status == self.Status.PENDING and not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        
        # Calculate net amount
        if self.price_paid_toman and not self.net_amount:
            from decimal import Decimal
            self.commission_amount = int(Decimal(self.price_paid_toman) * self.commission_rate)
            self.net_amount = self.price_paid_toman - self.commission_amount
        
        super().save(*args, **kwargs)

    @property
    def can_download(self):
        """Check if athlete can still download the program"""
        if self.status not in [self.Status.PAID, self.Status.DELIVERED]:
            return False
        if self.download_count >= self.max_downloads:
            return False
        return True

    def increment_download(self, ip_address=None):
        """Record a download attempt"""
        self.download_count += 1
        self.last_downloaded_at = timezone.now()
        if ip_address:
            self.last_download_ip = ip_address
        if self.status == self.Status.PAID:
            self.status = self.Status.DELIVERED
            self.delivered_at = timezone.now()
        self.save(update_fields=[
            'download_count', 'last_downloaded_at', 
            'last_download_ip', 'status', 'delivered_at'
        ])


class DownloadToken(models.Model):
    """
    Secure, time-limited download token for PDF delivery.
    
    Security features:
    - Single-use or limited-use tokens
    - Time-based expiration
    - IP binding (optional)
    - Cryptographic token generation
    """
    
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        USED = 'used', 'Used'
        EXPIRED = 'expired', 'Expired'
        REVOKED = 'revoked', 'Revoked'

    class Meta:
        db_table = 'programs_download_token'
        indexes = [
            models.Index(fields=['token_hash', 'status']),
            models.Index(fields=['purchase', 'status']),
            models.Index(fields=['expires_at']),
        ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    purchase = models.ForeignKey(
        Purchase,
        on_delete=models.CASCADE,
        related_name='download_tokens'
    )
    
    # Token security
    token_hash = models.CharField(max_length=64, unique=True)  # SHA-256 of actual token
    
    # Usage limits
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    max_uses = models.PositiveIntegerField(default=1)
    use_count = models.PositiveIntegerField(default=0)
    
    # Time limits
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    
    # IP binding (optional security)
    bound_ip = models.GenericIPAddressField(null=True, blank=True)
    used_from_ip = models.GenericIPAddressField(null=True, blank=True)
    
    # User agent tracking
    created_user_agent = models.TextField(blank=True)
    used_user_agent = models.TextField(blank=True)

    @classmethod
    def generate_token(cls, purchase, expires_in_minutes=30, max_uses=1, bind_ip=None, user_agent=''):
        """
        Generate a secure download token.
        
        Args:
            purchase: Purchase object
            expires_in_minutes: Token validity period
            max_uses: Maximum number of downloads
            bind_ip: Optional IP to bind token to
            user_agent: User agent string
            
        Returns:
            Tuple of (DownloadToken, raw_token_string)
        """
        # Generate cryptographically secure token
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        
        token = cls.objects.create(
            purchase=purchase,
            token_hash=token_hash,
            expires_at=timezone.now() + timedelta(minutes=expires_in_minutes),
            max_uses=max_uses,
            bound_ip=bind_ip,
            created_user_agent=user_agent,
        )
        
        return token, raw_token

    @classmethod
    def validate_token(cls, raw_token, request_ip=None):
        """
        Validate a download token.
        
        Args:
            raw_token: The raw token string
            request_ip: IP address of the request
            
        Returns:
            Tuple of (is_valid, token_or_error_message)
        """
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        
        try:
            token = cls.objects.select_related('purchase', 'purchase__program').get(
                token_hash=token_hash
            )
        except cls.DoesNotExist:
            return False, "Invalid token"
        
        # Check status
        if token.status != cls.Status.ACTIVE:
            return False, f"Token is {token.status}"
        
        # Check expiration
        if token.expires_at <= timezone.now():
            token.status = cls.Status.EXPIRED
            token.save(update_fields=['status'])
            return False, "Token expired"
        
        # Check usage limit
        if token.use_count >= token.max_uses:
            token.status = cls.Status.USED
            token.save(update_fields=['status'])
            return False, "Token usage limit exceeded"
        
        # Check IP binding
        if token.bound_ip and request_ip and token.bound_ip != request_ip:
            return False, "Token bound to different IP"
        
        # Check purchase status
        if not token.purchase.can_download:
            return False, "Purchase does not allow downloads"
        
        return True, token

    def mark_used(self, ip_address=None, user_agent=''):
        """Mark token as used"""
        self.use_count += 1
        self.used_at = timezone.now()
        self.used_from_ip = ip_address
        self.used_user_agent = user_agent
        
        if self.use_count >= self.max_uses:
            self.status = self.Status.USED
        
        self.save(update_fields=[
            'use_count', 'used_at', 'used_from_ip', 
            'used_user_agent', 'status'
        ])


class ProgramReview(models.Model):
    """
    Athlete review of a purchased program.
    """

    class Meta:
        db_table = 'programs_review'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['purchase'],
                name='one_review_per_purchase'
            )
        ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    purchase = models.OneToOneField(
        Purchase,
        on_delete=models.CASCADE,
        related_name='review'
    )
    
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title = models.CharField(max_length=255, blank=True)
    content = models.TextField(blank=True)
    
    # Moderation
    is_approved = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    
    # Helpful votes
    helpful_count = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Review by {self.purchase.athlete} - {self.rating}★"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update program average rating
        self._update_program_rating()

    def _update_program_rating(self):
        """Update program's average rating"""
        from django.db.models import Avg
        program = self.purchase.program
        avg = ProgramReview.objects.filter(
            purchase__program=program,
            is_approved=True
        ).aggregate(avg=Avg('rating'))['avg'] or 0
        
        count = ProgramReview.objects.filter(
            purchase__program=program,
            is_approved=True
        ).count()
        
        program.average_rating = avg
        program.total_reviews = count
        program.save(update_fields=['average_rating', 'total_reviews'])
        # programs/models.py (append to end)

from django.db import models
from users.models import User  # Assuming User model exists

class Program(models.Model):
    coach = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'coach'})
    title = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)  # For 12% commission calc
    pdf_file = models.FileField(upload_to='programs/pdfs/')  # Secure PDF delivery
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Purchase(models.Model):
    athlete = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'athlete'})
    program = models.ForeignKey(Program, on_delete=models.CASCADE)
    gross_amount = models.DecimalField(max_digits=10, decimal_places=2)
    commission = models.DecimalField(max_digits=10, decimal_places=2)  # 12% platform take
    net_amount = models.DecimalField(max_digits=10, decimal_places=2)  # Coach payout
    purchased_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, choices=[('pending', 'Pending'), ('completed', 'Completed')])

    def save(self, *args, **kwargs):
        self.commission = self.gross_amount * 0.12  # BP: average 12% take
        self.net_amount = self.gross_amount - self.commission
        super().save(*args, **kwargs)
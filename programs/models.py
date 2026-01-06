# FILE: myfita/apps/backend/programs/models.py

from django.conf import settings
from django.core.validators import FileExtensionValidator, MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
import hashlib
import os
import uuid


def program_pdf_upload_path(instance, filename):
    """
    Generate upload path for program PDFs.
    Format: programs/<program_id>/<uuid>.<ext>
    
    BP: Supports "program purchase delivery (PDF)" (MY_FITA_Business_Plan.pdf, page 3).
    """
    ext = filename.split('.')[-1] if '.' in filename else 'pdf'
    name = f"{uuid.uuid4()}.{ext}"
    pk = instance.pk or 'unsaved'
    return os.path.join('programs', str(pk), name)


class Program(models.Model):
    """
    Training program created by coaches.
    BP: Core product for "transaction commission" (12% take rate, page 3).
    """
    DIFFICULTY_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]
    
    CATEGORY_CHOICES = [
        ('strength', 'Strength Training'),
        ('cardio', 'Cardio'),
        ('flexibility', 'Flexibility'),
        ('sports', 'Sports Specific'),
        ('nutrition', 'Nutrition'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]

    # UUID primary key (matches existing database)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic Info
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    short_description = models.CharField(max_length=500, blank=True)
    long_description = models.TextField(blank=True)
    
    # Coach relationship
    coach = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='programs'
    )
    
    # Classification
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, blank=True)
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, blank=True)
    tags = models.CharField(max_length=500, blank=True, help_text="Comma-separated tags")
    duration_weeks = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(52)]
    )
    sessions_per_week = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(14)]
    )
    
    # Pricing (in Toman)
    price_toman = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        default=0,
        validators=[MinValueValidator(0)]
    )
    original_price_toman = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    
    # Content
    pdf_file = models.FileField(
        upload_to=program_pdf_upload_path,
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])]
    )
    pdf_file_hash = models.CharField(max_length=64, blank=True, editable=False)
    pdf_page_count = models.PositiveIntegerField(null=True, blank=True)
    preview_images = models.JSONField(default=list, blank=True)
    preview_video_url = models.URLField(max_length=500, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    is_featured = models.BooleanField(default=False)
    is_bestseller = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'is_featured']),
            models.Index(fields=['coach', 'status']),
            models.Index(fields=['category', 'difficulty']),
        ]

    def save(self, *args, **kwargs):
        # Auto-generate slug from title
        if not self.slug:
            base_slug = slugify(self.title, allow_unicode=True)
            self.slug = base_slug
            counter = 1
            while Program.objects.filter(slug=self.slug).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        
        # Generate PDF hash if file exists
        if self.pdf_file:
            try:
                self.pdf_file.seek(0)
                file_hash = hashlib.sha256()
                for chunk in self.pdf_file.chunks():
                    file_hash.update(chunk)
                self.pdf_file_hash = file_hash.hexdigest()
            except Exception:
                pass
        
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class Purchase(models.Model):
    """
    Record of athlete purchasing a program.
    BP: Enables "transaction commission" (12% of GMV, page 3) and "payouts: weekly or every 3 days" (page 12).
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('delivered', 'Delivered'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
    ]

    # UUID primary key (matches existing database)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationships
    athlete = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='purchases'
    )
    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name='purchase_set'
    )
    
    # Transaction details
    price_paid_toman = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        validators=[MinValueValidator(0)]
    )
    commission_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    net_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    
    # Security & tracking
    trust_token = models.CharField(max_length=255, blank=True, default='')
    download_count = models.PositiveIntegerField(default=0)
    last_downloaded_at = models.DateTimeField(null=True, blank=True)
    last_download_ip = models.GenericIPAddressField(null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['athlete', 'status']),
            models.Index(fields=['program', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f"Purchase #{self.pk} - {self.program.title} by {self.athlete}"


class DownloadToken(models.Model):
    """
    Secure token for PDF downloads.
    BP: Implements "secure messaging" and content delivery (page 4).
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('used', 'Used'),
        ('expired', 'Expired'),
        ('revoked', 'Revoked'),
    ]

    # UUID primary key (matches existing database)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    purchase = models.ForeignKey(
        Purchase,
        on_delete=models.CASCADE,
        related_name='download_tokens'
    )
    
    # Token data
    token = models.CharField(max_length=255, unique=True, default='')
    token_hash = models.CharField(max_length=64, editable=False, db_index=True)
    
    # Usage tracking
    use_count = models.PositiveIntegerField(default=0)
    max_uses = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Expiry
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Audit trail
    used_at = models.DateTimeField(null=True, blank=True)
    used_from_ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token_hash']),
            models.Index(fields=['status', 'expires_at']),
            models.Index(fields=['purchase', 'status']),
        ]

    def save(self, *args, **kwargs):
        # Generate token hash
        if self.token:
            self.token_hash = hashlib.sha256(self.token.encode('utf-8')).hexdigest()
        super().save(*args, **kwargs)

    def is_valid(self):
        """Check if token is still valid for use."""
        if self.status != 'active':
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        if self.use_count >= self.max_uses:
            return False
        return True

    def __str__(self):
        return f"Token #{self.pk} for Purchase #{self.purchase_id}"


class ProgramReview(models.Model):
    """
    Athlete reviews of purchased programs.
    BP: Supports "coach credibility" (page 1) and "verified coaches" (page 6).
    """
    # UUID primary key (matches existing database)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationships
    purchase = models.ForeignKey(
        Purchase,
        on_delete=models.CASCADE,
        related_name='programreview_set'
    )
    
    # Review content
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    content = models.TextField(blank=True)
    
    # Moderation
    is_approved = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    
    # Engagement
    helpful_count = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_approved', 'rating']),
            models.Index(fields=['purchase']),
        ]
        unique_together = [['purchase']]  # One review per purchase

    def __str__(self):
        return f"Review #{self.pk} - {self.purchase.program.title} ({self.rating}★)"
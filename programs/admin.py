# FILE: myfita/apps/backend/programs/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Avg
from .models import Program, Purchase, DownloadToken, ProgramReview


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'title',
        'coach',
        'category',
        'difficulty',
        'price_display',
        'status',
        'total_purchases',
        'average_rating',
        'created_at',
    ]
    list_filter = ['status', 'category', 'difficulty', 'is_featured', 'is_bestseller', 'created_at']
    search_fields = ['title', 'coach__phone', 'coach__first_name', 'coach__last_name', 'short_description']
    readonly_fields = [
        'id',
        'total_purchases',
        'average_rating',
        'total_reviews',
        'pdf_file_hash',
        'created_at',
        'updated_at',
    ]
    ordering = ['-created_at']
    prepopulated_fields = {'slug': ('title',)}
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('id', 'coach', 'title', 'slug', 'short_description', 'long_description')
        }),
        ('Classification', {
            'fields': ('category', 'difficulty', 'tags', 'duration_weeks', 'sessions_per_week')
        }),
        ('Pricing', {
            'fields': ('price_toman', 'original_price_toman')
        }),
        ('Content', {
            'fields': ('pdf_file', 'pdf_file_hash', 'pdf_page_count', 'preview_images', 'preview_video_url')
        }),
        ('Status', {
            'fields': ('status', 'is_featured', 'is_bestseller', 'published_at')
        }),
        ('Statistics', {
            'fields': ('total_purchases', 'average_rating', 'total_reviews')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            total_purchases_count=Count('purchase_set'),
            average_rating_value=Avg('programreview_set__rating'),
            total_reviews_count=Count('programreview_set'),
        )

    @admin.display(description='Price', ordering='price_toman')
    def price_display(self, obj):
        return f"{obj.price_toman:,.0f} ﺗﻮﻣﺎن"

    @admin.display(description='Total Purchases', ordering='total_purchases_count')
    def total_purchases(self, obj):
        return obj.total_purchases_count or 0

    @admin.display(description='Average Rating', ordering='average_rating_value')
    def average_rating(self, obj):
        if obj.average_rating_value is not None:
            return f"{obj.average_rating_value:.1f}★"
        return "—"

    @admin.display(description='Total Reviews', ordering='total_reviews_count')
    def total_reviews(self, obj):
        return obj.total_reviews_count or 0


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = [
        'id_short',
        'athlete',
        'program',
        'price_display',
        'status',
        'download_count',
        'created_at',
    ]
    list_filter = ['status', 'created_at', 'paid_at']
    search_fields = [
        'athlete__phone',
        'athlete__first_name',
        'athlete__last_name',
        'program__title',
        'trust_token',
    ]
    readonly_fields = [
        'id',
        'trust_token',
        'commission_amount',
        'net_amount',
        'download_count',
        'last_downloaded_at',
        'last_download_ip',
        'created_at',
        'paid_at',
        'delivered_at',
    ]
    ordering = ['-created_at']

    fieldsets = (
        ('Basic Info', {
            'fields': ('id', 'athlete', 'program', 'status')
        }),
        ('Transaction', {
            'fields': ('price_paid_toman', 'commission_amount', 'net_amount', 'trust_token')
        }),
        ('Downloads', {
            'fields': ('download_count', 'last_downloaded_at', 'last_download_ip')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'paid_at', 'delivered_at')
        }),
    )

    @admin.display(description='ID')
    def id_short(self, obj):
        return str(obj.id)[:8]

    @admin.display(description='Price Paid', ordering='price_paid_toman')
    def price_display(self, obj):
        return f"{obj.price_paid_toman:,.0f} ﺗﻮﻣﺎن"


@admin.register(DownloadToken)
class DownloadTokenAdmin(admin.ModelAdmin):
    list_display = [
        'id_short',
        'purchase',
        'status',
        'use_count',
        'max_uses',
        'expires_at',
        'created_at',
    ]
    list_filter = ['status', 'created_at', 'expires_at']
    search_fields = ['token_hash', 'purchase__id', 'purchase__athlete__phone']
    readonly_fields = [
        'id',
        'token_hash',
        'use_count',
        'used_at',
        'used_from_ip',
        'created_at',
    ]
    ordering = ['-created_at']

    fieldsets = (
        ('Token Info', {
            'fields': ('id', 'purchase', 'token', 'token_hash')
        }),
        ('Usage', {
            'fields': ('status', 'use_count', 'max_uses', 'expires_at')
        }),
        ('Audit', {
            'fields': ('used_at', 'used_from_ip', 'created_at')
        }),
    )

    @admin.display(description='ID')
    def id_short(self, obj):
        return str(obj.id)[:8]


@admin.register(ProgramReview)
class ProgramReviewAdmin(admin.ModelAdmin):
    list_display = [
        'id_short',
        'get_athlete',
        'get_program',
        'rating_display',
        'is_approved',
        'is_featured',
        'created_at',
    ]
    list_filter = ['rating', 'is_approved', 'is_featured', 'created_at']
    search_fields = [
        'purchase__athlete__phone',
        'purchase__athlete__first_name',
        'purchase__program__title',
        'content',
    ]
    readonly_fields = ['id', 'purchase', 'helpful_count', 'created_at', 'updated_at']
    ordering = ['-created_at']

    fieldsets = (
        ('Review Info', {
            'fields': ('id', 'purchase', 'rating', 'content')
        }),
        ('Moderation', {
            'fields': ('is_approved', 'is_featured')
        }),
        ('Engagement', {
            'fields': ('helpful_count',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    @admin.display(description='ID')
    def id_short(self, obj):
        return str(obj.id)[:8]

    @admin.display(description='Athlete')
    def get_athlete(self, obj):
        return obj.purchase.athlete

    @admin.display(description='Program')
    def get_program(self, obj):
        return obj.purchase.program.title

    @admin.display(description='Rating', ordering='rating')
    def rating_display(self, obj):
        return '★' * obj.rating
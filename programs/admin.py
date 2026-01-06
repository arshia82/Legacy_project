# FILE: myfita/apps/backend/programs/admin.py

from django.contrib import admin
from django.utils.html import format_html
from .models import Program, Purchase, DownloadToken, ProgramReview


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'coach', 'category', 'difficulty', 
        'price_display', 'status', 'total_purchases', 
        'average_rating', 'created_at'
    ]
    list_filter = ['status', 'category', 'difficulty', 'is_featured', 'is_bestseller']
    search_fields = ['title', 'coach__phone', 'coach__first_name', 'coach__last_name']
    readonly_fields = [
        'id', 'total_purchases', 'average_rating', 'total_reviews', 
        'total_views', 'pdf_file_hash', 'created_at', 'updated_at'
    ]
    ordering = ['-created_at']
    
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
            'fields': ('total_purchases', 'average_rating', 'total_reviews', 'total_views')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def price_display(self, obj):
        return f"{obj.price_toman:,} تومان"
    price_display.short_description = 'Price'


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = [
        'id_short', 'athlete', 'program', 'price_display',
        'status', 'download_count', 'created_at'
    ]
    list_filter = ['status', 'created_at']
    search_fields = ['athlete__phone', 'program__title']
    readonly_fields = [
        'id', 'trust_token', 'commission_amount', 'net_amount',
        'download_count', 'last_downloaded_at', 'last_download_ip',
        'created_at', 'paid_at', 'delivered_at'
    ]
    ordering = ['-created_at']

    def id_short(self, obj):
        return str(obj.id)[:8]
    id_short.short_description = 'ID'

    def price_display(self, obj):
        return f"{obj.price_paid_toman:,} تومان"
    price_display.short_description = 'Price Paid'


@admin.register(DownloadToken)
class DownloadTokenAdmin(admin.ModelAdmin):
    list_display = [
        'id_short', 'purchase', 'status', 'use_count', 
        'max_uses', 'expires_at', 'created_at'
    ]
    list_filter = ['status', 'created_at']
    readonly_fields = [
        'id', 'token_hash', 'use_count', 'used_at',
        'used_from_ip', 'created_at'
    ]
    ordering = ['-created_at']

    def id_short(self, obj):
        return str(obj.id)[:8]
    id_short.short_description = 'ID'


@admin.register(ProgramReview)
class ProgramReviewAdmin(admin.ModelAdmin):
    list_display = [
        'id_short', 'get_athlete', 'get_program', 
        'rating_display', 'is_approved', 'created_at'
    ]
    list_filter = ['rating', 'is_approved', 'is_featured', 'created_at']
    search_fields = ['purchase__athlete__phone', 'purchase__program__title', 'content']
    readonly_fields = ['id', 'purchase', 'helpful_count', 'created_at', 'updated_at']
    ordering = ['-created_at']

    def id_short(self, obj):
        return str(obj.id)[:8]
    id_short.short_description = 'ID'

    def get_athlete(self, obj):
        return obj.purchase.athlete
    get_athlete.short_description = 'Athlete'

    def get_program(self, obj):
        return obj.purchase.program.title
    get_program.short_description = 'Program'

    def rating_display(self, obj):
        return '⭐' * obj.rating
    rating_display.short_description = 'Rating'
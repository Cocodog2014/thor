from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.core.management import call_command
from django.shortcuts import render
from django.urls import path
from .models import ImportJob, TradingData
import os


@admin.register(TradingData)
class TradingDataAdmin(admin.ModelAdmin):
    list_display = ('no_trades', 'dlst', 'date_display', 'open_price', 'close_price', 'volume', 'world_net_change')
    list_filter = ('year', 'month', 'dlst')
    search_fields = ('dlst', 'no_trades')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Identification', {
            'fields': ('no_trades', 'dlst')
        }),
        ('Date Information', {
            'fields': ('year', 'month', 'date', 'day')
        }),
        ('Core Financial Data', {
            'fields': ('open_price', 'close_price', 'volume')
        }),
        ('World Market Summary', {
            'fields': ('world_net_change', 'world_net_perc_change', 'world_high', 'world_low')
        }),
        ('Additional Data (JSON)', {
            'fields': ('additional_data',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related()
    
    def date_display(self, obj):
        return obj.date_display
    date_display.short_description = 'Date'
    date_display.admin_order_field = 'date'


@admin.register(ImportJob)
class ImportJobAdmin(admin.ModelAdmin):
    list_display = ("id", "file_name", "status", "progress_display", "duration_display", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("file_name",)
    readonly_fields = ('created_at', 'started_at', 'finished_at')
    
    actions = ['run_csv_import']
    
    def progress_display(self, obj):
        if obj.total_rows > 0:
            percentage = (obj.processed_rows / obj.total_rows) * 100
            return format_html(
                '<div style="width: 100px; background: #f0f0f0; border: 1px solid #ccc;">'
                '<div style="width: {}%; background: #28a745; height: 20px; text-align: center; color: white; font-size: 12px; line-height: 20px;">'
                '{}%</div></div>',
                percentage, round(percentage, 1)
            )
        return f"{obj.processed_rows:,}/{obj.total_rows:,}"
    progress_display.short_description = 'Progress'
    
    def duration_display(self, obj):
        if obj.started_at and obj.finished_at:
            duration = obj.finished_at - obj.started_at
            return str(duration).split('.')[0]  # Remove microseconds
        elif obj.started_at:
            return "Running..."
        return "Not started"
    duration_display.short_description = 'Duration'
    
    def run_csv_import(self, request, queryset):
        """Custom admin action to run CSV import."""
        if queryset.count() != 1:
            messages.error(request, "Please select exactly one import job.")
            return
        
        import_job = queryset.first()
        
        # For demo purposes, assume CSV is at the root of the project
        csv_path = os.path.join('A:', 'Thor', 'CleanData-ComputerLearning.csv')
        
        if not os.path.exists(csv_path):
            messages.error(request, f"CSV file not found at: {csv_path}")
            return
        
        try:
            call_command('import_trading_data', csv_path)
            messages.success(request, f"Import started for {import_job.file_name}")
        except Exception as e:
            messages.error(request, f"Failed to start import: {e}")
    
    run_csv_import.short_description = "Run CSV import for selected job"
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('upload-csv/', self.upload_csv_view, name='thordata_importjob_upload_csv'),
        ]
        return custom_urls + urls
    
    def upload_csv_view(self, request):
        """Custom view for uploading CSV files."""
        if request.method == 'POST':
            # This is a placeholder for file upload functionality
            # In a production environment, you'd handle file uploads here
            messages.info(request, "CSV upload functionality can be implemented here")
            return HttpResponseRedirect(reverse('admin:thordata_importjob_changelist'))
        
        context = {
            'title': 'Upload Trading Data CSV',
            'site_title': 'Thor Admin',
        }
        return render(request, 'admin/upload_csv.html', context)

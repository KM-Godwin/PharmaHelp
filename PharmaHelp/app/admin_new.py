from django.contrib import admin
from .models import Drug, Invoice
from django.http import HttpResponse
import csv

class ExportCsvMixin:
    def get_export_fields(self):
        """Override this method to specify fields to export"""
        return self.list_display
    
    def get_export_headers(self):
        """Override this method to specify CSV headers"""
        return [field.replace('_', ' ').title() for field in self.get_export_fields()]
    
    def export_as_csv(self, request, queryset):
        fields = self.get_export_fields()
        headers = self.get_export_headers()
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename={self.model.__name__.lower()}s.csv'
        writer = csv.writer(response)
        
        writer.writerow(headers)
        for obj in queryset:
            # Special handling for category in Drug model
            row = []
            for field in fields:
                value = getattr(obj, field)
                if field == 'category' and hasattr(obj, 'get_category_display'):
                    value = obj.get_category_display()
                row.append(value)
            writer.writerow(row)
        
        return response
    export_as_csv.short_description = "Export Selected to CSV"

@admin.register(Drug)
class DrugAdmin(ExportCsvMixin, admin.ModelAdmin):
    list_display = ('name', 'category', 'inStock', 'price', 'expiryDate')
    list_filter = ('category',)
    search_fields = ('name',)
    actions = ['export_as_csv']
    
    def get_export_fields(self):
        return ['name', 'category', 'inStock', 'price', 'expiryDate']
    
    def get_export_headers(self):
        return ['Name', 'Category', 'In Stock', 'Price', 'Expiry Date']

@admin.register(Invoice)
class InvoiceAdmin(ExportCsvMixin, admin.ModelAdmin):
    list_display = ('ID', 'productDescription', 'quantity', 'unit_Price', 'formatted_total_Price', 'date')
    list_filter = ('date',)
    search_fields = ('productDescription',)
    actions = ['export_as_csv']

    def get_readonly_fields(self, request, obj=None):
        return ['total_Price']
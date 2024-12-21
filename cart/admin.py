from django.contrib import admin
from .models import Order, OrderLine, Color, Size
from django.utils.html import format_html


class OrderLineInline(admin.TabularInline):
    model = OrderLine
    
    readonly_fields = ('product', 'quantity', 'color', 'size')
    extra = 0  

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'user', 'status', 'total_price', 'payment_method','note', 'created_at', 'updated_at')
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('order_id', 'user__username', 'user__email')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at','note', 'order_id','user','total_price')  # Giữ các trường này chỉ đọc
    
    fieldsets = (
        ("Order Details", {
            'fields': ('order_id','user', 'status', 'total_price', 'payment_method','note')  
        }),
        ("Timestamps", {
            'fields': ('created_at', 'updated_at'),
        }),
    )

    inlines = [OrderLineInline]
    
@admin.register(OrderLine)
class OrderLineAdmin(admin.ModelAdmin):
    list_display = ('orderline_id', 'order', 'product','color','size', 'quantity', 'created_at', 'updated_at')
    search_fields = ('orderline_id', 'order__order_id', 'product__name')
    list_filter = ('created_at',)
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    fieldsets = (
        ("Order Line Details", {
            'fields': ('orderline_id', 'order', 'product','color','size', 'quantity')
        }),
        ("Timestamps", {
            'fields': ('created_at', 'updated_at'),
        }),
    )
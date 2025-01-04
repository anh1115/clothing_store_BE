
import uuid
from django.contrib import admin
from .models import Order, OrderLine, Color, Size
from django.utils.html import format_html


class OrderLineInline(admin.TabularInline):
    model = OrderLine
    readonly_field = ("orderline_id")
    extra = 0  
    def save_new_inline(self, form, obj, commit=True):
        """
        Custom save method to generate `orderline_id`.
        """
        instance = form.save(commit=False)
        if not instance.orderline_id:  # Sinh orderline_id nếu chưa có
            instance.orderline_id = f"OL{str(uuid.uuid4())[:8].upper()}"
        if commit:
            instance.save()
        return instance

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'user', 'status', 'total_price', 'payment_method','note', 'created_at', 'updated_at')
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('order_id', 'user__username', 'user__email')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at', 'order_id','total_price')  # Giữ các trường này chỉ đọc
    
    fieldsets = (
        ("Order Details", {
            'fields': ('order_id','user', 'status', 'total_price', 'payment_method','note','created_at', 'updated_at')  
        }),
        
    )

    inlines = [OrderLineInline]
    
@admin.register(OrderLine)
class OrderLineAdmin(admin.ModelAdmin):
    list_display = ('orderline_id', 'order', 'product','color','size', 'quantity', 'created_at', 'updated_at')
    search_fields = ('orderline_id', 'order__order_id', 'product__name')
    list_filter = ('created_at',)
    readonly_fields = ('orderline_id', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    fieldsets = (
        ("Order Line Details", {
            'fields': ('orderline_id', 'order', 'product','color','size', 'quantity','created_at', 'updated_at')
        }),
        # ("Timestamps", {
        #     'fields': ('created_at', 'updated_at'),
        # }),
    )

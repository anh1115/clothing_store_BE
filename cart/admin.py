from django.contrib import admin
from .models import Order, OrderLine
from django.utils.html import format_html


class OrderLineInline(admin.TabularInline):
    model = OrderLine
    fields = ('orderline_id_link', 'product', 'quantity')  # Hiển thị các trường cần thiết
    readonly_fields = ('orderline_id_link', 'product', 'quantity')  # Không cho phép chỉnh sửa
    extra = 0  # Không thêm dòng trống mặc định

    # Tùy chỉnh nhãn
    verbose_name = "Order Line"
    verbose_name_plural = "Order Lines"

    def orderline_id_link(self, obj):
        """
        Tạo liên kết đến trang chi tiết của OrderLine trong Admin.
        """
        return format_html(
            '<a href="{}">{}</a>',
            f"/admin/cart/orderline/{obj.orderline_id}/change/",  # Đường dẫn đến chi tiết của OrderLine
            obj.orderline_id  # Hiển thị mã orderline_id
        )

    orderline_id_link.short_description = "OrderLine ID"  # Đặt tên cột hiển thị

    def has_add_permission(self, request, obj=None):
        return False  # Không cho phép thêm dòng mới
    class Media:
        css = {
            'all': ('data:text/css;charset=utf-8,'
                    'table#orderline_set-group tbody tr td { text-align: center; } '
                    'table#orderline_set-group th { text-align: center; font-weight: bold; } '
                    'table#orderline_set-group { width: 80%; margin: auto; }')
        }
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'user', 'status', 'total_price', 'payment_method', 'created_at', 'updated_at')
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('order_id', 'user__username', 'user__email')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ("Order Details", {
            'fields': ('order_id', 'user', 'status', 'total_price', 'payment_method')
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

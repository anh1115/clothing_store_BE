from import_export import fields, resources, widgets
from django.utils import timezone
from django.urls import path
from django.utils.safestring import mark_safe
from django.contrib import admin
from django.db.models import Sum, F
from cart.models import Order, OrderLine
from django.shortcuts import render
from .models import (
    Banner, Color, Size, Category, Product, Review, Image, 
    StockQuantity, PurchaseInvoice, PurchaseInvoiceLine
)
from import_export.admin import ExportActionModelAdmin, ImportExportModelAdmin
from django.utils.html import format_html
from django.contrib.admin import site
from django.http import HttpResponse
from django.utils.dateparse import parse_date
from django.urls import reverse

class ImageInline(admin.TabularInline):
    model = Image
    import_id_fields = ['id']
    extra = 1  # Số lượng hàng trống mặc định để thêm mới
    fields = ('url',)  # Chỉ hiển thị trường 'url'

class StockQuantityInline(admin.TabularInline):
    model = StockQuantity
    extra = 1
    fields = ('color', 'size', 'stock')

class ProductResource(resources.ModelResource):
    category = fields.Field(
        attribute='category',
        widget=widgets.ManyToManyWidget(Category, field='name')
    )
    color = fields.Field(
        attribute='color',
        widget=widgets.ManyToManyWidget(Color, field='name')
    )
    size = fields.Field(
        attribute='size',
        widget=widgets.ManyToManyWidget(Size, field='name')
    )
    class Meta:
        model = Product
        import_id_fields = ['product_id']
        fields = ('product_id', 'name', 'import_price', 'sell_price', 'category', 'color', 'size', 'description')
    
class ColorResource(resources.ModelResource):
    class Meta:
        model = Color
        import_id_fields = ['color_id']
        fields = ('name', 'slug', 'color_id')


class SizeResource(resources.ModelResource):
    class Meta:
        model = Size
        import_id_fields = ['size_id']
        fields = ('name', 'slug', 'size_id')

# Resource cho Category
# Resource để import dữ liệu Category
class CategoryResource(resources.ModelResource):
    class Meta:
        model = Category
        import_id_fields = ['category_id']
        fields = ('category_id', 'name', 'parent')
        
@admin.register(Color)
class ColorAdmin(ImportExportModelAdmin,admin.ModelAdmin):
    list_display = ('color_id', 'name',  'created_at', 'updated_at')
    search_fields = ('name', 'slug')
    ordering = ('name',)
    resource_class = ColorResource

@admin.register(Size)
class SizeAdmin(ImportExportModelAdmin,admin.ModelAdmin):
    list_display = ('size_id', 'name', 'created_at', 'updated_at')
    search_fields = ('name', 'slug')
    ordering = ('name',)
    resource_class = SizeResource

@admin.register(Category)
class CategoryAdmin(ImportExportModelAdmin,admin.ModelAdmin):
    list_display = ('category_id', 'name',  'parent', 'created_at', 'updated_at')
    search_fields = ('name',)
    list_filter = ('parent',)
    ordering = ('name',)
    resource_class = CategoryResource


@admin.register(Product)

class ProductAdmin(ImportExportModelAdmin,admin.ModelAdmin):
    resource_class = ProductResource
    list_display = ('product_id', 'name', 'import_price', 'sell_price', 'created_at', 'updated_at')
    search_fields = ('name', 'product_id')
    list_filter = ('category', 'color', 'size')
    ordering = ('name',)
    inlines = [ImageInline, StockQuantityInline]  # Gắn ImageInline vào ProductAdmin
    change_list_template = "admin/products/product_change_list.html" 
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('sales-stats/', self.sales_stats_view, name='product-sales-stats'),
        ]
        return custom_urls + urls

    # View cho thống kê sản phẩm bán chạy
    def sales_stats_view(self, request):
        # Lọc dữ liệu
        filter_type = request.GET.get('filter', 'all')
        selected_month = request.GET.get('month', None)  # Lấy tháng được chọn

        queryset = OrderLine.objects.select_related('product').all()

        if filter_type == 'daily':
            queryset = queryset.filter(order__created_at__date=timezone.now().date())
        elif filter_type == 'monthly':
            queryset = queryset.filter(order__created_at__month=timezone.now().month)
        elif filter_type == 'yearly':
            queryset = queryset.filter(order__created_at__year=timezone.now().year)

        # Lọc thêm theo tháng cụ thể (nếu có)
        if selected_month:
            year, month = map(int, selected_month.split('-'))
            queryset = queryset.filter(order__created_at__year=year, order__created_at__month=month)

        # Tính toán thống kê
        sales_data = (
            queryset
            .values('product__product_id', 'product__name')
            .annotate(
                quantity_sold=Sum('quantity'),
                total_sales=Sum(F('quantity') * F('product__sell_price'))
            )
        )

        # Render template
        extra_context = {
            'sales_data': sales_data,
            'filter_type': filter_type,
            'selected_month': selected_month,
            'opts': self.model._meta,
            'app_label': self.model._meta.app_label,
        }
        return render(request, 'admin/product_sales_stats.html', extra_context)
    def stats_button(self, request):
        url = reverse('admin:product-sales-stats')  # Tạo URL cho trang thống kê
        return format_html('<a class="button" href="{}" style="padding: 5px 10px; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 4px;">Xem thống kê</a>', url)

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('review_id', 'product', 'user', 'rating', 'created_at', 'updated_at')
    search_fields = ('product__name', 'user__username')
    list_filter = ('rating', 'created_at')
    ordering = ('-created_at',)


@admin.register(Image)
class ImageAdmin(ImportExportModelAdmin,admin.ModelAdmin):
    list_display = ('image_preview', 'product', 'created_at', 'updated_at')  # Hiển thị ảnh
    search_fields = ('product__name',)
    ordering = ('product__name',)

    def image_preview(self, obj):
        if obj.url:
            return format_html('<img src="{}" style="width: 100px; height: auto;" />', obj.url.url)
        return "No Image"
    image_preview.short_description = "Image Preview"



@admin.register(StockQuantity)
class StockQuantityAdmin(ImportExportModelAdmin,admin.ModelAdmin):
    list_display = ('id', 'product', 'color', 'size', 'stock')
    search_fields = ('product__name', 'color__name', 'size__name')
    ordering = ('product',)



@admin.register(PurchaseInvoice)
class PurchaseInvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_id', 'supplier', 'total_price', 'created_by', 'created_at', 'updated_at')
    search_fields = ('invoice_id', 'supplier', 'created_by__username')
    ordering = ('-created_at',)


@admin.register(PurchaseInvoiceLine)
class PurchaseInvoiceLineAdmin(admin.ModelAdmin):
    list_display = ('invoiceLine_id', 'invoice', 'product', 'quantity', 'price')
    search_fields = ('invoice__invoice_id', 'product__name')
    ordering = ('invoice',)



@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('banner_id', 'image_preview') 
    search_fields = ('banner_id',)                
    ordering = ('banner_id',)                     

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 200px; height: auto;" />', obj.image.url)
        return "No Image"
    image_preview.short_description = "Preview"
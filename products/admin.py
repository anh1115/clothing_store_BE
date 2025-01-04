import uuid
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

class ReviewResource(resources.ModelResource):
    class Meta:
        model = Review
        import_id_fields = ['review_id']
        fields = ('review_id', 'product', 'user', 'rating')

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
    




@admin.register(Review)
class ReviewAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    resource_class = ReviewResource
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

class PurchaseInvoiceLineInline(admin.TabularInline):
    model = PurchaseInvoiceLine
    fields = ('product', 'quantity', 'price')
    extra = 1
    

@admin.register(PurchaseInvoice)
class PurchaseInvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_id', 'supplier', 'total_price', 'created_by', 'created_at', 'updated_at')
    list_filter = ('supplier', 'created_at')  # Lọc theo nhà cung cấp và ngày tạo
    search_fields = ('invoice_id', 'supplier__name', 'created_by__username')  # Tìm kiếm
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at', 'invoice_id')  # Các trường chỉ đọc
    inlines = [PurchaseInvoiceLineInline]
    fieldsets = (
        ("Invoice Details", {
            'fields': ('supplier', 'total_price', 'created_by')  # Thông tin chính
        }),
        ("Timestamps", {
            'fields': ('created_at', 'updated_at'),  # Dấu thời gian
        }),
    )

    def save_model(self, request, obj, form, change):
        if not obj.invoice_id:  # Nếu chưa có invoice_id, tự tạo
            obj.invoice_id = f"INV{str(uuid.uuid4())[:8].upper()}"
        super().save_model(request, obj, form, change)

    def get_readonly_fields(self, request, obj=None):
        if obj:  # Khi chỉnh sửa hóa đơn (đã tồn tại)
            return self.readonly_fields
        return ('created_at', 'updated_at')  # Khi tạo mới

    def response_add(self, request, obj, post_url_continue=None):
        self.message_user(request, f"Hóa đơn {obj.invoice_id} đã được tạo thành công!")
        return super().response_add(request, obj, post_url_continue)

    

@admin.register(PurchaseInvoiceLine)
class PurchaseInvoiceLineAdmin(admin.ModelAdmin):
    list_display = ('invoiceLine_id', 'invoice', 'product', 'quantity', 'price')  # Hiển thị thông tin chính
    search_fields = ('invoice__invoice_id', 'product__name')  # Tìm kiếm theo hóa đơn và sản phẩm
    ordering = ('invoice',)  # Sắp xếp theo hóa đơn
    readonly_fields = ('invoiceLine_id',)  # Các trường chỉ đọc

    fieldsets = (
        ("Invoice Line Details", {
            'fields': ('invoice', 'product', 'quantity', 'price')  # Thông tin dòng hóa đơn
        }),
        ("Identifier", {
            'fields': ('invoiceLine_id',),  # Mã dòng hóa đơn
        }),
    )

    def save_model(self, request, obj, form, change):
        if not obj.invoiceLine_id:  # Nếu chưa có invoiceLine_id, tự tạo
            obj.invoiceLine_id = f"PIL{str(uuid.uuid4())[:8].upper()}"
        super().save_model(request, obj, form, change)

    def get_readonly_fields(self, request, obj=None):
        if obj:  # Khi chỉnh sửa dòng hóa đơn (đã tồn tại)
            return self.readonly_fields
        return []  # Khi tạo mới, không có trường nào chỉ đọc

    def response_add(self, request, obj, post_url_continue=None):
        self.message_user(request, f"Dòng hóa đơn {obj.invoiceLine_id} đã được tạo thành công!")
        return super().response_add(request, obj, post_url_continue)



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
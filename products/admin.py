from django.contrib import admin
from import_export import fields, resources, widgets
from import_export.admin import ExportActionModelAdmin, ImportExportModelAdmin
from .models import (
    Banner, Color, Size, Category, Product, Review, Image, 
    StockQuantity, PurchaseInvoice, PurchaseInvoiceLine
)
from django.utils.html import format_html

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
class ColorAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    resource_class = ColorResource
    list_display = ('color_id', 'name',  'created_at', 'updated_at')
    search_fields = ('name', 'slug')
    ordering = ('name',)


@admin.register(Size)
class SizeAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    resource_class = SizeResource
    list_display = ('size_id', 'name', 'created_at', 'updated_at')
    search_fields = ('name', 'slug')
    ordering = ('name',)


@admin.register(Category)
class CategoryAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    resource_class = CategoryResource
    list_display = ('category_id', 'name',  'parent', 'created_at', 'updated_at')
    search_fields = ('name',)
    list_filter = ('parent',)
    ordering = ('name',)


@admin.register(Product)

class ProductAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    resource_class = ProductResource
    list_display = ('product_id', 'name', 'import_price', 'sell_price', 'created_at', 'updated_at')
    search_fields = ('name', 'product_id')
    list_filter = ('category', 'color', 'size')
    ordering = ('name',)
    inlines = [ImageInline, StockQuantityInline]  # Gắn ImageInline vào ProductAdmin



@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('review_id', 'product', 'user', 'rating', 'created_at', 'updated_at')
    search_fields = ('product__name', 'user__username')
    list_filter = ('rating', 'created_at')
    ordering = ('-created_at',)


@admin.register(Image)
class ImageAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    list_display = ('image_preview', 'product', 'created_at', 'updated_at')  # Hiển thị ảnh
    search_fields = ('product__name',)
    ordering = ('product__name',)

    def image_preview(self, obj):
        if obj.url:
            return format_html('<img src="{}" style="width: 100px; height: auto;" />', obj.url.url)
        return "No Image"
    image_preview.short_description = "Image Preview"



@admin.register(StockQuantity)
class StockQuantityAdmin(ImportExportModelAdmin, admin.ModelAdmin):
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
    list_display = ('banner_id', 'image_preview')  # Hiển thị ID và ảnh xem trước
    search_fields = ('banner_id',)                # Tìm kiếm theo ID banner
    ordering = ('banner_id',)                     # Sắp xếp theo ID banner

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 100px; height: auto;" />', obj.image.url)
        return "No Image"
    image_preview.short_description = "Preview"
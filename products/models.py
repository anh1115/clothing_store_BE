from django.db import models
from django.utils.text import slugify
from django.utils.timezone import now
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError

class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SlugBaseModel(BaseModel):
    name = models.CharField(max_length=255,verbose_name="Tên",)
    slug = models.SlugField(max_length=255, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        abstract = True


class Color(SlugBaseModel):
    color_id = models.CharField(max_length=10, primary_key=True,verbose_name="Mã màu",)
    class Meta:
        verbose_name = "Màu sắc sản phẩm"
        verbose_name_plural = "Màu sắc sản phẩm"

class Size(SlugBaseModel):
    size_id = models.CharField(max_length=10, primary_key=True,verbose_name="Mã kích thước",)
    class Meta:
        verbose_name = "Kích thước sản phẩm"
        verbose_name_plural = "Kích thước sản phẩm"

class Category(BaseModel):
    category_id = models.CharField(max_length=10, primary_key=True,verbose_name="Mã danh mục",)
    name = models.CharField(max_length=255, unique=True, verbose_name="Tên danh mục",)
    description = models.TextField(null=True, blank=True, verbose_name="Mô tả",)
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories',verbose_name="Danh mục cha",
    )
 
    class Meta:
        verbose_name = "Danh mục sản phẩm"
        verbose_name_plural = "Danh mục sản phẩm"
        ordering = ['name']
    def __str__(self):
        return self.name
    
        
class Product(BaseModel):
    product_id = models.CharField(max_length=10, primary_key=True,verbose_name="Mã sản phẩm",)
    name = models.CharField(max_length=255,verbose_name="Tên sản phẩm",)
    import_price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0.0)],verbose_name="Giá nhập",
    )
    sell_price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0.0)], verbose_name="Giá bán",
    )
    description = models.TextField(blank=True, null=True, verbose_name="Mô tả",)
    color = models.ManyToManyField(Color, related_name='products', verbose_name="Màu sắc",)
    category = models.ManyToManyField(Category, related_name='products',verbose_name="Danh mục",)
    size = models.ManyToManyField(Size, related_name='products',verbose_name="Kích cỡ",)

    def __str__(self):
        return self.product_id
    class Meta:
        verbose_name = "Sản phẩm"
        verbose_name_plural = "Quản lý sản phẩm"

class Review(BaseModel):
    review_id = models.AutoField(primary_key=True,verbose_name="Mã đánh giá",)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews',verbose_name="Sản phẩm",)
    user = models.ForeignKey('user.User', on_delete=models.CASCADE, related_name='reviews',verbose_name="Người dùng",)
    rating = models.PositiveSmallIntegerField(verbose_name="Số sao",)
    comment = models.TextField(null=True, blank=True,verbose_name="Bình luận",)

    class Meta:
        verbose_name = "Đánh giá"
        verbose_name_plural = "Quản lý đánh giá"
        constraints = [
            models.CheckConstraint(
                check=models.Q(rating__gte=1) & models.Q(rating__lte=5),
                name="rating_range_1_to_5"
            )
        ]
        ordering = ['created_at']

    def __str__(self):
        return f"Review {self.review_id} for {self.product.name} by {self.user}"

class Image(BaseModel):
    id = models.AutoField(primary_key=True, verbose_name="Mã hình ảnh",)
    url = models.ImageField(upload_to='products/',verbose_name="URL",)  # Ảnh sẽ được lưu trong thư mục 'products/'
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images',verbose_name="Sản phẩm",)

    def __str__(self):
        if self.url:  # Kiểm tra nếu có ảnh
            return self.url.url
        return "No Image"
    class Meta:
        verbose_name = "Hình ảnh"
        verbose_name_plural = "Hình ảnh sản phẩm"


class StockQuantity(models.Model):
    id = models.AutoField(primary_key=True, verbose_name="Mã",)
    stock = models.IntegerField(verbose_name="Số lượng tồn kho",)
    size = models.ForeignKey(Size, on_delete=models.CASCADE, related_name='stock_quantities', verbose_name="Kích cỡ",)
    color = models.ForeignKey(Color, on_delete=models.CASCADE, related_name='stock_quantities',verbose_name="Màu sắc",)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_quantities', verbose_name="Sản phẩm",)

    def __str__(self):
        return f"{self.product.name} - {self.color.name} - {self.size.name}: {self.stock}"

    def save(self, *args, **kwargs):
        if self.id:  # Nếu bản ghi hiện tại đã tồn tại
        # Lưu thay đổi trực tiếp
            super().save(*args, **kwargs)
        else:  # Nếu là bản ghi mới
        # Truy vấn xem đã có bản ghi trùng lặp hay chưa
            existing_stock = StockQuantity.objects.filter(
                product=self.product,
                size=self.size,
                color=self.color
            ).first()

            if existing_stock:
                # Nếu tồn tại, cập nhật số lượng cho bản ghi trùng
                existing_stock.stock += self.stock
                existing_stock.save()
            else:
            # Nếu không tồn tại, lưu bản ghi mới
                super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Số lượng tồn kho"
        verbose_name_plural = "Số lượng tồn kho"




class ProductColor(BaseModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='product_colors')
    color = models.ForeignKey(Color, on_delete=models.CASCADE, related_name='product_colors')

    def __str__(self):
        return f"{self.product.name} - {self.color.name}"


class ProductSize(BaseModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='product_sizes')
    size = models.ForeignKey(Size, on_delete=models.CASCADE, related_name='product_sizes')

    def __str__(self):
        return f"{self.product.name} - {self.size.name}"


class ProductCategory(BaseModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='product_categories')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='product_categories')

    def __str__(self):
        return f"{self.product.name} - {self.category.name}"


class PurchaseInvoice(BaseModel):
    invoice_id = models.CharField(max_length=50, primary_key=True,verbose_name="Mã hóa đơn",)
    supplier = models.CharField(max_length=255, verbose_name="Nhà cung cấp",)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Tổng tiền",)
    created_by = models.ForeignKey('user.User', on_delete=models.CASCADE, verbose_name="Nhập bởi",)

    class Meta:
        verbose_name = "Hóa đơn nhập hàng"
        verbose_name_plural = "Hóa đơn nhập hàng"
        ordering = ['created_at']

    def __str__(self):
        return f"Purchase Invoice {self.invoice_id} by {self.created_by}"
    

class PurchaseInvoiceLine(models.Model):
    invoiceLine_id = models.CharField(max_length=50, primary_key=True,verbose_name="Mã chi tiết hóa đơn",)
    invoice = models.ForeignKey(PurchaseInvoice, on_delete=models.CASCADE, verbose_name="Mã hóa đơn",)
    product = models.ForeignKey(Product, on_delete=models.CASCADE,verbose_name="Sản phẩm",)
    quantity = models.IntegerField(verbose_name="Số lượng",)
    price = models.DecimalField(max_digits=10, decimal_places=2,verbose_name="Giá",)

    class Meta:
        verbose_name = "Chi tiết nhập hàng"
        verbose_name_plural = "Chi tiết nhập hàng"
        ordering = ['invoice']

    def __str__(self):
        return f"Invoice Line {self.invoiceLine_id} for {self.product.name}"
    
class Banner(models.Model):
    banner_id = models.CharField(max_length=10, primary_key=True)
    image = models.ImageField(upload_to='banners/')  # Lưu ảnh vào thư mục 'banners'
    def save(self, *args, **kwargs):
        if Banner.objects.count() >= 5:
            raise ValidationError("Chỉ cho phép lưu tối đa 5 ảnh")
        super().save(*args, **kwargs)
    def __str__(self):
        return f"Banner {self.banner_id}"
    class Meta:
        verbose_name = "Hình ảnh quảng cáo"
        verbose_name_plural = "Hình ảnh quảng cáo"


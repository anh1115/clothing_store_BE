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
    name = models.CharField(max_length=255)
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
    color_id = models.CharField(max_length=10, primary_key=True)


class Size(SlugBaseModel):
    size_id = models.CharField(max_length=10, primary_key=True)


class Category(BaseModel):
    category_id = models.CharField(max_length=10, primary_key=True)
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(null=True, blank=True)
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories'
    )
 
    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ['name']
    def __str__(self):
        return self.name

class Product(BaseModel):
    product_id = models.CharField(max_length=10, primary_key=True)
    name = models.CharField(max_length=255)
    import_price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0.0)]
    )
    sell_price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0.0)]
    )
    description = models.TextField(blank=True, null=True)
    color = models.ManyToManyField(Color, related_name='products')
    category = models.ManyToManyField(Category, related_name='products')
    size = models.ManyToManyField(Size, related_name='products')

    def __str__(self):
        return self.name


class Review(BaseModel):
    review_id = models.AutoField(primary_key=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey('user.User', on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = "Review"
        verbose_name_plural = "Reviews"
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
    id = models.AutoField(primary_key=True)
    url = models.ImageField(upload_to='products/')  # Ảnh sẽ được lưu trong thư mục 'products/'
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')

    def __str__(self):
        if self.url:  # Kiểm tra nếu có ảnh
            return self.url.url
        return "No Image"



class StockQuantity(models.Model):
    id = models.AutoField(primary_key=True)
    stock = models.IntegerField()
    size = models.ForeignKey(Size, on_delete=models.CASCADE, related_name='stock_quantities')
    color = models.ForeignKey(Color, on_delete=models.CASCADE, related_name='stock_quantities')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_quantities')

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
    invoice_id = models.CharField(max_length=10, primary_key=True)
    supplier = models.CharField(max_length=255)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    created_by = models.ForeignKey('user.User', on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Purchase Invoice"
        verbose_name_plural = "Purchase Invoices"
        ordering = ['created_at']

    def __str__(self):
        return f"Purchase Invoice {self.invoice_id} by {self.created_by}"


class PurchaseInvoiceLine(models.Model):
    invoiceLine_id = models.CharField(max_length=10, primary_key=True)
    invoice = models.ForeignKey(PurchaseInvoice, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Purchase Invoice Line"
        verbose_name_plural = "Purchase Invoice Lines"
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

from uuid import uuid4
from django.conf import settings
from django.db import models
from user.models import User
from products.models import Color, Product, Size

class Cart(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart of {self.user.username}"

    def total_quantity(self):
        """Calculate total quantity of items in the cart."""
        return sum(item.quantity for item in self.cart_details.all())

    def total_price(self):
        """Calculate total price of items in the cart."""
        return sum(item.subtotal() for item in self.cart_details.all())
    
class CartDetail(models.Model):
    id = models.AutoField(primary_key=True)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='cart_details')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='cart_details')
    color = models.ForeignKey('products.Color', on_delete=models.SET_NULL, null=True, blank=True, related_name='cart_details')
    size = models.ForeignKey('products.Size', on_delete=models.SET_NULL, null=True, blank=True, related_name='cart_details')
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        product_name = self.product.name if self.product else "No Product"
        color_name = self.color.name if self.color else "No Color"
        size_name = self.size.name if self.size else "No Size"
        return f"{product_name} ({color_name}, {size_name}) x {self.quantity}"

    def subtotal(self):
        """Calculate subtotal for the cart detail."""
        return self.product.price * self.quantity if self.product else 0

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['cart', 'product', 'color', 'size'],
                name='unique_cart_product_color_size'
            )
        ]

class Order(models.Model):
    order_id = models.CharField(max_length=50, primary_key=True, unique=True,verbose_name = "Mã đơn hàng")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders',verbose_name = "Khách hàng")
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Đang chờ xử lý'),
        ('confirmed', 'Đã xác nhận'),
        ('shipped', 'Đã vận chuyển'),
        ('delivered', 'Đã giao'),
        ('cancelled', 'Đã hủy'),
    ],verbose_name = "Trạng thái đơn")
    note = models.CharField(max_length=255,null=True,blank=True, default='',verbose_name = "Ghi chú")
    total_price = models.DecimalField(max_digits=10, decimal_places=2,default=0.00,editable=False,verbose_name = "Tổng giá trị")
    payment_method = models.CharField(max_length=50, choices=[
        ('cash_on_delivery', 'Tiền mặt'),
        ('bank_transfer', 'Chuyển khoản ngân hàng'),

    ],verbose_name = "Phương thức thanh toán")
    created_at = models.DateTimeField(auto_now_add=True,verbose_name = "Ngày tạo")
    updated_at = models.DateTimeField(auto_now=True,verbose_name = "Ngày cập nhật")
    vnp_BankCode = models.CharField(max_length=20,null=True,blank=True, default='')
    vnp_BankTranNo = models.CharField(max_length=255,null=True,blank=True,default='')
    vnp_CardType = models.CharField(max_length=20,null=True,blank=True,default='')
    vnp_ResponseCode = models.CharField(max_length=2,null=True,blank=True,default='')
    vnp_TransactionNo = models.CharField(max_length=15,null=True,blank=True,default='')
    vnp_TransactionStatus = models.CharField(max_length=2,null=True,blank=True,default='')
    def __str__(self):
        return f"Order {self.order_id} - {self.user.full_name} - {self.vnp_TransactionNo}"
    def update_total_price(self):
        total = sum(line.subtotal() for line in self.order_lines.all())
        self.total_price = total
        self.save()
    class Meta:
        verbose_name = "Đơn hàng"
        verbose_name_plural = "Quản lý đơn hàng"
class OrderLine(models.Model):
    orderline_id = models.CharField(max_length=50, primary_key=True, unique=True,editable=False, blank=True, verbose_name = "Mã dòng đơn hàng")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_lines',verbose_name = "Mã đơn hàng")
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='order_lines',verbose_name = "Sản phẩm")
    color = models.ForeignKey('products.Color', on_delete=models.CASCADE,default=1, related_name='order_lines',verbose_name = "Màu sắc")  
    size = models.ForeignKey('products.Size', on_delete=models.CASCADE,default=1, related_name='order_lines',verbose_name = "Kích cỡ") 
    quantity = models.PositiveIntegerField(verbose_name = "Số lượng")
    created_at = models.DateTimeField(auto_now_add=True,verbose_name = "Ngày tạo")
    updated_at = models.DateTimeField(auto_now=True,verbose_name = "Ngày cập nhật")
    status_review = models.IntegerField(choices=[(0, 'Not Reviewed'), (1, 'Reviewed')], default=0,verbose_name = "Trạng thái đánh giá")

    def __str__(self):
        return f"{self.orderline_id} "
    
    def subtotal(self):
        """Calculate subtotal for the order line."""
        return self.product.sell_price * self.quantity
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.order.update_total_price()
    def save(self, *args, **kwargs):
        # Tự động sinh `orderline_id` nếu chưa có
        if not self.orderline_id:
            self.orderline_id = f"OL{str(uuid4())[:8].upper()}"
        super().save(*args, **kwargs)
    # Gọi cập nhật tổng giá khi xóa
    def delete(self, *args, **kwargs):
        order = self.order  # Lưu lại tham chiếu đơn hàng
        super().delete(*args, **kwargs)
        order.update_total_price()
    class Meta:
        verbose_name = "Chi tiết đơn hàng"
        verbose_name_plural = "Chi tiết đơn hàng"
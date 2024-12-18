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
    order_id = models.CharField(max_length=50, primary_key=True, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Đang chờ xử lý'),
        ('confirmed', 'Đã xác nhận'),
        ('shipped', 'Đã vận chuyển'),
        ('delivered', 'Đã giao'),
        ('cancelled', 'Đã hủy'),
    ])
    note = models.CharField(max_length=255, default='')
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50, choices=[
        ('cash_on_delivery', 'Tiền mặt'),
        ('bank_transfer', 'Chuyển khoản ngân hàng'),
        ('paypal', 'PayPal'),
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order {self.order_id} - {self.user.full_name}"

class OrderLine(models.Model):
    orderline_id = models.CharField(max_length=50, primary_key=True, unique=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_lines')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='order_lines')
    color = models.ForeignKey('products.Color', on_delete=models.CASCADE, related_name='order_lines', default='1')  
    size = models.ForeignKey('products.Size', on_delete=models.CASCADE, related_name='order_lines', default='1') 
    quantity = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.orderline_id}" 

    def subtotal(self):
        """Calculate subtotal for the order line."""
        return self.product.sell_price * self.quantity

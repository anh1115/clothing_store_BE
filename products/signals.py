from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import PurchaseInvoice, PurchaseInvoiceLine, Product

@receiver(post_save, sender=PurchaseInvoice)
def create_invoice_lines(sender, instance, created, **kwargs):
    """
    Tự động tạo dòng chi tiết hóa đơn mặc định khi tạo hóa đơn nhập hàng
    """
    if created:  # Chỉ tạo khi hóa đơn mới được tạo
        products = Product.objects.all()  # Lấy danh sách sản phẩm (tùy vào logic)
        for product in products:
            # Tạo dòng chi tiết với số lượng mặc định (ví dụ: 0)
            PurchaseInvoiceLine.objects.create(
                invoice=instance,
                product=product,
                quantity=0,  # Hoặc số lượng mặc định
                price=product.import_price  # Hoặc giá mặc định
            )

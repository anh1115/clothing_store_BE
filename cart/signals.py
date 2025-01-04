# from django.db.models.signals import post_save, post_delete
# from django.dispatch import receiver
# from .models import Order, OrderLine

# @receiver(post_save, sender=OrderLine)
# @receiver(post_delete, sender=OrderLine)
# def update_order_total(sender, instance, **kwargs):
#     order = instance.order
#     # Tính tổng tiền từ tất cả các OrderLine thuộc Order
#     total_price = sum(line.quantity * line.price for line in order.order_lines.all())
#     order.total_price = total_price
#     order.save()

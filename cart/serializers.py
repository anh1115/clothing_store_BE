from rest_framework import serializers
from .models import Cart, CartDetail, Order, OrderLine
from products.models import Product, Color, Size

class CartDetailSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')
    product_sell_price = serializers.ReadOnlyField(source='product.sell_price')
    color_name = serializers.ReadOnlyField(source='color.name')
    size_name = serializers.ReadOnlyField(source='size.name')
    subtotal = serializers.SerializerMethodField()
    first_image_url = serializers.SerializerMethodField()

    class Meta:
        model = CartDetail
        fields = [
            'product_id', 'product_name', 'product_sell_price', 'color_id', 'color_name', 
            'size_id', 'size_name', 'quantity', 'subtotal', 'first_image_url'
        ]

    def get_subtotal(self, obj):
        """
        Tính tổng tiền cho mục giỏ hàng này.
        """
        return obj.quantity * obj.product.sell_price
    def get_first_image_url(self, obj):
        """
        Lấy URL của ảnh đầu tiên của sản phẩm.
        """
        first_image = obj.product.images.first() # Lấy ảnh đầu tiên
        if first_image:
            return first_image.url.url  # Trả về URL của ảnh đầu tiên
        return None


class CartSerializer(serializers.ModelSerializer):
    items = CartDetailSerializer(source='cart_details', many=True)
    total = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['id', 'user', 'items', 'total']

    def get_total(self, obj):
        """
        Tính tổng tiền cho toàn bộ giỏ hàng.
        """
        return sum(
            detail.quantity * detail.product.sell_price for detail in obj.cart_details.all()
        )

class OrderLineSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name')
    product_sell_price = serializers.DecimalField(source='product.sell_price', max_digits=10, decimal_places=2)
    color_name = serializers.CharField(source='color.name')  # Thêm trường color_name
    size_name = serializers.CharField(source='size.name')    # Thêm trường size_name

    class Meta:
        model = OrderLine
        fields = ['orderline_id', 'product_id', 'product_name', 'product_sell_price', 'color_name', 'size_name','quantity', 'subtotal','status_review']
    
    

class OrderSerializer(serializers.ModelSerializer):
    order_lines = OrderLineSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    class Meta:
        model = Order
        fields = ['order_id', 'user', 'status_display', 'total_price', 'payment_method','note', 'created_at', 'updated_at', 'order_lines']


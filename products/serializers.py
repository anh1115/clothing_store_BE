from rest_framework import serializers
from django.conf import settings
from .models import Banner, Product, Category, Color, Review, Size, StockQuantity, Image


class ColorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Color
        fields = ['color_id', 'name']


class SizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Size
        fields = ['size_id', 'name']


class StockQuantitySerializer(serializers.ModelSerializer):
    color = ColorSerializer()
    size = SizeSerializer()

    class Meta:
        model = StockQuantity
        fields = ['color', 'size', 'stock']

class CategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    class Meta:
        model = Category
        fields = ['category_id', 'name', 'description', 'parent', 'children']

    def get_children(self, obj):
        # Lấy các danh mục con
        children = Category.objects.filter(parent=obj)
        return CategorySerializer(children, many=True).data

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Image
        fields = ['id', 'url']
    def get_url(self, obj):
        # Nối domain của BE vào URL
        domain = settings.BASE_URL
        return domain + obj.url

class ProductSerializer(serializers.ModelSerializer):
    colors = ColorSerializer(source='color', many=True, read_only=True)
    sizes = SizeSerializer(source='size', many=True, read_only=True)
    categories = CategorySerializer(source='category', many=True, read_only=True)
    stock_quantities = StockQuantitySerializer( many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            'product_id', 'name', 'images', 'description', 'sell_price', 
            'colors', 'sizes', 'categories', 'stock_quantities', 'created_at', 'updated_at'
        ]

class ReviewSerializer(serializers.ModelSerializer):
    product_id = serializers.CharField(write_only=True) 
    full_name = serializers.CharField(source='user.full_name', read_only=True)
    class Meta:
        model = Review
        fields = ['review_id', 'product_id','full_name', 'rating', 'comment']
    
    def create(self, validated_data):
        # Lấy product_id và tìm sản phẩm tương ứng
        product_id = validated_data.pop('product_id')
        try:
            product = Product.objects.get(product_id=product_id)
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product with given product_id does not exist.")

        # Tạo bình luận với sản phẩm đã tìm được
        review = Review.objects.create(product=product, **validated_data)
        return review
    
class BannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = ['banner_id', 'image']

    def validate(self, data):
        if Banner.objects.count() >= 5:
            raise serializers.ValidationError("Chỉ cho phép lưu tối đa 5 ảnh")
        return data


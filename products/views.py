from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import ListAPIView
from rest_framework.exceptions import  ValidationError
from django.db.models import Q
from .models import Banner, Product, Category, Review
from .serializers import BannerSerializer, ProductSerializer, CategorySerializer, ReviewSerializer
from rest_framework import status, permissions
from unidecode import unidecode
from rest_framework.permissions import IsAuthenticated

class ProductListView(ListAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

class ProductDetail(APIView):
    def get(self, request, product_id, format=None):
        try:
            # Lấy sản phẩm từ database theo product_id
            product = Product.objects.get(product_id=product_id)
        except Product.DoesNotExist:
            return Response({"detail": "Product not found."}, status=status.HTTP_404_NOT_FOUND)
        
        # Serialize sản phẩm
        serializer = ProductSerializer(product)
        return Response(serializer.data)

class ProductSearchView(APIView):
    def get(self, request):
        search_query = request.query_params.get('q', '').strip()

        if search_query:
            normalized_query = unidecode(search_query).lower()
            products = Product.objects.filter(
                Q(name__icontains=search_query) | 
                Q(name__icontains=normalized_query) |
                Q(name__icontains=unidecode(search_query))
            )
        else:
            products = Product.objects.all()

        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)

class CategoryListView(ListAPIView):
    queryset = Category.objects.filter(parent=None)
    serializer_class = CategorySerializer


class NewProductsView(APIView):
    def get(self, request):
        products = Product.objects.order_by('-created_at')[:10]
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)


class FilterProductsByPriceView(APIView):
    def get(self, request):
        min_price = request.query_params.get('min_price', 0)
        max_price = request.query_params.get('max_price', 9999999)
        category_id = request.query_params.get('category_id', None)
        
        # Xây dựng bộ lọc cơ bản
        filters = Q(sell_price__gte=min_price) & Q(sell_price__lte=max_price)

        # Thêm điều kiện lọc theo category_id nếu có
        if category_id:
            filters &= Q(category__category_id=category_id)
        
        # Truy vấn sản phẩm theo điều kiện lọc
        products = Product.objects.filter(filters)
        
        # Serialize và trả kết quả
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)


class ProductsByCategoryView(APIView):
    def get(self, request, category_id):
        products = Product.objects.filter(category__category_id=category_id)
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)

class ProductReviewListView(APIView):
    permission_classes = [permissions.AllowAny] 

    def get(self, request, product_id):
        try:
            reviews = Review.objects.filter(product_id=product_id)
            if not reviews.exists():
                return Response({"message": "No reviews found for this product."}, status=status.HTTP_404_NOT_FOUND)
            
            serializer = ReviewSerializer(reviews, many=True)
            
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            raise ValidationError({"error": str(e)})


class ReviewCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]  # Chỉ cho phép người dùng đã đăng nhập

    def post(self, request, *args, **kwargs):
        # Thêm bình luận và gắn với product_id
        serializer = ReviewSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)  # Gán người dùng hiện tại vào bình luận
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




class BannerList(APIView):
    def get(self, request, format=None):
        banners = Banner.objects.all()
        serializer = BannerSerializer(banners, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, format=None):
        serializer = BannerSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

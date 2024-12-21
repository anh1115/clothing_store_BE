import logging
from cart.models import OrderLine
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import ListAPIView
from rest_framework.exceptions import  ValidationError
from django.db.models import Q
from .models import Banner, Image, Product, Category, Review
from .serializers import BannerSerializer, ProductSerializer, CategorySerializer, ReviewSerializer
from rest_framework import status, permissions
from unidecode import unidecode
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, F
from django.utils.timezone import now
from django.db.models import OuterRef, Subquery
from rest_framework import pagination
from rest_framework.pagination import PageNumberPagination
from .utils import get_vietnamese_stopwords, clean_description, calculate_cosine_similarity, calculate_weighted_scores

class ProductReviewPagination(pagination.PageNumberPagination):
    page_size = 10  # Số lượng bình luận mỗi trang
    page_size_query_param = 'page_size'  # Cho phép client thay đổi số lượng bình luận mỗi trang
    max_page_size = 100  # Số bình luận tối đa mỗi trang
    def get_paginated_response(self, data):
        # Sử dụng method gốc để lấy response phân trang
        response = super().get_paginated_response(data)
        
        # Thêm các thông tin bổ sung vào response
        response.data['count'] = self.page.paginator.count  # Tổng số bình luận
        response.data['page_size'] = self.page_size  # Số bình luận mỗi trang
        response.data['current_page'] = self.page.number  # Trang hiện tại
        response.data['total_pages'] = self.page.paginator.num_pages  # Tổng số trang
        
        return response

class CustomPagination(PageNumberPagination):
    page_size = 20  # Số sản phẩm mỗi trang
    page_size_query_param = 'page_size'  # Client có thể thay đổi số lượng sản phẩm mỗi trang
    max_page_size = 100  # Giới hạn số lượng sản phẩm tối đa mỗi trang
    def get_paginated_response(self, data):
        response = super().get_paginated_response(data)
        response.data['count'] = self.page.paginator.count  
        response.data['page_size'] = self.page_size  
        response.data['current_page'] = self.page.number  
        response.data['total_pages'] = self.page.paginator.num_pages 
        
        return response
    
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
        paginator = CustomPagination()
        paginated_products = paginator.paginate_queryset(products, request)
        
        # Serialize và trả kết quả
        
        serializer = ProductSerializer(paginated_products, many=True)
        return paginator.get_paginated_response(serializer.data)
        


class ProductsByCategoryView(APIView):
    
    def get(self, request, category_id):
        products = Product.objects.filter(category__category_id=category_id)
        
        paginator = CustomPagination()
        paginated_products = paginator.paginate_queryset(products, request)
        
        # Serialize và trả kết quả
        
        serializer = ProductSerializer(paginated_products, many=True)
        return paginator.get_paginated_response(serializer.data)

class ProductReviewListView(APIView):
    permission_classes = [permissions.AllowAny] 

    def get(self, request, product_id):
        try:
            reviews = Review.objects.filter(product_id=product_id)
            if not reviews.exists():
                return Response({"message": "No reviews found for this product."}, status=status.HTTP_404_NOT_FOUND)
            
            # Áp dụng phân trang
            paginator = ProductReviewPagination()
            result_page = paginator.paginate_queryset(reviews, request)

            serializer = ReviewSerializer(result_page, many=True)
            
            return paginator.get_paginated_response(serializer.data)
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


class TopSalesRealTimeAPIView(APIView):
    def get(self, request, *args, **kwargs):
        # Lấy thời gian hiện tại
        current_date = now()
        current_month = current_date.month
        current_year = current_date.year

        # Mặc định lấy dữ liệu của tháng hiện tại
        month = int(request.GET.get('month', current_month))  # Lấy từ query params hoặc mặc định
        year = int(request.GET.get('year', current_year))  # Lấy từ query params hoặc mặc định

        try:
            # Truy vấn dữ liệu của tháng hiện tại
            order_lines = OrderLine.objects.filter(
                order__created_at__year=year,
                order__created_at__month=month
            )
            product_images = Image.objects.filter(product=OuterRef('product')).values('url')[:1]
            # Tổng hợp số lượng bán và doanh thu của từng sản phẩm
            sales_data = (
                order_lines.values('product__product_id', 'product__name', 'product__sell_price')
                .annotate(
                    quantity_sold=Sum('quantity'),
                    total_sales=Sum(F('quantity') * F('product__sell_price')),
                    image_url=Subquery(product_images)
                )
                .order_by('-quantity_sold')[:8]  # Sắp xếp theo số lượng bán giảm dần
            )

            # Chuẩn bị dữ liệu để trả về
            response_data = [
                {
                    'product_id': item['product__product_id'],
                    'name': item['product__name'],
                    'sell_price': item['product__sell_price'],
                    'quantity_sold': item['quantity_sold'],
                    'total_sales': item['total_sales'],
                    'image_url': item['image_url'] if item['image_url'] else None
                }
                for item in sales_data
            ]

            return Response({
                'month': month,
                'year': year,
                'top_sales': response_data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        
        

# Sản phẩm liên quan
logger = logging.getLogger(__name__)

class RelatedProductsView(APIView):
    def get(self, request, product_id):
        try:
            logger.info(f"Fetching related products for product_id: {product_id}")

            vietnamese_stopwords = get_vietnamese_stopwords()

            # Lấy sản phẩm hiện tại từ product_id
            product = Product.objects.get(product_id=product_id)
            products = Product.objects.exclude(product_id=product_id)  # Exclude the current product

            # Xử lý mô tả của các sản phẩm
            features = [f"{p.name} {p.category} {clean_description(p.description)}" for p in products] + [f"{product.name} {product.category} {clean_description(product.description)}"]

            # Tính độ tương đồng cosine
            cosine_sim = calculate_cosine_similarity(features, vietnamese_stopwords)

            # Tính sự khác biệt về giá và điểm trọng số
            weighted_scores = calculate_weighted_scores(cosine_sim, product, products)

            # Sắp xếp các sản phẩm theo điểm tương đồng (cả mô tả và giá)
            sorted_indices = weighted_scores.argsort()[-5:][::-1]

            # Chuyển QuerySet thành danh sách để truy cập qua chỉ mục
            products_list = list(products)
            related_products = [products_list[i] for i in sorted_indices]

            # Serialize dữ liệu
            serializer = ProductSerializer(related_products, many=True)
            return Response(serializer.data)

        except Product.DoesNotExist:
            logger.error(f"Product with id {product_id} not found.")
            return Response({"error": "Product not found"}, status=404)
        except Exception as e:
            logger.error(f"Error occurred: {e}")
            return Response({"error": str(e)}, status=500)
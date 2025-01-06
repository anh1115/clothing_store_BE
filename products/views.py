
from cart.models import Order, OrderLine
import json
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import ListAPIView
from rest_framework.exceptions import  ValidationError
from django.db.models import Q

from .vnpay import VNPay
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

from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from datetime import datetime
from django.contrib.auth.decorators import user_passes_test
from user.models import User
from .utils import get_vietnamese_stopwords, clean_description, calculate_cosine_similarity, calculate_weighted_scores, recommend_products

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.conf import settings
from datetime import datetime, timedelta
import hashlib
import json
import hmac
import pytz

def hmacsha512(key, data):
    byteKey = key.encode('utf-8')
    byteData = data.encode('utf-8')
    return hmac.new(byteKey, byteData, hashlib.sha512).hexdigest()
    
@csrf_exempt
# API tạo giao dịch thanh toán
def create_payment(request):
    if request.method == 'POST':
        try:
            # Lấy dữ liệu JSON từ request.body
            data = json.loads(request.body)


            # Lấy các tham số từ dữ liệu JSON
            order_type = data.get('order_type')
            order_id = data.get('order_id')
            amount = data.get('amount')
            order_desc = data.get('order_desc')
            bank_code = data.get('bank_code')
            language = data.get('language')
            ipaddr = "127.0.0.1"  # Có thể thay đổi cách lấy IP nếu cần

            # Kiểm tra nếu dữ liệu cần thiết bị thiếu
            if not all([order_type, order_id, amount, order_desc]):
                return JsonResponse({
                    "status": "error",
                    "message": "Dữ liệu đầu vào không hợp lệ.",
                    "errors": "Thiếu thông tin quan trọng như order_type, order_id, amount, hoặc order_desc."
                }, status=400)

            # Chuyển đổi amount thành integer (vì nó có thể là chuỗi)
            try:
                amount = int(amount)
            except ValueError:
                return JsonResponse({
                    "status": "error",
                    "message": "Số tiền không hợp lệ."
                }, status=400)

            # Tính toán thời gian hiện tại theo múi giờ GMT+7 (Sài Gòn)
            vietnam_timezone = pytz.timezone('Asia/Ho_Chi_Minh')
            current_time = datetime.now(vietnam_timezone)

            # Định dạng thời gian theo định dạng yyyyMMddHHmmss
            vnp_create_date = current_time.strftime("%Y%m%d%H%M%S")

            # Tính toán thời gian hết hạn (ví dụ: 15 phút từ thời điểm hiện tại)
            expire_time = current_time + timedelta(minutes=15)
            vnp_expire_date = expire_time.strftime("%Y%m%d%H%M%S")  # Định dạng yyyyMMddHHmmss
            # Tạo dữ liệu thanh toán VNPAY
            vnpay_data = {
                "vnp_OrderInfo": order_desc,  # Thông tin đơn hàng
                "vnp_TmnCode": settings.VNPAY_MERCHANT_CODE,  # Mã Merchant (TmnCode)
                "vnp_TxnRef": order_id,  # Mã đơn hàng
                "vnp_Amount": amount * 100,  # Số tiền (VND)
                "vnp_OrderType": order_type,  # Loại giao dịch
                "vnp_Locale": 'vn',  # Ngôn ngữ giao diện
                "vnp_IpAddr": ipaddr,  # Địa chỉ IP người dùng
                "vnp_ReturnUrl": "http://127.0.0.1:5173/vnpay-return/",  # URL trả về sau thanh toán
                "vnp_CurrCode": "VND",  # Mã tiền tệ (VND)
                "vnp_Version": "2.1.0",  # Phiên bản API
                "vnp_Command": "pay",  # Lệnh thanh toán
                "vnp_ExpireDate": vnp_expire_date,
                "vnp_CreateDate": vnp_create_date,
            }

            # Khởi tạo đối tượng VNPay và tạo URL thanh toán
            vnpay = VNPay(vnpay_data)
            vnpay_url = vnpay.get_payment_url(settings.VNPAY_URL, settings.VNPAY_HASH_SECRET)

            # Trả về URL thanh toán VNPAY
            return JsonResponse({
                "status": "success",
                "payment_url": vnpay_url,
                "message": "Vui lòng truy cập URL để thực hiện thanh toán."
            }, status=200)

        except json.JSONDecodeError as e:
            return JsonResponse({
                "status": "error",
                "message": "Dữ liệu JSON không hợp lệ.",
                "errors": str(e)
            }, status=400)

    else:
        return JsonResponse({
            "status": "error",
            "message": "Phương thức không được hỗ trợ."
        }, status=405)
    

        
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

class CustomsPagination(PageNumberPagination):
    page_size = 20  # Số sản phẩm mỗi trang mặc định
    page_size_query_param = 'page_size'  # Tham số để client tùy chỉnh số sản phẩm mỗi trang
    max_page_size = 100  # Giới hạn số lượng sản phẩm tối đa mỗi trang

    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,  # Tổng số sản phẩm
            'page_size': self.page_size,  # Số sản phẩm mỗi trang
            'current_page': self.page.number,  # Trang hiện tại
            'total_pages': self.page.paginator.num_pages,  # Tổng số trang
            'results': data  # Dữ liệu sản phẩm
        })


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

        paginator = CustomsPagination()
        paginated_products = paginator.paginate_queryset(products, request)

        if paginated_products is not None:
            # Trường hợp sử dụng phân trang
            serializer = ProductSerializer(paginated_products, many=True)
            return paginator.get_paginated_response(serializer.data)

        # Trường hợp không sử dụng phân trang
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
        # Giả sử bạn gửi orderline_id trong request để xác định dòng đơn hàng cần cập nhật
        orderline_id = request.data.get('orderline_id')
        
        # Kiểm tra nếu orderline_id tồn tại
        if not orderline_id:
            return Response({'message': 'orderline_id là bắt buộc.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Lấy OrderLine tương ứng với orderline_id
            orderline = OrderLine.objects.get(orderline_id=orderline_id)

            # Thực hiện lưu review (bạn có thể sử dụng ReviewSerializer để tạo review)
            serializer = ReviewSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(user=request.user)  # Gán người dùng hiện tại vào bình luận
                
                # Cập nhật status_review thành 1 (đã đánh giá)
                orderline.status_review = 1
                orderline.save()

                return Response({
                    'message': 'Bình luận đã được thêm thành công.',
                    'data': serializer.data
                }, status=status.HTTP_201_CREATED)
            return Response({
                'message': 'Có lỗi xảy ra khi thêm bình luận.',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        except OrderLine.DoesNotExist:
            return Response({'message': 'Dòng đơn hàng không tồn tại.'}, status=status.HTTP_404_NOT_FOUND)



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

from datetime import datetime

def is_superuser(user):
    return user.is_superuser

@user_passes_test(is_superuser)
def dashboard_view(request):
    # Tính toán doanh thu trong thời gian qua
    orders = Order.objects.filter(status='delivered')

    # Chọn thời gian để thống kê (ví dụ: tháng qua)
    start_date_str = request.GET.get('start_date', '2023-01-01')
    end_date_str = request.GET.get('end_date', '2023-12-31')

    # Chuyển đổi chuỗi thành ngày
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        # Nếu không thể chuyển đổi, gán giá trị mặc định
        start_date = datetime(2023, 1, 1).date()
        end_date = datetime(2023, 12, 31).date()

    # Lọc đơn hàng theo khoảng thời gian
    orders_in_range = orders.filter(created_at__date__range=[start_date, end_date])

    # Tính toán doanh thu theo ngày
    revenue_per_day = orders_in_range.values('created_at__date').annotate(
        total_revenue=Sum('total_price')
    ).order_by('created_at__date')

    # Nếu không có doanh thu, tạo một danh sách với doanh thu 0
    if not revenue_per_day:
        dates = [start_date.strftime('%Y-%m-%d')]
        revenues = [0]
    else:
        # Chuyển doanh thu thành số thực (float) để tránh lỗi Decimal trong JavaScript
        dates = [entry['created_at__date'].strftime('%Y-%m-%d') for entry in revenue_per_day]
        revenues = [float(entry['total_revenue']) for entry in revenue_per_day]


    # Trả về kết quả cho template
    return render(request, 'admin/dashboard.html', {
        'dates': dates,
        'revenues': revenues
    })




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
class RelatedProductsView(APIView):
    def get(self, request, product_id):
        try:
            vietnamese_stopwords = get_vietnamese_stopwords()
            # Lấy sản phẩm hiện tại từ product_id
            product = Product.objects.get(product_id=product_id)
            products = Product.objects.exclude(product_id=product_id) 
            features = [f"{p.name} {p.category} {clean_description(p.description)}" for p in products] + [f"{product.name} {product.category} {clean_description(product.description)}"]
            # Tính độ tương đồng cosine
            cosine_sim = calculate_cosine_similarity(features, vietnamese_stopwords)
            # Tính sự khác biệt về giá và điểm trọng số
            weighted_scores = calculate_weighted_scores(cosine_sim, product, products)
            # Sắp xếp các sản phẩm theo điểm tương đồng (cả mô tả và giá)
            sorted_indices = weighted_scores.argsort()[-5:][::-1]
            products_list = list(products)
            related_products = [products_list[i] for i in sorted_indices]
            serializer = ProductSerializer(related_products, many=True)
            return Response(serializer.data)
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)
# Sản phẩm gợi ý
class RecommendProductsView(APIView):
    def get(self, request, user_id):
        try:
            user = User.objects.get(user_id=user_id)  # Kiểm tra xem user có tồn tại không
            recommended_products = recommend_products(user_id)  # Gọi hàm gợi ý sản phẩm
            return Response({'recommended_products': recommended_products}, status=200)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)
        except Exception as e:
            return Response({'error': f'Internal server error: {str(e)}'}, status=500)
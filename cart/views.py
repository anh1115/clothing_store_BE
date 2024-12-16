from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import Cart, CartDetail
from .serializers import CartSerializer, CartDetailSerializer, OrderLineSerializer
from django.db import transaction
from .models import Order, OrderLine
from products.models import Color, Product, Size, StockQuantity
from .serializers import OrderSerializer
from rest_framework.views import APIView
from uuid import uuid4

def get_user_cart(user):
    """
    Lấy giỏ hàng của người dùng, hoặc tạo mới nếu chưa tồn tại.
    """
    cart, created = Cart.objects.get_or_create(user=user)
    return cart


def get_cart_detail(cart, product_id, color_id, size_id):
    """
    Lấy chi tiết sản phẩm trong giỏ hàng.
    """
    try:
        return CartDetail.objects.get(cart=cart, product_id=product_id, color_id=color_id, size_id=size_id)
    except CartDetail.DoesNotExist:
        return None


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def view_cart(request):
    """
    Lấy thông tin giỏ hàng của người dùng hiện tại.
    """
    cart = get_user_cart(request.user)
    serializer = CartSerializer(cart)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_product_to_cart(request):
    """
    Thêm sản phẩm vào giỏ hàng.
    """
    product_id = request.data.get('product_id')
    color_id = request.data.get('color_id')
    size_id = request.data.get('size_id')
    quantity = int(request.data.get('quantity', 1))

    if not product_id:
        return Response({"detail": "Product ID is required."}, status=status.HTTP_400_BAD_REQUEST)

    if quantity <= 0:
        return Response({"detail": "Quantity must be greater than 0."}, status=status.HTTP_400_BAD_REQUEST)

    cart = get_user_cart(request.user)

    # Kiểm tra xem sản phẩm đã có trong giỏ hàng hay chưa
    cart_detail = get_cart_detail(cart, product_id, color_id, size_id)

    if cart_detail:
        cart_detail.quantity += quantity
        cart_detail.save()
    else:
        cart_detail = CartDetail.objects.create(
            cart=cart,
            product_id=product_id,
            color_id=color_id,
            size_id=size_id,
            quantity=quantity
        )

    serializer = CartDetailSerializer(cart_detail)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_product_in_cart(request):
    """
    Cập nhật số lượng sản phẩm trong giỏ hàng.
    """
    product_id = request.data.get('product_id')
    color_id = request.data.get('color_id')
    size_id = request.data.get('size_id')
    quantity = int(request.data.get('quantity', 1))

    # Kiểm tra thông tin yêu cầu
    if not product_id:
        return Response({"detail": "Product ID is required."}, status=status.HTTP_400_BAD_REQUEST)

    if quantity <= 0:
        return Response({"detail": "Quantity must be greater than 0."}, status=status.HTTP_400_BAD_REQUEST)

    # Lấy giỏ hàng của người dùng
    cart = get_user_cart(request.user)
    
    # Lấy chi tiết giỏ hàng
    cart_detail = get_cart_detail(cart, product_id, color_id, size_id)

    if not cart_detail:
        return Response({"detail": "Product not found in cart."}, status=status.HTTP_404_NOT_FOUND)

    # Cập nhật số lượng sản phẩm
    cart_detail.quantity = quantity
    cart_detail.save()

    # Lấy lại toàn bộ giỏ hàng mới sau khi cập nhật
    cart_details = CartDetail.objects.filter(cart=cart)
    
    # Serialize dữ liệu giỏ hàng mới
    serializer = CartDetailSerializer(cart_details, many=True)

    # Trả về toàn bộ giỏ hàng mới
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_product_from_cart(request):
    """
    Xóa sản phẩm khỏi giỏ hàng.
    """
    product_id = request.data.get('product_id')
    color_id = request.data.get('color_id')
    size_id = request.data.get('size_id')

    if not product_id:
        return Response({"detail": "Product ID is required."}, status=status.HTTP_400_BAD_REQUEST)

    # Lấy giỏ hàng của người dùng
    cart = get_user_cart(request.user)
    
    # Lấy chi tiết giỏ hàng cần xóa
    cart_detail = get_cart_detail(cart, product_id, color_id, size_id)

    if not cart_detail:
        return Response({"detail": "Không tìm thấy sản phẩm trong giỏ hàng."}, status=status.HTTP_404_NOT_FOUND)

    # Xóa sản phẩm khỏi giỏ hàng
    cart_detail.delete()

    # Lấy lại toàn bộ giỏ hàng mới sau khi xóa
    cart_details = CartDetail.objects.filter(cart=cart)
    
    # Serialize dữ liệu giỏ hàng mới
    serializer = CartDetailSerializer(cart_details, many=True)

    # Trả về toàn bộ giỏ hàng mới
    return Response(serializer.data, status=status.HTTP_200_OK)




class CreateOrderAPIView(APIView):
    """
    API để tạo đơn đặt hàng từ các sản phẩm đã chọn.
    """
    def post(self, request, *args, **kwargs):
        user = request.user
        selected_items = request.data.get('items', [])  # Danh sách sản phẩm chọn lọc cho đơn hàng

        # Thông tin giao hàng từ yêu cầu
        full_name = request.data.get('full_name')
        phone = request.data.get('phone')
        address = request.data.get('address')

        if not all([full_name, phone, address]):
            return Response({"error": "Missing user information: full_name, phone, or address."}, 
                            status=status.HTTP_400_BAD_REQUEST)

        if not selected_items:
            return Response({"error": "No products selected for the order."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Bắt đầu giao dịch
            with transaction.atomic():
                # Cập nhật thông tin người dùng trong bảng User
                user.full_name = full_name
                user.phone = phone
                user.address = address
                user.save()

                # Tạo đơn hàng với `uuid`
                order = Order.objects.create(
                    order_id=f"OD{str(uuid4())[:8].upper()}",  # Tạo mã đơn hàng duy nhất
                    user=user,
                    status="pending",  # Mặc định trạng thái đơn hàng là "pending"
                    total_price=0,  # Sẽ tính lại tổng giá sau
                    payment_method=request.data.get("payment_method", "cash_on_delivery"),
                )

                total_price = 0
                order_lines_data = []  # Lưu thông tin các dòng chi tiết đơn hàng
                errors = []  # Thu thập lỗi

                # Thêm các dòng chi tiết đơn hàng từ các sản phẩm chọn lựa
                for item in selected_items:
                    product_id = item.get('product_id')
                    color_id = item.get('color_id')
                    size_id = item.get('size_id')
                    quantity = item.get('quantity', 0)

                    # Không sử dụng các trường bổ sung để xác thực
                    product_name = item.get('product_name', '')  # Chỉ sử dụng cho hiển thị
                    color_name = item.get('color_name', '')  # Chỉ sử dụng cho hiển thị
                    size_name = item.get('size_name', '')  # Chỉ sử dụng cho hiển thị
                    product_sell_price = item.get('product_sell_price', '')
                    try:
                        product = Product.objects.get(product_id=product_id)
                        color = product.color.filter(color_id=color_id).first()
                        size = product.size.filter(size_id=size_id).first()

                        if not color or not size:
                            errors.append(f"Invalid color or size selected for product '{product.name}'.")
                            continue

                        stock = StockQuantity.objects.filter(product=product, color=color, size=size).first()

                        if not stock or stock.stock < quantity:
                            errors.append(
                                f"Not enough stock for product '{product.name}', color '{color.name}', size '{size.name}'."
                            )
                            continue

                        # Cập nhật tồn kho
                        stock.stock -= quantity
                        stock.save()

                        # Tính tổng tiền sản phẩm
                        subtotal = product.sell_price * quantity
                        total_price += subtotal

                        # Tạo chi tiết đơn hàng
                        order_line = OrderLine.objects.create(
                            order=order,
                            product=product,
                            color=color,
                            size=size,
                            quantity=quantity,
                            orderline_id=f"OL{str(uuid4())[:8].upper()}",
                        )

                        # Thêm dữ liệu dòng chi tiết vào danh sách
                        order_lines_data.append({
                            "product_id": product.product_id,
                            "product_name": product.name,
                            "sell_price": product.sell_price,
                            "quantity": quantity,
                            "color_id": color.color_id,
                            "color_name": color.name,
                            "size_id": size.size_id,
                            "size_name": size.name,
                            "first_image_url": item.get("first_image_url", ""),
                            "subtotal": subtotal
                        })
                    except Product.DoesNotExist:
                        errors.append(f"Invalid product selected with ID '{product_id}'.")

                # Nếu có lỗi, trả về tất cả lỗi
                if errors:
                    return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

                # Cập nhật lại tổng giá đơn hàng
                order.total_price = total_price
                order.save()

                # Chuẩn bị dữ liệu phản hồi
                response_data = {
                    "order": {
                        "order_id": order.order_id,
                        "total_price": order.total_price,
                        "status": order.status,
                        "payment_method": order.payment_method,
                    },
                    "order_lines": order_lines_data,
                    "user": {
                        "user_id": user.user_id,
                        "full_name": user.full_name,
                        "phone": user.phone,
                        "address": user.address,
                    }
                }

                return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class OrderListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        orders = Order.objects.filter(user=user).order_by('-created_at')
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class OrderDetailView(APIView):
    permission_classes = [IsAuthenticated] 

    def get(self, request):
        order_id = request.GET.get('order_id')  # Lấy tham số order_id từ query string

        if not order_id:
            return Response({'error': 'order_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Lọc đúng đơn hàng dựa trên order_id và user hiện tại
            order = Order.objects.get(order_id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

        order_serializer = OrderSerializer(order)
    
        return Response({
            'order': order_serializer.data,          # Thông tin đơn hàng
        }, status=status.HTTP_200_OK)

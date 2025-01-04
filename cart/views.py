
import json

import urllib
from products import vnpay
from products.vnpay import VNPay

from datetime import timezone
import hashlib
import hmac
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from shop_vivu import settings
from .models import Cart, CartDetail
from .serializers import CartSerializer, CartDetailSerializer, OrderLineSerializer
from django.db import transaction
from .models import Order, OrderLine
from products.models import Color, Product, Size, StockQuantity
from .serializers import OrderSerializer
from rest_framework.views import APIView
from uuid import uuid4
from django.db import transaction


def get_user_cart(user):
    """
    Lấy giỏ hàng của người dùng, hoặc tạo mới nếu chưa tồn tại.
    """
    cart, created = Cart.objects.get_or_create(user=user)
    return cart



def get_cart_detail(cart, product_id, color_id, size_id):
    """
    Lấy chi tiết sản phẩm trong giỏ hàng nếu đã tồn tại.
    """
    return CartDetail.objects.filter(
        cart=cart,
        product_id=product_id,
        color_id=color_id,
        size_id=size_id
    ).first()

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

    if not color_id or not size_id:
        return Response({"detail": "Color and size are required."}, status=status.HTTP_400_BAD_REQUEST)

    if quantity <= 0:
        return Response({"detail": "Quantity must be greater than 0."}, status=status.HTTP_400_BAD_REQUEST)

    # Lấy sản phẩm tồn kho theo màu sắc và kích thước
    try:
        stock_entry = StockQuantity.objects.get(product_id=product_id, color_id=color_id, size_id=size_id)
    except StockQuantity.DoesNotExist:
        return Response({"detail": "Stock for the specified product, color, and size does not exist."},
                        status=status.HTTP_404_NOT_FOUND)

    cart = get_user_cart(request.user)

    # Kiểm tra xem sản phẩm đã có trong giỏ hàng hay chưa
    cart_detail = get_cart_detail(cart, product_id, color_id, size_id)

    # Tính số lượng hiện có trong giỏ hàng và số lượng thêm mới
    current_quantity_in_cart = cart_detail.quantity if cart_detail else 0
    new_quantity = current_quantity_in_cart + quantity

    # Kiểm tra số lượng tồn kho
    if new_quantity > stock_entry.stock:
        return Response(
            {
                "detail": f"Cannot add {quantity} items to the cart. "
                          f"Only {stock_entry.stock - current_quantity_in_cart} items are available in stock."
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # Cập nhật hoặc thêm mới vào giỏ hàng
    if cart_detail:
        cart_detail.quantity = new_quantity
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
        selected_items = request.data.get('items', [])  # Danh sách sản phẩm chọn
        payment_method = request.data.get("payment_method", "cash_on_delivery")

        # Thông tin giao hàng
        full_name = request.data.get('full_name')
        phone = request.data.get('phone')
        address = request.data.get('address')

        if not all([full_name, phone, address]):
            return Response({"error": "Missing user information: full_name, phone, or address."}, 
                            status=status.HTTP_400_BAD_REQUEST)

        if not selected_items:
            return Response({"error": "No products selected for the order."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():  # Đảm bảo tính toàn vẹn dữ liệu
                # Cập nhật thông tin người dùng
                user.full_name = full_name
                user.phone = phone
                user.address = address
                user.save()

                # Tạo đơn hàng
                order = Order.objects.create(
                    order_id=f"OD{str(uuid4())[:8].upper()}",  # Tạo mã đơn hàng duy nhất
                    user=user,
                    status="pending",  # Trạng thái ban đầu là "pending"
                    total_price=0,
                    payment_method=payment_method,
                )

                total_price = 0
                order_lines_data = []  # Thông tin chi tiết từng dòng sản phẩm
                stock_updates = []  # Lưu trữ các cập nhật tồn kho để rollback nếu cần
                errors = []  # Thu thập lỗi nếu có

                # Duyệt qua từng sản phẩm được chọn
                for item in selected_items:
                    product_id = item.get('product_id')
                    color_id = item.get('color_id')
                    size_id = item.get('size_id')
                    quantity = item.get('quantity', 0)

                    try:
                        # Lấy thông tin sản phẩm, màu sắc và kích thước
                        product = Product.objects.get(product_id=product_id)
                        color = product.color.get(color_id=color_id)
                        size = product.size.get(size_id=size_id)
                        stock = StockQuantity.objects.get(product=product, color=color, size=size)

                        # Kiểm tra tồn kho
                        if stock.stock < quantity:
                            errors.append(
                                f"Not enough stock for product '{product.name}', color '{color.name}', size '{size.name}'."
                            )
                            continue

                        # Cập nhật tồn kho
                        stock.stock -= quantity
                        stock_updates.append((stock, quantity))  # Lưu thông tin để rollback nếu cần
                        stock.save()

                        # Tính tổng giá
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

                        # Lưu thông tin chi tiết
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

                    except (Product.DoesNotExist, Color.DoesNotExist, Size.DoesNotExist, StockQuantity.DoesNotExist):
                        errors.append(f"Invalid product, color, or size selected for product_id '{product_id}'.")
                        continue

                if errors:
                    raise Exception(", ".join(errors))

                # Cập nhật tổng giá trị đơn hàng
                order.total_price = total_price
                order.save()

                # Nếu thanh toán qua VNPAY
                if payment_method == "vnpay":
                    vnpay_url = self.initiate_vnpay_payment(order)

                    # Nếu không tạo được URL thanh toán, rollback tất cả thay đổi
                    if not vnpay_url:
                        for stock, qty in stock_updates:
                            stock.stock += qty  # Hoàn trả tồn kho
                            stock.save()
                        order.delete()  # Xóa đơn hàng
                        return Response({"error": "Failed to initiate VNPAY payment."}, status=status.HTTP_400_BAD_REQUEST)

                    return Response({"redirect_url": vnpay_url}, status=status.HTTP_302_FOUND)

                # Phản hồi khi đơn hàng thanh toán COD
                return Response({
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
                }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
class VnpayReturn(APIView):
    permission_classes = [IsAuthenticated]
    


    def post(self, request, *args, **kwargs):
        # Lấy dữ liệu từ request
        # data = request.data
        data = json.loads(request.body)
        if data is None:
            return Response({'RspCode': '99', 'Message': 'Invalid JSON data'}, status=400)

        
        try:
            order = Order.objects.get(order_id=data['vnp_TxnRef'])
        except Order.DoesNotExist:
            return Response({'RspCode': '01', 'Message': 'Order not found'}, status=404)
        if data:
            vnp = VNPay(data)
            vnp.responseData = data
            order_id = data['vnp_TxnRef']
            amount = data['vnp_Amount']
            order_desc = data['vnp_OrderInfo']
            vnp_TransactionNo = data['vnp_TransactionNo']
            vnp_ResponseCode = data['vnp_ResponseCode']
            vnp_TmnCode = data['vnp_TmnCode']
            vnp_PayDate = data['vnp_PayDate']
            vnp_BankCode = data['vnp_BankCode']
            vnp_CardType = data['vnp_CardType']
            if vnp.validate_response(settings.VNPAY_HASH_SECRET):
                firstTimeUpdate = True
                totalAmount = True
                if totalAmount:
                    if firstTimeUpdate:
                        if vnp_ResponseCode == '00':
                            print('Payment Success. Your code implement here')
                            order.vnp_BankCode = data.get("vnp_BankCode")
                            order.vnp_BankTranNo = data.get("vnp_BankTranNo")
                            order.vnp_CardType = data.get("vnp_CardType")
                            order.vnp_ResponseCode = data.get("vnp_ResponseCode")
                            order.vnp_TransactionNo = data.get("vnp_TransactionNo")
                            order.vnp_TransactionStatus = data.get("vnp_TransactionStatus")
                            order.payment_method = 'bank_transfer'
                            order.save()
                        else:
                            print('Payment Error. Your code implement here')
                            try:
                                with transaction.atomic():
                                    for item in order.order_lines.all():  
                                        product = item.product 
                                        size = item.size 
                                        color = item.color  
                    
                                    try:
                                        stock_quantity = StockQuantity.objects.get(product=product, size=size, color=color)
                                        stock_quantity.stock += item.quantity  
                                        stock_quantity.save()  
                                    except StockQuantity.DoesNotExist:
                                        return Response({"error": f"Stock not found for {product.name} - {size.name} - {color.name}"}, status=404)
                                    order.delete()

                                return Response({"message": "Transaction failed, order deleted, stock updated"}, status=200)
                            except Order.DoesNotExist:
                                return Response({"error": "Order not found"}, status=404)
                            except Exception as e:
                                return Response({"error": str(e)}, status=500)
                        result = Response({'RspCode': '00', 'Message': 'Confirm Success'})
                    else:
                        try:
                            with transaction.atomic():
                                for item in order.order_lines.all():  
                                    product = item.product  
                                    size = item.size  
                                    color = item.color  
                
                                try:
                                    stock_quantity = StockQuantity.objects.get(product=product, size=size, color=color)
                                    stock_quantity.stock += item.quantity  
                                    stock_quantity.save()  
                                except StockQuantity.DoesNotExist:
                                    return Response({"error": f"Stock not found for {product.name} - {size.name} - {color.name}"}, status=404)
                                order.delete()

                            return Response({"message": "Transaction failed, order deleted, stock updated"}, status=200)
                        except Order.DoesNotExist:
                            return Response({"error": "Order not found"}, status=404)
                        except Exception as e:
                            return Response({"error": str(e)}, status=500)
                        result = Response({'RspCode': '02', 'Message': 'Order Already Update'})
                else:
                    try:
                        with transaction.atomic():
                            for item in order.order_lines.all():  
                                product = item.product  
                                size = item.size  
                                color = item.color 
            
                            try:
                                stock_quantity = StockQuantity.objects.get(product=product, size=size, color=color)
                                stock_quantity.stock += item.quantity
                                stock_quantity.save()  
                            except StockQuantity.DoesNotExist:
                                return Response({"error": f"Stock not found for {product.name} - {size.name} - {color.name}"}, status=404)
                            order.delete()

                        return Response({"message": "Transaction failed, order deleted, stock updated"}, status=200)
                    except Order.DoesNotExist:
                        return Response({"error": "Order not found"}, status=404)
                    except Exception as e:
                        return Response({"error": str(e)}, status=500)
                    result = Response({'RspCode': '04', 'Message': 'invalid amount'})
            else:
                try:
                    with transaction.atomic():
                        for item in order.order_lines.all(): 
                            product = item.product  
                            size = item.size  
                            color = item.color  
        
                        try:
                            stock_quantity = StockQuantity.objects.get(product=product, size=size, color=color)
                            stock_quantity.stock += item.quantity  
                            stock_quantity.save()  
                        except StockQuantity.DoesNotExist:
                            return Response({"error": f"Stock not found for {product.name} - {size.name} - {color.name}"}, status=404)
                        order.delete()

                    return Response({"message": "Transaction failed, order deleted, stock updated"}, status=200)
                except Order.DoesNotExist:
                    return Response({"error": "Order not found"}, status=404)
                except Exception as e:
                    return Response({"error": str(e)}, status=500)
                result = Response({'RspCode': '97', 'Message': 'Invalid Signature'})
        else:
            result = Response({'RspCode': '99', 'Message': 'Invalid request'})
    
        return result
        

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
        order_id = request.GET.get('order_id')  

        if not order_id:
            return Response({'error': 'order_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            order = Order.objects.get(order_id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

        order_serializer = OrderSerializer(order)
    
        return Response({
            'order': order_serializer.data,         
        }, status=status.HTTP_200_OK)

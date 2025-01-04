from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import User
from .forms import UserRegistrationForm
from rest_framework.authtoken.models import Token

# Đăng ký tài khoản
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    form = UserRegistrationForm(data=request.data)
    if form.is_valid():
        user = form.save(commit=False)
        user_id_prefix = "KH"
        current_count = User.objects.count() + 1
        user.user_id = f"{user_id_prefix}{current_count:04d}"  # Tạo mã như KH0001, KH0002
        user.set_password(form.cleaned_data['password1'])  # Mã hóa mật khẩu
        user.save()
        return JsonResponse({"message": "Đăng ký tài khoản thành công"}, status=201)
    else:
        return JsonResponse({"errors": form.errors}, status=400)

# Đăng nhập người dùng
@api_view(['POST'])
@permission_classes([AllowAny])
def user_login(request):
    email = request.data.get('email')
    password = request.data.get('password')

    if not email or not password:
        return JsonResponse({'error': 'Vui lòng nhập đầy đủ email và mật khẩu'}, status=400)

    user = authenticate(request, email=email, password=password)
    if user is not None:
        if not user.is_active:
            return JsonResponse({'error': 'Tài khoản đã bị vô hiệu hóa'}, status=403)
        login(request, user)
        # Tạo hoặc lấy token cho user
        token, _ = Token.objects.get_or_create(user=user)
        return JsonResponse({'message': 'Đăng nhập thành công', 'user_id': user.user_id, 'user_name': user.full_name, 'token': token.key}, status=200)
    return JsonResponse({'error': 'Email hoặc mật khẩu không đúng'}, status=401)

# Đăng xuất người dùng
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_logout(request):
    logout(request)
    return JsonResponse({'message': 'Đăng xuất thành công'}, status=200)

# Lấy thông tin người dùng
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_detail(request):
    user = request.user
    user_data = {
        'user_id': user.user_id,
        'full_name': user.full_name,
        'email': user.email,
        'phone': user.phone,
        'gender': user.gender,
        'address': user.address,
        'role': user.role,
        'created_at': user.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    }
    return JsonResponse(user_data, status=200)

# Cập nhật thông tin người dùng
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_user(request):
    user = request.user
    data = request.data

    full_name = data.get('full_name')
    phone = data.get('phone')
    gender = data.get('gender')
    address = data.get('address')

    # Cập nhật từng trường nếu có dữ liệu mới
    if full_name:
        user.full_name = full_name
    if phone:
        user.phone = phone
    if gender:
        user.gender = gender
    if address:
        user.address = address

    user.save()
    return JsonResponse({'message': 'Thông tin người dùng đã được cập nhật'}, status=200)
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def change_password(request):
    user = request.user
    current_password = request.data.get('current_password')
    new_password = request.data.get('new_password')

    # Kiểm tra xem người dùng đã nhập đủ dữ liệu chưa
    if not current_password or not new_password:
        return JsonResponse({'error': 'Vui lòng nhập đủ mật khẩu hiện tại và mật khẩu mới'}, status=400)

    # Kiểm tra mật khẩu cũ có chính xác không
    if not user.check_password(current_password):
        return JsonResponse({'error': 'Mật khẩu hiện tại không chính xác'}, status=400)

    # Đặt mật khẩu mới và lưu thay đổi
    user.set_password(new_password)
    user.save()
    return JsonResponse({'message': 'Mật khẩu đã được thay đổi thành công'}, status=200)

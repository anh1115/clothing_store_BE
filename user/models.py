from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class CustomUserManager(BaseUserManager):
    def create_user(self, email, full_name, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)

        # Tự động tạo `user_id`
        max_id = self.model.objects.aggregate(models.Max('user_id'))['user_id__max']
        if max_id:
            # Lấy số từ mã cuối cùng và tăng lên 1
            num = int(max_id[2:]) + 1
        else:
            num = 1
        user_id = 'KH' + str(num).zfill(4)  # KH0001, KH0002, KH0003...

        user = self.model(user_id=user_id, email=email, full_name=full_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, full_name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(email=email, full_name=full_name, password=password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    GENDER_CHOICES = [
        ('Male', 'Nam'),
        ('Female', 'Nữ'),
        ('Other', 'Khác'),
    ]

    ROLE_CHOICES = [
        ('Customer', 'Khách hàng'),
        ('Admin', 'Quản lý'),
        ('Staff', 'Nhân viên'),
    ]

    user_id = models.CharField(
        max_length=10,
        primary_key=True,
        verbose_name="User ID",
        editable=False,  # Không cho phép chỉnh sửa trong admin
        unique=True
    )
    full_name = models.CharField(
        max_length=255,
        verbose_name="Họ và tên",
        null=False
    )
    email = models.EmailField(
        max_length=255,
        unique=True,
        verbose_name="Email",
        null=False
    )
    password = models.CharField(
        max_length=255,
        verbose_name="Mật khẩu",
        null=False
    )
    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES,
        default='Other',
        verbose_name="Giới tính",
        null=True
    )
    phone = models.CharField(
        max_length=15,
        unique=True,
        verbose_name="Số điện thoại",
        null=True
    )
    address = models.TextField(
        verbose_name="Địa chỉ",
        null=True
    )
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='Customer',
        verbose_name="Vai trò",
        null=False
    )
    is_active = models.BooleanField(default=True, verbose_name="Còn hoạt động")
    is_staff = models.BooleanField(default=False, verbose_name="Là nhân viên")
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Updated At"
    )

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']
    def save(self, *args, **kwargs):
        if not self.user_id:
            current_count = User.objects.count() + 1
            self.user_id = f"KH{current_count:04d}"
        super().save(*args, **kwargs)
    def __str__(self):
        return f"{self.user_id} - {self.full_name}"
    class Meta:
        verbose_name = "Quản lý người dùng"
        verbose_name_plural = "Quản lý người dùng"
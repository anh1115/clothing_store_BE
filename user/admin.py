from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.urls import path
from django.utils.translation import gettext_lazy as _
from .models import User


class UserAdmin(BaseUserAdmin):
    model = User
    list_display = ('user_id', 'full_name', 'email', 'phone', 'role', 'is_active', 'is_staff', 'created_at')
    list_filter = ('role', 'is_active', 'is_staff', 'gender')
    search_fields = ('user_id', 'full_name', 'email', 'phone')
    ordering = ('created_at',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('full_name', 'gender', 'phone', 'address')}),
        ('Permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'password1', 'password2', 'gender', 'phone', 'address', 'role'),
        }),
    )

    def save_model(self, request, obj, form, change):
        """
        Đảm bảo `user_id` được tạo trước khi lưu người dùng mới.
        """
        if not obj.user_id:
            current_count = User.objects.count() + 1
            obj.user_id = f"KH{current_count:04d}"
        super().save_model(request, obj, form, change)

    def get_urls(self):
        """
        Tùy chỉnh URL để sử dụng `user_id` thay vì `id` trong Admin.
        """
        urls = super().get_urls()
        custom_urls = [
            path(
                '<str:object_id>/change/',
                self.admin_site.admin_view(self.change_view),
                name='user_user_change',
            ),
        ]
        return custom_urls + urls

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """
        Ghi đè hàm `change_view` để xử lý bằng `user_id`.
        """
        obj = User.objects.filter(user_id=object_id).first()
        if not obj:
            # Nếu không tìm thấy, trả về lỗi
            from django.http import Http404
            raise Http404(f"User with ID {object_id} does not exist.")
        return super().change_view(request, str(obj.pk), form_url, extra_context)


# Đăng ký mô hình User với Admin
admin.site.register(User, UserAdmin)

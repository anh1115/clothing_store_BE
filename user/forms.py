from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Email")
    full_name = forms.CharField(max_length=255, required=True, label="Full Name")
    phone = forms.CharField(max_length=15, required=False, label="Phone Number")
    gender = forms.ChoiceField(
        choices=User.GENDER_CHOICES,
        required=False,
        label="Gender"
    )
    address = forms.CharField(
        widget=forms.Textarea,
        required=False,
        label="Address"
    )

    class Meta:
        model = User
        fields = ['full_name', 'email', 'password1', 'password2', 'phone', 'gender', 'address']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email đã được sử dụng. Vui lòng sử dụng email khác.")
        return email

    # Tự động tạo user_id trong quá trình đăng ký, không cần người dùng nhập vào.
    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
        return user


class UserLoginForm(forms.Form):
    email = forms.EmailField(required=True, label="Email")
    password = forms.CharField(widget=forms.PasswordInput, label="Password")

    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')

        if not User.objects.filter(email=email).exists():
            raise forms.ValidationError("Tài khoản với email này không tồn tại.")
        user = User.objects.filter(email=email).first()
        if user and not user.is_active:
            raise forms.ValidationError("Tài khoản này đã bị vô hiệu hóa.")
        if user and not user.check_password(password):
            raise forms.ValidationError("Mật khẩu không chính xác.")
        return self.cleaned_data


class UserUpdateForm(forms.ModelForm):
    phone = forms.CharField(max_length=15, required=False, label="Phone Number")
    gender = forms.ChoiceField(
        choices=User.GENDER_CHOICES,
        required=False,
        label="Gender"
    )
    address = forms.CharField(
        widget=forms.Textarea,
        required=False,
        label="Address"
    )

    class Meta:
        model = User
        fields = ['full_name', 'phone', 'gender', 'address']

    # Cập nhật user và xử lý các thay đổi của các trường.
    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
        return user

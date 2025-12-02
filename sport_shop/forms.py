from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import Order, UserProfile, Review, PaymentMethod, Product, Category, ProductVariant, ProductImage, Discount
from django.core.exceptions import ValidationError

class OrderForm(forms.ModelForm):
    """Форма оформления заказа."""
    
    class Meta:
        model = Order
        fields = ['full_name', 'address', 'payment_method']
        labels = {
            'full_name': 'Полное имя',
            'address': 'Адрес',
            'payment_method': 'Способ оплаты',
        }
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Показываем только активные методы оплаты
        self.fields['payment_method'].queryset = PaymentMethod.objects.filter(is_active=True)

class UserProfileForm(forms.ModelForm):
    email = forms.EmailField(required=False)

    class Meta:
        model = UserProfile
        fields = ['avatar']
        widgets = {
            'avatar': forms.FileInput(attrs={'style': 'display: none;', 'id': 'avatar-input'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.user:
            self.fields['email'].initial = self.instance.user.email

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = profile.user
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            profile.save()
        return profile

class SignUpForm(UserCreationForm):
    """Форма регистрации нового пользователя."""
    email = forms.EmailField(
        max_length=254,
        required=True,
        help_text='Обязательное поле. Введите действующий email адрес.'
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        self.fields['username'].widget.attrs.update({'placeholder': 'Имя пользователя'})
        self.fields['email'].widget.attrs.update({'placeholder': 'Email'})
        self.fields['password1'].widget.attrs.update({'placeholder': 'Пароль'})
        self.fields['password2'].widget.attrs.update({'placeholder': 'Подтверждение пароля'})

    def clean_email(self):
        """Проверка уникальности email."""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("Пользователь с таким email уже существует.")
        return email

    def clean_password1(self):
        """Дополнительная валидация пароля."""
        password1 = self.cleaned_data.get("password1")
        if password1 and password1.isdigit():
            raise ValidationError("Пароль не может состоять только из цифр.")
        return password1

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'text']
        widgets = {
            'rating': forms.Select(choices=[(i, i) for i in range(1, 6)]),
            'text': forms.Textarea(attrs={'rows': 4}),
        }

class UserNameForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username']

class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Имя пользователя'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Пароль'}))


# ============================================
# ФОРМЫ ДЛЯ ПАНЕЛИ УПРАВЛЕНИЯ
# ============================================

class ProductAdminForm(forms.ModelForm):
    """Форма для редактирования товара в панели управления."""
    
    # Объединенное поле для описания
    description_text = forms.CharField(
        label='Описание товара',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control rich-text-editor',
            'rows': 15,
            'id': 'description-editor'
        }),
        help_text='Используйте кнопки форматирования для оформления текста. Поддерживаются теги: <b>, <i>, <u>, <p>, <link>, <color>, <image>, <vid>'
    )
    
    class Meta:
        model = Product
        fields = ['name', 'category']
        labels = {
            'name': 'Название товара',
            'category': 'Категория',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # Если товар существует, объединяем description и formatted_description_text
            desc = self.instance.formatted_description_text or self.instance.description
            self.fields['description_text'].initial = desc
    
    def save(self, commit=True):
        product = super().save(commit=False)
        # Сохраняем в formatted_description_text
        product.formatted_description_text = self.cleaned_data.get('description_text', '')
        # Если formatted_description_text пусто, сохраняем в description
        if not product.formatted_description_text:
            product.description = self.cleaned_data.get('description_text', '')
        if commit:
            product.save()
        return product


class DiscountForm(forms.ModelForm):
    """Форма для создания/редактирования скидок."""
    
    class Meta:
        model = Discount
        fields = ['name', 'discount_type', 'product', 'category', 'discount_percent', 'discount_amount', 'is_active', 'start_date', 'end_date']
        labels = {
            'name': 'Название скидки',
            'discount_type': 'Тип скидки',
            'product': 'Товар',
            'category': 'Категория',
            'discount_percent': 'Процент скидки (%)',
            'discount_amount': 'Фиксированная сумма скидки (₽)',
            'is_active': 'Активна',
            'start_date': 'Дата начала',
            'end_date': 'Дата окончания',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'discount_type': forms.Select(attrs={'class': 'form-control', 'onchange': 'toggleDiscountFields()'}),
            'product': forms.Select(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'discount_percent': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'discount_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'start_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['product'].queryset = Product.objects.all()
        self.fields['category'].queryset = Category.objects.all()
        self.fields['product'].required = False
        self.fields['category'].required = False
        self.fields['product'].label = 'Товар (для скидки на товар)'
        self.fields['category'].label = 'Категория (для скидки на категорию)'

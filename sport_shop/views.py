from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib import messages
from django.db.models import Count, Q, Min, Avg, F, ExpressionWrapper, FloatField, Max
from django.db.models.functions import Coalesce
from .models import Product, Category, ProductVariant, Order, OrderItem, PaymentMethod, UserProfile, Review, Discount
from django.contrib.auth.models import User, Group
from .forms import UserProfileForm, OrderForm, SignUpForm, ReviewForm, UserNameForm
from django.views.decorators.http import require_http_methods
from decimal import Decimal
from yookassa import Configuration, Payment
import uuid
from django.conf import settings
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.views import LoginView
from .forms import LoginForm
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404
import re

def home(request):
    # Выбираем топ 50 товаров по количеству звезд и заказов
    popular_products = Product.objects.annotate(
        avg_rating=Coalesce(Avg('reviews__rating'), 0.0),
        order_count=Count('variants__orderitems'),
        popularity_score=ExpressionWrapper(
            F('avg_rating') * F('order_count'),
            output_field=FloatField()
        )
    ).order_by('-popularity_score')[:50]
    
    return render(request, 'nut_shop/home.html', {'products': popular_products})

def product_list(request):
    # Примечание: categories уже доступны через context_processors,
    # но загружаем их здесь для явного использования в шаблоне
    categories = Category.objects.all()
    query = request.GET.get('query')
    sort_by = request.GET.get('sort_by', 'name')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    min_rating = request.GET.get('min_rating')
    min_weight = request.GET.get('min_weight')
    max_weight = request.GET.get('max_weight')
    category_id = request.GET.get('category')
    current_category = None

    # Инициализируем products здесь
    products = Product.objects.all()

    if category_id:
        current_category = get_object_or_404(Category, id=category_id)
        products = products.filter(category=current_category)
    
    if query:
        # Проверяем, есть ли в запросе тег id
        id_match = re.match(r'id\((\d+)\)', query)
        if id_match:
            # Если есть, ищем продукт только по ID
            product_id = id_match.group(1)
            products = products.filter(id=product_id)
        else:
            # Если нет, используем обычный поиск
            products = products.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(category__name__icontains=query) |
                Q(variants__weight__icontains=query) |
                Q(variants__price__icontains=query)
            ).distinct()
    
    # Аннотации для сортировки и фильтрации
    products = products.annotate(
        min_price=Min('variants__price'),
        avg_rating=Avg('reviews__rating'),
        order_count=Count('variants__orderitems')
    )
    
    if min_price:
        products = products.filter(min_price__gte=min_price)
    if max_price:
        products = products.filter(min_price__lte=max_price)
    if min_rating:
        products = products.filter(avg_rating__gte=min_rating)
    if min_weight:
        products = products.filter(variants__weight__gte=min_weight)
    if max_weight:
        products = products.filter(variants__weight__lte=max_weight)
    
    # Сортировка
    if sort_by == 'name':
        products = products.order_by('name')
    elif sort_by == 'price_asc':
        products = products.order_by('min_price')
    elif sort_by == 'price_desc':
        products = products.order_by('-min_price')
    elif sort_by == 'popularity':
        products = products.order_by('-order_count', '-avg_rating')
    
    # Пагинация
    page = request.GET.get('page', 1)
    paginator = Paginator(products, 12)  # 12 продуктов на страницу
    try:
        products = paginator.page(page)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)
    
    # Получаем минимальные и максимальные значения цены и веса
    price_range = Product.objects.aggregate(min_price=Min('variants__price'), max_price=Max('variants__price'))
    weight_range = ProductVariant.objects.aggregate(min_weight=Min('weight'), max_weight=Max('weight'))

    min_price = request.GET.get('min_price', price_range['min_price'])
    max_price = request.GET.get('max_price', price_range['max_price'])
    min_weight = request.GET.get('min_weight', weight_range['min_weight'])
    max_weight = request.GET.get('max_weight', weight_range['max_weight'])

    context = {
        'products': products,
        'categories': categories,
        'query': query,
        'sort_by': sort_by,
        'min_price': min_price,
        'max_price': max_price,
        'min_rating': min_rating,
        'min_weight': min_weight,
        'max_weight': max_weight,
        'price_range': price_range,
        'weight_range': weight_range,
        'category_id': category_id,
        'current_category': current_category,  # Добавляем текущую категорию в контекст
    }
    return render(request, 'nut_shop/product_list.html', context)

def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    reviews = product.reviews.all().order_by('-created_at')
    user_can_review = False
    user_orders = []

    if request.user.is_authenticated:
        user_orders = Order.objects.filter(
            user=request.user, 
            status='delivered', 
            is_completed=True,
            items__product_variant__product=product
        ).distinct()
        user_can_review = user_orders.exists() and not Review.objects.filter(user=request.user, product=product).exists()

    # Получаем рекомендованные товары (максимум 15)
    recommended_products = Product.objects.filter(category=product.category).exclude(id=product.id)[:15]

    if request.method == 'POST' and user_can_review:
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user
            review.save()
            messages.success(request, 'Ваш отзыв успешно добавлен.')
            return redirect('product_detail', pk=pk)
    else:
        form = ReviewForm()

    context = {
        'product': product,
        'reviews': reviews,
        'form': form,
        'user_can_review': user_can_review,
        'user_orders': user_orders,
        'recommended_products': recommended_products,
    }
    return render(request, 'nut_shop/product_detail.html', context)

@login_required
def add_to_cart(request):
    if request.method == 'POST':
        variant_id = request.POST.get('variant_id')
        quantity = int(request.POST.get('quantity', 1))  # Получаем количество из формы
        variant = get_object_or_404(ProductVariant, id=variant_id)
        cart = request.session.get('cart', {})
        cart[variant_id] = cart.get(variant_id, 0) + quantity  # Добавляем выбранное количество
        request.session['cart'] = cart
        messages.success(request, f"{variant.product.name} ({variant.weight}г) - {quantity} шт. добавлено в корзину.")
    return redirect('product_list')

@login_required
def cart(request):
    cart = request.session.get('cart', {})
    
    if request.method == 'POST':
        variant_id = request.POST.get('remove_variant')
        if variant_id:
            del cart[variant_id]
            request.session['cart'] = cart
            messages.success(request, "Товар удален из корзины.")
            return redirect('cart')
    
    items = []
    total = 0
    for variant_id, quantity in cart.items():
        variant = get_object_or_404(ProductVariant, id=variant_id)
        item_total = variant.price * quantity
        items.append({
            'variant': variant,
            'quantity': quantity,
            'item_total': item_total
        })
        total += item_total
    return render(request, 'nut_shop/cart.html', {'items': items, 'total': total})

@login_required
def checkout(request):
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.user = request.user
            cart = request.session.get('cart', {})
            total_price = Decimal('0')
            
            for variant_id, quantity in cart.items():
                variant = get_object_or_404(ProductVariant, id=variant_id)
                total_price += variant.price * Decimal(quantity)
            
            order.total_price = total_price
            order.status = 'pending_payment'
            order.is_completed = False
            order.save()

            for variant_id, quantity in cart.items():
                variant = get_object_or_404(ProductVariant, id=variant_id)
                OrderItem.objects.create(
                    order=order,
                    product_variant=variant,
                    quantity=quantity,
                    price=variant.price
                )
            
            payment_method = order.payment_method
            if payment_method.name == "По реквизитам":
                return redirect('payment_by_requisites', order_id=order.id)
            elif payment_method.name == "ЮKassa":
                payment_url = create_payment(order, payment_method)
                if payment_url:
                    return redirect(payment_url)
                else:
                    messages.error(request, "Ошибка при создан��и платежа. Пожалуйста, попробуйте позже.")
                    return redirect('cart')
            
            else:
                # Для других методов оплаты
                request.session['cart'] = {}
                messages.success(request, "Заказ успешно оформлен.")
                return redirect('order_confirmation', order_id=order.id)
    else:
        form = OrderForm()
    
    cart = request.session.get('cart', {})
    total_price = Decimal('0')
    for variant_id, quantity in cart.items():
        variant = get_object_or_404(ProductVariant, id=variant_id)
        total_price += variant.price * Decimal(quantity)
    
    return render(request, 'nut_shop/checkout.html', {'form': form, 'total_price': total_price})


@login_required
def payment_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order.status = 'processing'
    order.save()
    request.session['cart'] = {}  # Очищаем корзину после успешной оплаты
    messages.success(request, "Оплата прошла успешно. Ваш заказ обрабатывается.")
    return render(request, 'nut_shop/payment_success.html', {'order': order})

@login_required
def order_confirmation(request, order_id):
    order = get_object_or_404(
        Order.objects.select_related('payment_method').prefetch_related('items__product_variant__product__images', 'items__product_variant__product__category'),
        id=order_id,
        user=request.user
    )
    return render(request, 'nut_shop/order_confirmation.html', {'order': order})

@login_required
def profile(request):
    try:
        user_profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        user_profile = UserProfile.objects.create(user=request.user)

    if request.method == 'POST':
        profile_form = UserProfileForm(request.POST, request.FILES, instance=user_profile)
        name_form = UserNameForm(request.POST, instance=request.user)
        if profile_form.is_valid() and name_form.is_valid():
            profile_form.save()
            name_form.save()
            messages.success(request, "Профиль успешно обновлен.")
            return redirect('profile')
    else:
        profile_form = UserProfileForm(instance=user_profile)
        name_form = UserNameForm(instance=request.user)

    return render(request, 'nut_shop/profile.html', {
        'profile_form': profile_form,
        'name_form': name_form,
        'user_profile': user_profile
    })

@login_required
def change_password(request):
    if request.method == 'POST':
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')
        
        if new_password1 != new_password2:
            return JsonResponse({'error': 'Пароли не совпадают.'}, status=400)
        
        if len(new_password1) < 8:
            return JsonResponse({'error': 'Пароль должен содержать не менее 8 символов.'}, status=400)
        
        try:
            validate_password(new_password1, request.user)
        except ValidationError as e:
            return JsonResponse({'error': ' '.join(e.messages)}, status=400)
        
        user = request.user
        user.set_password(new_password1)
        user.save()
        update_session_auth_hash(request, user)  # Важно, чтобы пользователь не вышел из системы
        return JsonResponse({'success': 'Ваш пароль был успешно изменен.'})
    return JsonResponse({'error': 'Неверный метод запроса.'}, status=400)

@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).select_related('payment_method').prefetch_related('items__product_variant__product__images').order_by('-created_at')
    return render(request, 'nut_shop/order_history.html', {'orders': orders})

def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')  # или куда вы хотите перенаправить после регистрации
    else:
        form = SignUpForm()
    return render(request, 'nut_shop/signup.html', {'form': form})

@require_http_methods(["GET", "POST"])
def logout_view(request):
    logout(request)
    return redirect('home')

@login_required
def payment_by_requisites(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if order.status != 'pending_payment':
        messages.error(request, "Этот заказ уже оплачен или отменен.")
        return redirect('order_history')
    return render(request, 'nut_shop/payment_by_requisites.html', {
        'order': order,
        'bank_account': order.payment_method.bank_account
    })


@login_required
def confirm_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if order.status == 'pending_payment':
        order.status = 'processing'
        order.save()
        messages.success(request, "Оплата подтверждена. Ваш заказ обрабатывается.")
    else:
        messages.error(request, "Невозможно подтвердить оплату для этого заказа.")
    return redirect('order_history')

def create_payment(order, payment_method):
    if not payment_method.shop_id or not payment_method.secret_key:
        print(f"Ошибка: отсутствует shop_id или secret_key для метода оплаты {payment_method.name}")
        return None

    Configuration.account_id = payment_method.shop_id
    Configuration.secret_key = payment_method.secret_key

    try:
        payment = Payment.create({
            "amount": {
                "value": str(order.total_price),
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": f"{settings.SITE_DOMAIN}/payment-success/{order.id}/"
            },
            "capture": True,
            "description": f"Оплата заказа №{order.id} в Орех Маркет",
            "metadata": {
                "order_id": order.id
            }
        }, uuid.uuid4())

        return payment.confirmation.confirmation_url
    except Exception as e:
        print(f"Ошибка при созданииии платежа: {e}")
        return None

@login_required
def add_review(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    if not Order.objects.filter(user=request.user, items__product_variant__product=product, is_completed=True).exists():
        messages.error(request, 'Вы можете оставить отзыв только поле покупки товара.')
        return redirect('product_detail', pk=product_id)

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user
            review.save()
            messages.success(request, 'Ваш отзыв успешно добавлен.')
            return redirect('product_detail', pk=product_id)
    else:
        form = ReviewForm()

    return render(request, 'nut_shop/add_review.html', {'form': form, 'product': product})

@login_required
def user_orders(request):
    orders = Order.objects.filter(user=request.user, status='delivered', is_completed=True)
    products_to_review = Product.objects.filter(
        variants__orderitem__order__in=orders
    ).exclude(
        reviews__user=request.user
    ).distinct()

    context = {
        'orders': orders,
        'products_to_review': products_to_review,
    }
    return render(request, 'nut_shop/user_orders.html', context)

class CustomLoginView(LoginView):
    form_class = LoginForm
    template_name = 'nut_shop/login.html'

# Панель управления доступна только для персонала
from django.http import Http404

def panel_access_required(view_func):
    """Декоратор для проверки доступа к панели управления."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise Http404("Страница не найдена")
        if not (request.user.is_superuser or request.user.is_staff):
            raise Http404("Страница не найдена")
        return view_func(request, *args, **kwargs)
    return wrapper


@panel_access_required
def panel_dashboard(request):
    """Главная страница панели управления."""
    from django.db.models import Count, Sum
    from datetime import datetime, timedelta
    
    # Статистика
    total_products = Product.objects.count()
    total_orders = Order.objects.count()
    total_users = User.objects.filter(is_staff=False).count()
    
    # Заказы за последние 7 дней
    week_ago = datetime.now() - timedelta(days=7)
    recent_orders = Order.objects.filter(created_at__gte=week_ago).count()
    recent_revenue = Order.objects.filter(
        created_at__gte=week_ago,
        status__in=['delivered', 'shipped']
    ).aggregate(Sum('total_price'))['total_price__sum'] or 0
    
    # Заказы по статусам
    orders_by_status = Order.objects.values('status').annotate(count=Count('id'))
    
    # Последние заказы
    latest_orders = Order.objects.select_related('user').order_by('-created_at')[:10]
    
    context = {
        'total_products': total_products,
        'total_orders': total_orders,
        'total_users': total_users,
        'recent_orders': recent_orders,
        'recent_revenue': recent_revenue,
        'orders_by_status': orders_by_status,
        'latest_orders': latest_orders,
    }
    return render(request, 'panel/dashboard.html', context)


# ============================================
# УПРАВЛЕНИЕ ТОВАРАМИ
# ============================================

@panel_access_required
def panel_products(request):
    """Список товаров."""
    products = Product.objects.select_related('category').prefetch_related('variants', 'images').all()
    
    # Поиск
    search_query = request.GET.get('search', '')
    if search_query:
        products = products.filter(Q(name__icontains=search_query) | Q(description__icontains=search_query))
    
    # Фильтр по категории
    category_filter = request.GET.get('category', '')
    if category_filter:
        products = products.filter(category_id=category_filter)
    
    # Пагинация
    paginator = Paginator(products, 20)
    page = request.GET.get('page', 1)
    try:
        products = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        products = paginator.page(1)
    
    categories = Category.objects.all()
    
    context = {
        'products': products,
        'categories': categories,
        'search_query': search_query,
        'category_filter': category_filter,
    }
    return render(request, 'panel/products/list.html', context)


@panel_access_required
def panel_product_edit(request, product_id=None):
    """Редактирование или создание товара."""
    from .forms import ProductAdminForm
    
    if product_id:
        product = get_object_or_404(Product, id=product_id)
    else:
        product = None
    
    if request.method == 'POST':
        form = ProductAdminForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            product = form.save()
            messages.success(request, 'Товар успешно сохранен.')
            return redirect('panel_products')
    else:
        form = ProductAdminForm(instance=product)
    
    context = {
        'form': form,
        'product': product,
    }
    return render(request, 'panel/products/edit.html', context)


@panel_access_required
def panel_product_delete(request, product_id):
    """Удаление товара."""
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Товар удален.')
        return redirect('panel_products')
    return render(request, 'panel/products/delete.html', {'product': product})


# ============================================
# УПРАВЛЕНИЕ КАТЕГОРИЯМИ
# ============================================

@panel_access_required
def panel_categories(request):
    """Список категорий."""
    categories = Category.objects.prefetch_related('products').all()
    
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            Category.objects.create(name=name)
            messages.success(request, 'Категория добавлена.')
            return redirect('panel_categories')
    
    context = {'categories': categories}
    return render(request, 'panel/categories/list.html', context)


@panel_access_required
def panel_category_delete(request, category_id):
    """Удаление категории."""
    category = get_object_or_404(Category, id=category_id)
    if request.method == 'POST':
        category.delete()
        messages.success(request, 'Категория удалена.')
        return redirect('panel_categories')
    return render(request, 'panel/categories/delete.html', {'category': category})


# ============================================
# УПРАВЛЕНИЕ СКИДКАМИ
# ============================================

@panel_access_required
def panel_discounts(request):
    """Список скидок."""
    discounts = Discount.objects.select_related('product', 'category').all()
    
    if request.method == 'POST':
        from .forms import DiscountForm
        form = DiscountForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Скидка добавлена.')
            return redirect('panel_discounts')
    else:
        from .forms import DiscountForm
        form = DiscountForm()
    
    context = {
        'discounts': discounts,
        'form': form,
    }
    return render(request, 'panel/discounts/list.html', context)


@panel_access_required
def panel_discount_edit(request, discount_id=None):
    """Редактирование скидки."""
    from .forms import DiscountForm
    
    if discount_id:
        discount = get_object_or_404(Discount, id=discount_id)
    else:
        discount = None
    
    if request.method == 'POST':
        form = DiscountForm(request.POST, instance=discount)
        if form.is_valid():
            form.save()
            messages.success(request, 'Скидка сохранена.')
            return redirect('panel_discounts')
    else:
        form = DiscountForm(instance=discount)
    
    context = {
        'form': form,
        'discount': discount,
    }
    return render(request, 'panel/discounts/edit.html', context)


@panel_access_required
def panel_discount_delete(request, discount_id):
    """Удаление скидки."""
    discount = get_object_or_404(Discount, id=discount_id)
    if request.method == 'POST':
        discount.delete()
        messages.success(request, 'Скидка удалена.')
        return redirect('panel_discounts')
    return render(request, 'panel/discounts/delete.html', {'discount': discount})


# ============================================
# УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ
# ============================================

@panel_access_required
def panel_users(request):
    """Список пользователей."""
    users = User.objects.all()
    
    # Поиск
    search_query = request.GET.get('search', '')
    if search_query:
        users = users.filter(Q(username__icontains=search_query) | Q(email__icontains=search_query))
    
    # Пагинация
    paginator = Paginator(users, 30)
    page = request.GET.get('page', 1)
    try:
        users = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        users = paginator.page(1)
    
    context = {
        'users': users,
        'search_query': search_query,
    }
    return render(request, 'panel/users/list.html', context)


@panel_access_required
def panel_user_edit(request, user_id):
    """Редактирование пользователя."""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        is_staff = request.POST.get('is_staff') == 'on'
        is_active = request.POST.get('is_active') == 'on'
        
        user.username = username
        user.email = email
        user.is_staff = is_staff
        user.is_active = is_active
        user.save()
        
        # Группы
        selected_groups = request.POST.getlist('groups')
        user.groups.clear()
        for group_id in selected_groups:
            group = Group.objects.get(id=group_id)
            user.groups.add(group)
        
        messages.success(request, 'Пользователь обновлен.')
        return redirect('panel_users')
    
    groups = Group.objects.all()
    context = {
        'user': user,
        'groups': groups,
    }
    return render(request, 'panel/users/edit.html', context)


# ============================================
# УПРАВЛЕНИЕ ЗАКАЗАМИ
# ============================================

@panel_access_required
def panel_orders(request):
    """Список заказов."""
    orders = Order.objects.select_related('user', 'payment_method').prefetch_related('items').order_by('-created_at')
    
    # Фильтры
    status_filter = request.GET.get('status', '')
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    # Поиск
    search_query = request.GET.get('search', '')
    if search_query:
        orders = orders.filter(
            Q(id__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(full_name__icontains=search_query)
        )
    
    # Пагинация
    paginator = Paginator(orders, 25)
    page = request.GET.get('page', 1)
    try:
        orders = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        orders = paginator.page(1)
    
    context = {
        'orders': orders,
        'status_filter': status_filter,
        'search_query': search_query,
        'status_choices': Order.STATUS_CHOICES,
    }
    return render(request, 'panel/orders/list.html', context)


@panel_access_required
def panel_order_detail(request, order_id):
    """Детали заказа."""
    order = get_object_or_404(Order.objects.select_related('user', 'payment_method').prefetch_related('items__product_variant__product'), id=order_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Order.STATUS_CHOICES):
            order.status = new_status
            order.save()
            messages.success(request, 'Статус заказа обновлен.')
            return redirect('panel_order_detail', order_id=order_id)
    
    context = {
        'order': order,
        'status_choices': Order.STATUS_CHOICES,
    }
    return render(request, 'panel/orders/detail.html', context)













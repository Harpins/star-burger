from django.contrib import admin
from django.shortcuts import reverse
from django.templatetags.static import static
from django.utils.html import format_html
from django.db.models import Sum, F

from .models import Product, ProductCategory, Restaurant, RestaurantMenuItem, Order, OrderItem

class OrderItemInline(admin.TabularInline): 
    model = OrderItem
    extra = 0  
    min_num = 1  
    readonly_fields = ['get_total_price'] 
    
    fields = ['product', 'quantity', 'get_total_price']
        
    def get_total_price(self, obj):
        return f"{obj.get_total_price()} руб."
    get_total_price.short_description = 'Стоимость позиции'
    
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'id', 
        'firstname', 
        'lastname', 
        'phonenumber', 
        'address',
        'created_at',
        'get_total_order_price',
        'get_items_count'
    ]
    
    list_filter = ['created_at']
    search_fields = ['firstname', 'lastname', 'phonenumber', 'address']
    readonly_fields = ['created_at', 'updated_at', 'get_total_order_price']
    
    inlines = [OrderItemInline]
    
    fieldsets = [
        ('Информация о клиенте', {
            'fields': [
                'firstname', 
                'lastname', 
                'phonenumber', 
                'address'
            ]
        }),
        ('Даты', {
            'fields': [
                'created_at', 
                'updated_at'
            ],
            'classes': ['collapse']
        }),
        ('Итоговая стоимость', {
            'fields': ['get_total_order_price']
        }),
    ]
    
    def get_total_order_price(self, obj):
        total = obj.items.aggregate(total=Sum(F('quantity') * F('product__price')))['total']
        return f"{total} руб." if total else "0 руб."
    get_total_order_price.short_description = 'Итоговая стоимость'
    
    
    def get_items_count(self, obj):
        """Количество позиций в заказе"""
        return obj.items.count()
    get_items_count.short_description = 'Кол-во позиций'
    
    def get_queryset(self, request):
        """Оптимизация запроса с prefetch_related"""
        return super().get_queryset(request).prefetch_related('items', 'items__product')

class RestaurantMenuItemInline(admin.TabularInline):
    model = RestaurantMenuItem
    extra = 0


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    search_fields = [
        'name',
        'address',
        'contact_phone',
    ]
    list_display = [
        'name',
        'address',
        'contact_phone',
    ]
    inlines = [
        RestaurantMenuItemInline
    ]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'get_image_list_preview',
        'name',
        'category',
        'price',
        'id'
    ]
    list_display_links = [
        'name',
    ]
    list_filter = [
        'category',
    ]
    search_fields = [
        # FIXME SQLite can not convert letter case for cyrillic words properly, so search will be buggy.
        # Migration to PostgreSQL is necessary
        'name',
        'category__name',
    ]

    inlines = [
        RestaurantMenuItemInline
    ]
    fieldsets = (
        ('Общее', {
            'fields': [
                'name',
                'category',
                'image',
                'get_image_preview',
                'price',
            ]
        }),
        ('Подробно', {
            'fields': [
                'special_status',
                'description',
            ],
            'classes': [
                'wide'
            ],
        }),
    )

    readonly_fields = [
        'get_image_preview',
        'id'
    ]

    class Media:
        css = {
            "all": (
                static("admin/foodcartapp.css")
            )
        }

    def get_image_preview(self, obj):
        if not obj.image:
            return 'выберите картинку'
        return format_html('<img src="{url}" style="max-height: 200px;"/>', url=obj.image.url)
    get_image_preview.short_description = 'превью'

    def get_image_list_preview(self, obj):
        if not obj.image or not obj.id:
            return 'нет картинки'
        edit_url = reverse('admin:foodcartapp_product_change', args=(obj.id,))
        return format_html('<a href="{edit_url}"><img src="{src}" style="max-height: 50px;"/></a>', edit_url=edit_url, src=obj.image.url)
    get_image_list_preview.short_description = 'превью'


@admin.register(ProductCategory)
class ProductAdmin(admin.ModelAdmin):
    pass


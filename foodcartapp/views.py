from django.db import transaction
from django.http import JsonResponse
from django.templatetags.static import static


from .models import Product, Order, OrderItem
import json

def banners_list_api(request):
    # FIXME move data to db?
    return JsonResponse([
        {
            'title': 'Burger',
            'src': static('burger.jpg'),
            'text': 'Tasty Burger at your door step',
        },
        {
            'title': 'Spices',
            'src': static('food.jpg'),
            'text': 'All Cuisines',
        },
        {
            'title': 'New York',
            'src': static('tasty.jpg'),
            'text': 'Food is incomplete without a tasty dessert',
        }
    ], safe=False, json_dumps_params={
        'ensure_ascii': False,
        'indent': 4,
    })


def product_list_api(request):
    products = Product.objects.select_related('category').available()

    dumped_products = []
    for product in products:
        dumped_product = {
            'id': product.id,
            'name': product.name,
            'price': product.price,
            'special_status': product.special_status,
            'description': product.description,
            'category': {
                'id': product.category.id,
                'name': product.category.name,
            } if product.category else None,
            'image': product.image.url,
            'restaurant': {
                'id': product.id,
                'name': product.name,
            }
        }
        dumped_products.append(dumped_product)
    return JsonResponse(dumped_products, safe=False, json_dumps_params={
        'ensure_ascii': False,
        'indent': 4,
    })


def register_order(request):
    try:
        frontend_data = json.loads(request.body.decode())
       
        order_data = {
            'products': frontend_data.get('products', []),
            'firstname': frontend_data.get('firstname', '').strip(),
            'lastname': frontend_data.get('lastname', '').strip(),
            'phonenumber': frontend_data.get('phonenumber', '').strip(),
            'address': frontend_data.get('address', '').strip(),
        }
        

        required_fields = ['firstname', 'lastname', 'phonenumber', 'address']
        missing_fields = [field for field in required_fields if not order_data[field]]
        
        if missing_fields:
            return JsonResponse({
                'error': f'Не заполнены обязательные поля: {", ".join(missing_fields)}'
            }, status=400)
        if not order_data['products']:
            return JsonResponse({
                'error': f'Корзина не должна быть пустой'
            }, status=400)
            
        with transaction.atomic():
            order = Order.objects.create(
                firstname=order_data['firstname'],
                lastname=order_data['lastname'],
                phonenumber=order_data['phonenumber'],
                address=order_data['address']
            )

            for product_data in order_data['products']:
                product_id = product_data.get('product')
                quantity = product_data.get('quantity', 1)
                try:
                    product = Product.objects.get(id=product_id)
                except Product.DoesNotExist:
                    return JsonResponse({
                        'error': f'Товар с ID {product_id} не найден'
                    }, status=400)

                if quantity < 1 or quantity > 100:
                    return JsonResponse({
                        'error': f'Количество товара {product.name} должно быть от 1 до 100'
                    }, status=400)

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity
                )
        return JsonResponse({
            'id': order.id,
            'status': 'success',
            'message': 'Заказ успешно создан',
            'order_details': {
                'customer': f"{order.firstname} {order.lastname}",
                'phone': str(order.phonenumber),
                'address': order.address,
                'total_items': order.items.count(),
                'total_cost': str(sum(item.get_total_price() for item in order.items.all()))
            }
        }, status=201)
    
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Неверный формат JSON'
        }, status=400)
    except Exception as err:
        return JsonResponse({
            'error': f'Внутренняя ошибка сервера: {str(err)}'
        }, status=500)  
          
    return JsonResponse(order_data)

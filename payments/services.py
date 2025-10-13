import uuid
from decimal import Decimal
from django.conf import settings
from yookassa import Configuration, Payment

def _yk_configure():
    # SDK конфигурируется глобально
    Configuration.account_id = settings.YOO_KASSA_SHOP_ID
    Configuration.secret_key = settings.YOO_KASSA_SECRET_KEY

def create_yk_payment(order, *, return_url: str):
    """
    Создаёт платеж в ЮKassa и возвращает payment object.
    """
    _yk_configure()

    amount = Decimal(order.total_price or 0).quantize(Decimal('0.01'))
    idempotence_key = str(uuid.uuid4())

    payment = Payment.create({
        "amount": {
            "value": str(amount),   # '123.45'
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": return_url
        },
        "capture": True,  # авто-капчер, без wait_for_capture
        "description": f"CulT — заказ #{order.id}",
        "metadata": {
            "order_id": order.id,
            "user_id": order.user_id,
        },
        # "test": settings.YOO_KASSA_IS_TEST  # для новых SDK не обязателен
    }, idempotence_key)

    return payment

def get_yk_payment(payment_id: str):
    _yk_configure()
    return Payment.find_one(payment_id)
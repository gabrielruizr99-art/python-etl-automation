from decimal import ROUND_HALF_UP, Decimal
from typing import Any


def transform_row(row: dict[str, str], source_file: str, source_hash: str) -> dict[str, Any]:
    """
    Transforma una fila validada en los tipos finales para la carga en BD.
    Aplica redondeo ROUND_HALF_UP a dos decimales y evita floats para cálculos.
    """
    quantity = int(row["quantity"])
    unit_price = Decimal(row["unit_price"])
    discount_pct = Decimal(row["discount_pct"])
    
    # Cálculos financieros precisos
    gross_amount = (Decimal(quantity) * unit_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    discount_amount = (gross_amount * discount_pct).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    net_amount = (gross_amount - discount_amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    return {
        "sale_id": row["sale_id"],
        "sale_date": row["sale_date"],
        "sale_time": row["sale_time"],
        "branch_id": row["branch_id"],
        "customer_id": row["customer_id"],
        "product_id": row["product_id"],
        "seller_id": row["seller_id"],
        "sales_channel": row["sales_channel"],
        "payment_method": row["payment_method"],
        "quantity": quantity,
        "unit_price": unit_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        "discount_pct": discount_pct.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        "gross_amount": gross_amount,
        "discount_amount": discount_amount,
        "net_amount": net_amount,
        "source_file": source_file,
        "source_hash": source_hash
    }


"""Financial reporting for bookstore super-users."""

from collections import Counter

from .data import book_by_id


def financial_report(orders: list[dict], users: list[dict]) -> dict:
    orders_by_day = Counter()
    book_sales = Counter()

    for order in orders:
        orders_by_day[order["placed"]] += 1
        book_sales.update(order.get("book_ids", []))

    top_books = []

    for book_id, quantity in book_sales.most_common(5):
        book = book_by_id(book_id)
        if book is not None:
            top_books.append({
                "title": book.title,
                "quantity": quantity,
            })

    return {
        "total_orders": len(orders),
        "total_sales": round(
            sum(o.get("total", 0.0) for o in orders), 2
        ),
        "total_discounts": round(
            sum(o.get("discount_amount", 0.0) for o in orders), 2
        ),
        "books_sold": sum(book_sales.values()),
        "orders_by_day": dict(sorted(orders_by_day.items())),
        "top_selling_books": top_books,
        "vip_customers": sum(u.get("role") == "VC" for u in users),
        "registered_customers": sum(u.get("role") == "RC" for u in users),
    }
"""
Shopify Service — Live Data Injection
Equivalent to: Shopify App (Railway) in AeroChat architecture

Step 3 of Real-Time Flow (from architecture doc):
"If customer asks 'Where is my order?', Backend makes real-time call
 through Shopify App → pulls status from Shopify API → merges with AI"

OAuth + API calls to pull product and order data.
"""

import httpx
from typing import Optional
from app.core.config import get_settings


class ShopifyService:
    """
    Handles Shopify OAuth and API calls for a tenant.
    Each tenant has their own Shopify store credentials.
    """

    def __init__(self):
        settings = get_settings()
        self.api_version = settings.shopify_api_version

    def _get_headers(self, access_token: str) -> dict:
        return {
            "X-Shopify-Access-Token": access_token,
            "Content-Type": "application/json"
        }

    def _base_url(self, shop_domain: str) -> str:
        domain = shop_domain.replace("https://", "").replace("http://", "").rstrip("/")
        return f"https://{domain}/admin/api/{self.api_version}"

    async def get_order_by_number(
        self,
        shop_domain: str,
        access_token: str,
        order_number: str
    ) -> Optional[dict]:
        """
        Fetch specific order details from Shopify.
        Called when customer asks about their order.
        """
        url = f"{self._base_url(shop_domain)}/orders.json"
        params = {"name": f"#{order_number}", "status": "any", "limit": 1}

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url,
                headers=self._get_headers(access_token),
                params=params,
                timeout=10.0
            )

            if resp.status_code != 200:
                return None

            data = resp.json()
            orders = data.get("orders", [])
            if not orders:
                return None

            order = orders[0]
            return self._format_order(order)

    async def get_product_info(
        self,
        shop_domain: str,
        access_token: str,
        query: str
    ) -> list[dict]:
        """
        Search for product information (inventory, price, details).
        """
        url = f"{self._base_url(shop_domain)}/products.json"
        params = {"title": query, "limit": 3, "fields": "id,title,variants,status,body_html"}

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url,
                headers=self._get_headers(access_token),
                params=params,
                timeout=10.0
            )

            if resp.status_code != 200:
                return []

            products = resp.json().get("products", [])
            return [self._format_product(p) for p in products]

    def _format_order(self, order: dict) -> dict:
        """Format Shopify order for LLM context injection."""
        fulfillments = order.get("fulfillments", [])
        tracking = None
        if fulfillments:
            tracking = fulfillments[0].get("tracking_number")
            tracking_url = fulfillments[0].get("tracking_url")
        else:
            tracking_url = None

        return {
            "order_number": order.get("name"),
            "status": order.get("financial_status"),
            "fulfillment_status": order.get("fulfillment_status") or "unfulfilled",
            "created_at": order.get("created_at", "")[:10],
            "total_price": f"{order.get('total_price', '0')} {order.get('currency', 'USD')}",
            "tracking_number": tracking,
            "tracking_url": tracking_url,
            "line_items": [
                {"name": item["name"], "quantity": item["quantity"]}
                for item in order.get("line_items", [])[:3]
            ]
        }

    def _format_product(self, product: dict) -> dict:
        """Format Shopify product for LLM context."""
        variants = product.get("variants", [])
        in_stock = any(v.get("inventory_quantity", 0) > 0 for v in variants)
        prices = [float(v.get("price", 0)) for v in variants if v.get("price")]

        return {
            "title": product.get("title"),
            "status": product.get("status"),
            "in_stock": in_stock,
            "price_range": f"{min(prices):.2f} - {max(prices):.2f}" if prices else "N/A",
            "variants": len(variants)
        }

    def format_order_for_llm(self, order_data: dict) -> str:
        """Convert order dict to readable string for LLM prompt."""
        if not order_data:
            return "Order not found."

        lines = [
            f"Order: {order_data['order_number']}",
            f"Status: {order_data['status']}",
            f"Fulfillment: {order_data['fulfillment_status']}",
            f"Ordered on: {order_data['created_at']}",
            f"Total: {order_data['total_price']}",
        ]

        if order_data.get("tracking_number"):
            lines.append(f"Tracking: {order_data['tracking_number']}")
        if order_data.get("tracking_url"):
            lines.append(f"Track link: {order_data['tracking_url']}")

        items = ", ".join(
            f"{i['name']} (x{i['quantity']})"
            for i in order_data.get("line_items", [])
        )
        if items:
            lines.append(f"Items: {items}")

        return "\n".join(lines)

    def extract_order_number(self, text: str) -> Optional[str]:
        """Extract order number from customer message."""
        import re
        patterns = [
            r'#(\d{4,})',
            r'order[:\s#]+(\d{4,})',
            r'\b(\d{4,6})\b'
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None


_shopify_service: Optional[ShopifyService] = None

def get_shopify_service() -> ShopifyService:
    global _shopify_service
    if _shopify_service is None:
        _shopify_service = ShopifyService()
    return _shopify_service

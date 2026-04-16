import httpx
import re
from typing import Optional, List, Dict
from ..core.config import get_settings

class ShopifyService:
    """
    Handles live data lookups for Shopify orders and products.
    """

    def __init__(self):
        # Default to a stable API version
        self.api_version = "2024-04"

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
        """Fetch status and tracking for a specific order."""
        url = f"{self._base_url(shop_domain)}/orders.json"
        params = {"name": f"#{order_number}", "status": "any", "limit": 1}

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    url,
                    headers=self._get_headers(access_token),
                    params=params,
                    timeout=10.0
                )
                if resp.status_code != 200:
                    return None

                orders = resp.json().get("orders", [])
                if not orders:
                    return None

                return self._format_order(orders[0])
            except Exception:
                return None

    async def get_product_info(
        self,
        shop_domain: str,
        access_token: str,
        query: str
    ) -> List[Dict]:
        """Search products for inventory and pricing context."""
        url = f"{self._base_url(shop_domain)}/products.json"
        params = {"title": query, "limit": 3}

        async with httpx.AsyncClient() as client:
            try:
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
            except Exception:
                return []

    def _format_order(self, order: dict) -> dict:
        fulfillments = order.get("fulfillments", [])
        tracking = fulfillments[0].get("tracking_number") if fulfillments else None
        
        return {
            "order_number": order.get("name"),
            "status": order.get("financial_status"),
            "fulfillment_status": order.get("fulfillment_status") or "unfulfilled",
            "total_price": f"{order.get('total_price')} {order.get('currency')}",
            "tracking_number": tracking,
            "items": [item["name"] for item in order.get("line_items", [])]
        }

    def _format_product(self, product: dict) -> dict:
        variants = product.get("variants", [])
        in_stock = any(v.get("inventory_quantity", 0) > 0 for v in variants)
        price = variants[0].get("price") if variants else "N/A"
        
        return {
            "title": product.get("title"),
            "in_stock": in_stock,
            "price": price
        }

    def format_order_for_llm(self, order: dict) -> str:
        if not order: return "Order not found."
        return (
            f"Order: {order['order_number']}\n"
            f"Status: {order['status']}\n"
            f"Fulfillment: {order['fulfillment_status']}\n"
            f"Tracking: {order.get('tracking_number', 'Not available')}"
        )

    def extract_order_number(self, text: str) -> Optional[str]:
        match = re.search(r'#(\d{4,})', text)
        return match.group(1) if match else None

_shopify_service: Optional[ShopifyService] = None

def get_shopify_service() -> ShopifyService:
    global _shopify_service
    if _shopify_service is None:
        _shopify_service = ShopifyService()
    return _shopify_service

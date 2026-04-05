"""Inventory tool - manage product inventory."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from agent.tools.base import BaseTool

STORAGE_PATH = "/tmp/whiteops_inventory.json"


class InventoryTool(BaseTool):
    name = "inventory"
    description = (
        "Manage product inventory: add items, remove items, update stock levels, "
        "list all items, get low-stock alerts, and search the inventory."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["add_item", "remove_item", "update_stock", "list_items", "low_stock_alert", "search"],
                "description": "Action to perform.",
            },
            "item_id": {
                "type": "string",
                "description": "Item ID.",
            },
            "name": {
                "type": "string",
                "description": "Item name.",
            },
            "sku": {
                "type": "string",
                "description": "Stock Keeping Unit code.",
            },
            "category": {
                "type": "string",
                "description": "Item category.",
            },
            "quantity": {
                "type": "integer",
                "description": "Quantity (for add/update).",
            },
            "unit_price": {
                "type": "number",
                "description": "Price per unit.",
            },
            "min_stock": {
                "type": "integer",
                "description": "Minimum stock level for alerts. Default: 10.",
            },
            "query": {
                "type": "string",
                "description": "Search query (for search action).",
            },
            "threshold": {
                "type": "integer",
                "description": "Stock threshold for low_stock_alert. Uses item's min_stock if not set.",
            },
        },
        "required": ["action"],
    }

    def _load(self) -> list[dict]:
        path = Path(STORAGE_PATH)
        if path.exists():
            return json.loads(path.read_text())
        return []

    def _save(self, items: list[dict]) -> None:
        Path(STORAGE_PATH).write_text(json.dumps(items, indent=2, ensure_ascii=False))

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs["action"]
        items = self._load()

        if action == "add_item":
            name = kwargs.get("name")
            if not name:
                return {"error": "name is required."}
            item = {
                "id": uuid4().hex[:8],
                "name": name,
                "sku": kwargs.get("sku", ""),
                "category": kwargs.get("category", ""),
                "quantity": kwargs.get("quantity", 0),
                "unit_price": kwargs.get("unit_price", 0),
                "min_stock": kwargs.get("min_stock", 10),
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
            items.append(item)
            self._save(items)
            return {"message": "Item added.", "item": item}

        elif action == "remove_item":
            item_id = kwargs.get("item_id")
            if not item_id:
                return {"error": "item_id is required."}
            for i, item in enumerate(items):
                if item["id"] == item_id:
                    removed = items.pop(i)
                    self._save(items)
                    return {"message": "Item removed.", "item": removed}
            return {"error": f"Item {item_id} not found."}

        elif action == "update_stock":
            item_id = kwargs.get("item_id")
            quantity = kwargs.get("quantity")
            if not item_id:
                return {"error": "item_id is required."}
            if quantity is None:
                return {"error": "quantity is required."}
            for item in items:
                if item["id"] == item_id:
                    item["quantity"] = quantity
                    if "unit_price" in kwargs:
                        item["unit_price"] = kwargs["unit_price"]
                    if "min_stock" in kwargs:
                        item["min_stock"] = kwargs["min_stock"]
                    item["updated_at"] = datetime.now().isoformat()
                    self._save(items)
                    return {"message": "Stock updated.", "item": item}
            return {"error": f"Item {item_id} not found."}

        elif action == "list_items":
            category = kwargs.get("category")
            if category:
                items = [i for i in items if i.get("category", "").lower() == category.lower()]
            total_value = sum(i["quantity"] * i.get("unit_price", 0) for i in items)
            return {
                "items": items,
                "count": len(items),
                "total_inventory_value": round(total_value, 2),
            }

        elif action == "low_stock_alert":
            threshold = kwargs.get("threshold")
            low_stock = []
            for item in items:
                item_threshold = threshold if threshold is not None else item.get("min_stock", 10)
                if item["quantity"] <= item_threshold:
                    low_stock.append({
                        **item,
                        "below_by": item_threshold - item["quantity"],
                    })
            low_stock.sort(key=lambda x: x["quantity"])
            return {"low_stock_items": low_stock, "count": len(low_stock)}

        elif action == "search":
            query = kwargs.get("query", "").lower()
            if not query:
                return {"error": "query is required."}
            results = [
                i for i in items
                if query in i.get("name", "").lower()
                or query in i.get("sku", "").lower()
                or query in i.get("category", "").lower()
            ]
            return {"results": results, "count": len(results)}

        return {"error": f"Unknown action: {action}"}

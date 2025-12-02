"""
Product Order API Router
Ürün sıralama yönetimi
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from pydantic import BaseModel

from app.core.database import get_session
from app.models import Product


class ProductOrderItem(BaseModel):
    id: str
    code: str
    name: str
    display_order: int


class ProductOrderUpdate(BaseModel):
    products: List[dict]  # [{"id": "...", "display_order": 1}, ...]


router = APIRouter()


@router.get("/")
async def list_products_ordered(
    session: Session = Depends(get_session)
):
    """Tüm ürünleri display_order'a göre listele"""
    stmt = select(Product).order_by(Product.display_order, Product.code)
    products = session.exec(stmt).all()
    
    return [
        {
            "id": str(p.id),
            "code": p.code,
            "name": p.name,
            "display_order": p.display_order
        }
        for p in products
    ]


@router.put("/")
async def update_product_order(
    data: ProductOrderUpdate,
    session: Session = Depends(get_session)
):
    """Ürün sıralamasını güncelle"""
    try:
        # Her ürünün display_order'ını güncelle
        for item in data.products:
            product_id = item.get("id")
            new_order = item.get("display_order")
            
            if not product_id or new_order is None:
                continue
            
            # UUID parse
            from uuid import UUID
            try:
                uuid_obj = UUID(product_id)
            except ValueError:
                continue
            
            product = session.get(Product, uuid_obj)
            if product:
                product.display_order = new_order
                session.add(product)
        
        session.commit()
        
        return {"success": True, "message": f"{len(data.products)} ürün sıralaması güncellendi"}
    
    except Exception as e:
        session.rollback()
        raise HTTPException(500, f"Güncelleme hatası: {str(e)}")


@router.post("/reset")
async def reset_product_order(
    session: Session = Depends(get_session)
):
    """Ürün sıralamasını varsayılan değerlere döndür"""
    
    # Varsayılan SKU sıralaması
    DEFAULT_ORDER = {
        'MLR100': 1,
        'MFTB': 2,
        'MLFTB': 3,
        'MLTBLUE': 4,
        'MLTGRAY': 5,
        'MLTONE': 6,
        'MLEDGE': 7,
        'MLEDBLUE': 8,
        'MLEDSLIMS': 9,
        'PL100': 10,
        'PLLONGRCB': 11,
        'PLRC': 12,
        'PLLRC': 13,
        'PLABS100': 14,
        'PLRSVRCB': 15,
        'PLMNRCB': 16,
        'LAB100RCB': 17,
        'LARKBRCB': 18,
        'CHNB100RCB': 19,
        'CHNAVYBRCB': 20,
        'CHMODENAVY': 21,
        'MUARCB': 22,
        'MUABLU': 23,
        'LM100RCB': 24,
        'LMRCB': 25,
        'MLROLL50': 26,
    }
    
    try:
        updated_count = 0
        
        for sku, order in DEFAULT_ORDER.items():
            stmt = select(Product).where(Product.code == sku)
            product = session.exec(stmt).first()
            
            if product:
                product.display_order = order
                session.add(product)
                updated_count += 1
        
        session.commit()
        
        return {
            "success": True,
            "message": f"{updated_count} ürün varsayılan sıralamaya döndürüldü"
        }
    
    except Exception as e:
        session.rollback()
        raise HTTPException(500, f"Reset hatası: {str(e)}")

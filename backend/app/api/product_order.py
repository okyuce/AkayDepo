"""
Product Order API Router
Ürün sıralama yönetimi (depo bazlı)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from uuid import UUID
from pydantic import BaseModel

from app.core.database import get_session
from app.api.auth import get_current_user
from app.models import Product, DepotProductOrder


class ProductOrderUpdate(BaseModel):
    products: List[dict]  # [{"id": "...", "display_order": 1}, ...]


router = APIRouter()


def get_depot_order_map(session: Session, depot_id) -> dict:
    """Depo bazlı ürün sıralama map'i döndürür. {product_id_str: display_order}"""
    if not depot_id:
        return {}
    try:
        stmt = select(DepotProductOrder).where(DepotProductOrder.depot_id == depot_id)
        entries = session.exec(stmt).all()
        return {str(e.product_id): e.display_order for e in entries}
    except Exception:
        return {}


@router.get("/")
async def list_products_ordered(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Tüm ürünleri sıralı listele (depo bazlı sıralama varsa onu kullan)"""
    depot_id = current_user.get("depot_id")

    # Global ürünleri al
    products = session.exec(select(Product)).all()

    # Depo bazlı sıralama map'i
    depot_order = get_depot_order_map(session, depot_id)

    result = []
    for p in products:
        order = depot_order.get(str(p.id), p.display_order)
        result.append({
            "id": str(p.id),
            "code": p.code,
            "name": p.name,
            "display_order": order
        })

    result.sort(key=lambda x: (x["display_order"], x["code"]))
    return result


@router.put("/")
async def update_product_order(
    data: ProductOrderUpdate,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Ürün sıralamasını güncelle (depo bazlı)"""
    depot_id = current_user.get("depot_id")

    try:
        for item in data.products:
            product_id_str = item.get("id")
            new_order = item.get("display_order")

            if not product_id_str or new_order is None:
                continue

            try:
                product_uuid = UUID(product_id_str)
            except ValueError:
                continue

            # Ürün var mı kontrol et
            product = session.get(Product, product_uuid)
            if not product:
                continue

            if depot_id:
                # Depo bazlı sıralama kaydet
                stmt = select(DepotProductOrder).where(
                    DepotProductOrder.depot_id == depot_id,
                    DepotProductOrder.product_id == product_uuid
                )
                existing = session.exec(stmt).first()

                if existing:
                    existing.display_order = new_order
                    session.add(existing)
                else:
                    entry = DepotProductOrder(
                        depot_id=depot_id,
                        product_id=product_uuid,
                        display_order=new_order
                    )
                    session.add(entry)
            else:
                # Superadmin: global sıralamayı güncelle
                product.display_order = new_order
                session.add(product)

        session.commit()

        return {"success": True, "message": f"{len(data.products)} ürün sıralaması güncellendi"}

    except Exception as e:
        session.rollback()
        raise HTTPException(500, f"Güncelleme hatası: {str(e)}")


@router.post("/reset")
async def reset_product_order(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Ürün sıralamasını varsayılan değerlere döndür (depo bazlı kaydı siler)"""
    depot_id = current_user.get("depot_id")

    DEFAULT_ORDER = {
        'MLR100': 1, 'MFTB': 2, 'MLFTB': 3, 'MLTBLUE': 4, 'MLTGRAY': 5,
        'MLTONE': 6, 'MLEDGE': 7, 'MLEDBLUE': 8, 'MLEDSLIMS': 9, 'PL100': 10,
        'PLLONGRCB': 11, 'PLRC': 12, 'PLLRC': 13, 'PLABS100': 14, 'PLRSVRCB': 15,
        'PLMNRCB': 16, 'LAB100RCB': 17, 'LARKBRCB': 18, 'CHNB100RCB': 19,
        'CHNAVYBRCB': 20, 'CHMODENAVY': 21, 'MUARCB': 22, 'MUABLU': 23,
        'LM100RCB': 24, 'LMRCB': 25, 'MLROLL50': 26,
    }

    try:
        if depot_id:
            # Depo bazlı sıralama kayıtlarını sil → global sıralamaya döner
            stmt = select(DepotProductOrder).where(DepotProductOrder.depot_id == depot_id)
            entries = session.exec(stmt).all()
            for entry in entries:
                session.delete(entry)
            session.commit()
            return {"success": True, "message": "Depo sıralaması silindi, global sıralama kullanılacak"}
        else:
            # Superadmin: global sıralamayı varsayılana döndür
            updated_count = 0
            for sku, order in DEFAULT_ORDER.items():
                stmt = select(Product).where(Product.code == sku)
                product = session.exec(stmt).first()
                if product:
                    product.display_order = order
                    session.add(product)
                    updated_count += 1
            session.commit()
            return {"success": True, "message": f"{updated_count} ürün varsayılan sıralamaya döndürüldü"}

    except Exception as e:
        session.rollback()
        raise HTTPException(500, f"Reset hatası: {str(e)}")

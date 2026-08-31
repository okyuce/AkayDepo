"""
Closing Check API Router
Gün sonu "kapanış" Excel'i ile sipariş kontrolü.

İki adım: önce /analyze (hiçbir şeyi değiştirmez, rapor üretir), kullanıcı
raporu görüp onaylarsa /{id}/apply (yalnızca iptalleri fişlere yansıtır).
"""
import hashlib
import json
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlmodel import Session, select

from app.core.cache import cache_delete_pattern
from app.core.database import get_session
from app.api.auth import get_current_user, require_depot
from app.models import ClosingCheck, Cycle
from app.services.closing_checker import ClosingChecker, ClosingCheckError
from app.services.excel_parser import ExcelParser, ExcelParseError

router = APIRouter()


def _require_admin(current_user: dict):
    if current_user.get("role") not in ("admin", "superadmin"):
        raise HTTPException(403, "Bu işlem sadece admin kullanıcılar için geçerlidir")


def _closing_error(e: ClosingCheckError):
    return HTTPException(400, {
        "message": e.message,
        "reasons": e.reasons,
        "needs_confirm": e.needs_confirm,
    })


@router.post("/analyze")
async def analyze_closing(
    file: UploadFile = File(...),
    force: bool = Form(False),
    depot_id: str = Depends(require_depot),
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Kapanış Excel'ini doğrula ve döngüyle karşılaştır. Hiçbir şeyi değiştirmez."""
    _require_admin(current_user)

    if not file.filename or not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(400, "Sadece Excel dosyaları desteklenir (.xlsx, .xls)")

    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()

    checker = ClosingChecker(session, depot_id)

    try:
        cycle = checker.resolve_active_cycle()
    except ClosingCheckError as e:
        raise _closing_error(e)

    # Aynı dosya bu döngüde daha önce UYGULANDIYSA tekrar işleme alma
    applied = session.exec(
        select(ClosingCheck).where(
            ClosingCheck.cycle_id == cycle.id,
            ClosingCheck.file_hash == file_hash,
            ClosingCheck.status == "applied",
        )
    ).first()
    if applied:
        raise HTTPException(400, {
            "message": "Bu dosya bu döngüde zaten uygulandı.",
            "reasons": [
                f"{applied.applied_at:%d.%m.%Y %H:%M} tarihinde "
                f"{applied.cancelled_count} fiş iptal edildi."
            ],
            "needs_confirm": False,
        })

    try:
        parser = ExcelParser(content)
        df = parser.validate_and_parse()
        report = checker.analyze(cycle, df, force=force)
    except ExcelParseError as e:
        raise HTTPException(400, {
            "message": "Excel okunamadı.", "reasons": [str(e)], "needs_confirm": False,
        })
    except ClosingCheckError as e:
        raise _closing_error(e)

    check = ClosingCheck(
        cycle_id=cycle.id,
        depot_id=UUID(str(depot_id)),
        filename=file.filename,
        file_size=len(content),
        file_hash=file_hash,
        status="analyzed",
        report_json=json.dumps(report, ensure_ascii=False),
        max_batch_at_analysis=report["cycle"]["batch_count"],
    )
    session.add(check)
    session.commit()
    session.refresh(check)

    return {
        "check_id": str(check.id),
        "filename": check.filename,
        "status": check.status,
        "uploaded_at": check.uploaded_at.isoformat(),
        **report,
    }


@router.post("/{check_id}/apply")
async def apply_closing(
    check_id: UUID,
    depot_id: str = Depends(require_depot),
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Analiz raporundaki iptalleri fişlere yansıt (yalnızca A vakası)."""
    _require_admin(current_user)

    check = session.exec(
        select(ClosingCheck).where(ClosingCheck.id == check_id).with_for_update()
    ).first()
    if not check:
        raise HTTPException(404, "Kontrol kaydı bulunamadı")
    if str(check.depot_id) != str(depot_id):
        raise HTTPException(403, "Bu kontrol başka bir depoya ait")

    checker = ClosingChecker(session, depot_id)
    try:
        result = checker.apply(check, current_user.get("username"))
    except ClosingCheckError as e:
        session.rollback()
        raise _closing_error(e)

    cache_delete_pattern(f"active_cycle:{depot_id}")

    return {"check_id": str(check.id), "status": check.status, **result}


@router.get("/history")
async def closing_history(
    limit: int = 20,
    depot_id: str = Depends(require_depot),
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Bu deponun kapanış kontrolü geçmişi."""
    _require_admin(current_user)

    items = session.exec(
        select(ClosingCheck)
        .where(ClosingCheck.depot_id == UUID(str(depot_id)))
        .order_by(ClosingCheck.uploaded_at.desc())
        .limit(limit)
    ).all()

    result = []
    for x in items:
        cycle = session.get(Cycle, x.cycle_id)
        summary = {}
        try:
            summary = json.loads(x.report_json or "{}").get("summary", {})
        except (ValueError, TypeError):
            pass
        result.append({
            "id": str(x.id),
            "filename": x.filename,
            "status": x.status,
            "uploaded_at": x.uploaded_at.isoformat(),
            "applied_at": x.applied_at.isoformat() if x.applied_at else None,
            "applied_by": x.applied_by,
            "cancelled_count": x.cancelled_count,
            "plan_date": str(cycle.plan_date) if cycle else None,
            "summary": summary,
        })
    return result


@router.get("/{check_id}")
async def get_closing_check(
    check_id: UUID,
    depot_id: str = Depends(require_depot),
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Kayıtlı bir kontrolün raporunu getir."""
    _require_admin(current_user)

    check = session.get(ClosingCheck, check_id)
    if not check:
        raise HTTPException(404, "Kontrol kaydı bulunamadı")
    if str(check.depot_id) != str(depot_id):
        raise HTTPException(403, "Bu kontrol başka bir depoya ait")

    try:
        report = json.loads(check.report_json or "{}")
    except (ValueError, TypeError):
        report = {}

    return {
        "check_id": str(check.id),
        "filename": check.filename,
        "status": check.status,
        "uploaded_at": check.uploaded_at.isoformat(),
        "applied_at": check.applied_at.isoformat() if check.applied_at else None,
        "cancelled_count": check.cancelled_count,
        **report,
    }

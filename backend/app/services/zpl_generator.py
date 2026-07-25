"""
ZPL Generator
Loadsheet'i Zebra termal yazıcı için ZPL string'ine çevirir.

Hedef yazıcılar: iMZ320, ZQ320 (203 DPI, 72mm = 576 dot genişlik).
PrintLabel.tsx layout'unu birebir takip eder (FIŞ-N, dealer, territory, ürün tablosu, TOPLAM).
"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlmodel import Session, select

from app.models import (
    Loadsheet, LoadsheetLine, Dealer, Product,
    StationAssignment, Territory, TerritoryInfo,
    Station, Cycle,
)


# 203 DPI Zebra mobil yazıcıları için ölçüler.
LABEL_WIDTH_DOTS = 576           # 72 mm
MARGIN_X = 18                    # sol/sağ boşluk
CONTENT_WIDTH = LABEL_WIDTH_DOTS - 2 * MARGIN_X  # 540

# Satır yükseklikleri (dot)
HEADER_LINE = 44
SUBHEADER_LINE = 34
SECTION_GAP = 8
TABLE_ROW = 32
TABLE_HEADER_HEIGHT = 36
FOOTER_HEIGHT = 50

# Ürün adı sütunu genişliği — KRT ve PKT için 70'er dot ayır.
COL_QTY_W = 70
COL_NAME_W = CONTENT_WIDTH - 2 * COL_QTY_W
COL_KRT_X = MARGIN_X + COL_NAME_W
COL_PKT_X = COL_KRT_X + COL_QTY_W


def _get_territory_display_name(session: Session, territory: Optional[Territory], depot_id: Optional[str]) -> str:
    """TerritoryInfo master'dan doğru isim — yoksa territory.name."""
    if not territory:
        return ""
    stmt = select(TerritoryInfo).where(TerritoryInfo.code == territory.code)
    if depot_id:
        stmt = stmt.where(TerritoryInfo.depot_id == depot_id)
    ti = session.exec(stmt).first()
    return ti.name if ti else territory.name


def _compute_dealer_local_seq(session: Session, loadsheet: Loadsheet) -> int:
    """Bu bayinin aynı cycle'daki fişleri arasında bu fişin sırası (FIŞ-N için).

    Frontend `LoadsheetListPage.tsx:642-646`'daki mantıkla aynı.
    """
    stmt = (
        select(Loadsheet)
        .where(
            Loadsheet.cycle_id == loadsheet.cycle_id,
            Loadsheet.dealer_id == loadsheet.dealer_id,
        )
        .order_by(Loadsheet.batch_number.asc())
    )
    all_for_dealer = session.exec(stmt).all()
    for idx, ls in enumerate(all_for_dealer):
        if ls.id == loadsheet.id:
            return idx + 1
    return 1


def _zpl_escape(text: str) -> str:
    """ZPL'in özel karakterlerini kaçır.

    ZPL parser'ında problemli olanlar: ^ (komut başı), ~ (komut başı), \\ (escape).
    ^FH komutu kullanmıyoruz çünkü ^CI28 (UTF-8) ile direkt yazıyoruz.
    """
    if text is None:
        return ""
    return (
        str(text)
        .replace("\\", "\\\\")
        .replace("^", " ")
        .replace("~", " ")
    )


def _line_for_text(
    x: int, y: int, text: str, font_height: int = 28, font_width: int = 0
) -> str:
    """Tek satır metin için ZPL parçası."""
    return f"^CF0,{font_height},{font_width}\n^FO{x},{y}^FD{_zpl_escape(text)}^FS\n"


def _right_aligned_text(
    right_x: int, y: int, text: str, font_height: int = 28, est_char_w: int = 16
) -> str:
    """Sayıları sağa hizala. ZPL'de native right-align yok — width tahmini ile sola öteliyoruz."""
    s = str(text) if text is not None else ""
    width = len(s) * est_char_w
    x = max(MARGIN_X, right_x - width)
    return f"^CF0,{font_height}\n^FO{x},{y}^FD{_zpl_escape(s)}^FS\n"


def _wrap_text(text: str, max_chars: int) -> List[str]:
    """Basit greedy word-wrap; ürün adları için."""
    text = text or ""
    if len(text) <= max_chars:
        return [text]
    words = text.split()
    if not words:
        return [text[:max_chars]]
    lines: List[str] = []
    current = ""
    for word in words:
        if not current:
            current = word
        elif len(current) + 1 + len(word) <= max_chars:
            current = f"{current} {word}"
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [text[:max_chars]]


def build_label_data(
    session: Session,
    loadsheet: Loadsheet,
    depot_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Loadsheet → PrintLabelData benzeri dict. ZPL üretirken kullanılır, test edilebilir."""
    dealer = session.get(Dealer, loadsheet.dealer_id)
    assignment = session.get(StationAssignment, loadsheet.assignment_id)
    territory = session.get(Territory, assignment.territory_id) if assignment else None
    station = session.get(Station, assignment.station_id) if assignment else None

    # Fiş tarihi — atamanın plan tarihi, yoksa döngünün plan tarihi.
    plan_date_val = assignment.plan_date if assignment else None
    if plan_date_val is None:
        cycle = session.get(Cycle, loadsheet.cycle_id)
        plan_date_val = cycle.plan_date if cycle else None
    plan_date_str = plan_date_val.strftime("%d.%m.%Y") if plan_date_val else ""

    # Lines — depot bazlı sıraya göre
    try:
        from app.api.product_order import get_depot_order_map
        depot_order = get_depot_order_map(session, depot_id)
    except Exception:
        depot_order = {}

    line_rows = session.exec(
        select(LoadsheetLine).where(LoadsheetLine.loadsheet_id == loadsheet.id)
    ).all()

    lines: List[Dict[str, Any]] = []
    total_carton = 0
    total_pack = 0
    for line in line_rows:
        product = session.get(Product, line.product_id)
        lines.append({
            "product_code": product.code if product else "",
            "product_name": product.name if product else "",
            "qty_carton": line.qty_carton,
            "qty_pack": line.qty_pack,
            "_order": depot_order.get(
                str(line.product_id),
                product.display_order if product else 999,
            ),
        })
        total_carton += line.qty_carton
        total_pack += line.qty_pack

    lines.sort(key=lambda x: (x["_order"], x["product_code"]))
    for line in lines:
        line.pop("_order", None)

    return {
        "loadsheet_no": _compute_dealer_local_seq(session, loadsheet),
        "station_name": station.name if station else "",
        "plan_date": plan_date_str,
        "route_order": dealer.route_order if dealer else 0,
        "package_number": loadsheet.package_number,
        "dealer_code": dealer.code if dealer else "",
        "dealer_name": dealer.name if dealer else "",
        "territory_code": territory.code if territory else "",
        "territory_name": _get_territory_display_name(session, territory, depot_id),
        "lines": lines,
        "total_carton": total_carton,
        "total_pack": total_pack,
    }


def build_zpl(data: Dict[str, Any]) -> str:
    """PrintLabelData benzeri dict'ten ZPL string üret.

    Yapı:
      ^XA ^CI28 ^PW576
      FIŞ-N (center, 40)
      package_number (center, 30)
      ---- ayraç ----
      dealer_name (40)
      dealer_code (26)
      territory_code - territory_name (24) [opsiyonel]
      ---- ayraç ----
      ÜRÜN | KRT | PKT (header 24)
      ürün satırları (26)
      ---- ayraç ----
      TOPLAM | krt | pkt (30)
      ^XZ
    """
    parts: List[str] = ["^XA", "^CI28", f"^PW{LABEL_WIDTH_DOTS}", "^LH0,0"]

    # Üst boşluk: yazıcı kafa↔kesim bıçağı ölü bölgesi (~12mm) yüzünden
    # içerik çok yukarıdan başlarsa fiş kesilince üst yazılar kayboluyor.
    y = 96

    # En üst satır: istasyon (sol) + tarih (sağ) — package number (T04-B03) puntosunda.
    station_name = data.get("station_name") or ""
    plan_date = data.get("plan_date") or ""
    if station_name or plan_date:
        if station_name:
            parts.append(f"^CF0,30\n^FO{MARGIN_X},{y}^FD{_zpl_escape(station_name)}^FS")
        if plan_date:
            parts.append(_right_aligned_text(
                LABEL_WIDTH_DOTS - MARGIN_X, y, plan_date,
                font_height=30, est_char_w=15,
            ))
        y += SUBHEADER_LINE

    # RUT (Rut Sırası) — en üstte büyük, şoför/yükleyici dağıtım sırasını uzaktan görsün.
    route_order = data.get("route_order") or 0
    if route_order:
        rut_text = f"RUT {route_order}"
        rut_w = len(rut_text) * 31
        rut_x = max(MARGIN_X, (LABEL_WIDTH_DOTS - rut_w) // 2)
        parts.append(f"^CF0,56\n^FO{rut_x},{y}^FD{_zpl_escape(rut_text)}^FS")
        y += 60

    # FIŞ-N başlık (center).
    fis_text = f"FIŞ-{data['loadsheet_no']}"
    fis_w = len(fis_text) * 22
    fis_x = max(MARGIN_X, (LABEL_WIDTH_DOTS - fis_w) // 2)
    parts.append(f"^CF0,40\n^FO{fis_x},{y}^FD{_zpl_escape(fis_text)}^FS")
    y += HEADER_LINE

    # Package number (center).
    pkg = data.get("package_number") or ""
    if pkg:
        pkg_w = len(pkg) * 18
        pkg_x = max(MARGIN_X, (LABEL_WIDTH_DOTS - pkg_w) // 2)
        parts.append(f"^CF0,30\n^FO{pkg_x},{y}^FD{_zpl_escape(pkg)}^FS")
        y += SUBHEADER_LINE

    # Üst ayraç çizgisi.
    y += 4
    parts.append(f"^FO{MARGIN_X},{y}^GB{CONTENT_WIDTH},3,3^FS")
    y += 12

    # Dealer name (büyük).
    dealer_name = data.get("dealer_name") or ""
    for wline in _wrap_text(dealer_name, 22):
        parts.append(f"^CF0,40\n^FO{MARGIN_X},{y}^FD{_zpl_escape(wline)}^FS")
        y += 42

    # Dealer code.
    dealer_code = data.get("dealer_code") or ""
    if dealer_code:
        parts.append(f"^CF0,26\n^FO{MARGIN_X},{y}^FD{_zpl_escape(dealer_code)}^FS")
        y += 30

    # Territory.
    terr_code = data.get("territory_code") or ""
    terr_name = data.get("territory_name") or ""
    territory_label = ""
    if terr_code and terr_name:
        territory_label = f"{terr_code} - {terr_name}"
    elif terr_code or terr_name:
        territory_label = terr_code or terr_name
    if territory_label:
        parts.append(f"^CF0,24\n^FO{MARGIN_X},{y}^FD{_zpl_escape(territory_label)}^FS")
        y += 28

    # Alt ayraç.
    y += 6
    parts.append(f"^FO{MARGIN_X},{y}^GB{CONTENT_WIDTH},3,3^FS")
    y += 12

    # Tablo başlığı.
    parts.append(f"^CF0,24\n^FO{MARGIN_X},{y}^FDÜRÜN^FS")
    parts.append(_right_aligned_text(COL_KRT_X + COL_QTY_W - 6, y, "KRT", font_height=24, est_char_w=14))
    parts.append(_right_aligned_text(COL_PKT_X + COL_QTY_W - 6, y, "PKT", font_height=24, est_char_w=14))
    y += TABLE_HEADER_HEIGHT

    # Başlık altı ince çizgi.
    parts.append(f"^FO{MARGIN_X},{y}^GB{CONTENT_WIDTH},1,1^FS")
    y += 6

    # Ürün satırları.
    lines = data.get("lines") or []
    for line in lines:
        name = line.get("product_name") or line.get("product_code") or ""
        wrapped = _wrap_text(name, 22)
        # İlk satırda miktarlar görünür; sonraki wrap satırları sadece isim devamı.
        for i, wline in enumerate(wrapped):
            parts.append(f"^CF0,26\n^FO{MARGIN_X},{y}^FD{_zpl_escape(wline)}^FS")
            if i == 0:
                qty_carton = line.get("qty_carton") or 0
                qty_pack = line.get("qty_pack") or 0
                if qty_carton:
                    parts.append(_right_aligned_text(
                        COL_KRT_X + COL_QTY_W - 6, y, str(qty_carton),
                        font_height=26, est_char_w=16,
                    ))
                if qty_pack:
                    parts.append(_right_aligned_text(
                        COL_PKT_X + COL_QTY_W - 6, y, str(qty_pack),
                        font_height=26, est_char_w=16,
                    ))
            y += 30
        y += 2
        # Satır altı ince ayraç.
        parts.append(f"^FO{MARGIN_X},{y}^GB{CONTENT_WIDTH},1,1^FS")
        y += 4

    # TOPLAM ayraç (kalın).
    y += 6
    parts.append(f"^FO{MARGIN_X},{y}^GB{CONTENT_WIDTH},3,3^FS")
    y += 12

    total_carton = data.get("total_carton") or 0
    total_pack = data.get("total_pack") or 0
    parts.append(f"^CF0,32\n^FO{MARGIN_X},{y}^FDTOPLAM^FS")
    parts.append(_right_aligned_text(
        COL_KRT_X + COL_QTY_W - 6, y, str(total_carton),
        font_height=32, est_char_w=20,
    ))
    if total_pack:
        parts.append(_right_aligned_text(
            COL_PKT_X + COL_QTY_W - 6, y, str(total_pack),
            font_height=32, est_char_w=20,
        ))
    y += FOOTER_HEIGHT

    # Alt boşluk (yazıcı şeritte kessin) — kafa↔kesim ölü bölgesi kadar feed,
    # böylece son satırlar da kesim bıçağının üstüne çıkar.
    y += 96

    # Etiket yüksekliği — toplam içeriği yerleştirecek kadar.
    label_length = max(y, 480)
    parts.insert(3, f"^LL{label_length}")

    parts.append("^XZ")
    return "\n".join(parts)


def generate_loadsheet_zpl(
    session: Session,
    loadsheet_id: UUID,
    depot_id: Optional[str] = None,
) -> str:
    """Verilen loadsheet için tam ZPL üret. None döndürmez — fiş yoksa KeyError."""
    loadsheet = session.get(Loadsheet, loadsheet_id)
    if not loadsheet:
        raise KeyError(f"Loadsheet bulunamadı: {loadsheet_id}")
    data = build_label_data(session, loadsheet, depot_id)
    return build_zpl(data)

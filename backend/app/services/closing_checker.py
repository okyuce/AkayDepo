"""
Closing Checker Service
Gün sonu "kapanış" Excel'i ile döngüdeki siparişleri karşılaştırır.

Neden gerekli: gün içinde gelen parçalı Excel'ler ARTIMLI — her dosya sadece
o ana kadarki yeni/değişmiş siparişleri taşır. Bayi siparişini revize ederse
yeni kodla gelir ve sistem yakalar; ama siparişi tamamen İPTAL ederse hiçbir
dosyada iz kalmaz ve fişi yüklemeye devam ederiz. Kapanış Excel'i günün
tamamını (her bayi için SON sürümü) içerdiği için, eksik kalan bayiler
iptal edilmiş siparişlerdir.

Karşılaştırma anahtarı BayiKodu'dur, SiparişKodu değil: kapanış her bayi
için yalnızca son revizyonu tuttuğundan, sipariş koduna göre bakmak eskimiş
revizyonları "iptal" sanır (26.11.2025 verisinde 6 yanlış pozitif).
"""
import json
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from uuid import UUID

import pandas as pd
from sqlmodel import Session, select

from app.models import (
    Cycle, Dealer, Depot, Loadsheet, LoadsheetLine, Order, OrderLine,
    Product, Station, StationAssignment, StationInventory, StockMovement,
    Territory, TerritoryInfo,
)


class ClosingCheckError(Exception):
    """Doğrulama hatası — kullanıcıya gerekçeleriyle gösterilir."""

    def __init__(self, message: str, reasons: Optional[List[str]] = None,
                 needs_confirm: bool = False):
        super().__init__(message)
        self.message = message
        self.reasons = reasons or []
        # True ise engel aşılabilir: kullanıcı açıkça onaylarsa devam edilir.
        self.needs_confirm = needs_confirm


def territory_key(code: str) -> str:
    """'TERR030702-Eski-Garaj' -> 'TERR030702'

    Bölge ADI zamanla değişiyor (aynı numara territory_info'da iki farklı
    adla duruyor: TERR030702-Eski-Garaj / -Kadınlarpazarı). Depo sahipliği
    bu yüzden tam string yerine numara kısmıyla eşleştirilir.
    """
    return str(code).strip().split('-', 1)[0].upper()


class ClosingChecker:
    """Kapanış Excel'i doğrulama, karşılaştırma ve iptal uygulama."""

    # Kapanışta bulunmayan bayi oranı bu eşiği aşarsa kullanıcıdan açık
    # onay istenir — yanlış dosya sessizce toplu iptale dönüşmesin.
    MISSING_RATIO_CONFIRM = 0.20

    def __init__(self, session: Session, depot_id: str):
        self.session = session
        self.depot_id = str(depot_id)

    # ------------------------------------------------------------------
    # Döngü seçimi
    # ------------------------------------------------------------------
    def resolve_active_cycle(self) -> Cycle:
        """Deponun tek aktif döngüsünü bul.

        Birden fazla aktif döngü varsa kontrol yapılamaz: kapanış bir
        döngüyü görüp diğerini görmez ve diğerinin fişlerini toptan
        "iptal" sanar.
        """
        cycles = self.session.exec(
            select(Cycle)
            .where(Cycle.status == "active", Cycle.depot_id == self.depot_id)
            .order_by(Cycle.imported_at.desc())
        ).all()

        if not cycles:
            raise ClosingCheckError(
                "Bu depoda aktif döngü yok.",
                ["Kapanış kontrolü için önce günün Excel'leri yüklenmiş ve planlanmış olmalı."]
            )
        if len(cycles) > 1:
            detay = ", ".join(f"Döngü-{c.cycle_no} ({c.plan_date})" for c in cycles)
            raise ClosingCheckError(
                "Bu depoda birden fazla aktif döngü var — kontrol yapılamaz.",
                [f"Aktif döngüler: {detay}",
                 "Kapanış tek bir döngüyle karşılaştırılabilir. Önce fazla döngüyü kapatın."]
            )
        return cycles[0]

    # ------------------------------------------------------------------
    # Analiz (hiçbir şeyi değiştirmez)
    # ------------------------------------------------------------------
    def analyze(self, cycle: Cycle, df: pd.DataFrame, force: bool = False) -> Dict:
        db = self._load_cycle_state(cycle)
        xl = self._load_excel_state(df)

        if not db["dealers"]:
            raise ClosingCheckError(
                "Aktif döngüde hiç sipariş yok.",
                ["Karşılaştırılacak veri bulunamadı."]
            )
        if not xl["dealers"]:
            raise ClosingCheckError(
                "Yüklenen Excel'de hiç sipariş satırı yok.",
                ["Dosya boş ya da beklenen kolonlar dolu değil."]
            )

        reasons: List[str] = []
        warnings: List[str] = []

        # --- D1: depo sahipliği (en kritik kontrol) ---------------------
        reasons += self._check_depot_ownership(xl)

        # --- D2: tarih uyumu -------------------------------------------
        reasons += self._check_dates(db, xl)

        # --- D3: kapsam (parçalı dosya kapanış diye yüklenmiş mi) -------
        cover_reasons, cover_warnings = self._check_coverage(db, xl)
        reasons += cover_reasons
        warnings += cover_warnings

        if reasons:
            raise ClosingCheckError(
                "Bu dosya kapanış kontrolü için kullanılamaz.", reasons
            )

        # --- Karşılaştırma: A / B / C / D -------------------------------
        result = self._compare(cycle, db, xl)

        # --- D4: eksik oranı çok yüksekse açık onay iste ----------------
        toplam = len(db["dealers"])
        eksik = len(result["cancelled"]) + len(result["already_cancelled"])
        oran = eksik / toplam if toplam else 0.0
        if oran > self.MISSING_RATIO_CONFIRM and not force:
            raise ClosingCheckError(
                f"Döngüdeki {toplam} bayinin {eksik} tanesi ({oran:.0%}) kapanışta yok.",
                [f"Bu oran normalden yüksek — yanlış ya da eksik dosya yüklenmiş olabilir.",
                 "Dosyanın günün tamamını kapsadığından eminseniz onaylayıp devam edin."],
                needs_confirm=True,
            )
        if oran > self.MISSING_RATIO_CONFIRM:
            warnings.append(
                f"Eksik bayi oranı yüksek (%{oran*100:.0f}) — kullanıcı onayıyla devam edildi."
            )

        report = {
            "cycle": {
                "id": str(cycle.id),
                "cycle_no": cycle.cycle_no,
                "plan_date": str(cycle.plan_date),
                "order_date": db["order_dates"][0].isoformat() if db["order_dates"] else None,
                "dealer_count": toplam,
                "batch_count": db["max_batch"],
            },
            "warnings": warnings,
            "summary": {
                "cycle_dealers": toplam,
                "closing_dealers": len(xl["dealers"]),
                "cancelled": len(result["cancelled"]),
                "already_cancelled": len(result["already_cancelled"]),
                "missing_orders": len(result["missing_orders"]),
                "missed_revisions": len(result["missed_revisions"]),
                "qty_diffs": len(result["qty_diffs"]),
                "matched": len(result["matched_dealers"]),
            },
            "cancelled": result["cancelled"],
            "already_cancelled": result["already_cancelled"],
            "missing_orders": result["missing_orders"],
            "missed_revisions": result["missed_revisions"],
            "qty_diffs": result["qty_diffs"],
        }
        report["message"] = self._build_message(report)
        return report

    # ------------------------------------------------------------------
    # Uygulama (yalnızca A vakası — iptaller)
    # ------------------------------------------------------------------
    def apply(self, check, username: Optional[str]) -> Dict:
        if check.status == "applied":
            return {
                "already_applied": True,
                "cancelled_count": check.cancelled_count,
                "message": "Bu kontrol daha önce uygulanmış.",
            }

        cycle = self.session.get(Cycle, check.cycle_id)
        if not cycle:
            raise ClosingCheckError("Döngü bulunamadı.")
        if str(cycle.depot_id) != self.depot_id or str(check.depot_id) != self.depot_id:
            raise ClosingCheckError("Bu kontrol başka bir depoya ait.")

        # Analizden sonra yeni Excel yüklendiyse rapor bayatlamıştır.
        current_max_batch = self._max_batch(cycle.id)
        if current_max_batch != check.max_batch_at_analysis:
            raise ClosingCheckError(
                "Analizden sonra yeni Excel yüklenmiş — rapor güncel değil.",
                [f"Analiz anındaki yükleme sayısı: {check.max_batch_at_analysis}, "
                 f"şu an: {current_max_batch}.",
                 "Kapanış dosyasını tekrar yükleyip yeniden analiz edin."]
            )

        report = json.loads(check.report_json or "{}")
        items = report.get("cancelled", [])

        sheets_by_dealer = self._loadsheets_by_dealer(cycle.id)

        cancelled, skipped = [], []
        for item in items:
            dealer_id = item.get("dealer_id")
            sheet_id = item.get("loadsheet_id")

            if not sheet_id:
                skipped.append({**item, "reason": "Bu bayi için üretilmiş fiş yok"})
                continue

            # Canlı fiş hâlâ analizdeki fiş mi? (araya planlama girmiş olabilir)
            live = self._live_sheet(sheets_by_dealer.get(UUID(dealer_id), []))
            if live is None or str(live.id) != sheet_id:
                skipped.append({**item, "reason": "Fiş durumu analizden sonra değişmiş"})
                continue

            sheet = self.session.exec(
                select(Loadsheet).where(Loadsheet.id == UUID(sheet_id)).with_for_update()
            ).first()
            if not sheet:
                skipped.append({**item, "reason": "Fiş bulunamadı"})
                continue
            # Kuşak-kemer: iptal etmeden önce fişin deposunu ve döngüsünü tekrar doğrula
            if str(sheet.cycle_id) != str(cycle.id) or (
                sheet.depot_id and str(sheet.depot_id) != self.depot_id
            ):
                skipped.append({**item, "reason": "Fiş bu döngüye/depoya ait değil"})
                continue
            if sheet.status == "cancelled":
                skipped.append({**item, "reason": "Fiş zaten iptal"})
                continue

            stock_returned = self._cancel_sheet(sheet)
            cancelled.append({**item, "stock_returned": stock_returned})

        check.status = "applied"
        check.applied_at = datetime.now()
        check.applied_by = username
        check.cancelled_count = len(cancelled)
        report["applied"] = {"cancelled": cancelled, "skipped": skipped}
        check.report_json = json.dumps(report, ensure_ascii=False)
        self.session.add(check)
        self.session.commit()

        return {
            "already_applied": False,
            "cancelled_count": len(cancelled),
            "skipped_count": len(skipped),
            "cancelled": cancelled,
            "skipped": skipped,
            "message": self._build_apply_message(cancelled, skipped),
        }

    # ------------------------------------------------------------------
    # Döngü tarafı veri
    # ------------------------------------------------------------------
    def _load_cycle_state(self, cycle: Cycle) -> Dict:
        rows = self.session.exec(
            select(Order, Dealer, Territory)
            .join(Dealer, Dealer.id == Order.dealer_id)
            .join(Territory, Territory.id == Order.territory_id)
            .where(Order.cycle_id == cycle.id)
        ).all()

        line_rows = self.session.exec(
            select(OrderLine.order_id, Product.code, OrderLine.qty_carton, OrderLine.qty_pack)
            .join(Product, Product.id == OrderLine.product_id)
            .join(Order, Order.id == OrderLine.order_id)
            .where(Order.cycle_id == cycle.id)
        ).all()

        lines_by_order: Dict[UUID, Dict[str, Tuple[int, int]]] = defaultdict(dict)
        for order_id, product_code, carton, pack in line_rows:
            if carton or pack:
                lines_by_order[order_id][str(product_code).strip().upper()] = (
                    int(carton), int(pack)
                )

        # Bayi başına CANLI sipariş = en büyük import_batch
        latest: Dict[str, Dict] = {}
        order_dates = set()
        delivery_dates = set()
        max_batch = 0
        for order, dealer, territory in rows:
            code = str(dealer.code).strip()
            order_dates.add(order.order_date.date())
            delivery_dates.add(order.delivery_date)
            max_batch = max(max_batch, order.import_batch)

            prev = latest.get(code)
            if prev is None or order.import_batch > prev["batch"] or (
                order.import_batch == prev["batch"] and order.order_date > prev["order_date"]
            ):
                latest[code] = {
                    "dealer_id": dealer.id,
                    "dealer_code": code,
                    "dealer_name": dealer.name,
                    "territory_code": territory.code,
                    "territory_no": territory.display_number,
                    "order_id": order.id,
                    "order_code": str(order.external_order_code).strip(),
                    "order_date": order.order_date,
                    "batch": order.import_batch,
                }

        for info in latest.values():
            info["lines"] = lines_by_order.get(info["order_id"], {})

        # Batch bazlı canlı bayi listesi — kapsam kontrolü için
        dealers_by_batch: Dict[int, set] = defaultdict(set)
        for code, info in latest.items():
            dealers_by_batch[info["batch"]].add(code)

        return {
            "dealers": latest,
            "dealers_by_batch": dealers_by_batch,
            "order_dates": sorted(order_dates),
            "delivery_dates": sorted(delivery_dates),
            "max_batch": max_batch,
        }

    # ------------------------------------------------------------------
    # Excel tarafı veri
    # ------------------------------------------------------------------
    def _load_excel_state(self, df: pd.DataFrame) -> Dict:
        dealers: Dict[str, Dict] = {}
        order_dates = set()
        delivery_dates = set()
        multi_order_dealers = set()

        for terr, dcode, dname, ocode, pcode, carton, pack, odate, ddate in zip(
            df['Territory'], df['BayiKodu'], df['BayiAdı'], df['SiparişKodu'],
            df['ÜrünKodu'], df['Karton'], df['Paket'],
            df['SiparişTarihi'], df['TeslimatTarihi'],
        ):
            dcode = str(dcode).strip()
            if not dcode or dcode.lower() == 'nan':
                continue

            if pd.notna(odate):
                order_dates.add(odate.date())
            if pd.notna(ddate):
                delivery_dates.add(ddate.date())

            info = dealers.get(dcode)
            if info is None:
                info = dealers[dcode] = {
                    "dealer_code": dcode,
                    "dealer_name": str(dname).strip(),
                    "territory_code": str(terr).strip(),
                    "order_code": str(ocode).strip(),
                    "order_date": odate,
                    "lines": {},
                }
            elif str(ocode).strip() != info["order_code"]:
                # Kapanışta bir bayinin iki sipariş kodu olmamalı; olursa
                # en yenisini alıp uyarı üretiyoruz.
                multi_order_dealers.add(dcode)
                if str(ocode).strip() > info["order_code"]:
                    info["order_code"] = str(ocode).strip()
                    info["order_date"] = odate

            key = str(pcode).strip().upper()
            c, p = int(carton or 0), int(pack or 0)
            if c or p:
                prev_c, prev_p = info["lines"].get(key, (0, 0))
                info["lines"][key] = (prev_c + c, prev_p + p)

        return {
            "dealers": dealers,
            "order_dates": sorted(order_dates),
            "delivery_dates": sorted(delivery_dates),
            "multi_order_dealers": sorted(multi_order_dealers),
            "territory_keys": {territory_key(i["territory_code"]) for i in dealers.values()},
        }

    # ------------------------------------------------------------------
    # Doğrulamalar
    # ------------------------------------------------------------------
    def _check_depot_ownership(self, xl: Dict) -> List[str]:
        """Dosya gerçekten BU depoya mı ait?

        13 depo aynı arayüzü kullanıyor ve dosya adları benziyor. Yanlış
        deponun kapanışı yüklenirse bu deponun TÜM bayileri "iptal" görünür.
        Konya (TERR0307xx) ile Seydişehir (TERR030717-19) aynı prefix'i
        paylaştığı için prefix eşleştirmesi yetmez; tam kod üyeliğine bakılır.
        """
        reasons: List[str] = []

        depot_names = {
            str(d.id): f"{d.code} ({d.name})"
            for d in self.session.exec(select(Depot)).all()
        }

        # Territory sahipliği — hem canlı territories hem master territory_info
        owner: Dict[str, set] = defaultdict(set)
        for code, dep in self.session.exec(select(Territory.code, Territory.depot_id)).all():
            if dep:
                owner[territory_key(code)].add(str(dep))
        for code, dep in self.session.exec(select(TerritoryInfo.code, TerritoryInfo.depot_id)).all():
            if dep:
                owner[territory_key(code)].add(str(dep))

        foreign_terr: Dict[str, set] = {}
        own_terr = 0
        for key in xl["territory_keys"]:
            owners = owner.get(key)
            if not owners:
                continue  # bilinmeyen/yeni bölge — engel değil
            if self.depot_id in owners:
                own_terr += 1
            else:
                foreign_terr[key] = owners

        if foreign_terr:
            isim = sorted({
                depot_names.get(d, d)
                for owners in foreign_terr.values() for d in owners
            })
            reasons.append(
                f"Dosyadaki {len(foreign_terr)} bölge başka depoya ait: "
                f"{', '.join(sorted(foreign_terr)[:5])}"
                f"{' …' if len(foreign_terr) > 5 else ''} → {', '.join(isim)}"
            )
        elif own_terr == 0:
            reasons.append(
                "Dosyadaki bölgelerin hiçbiri bu depoya tanımlı değil — "
                "yanlış deponun dosyası olabilir."
            )

        # Bayi sahipliği
        dealer_owner: Dict[str, str] = {}
        for code, dep in self.session.exec(select(Dealer.code, Dealer.depot_id)).all():
            if dep:
                dealer_owner[str(code).strip()] = str(dep)

        foreign_dealers = [
            c for c in xl["dealers"]
            if c in dealer_owner and dealer_owner[c] != self.depot_id
        ]
        if foreign_dealers:
            isim = sorted({depot_names.get(dealer_owner[c], "?") for c in foreign_dealers})
            reasons.append(
                f"Dosyadaki {len(foreign_dealers)} bayi başka depoya kayıtlı "
                f"(ör. {', '.join(foreign_dealers[:3])}) → {', '.join(isim)}"
            )

        return reasons

    def _check_dates(self, db: Dict, xl: Dict) -> List[str]:
        reasons: List[str] = []

        if len(xl["order_dates"]) > 1:
            gunler = ", ".join(d.strftime('%d.%m.%Y') for d in xl["order_dates"])
            reasons.append(f"Dosya birden fazla güne ait sipariş içeriyor: {gunler}")
        elif xl["order_dates"] and db["order_dates"]:
            xl_gun = xl["order_dates"][0]
            if xl_gun not in db["order_dates"]:
                db_gun = ", ".join(d.strftime('%d.%m.%Y') for d in db["order_dates"])
                reasons.append(
                    f"Dosyanın sipariş tarihi {xl_gun.strftime('%d.%m.%Y')}, "
                    f"aktif döngü ise {db_gun} tarihli."
                )

        if (len(xl["delivery_dates"]) == 1 and len(db["delivery_dates"]) == 1
                and xl["delivery_dates"][0] != db["delivery_dates"][0]):
            reasons.append(
                f"Teslimat tarihi uyuşmuyor: dosya "
                f"{xl['delivery_dates'][0].strftime('%d.%m.%Y')}, döngü "
                f"{db['delivery_dates'][0].strftime('%d.%m.%Y')}."
            )

        return reasons

    def _check_coverage(self, db: Dict, xl: Dict) -> Tuple[List[str], List[str]]:
        """Kapanış günün TAMAMINI kapsıyor mu?

        Operatör yanlışlıkla parçalı bir dosyayı (ör. 17-00.xlsx) kapanış
        diye yüklerse, o dosyada olmayan batch'lerin bayileri toptan
        "iptal" görünür. Bir batch'in HİÇBİR canlı bayisi kapanışta yoksa
        dosya günün tamamını kapsamıyor demektir.
        """
        reasons: List[str] = []
        warnings: List[str] = []
        xl_codes = set(xl["dealers"])

        bos_batchler = []
        for batch in sorted(db["dealers_by_batch"]):
            codes = db["dealers_by_batch"][batch]
            if codes and not (codes & xl_codes):
                bos_batchler.append(batch)

        if bos_batchler:
            reasons.append(
                f"Dosya günün tamamını kapsamıyor: "
                f"{', '.join(str(b) + '. yükleme' for b in bos_batchler)} "
                f"siparişlerinin hiçbiri dosyada yok."
            )

        if xl["multi_order_dealers"]:
            warnings.append(
                f"{len(xl['multi_order_dealers'])} bayinin kapanışta birden fazla "
                f"sipariş kodu var; en yenisi esas alındı."
            )

        return reasons, warnings

    # ------------------------------------------------------------------
    # Karşılaştırma
    # ------------------------------------------------------------------
    def _compare(self, cycle: Cycle, db: Dict, xl: Dict) -> Dict:
        sheets_by_dealer = self._loadsheets_by_dealer(cycle.id)

        db_codes = set(db["dealers"])
        xl_codes = set(xl["dealers"])

        cancelled, already_cancelled = [], []
        for code in sorted(db_codes - xl_codes):
            info = db["dealers"][code]
            sheets = sheets_by_dealer.get(info["dealer_id"], [])
            live = self._live_sheet(sheets)
            karton, paket = self._totals(info["lines"])

            item = {
                "dealer_code": code,
                "dealer_id": str(info["dealer_id"]),
                "dealer_name": info["dealer_name"],
                "territory_no": info["territory_no"],
                "territory_code": info["territory_code"],
                "order_code": info["order_code"],
                "order_time": info["order_date"].strftime('%H:%M'),
                "batch": info["batch"],
                "carton": karton,
                "pack": paket,
                "loadsheet_id": str(live.id) if live else None,
                "package_number": live.package_number if live else None,
                "loadsheet_status": live.status if live else None,
                "was_loaded": bool(live and live.status == "loaded"),
            }

            if live is None and any(s.cancelled_by_closing for s in sheets):
                item["note"] = "Daha önce kapanış kontrolüyle iptal edilmiş"
                already_cancelled.append(item)
            elif live is None and sheets:
                item["note"] = "Fişi zaten iptal durumda"
                already_cancelled.append(item)
            elif live is None:
                item["note"] = "Bu bayi için fiş üretilmemiş (Park bölgesi olabilir)"
                cancelled.append(item)
            else:
                cancelled.append(item)

        missing_orders = []
        for code in sorted(xl_codes - db_codes):
            info = xl["dealers"][code]
            karton, paket = self._totals(info["lines"])
            missing_orders.append({
                "dealer_code": code,
                "dealer_name": info["dealer_name"],
                "territory_code": info["territory_code"],
                "order_code": info["order_code"],
                "order_time": info["order_date"].strftime('%H:%M') if pd.notna(info["order_date"]) else "",
                "carton": karton,
                "pack": paket,
            })

        missed_revisions, qty_diffs, matched = [], [], []
        for code in sorted(db_codes & xl_codes):
            d, x = db["dealers"][code], xl["dealers"][code]
            base = {
                "dealer_code": code,
                "dealer_name": d["dealer_name"],
                "territory_no": d["territory_no"],
                "db_order_code": d["order_code"],
                "closing_order_code": x["order_code"],
            }
            if d["order_code"] != x["order_code"]:
                sheets = sheets_by_dealer.get(d["dealer_id"], [])
                live = self._live_sheet(sheets)
                missed_revisions.append({
                    **base,
                    "changes": self._line_changes(d["lines"], x["lines"]),
                    "package_number": live.package_number if live else None,
                    "loadsheet_status": live.status if live else None,
                })
            elif d["lines"] != x["lines"]:
                qty_diffs.append({
                    **base,
                    "changes": self._line_changes(d["lines"], x["lines"]),
                })
            else:
                matched.append(code)

        return {
            "cancelled": cancelled,
            "already_cancelled": already_cancelled,
            "missing_orders": missing_orders,
            "missed_revisions": missed_revisions,
            "qty_diffs": qty_diffs,
            "matched_dealers": matched,
        }

    @staticmethod
    def _totals(lines: Dict[str, Tuple[int, int]]) -> Tuple[int, int]:
        return (sum(c for c, _ in lines.values()), sum(p for _, p in lines.values()))

    @staticmethod
    def _line_changes(db_lines: Dict, xl_lines: Dict) -> List[Dict]:
        """Ürün bazlı fark listesi (paket eşdeğerine göre)."""
        changes = []
        for code in sorted(set(db_lines) | set(xl_lines)):
            oc, op = db_lines.get(code, (0, 0))
            nc, np_ = xl_lines.get(code, (0, 0))
            if (oc, op) == (nc, np_):
                continue
            diff_packs = (nc * 10 + np_) - (oc * 10 + op)
            sign = 1 if diff_packs > 0 else -1
            abs_packs = abs(diff_packs)
            changes.append({
                "product_code": code,
                "old_carton": oc, "old_pack": op,
                "new_carton": nc, "new_pack": np_,
                "diff_carton": (abs_packs // 10) * sign,
                "diff_pack": (abs_packs % 10) * sign,
            })
        return changes

    # ------------------------------------------------------------------
    # Fiş yardımcıları
    # ------------------------------------------------------------------
    def _loadsheets_by_dealer(self, cycle_id: UUID) -> Dict[UUID, List[Loadsheet]]:
        sheets: Dict[UUID, List[Loadsheet]] = defaultdict(list)
        for ls in self.session.exec(
            select(Loadsheet).where(Loadsheet.cycle_id == cycle_id)
        ).all():
            sheets[ls.dealer_id].append(ls)
        for lst in sheets.values():
            lst.sort(key=lambda s: s.batch_number, reverse=True)
        return sheets

    @staticmethod
    def _live_sheet(sheets: List[Loadsheet]) -> Optional[Loadsheet]:
        """İptal edilmemiş en yüksek batch'li fiş."""
        for s in sheets:
            if s.status != "cancelled":
                return s
        return None

    def _max_batch(self, cycle_id: UUID) -> int:
        batches = self.session.exec(
            select(Order.import_batch).where(Order.cycle_id == cycle_id)
        ).all()
        return max(batches) if batches else 0

    def _cancel_sheet(self, sheet: Loadsheet) -> bool:
        """Fişi iptal et; tamamlanmışsa stoku istasyona geri ekle.

        `loadsheet_generator._cancel_previous_loadsheet` ile aynı mantık,
        farkı: depot_id açıkça yazılır (çok depolu ortamda stok hareketi
        yanlış depoya düşmesin).
        """
        stock_returned = False
        was_completed = sheet.completed_at is not None or sheet.status == "loaded"

        if was_completed:
            assignment = self.session.get(StationAssignment, sheet.assignment_id)
            if assignment:
                lines = self.session.exec(
                    select(LoadsheetLine).where(LoadsheetLine.loadsheet_id == sheet.id)
                ).all()
                for line in lines:
                    inventory = self.session.exec(
                        select(StationInventory).where(
                            StationInventory.station_id == assignment.station_id,
                            StationInventory.product_id == line.product_id,
                        )
                    ).first()
                    if not inventory:
                        inventory = StationInventory(
                            station_id=assignment.station_id,
                            product_id=line.product_id,
                            quantity_carton=0,
                            quantity_pack=0,
                            depot_id=self.depot_id,
                        )
                        self.session.add(inventory)
                        self.session.flush()

                    before_carton = inventory.quantity_carton
                    before_pack = inventory.quantity_pack

                    total = inventory.quantity_carton * 10 + inventory.quantity_pack
                    total += line.qty_carton * 10 + line.qty_pack
                    inventory.quantity_carton = total // 10
                    inventory.quantity_pack = total % 10
                    inventory.updated_at = datetime.now()
                    self.session.add(inventory)

                    self.session.add(StockMovement(
                        station_id=assignment.station_id,
                        product_id=line.product_id,
                        loadsheet_id=sheet.id,
                        movement_type="closing_cancel",
                        quantity_carton=line.qty_carton,
                        quantity_pack=line.qty_pack,
                        before_carton=before_carton,
                        before_pack=before_pack,
                        after_carton=inventory.quantity_carton,
                        after_pack=inventory.quantity_pack,
                        note="Gün sonu kapanış kontrolü: sipariş iptal",
                        depot_id=self.depot_id,
                    ))
                    stock_returned = True

        sheet.status = "cancelled"
        sheet.cancelled_by_closing = True
        sheet.completed_at = None
        sheet.loaded_at = None
        self.session.add(sheet)
        return stock_returned

    # ------------------------------------------------------------------
    # Sonuç ibareleri
    # ------------------------------------------------------------------
    @staticmethod
    def _build_message(report: Dict) -> str:
        s = report["summary"]
        if not any([s["cancelled"], s["missing_orders"], s["missed_revisions"], s["qty_diffs"]]):
            if s["already_cancelled"]:
                return (f"✅ Kontrol tamam — kaçırılmış iptal yok. "
                        f"({s['already_cancelled']} sipariş daha önce iptal edilmişti, "
                        f"{s['matched']} bayi birebir tutuyor.)")
            return (f"✅ Kontrol tamam — {s['matched']} bayi birebir tutuyor, "
                    f"iptal edilen sipariş yok.")

        parts = []
        if s["cancelled"]:
            parts.append(f"{s['cancelled']} iptal edilmiş sipariş")
        if s["missed_revisions"]:
            parts.append(f"{s['missed_revisions']} kaçırılmış revizyon")
        if s["qty_diffs"]:
            parts.append(f"{s['qty_diffs']} miktar farkı")
        if s["missing_orders"]:
            parts.append(f"{s['missing_orders']} hiç yüklenmemiş sipariş")
        return "⚠️ " + ", ".join(parts) + " bulundu."

    @staticmethod
    def _build_apply_message(cancelled: List, skipped: List) -> str:
        if not cancelled and not skipped:
            return "✅ İptal edilecek sipariş yoktu — siparişler tam tutuyor."
        iade = sum(1 for c in cancelled if c.get("stock_returned"))
        msg = f"✅ {len(cancelled)} fiş iptal edildi"
        if iade:
            msg += f" ({iade} tanesi tamamlanmıştı, stoka iade edildi)"
        if skipped:
            msg += f"; {len(skipped)} kayıt atlandı"
        return msg + "."

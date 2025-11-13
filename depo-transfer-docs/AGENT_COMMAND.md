# AGENT_COMMAND.md

**Komut Satırı (Kod Ajanı için):**

Bu repodaki `.md` belgeler **kaynak sözleşmeler**. `WORKLIST.md`’deki fazları **sırayla** uygula.

- Önce **FAZ 0–1**: backend iskeleti + DB şeması (**DATA_MODEL.md**), Docker/Compose (**DEPLOYMENT.md**).
- **FAZ 2–3**: **PIPELINES.md**’e göre ISMS Excel ingest + revizyon diff + istasyon paylaştırma (**ALGO_STATIONS.md**).
- **FAZ 4–5**: **BACKEND_API_SPEC.md** API’leri ve **PRINT_TEMPLATES.md** ile fiş üret/yazdır; grid görünüm ve durum renkleri (**UI_SPEC.md**).
- **FAZ 6–7**: **TEST_PLAN.md**’i çalıştır; ardından dağıtım.

**Çalıştırılacak Komut:**
`agent run --spec ./WORKLIST.md --root . --strict`

# AkayDepo — Çalışma Günlüğü (WORKLOG)

> En yeni kayıt **en üstte**. Format: `tarih · ne yapıldı · kararlar · sıradaki adım`.
> Oturum başında SessionStart hook'u son kayıtları + hafıza indeksini otomatik yükler.

---

## 2026-06-09 — Kalıcı hafıza iskeleti kuruldu
- **Yapıldı:** Oturumlar-arası hafıza altyapısı eklendi — mevcut `CLAUDE.md`'nin (PMI ISMS proje bağlamı) sonuna "Kalıcı Hafıza & Oturum Kuralları" bölümü (içerik **dokunulmadan**), `WORKLOG.md`, `memory/`, `worklog-archive/` ve SessionStart hook'u. Mevcut `Bash(curl:*)` izni korundu.
- **Dokunulmadı:** `backend/akaydepo.db` (uygulama veritabanı).
- **Karar:** Hafıza dosyaları henüz commit edilmedi — istenince commit edilir.
- **Sıradaki adım:** Normal AkayDepo geliştirmesine devam.

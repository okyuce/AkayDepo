# TEST_PLAN

## Smoke
- [ ] Excel yüklenebiliyor mu?
- [ ] Zorunlu kolonlar var mı?
- [ ] 1 çalışan -> 1 istasyon plan çıkıyor mu?
- [ ] Fiş grid render oluyor mu?

## Fonksiyonel
- [ ] Greedy paylaştırma ile istasyon yükleri yakın mı?
- [ ] Revizyon fark fişine sadece artan kalemler düşüyor mu?
- [ ] C1..Ck sayımları doğru azalıyor mu?
- [ ] “Loaded” olduğunda kart yeşile dönüyor mu?
- [ ] Yazdırma tek fiş/tek sayfa, çoklu fiş grid önizleme

## Performans
- [ ] 100k satır içe aktarma < 60 sn (lokal)
- [ ] Fiş üretimi 10k dealer < 30 sn

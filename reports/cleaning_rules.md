# Temizleme kuralları

`scripts/03_clean.py` tarafından üretilir; elle düzenlemeyin. Kuralların kodu ve gerekçesi:
`scripts/utils/text_utils.py`. Kod dokümanlarına yalnızca R2 uygulanır.

Temizlenen doküman: 608. Toplam karakter: 7.428.646 -> 6.257.256.

| Kural | Ne yapar | Neden | Etkilenen doküman | Silinen karakter |
| --- | --- | --- | --- | --- |
| R1 | Unicode NFC; ligatürler (ﬁ ﬂ ﬀ ﬃ ﬄ) harflere açılır; NBSP boşluğa çevrilir; sıfır genişlikli boşluk, BOM ve yumuşak tire silinir | Aynı kelime farklı kodlarla yazılmasın. NFKC kullanılmaz: ² karakterini 2 yapar, O(n²) anlam değiştirir | 117 | 0 |
| R2 | Kontrol karakterleri silinir (\n \t \f hariç); CRLF ve CR -> LF; çözülemeyen glif işaretleri (U+FFFD, U+FFFF) silinir | Bozuk baytlar ve PDF'te karşılığı bulunamayan glifler bilgi taşımaz; tahminle harfe çevrilmez | 6 | 466 |
| R3 | Sayfalı dokümanda (PDF) sayfanın ilk/son dolu satırlarındaki sayı, dokümanın sayfa numaralamasına uyuyorsa (sayı - sayfa sırası = dokümanda en sık görülen fark) silinir | Sayfa numarası kalıntısı. Numaralamaya uymayan sayılar içeriktir: sayfa sonuna denk gelen dizi elemanı ('9 7 7 2 ... 6 9' dizisinin son 9'u), şekil etiketi. Gövdedeki sayılara hiç bakılmaz | 24 | 1.626 |
| R4 | Sayfanın ilk/son dolu satırlarında, normalize edilince (rakam -> #, küçük harf, tek boşluk) en az repeated_line_min_pages farklı sayfada tekrar eden satırlar silinir; sonra sayfalar birleştirilir | Sayfa başlığı ve alt bilgisi. Yalnızca sayfa kenarı: gövdede tekrar eden satırlar sözde kod ('mark v') ve formül parçasıdır ('∑') | 24 | 13.586 |
| R5 | config.clean.boilerplate_lines ile tam eşleşen satırlar silinir | Site menüsü ve navigasyon | 12 | 105 |
| R8 | Vikipedi'de sondaki kaynakça bölümleri (References, See also, Kaynakça, Dış bağlantılar ...) silinir; kesim noktasından sonra düzyazı paragraf varsa o noktadan kesilmez. Ayrıca kesilmeyen yerlerde kalan dipnot girdileri (Vikipedi'nin geri bağlantı işareti '↑' ile başlayan satırlar) silinir | Bilgi taşımayan kaynak ve bağlantı listeleri. Düzyazı denetimi: bazı maddelerde kaynakça başlığından sonra içerik bölümü geliyor (Segment tree: Notes, sonra History). '↑' corpus'ta yalnızca dipnot girdilerinin başında geçiyor (363 satırın 363'ü), içerikte kullanılmıyor | 442 | 1.147.362 |
| R9 | Sayfalı dokümanda (PDF) art arda gelen kısa satırlar (en çok short_line_max_chars karakter, kod değil; en az short_line_run_min satır) boşlukla tek satırda birleştirilir. Harf ya da sembol silinmez; yalnızca satır başı/sonu boşlukları gider | PDF çıkarımı aralıklı dizilmiş şekil hücrelerini ve parçalı formülleri her hücre bir satır olacak şekilde veriyor (mergesort şeklindeki 'S O R T ...' harflerinin her biri ayrı satırda). HTML'de uygulanmaz: orada kısa satırlar ASCII çizimdir (ağaç şekli) | 24 | 27 |
| R6 | Satır sonu tiresi birleştirilir (sonraki satır küçük harfle başlıyorsa). Kelimenin tireli hâli corpus'ta tiresizinden sık geçiyorsa tire korunur | PDF satır kırılması. Tire koruma: 'B-|tree', 'two-|dimensional' yalın kuralla 'Btree' olurdu | 24 | 1.251 |
| R7 | Kod olmayan satırlarda ardışık boşluk/tab tek boşluğa iner, satır sonu boşlukları silinir (satır başı girintisi korunur); 3+ boş satır 2'ye iner | PDF sütun hizalamasından kalan boşluklar. Girinti iç içe liste ve sözde kod yapısını taşır | 502 | 4.871 |

Silinen karakter nettir: R1'de ligatür açılması metni uzatabilir (eksi değer).

## Kaynak bazında

| Kaynak | Doküman | Önce | Sonra | Silinen pay |
| --- | --- | --- | --- | --- |
| erickson_algorithms | 10 | 682.536 | 674.425 | %1,2 |
| open_data_structures | 14 | 404.798 | 394.219 | %2,6 |
| open_guide_dsa | 11 | 347.852 | 347.863 | %-0,0 |
| thealgorithms_python | 100 | 389.745 | 389.291 | %0,1 |
| vikipedi_tr | 68 | 216.923 | 182.570 | %15,8 |
| wikipedia_en | 405 | 5.386.792 | 4.268.888 | %20,8 |

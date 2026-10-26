# Kalite kontrol raporu

`python -m scripts.13_qc_report` üretir. İnceleyen: Sedef Gizem Orulluoğlu. Tarih: 26.10.2026. Örneklemi `scripts/12_sample_for_manual_qc.py` seed 42 ile çekti: corpus kaynağa, instruction seti görev türüne göre orantılı tabakalı. Her kontrol 1 (başarılı) ya da 0 (başarısız).

Kontrol tanımları:

- Corpus: readable (metin okunabiliyor), in_domain (veri yapıları ve algoritmalar alanında), extraction_ok (metin eksiksiz ve doğru sırada çıkarılmış), header_footer_clean (başlık/altbilgi, sayfa numarası, menü kalıntısı yok), no_broken_chars (bozuk karakter yok), metadata_ok (başlık, kaynak, dil, yıl, alt konu doğru).
- Instruction: instruction_clear (talimat anlaşılır), response_correct (cevap doğru), grounded_in_source (cevap kaynak metinle tutarlı), answers_instruction (cevap talimatı karşılıyor), task_type_ok (örnek görev türüne uyuyor).

## Domain corpus

İncelenen doküman: 150

### İki inceleme turu

Aynı dokümanları önce corpus v0.9'da inceledim, bulduğum hataları pipeline'da düzelttim, sonra v1.0'da yeniden inceledim. Aşağıdaki diğer tablolar 2. turun (v1.0) sonuçlarıdır.

| Kontrol | 1. tur (v0.9) | 2. tur (v1.0) |
| --- | --- | --- |
| readable | 150/150 (%100,0) | 150/150 (%100,0) |
| in_domain | 150/150 (%100,0) | 150/150 (%100,0) |
| extraction_ok | 135/150 (%90,0) | 144/150 (%96,0) |
| header_footer_clean | 139/150 (%92,7) | 149/150 (%99,3) |
| no_broken_chars | 145/150 (%96,7) | 146/150 (%97,3) |
| metadata_ok | 123/150 (%82,0) | 146/150 (%97,3) |
| **hepsi başarılı** | 98/150 (%65,3) | 135/150 (%90,0) |

### Kontrol bazında başarı

| Kontrol | Başarılı | Oran |
| --- | --- | --- |
| readable | 150/150 | %100,0 |
| in_domain | 150/150 | %100,0 |
| extraction_ok | 144/150 | %96,0 |
| header_footer_clean | 149/150 | %99,3 |
| no_broken_chars | 146/150 | %97,3 |
| metadata_ok | 146/150 | %97,3 |
| **hepsi başarılı** | 135/150 | %90,0 |

### Kaynak bazında

| Kaynak | İncelenen | Hepsi başarılı | Başarısız kontroller |
| --- | --- | --- | --- |
| erickson_algorithms | 6 | 2 (%33,3) | extraction_ok 1, no_broken_chars 2, metadata_ok 1 |
| open_data_structures | 7 | 5 (%71,4) | extraction_ok 2 |
| open_guide_dsa | 6 | 6 (%100,0) | — |
| thealgorithms_python | 26 | 26 (%100,0) | — |
| vikipedi_tr | 16 | 13 (%81,2) | extraction_ok 1, no_broken_chars 1, metadata_ok 1 |
| wikipedia_en | 89 | 83 (%93,3) | extraction_ok 2, header_footer_clean 1, no_broken_chars 1, metadata_ok 2 |

### Hatalı dokümanlar

| Doküman | Kaynak | Başarısız kontroller | Not |
| --- | --- | --- | --- |
| DOC_000001 | erickson_algorithms | metadata_ok | sayfa başlıkları silindi; alt konu hâlâ yanlış (yigin_ve_kuyruk; giriş bölümü, genel olmalı) |
| DOC_000003 | erickson_algorithms | no_broken_chars | süs glifi kalıntısı sürüyor: "nAnalysis"; sayfa başlıkları silindi, tireler birleşti |
| DOC_000004 | erickson_algorithms | no_broken_chars | bozuk aksanlar sürüyor: "M¯atr¯avr.tta", "Pi˙ngala" (PDF glif kodlaması); sayfa başlıkları silindi |
| DOC_000009 | erickson_algorithms | extraction_ok | sayfa başlıkları silindi; şekil etiketleri metne dökülmüş olarak duruyor ("0 1 3 4 4 9 –5 ...") |
| DOC_000015 | open_data_structures | extraction_ok | tireler birleşti; şekil 5.1'in harfleri initialize() pseudocode'unun ortasında duruyor |
| DOC_000020 | open_data_structures | extraction_ok | sayfa başlıkları silindi; şekil 10.4'ün sayıları metinde duruyor |
| DOC_000138 | vikipedi_tr | metadata_ok | alt konu hâlâ yanlış (agaclar; "Algoritma" maddesi genel olmalı); algoritma türleri listesi geri geldi |
| DOC_000183 | vikipedi_tr | no_broken_chars | yorum satırında anlamsız karakter sürüyor: "dizisiǖ" (kaynak sayfada da var) |
| DOC_000193 | vikipedi_tr | extraction_ok | kaynakça kesildi; dipnot metni paragrafın içine karışmış olarak duruyor, Delete sözde kodunun başı tek satırda |
| DOC_000270 | wikipedia_en | header_footer_clean | sonda not metni ve kenar kutusu yazısı ("Gerth Stølting Brodal is a professor ...") duruyor |
| DOC_000317 | wikipedia_en | no_broken_chars | telaffuz kalıntısı "deque — // DEK)" duruyor (ikinci geçiş düzeldi) |
| DOC_000326 | wikipedia_en | extraction_ok | düzenleme mesafesi türleri tablosu yok (tablolar kapsam dışı) |
| DOC_000343 | wikipedia_en | metadata_ok | alt konu hâlâ yanlış (diziler_ve_listeler; seçim algoritması, siralama_ve_arama olmalı) |
| DOC_000363 | wikipedia_en | metadata_ok | karekök düzeldi (O(√n)); alt konu bu kez yanlış (agaclar; dinamik dizi, diziler_ve_listeler olmalı) |
| DOC_000506 | wikipedia_en | extraction_ok | örnek değerler hâlâ kayıp ("is , as A[7] = 1") |

## Instruction dataset

İncelenen örnek: 200

### Kontrol bazında başarı

| Kontrol | Başarılı | Oran |
| --- | --- | --- |
| instruction_clear | 192/200 | %96,0 |
| response_correct | 183/200 | %91,5 |
| grounded_in_source | 189/200 | %94,5 |
| answers_instruction | 194/200 | %97,0 |
| task_type_ok | 181/200 | %90,5 |
| **hepsi başarılı** | 151/200 | %75,5 |

### Görev türü bazında

| Görev türü | İncelenen | Hepsi başarılı | Başarısız kontroller |
| --- | --- | --- | --- |
| algoritma_izleme | 23 | 19 (%82,6) | response_correct 4 |
| bilgi_yetersizligi | 14 | 14 (%100,0) | — |
| coktan_secmeli_soru_uretimi | 24 | 18 (%75,0) | response_correct 2, grounded_in_source 1, answers_instruction 3, task_type_ok 1 |
| hata_bulma | 16 | 2 (%12,5) | instruction_clear 1, response_correct 4, grounded_in_source 1, task_type_ok 11 |
| karmasiklik_analizi | 19 | 15 (%78,9) | instruction_clear 2, grounded_in_source 1, answers_instruction 1, task_type_ok 1 |
| karsilastirma | 23 | 16 (%69,6) | instruction_clear 2, grounded_in_source 1, answers_instruction 2, task_type_ok 2 |
| kavram_aciklama | 33 | 28 (%84,8) | instruction_clear 1, response_correct 4, grounded_in_source 3, task_type_ok 1 |
| kod_okuma | 20 | 17 (%85,0) | grounded_in_source 2, task_type_ok 1 |
| konu_ozeti_anlatim | 14 | 11 (%78,6) | instruction_clear 1, response_correct 1, task_type_ok 2 |
| yanlis_cevap_aciklama | 14 | 11 (%78,6) | instruction_clear 1, response_correct 2, grounded_in_source 2 |

### Setten çıkarılan örnekler

| Örnek | Görev türü | Başarısız kontroller | Not |
| --- | --- | --- | --- |
| DOC_000001:18:kavram_aciklama | kavram_aciklama | instruction_clear, task_type_ok | bağlamsız talimat metindeki N, I, E simgelerini tanımlamadan kullanıyor; bir kavramı açıklatmıyor, değer soruyor |
| DOC_000002:43:karmasiklik_analizi | karmasiklik_analizi | grounded_in_source | O(n) sonucu metinde var ama gerekçe ("alt ağaç sınırları doğrusal taramayla", "sabit sayıda karşılaştırma") metinde yok; metin yalnızca alıştırma listesi |
| DOC_000003:7:algoritma_izleme | algoritma_izleme | response_correct | sonuç {2, 3} doğru ama izleme karışık: 2. adım CS(X,1,2) çağrısını CS(X,1,5)'in içinden yapılmış gibi anlatıyor; ilk dalın None döndüğü gösterilmiyor |
| DOC_000005:13:karsilastirma | karsilastirma | task_type_ok | karşılaştırma türünde ama talimat bir kavramı açıklatıyor (istikrarsız eşleşme), karşılaştırma yok |
| DOC_000005:18:karsilastirma | karsilastirma | instruction_clear | talimat "hastalar (doktorlar)" diyor: metinde hasta değil doktor var, ifade yanıltıcı |
| DOC_000006:21:karsilastirma | karsilastirma | grounded_in_source | son cümle ("bağlantı ve döngüsüzlüğü test etmek için ilk tanım tercih edilir") metinde yok |
| DOC_000014:0:karsilastirma | karsilastirma | task_type_ok | karşılaştırma türünde ama talimat bir ilişkiyi açıklatıyor, karşılaştırma ekseni yok |
| DOC_000015:0:hata_bulma | hata_bulma | task_type_ok | talimat hatanın yerini ima ediyor ("tablonun boyutunu ayarlarken"), koddaki tek boyut satırı resize koşulu; hata ve düzeltme doğru (DOC_000051:0 ile aynı ölçüt, ikinci okumada düzelttim) |
| DOC_000015:6:kavram_aciklama | kavram_aciklama | response_correct, grounded_in_source | HATA: q'yu "silinmiş elemanlar hariç" diye tanımlıyor; metne göre q = n + del sayısı, yani silinenler dahil |
| DOC_000021:17:konu_ozeti_anlatim | konu_ozeti_anlatim | instruction_clear, task_type_ok | bağlamsız talimat "bu dersteki uygulaması" diyerek görülmeyen metne dayanıyor; cevap tek cümle, özet değil |
| DOC_000021:2:hata_bulma | hata_bulma | task_type_ok | hatanın yeri talimatta söyleniyor ("i1 ← i2 satırı yanlış"); hata, kaynak metindeki PDF çıkarım bozukluğundan geliyor |
| DOC_000026:9:kod_okuma | kod_okuma | task_type_ok | kod okuma türünde ama "kod" yalnızca metindeki bir koşul satırı; aslında kavram sorusu |
| DOC_000030:0:yanlis_cevap_aciklama | yanlis_cevap_aciklama | response_correct, grounded_in_source | HATA: son cümle "O(1) ekleme için yığın (heap) gerekir" diyor; ikili yığında ekleme O(log n), metinde de böyle bir bilgi yok |
| DOC_000051:0:hata_bulma | hata_bulma | task_type_ok | talimat hatanın yerini ima ediyor ("minn ve maxx değerlerini yanlış atıyor"); hata gerçek, düzeltme doğru |
| DOC_000059:0:hata_bulma | hata_bulma | task_type_ok | talimat hatanın yerini söylüyor ("boş liste kontrolünde beklenen sonuç yanlış ele alınıyor"); hata ve düzeltme doğru (DOC_000466:1 ile aynı ölçüt, ikinci okumada düzelttim) |
| DOC_000072:1:hata_bulma | hata_bulma | task_type_ok | talimat hatanın yerini söylüyor ("is_full() metodu yanlış sonuç veriyor") ve kod yalnızca o tek satırdan ibaret; bulunacak bir şey kalmıyor (DOC_000513:9 ile aynı ölçüt, ikinci okumada düzelttim) |
| DOC_000110:1:hata_bulma | hata_bulma | instruction_clear | talimattaki belirti yanıltıcı ("sıralı olmayan dizide hata fırlatması gerekirken"); asıl hata bound = 0 ve cevap onu doğru buluyor |
| DOC_000111:0:hata_bulma | hata_bulma | response_correct, task_type_ok | HATA: konan değişiklik (prev >= yerine prev >) davranışı değiştirmiyor; iki sürümü 39 dizi × 210 değerde çalıştırdım, sonuçlar aynı. Cevabın "sonsuz döngü / yanlış indeks" iddiası yanlış |
| DOC_000124:0:algoritma_izleme | algoritma_izleme | response_correct | sonuç [1,2,3] doğru ama izleme kodun sırasını yanlış anlatıyor: kod aynı j adımında önce ileri sonra geri karşılaştırıyor (j=0'da iki yer değişimi), cevap önce bütün ileri turu yapıyor |
| DOC_000146:0:coktan_secmeli_soru_uretimi | coktan_secmeli_soru_uretimi | response_correct | HATA: açıklama A, C ve D şıklarını "bağlı listelerin avantajları arasındadır" diyor; bu şıklar avantajların tersi, yani açıklama yanlış bilgi veriyor (ilk okumada küçük kusur saymıştım, ikinci okumada yanlış bilgi olduğu için düzelttim) |
| DOC_000148:0:hata_bulma | hata_bulma | response_correct, grounded_in_source, task_type_ok | HATA: talimattaki kod kaynaktaki kodla aynı (yalnızca ≤ yerine <=), hata konmamış; cevap var olmayan bir hata uyduruyor |
| DOC_000158:2:hata_bulma | hata_bulma | task_type_ok | talimat hatanın yerini söylüyor ("while döngüsünün koşulunda"); hata ve düzeltme doğru |
| DOC_000206:4:karsilastirma | karsilastirma | instruction_clear | bağlamsız talimat 2–3 heap'e özgü "çalışma alanı" kavramını hangi yapı olduğunu söylemeden kullanıyor ("Heap veri yapısında") |
| DOC_000211:1:yanlis_cevap_aciklama | yanlis_cevap_aciklama | response_correct, grounded_in_source | HATA: "tutarlılık her zaman zorunludur" diyor; metin yalnızca en az düğüm genişletme (optimal efficiency) için tutarlılığın gerektiğini söylüyor, kabul edilebilir heuristic ile de en kısa yol bulunur |
| DOC_000216:0:hata_bulma | hata_bulma | response_correct | HATA: cevap j=0 iken X[i-1] negatif indekse erişir diyor; i=0 olunca while koşulu kısa devre yapar, asıl hata yalnızca length(X) üst sınırı |
| DOC_000219:1:konu_ozeti_anlatim | konu_ozeti_anlatim | task_type_ok | konu özeti değil, iki matrisin farkını soran karşılaştırma sorusu |
| DOC_000244:0:kavram_aciklama | kavram_aciklama | response_correct, grounded_in_source | HATA: "ulaşılamayan veya ulaşılan negatif döngüleri tespit eder" diyor; metne göre yalnızca kaynaktan ulaşılabilen negatif döngü tespit edilir |
| DOC_000255:8:hata_bulma | hata_bulma | task_type_ok | talimat hatanın yerini söylüyor ("A düğümünün hiç çocuğu yoksa"); hata ve düzeltme metindeki silme kuralıyla uyumlu |
| DOC_000267:3:coktan_secmeli_soru_uretimi | coktan_secmeli_soru_uretimi | answers_instruction | bağlamsız örnekte üretilen soru "Verilen bilgilere göre" diyor, metni görmeyen öğrenci cevaplayamaz; LaTeX kalıntısı "x_2leq26", "x_2geq27" |
| DOC_000270:5:kavram_aciklama | kavram_aciklama | response_correct | HATA: "kökler üzerinde dörder kılavuz" diyor; metne göre her kök için iki, toplam dört kılavuz var; talimatta yazım hatası "Brodie kuyruğu" |
| DOC_000343:1:kod_okuma | kod_okuma | grounded_in_source | talimattaki kod kaynaktan bozuk kopyalanmış: newRight satırında "(n − i) × s/n" yerine "(n − i) − s/n"; cevap farkı fark etmiyor |
| DOC_000360:4:karmasiklik_analizi | karmasiklik_analizi | instruction_clear, task_type_ok | talimat bulanık: metin "n, 2^b'den çok küçük" diyor, talimat "b'den küçük" diyor; sorulan şey asimptotik karmaşıklık değil, sabit maliyet (bölme yerine kaydırma) |
| DOC_000378:3:coktan_secmeli_soru_uretimi | coktan_secmeli_soru_uretimi | response_correct | HATA: açıklama A şıkkını yanlış anlatıyor ("sadece bit sayısını yarıya indirmeden bahsediyor"); A şıkkı anahtar boyutunu yarıya indirip bit sayısını koruduğunu söylüyor; yazım hatası "n faktörküçültme" (ikinci okumada düzelttim) |
| DOC_000404:1:konu_ozeti_anlatim | konu_ozeti_anlatim | response_correct | HATA: "en az 1 içeren sütunlar incelenir" diyor; metinde en az sayıda 1 içeren sütun seçiliyor; matris boşsa başarıyla bitme adımı yok |
| DOC_000405:3:coktan_secmeli_soru_uretimi | coktan_secmeli_soru_uretimi | answers_instruction | bağlamsız örnekte üretilen soru metindeki S/W örneğine dayanıyor (W[2], S[10]); örneği görmeyen öğrenci cevaplayamaz |
| DOC_000415:0:algoritma_izleme | algoritma_izleme | response_correct | HATA: verilen örnekte boşluk zaten hazır, hiçbir eleman kaymıyor; izleme yine de "birkaç komşu eleman hareket ettirilir" diyor, yani izleme örnekle uyuşmuyor (ikinci okumada düzelttim) |
| DOC_000417:5:karsilastirma | karsilastirma | answers_instruction | karşılaştırma tek taraflı: zincirleme için yalnızca tarih var, teknik özellik yok; terim hataları: "linear probing" için "doğrusal arama", "assembler" için "derleyici" |
| DOC_000454:5:hata_bulma | hata_bulma | response_correct | düzeltme doğru (or) ama gerekçe çelişkili: "dizilerden herhangi biri bitene kadar devam etmeli" diyor, doğrusu ikisi de bitene kadar |
| DOC_000454:6:yanlis_cevap_aciklama | yanlis_cevap_aciklama | instruction_clear | talimat yanlış önkabulle soruyor ("uzun sekanslar için neden uygundur"); cevap doğru; yazım hatası "hizzalama" |
| DOC_000466:1:hata_bulma | hata_bulma | task_type_ok | talimat hatanın yerini söylüyor ("heap1 boş olduğunda"); hata ve düzeltme doğru |
| DOC_000487:0:algoritma_izleme | algoritma_izleme | response_correct | HATA: kalan kümede anahtarı 8 olan nokta da var ve 8 <= 8 olduğu için left_data'ya girmeli; cevap bu noktayı atlıyor, doğrusu left=[2,5,8], right=[12,15] |
| DOC_000508:10:karsilastirma | karsilastirma | answers_instruction | soru iki bileşenin farkını istiyor; cevap count(x) için "sayım bilgilerini sağlar" deyip geçiyor, fark anlatılmıyor |
| DOC_000508:9:karmasiklik_analizi | karmasiklik_analizi | instruction_clear | bağlamsız talimat "bu veri yapısının" diyor, hangi yapı olduğu belli değil (yol üzerinde τ-çoğunluk sorgusu yapısı); cevap metinle aynı |
| DOC_000513:9:hata_bulma | hata_bulma | task_type_ok | talimat yalnızca hatalı iki satırı veriyor ve durumu söylüyor; bulunacak bir şey kalmıyor |
| DOC_000517:1:kod_okuma | kod_okuma | grounded_in_source | talimattaki kod kaynaktan bozuk kopyalanmış: getLeft içinde "return left;" iki kez (Java'da derlenmez); cevap fark etmiyor |
| DOC_000531:4:coktan_secmeli_soru_uretimi | coktan_secmeli_soru_uretimi | grounded_in_source | doğru şık D'nin yanlışlığı metinden çıkmıyor; açıklama yalnızca "metinde böyle bir ifade yok" diyor (metin NSCountedSet'in yapısını hiç anlatmıyor) |
| DOC_000536:4:karmasiklik_analizi | karmasiklik_analizi | answers_instruction | "neden" kısmı totoloji: "|V| ile |E|'nin çarpımına bağlı" diyor; |V|−1 tur boyunca tüm kenarların gevşetilmesi anlatılmıyor |
| DOC_000559:7:coktan_secmeli_soru_uretimi | coktan_secmeli_soru_uretimi | answers_instruction, task_type_ok | talimat düz bir soru soruyor ("küçük yığına ne yapılır?"), cevap çoktan seçmeli soru üretiyor; soruya doğrudan cevap verilmiyor |
| DOC_000598:6:kavram_aciklama | kavram_aciklama | response_correct, grounded_in_source | HATA: WAVL'ı "çocuklarının rank farkı en fazla bir olan ağaç" diye tanımlıyor; bu AVL koşulu, metin de bazı WAVL ağaçlarında çocuk yükseklik farkının birden fazla olduğunu söylüyor |

## Uygulanan işlem

Instruction setinde incelenen 200 örnekten 151 tanesi onaylandı (verified=true, verified_by=manual:Sedef Gizem Orulluoğlu); 49 tanesi manual_rejected sebebiyle setten çıkarıldı (reports/exclusions.csv, aşama manual_qc). Corpus'ta inceleme yalnızca ölçüm için; hatalı dokümanların listesi yukarıda.

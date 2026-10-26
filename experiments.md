# Çalışma Günlüğü

Ne denedim, ne sonuç aldım, ne karar verdim. Sayıların tamamını pipeline çıktılarından aldım.

## 12.10.2026 — Kaynak araştırması

Açık lisanslı DSA kaynakları aradım; her adayın lisansını kaynağın kendi sayfasından okudum.

- Uygun bulduklarım: Open Data Structures (CC BY 2.5 CA), An Open Guide to Data Structures and
  Algorithms (CC BY 4.0), Erickson — Algorithms (CC BY 4.0), TheAlgorithms/Python (MIT),
  Türkçe Vikipedi (CC BY-SA 4.0).
- Ticari olmayan lisanslı adaylar (bu turda almadım): pythonds kitabı, MIT OCW 6.006,
  Ankara Üniversitesi Açık Ders (üçü de CC BY-NC-SA 4.0).
- Lisansı belirsiz olduğu için elediklerim: OpenDSA (MIT lisans dosyası kitap metnini açıkça
  kapsamıyor), lisanssız Türkçe GitHub depoları, lisans bildirimi olmayan Türkçe ders notu PDF'leri.
- Türkçe Vikikitap'ta DSA kitabı yok.

Sonuç: Açık lisanslı Türkçe DSA metni çok az. Corpus ağırlıkla İngilizce olacak.

## 13.10.2026 — Kaynak seti

Karar: Beş kaynak aldım (yukarıdaki "uygun bulduklarım"). İngilizce Vikipedi ilk sette yoktu;
aynı gün sonradan ekledim (aşağıda "İngilizce Vikipedi eklendi" girdisi).

Türkçe Vikipedi madde seçimi: ilgili kategorilerdeki 121 maddenin her birini açıp içeriğine baktım,
69'unu aldım (6'sını "sınırda" olarak işaretledim). Elediklerim veritabanı, kriptografi, NP teorisi
ya da konu dışı maddeler. Örnek: "Ağaçlar (yapı)" kategorisindeki "Koru" maddesi veri yapısı değil,
ağaçlık alan. Kategorilerde olmayan 5 çekirdek maddeyi (Bağlı liste, Veri yapısı, Zaman karmaşıklığı,
Çizge teorisi, En kısa yol problemi) ayrıca ekledim.

Kod dosyaları: seçtiğim beş dizinde 331 dosya var; kod corpus'taki dokümanların çoğunluğu olmasın
diye 100 ile sınırladım (dizin başına 40/20/10/15/15, sabit seed ile rastgele seçim).

## 13.10.2026 — Open Data Structures: HTML yerine PDF

Kitabın HTML sürümünü denedim. Formüller, değişken adları ve sözde kod resim olarak gömülü
(bir alt bölüm sayfasında 172 resim); trafilatura çıktısında cümleler boşluklu ve anlamsız kaldı.
Site de HTML sürümünün eksik formül içerebileceğini, PDF'in daha güvenilir olduğunu yazıyor.

Karar: PDF kullanıyorum. Kitap tek doküman olmasın diye PDF'in kendi içindekiler ağacındaki
sayfa aralıklarıyla 14 bölüme ayırdım. Bunun için indirme listesine `pages` sütununu ekledim;
ham PDF bölünmüyor, aralığı metin çıkarma adımı okuyor.

## 13.10.2026 — Vikipedi ve robots.txt

Vikipedi'nin robots.txt dosyası `/w/` ve `/api/` yollarını (API dahil) kapatıyor,
`/wiki/` madde sayfalarına izin veriyor.

Karar: Maddeleri API ile değil, normal madde sayfası (HTML) olarak indirdim.

## 13.10.2026 — İndirme

204 doküman indirdim, hata yok: 104 adres + 100 kod dosyası.

Karşılaştığım sorunlar ve çözümleri:

- Windows'ta kayıt dosyası yazılırken anlık dosya kilidi hatası aldım. Yazma işlemine yeniden
  deneme ekledim.
- Git, kod dosyalarının satır sonlarını Windows biçimine çevirdi (deponun `.gitattributes`
  dosyası `* text=auto` diyor). `core.autocrlf=false` tek başına yetmedi; `core.eol=lf` de
  gerekti. Düzeltmeden sonra 100 dosyanın 100'ü depodaki içerikle bayt bayt aynı.
- Bir çalıştırmada Erickson sitesinin robots.txt isteği zaman aşımına uğradı. Bu durumu artık
  "robots engeli" değil `robots_unreachable` olarak kaydediyorum ve sonraki çalıştırmada
  yeniden deniyorum.
- Doküman numaraları indirme sırasına bağlı kalmasın diye her çalıştırmanın sonunda
  (kaynak adı, dosya yolu, sayfa) sırasına göre veriyorum.

Ham veriyi bu düzeltmelerden sonra temiz bir klasöre baştan indirdim.

## 13.10.2026 — Erickson: bölüm PDF'leri yerine tam kitap

Sitedeki ayrı bölüm PDF'lerini denedim. Çıkardığım metinde 4.026 adet U+FFFF ve 175 adet U+F8FF
karakteri vardı: bölüm numaraları, şekil numaraları ve küçük büyük harfle dizilmiş sayfa
başlıkları okunmuyordu. Font tablolarını inceledim: matematik fontlarının Unicode tablosu yok;
örneğin sol ok boşluk olarak, `∈` işareti `2` olarak çıkıyordu. Site bu dosyaların tam kitap
PDF'inden kesildiğini yazıyor.

Tam kitap PDF'ini (pdfTeX çıktısı) denedim: aynı yerler doğru çıkıyor.

Karar: Tam kitap PDF'ini tek dosya olarak indiriyorum, 10 bölümü içindekiler ağacındaki sayfa
aralıklarıyla ayırıyorum.

## 13.10.2026 — Unicode karşılığı olmayan matematik glifleri

Tam kitap PDF'lerinde de bazı glifler Unicode'a çevrilemiyor: Open Data Structures'ta 1.217,
Erickson'da 736 glif. Bunlar büyük toplam işareti, uzun parantez/köşeli/süslü parantez parçaları,
`≠`, kenar oku ve karekök. PyMuPDF bunları varsayılan ayarda ham font koduna çeviriyordu
(örneğin toplam işareti `X` harfi olarak çıkıyordu).

Çözüm: Glifin adı gömülü Type1 font programında yazılı (`summationdisplay`, `parenleftbig`,
`nequal`, `shortrightarrow` …). Bu adları okuyup küçük bir tabloyla metne çeviriyorum.
Çok parçalı uzun ayraçlarda üst parçayı ayracın kendisi sayıyorum, diğer parçaları atıyorum.
Tabloda olmayan glifi tahmin etmiyorum, U+FFFD olarak işaretleyip sayıyorum.

Doğrulama: Her glif türünün ilk geçtiği yeri sayfa görüntüsü olarak basıp adla karşılaştırdım.

| Kitap | Sorunlu glif | Çözülen | Çözülemeyen |
| --- | --- | --- | --- |
| Open Data Structures | 1.217 | 1.217 (`∑` 86, `≠` 82, parantezler; 872 iskele parçası atıldı) | 0 |
| Erickson | 736 | 724 (`→` 314, `∑` 54, `√` 19, parantezler) | 12 |

Çözülemeyen 12 glif: çıkarıcı uzun font adlarını kısalttığı için iki farklı fonta uyan adlar.
Temizleme adımında siliniyor.

Not: PyMuPDF'in hazır glif adı sözlüğünü (`glyph_name_to_unicode`) denedim; `A` gibi temel adları
bile çözmediği için kullanmadım.

## 13.10.2026 — Ligatürler ve kaybolan boşluklar

Çıkardığım kitap metinlerinde `ﬁ ﬀ ﬂ ﬃ ﬄ` ligatürleri tek karakter olarak kalıyordu
(Open Data Structures 875, Erickson 1.804). Asıl sorun: kelime sonundaki ligatürden sonraki
boşluk kayboluyordu ("trade-oﬀbetween", "oﬀthe"). Bu, temizleme adımında düzeltilemez; çünkü
"oﬀthe" ile "oﬀered" ayırt edilemez.

Deneme: PyMuPDF'in ligatür koruma bayrağını kapattım. İki kitabın 624 sayfasını eski ve yeni
ayarla karşılaştırdım: ligatürlerin harflere açılması dışındaki tek fark 37 boşluğun geri
gelmesi (Open Data Structures 8, Erickson 29). Başka hiçbir karakter değişmedi.

Karar: Ligatürleri metin çıkarma adımında açıyorum. Temizlemedeki ligatür kuralı (R1) HTML
kaynakları için yerinde kalıyor.

Not: Metin dosyalarında editörün "FF" kutusu olarak gösterdiği karakter sayfa ayırıcıdır
(form feed). Bilerek koyuyorum; temizleme adımı tekrar eden sayfa başlıklarını bununla buluyor
ve iş bitince siliyor.

## 13.10.2026 — Extraction aracı karşılaştırması

24 PDF dokümanı (iki kitabın 24 bölümü) üzerinde PyMuPDF ve pdfplumber'ı denedim.

| Araç | Başarılı | Süre | Çevrilemeyen karakter |
| --- | --- | --- | --- |
| PyMuPDF (glif çözümüyle) | 24 | 7,62 sn | 12 |
| pdfplumber | 24 | 70,80 sn | 590 |

pdfplumber ayrıca incelediğim sayfada kelimeleri birbirine yapıştırdı ("SimplifyandDelegate").

Karar: PyMuPDF kullanıyorum. Taranmış PDF yok; OCR gerekmedi.

## 13.10.2026 — Extraction sonucu

204 dokümanın 203'ünden metin çıkardım, 1'i elendi.

| Kaynak | Doküman | Karakter |
| --- | --- | --- |
| Erickson — Algorithms | 10 | 681.536 |
| Open Data Structures | 14 | 404.165 |
| TheAlgorithms/Python | 100 | 389.745 |
| An Open Guide to DSA | 11 | 333.510 |
| Türkçe Vikipedi | 68 | 205.727 |
| Toplam | 203 | 2.014.683 |

- Elenen: "Seçim problemi" Vikipedi maddesi, 176 karakter (alt sınır 200). Madde gerçekten
  bu kadar kısa; kural gereği sebep kodu `extraction_error`.
- Türkçe pay karakter bazında %10,2.
- 11 Vikipedi maddesi 500 karakterin altında; filtreleme adımında `too_short` adayı.

Açık konular: corpus küçük (yaklaşık 2 milyon karakter); kaynak genişletmeyi ilk tur sonunda
değerlendireceğim. Tokenizer'ın hangi model ailesinden olacağını hocama soracağım.

## 13.10.2026 — İngilizce Vikipedi eklendi

Sebep: İlk beş kaynakla corpus yaklaşık 2 milyon karakterde kaldı; ileride veri yetersizliği
sorunu çıkmasın diye İngilizce Vikipedi'yi de aldım.

Madde seçimi:

- 46 kategori sayfasını taradım (veri yapıları, ağaçlar, yığınlar, hash, sıralama, arama, çizge
  algoritmaları, dinamik programlama, açgözlü, böl-yönet, özyineleme, algoritma analizi vb.):
  1.369 benzersiz başlık.
- Başlıkları elle seçtim: 385 madde kategorilerden, 23 çekirdek madde ayrıca (Memoization,
  Edit distance, Space complexity, Graph theory …). Toplam 408 aday.
- Kapsam dışı bıraktıklarım: ağ akışı ve NP teorisi (kitaplarda da dışarıda bırakmıştım),
  kriptografik hash, veritabanı, ağ protokolleri, oyun ağacı/yapay zekâ araması, makine
  öğrenmesi, matematiksel asimptotik, paralel/dağıtık/kuantum algoritmalar, liste ve
  karşılaştırma sayfaları.
- 408 adayın her birini açtım: hepsi HTTP 200; 3'ü başka bir maddeye yönlendirme çıktı
  (Multiset → Set, (a,b)-tree → B-tree, Decrease-and-conquer → Divide-and-conquer algorithm),
  onları çıkardım. Anlam ayrımı sayfası yok.

Sonuç: 405 madde (43'ü "sınırda" işaretli). Hepsini indirip metnini çıkardım; şüpheli karakter 0.
Lisans notu (CC BY-SA 4.0) indirdiğim 405 sayfanın her birinde var.

| Kaynak | Doküman | Karakter | Pay |
| --- | --- | --- | --- |
| İngilizce Vikipedi | 405 | 5.097.619 | %71,7 |
| Erickson — Algorithms | 10 | 681.536 | %9,6 |
| Open Data Structures | 14 | 404.165 | %5,7 |
| TheAlgorithms/Python | 100 | 389.745 | %5,5 |
| An Open Guide to DSA | 11 | 333.510 | %4,7 |
| Türkçe Vikipedi | 68 | 205.727 | %2,9 |
| Toplam | 608 | 7.112.302 | |

- Corpus 2,0 milyon karakterden 7,1 milyon karaktere çıktı.
- Bedeli: corpus'un %71,7'si tek kaynaktan (İngilizce Vikipedi) geliyor; Türkçe pay %10,2'den
  %2,9'a düştü.
- 2 madde 500 karakterin altında (Algorithmic paradigm 307, Cascade merge sort 331);
  filtreleme adımında `too_short` adayı. Elle çıkarmadım, kararı pipeline verecek.
- Vikipedi başlıklarının sonunda " - Wikipedia" / " - Vikipedi" eki var (14.10.2026 denetiminde düzelttim).

Not: İndirme sırasında konsol, "ů" harfi içeren bir adresi (Borůvka's algorithm) log satırına
yazamadı. Dosya indi, kayıt dosyaları doğru; konsol çıktısını bu karakterlerde hata vermeyecek
şekilde düzelttim.

## 14.10.2026 — FAZ 1–2 denetimi (Vize Rehberi ve proje planına karşı)

FAZ 3'e geçmeden önce yaptıklarımın hepsini rehbere ve proje planıma karşı yeniden kontrol ettim.

Sorunsuz çıkanlar:

- Ham veri (rehber §5): 609 dosyanın 609'u indirme kaydındaki sha256 ile bayt bayt aynı.
  Kayıtta olmayan ham dosya yok (TheAlgorithms'in LICENSE.md ve kaynak bilgisi dosyası bilerek var).
- Kaynak tablosu (rehber §4): her kaynağın doküman sayısı kayıt dosyasıyla aynı; lisanslar dolu.
- Kişisel veri (rehber §4): çıkarılan metinlerde e-posta adresi yok.
- Taranmış PDF yok; OCR gerekmedi.

Bulduğum ve düzelttiğim sorunlar:

1. Vikipedi formülleri sessizce kayboluyordu (rehber §6'nın uyardığı "hata vermeden çöp").
   Örnek: "on average, the algorithm takes O(n log n) comparisons" cümlesi "takes comparisons"
   olarak çıkıyordu. 316 sayfada 12.144 formül öğesi var. Her formülü, Vikipedi'nin sayfada
   sakladığı TeX kaynağıyla değiştiriyorum (satır içi `$…$`, ayrı satırda `$$…$$`).
   Sonuç: 10.405 kelime metne geri geldi; eski metindeki hiçbir kelime kaybolmadı.
2. Vikipedi'nin içi boş "çapa" etiketleri (`<span class="anchor">`, 33 sayfada 90 adet)
   trafilatura'nın arkalarındaki paragrafı atmasına yol açıyordu. Örnek: Double hashing
   maddesinde "The secondary hash function … should have several characteristics" cümlesi.
   Etiketleri metin çıkarılmadan önce siliyorum (boş oldukları için metne dokunmuyor).
3. Open Guide sözde kodları resim olarak veriliyor; 7 bölümdeki 69 sözde kod metne hiç
   girmiyordu. Resmin açıklama metni (alt) kodun satır numaralı tam yazımı; satırlara ayırıp
   metne koyuyorum. Girinti açıklama metninde olmadığı için kayıp.
4. Başlıklar: 473 Vikipedi başlığının sonunda " - Wikipedia" / " - Vikipedi" eki vardı.
   Sayfanın kendi ana başlığıyla (h1) karşılaştırarak atıyorum; site adını koda yazmadım.
5. "Seçim problemi" maddesi `extraction_error` ile elenmişti; oysa metin doğru çıkıyor, madde
   gerçekten 176 karakter. Web sayfası için kısa metin artık `too_short`; kitap bölümünden
   200 karakterden az metin çıkması ise hâlâ `extraction_error` (orada çıkarım bozulmuş demektir).
6. Kapsam: 4 İngilizce Vikipedi maddesi kapsam tanımımın dışarıda bıraktığı konularda (T-tree ve
   Log-structured merge-tree: veritabanı iç yapısı; Free list: işletim sistemi bellek yönetimi;
   Extendible hashing: veritabanı/dosya sistemi indekslemesi). Ham veriyi silmedim;
   `config.filter.out_of_scope_urls` listesine yazdım, FAZ 4'te `out_of_domain` olarak eleniyor.
7. Kaynak tablosundaki İngilizce Vikipedi satırına "neden alındı" bilgisini ekledim (rehber §4).

Doğrulama: Değişiklik yapmadığım 286 dokümanın metni bayt bayt aynı kaldı. Değişen her
dokümanda eski metindeki kelimeleri tek tek saydım; kaybolan kelime yok. 12 birim testi geçiyor.

Bilinen sınırlılık: Tabloları metin dışında bırakıyorum (FAZ 2'de verdiğim karar). 107 HTML
dokümanında 246 tablo var (çoğu Vikipedi'deki karmaşıklık karşılaştırma tabloları).

Extraction başarısı (rehber §6): 609 dokümanın 608'ini çıkardım (%99,8). Bozuk çıkarım 0;
1 doküman gerçekten kısa olduğu için elendi.

| Kaynak | Doküman | Karakter | Pay |
| --- | --- | --- | --- |
| İngilizce Vikipedi | 405 | 5.278.122 | %72,2 |
| Erickson — Algorithms | 10 | 681.536 | %9,3 |
| Open Data Structures | 14 | 404.165 | %5,5 |
| TheAlgorithms/Python | 100 | 389.745 | %5,3 |
| An Open Guide to DSA | 11 | 347.233 | %4,8 |
| Türkçe Vikipedi | 68 | 208.991 | %2,9 |
| Toplam | 608 | 7.309.792 | |

## 14.10.2026 — Extraction'a iki ek düzeltme (FAZ 3 hazırlığında buldum)

- Vikipedi bölüm başlıkları metne hiç girmiyordu ("History", "References" …): trafilatura,
  başlığı saran kutuyu süs öğesi sayıp atıyordu. Kutuyu açıyorum; 4.566 başlık satırı geri geldi
  (Türkçe karakterli başlıklarda ayrıca boş bir kimlik etiketi metni yutuyordu, onu da siliyorum).
  Başlıklar hem kaynakça bölümünü ayırmak (R8) hem de bölüm sınırında parçalama için gerekli.
- Kitaplarda üsler düz metne karışıyordu: `O(n²)` → `O(n2)`; `2ⁿ` ile `2n` ayırt edilemiyordu.
  PDF'in üst simge işaretini okuyup TeX gösterimiyle yazıyorum: `O(n^2)`, `2^{n−1}`, `10^6`.
  Doğrulama: işaretleme kapalıyken yeni kod 24 bölümün 24'ünde eski çıktıyla bayt bayt aynı;
  açıkken değişen 876 satırın hepsinde fark yalnızca `^ { }` eklenmesi. Bir örnek sayfayı
  görüntüsüyle karşılaştırdım (Erickson s. 180: O(n²)).
  Sınırlılık: alt simge PDF'te işaretli değil, `F2n−1` gibi kalıyor; dipnot numaraları da `^1`
  olarak işaretleniyor.

## 14.10.2026 — FAZ 3: Temizleme

Kurallar `scripts/utils/text_utils.py` içinde; sayılar `reports/cleaning_rules.md` dosyasında.
Kuralları uygulamadan önce gerçek metin üzerinde ölçtüm. Planladığım üç kuralı ölçüm sonucunda
daralttım:

- R3 ve R4 yalnızca sayfanın ilk ve son 2 dolu satırına bakıyor. Ölçüm: kitaplarda 5+ sayfada
  tekrar eden satırların çoğu gövdede ve sayfa başlığı değil; sözde kod ("mark v", "for each
  edge v→w"), formül parçası ("∑", "∞") ve şekil etiketi. Gövdede tek başına duran sayılar
  da alt alta dizilmiş kesirlerin paydası ya da sözde kodun boş satır numarası.
  Gerçek sayfa başlıkları ve numaraları hep sayfa kenarında.
- R5 listesinden "Search"ü çıkardım (İngilizce Vikipedi'de 7 yerde gerçek bölüm başlığı);
  "Appearance" ve "Görünüm"ü ekledim (Vikipedi menüsünden sızan satır).
- R6: satır sonundaki 654 tireden 37'si gerçek tireli kelime ("B-tree", "two-dimensional",
  "divide-and-conquer"). Planladığım yalın kural bunları "Btree" yapardı. Kararı corpus'taki
  kelime sıklığıyla veriyorum; iz yoksa varsayılan kural (tire atılır).
- R8: "ilk kaynakça başlığından sonrasını sil" Segment tree maddesinde "Notes"tan sonra gelen
  "History" bölümünü silerdi. Kesim noktasından sonra düzyazı varsa kesmiyorum.

Sonuç: 608 dokümanı temizledim, 7.390.772 → 6.346.577 karakter. Silinenin büyük kısmı Vikipedi
kaynakçaları (R8: 409 madde, 1.026.266 karakter). Kitaplardan %0,8 – %1,8 silindi.

Doğrulama: R8'in kestiği 409 kuyrukta düzyazı satırı yok. Kitap metinlerinde sayfa geçişini
kontrol ettim ("162", "§3.4", "Linked Lists" silinmiş, cümle kesintisiz sürüyor).
29 birim testi geçiyor (planladığım 5 temel test dahil).

Bilinen sınırlılıklar:

- 8 Vikipedi maddesinde kaynakça sonda kaldı: kaynaklar liste biçiminde değil, düz satır olarak
  yazılmış; kural düzyazı gördüğü yerde kesmiyor.
- Kitaplarda sayfa altı dipnotları metnin arasında kalıyor.
- 5 sayfadan kısa bölümlerin sayfa üstü başlığı ("4.2. Scheduling Classes") silinmiyor.

Sürüm: v0.5.

## 14.10.2026 — Temizleme düzeltmesi: şekil hücreleri ve sayfa kenarındaki sayılar

Erickson'ın temiz metninde her satırda tek harf / sembol olan yerler gördüm (Recursion bölümü).
Kitap sayfası görüntüsüyle karşılaştırdım:

- Semboller kitapta gerçekten var: ▲ (Alıştırma 32'de yerel minimum işareti), ♕ ♛ (8 vezir
  şekli), ■ □ (Mors kodu örneği), ➜ (şekildeki oklar). ✠ ise Erickson'ın BFS algoritmasında
  kullandığı özel işaret (`Push(✠)`); sözde kodun parçası, doğru.
- Sorun 1: PDF çıkarımı aralıklı dizilmiş şekil hücrelerini ve parçalı formülleri her hücre
  ayrı satır olacak şekilde veriyor; şeklin satır yapısı kayboluyor. Kitaplarda 4+ satırlık
  358 böyle dizi var (Erickson 167, ODS 191). Yeni kural R9: PDF'ten gelen metinde art arda
  en az 4 kısa satırı (en çok 3 karakter, kod değil) tek satırda birleştiriyorum. Silme yok.
  HTML'de uygulamıyorum: orada kısa satırlar ASCII çizimi (Vikipedi'de ağaç şekli).
  Sonuç: "Recurse Right: / I N O R S T A E G L M P X / Merge: / A E G I L M N O P R S T X".
- Sorun 2 (kendi hatam): R3, sayfanın sondan ikinci satırındaki içerik sayısını da sayfa
  numarası sandı. Alıştırma 32'deki dizinin son elemanı "9" silinmişti. Ölçüm: gerçek
  sayfa numarası her zaman sayfanın son satırı ve kitap boyunca sabit bir farkla ilerliyor
  (PDF sayfası − basılı numara). R3 artık yalnızca bu numaralamaya uyan sayıları siliyor;
  önceki kural 13 içerik sayısını silmişti. Dizi şimdi tam: `9 ▲ 7 7 2 ▲ 1 3 7 5 ▲ 4 7 ▲ 3 ▲ 3 4 8 ▲ 6 9`.

Doğrulama: 31 birim testi geçiyor (iki yeni test bu iki durum için). Temiz corpus'ta boş
doküman, sayfa ayırıcı ve çözülemeyen karakter yok. Önce/sonra örneklerini yeniden ürettim:
`_before` dosyaları `data/extracted`, `_after` dosyaları `data/cleaned` ile bayt bayt aynı.

## 14.10.2026 — FAZ 4 öncesi son kontrol

- Extraction motor karşılaştırmasını güncel kodla (ligatür ve üst simge düzeltmelerinden sonra)
  yeniden çalıştırdım: PyMuPDF 24/24 başarılı, 7,72 sn, 12 çevrilemeyen karakter;
  pdfplumber 24/24, 58,39 sn, 590. Karar değişmedi: PyMuPDF.

## 14.10.2026 — FAZ 4: Filtreleme (kalibrasyon aşaması)

`scripts/04_filter.py`'yi yazdım. Her doküman için dil, gürültü oranı, alan skoru, alt konu,
karakter ve kelime sayısı hesaplanıyor. Eleme sırası planladığım gibi: too_short → wrong_language →
too_much_noise → out_of_domain. Elle bulduğum 4 kapsam dışı madde out_of_domain olarak, gerekçesiyle
eleniyor.

Registry'ye yazmadan önce bütün dokümanlarda kuru çalıştırma yaptım. Bulduğum ve düzelttiğim sorunlar:

1. 4 Türkçe Vikipedi maddesi İngilizce tespit edildi (A* arama algoritması, Sayarak sıralama,
   Saçma sıralama, Yığın sıralaması). Sebep: maddeler Türkçe ama İngilizce kod bloklarıyla dolu
   (A*'da 1.490 karakterin 1.057'si kod). Dili artık yalnızca düzyazı satırlarından tespit ediyorum.
   Sonuç: 68 Türkçe maddenin 68'i Türkçe; kaynak listesiyle çelişen doküman yok.
2. Alan skoru: İngilizce listede "sort" yoktu, "Cascade merge sort" gibi sıralama maddeleri 0 puan
   alıyordu. Listeye DSA'nın çekirdek terimlerini ekledim (sort, search, hash, node, vertex,
   complexity, arama, düğüm, O( gösterimi …). Türkçede "ağaç" kalıbı "ağacı"yı yakalamıyordu
   (ünsüz yumuşaması); "ağac" kökünü ekledim.
3. Alt konu: Yalnız gövde sayımı Erickson'ın Recursion, Backtracking, Dynamic Programming ve Greedy
   bölümlerini "agaclar" yapıyordu ("tree" her yerde geçiyor). Artık önce başlığa, sonra gövdeye
   bakıyorum. Açgözlü / geri izleme / böl-yönet için `algoritma_paradigmalari` alt konusunu ekledim;
   "spanning tree"yi graflar'a ekledim. 51 atama değişti, tek tek baktım; çoğu düzelme.
   Sınırlılık: kural tabanlı; "Topological sorting" sıralama, "Heap's algorithm" ağaçlar sayılıyor.

Kuru çalıştırma sonuçları (eşik yokken): 17 doküman too_short (12'si Türkçe Vikipedi taslağı),
4 doküman elle out_of_domain. Gürültü oranı her yerde %0,4'ün altında; %15 sınırı kimseyi elemiyor.

Kalibrasyon: `reports/calibration_domain.csv`, 487 aday içinden alan skoru çeyreklerine göre
tabakalı 50 doküman. Eşiği etiketlerden belirleyeceğim.

Kabul testinin ikinci yarısını geçici bir kopyada deneme eşiğiyle (30) çalıştırdım: --limit 50,
2 doküman out_of_domain olarak exclusions.csv'ye düştü; gerçek registry değişmedi. Not: deneme
eşiği Erickson'ın Introduction ve Greedy bölümlerini eledi; eşiğin etiketle belirlenmesi şart.

## 19.10.2026 — FAZ 4: Kalibrasyon ve filtreleme sonucu

Etiketleme: 50 kalibrasyon dokümanını etiketledim. Ölçüt README'deki kapsam tanımı: konusu lisans düzeyi Veri
Yapıları ve Algoritmalar mı (1) değil mi (0). İleri düzey ama konusu veri yapısı/algoritma olan
dokümanları alan içi saydım. Her etiketin gerekçesini `reports/calibration_domain.csv` dosyasının
`label_note` sütununa yazdım; belirsiz beş dokümanın tam metnini okudum.

Sonuç: 49 alan içi, 1 alan dışı (Pivot eleman: çoğunluğu Gauss eliminasyonu, yani sayısal
lineer cebir; hızlı sıralamaya tek paragraf).

Eşik tablosu (`reports/calibration_domain_report.md`): en iyi sonuç 49/50; 0 ile 9,9 arasındaki
her eşikte alınıyor. Alan dışı doküman (skor 25,6), alan içi dört dokümandan daha yüksek skorlu
(Lineer zaman 9,9; Charging argument 20,4; Multimap 20,8; List ADT 23,6). Onu skorla yakalamak
en az 4 alan içi dokümanı da eler. Örneklem dışındaki en düşük skorlu 12 dokümanı da okudum;
hepsi alan içi (en düşüğü Özyineleme, 2,71).

Karar: `domain_score_threshold: 2.5`. Bu corpus'ta skorla elenen doküman yok. Eşik, ileride
eklenebilecek alakasız metne karşı güvenlik ağı. Pivot eleman'ı kalibrasyon etiketine dayanarak
elle kapsam dışı listesine ekledim. Gerekçe (sunum için): kaynakları elle ve kapsam tanımına göre
seçtiğim için alan dışı içerik büyük ölçüde baştan engellendi; anahtar kelime skoru bu durumda
ayırt edici değil.

Filtreleme (önce `--limit 50`, sonra kalanlar; ikinci tekrar hiçbir şey işlemedi):

- 608 temiz dokümandan 586'sı geçti, 22'si elendi: 17 too_short (12'si Türkçe Vikipedi
  taslağı), 5 out_of_domain (hepsi elle incelediklerim: T-tree, Log-structured merge-tree, Free list,
  Extendible hashing, Pivot eleman). too_much_noise ve wrong_language: 0.
- Dil: 431 İngilizce, 55 Türkçe, 100 kod. Türkçe pay karakter bazında %2,8.

| Kaynak | Doküman | Karakter | Kelime | Pay |
| --- | --- | --- | --- | --- |
| İngilizce Vikipedi | 396 | 4.325.554 | 715.626 | %68,5 |
| Erickson — Algorithms | 10 | 676.941 | 119.641 | %10,7 |
| Open Data Structures | 14 | 397.483 | 72.872 | %6,3 |
| TheAlgorithms/Python | 100 | 389.291 | 45.541 | %6,2 |
| An Open Guide to DSA | 11 | 347.244 | 60.976 | %5,5 |
| Türkçe Vikipedi | 55 | 175.253 | 23.463 | %2,8 |
| Toplam | 586 | 6.311.766 | 1.038.119 | |

Alt konu dağılımı: ağaçlar 152, sıralama ve arama 121, graflar 88, diziler ve listeler 67,
yığın ve kuyruk 40, hash tabloları 40, özyineleme ve DP 26, karmaşıklık analizi 26,
algoritma paradigmaları 13, genel 13.

Erime (şimdiye kadar): 609 ham → 608 extraction → 608 temizleme → 586 filtreleme.

## 19.10.2026 — FAZ 5: Tekrar ayıklama (deduplication)

Yöntem (`scripts/05_deduplicate.py`):

- Exact: normalize metnin (küçük harf, Türkçede İ/I kuralıyla; boşluklar teke) SHA-256'sı.
- Near: kelime 5-gram shingle, MinHash (128 permütasyon) + LSH ile aday çift; adayları gerçek
  Jaccard ile doğruluyorum, eşiği geçenleri union-find ile kümeliyorum. Kodda shingle boşlukla
  bölünmüş token'dan.
- Kümede kalan: `source_priority` sırası, sonra uzun metin, sonra küçük `document_id`.

Neden MinHash + Jaccard: kopya tanımım "aynı metin" olduğu için kelime dizisi örtüşmesini ölçüyorum.
Embedding benzerliği aynı konudaki farklı maddeleri (ör. Binomial heap / Pairing heap) de benzer
bulurdu; rehber §8'in uyardığı yanlış silme bu. MinHash + LSH bütün çiftleri karşılaştırmadan aday
buluyor; corpus büyüdüğünde de çalışır.

Ölçüm: 586 dokümanın en az bir ortak shingle'ı olan bütün çiftlerini ters indeksle tek tek hesapladım
(tahmin değil, gerçek Jaccard). En yüksek değer 0,2607 (randomized_heap.py / skew_heap.py). Exact
grup 0, Jaccard ≥ 0,60 çift 0. LSH (aday eşiği 0,5) de 0 aday verdi; tam hesapla tutarlı.

Kalibrasyon: Planladığım 0,60–0,95 aralığında çift olmadığı için örneklemi aralığın altındaki
en benzer 50 gerçek çiftle doldurdum (`reports/calibration_dedup.csv`, `pool` sütunu). Her çiftte
başlığı, ilk 300 karakteri ve ortak shingle'ları okudum; 50'si de farklı içerik (0). Benzerliğin
kaynakları:

- TheAlgorithms dosyalarının ortak kalıbı (docstring, doctest, `__main__` girişi).
- Vikipedi'nin birden çok maddede tekrarlanan bölümleri (yığın türleri karmaşıklık tablosu, join
  tabanlı küme işlemleri bölümü).
- Ortak sözde kod (Kabarcık / Kokteyl sıralaması).
- Kokteyl sıralaması / Cocktail shaker sort: aynı konu, farklı dil. Ortak kısım yalnızca sözde kod
  (Jaccard 0,049).

Gerçek çiftlerde farklı içerikli hiçbir çift 0,30 ve üstü eşikte silinmiyor (0,20'de 1 yanlış silme).

Kontrollü değişiklik deneyi (`reports/calibration_dedup_report.md` §2): seed'li 20 düzyazı + 10 kod
dokümanının kopyasını bilinen biçimde değiştirdim. 0,85'te yakalananlar (düzyazı / kod):

| Değişiklik | Yakalanan |
| --- | --- |
| Sona kaynak satırı | 20/20, 10/10 |
| Başa ve sona site menüsü | 20/20, 8/10 |
| %5 satır silme | 18/20, 8/10 |
| %10 satır silme | 15/20, 1/10 |
| %20 satır silme | 1/20, 0/10 |
| %1 kelime değişikliği | 20/20, 9/10 |
| %3 kelime değişikliği | 0/20, 0/10 |

Karar: `jaccard_threshold: 0.85`'i korudum. 0,85 "aynı metnin küçük farklarla kopyası" tanımına
karşılık geliyor: eklenmiş kaynak/menü satırı ve ~%5 eksik satır yakalanıyor; %20 ve daha çok farklı
metin, yeni içerik taşıdığı için tutuluyor. Gerçek verideki en benzer farklı çiftle (0,26) arada geniş
pay var. Bu corpus'ta 0,27 ile 1 arasındaki her eşik aynı sonucu veriyor; eşik sonradan eklenecek
kaynaklar için.

`source_priority`: open_guide_dsa, erickson_algorithms, open_data_structures, vikipedi_tr,
wikipedia_en, thealgorithms_python. Önce ders kitapları: tek yazarlı, editörlü, ders düzeyinde
anlatım ve CC BY (CC BY-SA'nın "aynı lisansla paylaş" yükümlülüğü yok). Kitaplar arasında HTML olan
Open Guide önde (PDF çıkarım izi yok), sonra Erickson (CC BY 4.0), sonra ODS (CC BY 2.5 CA). Vikipedi'de
Türkçe önde, çünkü Türkçe pay az. Bu corpus'ta kopya olmadığı için sıra sonucu değiştirmedi.

Çalıştırma: `--limit 50` (50 deduped), sonra tamamı: 586 işlendi, 586 kaldı, 0 elendi. İkinci
çalıştırma registry'yi değiştirmedi (byte düzeyinde aynı). `data/raw`'a dokunulmadı (sha256 609/609).
Testler: 47 geçti (`tests/test_dedup.py` 8 test).

Bilinen sınırlılıklar (Dataset Card için):

- Doküman düzeyinde dedup paragraf düzeyindeki tekrarı silmiyor. Vikipedi'nin ortak bölümleri ve
  TheAlgorithms'in kalıp kodu birden çok dokümanda kalıyor.
- Diller arası çeviri (Türkçe madde, İngilizce maddenin çevirisi) kelime örtüşmesiyle bulunamaz.

Neden kopya çıkmadı: kaynakları elle seçtim. Her kaynakta başlıklar tekrarsız. Kitapları aynı
PDF'ten bölüm bölüm aldım ve sayfa aralıkları çakışmıyor (registry'de 22 tekrar eden URL bu
bölümler; URL + sayfa aralığı tekrarsız). TheAlgorithms'te her dosya ayrı bir algoritma.

Erime (şimdiye kadar): 609 ham → 608 extraction → 608 temizleme → 586 filtreleme → 586 exact dedup
→ 586 near dedup.

## 19.10.2026 — FAZ 6 öncesi denetim (Vize Rehberi'ne karşı)

FAZ 6'ya geçmeden önce yaptıklarımı rehberin bölümlerine karşı yeniden kontrol ettim. Üç sorun buldum ve
düzelttim:

1. `--redo` tutarsızdı. 02 ileri adımlara geçmiş dokümanları yeniden işliyordu, 03 ve 04 işlemiyordu
   (ör. dedup'tan sonra 04'ü yeniden çalıştırmak 586 dokümanı yeniden filtrelemezdi). Artık her adımın
   `--redo`'su, o adıma ulaşmış bütün dokümanları işliyor: ileri adımlara geçmiş olanlar ve o adımda ya
   da sonrasında elenmiş olanlar dahil. Kural tek yerde (`scripts/utils/registry.py`, `reached`), testi
   `tests/test_registry.py`'de.
2. R6'nın kelime sözlüğü "excluded" durumundaki bütün dokümanları dışarıda bırakıyordu. Temizlik ilk
   çalıştığında filtre henüz yoktu, yani o gün sözlükte 22 doküman daha vardı; temizliği yeniden
   çalıştırmak farklı sözlükle çalışmak olurdu. Artık yalnızca temizlikten önce elenenler dışarıda.
3. Metadata (rehber §9): `publication_year` Vikipedi ve kod dokümanlarında boştu (551 doküman).
   Vikipedi'de indirdiğim sürümün son düzenleme yılını ham sayfanın alt bilgisinden okuyorum ("This page
   was last edited on 10 August 2026", "Sayfa en son … 8 Mayıs 2024 tarihinde değiştirildi"); 473
   sayfanın 473'ünde var. Yıl dağılımı (final 451 madde): 2020: 1, 2021: 2, 2022: 2, 2023: 5, 2024: 32,
   2025: 76, 2026: 333. TheAlgorithms için dosya bazında tarih yok (yalnızca commit `3935d28` kayıtlı);
   bu 100 dokümanda yıl boş kalıyor, tahmin etmiyorum.

Yeniden üretim testi: 02 `--redo` → 03 → 04 → 05 baştan çalıştırdım. `data/extracted` ve `data/cleaned`
altındaki 1.218 dosyanın 1.218'i bayt bayt aynı; temizlik raporu, kurallar raporu, 40 önce/sonra örneği
ve near_duplicates aynı; extraction raporu (süre sütunu hariç) aynı. Registry'de değişen tek sütun
`publication_year`. Eleme kayıtları: 23 (1 extract too_short, 17 filter too_short, 5 out_of_domain).
Testler: 50 geçti.

## 19.10.2026 — FAZ 6: Train / validation / test ayrımı

Yöntem (`scripts/06_split.py`): ayrımı doküman düzeyinde yapıyorum (rehber §10): bir dokümanın bütün
metni tek kümeye düşüyor. Chunk'lama bu fazda yok; instruction tarafında, ayrımdan sonra yapılacak.
Dokümanları kaynağa göre grupluyorum, her kaynağı kendi seed'iyle (`42:<kaynak>`) karıştırıp oranlara
göre bölüyorum. Böylece her kaynak her kümede var ve bir kaynağa doküman eklemek diğerlerinin atamasını
değiştirmiyor. Validation ve test sayısı yukarı yuvarlanıyor; 10 bölümlük kitap da 8/1/1.

Neden 80/10/10 (rehber 90/5/5'i "yaygın" diye veriyor, oranların değişebileceğini söylüyor): corpus
küçük (586 doküman). 90/5/5 ile test 31 doküman olurdu, Türkçe test dokümanı 3; 80/10/10 ile test 59,
Türkçe 6. Final döneminde modeli ölçerken test kümesinin çok küçük olması sonucu güvenilmez yapar.
Teslim ettiğim proje önerisi de 80/10/10 diyor.

Sonuç:

| Kaynak | Train | Validation | Test |
| --- | --- | --- | --- |
| İngilizce Vikipedi | 316 | 40 | 40 |
| TheAlgorithms/Python | 80 | 10 | 10 |
| Türkçe Vikipedi | 43 | 6 | 6 |
| Open Data Structures | 12 | 1 | 1 |
| An Open Guide to DSA | 9 | 1 | 1 |
| Erickson — Algorithms | 8 | 1 | 1 |
| Toplam | 468 | 59 | 59 |

Karakter payı: train %81,2, validation %8,8, test %10,0. Validation'daki kitap bölümleri: Erickson
"Introduction", ODS "Heaps", Open Guide "Dynamic Programming"; test'tekiler: Erickson "Greedy
Algorithms", ODS "Scapegoat Trees", Open Guide "Recursion". 10 alt konunun 9'u üç kümede de var;
"genel" (13 doküman) testte yok.

Doğrulama: 586 kaydın 586'sı tek dosyada (sızıntı yok); her kaydın `split` alanı dosyasıyla ve
registry'yle aynı; her `text` alanı `data/cleaned` dosyasıyla birebir aynı; boş metin, eksik
kaynak/URL/lisans 0. Kümeler arası en benzer doküman çifti bile Jaccard 0,26'yı geçmiyor (FAZ 5 ölçümü
bütün corpus için). İkinci çalıştırma üç JSONL'i ve registry'yi bayt bayt aynı üretti. Testler: 55
geçti (`tests/test_split.py` 5 test).

`token_count` bu fazda boş (null); FAZ 7'de tokenizer ile doldurulacak.

Erime: 609 ham → 608 extraction → 608 temizleme → 586 filtreleme → 586 exact dedup → 586 near dedup
→ 586 final (468 / 59 / 59).

## 19.10.2026 — FAZ 7: Token sayımı ve istatistik raporu (Corpus v0.9)

Tokenizer: final döneminde CPT/SFT için Qwen3 ailesini seçtim; `Qwen/Qwen3-4B-Base` tokenizer'ı
(rehber §10'daki örnekle aynı). Sürümü config'te sabitledim (revision `906bfd4`), başka bilgisayarda
da aynı sayılar çıksın. Yalnızca tokenizer dosyaları indi, model ağırlıkları değil. Sayım özel token
eklenmeden (`add_special_tokens=False`).

Sonuç (`reports/token_stats.json`):

| Küme | Doküman | Toplam token | Medyan | Ortalama | P95 | Max |
| --- | --- | --- | --- | --- | --- | --- |
| Tümü | 586 | 1.553.153 | 1.612 | 2.650 | 8.770 | 33.500 |
| Train | 468 | 1.261.090 | 1.691 | 2.695 | 8.736 | 33.500 |
| Validation | 59 | 135.865 | 1.355 | 2.303 | 7.327 | 11.909 |
| Test | 59 | 156.198 | 1.347 | 2.647 | 9.430 | 16.071 |

- 80.000 token'dan uzun doküman yok; en uzunu 33.500 token (Erickson bölümü). Chunk'lama eğitimde
  sequence length'e göre yapılacak (rehber §10: vizede kesinleşmesi zorunlu değil).
- Dil (token): İngilizce %89,5, kod %6,8, Türkçe %3,7. Türkçe pay karakterde %2,8, token'da %3,7:
  tokenizer Türkçeyi daha çok parçaya bölüyor (karakter/token: İngilizce 4,13, Türkçe 3,05;
  token/kelime: İngilizce 1,43, Türkçe 2,45).
- Kaynak payı (token): İngilizce Vikipedi %65,7, Erickson %11,5, ODS %7,3, TheAlgorithms %6,8,
  Open Guide %4,9, Türkçe Vikipedi %3,7. İstatistik raporu %50 sınırını aşan kaynak için uyarı yazıyor;
  bu payın gerekçesi (kitapların kapsamadığı konu çeşitliliği ve corpus hacmi, açık lisanslı Türkçe DSA
  metninin azlığı) Dataset Card'da yer alacak.

İstatistik raporu (`scripts/08_statistics.py` → `reports/statistics.md` ve `.json`): rehber §12'nin
özet tablosu, erime tablosu, eleme sebepleri, kaynak / dil / alt konu / split dağılımları ve token
istatistikleri. Rapor yazılmadan önce sayılar çapraz kontrol ediliyor: registry'deki elemeler ile
`exclusions.csv` aynı mı, ham − elenen = final mi, JSONL'deki dokümanlar registry'deki final
dokümanlarla aynı mı, token toplamı `token_stats.json` ile aynı mı. Tutarsızlık olursa rapor yazılmıyor.
Instruction ve manuel kontrol satırları FAZ 8 ve 9'da dolacak.

Örnek veri (rehber §13): `data/samples/` altına her split'ten seed'li 3 kısa kayıt (en çok 8.000
karakter) yazdım; depoya bunlar girecek, büyük dosyalar girmeyecek. Kaynakların lisansları (CC BY,
CC BY-SA, MIT) atıfla yeniden dağıtıma izin veriyor; her kayıtta `url` ve `license` var.

Doğrulama: 07 ve 08 ikinci kez çalıştırıldığında JSONL'ler, registry, token_stats, statistics ve örnek
dosyaları bayt bayt aynı. Testler: 60 geçti (`tests/test_statistics.py` 5 test: erime sayımı, eksik
eleme kaydının ve JSONL'de olmayan dokümanın yakalanması).

Sürüm: v0.9.

## 19.10.2026 — FAZ 8 hazırlığı: öğretmen model erişimi

Gemini API anahtarımı (Google AI Studio, ücretsiz katman) `.env` dosyasına ekledim; `.env` `.gitignore`
içinde. Anahtarın gördüğü modelleri listeledim (generateContent destekleyen 46 model) ve beş adaya tek
cümlelik Türkçe bir deneme isteği gönderdim ("Bağlı liste nedir?"):

| Model | Sonuç |
| --- | --- |
| gemini-2.5-flash (config'teki) | 404: yeni kullanıcılara kapalı, API gemini-3.8-flash'ı öneriyor |
| gemini-2.5-flash-lite | 404: yeni kullanıcılara kapalı |
| gemini-2.5-pro | 404: yeni kullanıcılara kapalı |
| gemini-3.5-flash | çalışıyor, 4,0 sn, doğru ve akıcı Türkçe |
| gemini-3.8-flash | çalışıyor, 4,4 sn, doğru ve akıcı Türkçe |

İki çalışan model de cevaptan önce düşünme token'ı kullanıyor (bu kısa soruda 448–556).

Ücretsiz katman sınırları (AI Studio → Rate Limit sayfası, 19.10.2026):

| Model grubu | Dakikada istek | Günde istek |
| --- | --- | --- |
| Gemini 3 / 3.6 / 3.7 / 3.8 Flash | 5 | 20 |
| Gemini 3.1 Flash Lite, 3.5 Flash Lite | 15 | 500 |

Hesap: 3.000 örnek için yaklaşık 3.000 üretim + 3.000 yargıç isteği (elenecekler için fazladan üretim
de gerekecek). Flash modelleriyle günde 20 istek bu işe yetmez. Flash Lite modelleriyle iki ayrı kota
(2 × 500/gün) kullanılabiliyor.

İki Lite modeli de denedim ("İkili arama ağacında iki çocuklu düğüm nasıl silinir?"): ikisi de doğru
(halef / selef düğümle değiştirme) ve akıcı Türkçe cevap verdi, 1,3–1,5 sn, düşünme token'ı yok.

Karar: üretici `gemini-3.5-flash-lite`, yargıç `gemini-3.1-flash-lite`. Farklı modeller seçmemin iki
nedeni var: her birinin kendi günlük kotası var ve yargıç, kendi ürettiği cevabı değerlendirmiyor.
Dakikalık sınırı 12'de tuttum (sınır 15). Günlük kota dolunca üretim duruyor, ertesi gün kaldığı yerden
devam ediyor. Lite modeller daha küçük olduğu için kaliteyi 20 pilot örnekte ölçeceğim; yetersiz
çıkarsa hedef sayıyı gerekçesiyle düşürmeyi değerlendireceğim (rehber §11 gerekçeli daha az örneğe izin
veriyor). Faturalandırma açmıyorum; üretim ücretsiz katmanda kalacak.

## 19.10.2026 — Corpus düzeltmeleri (instruction pilotunda bulundu)

Pilot örneklerini kaynak passage'larla karşılaştırırken corpus'ta iki sorun buldum ve kökünden düzelttim:

1. Kaynakça satırları: 27 İngilizce ve 1 Türkçe Vikipedi maddesinde "- ↑ Landau, E. (1924) …" biçiminde
   363 dipnot satırı kalmıştı (corpus'un %0,85'i). FAZ 3'te "8 maddede kaynakça sonda kaldı" diye
   kaydetmiştim; asıl kalan bunlar: R8 kaynakça başlığından keserken başlıktan önceki ("Notes" altındaki)
   dipnotlara dokunmuyordu. Pilotta bu satırlardan "Landau'nun 1924 çalışması nedir?" gibi işe yaramaz
   sorular çıktı. R8'e ekledim: '↑' ile başlayan dipnot satırları silinir. '↑' corpus'ta yalnızca bu
   satırların başında geçiyor (363/363). Doğrulama: her değişen dokümanın eski hâlini yeniden ürettim ve
   satır satır karşılaştırdım; 33 dokümandan tam 363 '↑' satırı silindi, başka hiçbir satır değişmedi.
2. HTML üs ve indisleri: Vikipedi üsleri ve indisleri çoğu zaman formül olarak değil `<sup>`/`<sub>`
   etiketiyle yazıyor; trafilatura etiketi atınca "2ⁿ" → "2n", "x³" → "x3", "log₂" → "log2" oluyordu
   (pilotta "test sayısı 2n'e düşer" cümlesi). 271 sayfada 714 sınıfsız `<sup>` ve 2.370 sınıfsız `<sub>`
   var. PDF'te yaptığım gibi TeX gösterimiyle yazıyorum: "2^n", "log_2", "x_{i+1}". Dipnot ("[1]") ve
   şablon ("[citation needed]") işaretleri sınıflı etiketler; onlara dokunulmuyor. Doğrulama: 216 dosya
   değişti, 3.134 işaret eklendi; işaretler çıkarılınca 215'i eski metinle bayt bayt aynı. Kalan 1 dosyada
   (Pancake graph) fark bir kazanç: trafilatura'nın önceden attığı "The γ(P_n) genus of P_n is:"
   satırı artık geliyor. Open Guide (HTML) da düzeldi: "O(n^2)", "F_{n−1}".

Bu iki düzeltmeden sonra 02 → 08 baştan çalıştı. Elemeler, dedup ve split aynı kaldı (586 final,
468/59/59). Yeni toplamlar: 6.259.618 karakter, 1.029.967 kelime, 1.535.759 token (medyan 1.596, p95
8.321, max 33.500). İngilizce Vikipedi'nin token payı %65,3, Türkçe pay %3,7. Dedup kalibrasyon
CSV'sindeki 11 çiftin Jaccard değeri küçük ölçüde değişti (ortak dipnot satırları gitti); değerleri
güncelledim, etiketler aynı kaldı. Bütün çiftlerde en yüksek Jaccard hâlâ 0,2607; 0,85 kararı değişmedi.
Testler: 72 geçti.

## 19.10.2026 — FAZ 8a: Instruction üretim altyapısı ve pilot

Passage bölme (`scripts/utils/chunking.py`): 250–700 token, yalnızca satır sonlarından kesiliyor. HTML'de
her satır bir paragraf; PDF'te cümle sonları ve bölüm başlıkları; kodda boş satırlar (fonksiyon arası)
tercih ediliyor. Sonuç: 2.885 passage, medyan ~570 token. Parçalar birleştirilince metin aynen geri
geliyor; yalnızca 30 dokümanın sonundaki 125 token'dan kısa artıklar soru üretimine alınmıyor.

Planlayıcı (`scripts/09_generate_instructions.py`): 3.000 × 1,15 = 3.450 görev (doğrulamada elenecekler
için %15 fazla). Görev türü yalnızca uygun passage'a veriliyor: kod okuma ve hata bulma art arda en az 3
kod/sözde kod satırı olan passage'a (Vikipedi formül satırları kod sayılmıyor), karmaşıklık analizi
karmaşıklıktan söz edene, algoritma izleme adım adım anlatılan bir algoritma/işlem içerene. Kaynakça
ağırlıklı passage'lar planlanmıyor. Doküman başına en çok 40 görev; with_context oranı tam 0,40. Aynı
passage'ın görevleri tek istekte üretiliyor (en çok 3): 1.180 istek, günde 500 istekle yaklaşık 2,5 gün.
bilgi_yetersizligi'nin yarısı (104) alan dışı sorular (22 tohum konudan; işletim sistemi, veritabanı iç
yapısı ve NP-tamlık ispatları da var), yarısı passage'da cevabı olmayan sorular.

Prompt'lar (`config/prompts/`): ortak kurallar (`_common.md`) + 10 görev türü dosyası, her birinde
kurallar ve doğru bir örnek (rehber Hafta 5: her tür için örnek). Stack/heap karışmasın diye "yığıt
(stack)", "yığın (heap)" zorunlu.

Pilot dört turda olgunlaştı (her turda 20 örnek, toplam 40 istek):

| Tur | Bulgu | Düzeltme |
| --- | --- | --- |
| 1 | LaTeX'li passage'da model JSON'u bozdu (`\log` kaçışsız) | API'den şemaya bağlı yapılandırılmış çıktı istiyorum |
| 1 | Kaynakça listesinden "Landau kimdir?" soruları | Corpus'tan dipnot satırları silindi; kaynakça ağırlıklı passage planlanmıyor |
| 1 | İzleme görevi izleme değil; "yığıt (heap)" terim hatası; tanımı passage'da olmayan kavram | Prompt'lar sıkılaştırıldı |
| 2 | Sözde kod Python'a çevrilirken hata girdi (dilim kuralı) | Kod içerikteki dilinde kalıyor |
| 2 | "Metinde yok" sorusunun yarısı metinde vardı, cevap çelişkiliydi | Alt tür kuralları netleştirildi |
| 3 | Bir istek hatasız ama boş yanıt döndü | Boş yanıt geçici hata sayılıp yeniden deneniyor |
| 3 | `\text` JSON'da TAB+"ext" oldu (`\t` geçerli kaçış) | Matematik ters bölüsüz yazılıyor; kontrol karakteri içeren çıktı reddedilip yeniden üretiliyor |
| 4 | 17 iyi, 2 zayıf, 1 kötü (hata eklenmemiş hata bulma sorusu) | FAZ 8b doğrulamasına bırakıldı |

Son pilot (`reports/instruction_pilot.md`): 20 örnek, 9 görev türü + alan dışı alt türü; kontrol
karakteri ve ters bölü 0. İzlemeleri ve kod çıktılarını elle hesapladım (Gosper i=2 → T_0; IDA* yol
kontrolü hatası).

Kabul testleri (FAZ 8):
- API anahtarı yokken: "GEMINI_API_KEY bulunamadı …" mesajıyla duruyor, kayıt yazmıyor.
- `--limit 20`: 20 ham kayıt (`data/instruction/generated_raw.jsonl`, her istekten sonra append + fsync).
- Kesinti: süreç üretimin ortasında zorla öldürüldü (5 kayıt yazılmıştı); yeniden çalıştırınca yalnızca
  eksik 15 kayıt üretildi; üçüncü çalıştırma 0 istek. Yinelenen anahtar yok, yarım satır yok.

Kota: bugün 40/500 istek kullanıldı. Testler: 72 geçti.

## 19.10.2026 — FAZ 8b: Tam üretim başladı, doğrulama ve derleme

Pilotu ve prompt'ları onayladım, tam üretimi başlattım (`reports/logs/generation_day1.out`). Günlük 500
istekle üç günde biter; kota dolunca script duruyor, ertesi gün kaldığı yerden sürüyor.

Öğretmen ve yargıç modelin ortak istemcisini (kota, bekleme, yeniden deneme, istek günlüğü)
`scripts/utils/llm.py`'ye taşıdım; 09'un davranışı değişmedi.

`scripts/10_verify_instructions.py` — kontroller bu sırayla, ilk takılan sebep kodu yazılıyor:

| Aşama | Sebep kodu | Ne yakalar |
| --- | --- | --- |
| auto_check | schema_error | eksik alan, kaynaksız passage örneği, kaynaklı alan dışı örnek |
| auto_check | too_much_noise | U+FFFD / kontrol karakteri, gürültü oranı > 0,15 (corpus'la aynı ölçü) |
| auto_check | too_short / too_long | talimat 8–800, cevap 40–1.200 Qwen3 token dışında |
| auto_check | invalid_json_quiz | geçersiz JSON, A–D dışında ya da aynı şık, geçersiz doğru şık |
| auto_check | wrong_language | talimat ya da cevabın kod dışı kısmı Türkçe değil |
| auto_check | task_mismatch | bağlamsız talimat ders içeriğine atıf yapıyor; hata bulma talimatında kod yok ya da kod içeriğin birebir kopyası |
| auto_check | duplicate_instruction | talimat kelime kümesi Jaccard ≥ 0,90 (MinHash aday + gerçek Jaccard); bağlamlıda yalnızca aynı passage |
| judge | not_grounded / judge_rejected / task_mismatch | yargıç model kararı |

Uzunluk sınırlarını ilk 179 kayda bakarak koydum: cevaplar 59–520, talimatlar 12–231 token. Sınırlar
bilerek geniş; doğal uzunluk farkını değil, yarım kalmış ya da kontrolden çıkmış çıktıyı yakalamak için.
Planladığım listeye iki sebep kodu ekledim: too_much_noise (rehber §12: bozuk karakter oranı) ve
task_mismatch (örnek görev türünün biçimine uymuyor).

Otomatik kontrolleri ilk 294 kayıtta çalıştırıp elenenlerin hepsini tek tek okudum:
- "Metne atıf yapan bağlamsız talimat" 6 örnek, 6'sı gerçekten hatalı ("Ders içeriğinde verilen ağaç
  üzerinde…" — öğrenci içeriği görmüyor). "metin" kelimesini tek başına aramıyorum: dizgi eşleme
  konusunda "bir metinde deseni ara" geçerli bir soru.
- Hata bulma: ilk denemede "kodun bütün satırları içerikte var" kuralı 6 örneği eledi, 5'i yanlıştı. Hata
  satır silerek, iki satırın yerini değiştirerek ya da içerikte başka yerde geçen bir satırı yazarak
  konunca da bütün satırlar içerikte bulunuyor. Kuralı "kod, içerikteki bir bölümün satırı satırına
  kopyası" olarak değiştirdim; kalan tek örnek gerçekten hata konmamış örnekti. Kod bloğu olmayan iki
  "hata bulma" örneği de gerçekten kavram sorusuydu.
- Dil tespiti ilk hâliyle cevapların 120/328'ini hiç değerlendirmiyordu: Türkçe düzyazıdaki ";" satırı kod
  saydırıyordu. Artık yalnızca kod blokları, satır içi kod, girintili satırlar ve kod anahtar kelimesiyle
  başlayan satırlar çıkarılıyor. Bir Türkçe talimat "ca" (Katalanca) çıktı: parantez içindeki İngilizce
  terimler kısa metni yanıltıyordu. Parantez içi terimleri dil tespitinden çıkarıyorum ve Türkçe olasılığı
  en az 0,20 ise metni Türkçe sayıyorum. İngilizce bir cevap hâlâ "en" olarak yakalanıyor (testte var).
- Talimat tekrarı: 2 çift, ikisi de birebir aynı soru.

Yargıç: `gemini-3.1-flash-lite`, temperature 0, prompt `config/prompts/judge.md`. Her örnek için önce kısa
gerekçe, sonra supported / answers_instruction / task_type_ok / states_limit / answer_in_passage alanları.
Aynı passage'ın örnekleri tek istekte yargılanıyor; alan dışı örnekler 10'arlı gruplar hâlinde. Kararlar
`data/instruction/judge_results.jsonl`'de saklanıyor (model ve prompt özetiyle); script yeniden
çalışınca aynı karar için istek atmıyor.

Yargıcı önce elle değerlendirdiğim 20 pilot örnekte denedim: 19'unda kararı benimkiyle aynıydı (kötü #2 ve
tür uyumsuz #13 reddedildi, 17 iyi örnek kabul edildi). Kaçırdığı #17 somut girdisi olmayan bir
izlemeydi. Bütün izleme örneklerine (37) bakınca sorun yaygındı: üçte birinde somut girdi yok, biri
tıp stajyeri yerleştirmesinin tarihçesi hakkında. Yargıç prompt'unda izleme tanımını netleştirdim (somut
değerler + her adımda ara durum; sözde kod satırlarını sırayla anlatmak izleme değil). Sonra:
- Pilot: 20/20 benim kararımla aynı.
- Girdisi somut olmayan 15 izleme: 15'i reddedildi.
- Talimatı somut 22 izleme: 18'i kabul, 4'ü reddedildi. Dördünü okudum: biri gerçek hesap hatası
  (bubble sort'ta "5 ve 2 yer değiştirir", doğrusu 5 ve 1), biri izleme sayılmayacak kadar yüzeysel
  (clone), ikisi sınırda (splay ağacı ve Scheme izlemesi ara durumu göstermiyor). Yargıç sınırda
  örnekte reddetme yönünde; rehber §12'ye uygun ("kaynakla doğrulanamayanı çıkarın").

Üretim prompt'unu üretimin ortasında değiştirmedim; değiştirseydim setin içinde iki prompt sürümü
karışırdı. İzleme türünde elenme oranı yüksek olacak; bütün yargı bittikten sonra tür bazında açığı
ölçüp eksik türler için ek üretim planlayacağım.

Üretim sürerken yargıç kotasını boşa harcamamak için yargıcı `--judge-only` ile çalıştırıyorum: yalnızca
karar topluyor, `reports/exclusions.csv`'ye dokunmuyor (09 da o dosyaya yazıyor; iki script aynı anda
değiştirmesin). Eleme kayıtları üretim bittikten sonra tek çalıştırmada yazılacak.

`scripts/11_build_instruction_dataset.py`: her örnek kaynak dokümanının corpus split'ini alıyor (aynı
dokümandan gelenler tek kümede, corpus test dokümanından üretilen örnek train'e girmiyor); kaynağı olmayan
alan dışı örnekler 06'daki seed'li oran fonksiyonuyla dağıtılıyor. id'ler anahtar sırasıyla INS_00001'den.
Derleme sonunda sızıntı ve id kontrolü yapıyor, yargıç kararı bekleyen örnek varsa derlemeyi reddediyor.
`instruction_{train,validation,test}.jsonl` SFT biçiminde (messages); bağlamlı örnekte kullanıcı
mesajı "Ders içeriği:\n{passage}\n\n{talimat}".

`08_statistics.py`'ye instruction için erime tablosu (planlanan → üretilen → otomatik kontroller → yargıç
→ manuel kontrol → final), sebep kodları, tür bazında planlanan/elenen/final, token dağılımı ve
model/prompt özeti ekledim. Bütün zinciri (10 → 11 → 08 → 12 → 13) gerçek dosyalara dokunmadan bir kopya
üzerinde uçtan uca denedim. Bu denemeden önce 10'u iki kez gerçek dosyada çalıştırmıştım; o
çalıştırmaların `exclusions.csv`'de bıraktığı 12 eski satırı 08'in "aynı örnek iki kez elenmiş"
kontrolü yakaladı, sildim.

FAZ 9 araçlarını da hazırladım (12 örneklem, 13 kalite raporu, `run_all.py`). Rehber §12'deki sorulara
göre planladığım sütunlara iki sütun ekledim: corpus'a no_broken_chars ("bozuk karakter var mı"),
instruction'a answers_instruction ("cevap talimatı gerçekten karşılıyor mu"). 12, doldurulmaya başlanmış
CSV'nin üzerine yazmıyor.

Testler: 90 geçti.

## 19.10.2026 — Benzer açık veri setleri (rehber Hafta 1)

Kaynak araştırmasında (12.10) metin kaynaklarına bakmıştım, hazır veri setlerine bakmamıştım. Bu açığı
kapattım. Bulduklarımın sayfalarını açıp içerik ve lisansı kontrol ettim:
- CLRS-Text (arXiv 2406.04229, 2024): 30 klasik algoritma için yürütme izi üreten araç, İngilizce, hazır
  veri değil üretici kod. İzleme görevime en yakın çalışma ama yalnızca sabit biçimli iz.
- CodeAlpaca-20k: 20.022 İngilizce kod talimatı (CC BY 4.0), genel programlama.
- InstrucTurca: ~2,58 milyon Türkçe talimat, İngilizce setlerin makine çevirisi (CC BY-SA 4.0), genel amaçlı.
- MMLU college_computer_science (116 soru, MIT) ve Türkçe çevirisi mmlu-tr (113 soru, Apache-2.0):
  değerlendirme seti. TurkishMMLU'da bilgisayar bilimi konusu yok (9 lise dersi).

Sonuç: Türkçe, DSA'ya özel ve kaynağa izlenebilir açık bir instruction seti bulamadım; projenin
dolduracağı boşluk bu. MMLU college_computer_science / mmlu-tr, final dönemindeki "modelimiz başarılı mı?"
sorusu için kendi test kümelerimin yanında dış bir ölçüt olabilir (rehber §11). README'ye tablo olarak
ekledim.

## 20.10.2026 — Ara ölçüm ve ek üretim planı

Yargıç sabah 09:20–09:38 arasında 503 hatası almadan çalıştı (dün akşam 21:00 sonrasında, ABD'de iş
saatlerinde, 68 kez "model yoğun" hatası alıp yavaşlamıştı). Ana üretimin ilk 1.568 örneğinin yargısı
bitince her türün doğrulamadan geçme oranını ölçtüm (dosyaya yazmadan, bellekte):

| Tür | Geçme oranı | Bu oranla tahmini final | Hedef |
| --- | --- | --- | --- |
| algoritma_izleme | %48,5 | ~201 | 360 |
| hata_bulma | %80,4 | ~222 | 240 |
| karmasiklik_analizi | %88,2 | ~304 | 300 |
| diğer yedi tür | %93–98 | hedefin üstünde | |

Toplam tahmin ~3.050, yani hedefi tutuyor; ama izleme payı %12 yerine ~%6,6 kalıyordu. Geçme oranını
passage türüne göre ayırdım:

| Passage | İzleme | Hata bulma |
| --- | --- | --- |
| Kod dosyası (TheAlgorithms) | %76 | %100 |
| Kod bloklu metin | %43 | %73 |
| Düzyazı | %36 | — |

Karar: Ana plana dokunmadan ek plan (`config.instruction.top_up`): 280 izleme, 30 hata bulma. Ek görev,
ana planda o türü almamış passage'a veriliyor; önce kod dosyalarına, sonra kod bloklu metne. Gerçek
passage'larla deneme: ana plan birebir aynı (3.450 anahtar), 310 ek görev (izleme 113 kod dosyası + 167
kod bloklu metin, hata bulma 30 kod dosyası), 286 istek. Beklenen: izleme ~360'a, hata bulma ~250'ye
çıkar. Ek görevler ana planın arkasından üretiliyor. Testler: 91 geçti.

## 20.10.2026 — Ağ hataları örnek eletmesin

Yargıcın bugünkü çalışmasında 27 hata kaydı oluştu: 503 "model yoğun" (7), sunucunun bağlantıyı kesmesi (5),
DNS çözülememesi (5), bağlantı zaman aşımı (5), bağlantının sıfırlanması (3) ve benzerleri. Hepsi bağlantı
ya da sunucu kaynaklı. Betik bunları "yargıç geçerli karar vermedi" denemesi sayıyordu; aynı örnekte iki
kez olsaydı örnek, kendisinde kusur olmadığı hâlde judge_rejected ile elenecekti (8 örnek bir denemesini
böyle harcamıştı, elenen olmadı). Üretimde de aynı mantık vardı (oradaki 18 hatanın hepsi modelin bozuk
çıktısıydı, ağ hatası yoktu).

Düzeltme (`scripts/utils/llm.py`, 09, 10): ağ hataları da beklenip aynı çalıştırmada yeniden deneniyor;
yeniden denemelere rağmen kalan API/ağ hatası `kind: api_error` olarak kaydediliyor ama deneme sayılmıyor,
örnek sonraki çalıştırmada yeniden deneniyor. Eski kayıtlar sınıf adından ("ConnectError: ...") tanınıyor.
Kontrol: 27 yargıç hatasının 0'ı, 18 üretim hatasının 18'i deneme sayılıyor. Testler: 92 geçti.

## 22.10.2026 — Otomatik kontrollerin bütün sette gözden geçirilmesi

19.10'da otomatik kontrollerin elediklerini ilk 600 kayıtta okumuştum; üretim 3.730 kayda çıkınca hepsine
yeniden baktım. "Çok kısa" ile elenen 7 örneğin hepsi gerçekten hatalı: yarıda kesilmiş cevap ("…tüm",
"..."), hata bulma etiketli "Euler hangi yılda?" sorusu. "Yanlış dil" ile elenen 3 örnekten ikisi doğru,
biri yanlıştı: Türkçe bir Viterbi talimatı, içine gömülü Python sözlükleri (`{"Healthy": 0.6, ...}`)
yüzünden İngilizce sayılmıştı. Dil tespitinden önce tırnak içindeki dizgileri ve `[...]`, `{...}`
değerlerini çıkarıyorum.

Doğru elenen iki örnek başka bir sorunu gösterdi: Türkçe karakter kullanmadan yazılmış Türkçe
("Baslangicta dizi ... dongu calisir"). Dil tespiti bunu çoğunlukla Türkçe sayıyor. Bütün sette 15 cevap ve
16 talimat böyle, çoğu izleme örneği. Türkçe cevap verecek bir model için kötü örnek; model yanlış yazmayı
öğrenir. Kural: 60 harften uzun Türkçe düzyazıda hiç ç/ğ/ı/ö/ş/ü yoksa wrong_language. Yakaladığı 17
örneğin hepsini okudum, hepsi bu biçimde ("sutunlar", "dugum", "Yukaridaki metne gore"); ayrıca
"Yukaridaki" yazılışı metne atıf kontrolünü de atlatıyordu. Testler: 93 geçti.

## 22.10.2026 — FAZ 8b sonucu: Instruction Dataset derlendi

Üretim 4 günde bitti (19–22.10; ücretsiz katman, günde 500 istek): 3.760 görevden 3.757 örnek; 3 görev iki
denemede de geçersiz çıktı verdi (generation_error). Yargıç ABD iş saatlerinde sık sık 503 "model yoğun"
hatası aldı; Türkiye saatiyle sabah erken saatlerde hiç almadı. Oturum kapanınca arka plandaki işler
iki kez durdu; resume sayesinde kayıp olmadı.

Doğrulama (`10_verify_instructions`, tam çalıştırma): 3.757 → otomatik kontroller 128 eledi (task_mismatch
92, wrong_language 20, too_short 8, duplicate_instruction 8) → yargıç 366 eledi (task_mismatch 147,
judge_rejected 140, not_grounded 79) → 3.263 örnek.

Derleme (`11_build_instruction_dataset`): train 2.630 / validation 309 / test 324. Her örnek kaynak
dokümanının corpus split'inde; sızıntı kontrolü ve `run_all` bütünlük kontrolleri temiz. with_context
%40,7. Örnek başına token medyanı 300, en çok 1.293; toplam 1.447.785.

Tür dağılımı ek planla hedefe yaklaştı: algoritma_izleme %11,7 (hedef %12; ek plan olmasaydı ~%7),
hata_bulma %7,6 (hedef %8), kavram_aciklama %18,4 (hedef %18), bilgi_yetersizligi %6,2 (alan dışı 101,
metinde yok 100). Hedef 3.000'in üstünde.

Final setten rastgele 5 örneği okudum: bisect_left izlemesi elle doğruladım, alan dışı ret iyi; bir
karmaşıklık sorusu cevabı soruda veriyor (zayıf, yargıç geçirmiş), bir cevapta yazım hatası ("Tetratin").
Yargıcın kaçırdığı zayıf örneklerin oranını FAZ 9'daki 200 örneklik manuel kontrol ölçecek.
Testler: 93 geçti.

## 22.10.2026 — Corpus manuel kontrolü ve v1.0 düzeltmeleri

`scripts/12_sample_for_manual_qc.py` corpus'tan kaynağa göre tabakalı 150 doküman seçti (seed 42; Vikipedi
EN 89, kod 26, Vikipedi TR 16, ODS 7, Erickson 6, Open Guide 6). Her dokümanın okuma dosyasını (metadata,
metnin başı, ortası, sonu) okuyup altı kontrolü işaretledim; her 0 için nedenini not ettim. Bu ilk tur v0.9
metni üzerindeydi (`reports/manual_qc_corpus_round1.csv`):

| Kontrol | Başarılı |
| --- | --- |
| readable | 150/150 |
| in_domain | 150/150 |
| extraction_ok | 135/150 |
| header_footer_clean | 139/150 |
| no_broken_chars | 145/150 |
| metadata_ok | 123/150 |
| hepsi | 98/150 (%65,3) |

Hataları türlerine ayırıp her birinin corpus genelindeki büyüklüğünü ölçtüm, sonra pipeline'ı düzelttim:

| Bulgu (örneklemde) | Corpus genelinde ölçüm | Düzeltme |
| --- | --- | --- |
| Yanlış alt konu (27 doküman): "Yığın sıralaması" → yigin_ve_kuyruk, "Recurrence relation" → yigin_ve_kuyruk, "Knapsack problem" → diziler | Eski kural örneklemde 123/150 doğru | Başlıkta en sonda biten eşleşme kazanır (Türkçe ve İngilizce tamlamada asıl ad sondadır); parantezli açıklama atılır; kod dosyasında klasör yolu kullanılır ("sorts/", "dynamic_programming/"); genel kelimeler ("search", "list") yalnızca başlıkta sayılır; listelere alanın terimleri eklendi (`config/subtopics.yaml`). Örneklemde 146/150. Örneklem dışında alt konusu değişen 64 dokümanın hepsine baktım; "Heapsort" → sıralama, "Levenshtein distance" → DP, "Master theorem" → karmaşıklık gibi |
| PDF'te sayfa başlığı kalıntısı: pseudocode ortasında "DualArrayDeque: Building a Deque from Two Stacks", paragraf ortasında "8.7. Relax ALL the Edges: Bellman-Ford" | R4 eşiği (5 sayfa) birkaç sayfalık bölümlerin başlığını yakalamıyordu | R4'e iki kalıp: sayfa üstünde "§2.1" varsa yanındaki satır; sayfanın ilk satırı "8.3. Başlık" biçimindeyse (gerçek bölüm başlığı numarayı ayrı satıra yazıyor). 174 satır silindi; hepsini okudum, hepsi bölüm adı; gerçek başlıklar ("2.7 / Discussion and Exercises") korunuyor |
| Satır sonu tiresi birleşmemiş ("inte-\|gers", "op-\|erations") | PDF kitaplarında 100 yer | R6'nın kod koruması yalnızca yapısal kod işaretlerine bakıyor (girinti, kod anahtar kelimesi, ←, :=, ==); "{0,...,2^w −1}" ya da "remove()" içeren düzyazı artık kod sayılmıyor. 86 birleşmenin hepsi doğru; kalan 13 yer gerçek kod işareti içeriyor |
| Vikipedi'de kayıp listeler ("Examples of addressable heaps include:" sonrası boş) | ':' ile biten paragraftan sonraki listelerin 25/507'si kayıp | Liste öğelerindeki bağlantılar düz metne çevriliyor (trafilatura bağlantı yoğun blokları atıyordu). 10/507'ye indi |
| Vikipedi'de kayıp ya da girintisi bozuk kod (Batcher odd–even mergesort, Overlapping subproblems; İkili arama ağacı'nın Python kodu girintisiz) | Renklendirilmiş kod blokları ve kod içeren düzen tabloları (9 maddede 40 tablo) | Renklendirilmiş bloklar düz metne çevriliyor (satır numaraları atılıyor); içinde kod olan tablolar hücre hücre açılıyor. 14 maddede kod geri geldi ya da girintisi düzeldi, 9 maddede tablolardaki kod geldi (AVL tree, Binary search tree, Recursion, Trie ...); eklenen satırların hepsi kod |
| Formül parçası kayıp: "O(√)" | 22 sayfada {{radic}} şablonu, 34 boş kök | Kök altı ifade korunuyor ("√n", çok parçalıysa "√(n log n)"). 34 → 1 |
| Kaynak işaretleri ("örneğidir.[1]", "[4]:459", "[citation needed]") | Corpus'ta 6.505 işaret | Çıkarımda siliniyor (gösterdikleri kaynakça zaten R8'de kesiliyor). Kalan 280 "[n]" eşleşmesi dizi indisi (A[1], a[9]), içerik |
| Sonda kalan kaynakça/See also (6 doküman) | 17 maddede "See also", 44 ISBN satırı | R8: başlıktan sonra künyeye benzemeyen en çok 2 uzun satır varsa da kesiliyor; düzyazının önünde "History" gibi bir içerik başlığı varsa kesilmiyor (Segment tree korunuyor). Yeni kesilen 32 maddenin kesilen kısımlarını okudum, hepsi kaynakça/bağlantı/not |
| Telaffuz kalıntısı "trie (//, // ⓘ)" | 4 madde | Boş telaffuz parantezi ve "(//," kalıntısı siliniyor. Kalan 1: "deque — // DEK)"; genel bir kural koddaki "//" yorumlarını bozabileceği için dokunmadım |

Ayırmada bir kırılganlık da çıktı: liste düzeltmesinin bir ara aşamasında bir doküman ("Algorithmic paradigm")
eşiği geçip corpus'a girince İngilizce Vikipedi'nin 117 dokümanı küme değiştirdi; grup listesi seed'le
karıştırılıyordu. `06_split.py` artık her dokümanı kimliğinin seed'li özetine göre sıralıyor (baştan test,
sonra validation, kalanı train): bir doküman eklemek ya da çıkarmak yalnızca sınırdaki bir iki dokümanı
yer değiştirtir (testi var). Final dönemde corpus büyüse de test kümesi kararlı kalır. Bu değişiklik
kümeleri bir kez yeniden dağıttı.

Corpus v1.0 (02 → 08 baştan): 586 doküman (aynı sayı; "Algorithmic paradigm" listeleri gelince 500
karakteri geçti, "Derin öncelikli arama" kaynak işaretleri ve "Ayrıca bakınız" listesi gidince 480 karaktere
indi ve too_short ile elendi), 1.028.018 kelime, 1.512.566 token, 470/58/58. Türkçe doküman 55 → 54
olduğu için Türkçe test kümesi 6'dan 5'e indi. Bütün çiftlerde en yüksek Jaccard hâlâ 0,2607; dedup eşiği
kararı değişmedi (kalibrasyon CSV'si v0.9 metniyle, değerler yakın).

İkinci tur: aynı 150 dokümanı v1.0 metniyle yeniden okudum (12 `--refresh-corpus` aynı listeyi korur).
İlk turda 0 aldığım her kontrol için düzelip düzelmediğine baktım; metni değişen diğer dokümanlarda
kaynak işareti silinmesi dışındaki her farkı okudum:

| Kontrol | 1. tur (v0.9) | 2. tur (v1.0) |
| --- | --- | --- |
| extraction_ok | 135 | 144 |
| header_footer_clean | 139 | 149 |
| no_broken_chars | 145 | 146 |
| metadata_ok | 123 | 146 |
| hepsi | 98 (%65,3) | 135 (%90,0) |

Kalan 15 hata: PDF şekil etiketlerinin metne dökülmesi (3), Erickson'un glif kodlamasından bozuk aksan ve süs
glifi (2), alt konu (4: "Introduction", "Algoritma" gibi genel maddeler ve iki yanıltıcı başlık), veri tablosu
kaybı (1, tablolar kapsam dışı), örnek değer kaybı (1), dipnotun paragrafa karışması (1), kaynak sayfadaki
anlamsız karakter (1), kenar kutusu yazısı (1), telaffuz kalıntısı (1). Testler: 94 geçti.

## 22.10.2026 — Instruction manuel kontrolü

`scripts/12_sample_for_manual_qc.py` final setten görev türüne göre tabakalı 200 örnek seçti (seed 42; her türden
en az 5). Her örnekte talimatı, cevabı ve örneğin üretildiği passage'ı okudum; beş kontrolü işaretledim, her 0
için nedenini not ettim (`reports/manual_qc_instruction.csv`). İzleme ve hesap içeren cevapları elle yeniden
hesapladım (ör. sırt çantası tablosu, insertion sort ve cocktail sort adımları, master teoremi). Bir hata bulma
örneğinde "hatalı" ve "düzeltilmiş" kodu kendi yazdığım küçük bir testle 39 dizi × 210 değerde çalıştırdım:
sonuçlar aynıydı, yani konan değişiklik hata değildi.

| Kontrol | Başarılı |
| --- | --- |
| instruction_clear | 192/200 |
| response_correct | 186/200 |
| grounded_in_source | 189/200 |
| answers_instruction | 194/200 |
| task_type_ok | 184/200 |
| hepsi | 157/200 (%78,5; %95 güven aralığı %72,3–%83,6) |

Hata türleri (başarısız 43 örnek, her örnek ana hatasına göre bir kez sayıldı):

| Hata türü | Örnek | Not |
| --- | --- | --- |
| Cevap yanlış | 14 | 7 olgu hatası (ör. Bellman–Ford'un ulaşılamayan negatif döngüyü de bulduğu, WAVL'ın AVL koşuluyla tanımlanması), 4 hata bulma (biri hiç hata konmamış koda hata uyduruyor), 3 izleme (sonuç doğru ama adımlar yanlış, ya da bir eleman atlanmış) |
| Hata bulmada hatanın yeri talimatta | 6 | "heap1 boş olduğunda yanlış sonuç veriyor" gibi: öğrencinin bulacağı bir şey kalmıyor |
| Bağlamsız talimat görünmeyen metne dayanıyor | 6 | "bu veri yapısının", "verilen bilgilere göre"; metni görmeyen öğrenci cevaplayamaz |
| Görev türüne uymuyor | 6 | karşılaştırma etiketli kavram sorusu, soru isteyen talimata çoktan seçmeli soru üretilmesi |
| Kaynağa dayanmayan ek | 5 | 2'sinde talimattaki kod kaynaktan bozuk kopyalanmış (bir satırda "×" yerine "−", tekrarlanan "return") |
| Eksik ya da yüzeysel cevap | 3 | "neden" sorusuna totolojiyle cevap |
| Yanıltıcı talimat | 3 | yanlış önkabul ("neden uygundur"), yanlış belirti |

Cevabı yanlış örnek oranı %7 (14/200; %95 güven aralığı %4,2–%11,4): yargıç modelin geçirdiği hatalı cevap
oranının tahmini. Görev türlerinde en zayıf hata bulma (16 örnekten 5'i her kontrolden geçti): hatayı talimatta
söyleme ve var olmayan hata uydurma bu türde toplanıyor. bilgi_yetersizligi 14/14, kavram_aciklama 28/33.

Örnek 141'de bir şey daha fark ettim: passage'ta "iki skorlama matrisi ailesi var:" cümlesinden sonra liste yok,
oysa v1.0 corpus'ta liste (PAM, BLOSUM) geri geldi. Instruction örneklerini v0.9'un passage'larından ürettiğim
için v1.0 düzeltmeleri passage'lara yansımadı. Ölçtüm: 1.319 farklı passage'ın 613'ü v1.0 metninde birebir
(boşluk farkı hariç) geçiyor, 430'unun tek farkı silinen kaynak işaretleri, 262'si %90'dan fazla aynı. Biri
(DOC_000239'un kaynakça bölümü, "See also / Notes / References" listesi) v1.0'da tamamen silinmiş; buna dayanan
2 bağlamlı örnek (B-tree'nin kaynakçasından soru ve iki yayını "karşılaştırma") yayımlanan corpus'a dayanmıyor.
Kural: passage'ın 5 kelimelik dizilerinden kaynak dokümanın v1.0 metninde bulunanların oranı 0,25'in altındaysa
örnek not_grounded ile (aşama build) çıkar. En düşük iki değer 0,019 ve 0,487, arası boş; eşik yalnızca bu
passage'ı ayırıyor. Satır bazında ölçmeyi de denedim, olmadı: uzun paragrafta tek bir "√" düzelmesi bütün
satırı farklı sayıyor (0,26 çıkan passage'ın tek farkı buydu). Set 3.263 → 3.261.

Kod okuma örneklerinde talimattaki kodun passage'ın birebir kopyası olup olmadığını da ölçtüm: 335 örneğin
187'sinde değil. Okuduklarımın çoğu meşru: yorumlar atılmış, kod kısaltılmış, bağlamsız örnekte model kendi
kodunu yazmış. Bozuk kopyayı bunlardan ayıran basit bir kural bulamadım; Instruction Card'a bilinen problem
olarak yazdım.

`13_qc_report` corpus için iki turu (v0.9 ve v1.0) yan yana yazıyor. Raporu kendi adımla çalıştırınca
başarısız 43 örnek manual_rejected ile setten çıkacak, 157'si manuel onaylı olacak. Testler: 96 geçti.

## 22.10.2026 — Çoktan seçmeli sorularda doğru şık dengesi

Instruction Card için sayıları çıkarırken çoktan seçmeli soruların doğru şıklarını saydım: 403 sorunun 244'ünde
doğru şık B, 79'unda A, 68'inde C, yalnızca 12'sinde D. Bu setle eğitilen model "emin değilsen B" kalıbını
öğrenir. Öğretmen modelin prompt'unda şık dağılımı hakkında bir kural yoktu.

Düzeltme derlemede (`11_build_instruction_dataset`): her soru için hedef harf, anahtarın seed'li özetinden
seçiliyor (bir örnek eklemek ya da çıkarmak diğerlerinin hedefini değiştirmiyor). Doğru şık o harfteki şıkla
yer değiştiriyor, açıklamadaki şık atıflarında ("B şıkkı doğrudur", "A, C ve D şıkları") iki harf karşılıklı
değişiyor. Önce açıklamalarda harflerin nasıl geçtiğini saydım: çoğu "X şıkkı / X seçeneği", ama harf içerik
olarak da kullanılıyor ("A matrisi", "D böleni", "A[j]", "B-ağaçları", "minimum kesim C'den"). Soruda ya da
şıklarda tek başına harf geçen, ya da açıklamasında şık atfı olmayan bir harf bulunan sorulara dokunulmuyor
(29 soru). "ilk şık", "son seçenek" gibi sıra atfı hiç yok.

Sonuç: 281 soru taşındı, doğru şık A 89 / B 122 / C 104 / D 88. Taşınan her soruda yeni doğru şıkkın metninin
eski doğru şıkla aynı olduğunu ve şık kümesinin değişmediğini programla denetledim (281/281); altısını baştan
sona okudum, açıklamalar yeni harflerle tutarlı. Manuel kontrolde okuduğum örneklerin harfleri de bu yüzden
CSV'dekinden farklı olabilir; içerik aynı. Testler: 98 geçti.

## 22.10.2026 — Kalite raporu ve teslim hazırlığı

`13_qc_report`'u kendi adımla çalıştırdım: corpus 135/150, instruction 157/200 onay, 43 ret. İlk denemede
sanal ortamı etkinleştirmeyi unuttuğum için sistem Python'u kullanıldı; rapor yazıldı ama 11, sistemdeki
uyumsuz `transformers` / `huggingface_hub` sürümleri yüzünden tokenizer'ı yükleyemedi. 11 ve 08'i sanal
ortamda çalıştırdım: Instruction Dataset v1.0 3.218 örnek (2.584 / 325 / 309), `run_all --check-deliverables`
temiz. README'ye sanal ortam uyarısı ekledim.

Depoda veri dosyaları olmadığı için `data/samples/`'a her görev türünden bir instruction örneği ekledim
(08 yazıyor; seed'li, 400 token'dan kısa). On örneği okudum; hepsi doğru (izlemeyi elle kontrol ettim).

Veri paketi (Rehber §13: büyük veri depoya girmez, yeri README'de): `data/final/` ve `data/instruction/`
(17 dosya, 49 MB) tek zip'te, 10,6 MB, içinde SHA256SUMS.txt; GitHub Releases'e `v1.0` olarak yüklenecek.
Ham veri (111 MB) paylaşılmıyor; manifest ve indirme günlüğüyle yeniden indirilebiliyor.

## 22.10.2026 — Instruction etiketlerinin ikinci okuması

Sunumdan önce 200 örneği, özellikle onayladığım 157'sini baştan bir kez daha okudum; izleme ve kod çıktılarını
yeniden hesapladım. İki tür tutarsızlık buldum ve 6 etiketi değiştirdim (`reports/manual_qc_instruction.csv`,
notlarda "ikinci okumada düzelttim"):

- **Küçük kusur değil, yanlış bilgi (3):** ilk turda "küçük kusur" diye geçtiğim cümleler aslında yanlış bilgi
  veriyordu. Bağlı liste sorusunun açıklaması yanlış şıkları "bağlı listelerin avantajları" sayıyor
  (DOC_000146:0); Kirkpatrick–Reisch sorusunun açıklaması A şıkkını yanlış anlatıyor (DOC_000378:3); library sort
  izlemesi hiçbir elemanın kaymadığı örnekte "birkaç eleman kaydırılır" diyor (DOC_000415:0).
  Ölçüt: açıklamada ya da izlemede yanlış bir ifade varsa response_correct = 0; yalnızca terim, yazım ya da
  üslup kusuru varsa 1.
- **Hata bulmada aynı ölçüt (3):** ilk turda hatanın yerini talimatta veren örnekleri çıkarmıştım ("heap1 boş
  olduğunda", "minn ve maxx değerlerini yanlış atıyor"), ama aynı durumdaki üç örneği onaylamışım: "is_full()
  metodu yanlış sonuç veriyor" ve kod yalnızca o satır (DOC_000072:1), "boş liste kontrolünde beklenen sonuç
  yanlış ele alınıyor" (DOC_000059:0), "tablonun boyutunu ayarlarken" (DOC_000015:0). Üçünde de task_type_ok = 0.

Çıkardığım 43 örneğin sınırda olanlarını da yeniden okudum; hiçbirini geri almadım.

Yeni sonuç: hepsi başarılı 151/200 (%75,5; %95 güven aralığı %69,1–%80,9), cevap doğru 183/200, görev türüne
uygun 181/200; cevabı yanlış oranı %8,5 (17/200; %5,4–%13,2). Hata bulma 16 örnekten 2'si. 13'ü yeniden
çalıştırınca set 3.218 → 3.212 (2.579 / 324 / 309). Örnek id'leri anahtar sırasıyla verildiği için kaydı;
Instruction Card'daki format örneğinin id'sini (INS_01643) ve kartlardaki sayıları güncelledim. `data/samples/`
içindeki iki örnek değişti (çoktan seçmeli ve hata bulma); ikisini de passage'la karşılaştırdım, doğru.

## 26.10.2026 — Temiz kopyada yeniden üretim testi

Rehber §19'daki "pipeline baştan sona yeniden çalıştırılabilir mi?" sorusunu denemeden cevaplamak istemedim.
Depoyu GitHub'dan boş bir klasöre klonladım; yanına yalnızca depoda olmayan ham veriyi (`data/raw/`) ve
Releases'teki zip'in `data/instruction/` klasörünü koydum. Zip'in 17 dosyası SHA256SUMS ile doğrulandı.

İlk denemede sorun çıktı: depodaki `data/registry.csv` dokümanları işlenmiş (final) olarak gösteriyor, ara
dosyalar (`data/extracted/`, `data/cleaned/`) ise depoda yok. 02 "işlenecek doküman yok" deyip geçti, 03 var
olmayan ara dosyayı açmaya çalışıp durdu. `--redo` ile çalıştırınca sorun kalmadı. Düzeltme: `run_all`
çalışmadan önce registry'de işlenmiş görünen ama ara dosyası diskte olmayan doküman var mı diye bakıyor; varsa
02–04'ü kendiliğinden `--redo` ile çalıştırıyor (`missing_intermediates`, testi `tests/test_run_all.py`).

Sonuç (düzeltilmiş `run_all`, ardından API anahtarı olmadan 10, 11, 08):

| Dosya | Releases'teki dosyayla |
| --- | --- |
| `train.jsonl`, `validation.jsonl`, `test.jsonl` | bayt bayt aynı |
| `instruction_v1.0.jsonl`, `instruction_{train,validation,test}.jsonl` | bayt bayt aynı |
| `reports/statistics.md`, `statistics.json` | aynı |
| `reports/exclusions.csv`, `extraction_report.csv` | yalnızca zaman sütunlarında (timestamp, seconds) farklı |

Erime yine 609 → 608 → 586. Ham dosyalar diskte olduğu için 01 hiçbir siteye istek atmadı (indirme günlüğü
değişmedi), 10 yargıç kararlarını dosyadan okudu. 01 `.env`'de iletişim adresi olmadan çalışmıyor; bu bilinçli
(README'de yazıyor). Kurulu paketler `requirements.txt` ile aynı sürümde, `pip check` temiz.

Bir açık daha kapattım: `run_all --check-deliverables` manuel kontrol tablosunun dolu olup olmadığına
bakıyordu ama kararların veri setine yansıyıp yansımadığına bakmıyordu. 22.10'daki ikinci okumada 6 etiketi
değiştirdiğimde denetim yine "hepsi tamam" dedi, oysa o 6 örnek hâlâ setteydi. Şimdi onaylanan her örneğin
sette ve `verified_by=manual` olduğunu, reddedilen her örneğin sette olmadığını da denetliyor
(`manual_review_problems`); 13 yeniden çalıştırılmadan bu 6 örneği yakalıyor, 13'ten sonra temiz. Testler: 100 geçti.

Aynı gün README'ye "Değerlendirme planı" bölümünü ekledim: ayrılmış test kümeleri, karşılaştırılacak üç sistem
ve tasarım raporundaki ölçütler.

Sonra 13'ü ikinci okumanın etiketleriyle çalıştırdım. Set 3.218 → 3.212 (2.579 / 324 / 309), manuel onaylı 151,
manual_rejected 49; sayılar kartlara önceden yazdıklarımla aynı çıktı. `--check-deliverables` artık "hepsi
tamam" diyor, 100 test geçiyor. Instruction Card'daki kod okuma ölçümünü final sete göre yeniden yaptım: 332
örneğin 184'ünde talimattaki kod passage'ın birebir kopyası değil (22.10'daki 335/187, manuel kontrolden önceki
setti). Veri zip'ini yeni dosyalarla yeniden oluşturdum.

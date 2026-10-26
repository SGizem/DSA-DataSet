# DSA Domain Corpus v1.0

## Amaç

Bu veri seti, lisans düzeyindeki "Veri Yapıları ve Algoritmalar" dersi için Türkçe soru cevaplayan bir dil
modelinin continued pretraining (CPT) aşamasında kullanılmak üzere hazırlandı. Genel amaçlı bir corpus
değildir. Modelin Türkçe cevap vermeyi öğrenmesi ayrı bir veri setiyle (Instruction Dataset v1.0,
`INSTRUCTION_CARD.md`) sağlanıyor; bu corpus alanın kavramlarını, algoritmalarını ve kodunu taşıyor.

## Kapsam

Kapsam içi: diziler ve bağlı listeler, yığıt (stack) ve kuyruk, hash tabloları, ağaçlar (ikili arama ağacı,
AVL, kırmızı-siyah, yığın (heap), trie), graflar ve graf algoritmaları, sıralama ve arama, karmaşıklık
analizi, özyineleme ve dinamik programlama, algoritma paradigmaları.

Kapsam dışı: işletim sistemleri, veritabanı iç yapısı, bilgisayar ağları, kriptografi, ileri algoritma
teorisi (NP-tamlık ispatları gibi), sayısal lineer cebir.

## Veri kaynakları

| Kaynak | Tür | Dil | Ham doküman | Final doküman | Lisans |
| --- | --- | --- | --- | --- | --- |
| İngilizce Vikipedi (elle seçilmiş maddeler) | HTML | en | 405 | 397 | CC BY-SA 4.0 |
| TheAlgorithms/Python | Kod (Git) | Python | 100 | 100 | MIT |
| Türkçe Vikipedi (elle seçilmiş maddeler) | HTML | tr | 69 | 54 | CC BY-SA 4.0 |
| Open Data Structures — Pat Morin (bölüm bölüm) | PDF | en | 14 | 14 | CC BY 2.5 CA |
| An Open Guide to Data Structures and Algorithms — PALNI | HTML | en | 11 | 11 | CC BY 4.0 |
| Algorithms — Jeff Erickson (bölüm bölüm) | PDF | en | 10 | 10 | CC BY 4.0 |
| **Toplam** | | | **609** | **586** | |

Ders kitaplarını bölüm bölüm ayrı doküman olarak aldım: tek bir kitap tek doküman olsaydı split'te
tamamen bir kümeye düşerdi. Vikipedi maddelerini kategori sayfalarından aday çıkarıp tek tek açarak
seçtim (Türkçe: 121 adaydan 69). Kod dosyalarını beş dizinden seed'li rastgele 100 dosyayla sınırladım ki
corpus'un çoğunluğu kod olmasın. Seçim gerekçeleri `config/sources.csv` ve `experiments.md` içinde.

**Neden çoğunlukla İngilizce?** Açık lisanslı, ders düzeyinde Türkçe veri yapıları kaynağı bulamadım
(ticari olmayan lisanslı Türkçe ders notları ve lisansı belirsiz kaynaklar dışında). Türkçe içerik
yalnızca Türkçe Vikipedi'den geliyor ve token'ların %3,8'ini oluşturuyor. İngilizce metni alan bilgisi
için tutuyorum; hedef dil olan Türkçeyi Instruction Dataset taşıyor. Türkçe Vikipedi ayrıca Türkçe terim
karşılıklarının tek açık kaynağı.

## Veri toplama

Dokümanları 13 Ekim 2026'da `scripts/01_download.py` ile indirdim. HTML kaynaklarında robots.txt
kurallarına uydum (Vikipedi'de API yerine normal madde sayfaları), istekler arasında 2 saniye bekledim,
User-Agent'a iletişim adresi koydum. Git kaynağının commit'i ve seçilen dosyalar kaydedildi; sonraki
çalıştırmalar aynı dosyaları görür. İndirilen dosyalar `data/raw/` altında değiştirilmeden saklanıyor; her
dosyanın HTTP durumu, boyutu ve SHA-256'sı `reports/download_log.csv` içinde.

## İşleme adımları

- **Extraction:** PDF için PyMuPDF. 24 PDF dokümanında pdfplumber'la karşılaştırdım: ikisi de 24/24
  başarılı; PyMuPDF 7,7 sn'de 12 çevrilemeyen karakter, pdfplumber 58,4 sn'de 590 çevrilemeyen karakter
  verdi ve bazı kelimeleri birbirine yapıştırdı (`reports/engine_comparison.csv`). Taranmış PDF yok, OCR
  gerekmedi. HTML için trafilatura, kod dosyaları olduğu gibi. Kitapların fontlarında Unicode
  karşılığı olmayan matematik glifleri ve ligatürleri çözdüm; Vikipedi formüllerini ve üs/indisleri TeX
  gösterimiyle (`2^n`, `log_2`) yazdım. Manuel kontrolde bulduğum hatalardan sonra Vikipedi çıkarımına
  şunları ekledim: kaynak işaretleri (`[1]`, `[citation needed]`) siliniyor; bağlantılı liste öğeleri
  düz metne çevriliyor (trafilatura bağlantı yoğun listeleri atıyordu); renklendirilmiş kod blokları ve
  içinde kod olan düzen tabloları düz metne açılıyor (kayıp ya da girintisi bozuk kod geri geldi); kök
  işareti korunuyor (`O(√n)`); boş telaffuz parantezleri siliniyor. 1 doküman 200 karakterden kısa çıktığı
  için elendi.
- **Cleaning:** Unicode NFC (NFKC değil: `O(n²)` bozulmasın), kontrol karakterleri, sayfa numaraları,
  sayfa başlığı/altbilgisi (bölüm numaralı sayfa üstü başlıklar dahil), site menüsü, Vikipedi kaynakça
  bölümleri ve dipnotları, PDF'te parçalanmış şekil hücreleri, satır sonu tireleri, fazla boşluk. Kısa
  satırları silmedim: `BFS`, `O(n²)`, sözde kod satırları bilginin kendisi. Kurallar ve etkiledikleri
  doküman sayıları `reports/cleaning_rules.md`, 20 önce/sonra örneği `reports/cleaning_examples/` içinde.
  Temizlenen 608 doküman 7.428.646 karakterden 6.257.256 karaktere indi; silinen kısmın çoğu Vikipedi
  kaynakçaları.
- **Filtering:** 500 karakterden (kodda 150) kısa 17 doküman, alan dışı 5 doküman (Gauss eliminasyonu,
  veritabanı ve dosya sistemi indeksleme, işletim sistemi bellek yönetimi, veritabanı depolama motoru, ana
  bellek veritabanı indeksleri) elendi.
  Dil (tr/en) ve bozuk karakter oranı (%15) filtresine takılan doküman olmadı. Alan dışı içeriği 50
  dokümanı elle etiketleyerek kalibre ettim (`reports/calibration_domain_report.md`).
  500 karakter Rehber'deki örnek değer; sonradan elenen 17 dokümanı tek tek okuyarak kontrol ettim. Hepsi
  1–5 cümlelik taslak madde (12'si Türkçe Vikipedi, ör. "Kuyruk (veri yapısı)" 411, "Dizi (veri yapısı)" 477
  karakter); 16'sının konusu corpus'ta daha uzun bir dokümanda var (Queue, Array, Depth-first search ...),
  yalnızca "Kirkpatrick–Reisch sort" yok. Eşik keskin bir kalite sınırı değil: hemen üstünde kalan "Sabit
  zaman" (515) da kısa bir madde. Bedeli Türkçe metnin yaklaşık %2,6'sı (4.566 karakter). Kodda eşiği 150
  tuttum çünkü birkaç satırlık bir fonksiyon tam bir algoritma olabilir; en kısa kod dosyası
  (`factorial.py`) 585 karakter olduğu için bu eşik hiçbir dosyayı elemedi.
- **Deduplication:** Exact duplicate SHA-256 ile, near duplicate MinHash (128 permütasyon, 5 kelimelik
  shingle) + gerçek Jaccard ≥ 0,85 ile. Hiç tekrar bulunmadı: 586 dokümanın bütün çiftlerinde en yüksek
  Jaccard 0,26. Eşiği 50 çifti elle etiketleyerek ve kontrollü değişiklik deneyiyle (metne tek satır
  eklemek, %5 satır silmek 0,85'i aşıyor; %20 farklı metin aşmıyor) seçtim
  (`reports/calibration_dedup_report.md`).

Elenen her doküman sebep koduyla `reports/exclusions.csv` içinde (toplam 23).

## Format

JSONL, satır başına bir doküman. Alanlar: `document_id`, `title`, `source`, `url`, `license`, `language`,
`document_type` (ders_kitabi / ansiklopedi / kod), `publication_year`, `subtopic`, `split`, `char_count`,
`word_count`, `token_count`, `text`.

Alanları Rehber §9'daki örnekten aldım ve üç alan ekledim. `license`: Vikipedi kısmının CC BY-SA koşulu
doküman düzeyinde izlenebilsin diye. `split`: dosyadan bağımsız da hangi kümede olduğu görülsün diye.
`word_count`: Rehber kelime sayısını da raporlamayı istiyor. `source`, `url` ve `document_id` her metni
kaynağına bağlıyor: instruction örnekleri `source_document` ile bu kimliğe dönüyor; ileride RAG'de cevabın
kaynağını göstermek (raporda "yanlış cevaplarda kaynak sayfa") için de bu alanlar gerekiyor. `subtopic`
alt konu dağılımını, `language` dil dağılımını çıkarmak için.

## İstatistikler

| Ölçüt | Değer |
| --- | --- |
| Final doküman | 586 |
| Dosya boyutu: ham / final (3 JSONL, metadata dahil) | 114,6 MB (587 dosya) / 6,6 MB |
| Toplam karakter | 6.223.372 |
| Toplam kelime | 1.028.018 |
| Toplam token (Qwen3 tokenizer, `Qwen/Qwen3-4B-Base`) | 1.512.566 |
| Doküman başına token: min / medyan / ortalama / p95 / max | 106 / 1.564 / 2.581,2 / 8.143,5 / 33.370 |
| İngilizce / kod / Türkçe (token) | %89,3 / %7,0 / %3,8 |

Alt konu dağılımı (token): ağaçlar %21,2, sıralama ve arama %18,5, graflar %18,0, özyineleme ve DP %11,3,
diziler ve listeler %7,9, hash tabloları %6,7, karmaşıklık analizi %6,3, yığıt ve kuyruk %6,0, algoritma
paradigmaları %3,8, genel %0,1. Alt konu, başlıktaki terimle (Türkçe ve İngilizce tamlamada asıl ad sonda
olduğu için başlıkta en sonda biten eşleşme), başlıkta yoksa metindeki terim sayımıyla, kod dosyalarında
klasör yoluyla atanıyor (`config/subtopics.yaml`). Ayrıntılı tablolar: `reports/statistics.md`.

## Veri ayrımı

Doküman düzeyinde %80 train, %10 validation, %10 test (470 / 58 / 58 doküman), kaynağa göre tabakalı:
her kaynak, kitaplar dahil, validation ve testte en az bir dokümanla temsil ediliyor. Rehberdeki
%90/5/5 yerine 80/10/10 seçtim çünkü Türkçe doküman az: %5'lik test kümesinde 3 Türkçe madde kalırdı,
%10'lukta 5 kalıyor. Bölme `scripts/06_split.py` içinde seed 42 ile yapılıyor: her kaynakta dokümanlar
kimliklerinin seed'li özetine göre sıralanıyor, baştan test, sonra validation, kalanı train. Bir doküman
eklemek ya da çıkarmak yalnızca sınırdaki bir iki dokümanın kümesini değiştiriyor; final döneminde corpus
büyüse de test kümesi kararlı kalıyor. Bir dokümanın bütün metni tek kümede; instruction örnekleri de kaynak
dokümanının kümesini alıyor.

**Chunk'lar.** Corpus doküman olarak teslim ediliyor; CPT'de model bir seferde sınırlı sayıda token
(sequence length) gördüğü için uzun dokümanlar parçalara bölünecek. En uzun doküman 33.370, p95 8.143 token.
Parçaları rastgele karakter sayısından değil paragraf, başlık ve cümle sınırlarından keseceğim: kesilmiş bir
tanım ya da yarım kalmış bir sözde kod modele yanlış bir bütün öğretir. Aynı yöntemi instruction üretiminde
kullandım (`scripts/utils/chunking.py`, 250–700 token'lık passage'lar). Bölme doküman düzeyinde yapıldığı ve
chunk'lar ondan sonra oluşturulacağı için bir dokümanın parçaları farklı kümelere düşmüyor. Nihai uzunluk final
döneminde seçilecek modelin bağlam uzunluğuna göre belirlenecek.

## Lisans ve kullanım

Bütün kaynaklar açık lisanslı; kaynak bazında lisanslar yukarıdaki tabloda. Vikipedi'den gelen kısım CC
BY-SA 4.0 olduğundan bu kısmı içeren türetilmiş veri aynı lisansla paylaşılmalı. Veri seti akademik amaçla
hazırlandı. Kişisel veri içermiyor (ders kitabı, ansiklopedi ve açık kaynak kod).

## Kalite kontrolü

Kaynağa göre tabakalı 150 dokümanı (seed 42; Vikipedi EN 89, kod 26, Vikipedi TR 16, Open Data Structures 7,
Erickson 6, Open Guide 6) okudum; her dokümanda altı kontrolü (okunabilir, alan içi, extraction doğru,
başlık/altbilgi temiz, bozuk karakter yok, metadata doğru) işaretledim. İlk tur v0.9 üzerindeydi; bulduğum
hataları türlerine ayırıp corpus genelinde ölçtüm, pipeline'ı düzelttim ve aynı 150 dokümanı v1.0'da yeniden
okudum (`experiments.md`, 22.10.2026; `reports/quality_report.md`):

| Kontrol | 1. tur (v0.9) | 2. tur (v1.0) |
| --- | --- | --- |
| readable | 150 | 150 |
| in_domain | 150 | 150 |
| extraction_ok | 135 | 144 |
| header_footer_clean | 139 | 149 |
| no_broken_chars | 145 | 146 |
| metadata_ok | 123 | 146 |
| Hepsi başarılı | 98 (%65,3) | 135 (%90,0; %95 güven aralığı %84,2–%93,8) |

Kaynak bazında hepsi başarılı: kod 26/26, Open Guide 6/6, Vikipedi EN 83/89, Vikipedi TR 13/16, Open Data
Structures 5/7, Erickson 2/6. Kalan 15 hatanın listesi aşağıda ve raporda.

## Bilinen problemler

- Kaynak dağılımı dengesiz: token'ların %64,9'u İngilizce Vikipedi'den geliyor (istatistik raporu %50
  sınırında uyarı veriyor). Ders kitapları anlatım kalitesi için önemli ama sayıca az (35 bölüm).
- Türkçe içerik az (%3,8).
- PDF kitaplarda şekil etiketleri ve sayıları metne dökülmüş olarak kalıyor (örneklemde 3 doküman; ör.
  bir şeklin harfleri sözde kodun ortasında). Erickson'un kitabında fontun glif kodlamasından gelen bozuk
  aksanlar ("M¯atr¯avr.tta") ve süs glifi kalıntısı var (örneklemde 2). Bu iki kitaptan gelen dokümanlar
  manuel kontrolde en düşük başarıyı aldı.
- `subtopic` genel konulu maddelerde ve yanıltıcı başlıklarda yanlış (örneklemde 4/150: "Introduction",
  "Algoritma" gibi giriş metinleri; ikisi başlığın yanlış alt konuya işaret etmesi).
- Tablolar kapsam dışı: HTML dokümanlarındaki veri tabloları (ör. düzenleme mesafesi türleri, karmaşıklık
  karşılaştırma tabloları) metne alınmadı. Final corpus'ta 107 dokümanda 246 tablo var: İngilizce Vikipedi
  95 doküman / 225 tablo, Türkçe Vikipedi 7 / 10, Open Guide 5 / 11. İçinde kod olan düzen tabloları
  açılıyor. Taranmış (OCR gerektiren) PDF yok.
- Vikipedi'de az sayıda kalıntı: dipnot metninin paragrafa karışması, kenar kutusu yazısı, bir telaffuz
  kalıntısı ("deque — // DEK)"), örnek değerlerin kaybolması, kaynak sayfada da bulunan anlamsız bir
  karakter ("dizisiǖ") (örneklemde birer doküman).
- `publication_year`: Vikipedi maddelerinde maddenin son düzenlendiği yıl (ilk yazıldığı yıl değil);
  kod dosyalarında boş.
- PDF'ten çıkarılan formüllerde düzen kayıpları var (iki boyutlu formül satırlara bölünmüş).

## Sınırlılıklar

Lisans düzeyindeki giriş dersinin konularına odaklı; ileri algoritma teorisi, paralel ve dağıtık
algoritmalar ve sistem konuları için yetersiz. Corpus küçük (1,5 milyon token); CPT'de büyük bir genel
corpus'un yerine değil, alan uyarlaması için tasarlandı. Üzerinde eğitilen model bir ders kitabının ya da
öğretim üyesinin yerine geçmez.

## Sürüm geçmişi

- v0.5 (14.10.2026): Extraction ve temizleme.
- v0.9 (19.10.2026): Filtreleme, tekrar ayıklama, split ve token sayımı; extraction ve temizlemeye iki
  düzeltme (Vikipedi dipnotları, üs/indisler).
- v1.0 (22.10.2026): Manuel kalite kontrolü (150 doküman, iki tur) ve bulunan hatalara göre düzeltmeler:
  alt konu atama kuralı, sayfa üstü bölüm başlıkları, satır sonu tireleri, Vikipedi'de kayıp liste ve kod
  blokları, kök işareti, kaynak işaretleri, sondaki kaynakça kalıntıları; split'in kararlı sıralamaya
  geçmesi (kümeler bir kez yeniden dağıldı). Vize teslimi: 2.11.2026.

## Hazırlayan

Sedef Gizem Orulluoğlu (2211012047) — Süleyman Demirel Üniversitesi, Mühendislik ve Doğa Bilimleri Fakültesi, Bilgisayar Mühendisliği Bölümü. Danışman: Asım Sinan Yüksel.

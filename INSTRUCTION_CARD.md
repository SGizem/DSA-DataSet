# DSA Instruction Dataset v1.0

## Amaç

Bu veri seti, "Veri Yapıları ve Algoritmalar" dersini alan bir öğrencinin sorularını Türkçe cevaplayan bir
dil modelinin supervised fine-tuning (SFT) aşaması için hazırlandı. Domain Corpus v1.0 (`DATASET_CARD.md`)
modele alan bilgisini taşıyor; bu set modele öğrencinin isteğine uygun biçimde, Türkçe, kaynağa dayanarak
ve bilmediğini söyleyerek cevap vermeyi öğretiyor. Genel amaçlı bir sohbet veri seti değildir.

## Kapsam

Konular corpus'unkiyle aynı: diziler ve listeler, yığıt ve kuyruk, hash tabloları, ağaçlar, graflar,
sıralama ve arama, karmaşıklık analizi, özyineleme ve dinamik programlama, algoritma paradigmaları. Talimat
ve cevapların hepsi Türkçe; kod, değişken adları ve matematiksel gösterim olduğu gibi. Kapsam dışı sorular
(hava durumu, yemek tarifi, siyaset gibi alan dışı konular ve işletim sistemi, veritabanı iç yapısı,
NP-tamlık ispatları gibi dersin dışında kalan bilgisayar bilimi konuları) için modelin nazikçe "alanım
dışında" demesini öğreten 101 örnek var.

## Görev türleri

| Görev türü | Ne öğretir | Hedef pay | Final örnek | Final payı | Bağlamlı / bağlamsız |
| --- | --- | --- | --- | --- | --- |
| kavram_aciklama | Bir veri yapısını, algoritmayı ya da kavramı açıklama | %18 | 596 | %18,5 | 229 / 367 |
| coktan_secmeli_soru_uretimi | Konuyla ilgili dört şıklı soru, doğru şık ve açıklama | %12 | 399 | %12,4 | 163 / 236 |
| algoritma_izleme | Bir algoritmayı küçük, somut bir girdide adım adım çalıştırma | %12 | 379 | %11,8 | 150 / 229 |
| karsilastirma | İki yapıyı ya da yöntemi belirli eksenlerde karşılaştırma | %12 | 378 | %11,7 | 177 / 201 |
| kod_okuma | Kısa bir kodun ne yaptığını ya da bir girdi için çıktısını açıklama | %10 | 332 | %10,3 | 134 / 198 |
| karmasiklik_analizi | Zaman/bellek karmaşıklığı ve gerekçesi | %10 | 295 | %9,2 | 120 / 175 |
| hata_bulma | İçine hata konmuş kodda hatalı satırı bulup düzeltme | %8 | 237 | %7,4 | 83 / 154 |
| yanlis_cevap_aciklama | Öğrencinin yanlış cevabının neden yanlış olduğunu açıklama | %6 | 201 | %6,2 | 77 / 124 |
| bilgi_yetersizligi | Uydurmak yerine sınırını söyleme: alan dışı soru (101) ya da metinde olmayan bilgi (100) | %6 | 201 | %6,2 | 100 / 101 |
| konu_ozeti_anlatim | Bir konunun sade özeti | %6 | 200 | %6,2 | 75 / 125 |
| **Toplam** | | | **3.218** | | **1.308 / 1.910** |

Bağlamlı örnekte kullanıcı mesajı ders içeriğini (passage) ve talimatı birlikte içerir; model verilen metne
dayanmayı öğrenir. Bağlamsız örnekte yalnızca talimat vardır; model bilgiyi kendisi taşımalıdır. Bağlamlı
oranı %40,6 (hedef %40).

## Örneklerin üretimi

- **Kaynak metin:** Corpus v0.9'un final dokümanları (bütün kaynakların lisansı API'ye gönderilmeye uygun,
  `config/sources.csv`: `external_api_ok=yes`). `scripts/utils/chunking.py` her dokümanı paragraf, başlık
  ve cümle sınırlarından 250–700 token'lık passage'lara böldü (kelime ya da cümle ortasından kesmeden):
  2.885 passage. Kaynakça satırlarının %30'undan fazlasını oluşturduğu passage'lar planlanmadı (pilotta
  kaynakça listesinden "Landau kimdir?" gibi sorular çıkmıştı).
- **Plan:** `scripts/09_generate_instructions.py` seed 42 ile (doküman, passage, görev türü) üçlülerini
  hedef paylara göre seçti: 3.000 hedef × 1,15 (doğrulamada elenecekler için pay) = 3.450 görev. Görev
  türü yalnızca uygun passage'a verildi: kod okuma ve hata bulma kod içeren passage'a, karmaşıklık analizi
  karmaşıklıktan söz eden passage'a, izleme adım adım anlatılan ya da kod içeren passage'a. Bir doküman en
  çok 40 görev aldı. Ara ölçümde izleme örneklerinin yarısı doğrulamada elendiği için ana plana 280 izleme
  ve 30 hata bulma görevi ekledim (önce kod dosyalarına): toplam 3.760 görev.
- **Öğretmen model:** `gemini-3.5-flash-lite` (Google Gemini API, ücretsiz katman), temperature 0,7,
  top_p 0,95. Aynı passage'ın en çok 3 görevi tek istekte üretildi; alan dışı sorular passage'sız, 5'erli
  gruplar hâlinde, `config/config.yaml`'daki 22 tohum konudan. Üretim 19–22 Ekim 2026'da, günde en çok 500
  istekle yapıldı; script her kaydı anında dosyaya yazıp kaldığı yerden devam edebiliyor.
- **Prompt:** Ortak bölüm `config/prompts/_common.md` (rol: dersin öğretim görevlisi; yalnızca verilen
  metne dayan, metinde olmayan bilgi ekleme; cevap Türkçe, kod olduğu gibi; yalnızca JSON döndür) ve her
  görev türü için ayrı bir dosya (`config/prompts/<görev_türü>.md`: türün tanımı, kurallar ve bir örnek
  çıktı). Sürüm `v1`; her örnekte ortak ve görev türü prompt'larının SHA-256 özetinin ilk 12 karakteri
  (`prompt_sha` = `8efe20f68258`) saklanıyor: prompt değişirse hangi örneğin hangi prompt'la üretildiği
  ayrılabiliyor.
  Prompt'ları 20 örneklik pilottan sonra düzelttim (`reports/instruction_pilot.md`, `experiments.md`).

## Doğrulama

1. **Otomatik kontroller** (`scripts/10_verify_instructions.py`, her örnek ilk takıldığı kontrolle elenir):
   zorunlu alanlar; bozuk karakter; talimat 8–800, cevap 40–1.200 token; çoktan seçmeli cevabın geçerli JSON
   olması, dört dolu ve farklı şık, doğru şıkkın şıklardan biri olması; dil (kod dışı metin Türkçe olmalı,
   Türkçe karakter kullanmadan yazılmış Türkçe de eleniyor); bağlamsız talimatın görünmeyen metne atıf
   yapmaması ("yukarıdaki metne göre"); hata bulma talimatında kod olması ve kodun kaynağın birebir kopyası
   olmaması (yani hata konmuş olması); talimat tekrarı (kelime kümesi Jaccard ≥ 0,90, MinHash ile aday).
2. **Yargıç model:** `gemini-3.1-flash-lite`, temperature 0, öğretmenden farklı bir model (kendi ürettiğini
   yargılamasın diye). Prompt `config/prompts/judge.md`. Her örneği passage'ıyla karşılaştırıp şunları
   soruyor: cevap metne dayanıyor mu (`not_grounded`), talimatı karşılıyor ve doğru mu (`judge_rejected`),
   görev türüne uyuyor mu (`task_mismatch`). Emin olamadığında reddetmesi isteniyor. Alan dışı ret
   örneklerinde alanın sınırını belirtip belirtmediğine bakıyor.
3. **Derleme kontrolü** (`scripts/11_build_instruction_dataset.py`): passage'ı corpus v1.0'da artık
   bulunmayan örnek çıkarılıyor (aşağıda "Bilinen problemler").
4. **Manuel kontrol:** Görev türüne göre tabakalı 200 örneği (seed 42) passage'ıyla birlikte okudum;
   başarısız olan her örnek setten çıkarıldı, geçenler `verified_by=manual` ile işaretlendi.

## Elenen örnekler

| Aşama | Kalan | Elenen | Sebep |
| --- | --- | --- | --- |
| Planlanan görev | 3.760 | — | |
| Üretilen | 3.757 | 3 | iki denemede de geçersiz çıktı (generation_error) |
| Otomatik kontroller | 3.629 | 128 | bağlamsız talimatın metne atfı ya da hata konmamış kod 92, yanlış dil 20, talimat tekrarı 8, çok kısa 8 |
| Yargıç model | 3.263 | 366 | görev türüne uymuyor 147, yanlış ya da talimatı karşılamıyor 140, metne dayanmıyor 79 |
| Derleme | 3.261 | 2 | passage corpus v1.0'da silinmiş (not_grounded) |
| Manuel kontrol | 3.218 | 43 | manual_rejected |

Toplam 3.757 üretilen örneğin 539'u (%14,3) elendi. En çok elenen tür algoritma izleme: 694 görevin 315'i.
Çoğunda talimat somut bir girdi vermiyor ya da cevap adım adım izleme yerine genel bir anlatım yapıyor
(görev türüne uymuyor 150, talimatı karşılamıyor 117); metne dayanmayan 27, Türkçe olmayan ya da Türkçe
karakter kullanmadan yazılmış 15. Elenen her örnek sebebiyle `reports/exclusions.csv` içinde.

## Format

`data/final/instruction_v1.0.jsonl` bütün metadata'yla tek dosya. Alanlar: `id`, `key` (doküman:passage:
görev türü), `source_document`, `passage_idx`, `task_type`, `subtype` (bilgi_yetersizligi için alan_disi /
metinde_yok), `with_context`, `instruction`, `response`, `topic`, `generation_method` (`llm_sentetik`),
`generation_model`, `prompt_version`, `prompt_sha`, `temperature`, `top_p`, `verified_by` (`auto_judge` ya
da `manual:<ad>`), `verified`, `judge_model`, `token_count`, `split`. passage metni bu dosyada tutulmuyor;
`source_document` + `passage_idx` ile `data/instruction/passages.jsonl`'den bulunuyor.

`data/final/instruction_{train,validation,test}.jsonl` SFT'ye hazır:

```json
{"id": "INS_01647", "messages": [
  {"role": "user", "content": "Euler yolu (Eulerian trail) nerelerde ve ne amaçla kullanılmaktadır?"},
  {"role": "assistant", "content": "Euler yolları, biyoinformatikte DNA dizilerinin parçalarından yeniden oluşturulmasında kullanılır. Ayrıca CMOS devre tasarımı aşamasında en uygun mantık kapısı sıralamasını bulmak için tercih edilir. Bunun yanı sıra de Bruijn dizileri, de Bruijn grafiklerinin Euler yolları olarak inşa edilebilir."}]}
```

Bağlamlı örnekte kullanıcı mesajı `Ders içeriği:\n{passage}\n\n{talimat}` biçiminde. Çoktan seçmeli
sorularda cevap şu şemaya uyan bir JSON metni: `{"question", "options": {"A", "B", "C", "D"},
"correct", "explanation"}`.

## İstatistikler

| Ölçüt | Değer |
| --- | --- |
| Örnek | 3.218 |
| Kaynak doküman | 490 (corpus'un 586 dokümanından) + 101 kaynaksız alan dışı örnek |
| Kaynağa göre örnek | İngilizce Vikipedi 2.051, TheAlgorithms/Python 326, Erickson 241, Open Data Structures 229, Open Guide 157, Türkçe Vikipedi 113 |
| Örnek başına token (kullanıcı mesajı + cevap, Qwen3): toplam / min / medyan / ortalama / p95 / max | 1.425.951 / 66 / 298 / 443,1 / 938 / 1.293 |
| Çoktan seçmeli doğru şık (A / B / C / D) | 88 / 121 / 104 / 86 |
| Manuel onaylı / yalnızca otomatik + yargıç doğrulamalı | 157 / 3.061 |

Ayrıntılı tablolar: `reports/statistics.md` (h).

## Veri ayrımı

Her örnek, üretildiği dokümanın corpus'taki kümesine giriyor: train 2.584 (%80,3), validation 325 (%10,1),
test 309 (%9,6). Aynı dokümandan üretilen örnekler hep aynı kümede; corpus test dokümanından üretilmiş bir
örnek instruction train'e girmiyor (derleme bunu her çalıştırmada denetliyor). Kaynaksız alan dışı örnekler
seed 42 ile 80/10/10 dağıtıldı.

## Kalite kontrolü

200 örnekte (`reports/quality_report.md`, `experiments.md` 22.10.2026):

| Kontrol | Başarılı |
| --- | --- |
| instruction_clear (talimat anlaşılır) | 192/200 |
| response_correct (cevap doğru) | 186/200 |
| grounded_in_source (kaynakla tutarlı) | 189/200 |
| answers_instruction (talimatı karşılıyor) | 194/200 |
| task_type_ok (görev türüne uyuyor) | 184/200 |
| Hepsi başarılı | 157/200 (%78,5; %95 güven aralığı %72,3–%83,6) |

Hesap ve izleme içeren cevapları elle yeniden hesapladım. Başarısız 43 örneğin ana hataları: cevap yanlış
14, hata bulmada hatanın yeri talimatta 6, bağlamsız talimatın görünmeyen metne dayanması 6, görev türüne
uymama 6, kaynağa dayanmayan ek 5, eksik ya da yüzeysel cevap 3, yanıltıcı talimat 3. Görev türlerinde en
zayıf hata bulma (16 örnekten 5'i her kontrolden geçti), en güçlü bilgi_yetersizligi (14/14).

## Lisans ve kullanım

Örnekler açık lisanslı metinlerden (CC BY 4.0, CC BY 2.5 CA, CC BY-SA 4.0, MIT; kaynak tablosu
`DATASET_CARD.md`) öğretmen modelle üretilmiş türetilmiş içerik; her örnekte kaynak dokümanın id'si
saklanıyor. Vikipedi'den üretilen örnekler (%67) CC BY-SA 4.0'ın "aynı lisansla paylaş" koşulunu taşır.
Üretimde Gemini API'nin kullanım koşulları geçerliydi. Veri seti akademik amaçla hazırlandı; kişisel veri
içermiyor.

## Bilinen problemler

- **Manuel kontrol edilmeyen örneklerde hata payı.** Kontrol edilen 200 örneğin 14'ünde cevap yanlıştı
  (%7; %95 güven aralığı %4,2–%11,4). Bu örnekler setten çıktı, ama yalnızca yargıçtan geçmiş 3.061 örnekte
  benzer bir oranda yanlış cevap olduğunu tahmin ediyorum. Öğretmen ve yargıç aynı model ailesinden
  (Gemini) olduğu için hataları ilişkili olabilir.
- **Hata bulma türü zayıf.** Prompt yasaklamasına rağmen bazı talimatlar hatanın yerini söylüyor ("heap1
  boş olduğunda yanlış sonuç veriyor"); bazılarında konan değişiklik davranışı değiştirmiyor ve cevap var
  olmayan bir hata anlatıyor. Otomatik kontrol yalnızca kodun kaynağın birebir kopyası olduğu durumu
  yakalıyor.
- **Bağlamsız örneklerde görünmeyen metne atıf.** Otomatik kontrol "yukarıdaki metne göre" gibi açık
  atıfları yakalıyor; "bu veri yapısının", "verilen bilgilere göre" gibi örtük atıflar kalabiliyor
  (örneklemde 6/114 bağlamsız örnek).
- **passage'lar corpus v0.9'dan.** Örnekleri v0.9 metninden ürettim; v1.0 düzeltmeleri bağlamlı örneklerin
  passage'larına yansımadı. 1.319 farklı passage'ın 613'ü v1.0 metninde birebir geçiyor, 430'unun tek farkı
  v1.0'da silinen kaynak işaretleri (`[1]`), 262'si %90'dan fazla aynı. Kalan farklar v1.0'da düzelen
  çıkarım hataları: kayıp liste, sayfa başlığı kalıntısı, satır sonu tiresi. Tamamen silinmiş tek passage
  (bir kaynakçası) ve ona dayanan 2 örnek çıkarıldı.
- **Kod okuma örneklerinde bozuk kopya.** Talimattaki kod bazen kaynaktan bozuk kopyalanmış (örneklemde
  2/20: bir satırda "×" yerine "−", tekrarlanan bir `return`). Otomatik ayıklanamıyor: 335 kod okuma
  örneğinin 187'sinde kod kaynakla birebir değil ve çoğu meşru (yorumlar atılmış, kod kısaltılmış).
- **Türkçe terim tutarsızlıkları.** Öğretmen model bazı terimleri alışılmadık karşılıklarla çevirdi:
  "degenerate tree" için "kötücül ağaç", "skew heap" için "eğri yığın", "inversion" için "tersinir",
  "linear probing" için "doğrusal arama". Yazım hataları da var ("faktörizyel", "quiksort").
- **Doğru şık dengesi.** Öğretmen model doğru şıkkı çoğunlukla B'ye koydu (399 sorunun 243'ü, D yalnızca
  11). Derlemede doğru şıkkı seed'li olarak başka bir harfe taşıdım (şıkların yeri ve açıklamadaki "A
  şıkkı" gibi atıflar birlikte değişiyor; 279 soru). Harfin içerik olarak da geçtiği 28 soruya ("A matrisi",
  "D böleni") dokunmadım; B hâlâ biraz fazla (121/399).
- **Kaynak dengesizliği.** Örneklerin %64'ü İngilizce Vikipedi passage'larından; Türkçe kaynaktan üretilen
  örnek 113.
- **Alan dışı soruların çeşitliliği sınırlı.** 22 tohum konudan üretildi; bazı sorular birbirine çok yakın
  ("Yarın Ankara'da hava nasıl olacak?" iki kez farklı ifadeyle).

## Sınırlılıklar

Örnekler sentetik: bir dil modelinin ders metnini okuyarak yazdığı sorular ve cevaplar, gerçek öğrenci
soruları değil. Sorular çoğunlukla tek bir passage'ın kapsamında; birden çok konuyu birleştiren, uzun
çözüm isteyen ya da öğrencinin kendi kodunu getirdiği sorular az. Cevaplar kısa (medyan 298 token, kullanıcı
mesajıyla birlikte). Üzerinde eğitilen model bir öğretim üyesinin yerine geçmez; cevaplarında, yukarıdaki
oranlarda hata olabilir.

## Sürüm geçmişi

- v1.0 (22.10.2026): Üretim (19–22.10), otomatik kontroller ve yargıç, 200 örneklik manuel kontrol;
  passage'ı silinmiş örneklerin çıkarılması ve doğru şık dengelemesi. Vize teslimi: 2.11.2026.

## Hazırlayan

Sedef Gizem Orulluoğlu (2211012047) — Süleyman Demirel Üniversitesi, Mühendislik ve Doğa Bilimleri Fakültesi, Bilgisayar Mühendisliği Bölümü. Danışman: Asım Sinan Yüksel.

# DSA Domain Corpus v1.0 + Instruction Dataset v1.0

Tasarım-I projemin ("Ders Müfredatına Özel Fine-Tune Edilmiş SLM ve RAG Tabanlı Adaptif Sınav Hazırlama ve
Öğrenme Asistanı"; danışman Asım Sinan Yüksel, Süleyman Demirel Üniversitesi Bilgisayar Mühendisliği) vize
aşaması: "Veri Yapıları ve Algoritmalar" alanında Türkçe soru cevaplayan bir dil modeli için iki eğitim veri
seti ve bu iki seti baştan sona yeniden üreten pipeline. Bu dönemde model eğitimi yok; final döneminde bir
base model önce Domain Corpus ile alana uyarlanacak (continued pretraining), sonra Instruction Dataset ile
asistan hâline getirilecek (supervised fine-tuning).

**Tasarım raporuyla ilişkisi.** Raporun "Veri Seti Oluşturma" adımını uyguluyor: açık kaynak ders
materyallerinden ham içerik, yalnızca veri hazırlamada kullanılan büyük bir dil modeliyle talimat-cevap
biçiminde sentetik veri (raporda dayanak gösterilen Self-Instruct'taki gibi talimatları bir model üretiyor;
farkı, her örneğin corpus'tan bir kaynak metne dayanması), format geçerliliği, şema uyumu ve kaynağa sadakat
(groundedness) kontrolleri, %80/%10/%10 ayrım. Format ve şema otomatik kontrollerde (çoktan seçmeli
cevaplar JSON şemasına göre), kaynağa sadakat yargıç modelde ve manuel kontrolde denetleniyor. Rapordan iki
fark: Vize Rehberi final döneminde fine-tuning'den önce continued pretraining de
istediği için instruction setinin yanına bir domain corpus hazırladım; token sayımında Rehber'in örneğindeki
Qwen3 tokenizer'ını kullandım (raporda aday model Qwen2.5-3B; model seçimi final döneminde). İki
tokenizer'ın kuralları ve sözlüğü aynı: Qwen2.5-3B tokenizer'ıyla da corpus 1.512.566, instruction seti
1.423.322 token çıkıyor (`experiments.md`, 26.10.2026), yani sayılar iki model için de geçerli. Takvim
farkı: raporda fine-tuning güz döneminin 5–9. haftalarındaydı; Vize Rehberi ilk yedi haftayı yalnızca veri
hazırlamaya ayırdığı için model eğitimi final dönemine kaydı. Instruction setinin görev türlerini raporun
sisteminden (konu anlatımı, kaynağa dayalı sınav soruları, yanlış cevap açıklaması, RAG için bağlamlı
örnekler) nasıl çıkardığım `INSTRUCTION_CARD.md` içinde ("Görev türlerinin gerekçesi").

## Problem ve alan tanımı

**Problem.** Genel amaçlı dil modelleri veri yapıları ve algoritmalar sorularında Türkçe terimleri
karıştırabiliyor, bir algoritmayı somut bir girdi üzerinde adım adım izlerken hesap hatası yapabiliyor ve
bilmediği soruda cevap uydurabiliyor. Bunları kendi denemelerimde de gördüm: instruction pilotunda
kullandığım model heap için "yığıt" yazdı (stack'in karşılığı), doğrulamada izleme örneklerinde hesap
hatası çıktı (`experiments.md`, 19.10.2026). Amacım, bu dersi alan bir öğrencinin sorularını Türkçe, ders
kitabına dayanarak cevaplayan ve sınırını bilen bir model için veri hazırlamak.

**Hedef kullanıcı.** Lisans düzeyinde veri yapıları ve algoritmalar dersini alan öğrenci. Sorular ve
cevaplar Türkçe; kod, değişken adları ve matematiksel gösterim olduğu gibi (çoğunlukla İngilizce / Python).

**Kapsam içi:** diziler ve bağlı listeler, yığıt (stack) ve kuyruk, hash tabloları, ağaçlar (ikili arama
ağacı, AVL, kırmızı-siyah, yığın (heap), trie), graflar ve graf algoritmaları, sıralama ve arama,
karmaşıklık analizi, özyineleme ve dinamik programlama, algoritma paradigmaları (açgözlü, böl ve yönet,
geri izleme).

**Kapsam dışı:** işletim sistemleri, veritabanı iç yapısı, bilgisayar ağları, kriptografi, ileri
algoritma teorisi (NP-tamlık ispatları gibi), makine öğrenmesi. Instruction setinde bu konulardan
sorulara modelin nazikçe "alanım dışında" demesini öğreten örnekler var.

**Gereken bilgi türleri.** (1) Kavramların ders kitabı düzeyinde anlatımı ve karmaşıklık gerekçeleri,
(2) algoritmaların sözde kodu ve gerçek kod uygulamaları (kod okuma, hata bulma, izleme görevleri için),
(3) Türkçe terim karşılıkları.

**Neden çoğunlukla İngilizce metin?** Açık lisanslı, ders düzeyinde Türkçe veri yapıları kaynağı
bulamadım; Türkçe kaynak olarak yalnızca Türkçe Vikipedi'yi kullanabildim (corpus token'larının %3,8'i).
Ders kitapları ve İngilizce Vikipedi alan bilgisini taşıyor; modelin Türkçe cevap vermesini Instruction
Dataset sağlıyor (bütün talimat ve cevaplar Türkçe). Ayrıntılar ve diğer bilinen sınırlılıklar
`DATASET_CARD.md` içinde.

## Benzer açık veri setleri

Aramalarımda Türkçe, veri yapıları ve algoritmalara özel ve her örneği kaynak dokümana izlenebilen açık
bir veri seti bulamadım. En yakın bulduklarım (19.10.2026'da her birinin sayfasını açıp kontrol ettim):

| Veri seti | İçerik | Dil / lisans | Bu projeden farkı |
| --- | --- | --- | --- |
| [CLRS-Text](https://arxiv.org/abs/2406.04229) (Markeeva vd., 2024) | 30 klasik algoritma için metin biçiminde yürütme izi üreten araç | en / makale CC BY 4.0, kod [GitHub](https://github.com/google-deepmind/clrs/tree/master/clrs/_src/clrs_text) | Yalnızca sabit biçimli izler; açıklama, karşılaştırma ya da Türkçe yok. `algoritma_izleme` görevime en yakın çalışma |
| [CodeAlpaca-20k](https://huggingface.co/datasets/sahil2801/CodeAlpaca-20k) | 20.022 kod yazma talimatı | en / CC BY 4.0 | Genel programlama; kavram anlatımı az, kaynak dokümanı yok |
| [InstrucTurca](https://huggingface.co/datasets/turkish-nlp-suite/InstrucTurca) | ~2,58 milyon talimat, İngilizce setlerden makine çevirisi (kod talimatları dahil) | tr / CC BY-SA 4.0 | Genel amaçlı ve çeviri; alana özel değil, kaynağa izlenemiyor |
| [MMLU](https://huggingface.co/datasets/cais/mmlu) college_computer_science ve Türkçe çevirisi [mmlu-tr](https://huggingface.co/datasets/malhajar/mmlu-tr) | 116 / 113 çoktan seçmeli soru | en, tr / MIT, Apache-2.0 | Eğitim verisi değil, değerlendirme seti; final döneminde karşılaştırma için aday |

## Veri setleri

| | Domain Corpus | Instruction Dataset |
| --- | --- | --- |
| Kullanım | Continued pretraining (CPT) | Supervised fine-tuning (SFT) |
| Biçim | JSONL, satır başına bir doküman + metadata | JSONL; `messages` biçimi + metadata'lı tam dosya |
| Dosyalar | `data/final/{train,validation,test}.jsonl` | `data/final/instruction_v1.0.jsonl`, `data/final/instruction_{train,validation,test}.jsonl` |
| Ayrım | Doküman düzeyinde 80/10/10, kaynağa göre tabakalı | Her örnek kaynak dokümanının split'ini alır (sızıntı yok) |
| Kart | `DATASET_CARD.md` | `INSTRUCTION_CARD.md` |

Güncel sayılar `reports/statistics.md` içinde (pipeline her çalıştığında yeniden üretilir), manuel
kontrolün sonuçları `reports/quality_report.md` içinde. v1.0 özeti:

| | Domain Corpus v1.0 | Instruction Dataset v1.0 |
| --- | --- | --- |
| Boyut | 586 doküman (6 kaynaktan 609 ham), 1.512.566 token (Qwen3 tokenizer) | 3.212 örnek, 10 görev türü, 1.423.322 token |
| Ayrım | 470 / 58 / 58 doküman | 2.579 / 324 / 309 örnek |
| Manuel kontrol | 150 doküman, iki tur: hepsi başarılı %65,3 → %90,0 | 200 örnek: hepsi başarılı %75,5, cevap doğru %91,5; başarısız 49 örnek setten çıkarıldı |

## Kaynaklar

| Kaynak | Tür | Dil | Lisans |
| --- | --- | --- | --- |
| Open Data Structures (Pat Morin) | PDF | en | CC BY 2.5 CA |
| An Open Guide to Data Structures and Algorithms (PALNI) | HTML | en | CC BY 4.0 |
| Algorithms (Jeff Erickson) | PDF | en | CC BY 4.0 |
| TheAlgorithms/Python | Git (kod) | Python | MIT |
| Türkçe Vikipedi (elle seçilmiş maddeler) | HTML | tr | CC BY-SA 4.0 |
| İngilizce Vikipedi (elle seçilmiş maddeler) | HTML | en | CC BY-SA 4.0 |

Adresler, erişim tarihleri ve seçim gerekçeleri `config/sources.csv` içinde; indirilen her dosya
`config/download_manifest.csv` içinde.

## Pipeline

Her aşama ayrı bir script; yollar ve eşikler `config/config.yaml` içinde, rastgelelik sabit seed (42) ile.

| Script | Ne yapar |
| --- | --- |
| `01_download.py` | Manifest'teki dokümanları indirir (robots.txt, istekler arası bekleme), `data/registry.csv`'ye kaydeder |
| `02_extract.py` | PDF (PyMuPDF), HTML (trafilatura) ve kod dosyalarından metin çıkarır |
| `03_clean.py` | Temizleme kuralları (`reports/cleaning_rules.md`) |
| `04_filter.py` | Kısa, yanlış dilde, gürültülü ve alan dışı dokümanları eler (`--calibrate` ile eşik etiketleme) |
| `05_deduplicate.py` | Exact (SHA-256) ve near duplicate (MinHash + Jaccard ≥ 0,85) ayıklama |
| `06_split.py` | Doküman düzeyinde train/validation/test |
| `07_token_count.py` | Qwen3 tokenizer ile token sayımı |
| `08_statistics.py` | `reports/statistics.md` ve küçük örnek veri (`data/samples/`) |
| `09_generate_instructions.py` | Passage'lardan öğretmen modelle talimat-cevap üretimi |
| `10_verify_instructions.py` | Otomatik kontroller + yargıç model |
| `11_build_instruction_dataset.py` | Split mirası, id'ler, SFT biçimi; passage'ı corpus'tan silinmiş ve manuel kontrolde reddedilen örnekleri çıkarır |
| `12_sample_for_manual_qc.py` | Manuel kalite kontrolü örneklemi ve okuma dosyaları |
| `13_qc_report.py` | Doldurulmuş kontrol tablolarından kalite kontrol raporu (`reports/quality_report.md`); reddedilen örnekleri setten çıkarır |
| `run_all.py` | 01→08 (ve `--with-instruction` ile 09→11) sırasıyla; `--check-deliverables` teslim denetimi |

Elenen her doküman ve örnek sebep koduyla `reports/exclusions.csv` içinde; denediklerim ve kararlarımın
gerekçeleri tarihli olarak `experiments.md` içinde.

## Kurulum ve çalıştırma

Python 3.13.14 (Windows 11) ile geliştirdim; kullandığım ortam `reports/environment.txt` içinde.

```bash
python -m venv venv
venv\Scripts\activate            # Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env           # Linux/macOS: cp; CONTACT_EMAIL (indirme User-Agent'ı), GEMINI_API_KEY (instruction üretimi)
```

Script'ler proje kökünden modül olarak ve **sanal ortam etkinken** çalışır (sistem Python'unda kurulu
farklı `transformers` / `huggingface_hub` sürümleri tokenizer yüklenirken hata verir):

```bash
python -m scripts.run_all                      # corpus: 01 -> 08
python -m scripts.run_all --with-instruction   # ardından 09 -> 11 ve istatistikler
python -m scripts.run_all --check-deliverables # teslim dosyaları + bütünlük kontrolleri
python -m pytest -q                            # testler
```

Manuel kalite kontrolü (pipeline'ın dışında, elle):

```bash
python -m scripts.12_sample_for_manual_qc      # örneklem: reports/manual_qc_corpus.csv, manual_qc_instruction.csv
# CSV'lerdeki kontrol sütunlarını 1/0 ile doldur (okuma dosyaları: reports/manual_qc_view/, manual_qc_instruction_view.md)
python -m scripts.13_qc_report --reviewer-name "<ad soyad>"   # rapor + reddedilenleri çıkarıp 11 ve 08'i yeniden çalıştırır
```

Her script `--config` ve `--limit N` (hızlı deneme) alır; logları `reports/logs/` altına yazar.
Depo `data/registry.csv`'yi işlenmiş hâliyle taşıyor, ara dosyalar ise depoda yok; `run_all` bunu fark edip
02–04'ü baştan çalıştırır (elle zorlamak için `--redo`).

Teslim edilen instruction setini zip'teki ara dosyalardan, API anahtarı olmadan yeniden derlemek için
(`--with-instruction` önce 09'u, yani üretimi çalıştırır; bunun yerine):

```bash
python -m scripts.10_verify_instructions       # kayıtlı yargıç kararlarını okur, API'ye istek atmaz
python -m scripts.11_build_instruction_dataset # manuel inceleme kararları zip'teki manual_review.jsonl'den
python -m scripts.08_statistics
```

**Yeniden üretim testi (26.10.2026).** Depoyu GitHub'dan boş bir klasöre klonladım, yanına yalnızca ham veriyi
ve Releases'teki zip'in `data/instruction/` klasörünü koydum, `.env`'de API anahtarı yokken `run_all`'ı ve
ardından 10, 11, 08'i çalıştırdım. Corpus'un 3 ve instruction setinin 4 teslim dosyası Releases'teki
dosyalarla bayt bayt aynı çıktı; `reports/statistics.md` aynı, `exclusions.csv` ve `extraction_report.csv`
yalnızca zaman sütunlarında farklı. Hiçbir siteye ve API'ye istek gitmedi (`experiments.md`).
Instruction üretimi ücretsiz API katmanının günlük kotasıyla sınırlı: kota dolunca 09 ve 10 durur, ertesi
gün aynı komutla kaldıkları yerden devam eder.

## Büyük dosyalar ve verinin yeri

Vize Rehberi §13 gereği büyük veri dosyalarını depoya koymadım (`.gitignore`). Depoda yalnızca küçük
örnekler var: `data/samples/` (her corpus split'inden 3 doküman, her instruction görev türünden 1 örnek).

| Ne | Boyut | Nerede |
| --- | --- | --- |
| Teslim edilen veri setleri (`data/final/`: corpus train/validation/test, `instruction_v1.0.jsonl` ve SFT dosyaları) | 16 MB | Bu deponun **Releases** sayfasında, `v1.0` sürümüne eklenmiş `DSA-DataSet-v1.0-data.zip` |
| Instruction üretiminin ara dosyaları (`data/instruction/`: passage'lar, plan, ham üretim, yargıç kararları, manuel inceleme kararları) | 34 MB | Aynı zip dosyasında |
| Ham dosyalar (`data/raw/`: PDF, HTML, kod) | 115 MB (587 dosya) | Paylaşılmıyor. Adresler `config/download_manifest.csv` içinde; `python -m scripts.01_download` yeniden indirir. İlk indirmenin boyut ve SHA-256 değerleri `reports/download_log.csv` içinde |
| `data/extracted/`, `data/cleaned/` | — | Ham veriden `python -m scripts.run_all` ile yeniden üretilir |

Zip proje köküne açılınca `data/final/` ve `data/instruction/` klasörleri oluşur; içindeki
`SHA256SUMS.txt` ile dosyalar doğrulanabilir. Vikipedi maddeleri indirdiğim günden (13.10.2026) sonra
düzenlenmiş olabileceği için ham veriyi yeniden indirmek birkaç dokümanda farklı metin verebilir.
Instruction örnekleri öğretmen modelle (temperature 0,7) üretildiği için 09 yeniden çalıştırılırsa birebir
aynı örnekler çıkmaz; teslim edilen set zip'teki dosyadır. 10 ve 11, zip'teki yargıç kararlarıyla API'ye
istek atmadan aynı seti yeniden derler.

## Değerlendirme planı

Değerlendirme seti vizede istenmiyor (Rehber §11), ama ölçümün temeli şimdiden ayrıldı:

- **Ayrılmış test kümeleri.** Corpus testi 58 doküman, instruction testi 309 örnek. Ayrım doküman düzeyinde:
  bir test dokümanının ne metni ne de ondan üretilen bir örnek eğitim kümelerine giriyor
  (`run_all --check-deliverables` her çalıştırmada denetliyor). Test kümesi seed'li ve kararlı; corpus final
  döneminde büyüse de mevcut test dokümanları yerinde kalıyor.
- **Karşılaştırılacak sistemler (Rehber §20).** Hazır model, corpus'la alana uyarlanmış model ve üstüne
  instruction setiyle SFT yapılmış model. Tasarım raporundaki üç yapılandırma (temel model, fine-tune
  edilmiş model, fine-tune edilmiş + RAG) bununla uyumlu: Rehber, raporun fine-tune adımını CPT ve SFT
  olarak ikiye ayırıyor. RAG'li yapılandırma RAG altyapısı kurulunca (raporun takviminde güz 10–13. hafta)
  eklenecek; bağlamlı test örnekleri (ders metni + talimat) o karşılaştırmada da kullanılabilir.
- **Ölçütler.** Tasarım raporundaki metrikler: geçerli JSON oranı ve şema uyumu (çoktan seçmeli soru
  görevinde cevap JSON), kaynağa sadakat (bağlamlı test örneklerinde cevabın passage'a dayanması) ve kör insan
  değerlendirmesi. Ek olarak corpus test kümesinde dil modeli kaybı (perplexity): alan uyarlamasının etkisini
  doğrudan gösterir. Dış ölçüt adayı: MMLU college_computer_science ve Türkçe çevirisi (yukarıdaki tablo).
- **Sınırlılık.** Instruction test örnekleri de aynı öğretmen modelle üretildi; sonuçlar bu modelin üslubuna
  yakın çıkabilir. Bu yüzden insan değerlendirmesi ve dış set ölçümün parçası.

## Lisans notu

Corpus'taki metinler kaynaklarının lisansını taşır (yukarıdaki tablo). Vikipedi'den gelen kısım CC BY-SA
4.0 olduğundan bu kısmı içeren türetilmiş veri aynı lisansla paylaşılmalıdır. Instruction örnekleri bu
metinlerden öğretmen modelle üretildi; her örnekte kaynak dokümanın id'si saklanıyor.

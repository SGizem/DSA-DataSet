# Near-duplicate eşik kalibrasyonu

`python -m scripts.05_deduplicate --calibration-report` üretir.

## 1. Gerçek çiftler

Kaynak: `reports/calibration_dedup.csv` (etiket 1 = aynı içerik, 0 = farklı içerik). Havuz: {'aralik_alti_en_benzer': 50}.

Dedup'a giren 586 dokümanın en az bir ortak shingle'ı olan bütün çiftlerinde gerçek Jaccard'ın en yüksek değeri: 0.2607.

Etiketli çift: 50 (aynı içerik 0, farklı 50). Farklı içerikli çiftlerde en yüksek Jaccard: 0.2607; aynı içerikli çiftlerde en düşük: -.

Eşik t için: gerçek Jaccard'ı t ve üstünde olan çift kopya sayılır, biri elenir.

| Eşik | Yanlış eleme (farklı içerik, kopya sayıldı) | Kaçan kopya (aynı içerik, elenmedi) | Doğru karar |
| --- | --- | --- | --- |
| 0.05 | 33 | 0 | 17/50 |
| 0.1 | 8 | 0 | 42/50 |
| 0.2 | 1 | 0 | 49/50 |
| 0.3 | 0 | 0 | 50/50 |
| 0.4 | 0 | 0 | 50/50 |
| 0.5 | 0 | 0 | 50/50 |
| 0.6 | 0 | 0 | 50/50 |
| 0.7 | 0 | 0 | 50/50 |
| 0.8 | 0 | 0 | 50/50 |
| 0.85 (config) | 0 | 0 | 50/50 |
| 0.9 | 0 | 0 | 50/50 |
| 0.95 | 0 | 0 | 50/50 |

## 2. Kontrollü değişiklik deneyi

Gerçek dokümanların kopyası bilinen bir biçimde değiştirilip orijinalle karşılaştırıldı (seed'li; eklenen metinler sabit). Satır silme: boş olmayan satırlardan rastgele; kelime değiştirme: rastgele kelimenin yerine aynı dokümandan rastgele bir kelime.

| Değişiklik | Grup | Doküman | Medyan Jaccard | En düşük | En yüksek | Eşiği (≥ 0.85) geçen |
| --- | --- | --- | --- | --- | --- | --- |
| Sona tek satır kaynak bilgisi eklendi | düzyazı | 20 | 0.993 | 0.966 | 0.999 | 20/20 |
| Sona tek satır kaynak bilgisi eklendi | kod | 10 | 0.981 | 0.966 | 0.995 | 10/10 |
| Başa ve sona site menüsü/altbilgisi eklendi (~30 kelime) | düzyazı | 20 | 0.979 | 0.901 | 0.996 | 20/20 |
| Başa ve sona site menüsü/altbilgisi eklendi (~30 kelime) | kod | 10 | 0.898 | 0.830 | 0.974 | 8/10 |
| Satırların %5'i silindi | düzyazı | 20 | 0.937 | 0.833 | 0.985 | 18/20 |
| Satırların %5'i silindi | kod | 10 | 0.879 | 0.756 | 0.917 | 8/10 |
| Satırların %10'u silindi | düzyazı | 20 | 0.869 | 0.772 | 0.982 | 15/20 |
| Satırların %10'u silindi | kod | 10 | 0.800 | 0.682 | 0.852 | 1/10 |
| Satırların %20'si silindi | düzyazı | 20 | 0.737 | 0.532 | 0.866 | 1/20 |
| Satırların %20'si silindi | kod | 10 | 0.615 | 0.513 | 0.710 | 0/10 |
| Satırların %30'u silindi | düzyazı | 20 | 0.629 | 0.450 | 0.815 | 0/20 |
| Satırların %30'u silindi | kod | 10 | 0.501 | 0.392 | 0.561 | 0/10 |
| Kelimelerin %1'i değiştirildi | düzyazı | 20 | 0.910 | 0.873 | 0.938 | 20/20 |
| Kelimelerin %1'i değiştirildi | kod | 10 | 0.871 | 0.850 | 0.894 | 9/10 |
| Kelimelerin %3'ü değiştirildi | düzyazı | 20 | 0.758 | 0.731 | 0.793 | 0/20 |
| Kelimelerin %3'ü değiştirildi | kod | 10 | 0.688 | 0.627 | 0.728 | 0/10 |
| Kelimelerin %5'i değiştirildi | düzyazı | 20 | 0.645 | 0.571 | 0.681 | 0/20 |
| Kelimelerin %5'i değiştirildi | kod | 10 | 0.547 | 0.477 | 0.627 | 0/10 |

Örneklem (seed 42) düzyazı: DOC_000498 DOC_000203 DOC_000013 DOC_000550 DOC_000294 DOC_000278 DOC_000266 DOC_000219 DOC_000548 DOC_000194 DOC_000517 DOC_000445 DOC_000163 DOC_000472 DOC_000377 DOC_000017 DOC_000016 DOC_000173 DOC_000263 DOC_000271; kod: DOC_000119 DOC_000041 DOC_000128 DOC_000070 DOC_000126 DOC_000104 DOC_000073 DOC_000110 DOC_000080 DOC_000036.

## 3. Etiketli çiftler

- DOC_000056 / DOC_000057 (randomized_heap.py / skew_heap.py), Jaccard 0.2607, etiket 0: iki farklı birleştirilebilir yığın (rastgele / skew); sınıf iskeleti ve doctest'ler ortak, birleştirme kuralı farklı
- DOC_000118 / DOC_000127 (bogo_sort.py / patience_sort.py), Jaccard 0.1418, etiket 0: farklı algoritma/dosya; ortak kısım deponun kalıbı (docstring, doctest, __main__ girişi)
- DOC_000118 / DOC_000132 (bogo_sort.py / shell_sort.py), Jaccard 0.1354, etiket 0: farklı algoritma/dosya; ortak kısım deponun kalıbı (docstring, doctest, __main__ girişi)
- DOC_000392 / DOC_000601 (Join-based tree algorithms / Weight-balanced tree), Jaccard 0.1209, etiket 0: Weight-balanced tree maddesinin join tabanlı algoritmalar bölümü diğer maddeyle ortak; maddelerin geri kalanı farklı
- DOC_000119 / DOC_000131 (bubble_sort.py / reversort.py), Jaccard 0.1124, etiket 0: farklı algoritma/dosya; ortak kısım deponun kalıbı (docstring, doctest, __main__ girişi)
- DOC_000118 / DOC_000125 (bogo_sort.py / exchange_sort.py), Jaccard 0.1049, etiket 0: farklı algoritma/dosya; ortak kısım deponun kalıbı (docstring, doctest, __main__ girişi)
- DOC_000106 / DOC_000110 (binary_search.py / exponential_search.py), Jaccard 0.1037, etiket 0: farklı arama yöntemleri (üstel arama ikili aramayı çağırır); ortak kısım docstring kalıbı
- DOC_000122 / DOC_000125 (cycle_sort.py / exchange_sort.py), Jaccard 0.101, etiket 0: farklı algoritma/dosya; ortak kısım deponun kalıbı (docstring, doctest, __main__ girişi)
- DOC_000112 / DOC_000114 (linear_search.py / sentinel_linear_search.py), Jaccard 0.0822, etiket 0: farklı arama yöntemleri (sentinel varyantı); ortak kısım docstring kalıbı
- DOC_000118 / DOC_000126 (bogo_sort.py / merge_sort.py), Jaccard 0.082, etiket 0: farklı algoritma/dosya; ortak kısım deponun kalıbı (docstring, doctest, __main__ girişi)
- DOC_000125 / DOC_000132 (exchange_sort.py / shell_sort.py), Jaccard 0.0809, etiket 0: farklı algoritma/dosya; ortak kısım deponun kalıbı (docstring, doctest, __main__ girişi)
- DOC_000125 / DOC_000127 (exchange_sort.py / patience_sort.py), Jaccard 0.0767, etiket 0: farklı algoritma/dosya; ortak kısım deponun kalıbı (docstring, doctest, __main__ girişi)
- DOC_000127 / DOC_000132 (patience_sort.py / shell_sort.py), Jaccard 0.0726, etiket 0: farklı algoritma/dosya; ortak kısım deponun kalıbı (docstring, doctest, __main__ girişi)
- DOC_000058 / DOC_000074 (kd_node.py / suffix_tree.py), Jaccard 0.0721, etiket 0: farklı veri yapıları; ortak kısım dosya başı yazar/PR yorum bloğu
- DOC_000217 / DOC_000443 (Addressable heap / Mergeable heap), Jaccard 0.072, etiket 0: farklı kavramlar (adreslenebilir / birleştirilebilir yığın); ortak kısım işlem tanımları
- DOC_000604 / DOC_000607 (X-fast trie / Y-fast trie), Jaccard 0.0673, etiket 0: farklı veri yapıları (Y-fast trie, X-fast trie üzerine kurulur); ortak kısım temel tanımlar
- DOC_000210 / DOC_000601 (AVL tree / Weight-balanced tree), Jaccard 0.0668, etiket 0: farklı ağaç türleri; ortak kısım Vikipedi maddelerinde tekrarlanan join tabanlı küme işlemleri bölümü
- DOC_000058 / DOC_000059 (kd_node.py / test_kdtree.py), Jaccard 0.0637, etiket 0: biri k-d ağaç düğüm sınıfı, biri test dosyası; ortak kısım aynı yazarın dosya başı yorum bloğu
- DOC_000118 / DOC_000124 (bogo_sort.py / double_sort.py), Jaccard 0.063, etiket 0: farklı algoritma/dosya; ortak kısım deponun kalıbı (docstring, doctest, __main__ girişi)
- DOC_000125 / DOC_000135 (exchange_sort.py / tree_sort.py), Jaccard 0.0622, etiket 0: farklı algoritma/dosya; ortak kısım deponun kalıbı (docstring, doctest, __main__ girişi)
- DOC_000125 / DOC_000131 (exchange_sort.py / reversort.py), Jaccard 0.0601, etiket 0: farklı algoritma/dosya; ortak kısım deponun kalıbı (docstring, doctest, __main__ girişi)
- DOC_000277 / DOC_000346 (Cache-oblivious distribution sort / Funnelsort), Jaccard 0.0596, etiket 0: farklı algoritmalar; ortak kısım cache-oblivious model tanımı
- DOC_000118 / DOC_000123 (bogo_sort.py / cyclic_sort.py), Jaccard 0.0595, etiket 0: farklı algoritma/dosya; ortak kısım deponun kalıbı (docstring, doctest, __main__ girişi)
- DOC_000111 / DOC_000125 (jump_search.py / exchange_sort.py), Jaccard 0.058, etiket 0: farklı algoritma/dosya; ortak kısım deponun kalıbı (docstring, doctest, __main__ girişi)
- DOC_000466 / DOC_000538 (Pairing heap / Skew binomial heap), Jaccard 0.0568, etiket 0: farklı yığın türleri; ortak kısım Vikipedi maddelerinde tekrarlanan yığın türleri karmaşıklık tablosu
- DOC_000256 / DOC_000466 (Binomial heap / Pairing heap), Jaccard 0.0563, etiket 0: farklı yığın türleri; ortak kısım Vikipedi maddelerinde tekrarlanan yığın türleri karmaşıklık tablosu
- DOC_000122 / DOC_000135 (cycle_sort.py / tree_sort.py), Jaccard 0.0556, etiket 0: farklı algoritma/dosya; ortak kısım deponun kalıbı (docstring, doctest, __main__ girişi)
- DOC_000256 / DOC_000538 (Binomial heap / Skew binomial heap), Jaccard 0.0555, etiket 0: farklı yığın türleri; ortak kısım Vikipedi maddelerinde tekrarlanan yığın türleri karmaşıklık tablosu
- DOC_000126 / DOC_000132 (merge_sort.py / shell_sort.py), Jaccard 0.0548, etiket 0: farklı algoritma/dosya; ortak kısım deponun kalıbı (docstring, doctest, __main__ girişi)
- DOC_000120 / DOC_000126 (bubble_sort_recursive.py / merge_sort.py), Jaccard 0.0534, etiket 0: farklı algoritma/dosya; ortak kısım deponun kalıbı (docstring, doctest, __main__ girişi)
- DOC_000122 / DOC_000130 (cycle_sort.py / recursive_quick_sort.py), Jaccard 0.0534, etiket 0: farklı algoritma/dosya; ortak kısım deponun kalıbı (docstring, doctest, __main__ girişi)
- DOC_000125 / DOC_000130 (exchange_sort.py / recursive_quick_sort.py), Jaccard 0.0517, etiket 0: farklı algoritma/dosya; ortak kısım deponun kalıbı (docstring, doctest, __main__ girişi)
- DOC_000124 / DOC_000125 (double_sort.py / exchange_sort.py), Jaccard 0.0515, etiket 0: farklı algoritma/dosya; ortak kısım deponun kalıbı (docstring, doctest, __main__ girişi)
- DOC_000513 / DOC_000601 (Red–black tree / Weight-balanced tree), Jaccard 0.0499, etiket 0: farklı ağaç türleri; ortak kısım Vikipedi maddelerinde tekrarlanan join tabanlı küme işlemleri bölümü
- DOC_000168 / DOC_000287 (Kokteyl sıralaması / Cocktail shaker sort), Jaccard 0.0492, etiket 0: aynı konu, farklı dil (Türkçe / İngilizce madde); ortak kısım yalnızca sözde kod
- DOC_000118 / DOC_000122 (bogo_sort.py / cycle_sort.py), Jaccard 0.0488, etiket 0: farklı algoritma/dosya; ortak kısım deponun kalıbı (docstring, doctest, __main__ girişi)
- DOC_000585 / DOC_000601 (Treap / Weight-balanced tree), Jaccard 0.0481, etiket 0: farklı ağaç türleri; ortak kısım Vikipedi maddelerinde tekrarlanan join tabanlı küme işlemleri bölümü
- DOC_000060 / DOC_000063 (from_sequence.py / print_reverse.py), Jaccard 0.048, etiket 0: farklı bağlı liste işlemleri; ortak kısım liste kuran yardımcı fonksiyon ve doctest'i
- DOC_000127 / DOC_000131 (patience_sort.py / reversort.py), Jaccard 0.0473, etiket 0: farklı algoritma/dosya; ortak kısım deponun kalıbı (docstring, doctest, __main__ girişi)
- DOC_000174 / DOC_000181 (Lineer zaman / Sabit zaman), Jaccard 0.047, etiket 0: farklı kavramlar (lineer / sabit zaman); ortak kısım aynı kalıp tanım cümlesi
- DOC_000118 / DOC_000119 (bogo_sort.py / bubble_sort.py), Jaccard 0.0465, etiket 0: farklı algoritma/dosya; ortak kısım deponun kalıbı (docstring, doctest, __main__ girişi)
- DOC_000118 / DOC_000131 (bogo_sort.py / reversort.py), Jaccard 0.0463, etiket 0: farklı algoritma/dosya; ortak kısım deponun kalıbı (docstring, doctest, __main__ girişi)
- DOC_000165 / DOC_000168 (Kabarcık sıralaması / Kokteyl sıralaması), Jaccard 0.0462, etiket 0: farklı algoritmalar (kabarcık / kokteyl sıralaması); ortak kısım benzer sözde kod
- DOC_000118 / DOC_000120 (bogo_sort.py / bubble_sort_recursive.py), Jaccard 0.046, etiket 0: farklı algoritma/dosya; ortak kısım deponun kalıbı (docstring, doctest, __main__ girişi)
- DOC_000337 / DOC_000538 (Fibonacci heap / Skew binomial heap), Jaccard 0.0454, etiket 0: farklı yığın türleri; ortak kısım Vikipedi maddelerinde tekrarlanan yığın türleri karmaşıklık tablosu
- DOC_000337 / DOC_000466 (Fibonacci heap / Pairing heap), Jaccard 0.0441, etiket 0: farklı yığın türleri; ortak kısım Vikipedi maddelerinde tekrarlanan yığın türleri karmaşıklık tablosu
- DOC_000256 / DOC_000337 (Binomial heap / Fibonacci heap), Jaccard 0.0437, etiket 0: farklı yığın türleri; ortak kısım Vikipedi maddelerinde tekrarlanan yığın türleri karmaşıklık tablosu
- DOC_000365 / DOC_000466 (Heap (data structure) / Pairing heap), Jaccard 0.0401, etiket 0: farklı yığın türleri; ortak kısım Vikipedi maddelerinde tekrarlanan yığın türleri karmaşıklık tablosu
- DOC_000256 / DOC_000365 (Binomial heap / Heap (data structure)), Jaccard 0.0377, etiket 0: farklı yığın türleri; ortak kısım Vikipedi maddelerinde tekrarlanan yığın türleri karmaşıklık tablosu
- DOC_000365 / DOC_000538 (Heap (data structure) / Skew binomial heap), Jaccard 0.0363, etiket 0: farklı yığın türleri; ortak kısım Vikipedi maddelerinde tekrarlanan yığın türleri karmaşıklık tablosu

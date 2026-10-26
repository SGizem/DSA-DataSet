# İstatistik raporu — Domain Corpus v1.0

`python -m scripts.08_statistics` üretir. Kaynak: `data/registry.csv`, `reports/exclusions.csv`, `data/final/*.jsonl`, `reports/token_stats.json`.

## Özet

| Özellik | Değer |
| --- | --- |
| Veri kaynağı sayısı | 6 |
| Ham doküman | 609 |
| Ham dosya boyutu | 114,6 MB (587 dosya) |
| Extraction başarılı | 608 |
| Extraction başarısız | 1 |
| Filtering sonrası | 586 |
| Exact duplicate | 0 |
| Near duplicate | 0 |
| Final doküman | 586 |
| Final corpus dosya boyutu (3 JSONL, metadata dahil) | 6,6 MB |
| Toplam karakter | 6.223.372 |
| Toplam kelime | 1.028.018 |
| Toplam token | 1.512.566 |
| Türkçe içerik (token) | %3,8 |
| Manuel kontrol örneği | 150 |
| Manuel kalite başarısı | %90,0 |
| Instruction örneği | 3.212 |
| Instruction kontrol örneği | 200 |

## (a) Erime tablosu

| Aşama | Kalan doküman | Bu aşamada elenen |
| --- | --- | --- |
| Ham (indirilen) | 609 | — |
| Extraction sonrası | 608 | 1 |
| Temizleme ve filtreleme sonrası | 586 | 22 |
| Exact duplicate sonrası | 586 | 0 |
| Near duplicate sonrası | 586 | 0 |
| Final | 586 | — |

## (b) Eleme sebepleri

| Aşama | Sebep | Doküman |
| --- | --- | --- |
| filter | too_short | 17 |
| filter | out_of_domain | 5 |
| extract | too_short | 1 |

Toplam elenen: 23

## (c) Kaynaklar

Kaynak sayısı: 6

| Kaynak | Doküman | Doküman payı | Token | Token payı | Kelime | Karakter |
| --- | --- | --- | --- | --- | --- | --- |
| wikipedia_en | 397 | %67,7 | 982.088 | %64,9 | 706.465 | 4.243.656 |
| erickson_algorithms | 10 | %1,7 | 178.257 | %11,8 | 119.299 | 674.425 |
| open_data_structures | 14 | %2,4 | 113.108 | %7,5 | 72.403 | 394.219 |
| thealgorithms_python | 100 | %17,1 | 105.305 | %7,0 | 45.541 | 389.291 |
| open_guide_dsa | 11 | %1,9 | 77.086 | %5,1 | 60.976 | 347.863 |
| vikipedi_tr | 54 | %9,2 | 56.722 | %3,8 | 23.334 | 173.918 |

**UYARI:** `wikipedia_en` kaynağının token payı %64,9 (sınır %50).

## (d) Dil dağılımı (token bazlı)

| Dil | Doküman | Token | Token payı |
| --- | --- | --- | --- |
| en | 432 | 1.350.539 | %89,3 |
| code | 100 | 105.305 | %7,0 |
| tr | 54 | 56.722 | %3,8 |

## (e) Alt konu dağılımı

| Alt konu | Doküman | Doküman payı | Token | Token payı |
| --- | --- | --- | --- | --- |
| siralama_ve_arama | 147 | %25,1 | 279.831 | %18,5 |
| agaclar | 133 | %22,7 | 321.170 | %21,2 |
| graflar | 86 | %14,7 | 272.266 | %18,0 |
| diziler_ve_listeler | 55 | %9,4 | 120.123 | %7,9 |
| ozyineleme_ve_dp | 44 | %7,5 | 171.115 | %11,3 |
| hash_tablolari | 37 | %6,3 | 101.468 | %6,7 |
| karmasiklik_analizi | 33 | %5,6 | 95.810 | %6,3 |
| yigin_ve_kuyruk | 30 | %5,1 | 91.239 | %6,0 |
| algoritma_paradigmalari | 18 | %3,1 | 58.153 | %3,8 |
| genel | 3 | %0,5 | 1.391 | %0,1 |

## (f) Split boyutları

| Split | Doküman | Doküman payı | Token | Token payı |
| --- | --- | --- | --- | --- |
| train | 470 | %80,2 | 1.199.337 | %79,3 |
| validation | 58 | %9,9 | 177.085 | %11,7 |
| test | 58 | %9,9 | 136.144 | %9,0 |

| Kaynak | train | validation | test |
| --- | --- | --- | --- |
| erickson_algorithms | 8 | 1 | 1 |
| open_data_structures | 12 | 1 | 1 |
| open_guide_dsa | 9 | 1 | 1 |
| thealgorithms_python | 80 | 10 | 10 |
| vikipedi_tr | 44 | 5 | 5 |
| wikipedia_en | 317 | 40 | 40 |

## (g) Token istatistikleri (doküman başına)

Tokenizer: `Qwen/Qwen3-4B-Base` (revision `906bfd4`), özel token eklenmeden.

| Küme | Doküman | Toplam | Min | Medyan | Ortalama | P95 | Max |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Tümü | 586 | 1.512.566 | 106 | 1.564,0 | 2.581,2 | 8.143,5 | 33.370 |
| train | 470 | 1.199.337 | 106 | 1.522,0 | 2.551,8 | 8.086,5 | 33.370 |
| validation | 58 | 177.085 | 226 | 1.946,5 | 3.053,2 | 8.293,8 | 21.380 |
| test | 58 | 136.144 | 136 | 1.552,5 | 2.347,3 | 7.208,0 | 9.031 |

80.000 token'dan uzun doküman: 0

## (h) Instruction istatistikleri

Toplam örnek: 3.212

Erime (planlanan görevden final örneğe):

| Aşama | Kalan örnek | Bu aşamada elenen |
| --- | --- | --- |
| Planlanan görev | 3.760 | — |
| Üretilen | 3.757 | 3 üretim hatası |
| Otomatik kontroller sonrası | 3.629 | 128 |
| Yargıç model sonrası | 3.263 | 366 |
| Derleme sonrası (passage'ı v1.0'da silinmiş olanlar) | 3.261 | 2 |
| Manuel kontrol sonrası (final) | 3.212 | 49 |

Eleme sebepleri:

| Aşama | Sebep | Örnek |
| --- | --- | --- |
| judge | task_mismatch | 147 |
| judge | judge_rejected | 140 |
| auto_check | task_mismatch | 92 |
| judge | not_grounded | 79 |
| manual_qc | manual_rejected | 49 |
| auto_check | wrong_language | 20 |
| auto_check | duplicate_instruction | 8 |
| auto_check | too_short | 8 |
| generate | generation_error | 3 |
| build | not_grounded | 2 |

Görev türü dağılımı:

| Görev türü | Planlanan | Elenen | Final | Final payı |
| --- | --- | --- | --- | --- |
| algoritma_izleme | 694 | 316 | 378 | %11,8 |
| kavram_aciklama | 621 | 25 | 596 | %18,6 |
| coktan_secmeli_soru_uretimi | 414 | 17 | 397 | %12,4 |
| karsilastirma | 414 | 36 | 378 | %11,8 |
| kod_okuma | 345 | 13 | 332 | %10,3 |
| karmasiklik_analizi | 345 | 50 | 295 | %9,2 |
| hata_bulma | 306 | 72 | 234 | %7,3 |
| konu_ozeti_anlatim | 207 | 7 | 200 | %6,2 |
| yanlis_cevap_aciklama | 207 | 6 | 201 | %6,3 |
| bilgi_yetersizligi | 207 | 6 | 201 | %6,3 |

bilgi_yetersizligi alt türleri: alan_disi 101, metinde_yok 100

| Split | Örnek | Oran |
| --- | --- | --- |
| train | 2.579 | %80,3 |
| validation | 324 | %10,1 |
| test | 309 | %9,6 |

with_context oranı: %40,7 (1.306 örnek)

Örnek başına token (kullanıcı mesajı + cevap, Qwen3):

| Toplam | Min | Medyan | Ortalama | 95. yüzdelik | Maks |
| --- | --- | --- | --- | --- | --- |
| 1.423.322 | 66 | 298 | 443,1 | 938 | 1.293 |

| verified_by | Örnek |
| --- | --- |
| auto_judge | 3.061 |
| manual | 151 |

Üretim modeli ve prompt:

| Öğretmen model | prompt_version | prompt_sha | Örnek |
| --- | --- | --- | --- |
| gemini-3.5-flash-lite | v1 | 8efe20f68258 | 3.212 |

## (i) Manuel kalite kontrolü

Corpus manuel kontrolü: 150 örnek incelendi.

| Kontrol | Başarılı | Oran |
| --- | --- | --- |
| readable | 150/150 | %100,0 |
| in_domain | 150/150 | %100,0 |
| extraction_ok | 144/150 | %96,0 |
| header_footer_clean | 149/150 | %99,3 |
| no_broken_chars | 146/150 | %97,3 |
| metadata_ok | 146/150 | %97,3 |
| hepsi başarılı | 135/150 | %90,0 |

Instruction manuel kontrolü: 200 örnek incelendi.

| Kontrol | Başarılı | Oran |
| --- | --- | --- |
| instruction_clear | 192/200 | %96,0 |
| response_correct | 183/200 | %91,5 |
| grounded_in_source | 189/200 | %94,5 |
| answers_instruction | 194/200 | %97,0 |
| task_type_ok | 181/200 | %90,5 |
| hepsi başarılı | 151/200 | %75,5 |

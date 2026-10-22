# algoritma_izleme — Algoritma izleme

Öğrenci, ders içeriğinde anlatılan bir algoritmanın küçük ve somut bir girdi üzerinde adım adım nasıl çalıştığını görmek ister.

Kurallar:
- Bu görev bir İZLEMEDİR, açıklama ya da karşılaştırma değildir. Talimat MUTLAKA somut bir girdi içersin, cevap MUTLAKA numaralı adımlardan oluşsun ("1. ...", "2. ..."). Bu biçime uymayan cevap yazma.
- Talimat algoritmayı ve somut girdiyi açıkça versin (ör. 5–7 elemanlı bir dizi, 4–6 düğümlü küçük bir graf, birkaç anahtar).
- İçerikteki algoritmayı izle. İçerikte adım adım izlenebilecek bir algoritma ya da işlem (ekleme, silme, dolaşma, döndürme ...) yoksa içerikte anlatılan en somut işlemi seç.
- Algoritmanın içerikte anlatıldığı biçimine sadık kal (aynı pivot seçimi, aynı döngü sırası gibi).
- Cevapta her adımı numaralandır ve her adımdan sonraki durumu (dizi, yığıt, kuyruk, mesafe tablosu vb.) göster. Sonucu en sonda açıkça yaz.
- Adımları kendin dikkatle hesapla; her ara durum bir öncekinden doğru türemeli. Hesap hatası olan izleme yazma.

Örnek:
{"instruction": "Seçmeli sıralamayı (selection sort) [29, 10, 14, 37, 13] dizisi üzerinde adım adım uygular mısın?", "response": "Her turda sıralanmamış kısmın en küçük elemanı bulunur ve o kısmın başındaki elemanla yer değiştirilir.\n1. Tur: [29, 10, 14, 37, 13] içinde en küçük 10; 29 ile yer değiştirir → [10, 29, 14, 37, 13]\n2. Tur: [29, 14, 37, 13] içinde en küçük 13; 29 ile yer değiştirir → [10, 13, 14, 37, 29]\n3. Tur: [14, 37, 29] içinde en küçük 14; zaten başta → [10, 13, 14, 37, 29]\n4. Tur: [37, 29] içinde en küçük 29; 37 ile yer değiştirir → [10, 13, 14, 29, 37]\nSon eleman kendiliğinden yerindedir. Sonuç: [10, 13, 14, 29, 37]."}

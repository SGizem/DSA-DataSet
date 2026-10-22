# karsilastirma — Karşılaştırma

Öğrenci, ders içeriğinde geçen iki veri yapısını, algoritmayı ya da yöntemi karşılaştırmanı ister.

Kurallar:
- Karşılaştırılan iki şeyin de ders içeriğinde anlatılıyor olması gerekir. İçerikte yalnızca biri varsa içerikte geçen bir varyantı, alternatifi ya da işlemi seç; içerikte olmayan bir yapıyı karşılaştırmaya katma.
- En az iki karşılaştırma ekseni kullan (ör. zaman karmaşıklığı, bellek kullanımı, uygulama kolaylığı, hangi durumda tercih edildiği).
- Sonunda hangi durumda hangisinin seçileceğini bir cümleyle söyle.

Örnek:
{"instruction": "Doğrusal arama ile ikili aramayı karşılaştırır mısın?", "response": "İki yöntemi üç açıdan karşılaştırabiliriz. Ön koşul: doğrusal arama her dizide çalışır, ikili arama ise dizinin sıralı olmasını gerektirir. Zaman: doğrusal arama en kötü durumda n elemanın hepsine bakar, O(n); ikili arama her adımda arama aralığını yarıya indirdiği için O(log n) adımda biter. Uygulama: doğrusal arama tek bir döngüdür; ikili aramada aralık sınırlarını doğru güncellemek gerekir. Dizi sıralı değilse ve tek bir arama yapılacaksa doğrusal arama, sıralı bir dizide çok sayıda arama yapılacaksa ikili arama tercih edilir."}

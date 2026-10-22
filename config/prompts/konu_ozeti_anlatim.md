# konu_ozeti_anlatim — Konu özeti / anlatım

Öğrenci, ders içeriğindeki konunun sade bir özetini ya da anlatımını ister.

Kurallar:
- Talimat konuyu adıyla anabilir ("Fibonacci yığınlarını kısaca özetler misin?"); BAĞLAMLI görevde "Bu bölümü sade bir dille özetler misin?" gibi içeriğe atıf yapabilir.
- Cevap içeriğin ana fikirlerini doğru sırayla, 4–8 cümlede ya da kısa maddelerle versin. Ayrıntıya boğma; öğrencinin konuyu ilk kez çalışırken okuyacağı bir özet olsun.
- İçerikte olmayan bir bilgiyi özete ekleme.

Örnek:
{"instruction": "Kuyruk (queue) veri yapısını kısaca özetler misin?", "response": "Kuyruk, elemanların eklendiği sırayla çıktığı (ilk giren ilk çıkar, FIFO) bir veri yapısıdır.\n- Ekleme (enqueue) kuyruğun sonuna, çıkarma (dequeue) kuyruğun başından yapılır.\n- Dizi ile dairesel (circular) olarak ya da bağlı liste ile uygulanabilir; iki uygulamada da ekleme ve çıkarma O(1) sürer.\n- Yazıcı işleri ya da genişlik öncelikli arama (BFS) gibi, işlerin geliş sırasıyla ele alındığı durumlarda kullanılır."}

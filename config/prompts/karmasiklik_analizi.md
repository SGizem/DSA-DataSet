# karmasiklik_analizi — Karmaşıklık analizi

Öğrenci, ders içeriğindeki bir işlemin ya da algoritmanın zaman (gerekirse bellek) karmaşıklığını ve nedenini sorar.

Kurallar:
- Cevap önce sonucu Big-O (gerekirse Θ) gösterimiyle versin, sonra kısa ve doğru bir gerekçe sunsun (kaç kez dönen döngü, her adımda yarıya inen aralık, yineleme bağıntısı vb.).
- En iyi, ortalama ve en kötü durum farklıysa ve içerikte geçiyorsa ayrı ayrı belirt.
- İçerikte verilmeyen bir karmaşıklık sonucunu kendinden ekleme; içerikte gerekçe yoksa gerekçeyi içerikteki algoritma tarifinden çıkar.

Örnek:
{"instruction": "Sıralı bir dizide ikili aramanın zaman karmaşıklığı nedir, neden?", "response": "İkili aramanın zaman karmaşıklığı en kötü durumda O(log n)'dir. Her adımda aranan değer ortadaki elemanla karşılaştırılır ve arama aralığının yarısı elenir. n elemanlı aralık n, n/2, n/4, ... diye küçülür ve yaklaşık log₂ n adımda tek elemana iner. En iyi durumda aranan değer ilk bakılan ortadaki elemandır ve arama O(1)'de biter."}

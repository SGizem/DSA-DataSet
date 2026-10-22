# hata_bulma — Hata bulma

Öğrenci, içinde hata olan kısa bir kodun neden yanlış çalıştığını ve nasıl düzeltileceğini sorar.

Kurallar:
- Ders içeriğindeki doğru koddan ya da sözde koddan kısa bir parça (en fazla ~25 satır) al ve içine TEK, gerçekçi bir hata koy: sınır hatası (off-by-one), yanlış karşılaştırma işareti, eksik temel durum (base case), yanlış güncellenen indeks, unutulan dönüş değeri gibi.
- Kodu içerikteki dilinde bırak (sözde kodsa sözde kod); başka bir programlama diline çevirme.
- Talimat hatalı kodu ``` içinde versin ve öğrencinin gözlemini anlatsın (ör. "Bu ikili arama bazı değerleri bulamıyor, hata nerede?"). Hatanın yerini talimatta söyleme.
- Cevap: hatalı satırı aynen alıntılayarak göstersin (satır numarası verme, sayarken yanılma riski var), neden yanlış sonuç verdiğini (mümkünse küçük bir örnek girdiyle) açıklasın ve düzeltilmiş satırı versin.
- Talimat hatanın yerini ima etmesin; öğrenci yalnızca gözlemlediği belirtiyi anlatsın.
- Koyduğun hata ile cevapta anlattığın hata aynı olmalı; başka satırlarda hata bırakma.

Örnek:
{"instruction": "Bu fonksiyon listedeki en büyük elemanı bulmalı ama `[-5, -2, -9]` için yanlış sonuç veriyor. Hata nerede?\n```python\ndef en_buyuk(a):\n    m = 0\n    for x in a:\n        if x > m:\n            m = x\n    return m\n```", "response": "Hatalı satır `m = 0`: başlangıç değeri yanlış seçilmiş. Listedeki bütün sayılar negatif olduğunda hiçbiri 0'dan büyük olmadığı için `m` hiç güncellenmez ve fonksiyon listede olmayan 0'ı döndürür. `[-5, -2, -9]` için doğru cevap -2'dir. Başlangıç değeri listenin ilk elemanı olmalı: `m = a[0]`. Böylece karşılaştırmalar her zaman listedeki gerçek bir değerden başlar."}

# kod_okuma — Kod okuma

Öğrenci kısa bir kod parçasının ne yaptığını ya da belirli bir girdi için ne çıktı vereceğini sorar.

Kurallar:
- Talimat, ders içeriğindeki koddan ya da sözde koddan alınmış kısa bir parçayı (en fazla ~25 satır) aynen içersin. Kodu ``` ile çevrele; gerçek kodsa dilini belirt (```python), sözde kodsa ``` yeterli.
- Kodu içerikte nasıl yazılmışsa öyle al. Sözde kodu başka bir programlama diline ÇEVİRME: çeviri sırasında indeks ve dilim (slice) kuralları değişir, hata girer.
- Talimat net bir soru sorsun: "Bu fonksiyon ne yapar?", "f([3, 1, 2]) çağrısı ne döndürür?" gibi. Sorunun cevabı verilen koddan kesin olarak çıkarılabilmeli; kodda dönüş değeri yoksa "ne döndürür?" diye sorma.
- Cevap kodun amacını, satır satır değil mantık adımlarıyla açıklasın; çıktı sorulduysa çıktıyı açıkça versin ve nasıl elde edildiğini göstersin.
- Çıktıyı kendin dikkatle hesapla; kodun gerçekten üreteceği sonucu yaz.

Örnek:
{"instruction": "Aşağıdaki fonksiyon ne yapar? `f([4, 1, 3])` ne döndürür?\n```python\ndef f(a):\n    s = 0\n    for x in a:\n        if x % 2 == 1:\n            s += x\n    return s\n```", "response": "Fonksiyon, listedeki tek sayıların toplamını döndürür. `s` sıfırdan başlar; döngü her elemana bakar ve `x % 2 == 1` koşulu yalnızca tek sayılarda doğru olduğu için yalnızca onları `s`'ye ekler. `[4, 1, 3]` için 4 çift olduğundan atlanır, 1 ve 3 eklenir: `f([4, 1, 3])` 4 döndürür."}

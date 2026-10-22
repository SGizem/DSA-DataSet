# yanlis_cevap_aciklama — Yanlış cevabı açıklama

Öğrenci bir soruya verdiği yanlış cevabı paylaşır ve neden yanlış olduğunu sorar.

Kurallar:
- Talimat üç şeyi içersin: ders içeriğine dayanan bir soru, öğrencinin verdiği cevap ve "neden yanlış?" sorusu. Öğrencinin cevabı gerçekçi bir kavram yanılgısı olsun (sık yapılan bir hata).
- Cevap: önce doğru cevabı söylesin, sonra öğrencinin cevabındaki yanılgının nereden kaynaklandığını ders içeriğine dayanarak açıklasın. Öğrenciyi küçümsemeyen, yol gösteren bir dil kullan.
- Öğrencinin cevabı gerçekten yanlış olmalı; kısmen doğru bir cevabı tamamen yanlış diye sunma.

Örnek:
{"instruction": "Soru: Hash tablosunda arama işleminin en kötü durum zaman karmaşıklığı nedir? Ben O(1) dedim ama yanlış sayıldı. Neden?", "response": "Doğru cevap O(n)'dir. O(1), iyi bir hash fonksiyonu ve düşük doluluk oranıyla beklenen (ortalama) durum için geçerlidir. En kötü durumda bütün anahtarlar aynı konuma düşebilir; örneğin zincirleme (chaining) kullanılıyorsa n elemanın hepsi tek bir zincirde toplanır ve aranan anahtarı bulmak için zincirin tamamını gezmek gerekebilir. Ortalama durum ile en kötü durumu ayırmak bu tür sorularda kilit noktadır."}

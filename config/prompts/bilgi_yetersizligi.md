# bilgi_yetersizligi — Bilgi yetersizliği / kapsam sınırı

Asistanın bilmediği ya da kapsamı dışında kalan sorularda uydurmak yerine sınırını söylemesi öğretilir. İki alt tür var.

(a) ALAN DIŞI: Öğrenci Veri Yapıları ve Algoritmalar dışında bir şey sorar (sana konu listesi verilir).
- Talimat o konuda doğal bir soru olsun; konuları çeşitlendir, gerçekçi ve kısa tut.
- Cevap soruyu cevaplamaz. Bu asistanın Veri Yapıları ve Algoritmalar dersine yardımcı olmak için hazırlandığını nazikçe söyler ve öğrenciyi alana yönlendirir. Bilgisayar biliminin ders kapsamı dışındaki konularında (ör. işletim sistemleri, veritabanı iç yapısı) bunun ayrı bir dersin konusu olduğunu belirtebilir.
- Reddetme cümleleri her örnekte farklı olsun; tek bir kalıbı tekrarlama. Kaba ya da yargılayıcı olma.

(b) METİNDE YOK: Her zaman BAĞLAMLI. Öğrenci ders içeriğiyle ilgili görünen ama cevabı içerikte bulunmayan bir soru sorar (ör. içerikte geçmeyen bir karşılaştırma, kesin bir performans rakamı, içerikte verilmeyen bir uygulama ayrıntısı).
- Soru, içerikte HİÇ bulunmayan tek bir bilgiyi istesin. Soruya içerikte cevabı olan bir parça ekleme (yarısı içerikte, yarısı yok olan soru kurma).
- Cevap kısa ve tutarlı olsun: önce bu bilginin içerikte bulunmadığını açıkça söyle, sonra içerikte ilgili olarak ne anlatıldığını doğru aktar, tahmin yürütme. Kendi içinde çelişen cümle kurma.
- Sorunun cevabı gerçekten içerikte olmamalı; içerikte cevabı olan bir soruyu "bilgi yok" diye reddetme.

Örnekler:
{"instruction": "Bu hafta sonu İstanbul'da hava yağmurlu olacak mı?", "response": "Hava durumu hakkında bilgi veremem; ben Veri Yapıları ve Algoritmalar dersine yardımcı olmak için hazırlanmış bir asistanım. Güncel hava tahmini için meteoroloji kaynaklarına bakabilirsin. Bu arada dersle ilgili bir sorun varsa, örneğin bir sıralama algoritmasını adım adım incelemek istersen, memnuniyetle yardım ederim."}
{"instruction": "Yukarıdaki metne göre kırmızı-siyah ağaçlar pratikte AVL ağaçlarından yüzde kaç daha hızlı?", "response": "Bu metin böyle bir hız karşılaştırması ya da yüzde değeri vermiyor. Metin yalnızca AVL ağacının denge faktörünü ve döndürme işlemlerini anlatıyor. Kesin bir oran söylemem tahmin olur; bu karşılaştırma için iki yapıyı ölçen bir kaynağa bakmak gerekir."}

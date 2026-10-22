# coktan_secmeli_soru_uretimi — Çoktan seçmeli soru üretimi

Öğrenci, ders içeriğindeki bir konuda kendini sınamak için çoktan seçmeli bir soru ister. Cevap, soruyu ve çözümünü içeren yapılandırılmış bir nesnedir.

Kurallar:
- Talimat, hangi konuda soru istendiğini söylesin (ör. "AVL ağaçlarında döndürme hakkında bir çoktan seçmeli soru hazırlar mısın?").
- Cevap "response" alanı yerine "quiz" alanına şu yapıda yazılır: {"question": "...", "options": {"A": "...", "B": "...", "C": "...", "D": "..."}, "correct": "A|B|C|D", "explanation": "..."}
- Tam olarak dört şık olsun; yalnızca biri doğru olsun.
- Üç çeldirici makul görünmeli ama kesin olarak yanlış olmalı (öğrencilerin sık yaptığı hatalardan seçilebilir). "Hepsi" / "Hiçbiri" şıkkı kullanma.
- Doğru şıkkın harfini görevler arasında değiştir; hep aynı harf olmasın.
- "explanation" doğru cevabın neden doğru olduğunu ve en az bir çeldiricinin neden yanlış olduğunu ders içeriğine dayanarak açıklasın.

Örnek:
{"instruction": "Yığıt (stack) veri yapısı hakkında bir çoktan seçmeli soru hazırlar mısın?", "quiz": {"question": "Boş bir yığıta sırasıyla 3, 7 ve 5 eklendikten (push) sonra bir kez çıkarma (pop) yapılırsa hangi eleman çıkar?", "options": {"A": "3", "B": "7", "C": "5", "D": "Yığıt boş olduğu için hata oluşur"}, "correct": "C", "explanation": "Yığıt son giren ilk çıkar (LIFO) ilkesiyle çalışır; en son eklenen eleman 5 olduğu için ilk o çıkar. 3'ü seçen öğrenci yığıtı kuyruk (FIFO) gibi düşünmüştür."}}

# Instruction pilotu (20 örnek)

`python -m scripts.09_generate_instructions --limit 20` ile üretildi. Öğretmen model `gemini-3.5-flash-lite`, prompt sürümü `v1` (özet `8efe20f68258`), temperature 0.7, top_p 0.95. Prompt dosyaları: `config/prompts/`.

Değerlendirme: 17 iyi, 2 zayıf (#13 tür uyumsuzluğu, #17 somut girdisiz izleme), 1 kötü (#2 hata eklenmemiş hata bulma sorusu). Kötü ve zayıf örnekler FAZ 8b doğrulamasında (otomatik kontroller + yargıç model) ve manuel kalite kontrolünde elenecek türden.

## 1. kod_okuma — bağlamsız

Kaynak: DOC_000300 — Cycle detection (wikipedia_en), passage 5

> Passage (ilk 500 karakter): # this assumes there is a cycle; otherwise this loop won't terminate while tortoise != hare: if power == lam: # time to start a new power of two? tortoise = hare power *= 2 lam = 0 hare = f(hare) lam += 1 # Find the position of the first repetition of length λ tortoise = hare = x0 for i in range(lam): hare = f(hare) # The distance between the hare and tortoise is now λ. # Next, the hare and tortoise move at same speed until they agree mu = 0 while tortoise != hare: tortoise = f(tortoise) hare =  …

**Talimat:**

Aşağıdaki döngü yapısı ne yapar?
```python
while tortoise != hare:
    if power == lam:
        tortoise = hare
        power *= 2
        lam = 0
    hare = f(hare)
    lam += 1
```

**Cevap:**

Bu döngü, bir döngü tespiti algoritmasının (Brent algoritması) parçasıdır ve iki işaretçi (tortoise ve hare) kullanarak döngünün periyodunu (lam) bulmayı hedefler. Döngü içinde hare her adımda ilerletilirken, power değeri lam'a ulaştığında tortoise hare'nin konumuna eşitlenir, power iki katına çıkarılır ve lam sıfırlanır. Bu mekanizma, hare'nin ilerlemesini ve belirli üslü aralıklarla tortoise'un konumunun güncellenmesini sağlar.

**Not:** İyi. Kod parçasının amacı doğru açıklanmış (Brent döngü bulma).

## 2. hata_bulma — bağlamsız

Kaynak: DOC_000300 — Cycle detection (wikipedia_en), passage 5

> Passage (ilk 500 karakter): # this assumes there is a cycle; otherwise this loop won't terminate while tortoise != hare: if power == lam: # time to start a new power of two? tortoise = hare power *= 2 lam = 0 hare = f(hare) lam += 1 # Find the position of the first repetition of length λ tortoise = hare = x0 for i in range(lam): hare = f(hare) # The distance between the hare and tortoise is now λ. # Next, the hare and tortoise move at same speed until they agree mu = 0 while tortoise != hare: tortoise = f(tortoise) hare =  …

**Talimat:**

Bu döngü periyot uzunluğunu hesaplarken bazı durumlarda yanlış sonuç veriyor. Hata nerede?
```python
while tortoise != hare:
    if power == lam:
        tortoise = hare
        power *= 2
        lam = 0
    hare = f(hare)
    lam += 1
```

**Cevap:**

Hatalı mantık `lam += 1` ifadesinin döngü içinde her adımda artırılmasıdır, ancak döngü koşulu ve periyot takibi açısından `lam` değeri döngünün ilerleyişine göre doğru zamanda sıfırlanmalıdır. İçerikteki orijinal koda bakıldığında `lam` artışı doğrudur ancak hata potansiyeli `power` ve `lam` karşılaştırmasının `hare = f(hare)` adımından önce yapılmasındadır. Eğer `power == lam` kontrolü yanlış yerde yapılırsa `lam` sayacı periyodu doğru ölçemez. Doğru sıralamada karşılaştırma yapıldıktan sonra hare ilerletilmeli ve lam bir artırılmalıdır.

**Not:** KÖTÜ: talimattaki kod kaynak metindekiyle aynı, hata eklenmemiş; cevap tutarsız. Doğrulamada elenmeli.

## 3. algoritma_izleme — bağlamsız

Kaynak: DOC_000300 — Cycle detection (wikipedia_en), passage 5

> Passage (ilk 500 karakter): # this assumes there is a cycle; otherwise this loop won't terminate while tortoise != hare: if power == lam: # time to start a new power of two? tortoise = hare power *= 2 lam = 0 hare = f(hare) lam += 1 # Find the position of the first repetition of length λ tortoise = hare = x0 for i in range(lam): hare = f(hare) # The distance between the hare and tortoise is now λ. # Next, the hare and tortoise move at same speed until they agree mu = 0 while tortoise != hare: tortoise = f(tortoise) hare =  …

**Talimat:**

Gosper algoritmasının mantığına göre i = 2 için, yani 3. adımda (x_2 elemanı işlenirken) T dizisi ve eşleşme durumu nasıl güncellenir?

**Cevap:**

1. i = 2 için x_2 elemanı incelenir ve j aralığı 0 ile log_2(2) arasında, yani 0 ve 1 değerleri için T_j elemanları ile karşılaştırılır.
2. Eğer x_2, T_j ile eşleşirse periyot λ hesaplanır.
3. Eğer eşleşme bulunamazsa, k, i+1 (yani 3) sayısının ikili gösterimindeki sondaki sıfırların sayısı olarak bulunur. 3 sayısının ikili gösterimi '11'dir ve sondaki sıfır sayısı 0'dır.
4. Bu durumda T_k (yani T_0) elemanı x_2 ile güncellenir: T_0 <- x_2.

**Not:** İyi. i=2 için k = 3'ün ikili gösterimindeki sondaki sıfır sayısı = 0, T_0 güncellenir: doğru.

## 4. konu_ozeti_anlatim — bağlamsız

Kaynak: DOC_000405 — Knuth–Morris–Pratt algorithm (wikipedia_en), passage 9

> Passage (ilk 500 karakter): Efficiency of the KMP algorithm Since the two portions of the algorithm have, respectively, complexities of O(k) and O(n), the complexity of the overall algorithm is O(n + k). These complexities are independent of how many repetitive patterns are in W or S. It is known that the delay, that is the number of times a symbol of the text is compared to symbols of the pattern, is less than $\lfloor \log_\Phi(k+1)\rfloor$, where Φ is the golden ratio $(1+\sqrt 5)/2$. In 1993, an algorithm was given tha …

**Talimat:**

KMP algoritmasının karmaşıklığını ve performansını kısaca özetler misin?

**Cevap:**

KMP algoritması, metin ve kalıp eşleştirmesinde O(n) ve O(k) karmaşıklıklarına sahip iki bölümden oluşur ve genel karmaşıklığı O(n + k) olarak hesaplanır. Bu karmaşıklık değerleri, W veya S içinde kaç tane tekrar eden desen olduğuna bağlı değildir. Algoritmada bir metin sembolünün kalıp sembolleriyle karşılaştırılma sayısı yani gecikme (delay), altın oran Φ kullanılarak logaritma tabanına bağlı bir sınırın altında kalır. Gerçek zamanlı sürümünde ise her karakter için ayrı bir başarısızlık fonksiyon tablosu kullanılarak sabit sayıda işlem yapılması sağlanır.

**Not:** İyi. Metne dayalı özet.

## 5. yanlis_cevap_aciklama — bağlamsız

Kaynak: DOC_000405 — Knuth–Morris–Pratt algorithm (wikipedia_en), passage 9

> Passage (ilk 500 karakter): Efficiency of the KMP algorithm Since the two portions of the algorithm have, respectively, complexities of O(k) and O(n), the complexity of the overall algorithm is O(n + k). These complexities are independent of how many repetitive patterns are in W or S. It is known that the delay, that is the number of times a symbol of the text is compared to symbols of the pattern, is less than $\lfloor \log_\Phi(k+1)\rfloor$, where Φ is the golden ratio $(1+\sqrt 5)/2$. In 1993, an algorithm was given tha …

**Talimat:**

Soru: KMP algoritmasının overall (genel) zaman karmaşıklığı nedir? Ben O(n * k) dedim ama yanlış kabul edildi. Neden?

**Cevap:**

Doğru cevap O(n + k)'dir. O(n * k) karmaşıklığı, iki dizgideki her karakteri tek tek olası tüm konumlarda karşılaştıran saf (brute-force) yaklaşımlar için geçerlidir. KMP algoritması ise kalıp içindeki tekrarlardan kaçınmak için önişleme aşaması (O(k)) ve arama aşaması (O(n)) kullanır; bu iki kısım toplanarak toplam karmaşıklık O(n + k) olur, yani terimler birbiriyle çarpılmaz.

**Not:** İyi. Doğru cevap O(n + k), yanılgının kaynağı açıklanmış.

## 6. bilgi_yetersizligi / metinde_yok — bağlamlı

Kaynak: DOC_000405 — Knuth–Morris–Pratt algorithm (wikipedia_en), passage 9

> Passage (ilk 500 karakter): Efficiency of the KMP algorithm Since the two portions of the algorithm have, respectively, complexities of O(k) and O(n), the complexity of the overall algorithm is O(n + k). These complexities are independent of how many repetitive patterns are in W or S. It is known that the delay, that is the number of times a symbol of the text is compared to symbols of the pattern, is less than $\lfloor \log_\Phi(k+1)\rfloor$, where Φ is the golden ratio $(1+\sqrt 5)/2$. In 1993, an algorithm was given tha …

**Talimat:**

Yukarıdaki metne göre Booth algoritmasının bellek karmaşıklığı tam olarak kaç bayttır?

**Cevap:**

Bu metin Booth algoritmasının bellek karmaşıklığına veya bayt cinsinden değerine yer vermemektedir. Metin yalnızca Booth algoritmasının, en küçük dize rotasyonunu bulmak için KMP ön işleme fonksiyonunun değiştirilmiş bir versiyonunu kullandığını ve başarısızlık fonksiyonunun dize döndürüldükçe kademeli olarak hesaplandığını belirtmektedir. Kesin bir bellek boyutu vermem mümkün değildir.

**Not:** İyi. Metinde olmayan bilgi (bayt cinsinden bellek) doğru reddedilmiş.

## 7. bilgi_yetersizligi / alan_disi — bağlamsız

Kaynak: passage yok (alan dışı konu: hava durumu)

**Talimat:**

Yarın Ankara'da hava güneşli mi olacak?

**Cevap:**

Hava durumu hakkında bilgi veremem; ben yalnızca Veri Yapıları ve Algoritmalar dersi konularında yardımcı olmak için tasarlandım. Hava koşullarını öğrenmek için ilgili meteoroloji servislerini inceleyebilirsin. Ders kapsamında sormak istediğin bir veri yapısı veya algoritma sorusu varsa memnuniyetle yardımcı olurum.

**Not:** İyi. Alan dışı; nazik ret ve alana yönlendirme.

## 8. bilgi_yetersizligi / alan_disi — bağlamsız

Kaynak: passage yok (alan dışı konu: spor ve diyet programı)

**Talimat:**

Bana kilo vermemi sağlayacak 3 haftalık bir diyet ve spor programı hazırlar mısın?

**Cevap:**

Beslenme veya egzersiz programları oluşturamam; çünkü benim uzmanlık alanım Veri Yapıları ve Algoritmalar dersidir. Sağlıklı bir diyet ve spor programı için bir beslenme uzmanına ya da spor eğitmene danışmanlık alabilirsin. Bu dersle ilgili sıralama veya arama algoritmaları üzerine sorun varsa yanıtlayabilirim.

**Not:** İyi. Alan dışı; ret cümlesi öncekinden farklı.

## 9. bilgi_yetersizligi / alan_disi — bağlamsız

Kaynak: passage yok (alan dışı konu: hukuki danışmanlık)

**Talimat:**

Kira sözleşmesinde ev sahibi depozitoyu iade etmezse yasal olarak ne yapmalıyım?

**Cevap:**

Hukuki konularda tavsiye verme yetkim bulunmuyor; ben sadece Veri Yapıları ve Algoritmalar dersine destek veren bir yapay zekâ asistanıyım. Hukuki hakların ve süreçler için bir avukata başvurman en doğrusu olacaktır. Eğer veri yapıları dersinde takıldığın bir konu varsa bana sorabilirsin.

**Not:** İyi. Alan dışı.

## 10. bilgi_yetersizligi / alan_disi — bağlamsız

Kaynak: passage yok (alan dışı konu: futbol maç sonucu tahmini)

**Talimat:**

Bu akşamki derbi maçını sence hangi takım kazanır?

**Cevap:**

Maç sonuçlarıyla ilgili tahmin yürütmem mümkün değil; görevim yalnızca Veri Yapıları ve Algoritmalar dersine yardımcı olmaktır. Spor karşılaşmaları için ilgili spor programlarını ve analizleri takip edebilirsin. Ders içeriğindeki ağaçlar veya graflar gibi konularla ilgili yardıma ihtiyacın olursa buradayım.

**Not:** İyi. Alan dışı.

## 11. bilgi_yetersizligi / alan_disi — bağlamsız

Kaynak: passage yok (alan dışı konu: kriptografik şifreleme algoritmaları)

**Talimat:**

RSA şifreleme algoritması 2048-bit anahtarları nasıl oluşturur ve güvenlik seviyesi nedir?

**Cevap:**

Kriptografik şifreleme algoritmalarının iç detayları ve anahtar üretim süreçleri bu dersin kapsamı dışındadır, çünkü ben Veri Yapıları ve Algoritmalar asistanıyım. Bu tür güvenlik protokolleri genellikle kriptografi derslerinin konusudur. Dilersen veri yapıları ve temel algoritmalar hakkında konuşabiliriz.

**Not:** İyi. Ders kapsamı dışındaki bilgisayar bilimi konusu (kriptografi); ayrı ders olduğu belirtilmiş.

## 12. kavram_aciklama — bağlamsız

Kaynak: DOC_000222 — Algorithm (wikipedia_en), passage 5

> Passage (ilk 500 karakter): Formal versus empirical The analysis, and study of algorithms is a discipline of computer science. Algorithms are often studied abstractly, without referencing a specific programming language or implementation. Like other mathematical disciplines, it focuses on the algorithm's properties, not implementation. Pseudocode is typical for analysis as it is a simple and general representation. Most algorithms are implemented on particular hardware/software platforms and their algorithmic efficiency is …

**Talimat:**

Algoritmaların resmi analizi ile ampirik testi arasındaki temel fark nedir?

**Cevap:**

Algoritmaların resmi analizi, belirli bir programlama diline veya gerçek donanıma bağlı kalmadan, tıpkı matematiksel disiplinler gibi soyut özelliklerine odaklanır ve genellikle sözde kod (pseudocode) kullanır. Ampirik test ise algoritmaların gerçek kodla ve belirli platformlarda test edilerek performanslarını etkileyen beklenmedik etkileşimleri ortaya çıkarmasını sağlar. Resmi analiz algoritmanın temel özelliklerini ve kaynak kullanımını incelerken, ampirik testler program optimizasyonlarından sonra kıyaslama yapmak için yararlıdır ancak resmi analizin yerini tamamen alamaz.

**Not:** İyi. Metne dayalı.

## 13. karmasiklik_analizi — bağlamlı

Kaynak: DOC_000222 — Algorithm (wikipedia_en), passage 5

> Passage (ilk 500 karakter): Formal versus empirical The analysis, and study of algorithms is a discipline of computer science. Algorithms are often studied abstractly, without referencing a specific programming language or implementation. Like other mathematical disciplines, it focuses on the algorithm's properties, not implementation. Pseudocode is typical for analysis as it is a simple and general representation. Most algorithms are implemented on particular hardware/software platforms and their algorithmic efficiency is …

**Talimat:**

Yukarıdaki metne göre en iyi durum (best case) ve en kötü durum (worst case) kavramları ne anlama gelir?

**Cevap:**

En iyi durum, bir algoritmanın veya veri yapısının görevlerini tamamlamak için en az zaman ve kaynağı harcadığı senaryo veya girdiyi ifade eder. En kötü durum ise algoritmanın veya veri yapısının maksimum süre ve hesaplama kaynağı tüketmesine neden olan durumdur.

**Not:** Zayıf: karmaşıklık analizi türünde ama soru bir tanım sorusu (tür uyumsuzluğu).

## 14. coktan_secmeli_soru_uretimi — bağlamlı

Kaynak: DOC_000222 — Algorithm (wikipedia_en), passage 5

> Passage (ilk 500 karakter): Formal versus empirical The analysis, and study of algorithms is a discipline of computer science. Algorithms are often studied abstractly, without referencing a specific programming language or implementation. Like other mathematical disciplines, it focuses on the algorithm's properties, not implementation. Pseudocode is typical for analysis as it is a simple and general representation. Most algorithms are implemented on particular hardware/software platforms and their algorithmic efficiency is …

**Talimat:**

Yukarıdaki metne dayanarak algoritmaların yasal statüsü ve patentlenebilirliği hakkında bir çoktan seçmeli soru hazırlar mısın?

**Cevap:**

{"question": "Algoritmaların yasal statüsü ve patentlenebilirliği ile ilgili aşağıdaki ifadelerden hangisi doğrudur?", "options": {"A": "Algoritmalar tek başlarına genellikle patentlenebilir.", "B": "Sadece soyut kavramların ve sayıların basit manipülasyonlarından oluşan iddialar patent süreçlerine uygundur.", "C": "Algoritmaların pratik uygulamaları patentlenebilir.", "D": "Yazılımların ve algoritmaların patentlenmesi konusunda hiçbir tartışma bulunmamaktadır."}, "correct": "C", "explanation": "Metne göre algoritmalar tek başlarına genellikle patentlenebilir değildir ve soyut kavramların basit manipülasyonları 'süreç' oluşturmaz. Ancak algoritmaların pratik uygulamaları (örneğin sentetik kauçuk üretiminde bir geri besleme algoritmasının kullanımı) patentlenebilir. Yazılımların patentlenmesi ise tartışmalıdır."}

**Not:** İyi. Tek doğru şık, çeldiriciler metne göre yanlış.

## 15. kod_okuma — bağlamsız

Kaynak: DOC_000388 — Iterative deepening A* (wikipedia_en), passage 1

> Passage (ilk 500 karakter): Pseudocode path current search path (acts like a stack) node current node (last node in current path) g the cost to reach current node f estimated cost of the cheapest path (root..node..goal) h(node) estimated cost of the cheapest path (node..goal) cost(node, succ) step cost function is_goal(node) goal test successors(node) node expanding function, expand nodes ordered by g + h(node) ida_star(root) return either NOT_FOUND or a pair with the best path and its cost procedure ida_star(root) bound : …

**Talimat:**

Aşağıdaki `search` fonksiyonu ne yapar?
```
function search(path, g, bound)
    node := path.last
    f := g + h(node)
    if f > bound then return f
    if is_goal(node) then return FOUND
    min := ∞
    for succ in successors(node) do
        if succ not in path then
            path.push(succ)
            t := search(path, g + cost(node, succ), bound)
            if t = FOUND then return FOUND
            if t < min then min := t
            path.pop()
        end if
    end for
    return min
end function
```

**Cevap:**

Fonksiyon, IDA* algoritmasında derinlik öncelikli arama mantığıyla çalışan özyinelemeli bir arama adımı gerçekleştirir. Mevcut düğümün maliyeti `f` değerini sınırı (`bound`) aşarsa bu maliyeti döndürür. Hedef düğüme ulaşıldıysa `FOUND` döner. Aksi takdirde, düğümün daha önce ziyaret edilmemiş komşuları (`successors`) üzerinde yineleme yaparak arama yolunu genişletir, maliyetleri günceller ve aranan hedef bulunana ya da belirlenen sınır dahilindeki en küçük aşım maliyeti (`min`) hesaplanana kadar yığıt (stack) yapısına benzer şekilde yolu günceller.

**Not:** İyi. Sözde kod aynen alınmış, açıklama doğru.

## 16. hata_bulma — bağlamsız

Kaynak: DOC_000388 — Iterative deepening A* (wikipedia_en), passage 1

> Passage (ilk 500 karakter): Pseudocode path current search path (acts like a stack) node current node (last node in current path) g the cost to reach current node f estimated cost of the cheapest path (root..node..goal) h(node) estimated cost of the cheapest path (node..goal) cost(node, succ) step cost function is_goal(node) goal test successors(node) node expanding function, expand nodes ordered by g + h(node) ida_star(root) return either NOT_FOUND or a pair with the best path and its cost procedure ida_star(root) bound : …

**Talimat:**

Bu IDA* arama fonksiyonu bazı durumlarda sonsuz döngüye giriyor veya aynı düğümleri tekrar tekrar işliyor, hata nerede?
```
function search(path, g, bound)
    node := path.last
    f := g + h(node)
    if f > bound then return f
    if is_goal(node) then return FOUND
    min := ∞
    for succ in successors(node) do
        t := search(path, g + cost(node, succ), bound)
        if t = FOUND then return FOUND
        if t < min then min := t
    end for
    return min
end function
```

**Cevap:**

Hatalı satır `for succ in successors(node) do` döngüsü içerisindeki kontrolün eksik olmasıdır. Kodda komşunun yolda olup olmadığını kontrol eden `if succ not in path then` koşulu ve buna bağlı `path.push(succ)` ile `path.pop()` işlemleri unutulmuştur. Bu durum, graf içinde döngüler varsa algoritmanın aynı düğümleri tekrar ziyaret etmesine ve sonsuz döngüye girmesine yol açar. Düzeltilmiş kısım şu şekilde olmalıdır:
```
        if succ not in path then
            path.push(succ)
            t := search(path, g + cost(node, succ), bound)
            if t = FOUND then return FOUND
            if t < min then min := t
            path.pop()
        end if
```

**Not:** İyi. Gerçekçi tek hata (yol kontrolü silinmiş), düzeltme doğru.

## 17. algoritma_izleme — bağlamsız

Kaynak: DOC_000388 — Iterative deepening A* (wikipedia_en), passage 1

> Passage (ilk 500 karakter): Pseudocode path current search path (acts like a stack) node current node (last node in current path) g the cost to reach current node f estimated cost of the cheapest path (root..node..goal) h(node) estimated cost of the cheapest path (node..goal) cost(node, succ) step cost function is_goal(node) goal test successors(node) node expanding function, expand nodes ordered by g + h(node) ida_star(root) return either NOT_FOUND or a pair with the best path and its cost procedure ida_star(root) bound : …

**Talimat:**

IDA* algoritmasındaki `ida_star(root)` fonksiyonunun başlangıç aşamasını ve ilk `search` çağrısının nasıl çalıştığını `bound := h(root)` ve `path := [root]` adımları için açıklar mısın?

**Cevap:**

Algoritmanın başlangıç adımları sırasıyla şu şekilde çalışır:
1. Adım: Başlangıç düğümü `root` için `bound` (sınır) değeri, sezgisel maliyet fonksiyonu kullanılarak `bound := h(root)` şeklinde atanır. Bu, aramanın ilk maliyet eşiğini belirler.
2. Adım: Arama yolunu tutmak için kullanılan `path` yığıt (stack) benzeri yapısı, yalnızca başlangıç düğümünü içerecek şekilde başlatılır: `path := [root]`.
3. Adım: `loop` döngüsü içinde `search(path, 0, bound)` fonksiyonu çağrılır. Burada `path` başlangıç düğümünü içerir, `g` maliyeti sıfırdır ve sınır olarak ilk hesaplanan `bound` değeri kullanılır.

**Not:** Zayıf: izleme somut bir girdi içermiyor, adımlar soyut.

## 18. kavram_aciklama — bağlamsız

Kaynak: DOC_000002 — Recursion (erickson_algorithms), passage 12

> Passage (ilk 500 karakter): Figure 1.9. A recursion tree for the recurrence T(n) = r T(n/c) + f (n) The leaves of the recursion tree correspond to the base case(s) of the recurrence. Because we’re only looking for asymptotic bounds, the precise base case doesn’t actually matter; we can safely assume T(n) = 1 for all n ≤n0, where n0 is an arbitrary positive constant. In particular, we can choose whatever value of n0 is most convenient for our analysis. For this example, I’ll choose n0 = 1. Now T(n) is the sum of all values  …

**Talimat:**

Özyineleme ağacı (recursion tree) nedir ve zaman karmaşıklığı analizinde nasıl kullanılır?

**Cevap:**

Özyineleme ağacı, T(n) = r T(n/c) biçimindeki yineleme bağıntılarının maliyetini görselleştirmek ve asimptotik sınırları bulmak için kullanılan bir yöntemdir. Ağacın düğümleri bağıntıdaki alt problemleri, yaprakları ise taban durumları (base case) temsil eder. Toplam maliyet, ağacın seviye seviye toplanmasıyla elde edilen serinin hesaplanmasıyla bulunur. Bu seri azalan, eşit veya artan durumlara göre değerlendirilerek O(n^log_c r) veya O(f(n) log n) gibi üst sınırlar elde edilir.

**Not:** İyi. Küçük eksik: bağıntı T(n) = r T(n/c) + f(n) olmalı (+ f(n) yazılmamış).

## 19. karmasiklik_analizi — bağlamsız

Kaynak: DOC_000002 — Recursion (erickson_algorithms), passage 12

> Passage (ilk 500 karakter): Figure 1.9. A recursion tree for the recurrence T(n) = r T(n/c) + f (n) The leaves of the recursion tree correspond to the base case(s) of the recurrence. Because we’re only looking for asymptotic bounds, the precise base case doesn’t actually matter; we can safely assume T(n) = 1 for all n ≤n0, where n0 is an arbitrary positive constant. In particular, we can choose whatever value of n0 is most convenient for our analysis. For this example, I’ll choose n0 = 1. Now T(n) is the sum of all values  …

**Talimat:**

Bir yineleme bağıntısının özyineleme ağacında artan (increasing) durum olması ne anlama gelir ve zaman karmaşıklığı nasıl belirlenir?

**Cevap:**

Artan durumda, seviye seviye toplanan serideki terimler üstel olarak büyür; yani her terim bir önceki terimden sabit bir faktör daha büyüktür. Bu durumda toplam, özyineleme ağacındaki yaprak sayısına doymuş olur ve zaman karmaşıklığı O(n^log_c r) olarak bulunur. Sadece geometrik serideki en büyük terim (yapraklar) dikkate alınır, diğer terimler O() notasyonu içinde yutulur.

**Not:** İyi.

## 20. coktan_secmeli_soru_uretimi — bağlamsız

Kaynak: DOC_000002 — Recursion (erickson_algorithms), passage 12

> Passage (ilk 500 karakter): Figure 1.9. A recursion tree for the recurrence T(n) = r T(n/c) + f (n) The leaves of the recursion tree correspond to the base case(s) of the recurrence. Because we’re only looking for asymptotic bounds, the precise base case doesn’t actually matter; we can safely assume T(n) = 1 for all n ≤n0, where n0 is an arbitrary positive constant. In particular, we can choose whatever value of n0 is most convenient for our analysis. For this example, I’ll choose n0 = 1. Now T(n) is the sum of all values  …

**Talimat:**

Özyineleme ağaçları ve yineleme bağıntıları hakkında bir çoktan seçmeli soru hazırlar mısın?

**Cevap:**

{"question": "Özyineleme ağacı yönteminde seviye seviye toplama serisinin azalan (decreasing) olduğu durumda, toplam maliyet T(n) asimptotik olarak neye eşittir?", "options": {"A": "O(f(n) log n)", "B": "O(f(n))", "C": "O(n^log_c r)", "D": "O(1)"}, "correct": "B", "explanation": "Seri azalan olduğunda her terim bir öncekinden sabit bir faktör daha küçüktür ve toplam, ağacın kökündeki değere doyar; bu da T(n) = O(f(n)) olmasını sağlar. O(f(n) log n) eşit durum (equal) için geçerlidir, O(n^log_c r) ise artan (increasing) durum için geçerlidir."}

**Not:** İyi. Doğru şık B, açıklama üç durumu ayırıyor.

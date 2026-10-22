"""FAZ 8b: instruction doğrulama kontrolleri (API çağrısı yok)."""
import importlib
import json

v = importlib.import_module("scripts.10_verify_instructions")

PASSAGE = "def en_buyuk(a):\n    m = a[0]\n    for x in a:\n        if x > m:\n            m = x\n    return m"
TR_RESPONSE = ("Fonksiyon listenin ilk elemanını başlangıç değeri olarak alır, sonra bütün elemanları sırayla "
               "dolaşır ve daha büyük bir değer gördüğünde onu saklar. Sonunda listedeki en büyük değeri döndürür.")


def words(text: str) -> int:
    return len(text.split())


def cfg() -> dict:
    return {"filter": {"max_noise_ratio": 0.15},
            "instruction": {"taxonomy": {t: 0.1 for t in ["kavram_aciklama", "kod_okuma", "hata_bulma",
                                                          "coktan_secmeli_soru_uretimi", "bilgi_yetersizligi"]},
                            "verify": {"instruction_tokens": {"min": 2, "max": 200},
                                       "response_tokens": {"min": 5, "max": 300}, "language_min_letters": 40,
                                       "ascii_turkish_min_letters": 60}}}


def record(**kw) -> dict:
    base = {"key": "DOC_000001:0:kod_okuma", "task_type": "kod_okuma", "subtype": "", "with_context": False,
            "source_document": "DOC_000001", "passage_idx": 0, "passage": PASSAGE,
            "instruction": "Bu fonksiyon ne yapar?\n```python\n" + PASSAGE + "\n```", "response": TR_RESPONSE,
            "generation_model": "m", "prompt_version": "v1"}
    return base | kw


def check(**kw):
    return v.auto_check(record(**kw), cfg(), words)


def test_valid_record_passes():
    assert check() is None


def test_schema_errors():
    assert check(response="")[0] == "schema_error"
    assert check(task_type="bilinmeyen")[0] == "schema_error"
    assert check(source_document=None)[0] == "schema_error"  # passage'a dayanan örnekte kaynak şart
    ood = dict(key="OOD:1:bilgi_yetersizligi", task_type="bilgi_yetersizligi", subtype="alan_disi",
               instruction="Yarın hava nasıl olacak?", passage=None, source_document=None,
               response="Hava durumu hakkında bilgi veremem; yalnızca veri yapıları ve algoritmalar konusunda yardımcı olabilirim.")
    assert check(**ood) is None
    assert check(**(ood | {"source_document": "DOC_000001"}))[0] == "schema_error"


def test_noise_and_length():
    assert check(response=TR_RESPONSE + "\ufffd")[0] == "too_much_noise"
    assert check(response="Kısa.")[0] == "too_short"
    assert check(response=" ".join(["kelime"] * 400))[0] == "too_long"


def test_quiz_structure():
    quiz = {"question": "Yığıt (stack) hangi sırayla çalışır?", "options": {"A": "LIFO", "B": "FIFO", "C": "Rastgele",
            "D": "Öncelik sırası"}, "correct": "A", "explanation": "Yığıta en son eklenen eleman ilk çıkarılır, bu yüzden LIFO."}
    kw = dict(task_type="coktan_secmeli_soru_uretimi", key="D:0:coktan_secmeli_soru_uretimi",
              instruction="Yığıt hakkında bir çoktan seçmeli soru hazırlar mısın?")
    assert check(**kw, response=json.dumps(quiz, ensure_ascii=False)) is None
    bad = quiz | {"correct": "E"}
    assert check(**kw, response=json.dumps(bad, ensure_ascii=False))[0] == "invalid_json_quiz"
    same = quiz | {"options": quiz["options"] | {"B": "LIFO"}}
    assert check(**kw, response=json.dumps(same, ensure_ascii=False))[0] == "invalid_json_quiz"
    assert check(**kw, response='{"question": "Yığıt hangi sırayla çalışır", "options": bozuk')[0] == "invalid_json_quiz"


def test_language_ignores_code_and_catches_english():
    english = ("The function takes the first element as the initial value, then scans every element and keeps the "
               "larger one. Finally it returns the largest value in the list.")
    assert check(response=english) == ("wrong_language", "response dili en")
    # Türkçe düzyazıda ";" satırı kod saydırmamalı; kod bloğu dil tespitine girmemeli.
    mixed = TR_RESPONSE.replace(", sonra", "; sonra") + "\n```python\nreturn max(a)  # returns the maximum value\n```"
    assert check(response=mixed) is None


def test_context_free_instruction_must_not_refer_to_text():
    assert check(instruction="Yukarıdaki metne göre bu fonksiyon ne yapar?")[0] == "task_mismatch"
    assert check(instruction="Yukarıdaki metne göre bu fonksiyon ne yapar?", with_context=True) is None
    # Dizgi eşleme sorusunda "metinde" geçmesi atıf değildir.
    assert check(instruction="KMP algoritması bir metinde deseni nasıl arar ve neden geri dönmez?") is None


def test_hata_bulma_needs_an_injected_bug():
    kw = dict(task_type="hata_bulma", key="DOC_000001:0:hata_bulma")
    copied = "Bu fonksiyon yanlış sonuç veriyor, hata nerede?\n```python\n" + PASSAGE + "\n```"
    assert check(**kw, instruction=copied)[0] == "task_mismatch"
    assert check(**kw, instruction="Bu fonksiyonda hata nerede?")[0] == "task_mismatch"  # kod yok
    changed = copied.replace("m = a[0]", "m = 0")
    assert check(**kw, instruction=changed) is None
    # Satır silinerek konan hata: kalan satırların hepsi içerikte var ama sıra bozuk, hata gerçek.
    deleted = copied.replace("        if x > m:\n", "")
    assert check(**kw, instruction=deleted) is None


def test_duplicates_only_within_same_context():
    a = record(key="A", instruction="İkili arama ağacına ekleme nasıl yapılır?")
    b = record(key="B", instruction="İkili arama ağacına ekleme nasıl yapılır")
    c = record(key="C", instruction="İkili arama ağacına ekleme nasıl yapılır?", with_context=True, passage_idx=1)
    d = record(key="D", instruction="İkili arama ağacına ekleme nasıl yapılır?", with_context=True, passage_idx=2)
    e = record(key="E", instruction="Kırmızı-siyah ağaçta döndürme ne zaman gerekir?")
    dropped = v.duplicate_instructions([e, d, c, b, a], 0.9, 128, 42)
    assert dropped == {"B": ("A", 1.0)}  # farklı passage'la gelen aynı talimat tekrar değil


def test_judge_decision_mapping():
    ok = {"supported": True, "answers_instruction": True, "task_type_ok": True, "states_limit": False,
          "answer_in_passage": False, "note": "", "unsupported_claims": []}
    r = record()
    assert v.judge_decision(r, ok) is None
    assert v.judge_decision(r, ok | {"supported": False, "unsupported_claims": ["x"]}) == ("not_grounded", "x")
    assert v.judge_decision(r, ok | {"answers_instruction": False})[0] == "judge_rejected"
    assert v.judge_decision(r, ok | {"task_type_ok": False})[0] == "task_mismatch"
    missing = record(task_type="bilgi_yetersizligi", subtype="metinde_yok")
    assert v.judge_decision(missing, ok)[0] == "judge_rejected"  # sınır belirtilmemiş
    assert v.judge_decision(missing, ok | {"states_limit": True}) is None
    assert v.judge_decision(missing, ok | {"states_limit": True, "answer_in_passage": True})[0] == "judge_rejected"
    ood = record(task_type="bilgi_yetersizligi", subtype="alan_disi")
    assert v.judge_decision(ood, ok | {"states_limit": True, "supported": False}) is None  # dayanak gerekmez
    assert v.judge_decision(ood, ok)[0] == "judge_rejected"


def test_parse_verdicts_and_grouping():
    group = [record(key="K1"), record(key="K2")]
    item = {"id": "e1", "note": "n", "unsupported_claims": [], "supported": True, "answers_instruction": True,
            "task_type_ok": True, "states_limit": False, "answer_in_passage": False}
    ok, errors = v.parse_verdicts(json.dumps({"items": [item]}), group)
    assert set(ok) == {"K1"} and set(errors) == {"K2"}
    ok, errors = v.parse_verdicts("json değil", group)
    assert not ok and set(errors) == {"K1", "K2"}
    recs = [record(key=f"P{i}", passage_idx=i % 2) for i in range(4)]
    recs += [record(key=f"OOD:{i}", subtype="alan_disi", source_document=None) for i in range(3)]
    groups = v.judge_groups(recs, ood_batch=2)
    assert [len(g) for g in groups] == [2, 2, 2, 1]
    assert all(len({(r["source_document"], r["passage_idx"]) for r in g}) == 1 for g in groups[:2])


def test_turkish_without_turkish_characters_is_rejected_and_code_literals_ignored():
    ascii_tr = ("Fonksiyon listenin ilk elemanini baslangic degeri olarak alir, sonra butun elemanlari sirayla "
                "dolasir ve daha buyuk bir deger gordugunde onu saklar. Sonunda en buyuk degeri dondurur.")
    assert check(response=ascii_tr) == ("wrong_language", "response Türkçe karakter kullanılmadan yazılmış")
    viterbi = ('Viterbi algoritmasını observations = ["normal", "cold"], start_p = {"Healthy": 0.6, "Fever": 0.4}, '
               'trans_p = {"Healthy": {"Healthy": 0.7, "Fever": 0.3}} değerleriyle adım adım izler misin?')
    assert check(instruction=viterbi) is None

from receipts.student import Student


def test_student_prompt_follows_the_locale():
    student = Student("unused.gguf")
    decimal = student.messages("TOTAL 9.00")
    rupiah = student.messages("TOTAL 5.000")
    assert "9.00 means 9" in decimal[0]["content"]
    assert decimal[1]["content"] == "TOTAL 9.00"
    assert "12500" in rupiah[0]["content"]
    assert rupiah[1]["content"] == "TOTAL 5.000"
from app.services.doctor_service import DoctorCheck


def test_doctor_check_to_dict():
    check = DoctorCheck("resume_source", True, "latex")
    assert check.to_dict() == {
        "name": "resume_source",
        "ok": True,
        "detail": "latex",
    }

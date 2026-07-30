import pytest

from app.services.resume_source_service import ResumeSourceService


def test_overleaf_project_url_is_not_treated_as_tex():
    service = ResumeSourceService()
    with pytest.raises(FileNotFoundError, match="Overleaf project URLs"):
        service._download_tex("https://www.overleaf.com/project/6a664bd18532b049b6961e71")

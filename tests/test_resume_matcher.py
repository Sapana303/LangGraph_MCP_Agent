from __future__ import annotations

from pathlib import Path

from mcp_service.tools.resume_matcher import rank_resumes_against_jd


def test_rank_resumes_against_jd(tmp_path):
    project_root = Path(__file__).resolve().parents[1]
    resume_dir = project_root / "data" / "tmp_resume_pool"
    resume_dir.mkdir(exist_ok=True)

    (resume_dir / "alice_resume.txt").write_text(
        "Python, FastAPI, SQL, AWS, leadership, mentoring teams and product delivery",
        encoding="utf-8",
    )
    (resume_dir / "bob_resume.txt").write_text(
        "Java, Spring Boot, Docker, manual QA, reporting",
        encoding="utf-8",
    )

    result = rank_resumes_against_jd(
        "data/tmp_resume_pool",
        "Python, FastAPI, SQL, AWS, backend engineering, leadership",
        max_results=2,
    )

    assert result["ok"] is True
    assert result["best_match"].endswith("alice_resume.txt")
    assert result["ranked_candidates"][0]["score"] >= result["ranked_candidates"][1]["score"]
    assert "python" in result["ranked_candidates"][0]["matched_skills"]
    assert "aws" in result["ranked_candidates"][0]["matched_skills"]


def test_rejects_paths_outside_project_root():
    result = rank_resumes_against_jd("../", "Python and SQL")
    assert result["ok"] is False
    assert "limited" in result["error"].lower()

from __future__ import annotations

import re
import zipfile
from pathlib import Path

from mcp_service.config import FILESYSTEM_ROOT
from mcp_service.logging_utils import get_logger


logger = get_logger(__name__)

STOPWORDS = {
    "the", "a", "an", "and", "or", "for", "with", "without", "into", "from",
    "this", "that", "these", "those", "your", "our", "their", "they", "them",
    "is", "are", "was", "were", "be", "been", "being", "as", "at", "on", "in",
    "to", "of", "by", "it", "its", "we", "you", "he", "she", "i", "me", "us",
    "about", "over", "under", "after", "before", "during", "through", "along",
    "will", "would", "should", "could", "can", "may", "must", "have", "has",
    "had", "do", "does", "did", "not", "more", "most", "some", "any", "all",
    "but", "if", "then", "than", "also", "just", "new", "old", "who", "what",
    "where", "when", "why", "how", "each", "other", "same", "such", "like",
    "using", "used", "work", "works", "working", "team", "teams", "role", "roles",
    "resume", "cv", "candidate", "candidates", "experience", "years",
}

SKILL_ALIASES = {
    "python": "python",
    "py": "python",
    "fastapi": "fastapi",
    "flask": "flask",
    "django": "django",
    "sql": "sql",
    "postgres": "sql",
    "postgresql": "sql",
    "mysql": "sql",
    "sqlite": "sql",
    "aws": "aws",
    "amazon web services": "aws",
    "azure": "azure",
    "gcp": "gcp",
    "google cloud": "gcp",
    "docker": "docker",
    "kubernetes": "kubernetes",
    "k8s": "kubernetes",
    "javascript": "javascript",
    "js": "javascript",
    "typescript": "typescript",
    "ts": "typescript",
    "react": "react",
    "node": "node.js",
    "nodejs": "node.js",
    "node.js": "node.js",
    "machine learning": "machine learning",
    "ml": "machine learning",
    "artificial intelligence": "ai",
    "ai": "ai",
    "data analysis": "data analysis",
    "analytics": "data analysis",
    "excel": "excel",
    "tableau": "tableau",
    "power bi": "power bi",
    "product management": "product management",
    "stakeholder management": "stakeholder management",
    "leadership": "leadership",
    "management": "leadership",
    "manager": "leadership",
    "communication": "communication",
    "agile": "agile",
    "scrum": "agile",
    "jira": "jira",
    "system design": "system design",
    "design": "system design",
    "backend": "backend engineering",
    "backend engineering": "backend engineering",
    "full stack": "full stack",
    "rest api": "rest api",
    "apis": "rest api",
    "database": "database design",
    "databases": "database design",
    "microservices": "microservices",
    "cloud": "cloud architecture",
    "cloud architecture": "cloud architecture",
    "testing": "testing",
    "qa": "testing",
    "quality assurance": "testing",
    "data structures": "data structures",
    "algorithms": "algorithms",
    "engineering": "engineering",
    "product": "product management",
}


def _resolve_safe_path(directory: str) -> Path:
    requested = Path(directory).expanduser()
    if requested.is_absolute():
        candidate = requested.resolve()
    else:
        candidate = (FILESYSTEM_ROOT / requested).resolve()

    try:
        candidate.relative_to(FILESYSTEM_ROOT)
    except ValueError as error:
        raise ValueError(f"Access is limited to the project directory: {FILESYSTEM_ROOT}") from error

    return candidate


def _tokenize(text: str) -> list[str]:
    cleaned = re.sub(r"[^a-zA-Z0-9+/.#\-\s]", " ", text.lower())
    return [token for token in cleaned.split() if token and len(token) > 2 and token not in STOPWORDS]


def _normalize_term(term: str) -> str:
    clean = term.strip().lower().replace("_", " ")
    return re.sub(r"\s+", " ", clean)


def _extract_text_from_docx(path: Path) -> str:
    try:
        with zipfile.ZipFile(path) as archive:
            data = archive.read("word/document.xml")
        text = re.sub(r"<[^>]+>", " ", data.decode("utf-8", errors="ignore"))
        return re.sub(r"\s+", " ", text)
    except Exception:
        return ""


def _extract_text_from_pdf(path: Path) -> str:
    try:
        data = path.read_bytes()
    except Exception:
        return ""

    text = re.sub(r"\s+", " ", data.decode("latin-1", errors="ignore"))
    matches = re.findall(r"BT\\s.*?\(.*?\)\sTj", text, flags=re.DOTALL)
    if matches:
        return " ".join(re.sub(r"[()\\]", " ", match) for match in matches)

    text = re.sub(r"[^\x00-\x7F]", " ", data.decode("latin-1", errors="ignore"))
    return re.sub(r"\s+", " ", text)


def _read_resume_text(path: Path) -> str:
    suffix = path.suffix.lower()
    try:
        if suffix in {".txt", ".md"}:
            return path.read_text(encoding="utf-8", errors="ignore")
        if suffix == ".docx":
            return _extract_text_from_docx(path)
        if suffix == ".pdf":
            return _extract_text_from_pdf(path)
    except Exception:
        logger.warning("Resume read failed path=%s", path)
    return ""


def _job_keywords(job_description: str) -> list[str]:
    text = _normalize_term(job_description)
    matches = []
    lowered = text.lower()
    for phrase, canonical in sorted(SKILL_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if phrase in lowered and canonical not in matches:
            matches.append(canonical)
    tokens = _tokenize(text)
    for token in tokens:
        normalized = SKILL_ALIASES.get(token)
        if normalized and normalized not in matches:
            matches.append(normalized)
    return matches


def _resume_matches(resume_text: str, jd_keywords: list[str]) -> list[str]:
    resume_text = _normalize_term(resume_text)
    resume_lower = resume_text.lower()
    resume_tokens = set(_tokenize(resume_text))
    matched: list[str] = []

    for keyword in jd_keywords:
        normalized = _normalize_term(keyword)
        if not normalized:
            continue
        if normalized in resume_lower:
            matched.append(normalized)
            continue
        if normalized.replace(" ", "") in resume_tokens:
            matched.append(normalized)
            continue
        if any(part in resume_tokens for part in normalized.split()):
            matched.append(normalized)

    return sorted(set(matched), key=lambda term: term)


def _improvement_suggestions(jd_keywords: list[str], ranked_candidates: list[dict]) -> list[str]:
    if not ranked_candidates:
        return []
    top = ranked_candidates[0]
    missing = [skill for skill in jd_keywords if skill not in top["matched_skills"]]
    return [f"Highlight experience in {skill} to better align with the job description." for skill in missing[:5]]


def rank_resumes_against_jd(resume_directory: str, job_description: str, max_results: int = 5) -> dict:
    """Rank all resumes in a folder by relevance to a job description."""
    try:
        directory = _resolve_safe_path(resume_directory)
    except ValueError as error:
        logger.warning("Resume matching blocked directory=%s error=%s", resume_directory, error)
        return {"ok": False, "error": str(error), "ranked_candidates": [], "best_match": None}

    if not job_description or not job_description.strip():
        return {"ok": False, "error": "A job description is required.", "ranked_candidates": [], "best_match": None}

    if not directory.exists():
        return {"ok": False, "error": f"Directory does not exist: {resume_directory}", "ranked_candidates": [], "best_match": None}

    if not directory.is_dir():
        return {"ok": False, "error": f"Path is not a directory: {resume_directory}", "ranked_candidates": [], "best_match": None}

    jd_keywords = _job_keywords(job_description)
    if not jd_keywords:
        return {
            "ok": False,
            "error": "Could not extract actionable skills from the job description.",
            "ranked_candidates": [],
            "best_match": None,
        }

    resume_files = []
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".txt", ".md", ".docx", ".pdf"}:
            resume_files.append(path)

    if not resume_files:
        return {
            "ok": False,
            "error": "No resume files were found in the target directory.",
            "ranked_candidates": [],
            "best_match": None,
        }

    ranked = []
    for path in resume_files:
        text = _read_resume_text(path)
        if not text.strip():
            continue
        matched_skills = _resume_matches(text, jd_keywords)
        score = round((len(matched_skills) / max(len(jd_keywords), 1)) * 100, 2)
        if matched_skills:
            ranked.append(
                {
                    "resume": str(path.relative_to(FILESYSTEM_ROOT)),
                    "score": score,
                    "matched_skills": matched_skills,
                    "summary": f"Matches {', '.join(matched_skills[:5])}",
                }
            )

    if not ranked:
        return {
            "ok": True,
            "directory": str(directory.relative_to(FILESYSTEM_ROOT)),
            "job_description": job_description,
            "best_match": None,
            "ranked_candidates": [],
            "improvement_suggestions": [
                f"Add experience for {skill} to strengthen alignment with this role." for skill in jd_keywords[:5]
            ],
        }

    ranked.sort(key=lambda item: (item["score"], len(item["matched_skills"])), reverse=True)
    top_candidates = ranked[: max(1, min(max_results, len(ranked)))]

    result = {
        "ok": True,
        "directory": str(directory.relative_to(FILESYSTEM_ROOT)),
        "job_description": job_description,
        "best_match": top_candidates[0]["resume"],
        "ranked_candidates": top_candidates,
        "improvement_suggestions": _improvement_suggestions(jd_keywords, top_candidates),
    }
    logger.info("Resume matching completed directory=%s candidates=%d best=%s", result["directory"], len(top_candidates), result["best_match"])
    return result

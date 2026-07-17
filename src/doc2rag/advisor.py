"""Medical-advisor + Tokyo hospital-finder, layered on top of a parsed document
(the PaddleOCR-VL Markdown, or a CanonicalDocument dict).

Pipeline:
  1. unique_departments()      -> unique 診療科目名 list from 01-2 (the LLM's menu)
  2. advise(document)           -> OpenAI LLM flags health problems and maps each
                                   to relevant departments chosen from that list
  3-4. recommend_hospitals(...) -> for each department, Tokyo-only hospitals
                                   (都道府県コード==13) that offer it, joined by
                                   hospital ID across 01-1 (name/address/website)
                                   and 01-2 (Monday 診療 hours), top 5 each.

`build_advice_markdown()` orchestrates 2-4 into one Markdown block.
"""

from __future__ import annotations

import csv
import functools
import json
from pathlib import Path

from doc2rag.config import Settings, get_settings

ROOT = Path(__file__).resolve().parents[2]  # repo root (src/doc2rag/advisor.py)
HOSP_DIR = ROOT / "data" / "hospitals"
FACILITY_CSV = HOSP_DIR / "01-1_hospital_facility_info_20251201.csv"
SPECIALITY_CSV = HOSP_DIR / "01-2_hospital_speciality_hours_20251201.csv"
TOKYO_PREF_CODE = "13"
TOP_N = 5


# ------------------------------------------------------------- feature 1: depts
@functools.lru_cache(maxsize=1)
def unique_departments() -> list[str]:
    """Sorted, de-duplicated list of 診療科目名 values in the speciality CSV."""
    depts: set[str] = set()
    with open(SPECIALITY_CSV, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            d = (row.get("診療科目名") or "").strip()
            if d:
                depts.add(d)
    return sorted(depts)


# -------------------------------------------------- features 3-4: hospital data
@functools.lru_cache(maxsize=1)
def _tokyo_facilities() -> dict[str, dict]:
    """Tokyo (都道府県コード==13) hospitals keyed by ID -> name/address/website."""
    fac: dict[str, dict] = {}
    with open(FACILITY_CSV, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            if (row.get("都道府県コード") or "").strip() == TOKYO_PREF_CODE:
                fac[(row.get("ID") or "").strip()] = {
                    "name": (row.get("正式名称") or "").strip(),
                    "address": (row.get("所在地") or "").strip(),
                    "website": (row.get("案内用ホームページアドレス") or "").strip(),
                }
    return fac


@functools.lru_cache(maxsize=1)
def _tokyo_dept_index() -> tuple[dict[str, list[str]], dict[tuple[str, str], list[str]]]:
    """Scan the speciality CSV once, keeping only Tokyo hospitals.

    Returns (dept_to_ids, monday_hours):
      dept_to_ids[dept]           = ordered unique hospital IDs offering `dept`
      monday_hours[(id, dept)]    = list of '開始–終了' Monday 診療 bands (may be empty)
    """
    tokyo_ids = set(_tokyo_facilities())
    dept_to_ids: dict[str, list[str]] = {}
    monday: dict[tuple[str, str], list[str]] = {}
    seen: set[tuple[str, str]] = set()
    with open(SPECIALITY_CSV, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            hid = (row.get("ID") or "").strip()
            if hid not in tokyo_ids:
                continue
            dept = (row.get("診療科目名") or "").strip()
            if not dept:
                continue
            key = (hid, dept)
            start = (row.get("月_診療開始時間") or "").strip()
            end = (row.get("月_診療終了時間") or "").strip()
            if start or end:
                band = f"{start or '?'}–{end or '?'}"
                monday.setdefault(key, [])
                if band not in monday[key]:
                    monday[key].append(band)
            if key not in seen:
                seen.add(key)
                dept_to_ids.setdefault(dept, []).append(hid)
    return dept_to_ids, monday


def _resolve_dept(name: str, choices: list[str]) -> str | None:
    """Map an LLM-produced department name to an exact CSV 診療科目名 (exact, then
    closest fuzzy match via rapidfuzz above a threshold)."""
    name = (name or "").strip()
    if not name:
        return None
    if name in set(choices):
        return name
    try:
        from rapidfuzz import fuzz, process

        hit = process.extractOne(name, choices, scorer=fuzz.WRatio)
        if hit and hit[1] >= 88:
            return hit[0]
    except Exception:  # noqa: BLE001 - fuzzy match is best-effort
        pass
    return None


def recommend_hospitals(departments: list[str], top_n: int = TOP_N) -> list[dict]:
    """For each department, up to `top_n` Tokyo hospitals offering it, with the
    joined name/address/website and Monday 診療 hours ('closed' if none)."""
    fac = _tokyo_facilities()
    dept_to_ids, monday = _tokyo_dept_index()
    choices = unique_departments()

    results: list[dict] = []
    seen_depts: set[str] = set()
    for raw in departments:
        dept = _resolve_dept(raw, choices)
        if not dept or dept in seen_depts:
            continue
        seen_depts.add(dept)
        hospitals = []
        for hid in dept_to_ids.get(dept, [])[:top_n]:
            info = fac[hid]
            bands = monday.get((hid, dept), [])
            hospitals.append(
                {
                    "id": hid,
                    "name": info["name"],
                    "address": info["address"],
                    "website": info["website"],
                    "monday_hours": ", ".join(bands) if bands else "closed",
                }
            )
        results.append({"query": raw, "department": dept, "hospitals": hospitals})
    return results


# ----------------------------------------------------- feature 2: LLM advisor
_ADVICE_SCHEMA = {
    "name": "medical_advice",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "overall_summary": {"type": "string"},
            "problems": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "finding": {"type": "string"},
                        "explanation": {"type": "string"},
                        "severity": {"type": "string", "enum": ["low", "moderate", "high"]},
                        "departments": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["finding", "explanation", "severity", "departments"],
                },
            },
            "recommended_departments": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["overall_summary", "problems", "recommended_departments"],
    },
}

_SYSTEM_PROMPT = (
    "You are a careful medical-advisor assistant supporting a health-checkup "
    "(健康診断) triage workflow. You are given the structured JSON of a patient's "
    "checkup and a fixed list of available hospital departments (診療科目名). "
    "Identify abnormal or concerning findings — out-of-range values, judgement "
    "codes such as D1/D2/要治療/要精査/要経過観察, and the doctor's comments. "
    "For each problem, briefly explain it and assign the most relevant "
    "department(s) chosen ONLY from the provided list, copying the names EXACTLY. "
    "Then give a de-duplicated 'recommended_departments' union across all problems. "
    "Write findings/explanations in Japanese. This is decision support and NOT a "
    "medical diagnosis."
)


def _document_as_text(document) -> str:
    """Accept a CanonicalDocument-style dict or already-extracted text/Markdown."""
    if isinstance(document, str):
        return document
    return json.dumps(document, ensure_ascii=False)


def advise(document, settings: Settings | None = None) -> dict:
    """Call the OpenAI LLM to flag health problems and map them to departments."""
    settings = settings or get_settings()
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    departments = unique_departments()
    user_prompt = (
        "AVAILABLE DEPARTMENTS (診療科目名) — choose only from these, exact strings:\n"
        + "\n".join(departments)
        + "\n\nPATIENT HEALTH-CHECKUP (JSON or Markdown):\n"
        + _document_as_text(document)
    )
    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_schema", "json_schema": _ADVICE_SCHEMA},
    )
    return json.loads(response.choices[0].message.content)


# --------------------------------------------------------------- orchestration
_SEV_ICON = {"high": "🔴", "moderate": "🟠", "low": "🟡"}


def build_advice_markdown(document, settings: Settings | None = None) -> str:
    """Run advisor (2) + hospital finder (3-4) and render one Markdown block."""
    if not document:
        return "_Parse a document first, then request advice._"

    advice = advise(document, settings)
    md: list[str] = ["## 🩺 Medical advisor"]
    if advice.get("overall_summary"):
        md.append(f"\n{advice['overall_summary']}\n")

    problems = advice.get("problems", [])
    if problems:
        md.append("### ⚠️ Problems / concerning findings\n")
        for p in problems:
            icon = _SEV_ICON.get(p.get("severity", ""), "•")
            depts = "、".join(p.get("departments", []))
            md.append(f"- {icon} **{p.get('finding','')}** — {p.get('explanation','')}")
            if depts:
                md.append(f"    - ↳ 関連診療科: {depts}")
    else:
        md.append("_No concerning findings were flagged._")

    recommended = advice.get("recommended_departments", [])
    md.append("\n### 🏥 Recommended departments\n")
    md.append("、".join(recommended) if recommended else "_none_")

    recs = recommend_hospitals(recommended)
    md.append("\n### 🗼 Tokyo hospitals (top 5 per department)\n")
    if not recs:
        md.append("_No matching Tokyo hospitals found for the recommended departments._")
    for rec in recs:
        title = rec["department"]
        if rec["query"] != rec["department"]:
            title += f"  _(matched from “{rec['query']}”)_"
        md.append(f"\n#### {title}\n")
        hospitals = rec["hospitals"]
        if not hospitals:
            md.append("_No Tokyo hospital offers this department._")
            continue
        md.append("| # | 病院名 | 所在地 | ホームページ | 月曜 診療時間 |")
        md.append("|---|--------|--------|--------------|----------------|")
        for i, h in enumerate(hospitals, 1):
            web = f"[link]({h['website']})" if h["website"] else "—"
            addr = h["address"] or "—"
            md.append(f"| {i} | {h['name']} | {addr} | {web} | {h['monday_hours']} |")
    md.append("\n\n_Decision support only — not a medical diagnosis._")
    return "\n".join(md)

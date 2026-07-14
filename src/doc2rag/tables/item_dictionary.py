from __future__ import annotations

from rapidfuzz import fuzz, process

# Seed dictionary of canonical 健康診断 test item names, grouped by section.
# This is a starting point, not exhaustive — extend as new clinic templates
# are observed (see docs/ARCHITECTURE.md open items). Keys are the canonical
# name; values are known OCR/clinic-template variants to match against.
ITEM_DICTIONARY: dict[str, list[str]] = {
    "身長": ["身長", "身長(cm)"],
    "体重": ["体重", "体重(kg)"],
    "BMI": ["BMI", "ＢＭＩ"],
    "腹囲": ["腹囲", "腹囲(cm)", "ウエスト"],
    "収縮期血圧": ["収縮期血圧", "血圧(収縮期)", "最高血圧", "収縮期"],
    "拡張期血圧": ["拡張期血圧", "血圧(拡張期)", "最低血圧", "拡張期"],
    "視力(右)": ["視力(右)", "右視力", "裸眼視力(右)"],
    "視力(左)": ["視力(左)", "左視力", "裸眼視力(左)"],
    "LDLコレステロール": ["LDLコレステロール", "LDL-C", "LDLｺﾚｽﾃﾛｰﾙ"],
    "HDLコレステロール": ["HDLコレステロール", "HDL-C", "HDLｺﾚｽﾃﾛｰﾙ"],
    "中性脂肪": ["中性脂肪", "トリグリセリド", "TG"],
    "空腹時血糖": ["空腹時血糖", "血糖", "血糖値", "FBS"],
    "HbA1c": ["HbA1c", "ヘモグロビンA1c"],
    "AST(GOT)": ["AST", "GOT", "AST(GOT)"],
    "ALT(GPT)": ["ALT", "GPT", "ALT(GPT)"],
    "γ-GTP": ["γ-GTP", "γGTP", "ガンマGTP"],
    "尿蛋白": ["尿蛋白", "尿タンパク"],
    "尿糖": ["尿糖"],
    "白血球数": ["白血球数", "WBC"],
    "赤血球数": ["赤血球数", "RBC"],
    "血色素量": ["血色素量", "ヘモグロビン", "Hb"],
}

_MATCH_THRESHOLD = 80


def normalize_item_name(raw_name: str) -> tuple[str, float]:
    """Fuzzy-match a raw OCR'd item name to a canonical name.

    Returns (canonical_name, match_score in [0, 1]). Falls back to the raw
    name (score 0.0) when nothing clears the match threshold, so unknown
    items are preserved rather than dropped.
    """
    candidates = {variant: canonical for canonical, variants in ITEM_DICTIONARY.items() for variant in variants}

    best = process.extractOne(raw_name, candidates.keys(), scorer=fuzz.ratio, score_cutoff=_MATCH_THRESHOLD)
    if best is None:
        return raw_name, 0.0

    matched_variant, score, _ = best
    return candidates[matched_variant], score / 100.0

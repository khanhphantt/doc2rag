from doc2rag.schema.intermediate import OcrRegionResult, RawTable

SYSTEM_PROMPT = """\
あなたは日本の健康診断結果表を構造化するアシスタントです。
以下に、OCRで抽出したテキストと表データ(項目・値・単位・基準値・判定)を渡します。

厳守事項:
- 与えられたOCRテキスト・表データに存在しない数値を絶対に作らないこと。
  数値は必ず入力のいずれかの値をそのまま採用すること。
- OCRの明らかな誤字(項目名の表記ゆれなど)は文脈から補正してよいが、
  検査値・基準値などの数値は補正せず、そのまま転記すること。
- 自由記述(所見・総合判定・問診回答など)は該当するセクションに分類すること。
- 指定されたJSON Schemaに厳密に従って出力すること。
"""


def build_structuring_prompt(text_regions: list[OcrRegionResult], tables: list[RawTable]) -> str:
    parts = ["# OCR抽出テキスト(自由記述領域)"]
    for region in text_regions:
        if region.text.strip():
            parts.append(region.text)

    parts.append("\n# 表データ(項目 / 値 / 単位 / 基準値 / 判定)")
    for table in tables:
        for row in table.rows:
            parts.append(f"{row.item_name} / {row.value} / {row.unit} / {row.reference_range} / {row.judgement}")

    return "\n".join(parts)

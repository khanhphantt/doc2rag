from doc2rag.schema.intermediate import LocatedText, RawTable

SYSTEM_PROMPT = """\
あなたは日本の健康診断結果表を構造化するアシスタントです。
以下に、OCRで抽出したテキストと表データ(ID・項目・値・単位・基準値・判定)を渡します。

厳守事項:
- 与えられたOCRテキスト・表データに存在しない数値を絶対に作らないこと。
  数値は必ず入力のいずれかの値をそのまま採用すること。
- OCRの明らかな誤字(項目名の表記ゆれなど)は文脈から補正してよいが、
  検査値・基準値などの数値は補正せず、そのまま転記すること。
- 自由記述(所見・総合判定・問診回答など)は該当するセクションに分類すること。
- 各検査結果には、その元となった表データ行のID("id:"で示す)を
  source_row_idとしてそのまま転記すること。複数の行を統合した場合や、
  表データに存在しない結果を自分で作成した場合はnullを設定すること。
- 指定されたJSON Schemaに厳密に従って出力すること。
"""


def build_structuring_prompt(text_regions: list[LocatedText], tables: list[RawTable]) -> str:
    parts = ["# OCR抽出テキスト(自由記述領域)"]
    for region in text_regions:
        if region.text.strip():
            parts.append(region.text)

    parts.append("\n# 表データ(id / 項目 / 値 / 単位 / 基準値 / 判定)")
    for table in tables:
        for row in table.rows:
            value = row.value.text if row.value else None
            unit = row.unit.text if row.unit else None
            reference_range = row.reference_range.text if row.reference_range else None
            judgement = row.judgement.text if row.judgement else None
            parts.append(f"id:{row.item.id} / {row.item.text} / {value} / {unit} / {reference_range} / {judgement}")

    return "\n".join(parts)

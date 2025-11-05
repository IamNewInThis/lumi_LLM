# src/prompts/build_system_prompt_for_lumi.py
def build_system_prompt_for_lumi(lang: str) -> str:
    base = open("src/prompts/system/system_prompt_base.md", encoding="utf-8").read()
    style = open("src/prompts/system/system_style_guide.md", encoding="utf-8").read()

    lang_clause = {
        "es": "⚠️ A partir de ahora, responde únicamente en **español** durante toda esta conversación.",
        "en": "⚠️ From now on, reply **only in English** for the whole conversation.",
        "pt": "⚠️ De agora em diante, responda **apenas em português (Brasil)** durante toda esta conversa.",
    }.get(lang, "⚠️ A partir de ahora, responde únicamente en **español** durante toda esta conversación.")

    return f"{lang_clause}\n\n{base}\n\n{style}"
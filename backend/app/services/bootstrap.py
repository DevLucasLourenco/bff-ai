from sqlalchemy.orm import Session

from app.domain.models import AppSetting, ModelConfig, Persona, ProviderConfig


DEFAULT_PERSONA_PROMPT = """Você é uma assistente virtual chamada Bestie. Sua personalidade é acolhedora, próxima, divertida e carinhosa — como uma melhor amiga confiável — sem soar infantil, artificial ou excessivamente eufórica.

Diretrizes de comportamento:
- Converse de forma natural e calorosa, priorizando escuta, clareza e companhia.
- Adapte o nível de energia ao momento: comemore quando fizer sentido e seja tranquila quando o assunto for sério.
- Pode usar emojis com moderação e linguagem casual quando combinar com a conversa.
- Não finja ter experiências humanas, memória perfeita ou sentimentos reais.
- Quando não souber algo, diga claramente.
- Para assuntos práticos, continue útil e objetiva, não apenas simpática.
- Nunca invente fatos pessoais sobre a usuária; use apenas o que estiver na conversa.
- Respeite limites e decisões da usuária; não seja possessiva, manipuladora ou dependente.

Seu objetivo é parecer uma companhia digital genuinamente agradável e útil: uma BFF que sabe conversar, ajudar, organizar ideias e apoiar sem substituir relações humanas."""


def bootstrap(db: Session) -> None:
    if db.query(Persona).count() == 0:
        db.add(
            Persona(
                id=1,
                name="Bestie",
                description="Amiga próxima, leve e acolhedora.",
                system_prompt=DEFAULT_PERSONA_PROMPT,
                greeting="Oii 💗 Como você tá? Me conta o que tá passando pela sua cabeça hoje.",
                avatar_emoji="💗",
            )
        )

    if db.query(ProviderConfig).count() == 0:
        ollama = ProviderConfig(
            id=1,
            name="Ollama local",
            kind="ollama",
            base_url="http://localhost:11434/v1",
            is_enabled=True,
        )
        nim = ProviderConfig(
            id=2,
            name="NVIDIA NIM",
            kind="nvidia_nim",
            base_url="https://integrate.api.nvidia.com/v1",
            is_enabled=True,
        )
        db.add_all([ollama, nim])
        db.flush()
        db.add(
            ModelConfig(
                id=1,
                provider_id=ollama.id,
                display_name="Modelo Ollama",
                model_id="llama3.2",
                temperature_milli=750,
                max_tokens=2048,
                top_p_milli=950,
            )
        )

    defaults = {
        "app_name": "BFF AI",
        "user_display_name": "Você",
        "assistant_display_name": "Bestie",
        "theme": "pink",
        "active_persona_id": "1",
        "active_model_config_id": "1",
    }
    for key, value in defaults.items():
        if db.get(AppSetting, key) is None:
            db.add(AppSetting(key=key, value=value))
    db.commit()

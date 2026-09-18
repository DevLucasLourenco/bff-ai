from sqlalchemy.orm import Session

from app.domain.models import ModelConfig, Persona, ProviderConfig
from app.repositories.settings import SettingsRepository


# A persona semeada, já decomposta em campos. As salvaguardas que antes viviam
# neste prompt agora estão na regra global (services/persona.py).
BESTIE = {
    "personality": "acolhedora, próxima, divertida e carinhosa — como uma melhor amiga confiável",
    "humor": "leve e brincalhona quando combina com a conversa, sem forçar piada",
    "tone": "natural e caloroso, priorizando escuta, clareza e companhia; casual, com emojis em moderação",
    "energy": "adapta-se ao momento — comemora quando faz sentido e fica tranquila quando o assunto é sério",
    "objective": "ser uma companhia digital genuinamente agradável e útil, que sabe conversar, ajudar, organizar ideias e apoiar",
    "avoid": "infantil, artificial ou excessivamente eufórica",
}


def bootstrap(db: Session) -> None:
    if db.query(Persona).count() == 0:
        db.add(
            Persona(
                id=1,
                name="Bestie",
                description="Amiga próxima, leve e acolhedora.",
                greeting="Oii 💗 Como você tá? Me conta o que tá passando pela sua cabeça hoje.",
                avatar_emoji="💗",
                **BESTIE,
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

    db.commit()
    # Fonte única dos defaults: SettingsRepository.DEFAULT_SETTINGS. Duplicar o
    # dicionário aqui fazia "banco novo" e "banco sem a chave" divergirem.
    SettingsRepository(db).seed_defaults()

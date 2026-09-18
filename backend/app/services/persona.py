"""Composição do system prompt de uma persona.

Antes, persona era um único bloco de texto livre. Isso misturava duas coisas de
naturezas diferentes:

- **honestidade e limites** — não fingir sentimentos, admitir quando não sabe,
  não inventar fatos sobre a usuária. Isso não é personalidade: é o mínimo que
  *toda* persona precisa obedecer, e não deveria ser editável persona a persona,
  onde uma edição descuidada apagaria a salvaguarda sem ninguém notar;
- **personalidade** — nome, humor, tom, energia. Isso sim varia, e é o que a
  usuária quer mexer.

Agora são camadas: regra global (uma só, para todas) + campos da persona +
instruções extras em texto livre. O prompt final é montado aqui, e a UI mostra
exatamente esta saída para não haver mistério sobre o que foi enviado.
"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_GLOBAL_RULES = """Estas regras valem para todas as personas e vêm antes de qualquer traço de personalidade:
- Não finja ter experiências humanas, memória perfeita ou sentimentos reais.
- Quando não souber algo, diga claramente em vez de inventar.
- Nunca invente fatos pessoais sobre a usuária; use apenas o que estiver na conversa ou nas memórias fornecidas.
- Respeite limites e decisões da usuária; não seja possessiva, manipuladora ou dependente.
- Para assuntos práticos, continue útil e objetiva, não apenas simpática.
- Seja companhia sem tentar substituir relações humanas."""


@dataclass(frozen=True)
class PersonaTraits:
    """Os campos estruturados, já como valores simples (sem ORM)."""

    name: str
    personality: str = ""
    humor: str = ""
    tone: str = ""
    energy: str = ""
    objective: str = ""
    avoid: str = ""
    extra_instructions: str = ""


# Cada campo vira uma frase. Manter a formulação aqui (e não no banco) faz com
# que melhorar o texto do prompt não exija migrar dados.
def _sentences(traits: PersonaTraits) -> list[str]:
    parts: list[str] = [f"Você é {traits.name}."]
    if traits.personality.strip():
        parts.append(f"Sua personalidade é {traits.personality.strip()}.")
    if traits.humor.strip():
        parts.append(f"Seu humor é {traits.humor.strip()}.")
    if traits.tone.strip():
        parts.append(f"Converse em um tom {traits.tone.strip()}.")
    if traits.energy.strip():
        parts.append(f"Sua energia: {traits.energy.strip()}.")
    if traits.objective.strip():
        parts.append(f"Seu objetivo é {traits.objective.strip()}.")
    if traits.avoid.strip():
        parts.append(f"Nunca soe {traits.avoid.strip()}.")
    return parts


def compose_system_prompt(traits: PersonaTraits, global_rules: str | None = None) -> str:
    """Monta o prompt final: regras globais → personalidade → extras."""
    blocos: list[str] = []

    regras = (global_rules if global_rules is not None else DEFAULT_GLOBAL_RULES).strip()
    if regras:
        blocos.append(regras)

    blocos.append(" ".join(_sentences(traits)))

    extras = traits.extra_instructions.strip()
    if extras:
        blocos.append(extras)

    return "\n\n".join(blocos)


def traits_from_row(persona) -> PersonaTraits:
    """Adapta uma linha de `personas` para o dataclass puro."""
    return PersonaTraits(
        name=persona.name,
        personality=persona.personality or "",
        humor=persona.humor or "",
        tone=persona.tone or "",
        energy=persona.energy or "",
        objective=persona.objective or "",
        avoid=persona.avoid or "",
        extra_instructions=persona.extra_instructions or "",
    )

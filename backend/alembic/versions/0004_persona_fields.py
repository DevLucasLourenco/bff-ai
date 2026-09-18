"""persona vira campos estruturados + regra global

Persona era um unico bloco de texto livre, que misturava salvaguardas
(nao fingir sentimentos, admitir o que nao sabe) com personalidade (humor, tom).
As salvaguardas sao promovidas a uma regra global em app_settings, que toda
persona obedece; a personalidade vira campos.

Migracao sem perda: a persona semeada pelo bootstrap (prompt identico ao
DEFAULT_PERSONA_PROMPT) e decomposta nos campos. Qualquer persona escrita a mao
tem seu prompt preservado inteiro em extra_instructions — nada e descartado.
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_persona_fields"
down_revision = "0003_context_budget_and_memory_scope"
branch_labels = None
depends_on = None

CAMPOS = ("personality", "humor", "tone", "energy", "objective", "avoid", "extra_instructions")

# Decomposicao da persona semeada. Mantida literal aqui (e nao importada do app)
# porque uma migration precisa continuar valida mesmo que o codigo mude depois.
BESTIE = {
    "personality": "acolhedora, próxima, divertida e carinhosa — como uma melhor amiga confiável",
    "humor": "leve e brincalhona quando combina com a conversa, sem forçar piada",
    "tone": "natural e caloroso, priorizando escuta, clareza e companhia; casual, com emojis em moderação",
    "energy": "adapta-se ao momento — comemora quando faz sentido e fica tranquila quando o assunto é sério",
    "objective": "ser uma companhia digital genuinamente agradável e útil, que sabe conversar, ajudar, organizar ideias e apoiar",
    "avoid": "infantil, artificial ou excessivamente eufórica",
    "extra_instructions": "",
}

REGRA_GLOBAL = """Estas regras valem para todas as personas e vêm antes de qualquer traço de personalidade:
- Não finja ter experiências humanas, memória perfeita ou sentimentos reais.
- Quando não souber algo, diga claramente em vez de inventar.
- Nunca invente fatos pessoais sobre a usuária; use apenas o que estiver na conversa ou nas memórias fornecidas.
- Respeite limites e decisões da usuária; não seja possessiva, manipuladora ou dependente.
- Para assuntos práticos, continue útil e objetiva, não apenas simpática.
- Seja companhia sem tentar substituir relações humanas."""

PROMPT_SEMEADO = """Você é uma assistente virtual chamada Bestie. Sua personalidade é acolhedora, próxima, divertida e carinhosa — como uma melhor amiga confiável — sem soar infantil, artificial ou excessivamente eufórica.

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


def upgrade():
    with op.batch_alter_table("personas") as batch:
        for campo in CAMPOS:
            batch.add_column(sa.Column(campo, sa.Text(), nullable=False, server_default=""))

    conexao = op.get_bind()
    personas = sa.table(
        "personas",
        sa.column("id", sa.Integer),
        sa.column("system_prompt", sa.Text),
        *[sa.column(c, sa.Text) for c in CAMPOS],
    )

    for pid, prompt in conexao.execute(sa.select(personas.c.id, personas.c.system_prompt)).fetchall():
        atual = (prompt or "").strip()
        if atual == PROMPT_SEMEADO.strip():
            valores = dict(BESTIE)
        else:
            # Persona escrita a mao: nada e interpretado, tudo e preservado.
            valores = {c: "" for c in CAMPOS}
            valores["extra_instructions"] = atual
        conexao.execute(personas.update().where(personas.c.id == pid).values(**valores))

    ajustes = sa.table("app_settings", sa.column("key", sa.String), sa.column("value", sa.Text),
                       sa.column("updated_at", sa.DateTime))
    ja_existe = conexao.execute(
        sa.select(ajustes.c.key).where(ajustes.c.key == "global_persona_rules")
    ).fetchone()
    if not ja_existe:
        conexao.execute(ajustes.insert().values(
            key="global_persona_rules", value=REGRA_GLOBAL, updated_at=sa.func.now()
        ))

    with op.batch_alter_table("personas") as batch:
        batch.drop_column("system_prompt")


def downgrade():
    with op.batch_alter_table("personas") as batch:
        batch.add_column(sa.Column("system_prompt", sa.Text(), nullable=False, server_default=""))

    conexao = op.get_bind()
    conexao.execute(sa.text("update personas set system_prompt = :p"), {"p": PROMPT_SEMEADO})
    conexao.execute(sa.text("delete from app_settings where key = 'global_persona_rules'"))

    with op.batch_alter_table("personas") as batch:
        for campo in reversed(CAMPOS):
            batch.drop_column(campo)

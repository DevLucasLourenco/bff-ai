"""Persona por campos + regra global.

A regra global existe porque salvaguardas (não fingir sentimentos, admitir o que
não sabe) não são personalidade: editá-las persona a persona deixava a
salvaguarda sumir sem ninguém notar.
"""

import json

from app.services.persona import DEFAULT_GLOBAL_RULES, PersonaTraits, compose_system_prompt


# ------------------------------------------------------------------ composição


def test_prompt_comeca_pela_regra_global():
    prompt = compose_system_prompt(PersonaTraits(name="Nina", personality="direta"))
    assert prompt.startswith(DEFAULT_GLOBAL_RULES)
    assert "Você é Nina." in prompt


def test_campos_vazios_nao_viram_frase_solta():
    prompt = compose_system_prompt(PersonaTraits(name="Nina"), global_rules="")
    assert prompt.strip() == "Você é Nina."


def test_cada_campo_preenchido_aparece_no_prompt():
    prompt = compose_system_prompt(
        PersonaTraits(
            name="Nina", personality="analítica", humor="seco", tone="formal",
            energy="estável", objective="destravar decisões", avoid="vaga",
            extra_instructions="Cite fontes quando houver.",
        ),
        global_rules="",
    )
    for trecho in ("analítica", "seco", "formal", "estável", "destravar decisões", "vaga"):
        assert trecho in prompt
    # Extras vêm por último, em bloco próprio.
    assert prompt.rstrip().endswith("Cite fontes quando houver.")


def test_regra_global_vazia_e_respeitada():
    prompt = compose_system_prompt(PersonaTraits(name="Nina"), global_rules="   ")
    assert not prompt.startswith("Estas regras")


# ------------------------------------------------------------------------ API


def test_bootstrap_semeia_bestie_em_campos(client):
    persona = client.get("/api/personas").json()[0]
    assert persona["name"] == "Bestie"
    assert "acolhedora" in persona["personality"]
    assert "sem forçar piada" in persona["humor"]
    assert "eufórica" in persona["avoid"]
    # O bloco de texto livre nasce vazio: tudo coube nos campos.
    assert persona["extra_instructions"] == ""
    assert "system_prompt" not in persona


def test_composed_prompt_mostra_o_que_sera_enviado(client):
    persona = client.get("/api/personas").json()[0]
    regras = client.get("/api/settings").json()["global_persona_rules"]
    assert persona["composed_prompt"].startswith(regras)
    assert "Você é Bestie." in persona["composed_prompt"]


def test_editar_um_campo_muda_o_prompt_composto(client):
    persona = client.get("/api/personas").json()[0]
    atualizada = client.patch(f"/api/personas/{persona['id']}", json={"humor": "humor seco e irônico"}).json()
    assert "humor seco e irônico" in atualizada["composed_prompt"]
    assert "sem forçar piada" not in atualizada["composed_prompt"]


def test_nome_de_persona_e_unico(client):
    assert client.post("/api/personas", json={"name": "Bestie"}).status_code == 409


def test_persona_nova_nasce_so_com_nome(client):
    criada = client.post("/api/personas", json={"name": "Coach"}).json()
    assert criada["personality"] == ""
    assert criada["composed_prompt"].strip().endswith("Você é Coach.")


# ------------------------------------------------- a regra global chega ao LLM


def test_regra_global_entra_no_prompt_da_conversa(client, fake_adapter):
    client.patch("/api/settings", json={"global_persona_rules": "REGRA-CANARIO: nunca prometa nada."})
    conversa = client.post("/api/conversations", json={}).json()["id"]

    adapter = fake_adapter()
    client.post(f"/api/conversations/{conversa}/messages/stream", json={"content": "oi"})

    system = next(m["content"] for m in adapter.received_messages if m["role"] == "system")
    assert system.startswith("REGRA-CANARIO: nunca prometa nada.")
    assert "Você é Bestie." in system


def test_mudar_a_persona_nao_apaga_a_regra_global(client, fake_adapter):
    persona = client.get("/api/personas").json()[0]
    # Mesmo esvaziando todos os campos, as salvaguardas continuam.
    client.patch(f"/api/personas/{persona['id']}", json={
        "personality": "", "humor": "", "tone": "", "energy": "", "objective": "", "avoid": "",
    })
    conversa = client.post("/api/conversations", json={}).json()["id"]

    adapter = fake_adapter()
    client.post(f"/api/conversations/{conversa}/messages/stream", json={"content": "oi"})

    system = json.dumps(adapter.received_messages, ensure_ascii=False)
    assert "Não finja ter experiências humanas" in system

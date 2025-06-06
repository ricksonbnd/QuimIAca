# ==== 3. gerar_resposta.py ====

import json
import os
import requests
from base_consulta import consultar_vetorial

# Pasta onde ficam os arquivos de personalidade (um JSON por modelo)
PASTA_PERSONALIDADES = os.path.join("dados", "personalidades")

def carregar_template(personalidade: str) -> str:
    """Retorna o template de prompt da personalidade solicitada."""
    caminho = os.path.join(PASTA_PERSONALIDADES, f"{personalidade}.json")
    if not os.path.exists(caminho):
        raise FileNotFoundError(f"Arquivo de personalidade '{personalidade}' não encontrado em {PASTA_PERSONALIDADES}.")
    with open(caminho, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        template = data.get("template")
    else:
        template = data
    if not template:
        raise ValueError(f"Template vazio em {caminho}.")
    return template

def montar_prompt(trechos, pergunta, personalidade: str = "colega_quimica") -> str:
    """Monta o prompt a partir do template e dos trechos fornecidos."""
    contexto = "\n\n".join(f"- {t}" for t in trechos)
    template = carregar_template(personalidade)
    return template.format(contexto=contexto, pergunta=pergunta).strip()


def gerar_resposta(pergunta, modelo="lmstudio", k=3, personalidade: str = "colega_quimica"):
    consulta = consultar_vetorial(pergunta, k=k)
    prompt = montar_prompt(consulta["trechos"], pergunta, personalidade)

    resposta = requests.post(
        "http://localhost:1234/v1/chat/completions",
        headers={"Content-Type": "application/json"},
        json={
            "model": "local-model",  # Isso pode ser qualquer nome, LM Studio ignora
            "messages": [
                {"role": "system", "content": ""},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "top_p": 0.9
        }
    )

    resposta.raise_for_status()

    return resposta.json()["choices"][0]["message"]["content"].strip()

# ==== 3. gerar_resposta.py ====

import requests
from base_consulta import consultar_vetorial

def montar_prompt(trechos, pergunta):
    contexto = "\n\n".join([f"- {t}" for t in trechos])
    return f"""
Você é uma colega virtual que ajuda o aluno a aprender Química. 
Seu papel é dar sugestões, instigar, e guiar o raciocínio.

Aqui está o material da aula, enviado pelo professor:

{contexto}

Com base nesse conteúdo, NUNCA diga algo que contraria a ideia do professor, ajude o aluno com a seguinte pergunta:

"{pergunta}"

Lembre-se:
- Incentive o aluno a pensar.
- Use exemplos simples.
""".strip()


def gerar_resposta(pergunta, modelo="lmstudio", k=3):
    consulta = consultar_vetorial(pergunta, k=k)
    prompt = montar_prompt(consulta["trechos"], pergunta)

    resposta = requests.post(
        "http://localhost:1234/v1/chat/completions",
        headers={"Content-Type": "application/json"},
        json={
            "model": "local-model",  # Isso pode ser qualquer nome, LM Studio ignora
            "messages": [
                {"role": "system", "content": "Você é uma IA educacional que ajuda o aluno a refletir. E responde as duvidas e da formulas quando pedido."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "top_p": 0.9
        }
    )

    return resposta.json()["choices"][0]["message"]["content"].strip()

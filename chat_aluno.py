# ==== 4. chat_aluno.py ====

import gradio as gr
from gerar_resposta import gerar_resposta
from base_consulta import consultar_vetorial

historico = []

def interagir(pergunta):
    resposta = gerar_resposta(pergunta)
    consulta = consultar_vetorial(pergunta)
    trechos = consulta["trechos"]

    interacao = {
        "pergunta": pergunta,
        "resposta": resposta,
        "trechos_usados": trechos
    }
    historico.append(interacao)

    trecho_formatado = "\n".join([f"\u2022 {t[:150]}..." for t in trechos])
    return resposta, trecho_formatado

def salvar_historico():
    import json
    with open("interacoes.json", "w", encoding="utf-8") as f:
        json.dump(historico, f, ensure_ascii=False, indent=2)
    return "Histórico salvo com sucesso!"

with gr.Blocks() as demo:
    gr.Markdown("Colega Virtual de Química\nConverse com a IA para tirar dúvidas, mas ela não vai te dar a resposta pronta 😉")
    with gr.Row():
        pergunta = gr.Textbox(label="Digite sua pergunta")
        botao = gr.Button("Perguntar")
    resposta = gr.Textbox(label="Resposta da IA", lines=6)
    trechos_usados = gr.Textbox(label="Trechos do material usados", lines=6)
    status = gr.Textbox(label="Status", value="", interactive=False)
    botao.click(fn=interagir, inputs=pergunta, outputs=[resposta, trechos_usados])
    gr.Button("Salvar histórico").click(fn=salvar_historico, outputs=status)

demo.launch()

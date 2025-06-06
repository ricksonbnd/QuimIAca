# ==== 4. chat_aluno.py ====

import os
import shutil
import gradio as gr
from gerar_resposta import gerar_resposta
from base_consulta import consultar_vetorial
from processar_aulas import processar_todos

PASTA_DESTINO = "dados/aulas_originais"

os.makedirs(PASTA_DESTINO, exist_ok=True)

historico = []

def interagir(pergunta):
    resposta = gerar_resposta(pergunta)
    consulta = consultar_vetorial(pergunta)
    trechos = consulta["trechos"]
    origens = consulta["origens"]

    interacao = {
        "pergunta": pergunta,
        "resposta": resposta,
        "trechos_usados": trechos
    }
    historico.append(interacao)

    trecho_formatado = "\n\n".join([
        f"\u2022 {t[:100]}... 📁 Origem: `{o[:50]}`"
        for t, o in zip(trechos, origens)
    ])
    return resposta, trecho_formatado


def salvar_historico():
    import json
    pasta = "historico"
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, "interacoes.json")

    historico_existente = []
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                historico_existente = json.load(f)
        except json.JSONDecodeError:
            historico_existente = []

    historico_existente.extend(historico)

    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(historico_existente, f, ensure_ascii=False, indent=2)
    return "Histórico salvo com sucesso!"

def salvar_arquivos(pdfs):
    nomes_salvos = []
    for pdf in pdfs:
        destino = os.path.join(PASTA_DESTINO, os.path.basename(pdf.name))
        shutil.copy(pdf.name, destino)
        nomes_salvos.append(destino)
    processar_todos()
    return f"✅ {len(nomes_salvos)} arquivo(s) salvo(s) em `{PASTA_DESTINO}`:\n\n" + "\n".join(nomes_salvos)




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

    ## função upar arquivos
    gr.Markdown("## 📘 Envie os PDFs para Análise")
    arquivos = gr.File(file_types=[".pdf",".txt"], file_count="multiple", label="PDFs e Textos")
    botao = gr.Button("Salvar Arquivos e Processar")
    saida = gr.Markdown()
    botao.click(fn=salvar_arquivos, inputs=arquivos, outputs=saida)

demo.launch()

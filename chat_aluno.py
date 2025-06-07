# ==== 4. chat_aluno.py ====

import os
import shutil
import gradio as gr
from gerar_resposta import gerar_resposta, montar_prompt
from base_consulta import consultar_vetorial
from processar_aulas import processar_todos, resetar_base

PASTA_DESTINO = "dados/aulas_originais"

os.makedirs(PASTA_DESTINO, exist_ok=True)

historico = []
mensagens_chat = []

def listar_personalidades():
    """Retorna a lista de personalidades disponíveis (arquivos JSON na pasta)."""
    pasta = os.path.join("dados", "personalidades")
    if not os.path.isdir(pasta):
        return []
    return [os.path.splitext(f)[0] for f in os.listdir(pasta) if f.endswith(".json")]

PERSONALIDADES = listar_personalidades()
PERSONALIDADE_PADRAO = "colega_quimica" if "colega_quimica" in PERSONALIDADES else (PERSONALIDADES[0] if PERSONALIDADES else "")

def interagir(pergunta, personalidade, opcao_trechos):
    global mensagens_chat
    resposta, consulta = gerar_resposta(
        pergunta,
        personalidade=personalidade,
        historico_chat=mensagens_chat,
    )
    trechos = consulta["trechos"]
    origens = consulta["origens"]

    prompt_atual = montar_prompt(trechos, pergunta, personalidade)
    mensagens_chat.append({"role": "user", "content": prompt_atual})
    mensagens_chat.append({"role": "assistant", "content": resposta})
    if len(mensagens_chat) > 10:
        mensagens_chat = mensagens_chat[-10:]

    interacao = {
        "pergunta": pergunta,
        "resposta": resposta,
        "trechos_usados": trechos,
        "personalidade": personalidade,
    }
    historico.append(interacao)

    trecho_formatado = "\n\n".join(
        [f"\u2022 {t[:100]}... \ud83d\udcc1 Origem: `{o[:50]}`" for t, o in zip(trechos, origens)]
    )
    return resposta, gr.update(
        value=trecho_formatado, visible=opcao_trechos == "Mostrar"
    )


def salvar_historico():
    import json
    pasta = "historico"
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, "interacoes.json")
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(historico, f, ensure_ascii=False, indent=2)
    return "Histórico salvo com sucesso!"

def carregar_historico():
    import json
    global historico, mensagens_chat
    pasta = "historico"
    caminho = os.path.join(pasta, "interacoes.json")
    if not os.path.exists(caminho):
        historico = []
        mensagens_chat = []
        return "Nenhum histórico encontrado."
    with open(caminho, "r", encoding="utf-8") as f:
        historico = json.load(f)

    mensagens_chat = []
    for inter in historico:
        trechos = inter.get("trechos_usados", [])
        personalidade = inter.get("personalidade", PERSONALIDADE_PADRAO)
        prompt = montar_prompt(trechos, inter.get("pergunta", ""), personalidade)
        mensagens_chat.append({"role": "user", "content": prompt})
        mensagens_chat.append({"role": "assistant", "content": inter.get("resposta", "")})
    if len(mensagens_chat) > 10:
        mensagens_chat = mensagens_chat[-10:]
    return "Histórico carregado com sucesso!"

def limpar_historico():
    global historico, mensagens_chat
    pasta = "historico"
    caminho = os.path.join(pasta, "interacoes.json")
    if os.path.exists(caminho):
        os.remove(caminho)
    historico = []
    mensagens_chat = []
    return "Histórico apagado."

def salvar_arquivos(pdfs):
    nomes_salvos = []
    for pdf in pdfs:
        destino = os.path.join(PASTA_DESTINO, os.path.basename(pdf.name))
        shutil.copy(pdf.name, destino)
        nomes_salvos.append(destino)
    processar_todos()
    return f"✅ {len(nomes_salvos)} arquivo(s) salvo(s) em `{PASTA_DESTINO}`:\n\n" + "\n".join(nomes_salvos)


def resetar_dados():
    resetar_base()
    return "✅ Base de dados resetada!"


carregar_historico()


with gr.Blocks() as demo:
    gr.Markdown("Colega Virtual de Química\nConverse com a IA para tirar dúvidas, mas ela não vai te dar a resposta pronta 😉")
    with gr.Row():
        pergunta = gr.Textbox(label="Digite sua pergunta")
        personalidade = gr.Dropdown(label="Personalidade", choices=PERSONALIDADES, value=PERSONALIDADE_PADRAO)
        botao = gr.Button("Perguntar")
    resposta = gr.Textbox(label="Resposta da IA", lines=6)
    mostrar_trechos = gr.Radio([
        "Mostrar",
        "Ocultar",
    ], value="Ocultar", label="Trechos")
    trechos_usados = gr.Textbox(
        label="Trechos do material usados", lines=6, visible=False
    )
    mostrar_trechos.change(
        lambda opcao: gr.update(visible=opcao == "Mostrar"),
        inputs=mostrar_trechos,
        outputs=trechos_usados,
    )
    status = gr.Textbox(label="Status", value="", interactive=False)

    botao.click(
        fn=interagir,
        inputs=[pergunta, personalidade, mostrar_trechos],
        outputs=[resposta, trechos_usados],
    )

    pergunta.submit(fn=interagir, inputs=[pergunta, personalidade, mostrar_trechos], outputs=[resposta, trechos_usados])
    gr.Button("Salvar histórico").click(fn=salvar_historico, outputs=status)
    gr.Button("Carregar histórico").click(fn=carregar_historico, outputs=status)
    gr.Button("Limpar histórico").click(fn=limpar_historico, outputs=status)
    gr.Button("Resetar base").click(fn=resetar_dados, outputs=status)

    ## função upar arquivos
    gr.Markdown("## 📘 Envie os PDFs para Análise")
    arquivos = gr.File(file_types=[".pdf",".txt"], file_count="multiple", label="PDFs e Textos")
    botao = gr.Button("Salvar Arquivos e Processar")
    saida = gr.Markdown()
    botao.click(fn=salvar_arquivos, inputs=arquivos, outputs=saida)

demo.launch()

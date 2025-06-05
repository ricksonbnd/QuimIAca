# ==== 1. processar_aulas.py ====

import os
import json
import fitz  # PyMuPDF
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

PASTA_AULAS = "dados/aulas_originais"
PASTA_CHUNKS = "dados/chunks"
PASTA_FAISS = "dados/faiss_index"

model = SentenceTransformer("all-MiniLM-L6-v2")

def extrair_texto_pdf(caminho_pdf):
    texto = ""
    with fitz.open(caminho_pdf) as doc:
        for pagina in doc:
            texto += pagina.get_text()
    return texto

def dividir_em_chunks(texto, tamanho=50):
    palavras = texto.split()
    chunks = []
    for i in range(0, len(palavras), tamanho):
        trecho = " ".join(palavras[i:i+tamanho])
        if len(trecho.strip()) > 0:
            chunks.append(trecho)
    return chunks

def processar_todos():
    print("🚀 Função processar_todos foi chamada")
    todos_chunks = []
    vetores = []

    print("🔍 Iniciando processamento dos arquivos em:", PASTA_AULAS)

    arquivos = os.listdir(PASTA_AULAS)
    if not arquivos:
        print("⚠️ Nenhum arquivo encontrado na pasta de aulas.")
        return

    for nome_arquivo in arquivos:
        caminho = os.path.join(PASTA_AULAS, nome_arquivo)

        if nome_arquivo.endswith(".pdf"):
            texto = extrair_texto_pdf(caminho)
        elif nome_arquivo.endswith(".txt"):
            with open(caminho, "r", encoding="utf-8") as f:
                texto = f.read()
        else:
            print(f"⏭️ Ignorando arquivo não suportado: {nome_arquivo}")
            continue

        if not texto.strip():
            print(f"⚠️ Arquivo vazio: {nome_arquivo}")
            continue

        print(f"📄 Processando: {nome_arquivo}")
        chunks = dividir_em_chunks(texto, tamanho=50)
        print(f"  ➕ {len(chunks)} chunks gerados")

        for i, chunk in enumerate(chunks):
            todos_chunks.append({
                "id": f"{nome_arquivo}_{i}",
                "texto": chunk,
                "origem": nome_arquivo,
                "ordem": i
            })
            vetor = model.encode(chunk)
            vetores.append(vetor)

    if not vetores:
        print("❌ Nenhum vetor gerado. Verifique se os arquivos têm conteúdo suficiente.")
        return

    os.makedirs(PASTA_CHUNKS, exist_ok=True)
    os.makedirs(PASTA_FAISS, exist_ok=True)

    with open(os.path.join(PASTA_CHUNKS, "base_chunks.json"), "w", encoding="utf-8") as f:
        json.dump(todos_chunks, f, indent=2, ensure_ascii=False)

    dim = len(vetores[0])
    index = faiss.IndexFlatL2(dim)
    index.add(np.array(vetores))
    faiss.write_index(index, os.path.join(PASTA_FAISS, "index.bin"))

    print(f"✅ Processamento completo: {len(todos_chunks)} chunks gerados.")

if __name__ == "__main__":
    processar_todos()

    
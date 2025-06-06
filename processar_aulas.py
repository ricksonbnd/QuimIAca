# processar_aulas.py

import os
import json
import fitz  # PyMuPDF para leitura de PDFs
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
import nltk
from nltk.tokenize import sent_tokenize
import argparse

# Diretórios de entrada e saída
PASTA_AULAS   = "dados/aulas_originais"
PASTA_CHUNKS  = "dados/chunks"
PASTA_FAISS   = "dados/faiss_index"
JSON_CHUNKS   = os.path.join(PASTA_CHUNKS, "base_chunks.json")
INDEX_FAISS   = os.path.join(PASTA_FAISS,  "index.bin")
META_FAISS    = os.path.join(PASTA_FAISS,  "meta.json")

# Modelo de embedding
model = SentenceTransformer("all-MiniLM-L6-v2")  # dimensão típica = 384

# 1) Certificar que 'punkt' está disponível
try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt")

def extrair_texto_pdf(caminho_pdf: str) -> str:
    """
    Abre um PDF e retorna todo o texto concatenado.
    """
    texto = ""
    with fitz.open(caminho_pdf) as doc:
        for pagina in doc:
            texto += pagina.get_text()
    return texto


def dividir_em_chunks_por_sentenca(texto: str, max_tokens: int = 100) -> list[str]:
    """
    Divide o texto em chunks de até ~max_tokens tokens, agrupando sentenças inteiras.
    Usa o tokenizador de sentenças do NLTK (punkt).
    """
    try:
        sentencas = sent_tokenize(texto, language="portuguese")
    except LookupError:
        # Caso não tenha o modelo “portuguese”, tenta inglês
        sentencas = sent_tokenize(texto, language="english")
        
    chunks = []
    buffer = []
    count = 0

    for s in sentencas:
        # Conta tokens da sentença usando o tokenizer interno do SentenceTransformer
        tam = len(model.tokenizer.tokenize(s))
        if count + tam <= max_tokens:
            buffer.append(s)
            count += tam
        else:
            if buffer:
                chunks.append(" ".join(buffer))
            buffer = [s]
            count = tam

    if buffer:
        chunks.append(" ".join(buffer))

    return chunks


def contar_chunks_existentes() -> int:
    """
    Retorna quantos chunks já estão gravados em base_chunks.json.
    Se o arquivo não existir, retorna 0.
    """
    if not os.path.exists(JSON_CHUNKS):
        return 0
    with open(JSON_CHUNKS, "r", encoding="utf-8") as f:
        base_chunks = json.load(f)
    return len(base_chunks)


def carregar_ou_criar_indice(dim: int):
    """
    Se já existir um índice FAISS em INDEX_FAISS e o JSON de chunks,
    carrega ambos. Caso contrário, cria um índice IndexIVFFlat vazio,
    treina com vetores aleatórios (placeholder) e salva.
    """
    os.makedirs(PASTA_CHUNKS, exist_ok=True)
    os.makedirs(PASTA_FAISS,  exist_ok=True)

    if os.path.exists(INDEX_FAISS) and os.path.exists(JSON_CHUNKS):
        # Carrega lista de chunks e índice existente
        with open(JSON_CHUNKS, "r", encoding="utf-8") as f:
            base_chunks = json.load(f)
        index = faiss.read_index(INDEX_FAISS)
        if not os.path.exists(META_FAISS):
            with open(META_FAISS, "w", encoding="utf-8") as f:
                json.dump({"full_trained": False}, f)
    else:
        # Cria do zero
        base_chunks = []
        nlist = 100  # Número de clusters para IVF (ajuste conforme volume esperado)
        quantizer = faiss.IndexFlatL2(dim)
        index = faiss.IndexIVFFlat(quantizer, dim, nlist, faiss.METRIC_L2)
        # Treinar com vetores aleatórios como placeholder (1000 vetores aleatórios)
        placeholder = np.random.rand(1000, dim).astype("float32")
        index.train(placeholder)
        faiss.write_index(index, INDEX_FAISS)
        # Inicializa JSON vazio
        with open(JSON_CHUNKS, "w", encoding="utf-8") as f:
            json.dump(base_chunks, f, ensure_ascii=False, indent=2)
        # Cria metadata inicial
        with open(META_FAISS, "w", encoding="utf-8") as f:
            json.dump({"full_trained": False}, f)

    return base_chunks, index


def precisa_treinar_de_verdade(total_chunks: int) -> bool:
    """
    Retorna True apenas quando já houver pelo menos 1000 chunks e o
    índice ainda **não** tiver sido treinado com embeddings reais.
    """
    meta = {"full_trained": False}
    if os.path.exists(META_FAISS):
        try:
            with open(META_FAISS, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except json.JSONDecodeError:
            meta = {"full_trained": False}
    return total_chunks >= 1000 and not meta.get("full_trained", False)


def re_treinar_indice_com_chunks_reais(base_chunks: list[dict], index: faiss.IndexIVFFlat):
    """
    Recria o índice FAISS do zero usando embeddings reais de todos os chunks.
    1) Gera embeddings em batch para cada chunk em base_chunks.
    2) Cria um novo IndexIVFFlat e chama train() com esses embeddings.
    3) Adiciona todos os embeddings ao novo índice e persiste.
    """
    textos = [c["texto"] for c in base_chunks]
    print(f"🔄 Gerando embeddings reais para {len(textos)} chunks...")
    embeddings = model.encode(textos, batch_size=32, convert_to_numpy=True).astype("float32")

    dim = embeddings.shape[1]
    nlist = int(np.sqrt(len(embeddings))) or 1
    quantizer = faiss.IndexFlatL2(dim)
    new_index = faiss.IndexIVFFlat(quantizer, dim, nlist, faiss.METRIC_L2)

    print(f"🔄 Treinando novo índice IVF com {len(embeddings)} vetores (nlist={nlist})...")
    new_index.train(embeddings)
    new_index.add(embeddings)

    faiss.write_index(new_index, INDEX_FAISS)
    with open(META_FAISS, "w", encoding="utf-8") as f:
        json.dump({"full_trained": True}, f)
    print("✅ Índice re-treinado com embeddings reais.")
    return new_index


def limpar_chunks() -> None:
    """Remove o arquivo JSON que armazena todos os chunks."""
    if os.path.exists(JSON_CHUNKS):
        os.remove(JSON_CHUNKS)
        print("🗑️  base_chunks.json removido.")
    else:
        print("ℹ️  Nenhum base_chunks.json para remover.")


def limpar_indice() -> None:
    """Remove o índice FAISS armazenado em disco."""
    if os.path.exists(INDEX_FAISS):
        os.remove(INDEX_FAISS)
        print("🗑️  index.bin removido.")
    else:
        print("ℹ️  Nenhum index.bin para remover.")
    if os.path.exists(META_FAISS):
        os.remove(META_FAISS)


def limpar_aulas() -> None:
    """Apaga arquivos de aulas já enviados, mantendo o .gitkeep."""
    if not os.path.exists(PASTA_AULAS):
        return
    for nome in os.listdir(PASTA_AULAS):
        if nome == ".gitkeep":
            continue
        caminho = os.path.join(PASTA_AULAS, nome)
        if os.path.isfile(caminho):
            os.remove(caminho)
    print("🗑️  Arquivos em aulas_originais removidos.")


def resetar_base() -> None:
    """Limpa arquivos de chunks, índice e PDFs de origem."""
    limpar_chunks()
    limpar_indice()
    limpar_aulas()
    print("✅ Base de dados resetada.")


def processar_todos():
    """
    Fluxo principal:
    1) Carrega (ou cria) índice FAISS e base_chunks.
    2) Verifica novos arquivos em PASTA_AULAS que ainda não foram processados.
    3) Gera chunks (por sentença) para cada novo arquivo.
    4) Faz batch encode desses novos chunks e adiciona incrementalmente ao índice.
    5) Grava JSON atualizado de base_chunks e o índice FAISS.
    6) Se total_chunks >= 1000, re-treina o índice com embeddings reais de todos os chunks.
    """
    arquivos = os.listdir(PASTA_AULAS)
    if not arquivos:
        print("⚠️ Nenhum arquivo encontrado em dados/aulas_originais.")
        return

    # Exemplo de dimensão de embedding (all-MiniLM-L6-v2 → 384)
    dim_example = 384

    # 1) Carregar ou criar índice e lista de chunks
    base_chunks, index = carregar_ou_criar_indice(dim_example)

    novos_chunks = []
    for nome_arquivo in arquivos:
        caminho = os.path.join(PASTA_AULAS, nome_arquivo)

        # Só processa PDF ou TXT
        if not nome_arquivo.lower().endswith((".pdf", ".txt")):
            continue

        # Pula arquivo se já estiver em base_chunks (campo "origem")
        if any(c["origem"] == nome_arquivo for c in base_chunks):
            continue

        # 2) Extrair texto
        if nome_arquivo.lower().endswith(".pdf"):
            texto = extrair_texto_pdf(caminho)
        else:
            with open(caminho, "r", encoding="utf-8") as f:
                texto = f.read()

        if not texto.strip():
            print(f"⚠️ Arquivo vazio: {nome_arquivo}")
            continue

        # 3) Dividir em chunks por sentença
        chunks_do_arquivo = dividir_em_chunks_por_sentenca(texto, max_tokens=100)
        print(f"📄 {nome_arquivo} → {len(chunks_do_arquivo)} chunks")

        for i, chunk in enumerate(chunks_do_arquivo):
            novos_chunks.append({
                "id":     f"{nome_arquivo}_{i}",
                "texto":  chunk,
                "origem": nome_arquivo,
                "ordem":  i
                # Deixamos embedding vazio; será gerado em batch
            })

    if not novos_chunks:
        print("✅ Não há novos chunks para adicionar.")
        return

    # 4) Em batch, gerar embeddings para todos os novos chunks
    textos = [c["texto"] for c in novos_chunks]
    print(f"🔍 Gerando embeddings para {len(textos)} novos chunks...")
    embeddings = model.encode(textos, batch_size=32, convert_to_numpy=True).astype("float32")

    # 5) Adicionar incrementalmente ao índice FAISS e atribuir faiss_id
    for idx, chunk_meta in enumerate(novos_chunks):
        faiss_id = index.ntotal  # índice disponível antes de inserir
        chunk_meta["faiss_id"] = faiss_id
        index.add(embeddings[idx:idx+1])

    # 6) Atualizar JSON de chunks e persistir o índice
    base_chunks.extend(novos_chunks)
    with open(JSON_CHUNKS, "w", encoding="utf-8") as f:
        json.dump(base_chunks, f, ensure_ascii=False, indent=2)

    faiss.write_index(index, INDEX_FAISS)
    total_chunks = len(base_chunks)
    print(f"✅ Adicionados {len(novos_chunks)} novos chunks. Total atual: {total_chunks} chunks.")

    # 7) Caso atinja 1000 ou mais, re-treinar com embeddings reais
    if precisa_treinar_de_verdade(total_chunks):
        # Recarrega JSON atualizado e re-treina
        with open(JSON_CHUNKS, "r", encoding="utf-8") as f:
            base_atualizado = json.load(f)
        index = re_treinar_indice_com_chunks_reais(base_atualizado, index)
    else:
        faltam = 1000 - total_chunks
        print(f"ℹ️ Ainda faltam {faltam} chunks para treinar com embeddings reais.")

    print("🚀 Processamento concluído.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Processa ou limpa a base de dados")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Remove arquivos de chunks e índice para começar do zero",
    )
    args = parser.parse_args()
    if args.reset:
        resetar_base()
    else:
        processar_todos()

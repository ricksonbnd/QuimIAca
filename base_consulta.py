# ==== 2. consulta.py ====

from sentence_transformers import SentenceTransformer
import faiss
import json

model = SentenceTransformer("all-MiniLM-L6-v2")
index = faiss.read_index("dados/faiss_index/index.bin")

with open("dados/chunks/base_chunks.json", "r", encoding="utf-8") as f:
    chunks = json.load(f)

def consultar_vetorial(pergunta, k=3):
    pergunta_vec = model.encode([pergunta])
    distancias, indices = index.search(pergunta_vec, k)
    trechos = [chunks[i]["texto"] for i in indices[0]]
    pontuacoes = [float(d) for d in distancias[0]]
    return {
        "trechos": trechos,
        "indices": indices[0].tolist(),
        "pontuacoes": pontuacoes
    }

# ==== 2. consulta.py ====

from sentence_transformers import SentenceTransformer
import faiss
import json

model = SentenceTransformer("all-MiniLM-L6-v2")

def consultar_vetorial(pergunta, k=5):
    index = faiss.read_index("dados/faiss_index/index.bin")

    with open("dados/chunks/base_chunks.json", "r", encoding="utf-8") as f:
        chunks = json.load(f)


    pergunta_vec = model.encode([pergunta])
    distancias, indices = index.search(pergunta_vec, k)

    trechos = []
    origens = []
    for i in indices[0]:
        trechos.append(chunks[i]["texto"])
        origens.append(chunks[i].get("origem", "desconhecido"))

    return {
        "trechos": trechos,
        "origens": origens,
        "indices": indices[0].tolist(),
        "pontuacoes": [float(d) for d in distancias[0]]
    }

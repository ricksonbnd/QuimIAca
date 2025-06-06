# QuimIAca

Projeto experimental de assistente virtual para alunos de Química. Os scripts permitem processar o material das aulas (PDF ou texto), gerar um índice vetorial com FAISS e interagir com uma IA via interface web.

## Instalação

1. Tenha o Python instalado (recomenda‑se Python 3.10+).
2. Instale as dependências:

```bash
pip install -r requirements.txt
```

## Processamento das aulas

Coloque os arquivos das aulas em `dados/aulas_originais/` e execute:

```bash
python processar_aulas.py
```

Esse comando extrai o texto dos PDFs/TXT, cria *chunks* de sentenças, gera os embeddings com `sentence-transformers` e monta o índice FAISS em `dados/faiss_index/`.

## Chat com o aluno

Para abrir a interface web do assistente, execute:

```bash
python chat_aluno.py
```

A página do Gradio permite enviar uma pergunta. O script usa `gerar_resposta.py` para chamar um servidor compatível com a API OpenAI (ex.: LM Studio) que deve estar rodando em `http://localhost:1234`.

Há um menu suspenso **Personalidade** para escolher qual arquivo de template usar na resposta.

Também há um botão "Resetar base" para apagar os arquivos processados e recomeçar do zero.

## Scripts auxiliares

- **base_consulta.py** – realiza a busca vetorial nos chunks usando FAISS.
- **gerar_resposta.py** – monta o prompt a partir dos trechos encontrados e envia para o servidor de linguagem.
- **dados/personalidades/** – contém um arquivo `.json` para cada personalidade de prompt.

Na interface `chat_aluno.py` há um menu para escolher entre essas personalidades antes de enviar a pergunta.

Para criar novas personalidades, adicione um JSON em `dados/personalidades` com a chave `"template"` contendo o texto do prompt. O nome do arquivo (sem extensão) é o identificador usado por `gerar_resposta.py`.


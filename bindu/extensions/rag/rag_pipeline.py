from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from openai import OpenAI
import os

emb_model = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en")

if not os.getenv("OPENROUTER_API_KEY"):
    raise ValueError("OPENROUTER_API_KEY not set")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

def run_rag(question: str):

    data = """
    LangChain is a framework for developing applications powered by language models.
    """

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_text(data)

    docs = [Document(page_content=c) for c in chunks]
    vectorstore = FAISS.from_documents(docs, emb_model)

    retriever = vectorstore.as_retriever(search_kwargs={"k": 1})
    retrieved_docs = retriever.invoke(question)

    context = retrieved_docs[0].page_content

    response = client.chat.completions.create(
        model="openrouter/auto",
        messages=[
            {"role": "system", "content": "Answer using context only"},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion:{question}"}
        ],
    )

    return response.choices[0].message.content
from operator import itemgetter
import os
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from werkzeug.utils import secure_filename

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain.schema.output_parser import StrOutputParser
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.memory import ConversationBufferMemory
from langchain_core.runnables import RunnableMap

UPLOAD_FOLDER = './uploads'
ALLOWED_EXTENSIONS = {'pdf'}

app = Flask(__name__)
app.secret_key = "secretKey"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    api_key="api_key",
    max_output_tokens=5000
)

#------초기 데이터 (pdf) 설정-------
subjects = {
    "ComputerPrograming": {
        "kor_name": "컴퓨터프로그래밍",
        "pdf_paths": [
            #"C:\\Users\\han-n\\OneDrive\\바탕 화면\\pdf_ai\\data\\12-1구조체-구조체의 정의.pdf",
            #"C:\\Users\\han-n\\OneDrive\\바탕 화면\\pdf_ai\\data\\12-2구조체-구조체와 포인터.pdf"
        ],
    },
}

def initialize_subjects(subjects: dict):
    embedding_model = HuggingFaceEmbeddings(
        model_name="jhgan/ko-sroberta-nli",
        encode_kwargs={'normalize_embeddings': True}
    )
    for subject_id, data in subjects.items():
        all_docs = []
        for path in data["pdf_paths"]:
            loader = PyMuPDFLoader(path)
            pages = loader.load_and_split()
            all_docs.extend(pages)

        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        split_docs = splitter.split_documents(all_docs)

        vectordb = Chroma.from_documents(
            split_docs,
            embedding_model,
            persist_directory=f"./chroma_store/{subject_id}",
            collection_name=f"db_{subject_id}"
        )
        retriever = vectordb.as_retriever()
        data["retriever"] = retriever
        data["memory"] = ConversationBufferMemory(return_messages=True)

def create_chain(subject_display_name: str, retriever):
    system_template = SystemMessagePromptTemplate.from_template(
        "당신은 친절하고 정확한 {subject} 과목의 한국어 AI 튜터입니다."
    )
    human_template = HumanMessagePromptTemplate.from_template(
        "다음은 학습 자료에서 발췌한 내용입니다:{context}\n위 자료를 참고하여 질문에 대해 가능한 구체적이고 자세하게 설명해주세요.\n질문: {question}"
    )
    chat_template = ChatPromptTemplate.from_messages([system_template, human_template])
    chain = create_stuff_documents_chain(llm, chat_template)

    rag_chain = (
        {
            "context": itemgetter("question") | retriever,
            "question": itemgetter("question"),
            "subject": itemgetter("subject"),
        }
        | RunnableMap({
            "answer": chain | StrOutputParser(),
            "sources": itemgetter("context"),
        })
    )
    return rag_chain

def translate_subject_id(user_subject: str):
    for sid, data in subjects.items():
        if data["kor_name"] == user_subject:
            return sid
    return None

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == "admin" and password == "1234":
            session["user"] = username
            return redirect(url_for("chat"))
        else:
            return "로그인 실패! 다시 시도하세요."
    return render_template("home.html")

@app.route("/chat")
def chat():
    if "user" not in session:
        return redirect(url_for("home"))
    return render_template("chat.html")

@app.route('/ask', methods=['POST'])
def ask():
    data = request.get_json() or {}
    user_subject = data.get("subject")
    question = data.get("question")

    subject_id = translate_subject_id(user_subject)
    if not subject_id:
        return jsonify({"error": f"Unknown subject: {user_subject}"}), 400

    chain = subjects[subject_id]["chain"]
    result = chain.invoke({
        "question": question,
        "subject": subjects[subject_id]["kor_name"]
    })

    answer = result["answer"]
    sources = []
    for doc in result["sources"][:5]:
        sources.append({
            "page": doc.metadata.get("page", "unknown"),
            "sources": doc.metadata.get("sources", "unknown"),
            "snippet": (doc.page_content or "")[:200]
        })

    return jsonify({"answer": answer, "sources": sources})

if __name__ == '__main__':
    initialize_subjects(subjects)
    for sid, data in subjects.items():
        data["chain"] = create_chain(
            retriever=data["retriever"],
            subject_display_name=data["kor_name"]
        )
    app.run(port=5000, debug=True)


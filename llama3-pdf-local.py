import os
import threading
import time
import sys
from itertools import cycle
from dotenv import load_dotenv
from langchain_community.document_loaders.pdf import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma.vectorstores import Chroma
from langchain_core.prompts.chat import ChatPromptTemplate
from langchain.chains.combine_documents.stuff import create_stuff_documents_chain
from langchain.chains.retrieval import create_retrieval_chain
from langchain_community.chat_models.ollama import ChatOllama
from langchain_community.embeddings.sentence_transformer import SentenceTransformerEmbeddings
from prompt import system_prompt

load_dotenv()

llm = ChatOllama(model="llama3.1:8b", base_url="http://127.0.0.1:11434/")

directory_path = os.path.abspath("data")
vectorstore_path = "vectorstore"


# Function to show a dot-based rotating circle as a processing indicator
def show_processing_indicator():
    for char in cycle(['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']):
        if stop_indicator:
            break
        sys.stdout.write(char)
        sys.stdout.flush()
        sys.stdout.write('\b')
        time.sleep(0.1)


# Check if vectorstore already exists
if os.path.exists(vectorstore_path):
    print("Loading existing vectorstore...")
    embedding_function = SentenceTransformerEmbeddings(model_name='all-MiniLM-L6-v2')
    vectorstore = Chroma(persist_directory=vectorstore_path, embedding_function=embedding_function)
else:
    # Validate directory
    if not os.path.isdir(directory_path):
        raise ValueError(f"Directory path {directory_path} is not valid or does not exist.")

    # Load PDF documents
    documents = []
    for filename in os.listdir(directory_path):
        if filename.endswith(".pdf"):
            filepath = os.path.join(directory_path, filename)
            loader = PyPDFLoader(filepath)
            documents.extend(loader.load())

    # Split the documents into chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    splits = text_splitter.split_documents(documents)

    # Prepare embeddings
    embedding_function = SentenceTransformerEmbeddings(model_name='all-MiniLM-L6-v2')
    texts = [split.page_content for split in splits]
    vectorstore = Chroma.from_texts(texts=texts, embedding=embedding_function, persist_directory=vectorstore_path)
    print("Embeddings created and vectorstore saved.")

# Use the loaded or newly created vectorstore
retriever = vectorstore.as_retriever()

# Create the prompt template
prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", "{input}")])

# Create the question-answer chain
question_answer_chain = create_stuff_documents_chain(llm, prompt)

# Create the retrieval augmented generation (RAG) chain
rag_chain = create_retrieval_chain(retriever, question_answer_chain)

# Chat loop
while True:
    query = input("Please ask a question (or type 'exit' or 'bye' to quit): \n")
    if query.lower() in ['exit', 'bye']:
        print("Goodbye!")
        break

    # Start the processing indicator in a separate thread
    stop_indicator = False
    indicator_thread = threading.Thread(target=show_processing_indicator)
    indicator_thread.start()

    # Collect the response
    response = []
    for s in rag_chain.stream({"input": query}):
        if "answer" in s.keys():
            response.append(s["answer"])

    # Stop the processing indicator
    stop_indicator = True
    indicator_thread.join()

    # Print the collected response word-by-word
    sys.stdout.write('\n')
    sys.stdout.flush()
    for word in " ".join(response).split():
        sys.stdout.write(word + ' ')
        sys.stdout.flush()
        time.sleep(0.2)
    print()  # Ensure there's a newline after the response is printed

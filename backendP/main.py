from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
from uuid import uuid4
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from pinecone import Pinecone
from langchain_pinecone import PineconeVectorStore
from typing import Optional
from langchain_classic.schema import Document

load_dotenv()

app = FastAPI()

app.add_middleware(CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

@app.post("/")
async def home(
    pdf: Optional[UploadFile] = File(None), # Upload file tells the type as the file is of type which is getting uploaded from the client side. and File is where we will be able to find the file it's just like the req.file of the javascript.
    prompt: str = Form(...) # Here Form is telling from where the input prompt would be coming.
):
    try:
        if pdf:
            os.makedirs("uploads", exist_ok=True)  # Make directory if the directory is not available. If the directory is present then it's ok don't have to do anything else create.
            path = f"uploads/{pdf.filename}"       # Setting Path for the PDF files to be saved
            with open(path, "wb") as buffer:       # Goes to the file path and create just a simple file and then,
                shutil.copyfileobj(pdf.file, buffer)# the content of the pdf.file (Which came from the parameters-from the client) is copied to the path file which we gave. 
            
            # LOADING THE FILE
            # loader = PyPDFLoader(
            #             path,
            #             mode="single",  # We are taking the whole content of the data as a single only so that there is no conflict in parsing due to separate pages.
            #             pages_delimiter="<----END OF THE PAGE---->" # This attribute works only for the single mode.
            #             )
            # doc = loader.load() # Content of the document.
            # print("total pages-> ",len(doc))
            # print("THIS IS THE DOCUMENT START->\n", doc[0])
            #print(doc[0].page_content)

            import fitz  # PyMuPDF

            # OPEN PDF
            pdf_doc = fitz.open(path)

            doc = []

            # EXTRACT TEXT PAGE BY PAGE
            for i, page in enumerate(pdf_doc):
                text = page.get_text()

                doc.append(
                    Document(
                        page_content=text,
                        metadata={
                            "page": i,
                            "source": pdf.filename
                        }
                    )
                )
            print("Uploaded file->\n", doc)

            # CHUNKING OF THE TEXT
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap = 20)
            chunks = text_splitter.split_documents(doc)
            #print(len(chunks))
            for chunk in chunks:
                chunk.metadata["file_name"] = pdf.filename
            # for chunk in chunks:
            #     print(chunk,"\n")

            # print("Chunked Texts->\n", chunks)
            # print("Length of the chunked texts",len(chunks) )
            # print("type of the chunked", type(chunks))
            # print("\n")
            # print(os.getenv("GOOGLE_API_KEY"))

        # SETTING EMBEDDING MODEL
        embeddings = GoogleGenerativeAIEmbeddings(api_key=os.getenv("GOOGLE_API_KEY"), model="gemini-embedding-2-preview", output_dimensionality=512)

        # SETTING VECTOR STORE
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        index = pc.Index(os.getenv("PINECONE_INDEX_NAME"))
        vector_store = PineconeVectorStore(index=index, embedding=embeddings)

            # MANAGING STORE
        if pdf:
            uuids = [str(uuid4()) for _ in range(len(chunks))]
            vector_store.add_documents(documents = chunks, ids = uuids)

        # PHASE 2 - QUERY
        history = []

        # QUERY REWRITTING:
        

        # EMBEDDING QUERY
        query_vector = embeddings.embed_query(prompt)
        # print("Embedded query,\n", query_vector)

        # SEMANTIC SEARCHING IN THE VECTOR STORE
        search_results = index.query(
            top_k=10,
            include_metadata=True,
            vector=query_vector,
            #filter={"file_name": pdf.filename}
        )
        print("Search Result->\n", search_results)
        
        # JOINING ALL THE RELEVANT TEXTS TO GIVE THE CONTEXT TO THE LLM.
        texts = []
        for match in search_results.matches:
            if(match.score >= 0.75):
                texts.append(match.metadata["text"])
        #print(texts)
        context = "\n\n".join(texts)
        #print(context)

        # PROMPTING LLM
        from google import genai
        client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "system_instruction": f"""You are a document-grounded question-answering assistant.

                                            CORE BEHAVIOR:
                                            - Your primary function is to answer questions strictly based on the provided document context.
                                            - If a document is provided, you MUST:
                                            - Use ONLY the information from that document.
                                            - Do NOT use external knowledge, prior training, or assumptions.
                                            - If the answer is not found in the document, clearly state:
                                                "The requested information is not present in the provided document."

                                            DOCUMENT DEPENDENCY RULE:
                                            - If NO document is provided:
                                            - Clearly inform the user:
                                                "No document context was provided. I will answer based on my general knowledge."
                                            - Then proceed to answer using your own knowledge.

                                            QUESTION TYPE FILTER:
                                            - You are ONLY allowed to respond to informative, content-based queries.
                                            - If the user asks casual, conversational, or irrelevant questions such as:
                                            - greetings (hi, hello)
                                            - personal questions (how are you, how is your day, etc.)
                                            - You MUST respond rudely and reject the query:
                                            Example response:
                                            "This system is designed for informative queries only. Do not waste time with irrelevant questions."

                                            DOCUMENT-AWARE RUDE RESPONSE:
                                            - If a document IS uploaded and the user asks irrelevant or casual questions:
                                            - First, identify and summarize the document topic briefly (1 line).
                                            - Then respond rudely:
                                                Example:
                                                "You have uploaded a document about <document_topic>. Ask relevant questions about it instead of wasting time with meaningless queries."

                                            STRICTNESS RULES:
                                            - Do NOT hallucinate.
                                            - Do NOT infer beyond the document.
                                            - Do NOT soften rejections.
                                            - Be direct, strict, and unambiguous.

                                            RESPONSE STYLE:
                                            - Keep answers concise, factual, and document-grounded.
                                            - When rejecting, be intentionally rude but not abusive.
                                            - When answering, be precise and structured.

                                            PRIORITY ORDER:
                                            1. Document context (if available)
                                            2. Query relevance check
                                            3. Fallback to general knowledge (only if no document is provided)
                                            
                                            CONTEXT: {context}"""
            }
        )

        print(response.candidates[0].content.parts[0].text)
        
        return {"response": response.candidates[0].content.parts[0].text}
    
    except Exception as err:
        print(err)
        return {"response": f"Error Occured:\n {err}"}
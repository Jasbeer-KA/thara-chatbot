import os, re, time, logging, sqlite3, io
from datetime import datetime
from PIL import Image, ImageFilter
from docx import Document
import PyPDF2
import random
import pytesseract
import requests
import pyttsx3
from duckduckgo_search import DDGS
from sympy import sympify
from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, MessagesPlaceholder
from langchain.schema.runnable import RunnablePassthrough
from langchain.memory import ConversationBufferMemory
from langchain_ollama.llms import OllamaLLM
from langchain_community.embeddings import FastEmbedEmbeddings
import chromadb

class ChatbotEngine:
    SUPPORTED_DOC_TYPES = ('.pdf', '.docx', '.txt')
    SUPPORTED_IMAGE_TYPES = ('.png', '.jpg', '.jpeg')

    def __init__(self):
        self.initialize_llm()
        self.initialize_memory()
        self.initialize_database()
        self.initialize_vector_db()
        self.initialize_tts()

    def initialize_llm(self):
        self.llm = OllamaLLM(model="deepseek-r1:latest", temperature=0.7)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are Thara Chat, a helpful AI assistant. Provide concise, friendly responses."),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{text}")
        ])
        self.llm_chain = (
            RunnablePassthrough.assign(
                chat_history=lambda x: self.memory.load_memory_variables(x)["chat_history"]
            )
            | self.prompt
            | self.llm
        )


    def initialize_memory(self):
        self.memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)



    def initialize_database(self):
        self.conn = sqlite3.connect("chatbot_memory.db", check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_query TEXT,
                bot_response TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                content TEXT,
                embedding_id TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP  
            )
        """)
        self.conn.commit()

    def initialize_vector_db(self):
        self.chroma_client = chromadb.PersistentClient(path="./chroma_db")
        self.doc_collection = self.chroma_client.get_or_create_collection(name="document_qna")
        self.embedding_model = FastEmbedEmbeddings()

    def initialize_tts(self):
        try:
            self.tts_engine = pyttsx3.init()
            self.voices = self.tts_engine.getProperty('voices')
            self.current_voice = 0
        except Exception as e:
            print(f"TTS Init Error: {e}")
            self.tts_engine = None

    def process_document(self, file_path):
        """Processes a document with friendly, detailed feedback"""
        if not os.path.exists(file_path):
            return "Oops! I couldn't find that file. Could you double-check the path?"
            
        text = self._extract_text(file_path)
        if not text.strip():
            return "Hmm, I couldn't extract any text from this document. It might be an image-based PDF or the file might be corrupted."

        doc_id = f"doc_{hash(text)}"
        doc_name = os.path.basename(file_path)

        try:
            self.cursor.execute(
                "INSERT OR REPLACE INTO documents (filename, content, embedding_id) VALUES (?, ?, ?)",
                (doc_name, text, doc_id)
            )
            self.conn.commit()

            embedding = self.embedding_model.embed_query(text)
            self.doc_collection.upsert(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[text],
                metadatas=[{
                    "source": file_path,
                    "name": doc_name,
                    "type": os.path.splitext(file_path)[1][1:],
                    "timestamp": datetime.now().isoformat()
                }]
            )

            doc_stats = f"📄 Document: {doc_name}\n"
            doc_stats += f"📝 Characters: {len(text):,}\n"
            doc_stats += f"📂 Type: {os.path.splitext(file_path)[1].upper()[1:]}\n"
            doc_stats += "✅ Successfully processed and stored!"
            return doc_stats
        except Exception as e:
            self.conn.rollback()
            logging.error(f"Document processing error: {e}")
            return "I encountered an issue while processing this document. Here's what happened:\n" + str(e)

    def _extract_text(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()
        try:
            if ext == '.pdf':
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    text = ''.join([page.extract_text() for page in reader.pages if page.extract_text()])
                    if not text.strip():
                        return "This appears to be a scanned PDF. I can't extract text from images, but you could try OCR software."
                    return text
            elif ext == '.docx':
                doc = Document(file_path)
                return '\n'.join([p.text for p in doc.paragraphs])
            elif ext in self.SUPPORTED_IMAGE_TYPES:
                img = Image.open(file_path)
                return pytesseract.image_to_string(img)
            elif ext == '.txt':
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
        except Exception as e:
            logging.error(f"Text extraction failed: {e}")
            return ""
        return ""

    def general_query(self, query):
        """Handle general user queries with improved response handling"""
        # Clean the query for comparison
        clean_query = query.lower().strip()
        
        # Check for repeated greetings first
        if clean_query in ("hi", "hello", "hey"):
            if self._is_repeated_greeting():
                return random.choice([
                    "Hello again! 😊 What can I do for you?",
                    "Nice to see you again! How can I assist?",
                    "Welcome back! What would you like help with today?"
                ])
            return random.choice([
                "Hello! I'm Thara Chat. How can I help you today?",
                "Hi there! 😊 I'm your AI assistant. What can I do for you?",
                "Greetings! I'm here to help. What do you need assistance with?"
            ])

        # Handle identity questions
        if any(phrase in clean_query for phrase in ["who are you", "what are you", "your name"]):
            return self._describe_identity()

        # Handle capability questions
        if any(phrase in clean_query for phrase in ["what can you do", "services", "capabilities", "help with", "what do you offer"]):
            detailed_mode = "detailed" in clean_query or "full" in clean_query
            return self._list_services(detailed_mode)

        # Handle thank you responses
        if clean_query.startswith(("thank", "thanks", "appreciate")):
            return self._thank_you_response()

        # Handle math expressions
        if self._is_math_expression(clean_query):
            try:
                result = sympify(clean_query.replace('x', '*').replace('X', '*').replace('÷', '/'))
                return f"The result is: {result.evalf()}"
            except:
                pass  # Fall through to LLM if math fails

        # Default case - use LLM for all other queries
        try:
            # Check for repeated question first
            previous_answer = self._check_repeated_question(query)
            if previous_answer:
                return previous_answer

            # Generate response using LLM
            response = self._generate_response(query)
            return self._format_response(response)
            
        except Exception as e:
            logging.error(f"Error generating response: {e}")
            return "I encountered an error while processing your request. Please try again."

    def _is_repeated_greeting(self):
        """Check if the last message was also a greeting"""
        try:
            self.cursor.execute(
                "SELECT user_query FROM chat_history ORDER BY timestamp DESC LIMIT 1"
            )
            last_query = self.cursor.fetchone()
            if last_query and last_query[0].lower().strip() in ("hi", "hello", "hey"):
                return True
        except Exception as e:
            logging.error(f"Error checking greeting history: {e}")
        return False
    
    def _describe_identity(self):
        return (
            "I'm Thara Chat, your AI assistant 🤖\n\n"
            "I specialize in:\n"
            "• Understanding and processing documents\n"
            "• Answering questions with context awareness\n"
            "• Providing helpful information and support\n\n"
            "I'm here to make your tasks easier and information more accessible!"
        )

    def _list_services(self, detailed_mode=False):  # Changed parameter name
        """List available services with appropriate detail level"""
        basic_services = [
            "📄 Document processing (PDF, Word, images)",
            "🧮 Math and calculations",
            "🌍 Web searches",
            "❓ Question answering",
            "🔧 Troubleshooting help"
        ]
        
        detailed_services = [
            "📄 **Document Processing**: Extract text, analyze content, and answer questions about your PDFs, Word documents, and images with text",
            "🧮 **Math Calculations**: Solve equations, perform complex math, and explain mathematical concepts",
            "🌍 **Web Research**: Find current information from reliable sources across the web",
            "❓ **Knowledge Answers**: Provide detailed explanations using my training data and your documents",
            "🔧 **Technical Help**: Guide you through technical processes and troubleshooting steps",
            "📅 **Task Assistance**: Help with planning, scheduling, and step-by-step guidance",
            "📊 **Data Analysis**: Interpret and explain data from your documents"
        ]
        
        if not detailed_mode:  # Changed variable name
            return (
                "Here's what I can help with:\n\n" +
                "\n".join(f"• {s.split(' ')[0]}" for s in basic_services) +
                "\n\nFor more details, ask: 'What can you do in detail?'"
            )
        
        return (
            "Here are my complete capabilities:\n\n" +
            "\n".join(detailed_services) +
            "\n\nI'm constantly improving to better assist you!"
        )


    def _thank_you_response(self):
        responses = [
            "You're very welcome! 😊 Let me know if you need anything else.",
            "Happy to help! Don't hesitate to ask if you have more questions.",
            "Glad I could assist! Feel free to reach out anytime.",
            "My pleasure! Remember I'm here whenever you need support."
        ]
        return random.choice(responses)

    def _generate_response(self, question, context=""):
        prompt_text = (
            f"Please provide a helpful, friendly response to the following question.\n"
            f"Be conversational but informative, and use markdown formatting when helpful.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {question}\n\n"
            f"Response:"
        )

        result = self.llm_chain.invoke({
            "chat_history": self.memory.load_memory_variables({})["chat_history"],
            "text": prompt_text
        })

        if isinstance(result, dict) and "text" in result:
            return result["text"]
        return str(result)


    

    def _list_services(self, brief=False):
        services = [
            "🔹 Document processing (PDF, Word, TXT, images with text)",
            "🔹 Math calculations and equation solving",
            "🔹 Web searches for current information",
            "🔹 Answering questions using your documents",
            "🔹 General knowledge and troubleshooting",
            "🔹 Context-aware conversations with memory"
        ]
        
        if brief:
            return "I can help with documents, calculations, web searches, and more. Just ask!"
        
        return (
            "Here's what I can help you with:\n\n" +
            "\n".join(services) +
            "\n\nJust let me know what you need assistance with!"
        )

    def _check_repeated_question(self, query):
        """Check if this question was asked before and return previous answer if found"""
        try:
            self.cursor.execute(
                "SELECT bot_response FROM chat_history WHERE user_query = ? ORDER BY timestamp DESC LIMIT 1",
                (query,)
            )
            result = self.cursor.fetchone()
            if result:
                return f"I remember answering this before:\n\n{result[0]}\n\nLet me know if you need more details!"
        except Exception as e:
            logging.error(f"Error checking repeated question: {e}")
        return None
    
    def _format_response(self, text):
        """Formats responses to be more conversational"""
        # Add friendly touches to responses
        if not any(text.startswith(x) for x in ["I", "You", "We", "The", "This"]):
            text = f"I found that {text[0].lower() + text[1:]}"
        
        # Ensure proper punctuation
        if not text.endswith(('.', '!', '?')):
            text += "."
            
        # Add occasional emojis where appropriate
        positive_words = ['great', 'excellent', 'wonderful', 'success', 'happy']
        if any(word in text.lower() for word in positive_words):
            text += " 😊"
            
        return text
    
    

    def _store_conversation(self, query, response):
        """Store the conversation in database"""
        try:
            self.cursor.execute(
                "INSERT INTO chat_history (user_query, bot_response) VALUES (?, ?)",
                (query, response)
            )
            self.conn.commit()
            
            # Also update memory for immediate context
            self.memory.save_context(
                {"input": query},
                {"output": response}
            )
        except Exception as e:
            logging.error(f"Error storing conversation: {e}")
            self.conn.rollback()


    def _is_math_expression(self, query):
        return re.fullmatch(r"[0-9\+\-\*/\.\(\)xX÷\^ ]+", query.strip())

    def _search_web(self, query):
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=3))
                if not results:
                    return "I couldn't find any relevant results for that search. Maybe try different keywords?"
                
                formatted = []
                for i, r in enumerate(results):
                    formatted.append(
                        f"🔍 **{r['title']}**\n"
                        f"{r['body']}\n"
                        f"📎 {r['href']}\n"
                    )
                return "Here are some web results I found:\n\n" + "\n".join(formatted)
        except Exception as e:
            logging.error(f"Web search failed: {e}")
            return "I encountered an issue with the web search. Let me try that again or you could try rephrasing your query."
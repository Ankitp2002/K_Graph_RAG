from typing import Union

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
import spacy


class LLMManager:
    __slot__ = ["available_client"]

    def __init__(self):
        self.available_client: dict[str, Union[ChatGroq, ChatGoogleGenerativeAI]] = {}

    def initialize(self):
        # =====================================================================
        # GROK Models
        # =====================================================================
        self.available_client["llm_gpt_oss_120"] = ChatGroq(
            model="openai/gpt-oss-120b", temperature=0
        )
        self.available_client["llm_vision_llama_17b"] = ChatGroq(
            model="meta-llama/llama-4-scout-17b-16e-instruct", temperature=0.3
        )
        # =====================================================================

        # =====================================================================
        # Gemini Models
        # =====================================================================
        self.available_client["llm_gemini_2_5_flash"] = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", temperature=0
        )
        # =====================================================================

    def get_embeddings_model(self):
        ## Return embeddings model
        return HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )

    def get_nlp_model(self):
        # Load spaCy NLP model for Local Entity Recognition
        return spacy.load("en_core_web_sm")

    def get_client(self, model_name: str) -> Union[ChatGroq, ChatGoogleGenerativeAI]:
        if model_name not in self.available_client:
            raise ValueError(
                f"Model {model_name} is not available. Please check the model name."
            )
        return self.available_client[model_name]

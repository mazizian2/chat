from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
print("OPENAI_API_KEY",api_key)
llm = ChatOpenAI(
    temperature=0.2,
    model="gpt-4",
    openai_api_key=api_key
)
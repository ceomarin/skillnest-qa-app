from dotenv import load_dotenv
import os
from langchain_google_genai import ChatGoogleGenerativeAI

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate


load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
modelo = ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite")

plantilla = PromptTemplate.from_template("Explica el concepto de {tema} en un párrafo,""para alguien que recién empieza en {area}.")

cadena_simple = plantilla | modelo | StrOutputParser()
#prompt = cadena_simple.invoke({"tema": "tokenización", "area": "procesamiento de texto"})
#print(prompt)
#print(prompt)




plantilla_conrol = ChatPromptTemplate.from_messages([
    ("system", "Eres un asistente útil."),
    ("user", "Explica el concepto de {tema} en un párrafo,""para alguien que recién empieza en {area}.")
])

cadena_conrol = plantilla_conrol | modelo | StrOutputParser()
resultado = cadena_conrol.invoke({"tema": "tokenización", "area": "procesamiento de texto"})

print(resultado)
import os
import sqlalchemy
from dotenv.main import load_dotenv
from prompt import sql_prompt
from langchain_ollama.chat_models import ChatOllama
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_core.messages.system import SystemMessage
from langchain_core.messages.human import HumanMessage
from langgraph.prebuilt.chat_agent_executor import create_react_agent


load_dotenv()

llm = ChatOllama(model="llama3.1:8b", base_url="http://127.0.0.1:11434/")

connection_string = sqlalchemy.URL.create(
        "mssql+pyodbc",
        username=os.environ["DB_USERNAME"],
        password=os.environ["DB_PASSWORD"],
        host=os.environ["DB_SERVER_NAME"],
        database=os.environ["DB_DATABASE"],
        query={"driver": os.environ["DB_DRIVER"]},
    )
db = SQLDatabase.from_uri(connection_string)
toolkit = SQLDatabaseToolkit(db=db, llm=llm)
tools = toolkit.get_tools()

system_message = SystemMessage(content=sql_prompt)
agent_executor = create_react_agent(llm, tools, state_modifier=system_message)
print("Please ask your question.")
user_input = input("You: ")
response = agent_executor.invoke({"messages": [HumanMessage(content=user_input)]})
print("Bot: ", response["messages"][-1].content)

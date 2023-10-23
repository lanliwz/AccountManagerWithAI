from langchain.prompts.prompt import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.chains import GraphCypherQAChain
from langchain.graphs import Neo4jGraph
import os, logging,sys

def create_qa_chain():
    url=os.getenv("Neo4jFinDBUrl")
    username=os.getenv("Neo4jFinDBUserName")
    password=os.getenv("Neo4jFinDBPassword")
    database=os.getenv("Neo4jFinDBName")
    graph = Neo4jGraph(
        url=url, username=username, password=password, database=database
    )

    CYPHER_GENERATION_TEMPLATE = (
        """Task:Generate Cypher statement to query a graph database.
        Instructions:
        Use only the provided relationship types and properties in the schema.
        Do not use any other relationship types or properties that are not provided.
        Schema:
        {schema}
        Note: Do not include any explanations or apologies in your responses.
        Do not respond to any questions that might ask anything else than for you to construct a Cypher statement.
        Do not include any text except the generated Cypher statement.
        The balance of the account is Billed + Paid
        
        # how much money paid to account address, the address start with '100 Main Street', ignore case, confirmed on year 2023"
        MATCH (a:Account)<-[:FOR]-(p:Payment)-[:CONFIRMED_BY]->(c:Confirmation)
        WHERE toLower(a.address) STARTS WITH '100 main street' AND c.timestamp =~ '.*2023.*'
        RETURN SUM(p.amount)"""
    
        """# What is the balance of tax account, the address of the account starts with '100 Main Street', ignore case, for year 2023"
        MATCH (a:Account)<-[:BILL_FOR]-(b:JerseyCityTaxBilling)
        WHERE toLower(a.address) STARTS WITH '100 main street' AND b.Year='2023'
        RETURN SUM(b.Billed) + SUM(b.Paid) AS AccountBalance
        
        The question is:
        {question}"""
    )

    CYPHER_GENERATION_PROMPT = PromptTemplate(
        input_variables=["schema", "question"], template=CYPHER_GENERATION_TEMPLATE
    )

    chain = GraphCypherQAChain.from_llm(
        ChatOpenAI(temperature=0), graph=graph, verbose=True, cypher_prompt=CYPHER_GENERATION_PROMPT
    )

    return chain


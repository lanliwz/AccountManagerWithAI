from bs4 import BeautifulSoup
from datetime import datetime
import json
import requests
from jcTaxJson2node import to_neo4j_statement
import os

def extract_tax_as_neo_stmt(account: str) -> list[str]:
    url = f"http://taxes.cityofjerseycity.com/ViewPay?accountNumber={account}"
    html = requests.get(url).content

    # Parse the HTML
    soup = BeautifulSoup(html, 'html.parser')

    # Find the table
    table = soup.find('table')

    # Find all the rows in the table
    rows = table.find_all('tr')

    # Get the headers
    headers_raw = [header.text.strip() for header in rows[0].find_all('th')]
    headers = ['Due Date' if x == 'Tr. / Due Date' else x for x in headers_raw]

    # Initialize an empty list to hold the row data
    table_data = []

    # Iterate over the rows
    for row in rows[1:]:
        row_data = {}
        # Find all the columns in the row
        cols = row.find_all('td')
        for i, col in enumerate(cols):
            text = col.text.strip()
            # If it's the due date column, convert the text to a date
            if headers[i] == 'Due Date':
                text = datetime.strptime(text, "%m/%d/%Y").date()
            # If it's the Paid column and the value is in brackets, make it negative
            elif headers[i] == 'Paid/Adjusted' and text.startswith('($') and text.endswith(')'):
                text = -float(text[2:-1].replace(',', '').replace('$', ''))
            # Otherwise just clean up the text
            elif text.startswith('$'):
                text = float(text.replace(',', '').replace('$', ''))
            row_data[headers[i]] = text
        table_data.append(row_data)
    return to_neo4j_statement(account,table_data)

def load2neo4j():
    from neo4j_storage.dataService import FinGraphDB
    neo4j_url=os.getenv("Neo4jFinDBUrl")
    username=os.getenv("Neo4jFinDBUserName")
    password=os.getenv("Neo4jFinDBPassword")
    database=os.getenv("Neo4jFinDBName")

    mydb = FinGraphDB(neo4j_url, username, password, database)

    accounts=mydb.get_account_number()
    for account in accounts:
        for stmt in extract_tax_as_neo_stmt(account):
            print(stmt)
            mydb.create_object(stmt)

    mydb.create_bill_for_rel("JerseyCityTaxBilling")
    mydb.close()

load2neo4j()
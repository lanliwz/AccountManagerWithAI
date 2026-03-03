from neo4j import GraphDatabase

class FinGraphDB:
    def __init__(self, uri, user, password,database_name):
        self._driver = GraphDatabase.driver(uri, auth=(user, password),database=database_name)


    def close(self):
        self._driver.close()

    def create_node(self, label, properties):
        with self._driver.session() as session:
            session.execute_write(self._create_node, label, properties)

    def create_object(self, query):
        with self._driver.session() as session:
            session.execute_write(self._create_object, query)

    def run_write(self, query, params=None):
        with self._driver.session() as session:
            session.execute_write(self._run_query, query, params or {})

    def replace_account_tax_history(self, account_properties, billing_rows, payment_rows):
        with self._driver.session() as session:
            session.execute_write(
                self._upsert_account,
                account_properties,
            )
            session.execute_write(self._delete_account_tax_history, account_properties["Account"])
            if billing_rows:
                session.execute_write(
                    self._insert_tax_rows,
                    "TaxBilling",
                    "BILL_FOR",
                    billing_rows,
                )
            if payment_rows:
                session.execute_write(
                    self._insert_tax_rows,
                    "TaxPayment",
                    "PAYMENT_FOR",
                    payment_rows,
                )

    def get_account_number(self):
        with self._driver.session() as session:
            return session.execute_read(self._get_accounts)


    @staticmethod
    def _get_accounts(tx):
            result = tx.run("MATCH (n:Account) RETURN n.Account as account_num")
            return [record["account_num"] for record in result]

    @staticmethod
    def _create_node(tx, label, properties):
        # Creating a Cypher query to create a node
        query = f"CREATE (a:{label} {{properties}})"
        tx.run(query, properties=properties)

    @staticmethod
    def _create_object(tx, query):
        tx.run(query)

    @staticmethod
    def _run_query(tx, query, params):
        tx.run(query, **params)

    def create_node_and_relationship(self, node1_label, node1_properties, relationship_type, node2_label, node2_properties):
        with self._driver.session() as session:
            session.execute_write(self._create_node_rel, node1_label, node1_properties, relationship_type, node2_label, node2_properties)

    def create_bill_for_rel(self, billingLabel):
        with self._driver.session() as session:
            session.execute_write(self._create_bill_for_rel, billingLabel)
    @staticmethod
    def _create_node_rel(tx, node1_label, node1_properties, relationship_type, node2_label, node2_properties):
        # Creating a Cypher query to create a node and relationship
        query = (
            f"CREATE (a:{node1_label} {{properties}}) "
            f"-[:{relationship_type}]-> "
            f"(b:{node2_label} {{properties}})"
        )

        # Execute the query
        tx.run(query, properties=node1_properties)
        tx.run(query, properties=node2_properties)

    @staticmethod
    def _create_bill_for_rel(tx, billingLabel):
        # Creating a Cypher query to create JerseyCityTaxBilling to Account and relationship
        query = (
            f"MATCH (n:{billingLabel}),(a:Account)"
            "WHERE a.Account=n.Account and not exists((n)-[:BILL_FOR]->(a))" 
            "CREATE (n)-[r:BILL_FOR]->(a)"
        )
        print(query)
        tx.run(query)

    @staticmethod
    def _upsert_account(tx, account_properties):
        tx.run(
            """
            MERGE (a:Account {Account: $Account})
            SET a += $account_properties
            """,
            Account=account_properties["Account"],
            account_properties=account_properties,
        )

    @staticmethod
    def _delete_account_tax_history(tx, account_number):
        tx.run(
            """
            MATCH (n)
            WHERE n.Account = $Account
              AND (n:JerseyCityTaxBilling OR n:TaxBilling OR n:TaxPayment)
            DETACH DELETE n
            """,
            Account=account_number,
        )

    @staticmethod
    def _insert_tax_rows(tx, node_label, relationship_type, rows):
        if node_label == "TaxBilling" and relationship_type == "BILL_FOR":
            tx.run(
                """
                UNWIND $rows AS row
                MERGE (n:TaxBilling {sourceId: row.sourceId})
                SET n += row
                WITH n, row
                MATCH (a:Account {Account: row.Account})
                MERGE (n)-[:BILL_FOR]->(a)
                """,
                rows=rows,
            )
            return

        if node_label == "TaxPayment" and relationship_type == "PAYMENT_FOR":
            tx.run(
                """
                UNWIND $rows AS row
                MERGE (n:TaxPayment {sourceId: row.sourceId})
                SET n += row
                WITH n, row
                MATCH (a:Account {Account: row.Account})
                MERGE (n)-[:PAYMENT_FOR]->(a)
                """,
                rows=rows,
            )
            return

        raise ValueError(f"Unsupported tax row target: {node_label}/{relationship_type}")

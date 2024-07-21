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


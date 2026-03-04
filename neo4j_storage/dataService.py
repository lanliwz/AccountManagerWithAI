import hashlib
import json

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

    def append_account_ledger(self, account_properties, ledger_block, ledger_entries):
        with self._driver.session() as session:
            session.execute_write(
                self._upsert_account,
                account_properties,
            )
            session.execute_write(
                self._append_account_ledger,
                account_properties["Account"],
                ledger_block,
                ledger_entries,
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

    @staticmethod
    def _append_account_ledger(tx, account_number, ledger_block, ledger_entries):
        existing_block = tx.run(
            """
            MATCH (b:LedgerBlock {blockId: $blockId})
            RETURN b.blockId AS blockId
            """,
            blockId=ledger_block["blockId"],
        ).single()

        previous_tip = None
        if existing_block is None:
            previous_tip = tx.run(
                """
                MATCH (a:Account {Account: $Account})
                OPTIONAL MATCH (tip:LedgerBlock)-[:LEDGER_FOR]->(a)
                WHERE NOT EXISTS { MATCH (:LedgerBlock)-[:PREVIOUS_BLOCK]->(tip) }
                RETURN tip.blockId AS blockId,
                       tip.blockHash AS blockHash,
                       coalesce(tip.blockHeight, -1) AS blockHeight
                LIMIT 1
                """,
                Account=account_number,
            ).single()

        previous_hash = previous_tip["blockHash"] if previous_tip and previous_tip["blockId"] else None
        block_height = (
            previous_tip["blockHeight"] + 1 if previous_tip and previous_tip["blockId"] else 0
        )
        block_hash = hashlib.sha1(
            json.dumps(
                {
                    "blockId": ledger_block["blockId"],
                    "prevHash": previous_hash,
                    "sourceHash": ledger_block["sourceHash"],
                    "blockHeight": block_height,
                    "entryCount": ledger_block["entryCount"],
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

        block_properties = dict(ledger_block)
        block_properties["prevHash"] = previous_hash
        block_properties["blockHeight"] = block_height
        block_properties["blockHash"] = block_hash

        tx.run(
            """
            MERGE (b:LedgerBlock {blockId: $blockId})
            ON CREATE SET b += $block_properties
            WITH b
            MATCH (a:Account {Account: $Account})
            MERGE (b)-[:LEDGER_FOR]->(a)
            """,
            blockId=block_properties["blockId"],
            block_properties=block_properties,
            Account=account_number,
        )

        if previous_tip and previous_tip["blockId"]:
            tx.run(
                """
                MATCH (b:LedgerBlock {blockId: $blockId})
                MATCH (prev:LedgerBlock {blockId: $prevBlockId})
                MERGE (b)-[:PREVIOUS_BLOCK]->(prev)
                """,
                blockId=block_properties["blockId"],
                prevBlockId=previous_tip["blockId"],
            )

        if ledger_entries:
            tx.run(
                """
                UNWIND $entries AS entry
                MERGE (e:LedgerEntry {entryId: entry.entryId})
                ON CREATE SET e += entry
                WITH e, entry
                MATCH (b:LedgerBlock {blockId: $blockId})
                MERGE (b)-[:CONTAINS]->(e)
                WITH e, entry
                MATCH (a:Account {Account: entry.Account})
                MERGE (e)-[:FOR_ACCOUNT]->(a)
                """,
                entries=ledger_entries,
                blockId=block_properties["blockId"],
            )

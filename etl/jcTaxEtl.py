import argparse
from datetime import datetime
import os

import requests

try:
    from neo4j_storage.dataService import FinGraphDB
except ImportError:
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from neo4j_storage.dataService import FinGraphDB

try:
    from etl.jcTaxJson2node import (
        classify_tax_rows,
        normalize_account_properties,
        normalize_billing_rows,
    )
except ImportError:
    from jcTaxJson2node import (
        classify_tax_rows,
        normalize_account_properties,
        normalize_billing_rows,
    )


PROPERTY_TAX_INQUIRY_URL = "https://apps.hlssystems.com/JerseyCity/PropertyTaxInquiry/GetAccountDetails"
REQUEST_TIMEOUT_SECONDS = 30
DEFAULT_DATABASE = "taxjc"


def _format_interest_thru_date(target_date=None):
    date_value = target_date or datetime.now()
    return date_value.strftime("%a %b %d %Y")


def fetch_account_details(session, account_number, interest_thru_date=None):
    response = session.get(
        PROPERTY_TAX_INQUIRY_URL,
        params={
            "accountNumber": str(account_number),
            "interestThruDate": _format_interest_thru_date(interest_thru_date),
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    payload = response.json()
    if not payload.get("validAccountNumber"):
        raise ValueError(f"Invalid account returned by source: {account_number}")

    return payload["accountInquiryVM"]


def _parse_account_list(raw_accounts):
    if not raw_accounts:
        return None

    parsed_accounts = []
    for value in raw_accounts.split(","):
        account = value.strip()
        if not account:
            continue
        parsed_accounts.append(int(account))

    return parsed_accounts or None


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Refresh Jersey City tax billing and payment data into Neo4j. "
            "By default, this loads all Account nodes from taxjc."
        )
    )
    parser.add_argument(
        "--accounts",
        help="Comma-separated account numbers to refresh instead of querying all accounts from Neo4j.",
    )
    parser.add_argument(
        "--database",
        default=DEFAULT_DATABASE,
        help=f"Neo4j database to refresh. Default: {DEFAULT_DATABASE}.",
    )
    return parser.parse_args()


def load2neo4j(accounts=None, database=DEFAULT_DATABASE):
    neo4j_url = os.getenv("Neo4jFinDBUrl")
    username = os.getenv("Neo4jFinDBUserName")
    password = os.getenv("Neo4jFinDBPassword")

    mydb = FinGraphDB(neo4j_url, username, password, database)
    accounts_to_load = accounts or mydb.get_account_number()

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "JCTaxLedger ETL/1.0",
            "Accept": "application/json",
        }
    )

    try:
        for account in accounts_to_load:
            account_details = fetch_account_details(session, account)
            account_properties = normalize_account_properties(account_details)
            tax_rows = normalize_billing_rows(account_details)
            billing_rows, payment_rows = classify_tax_rows(tax_rows)
            mydb.replace_account_tax_history(
                account_properties,
                billing_rows,
                payment_rows,
            )
            print(
                f"Loaded account {account_properties['Account']} "
                f"(accountId={account_properties['accountId']}) with "
                f"{len(billing_rows)} billing rows and {len(payment_rows)} payment rows"
            )
    finally:
        session.close()
        mydb.close()


def main():
    args = parse_args()
    load2neo4j(
        accounts=_parse_account_list(args.accounts),
        database=args.database,
    )


if __name__ == "__main__":
    main()

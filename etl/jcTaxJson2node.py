import json
from jsonschema import validate

# Given JSON Schema
schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Billing",
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "Year": {"type": "string", "pattern": "^[0-9]{4}$"},
            "Qtr": {"type": "string", "pattern": "^[1-4]$"},
            "Due Date": {"type": "string", "format": "date"},
            "Description": {"type": "string"},
            "Billed": {"type": "number"},
            "Paid": {"type": "number"},
            "Open Balance": {"type": "number"},
            "Days": {"type": "string", "pattern": "^[0-9]+$"},
            "Interest Due": {"type": "number"},
            "Paid By": {"type": "string"},
        },
        "required": ["Year", "Qtr", "Due Date", "Description", "Billed", "Paid"],
    },
}


def to_neo4j_statement(account, billing_json):
    # Validate JSON against the schema
    # validate(instance=billing_json, schema=schema)

    statements = []
    for item in billing_json:
        # Base MERGE statement
        merge_stmt = (
            f'MERGE (n:JerseyCityTaxBilling {{Account: {account}, '
            f'Year: "{item["Year"]}", Qtr: "{item["Qtr"]}", '
            f'DueDate: "{item["Due Date"]}", Description: "{item["Description"]}", '
            f'Billed: {item["Billed"]}, Paid: {item["Paid/Adjusted"]}}}) '
        )

        # Additional SET statements for optional fields
        set_stmts = []
        for field in ["Open Balance", "Days", "Interest Due", "Paid By"]:
            if field in item:
                set_stmts.append(f'n.{field.replace(" ", "")} = {json.dumps(item[field])}')

        # Combine MERGE and SET statements
        if set_stmts:
            merge_stmt += "ON CREATE SET " + ", ".join(set_stmts)

        statements.append(merge_stmt)

    return statements



import hashlib
import json
from datetime import datetime


def _clean_text(value):
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_mmddyyyy(value):
    text = _clean_text(value)
    if not text:
        return None
    return datetime.strptime(text, "%m/%d/%Y").date().isoformat()


def build_tax_account_id(account_details):
    block = _clean_text(account_details.get("Block")) or ""
    lot = _clean_text(account_details.get("Lot")) or ""
    qualifier = _clean_text(account_details.get("Qualifier")) or ""
    account_number = account_details["AccountNumber"]
    return f"{account_number}: B- {block} L- {lot} Q- {qualifier}"


def normalize_account_properties(account_details):
    address = _clean_text(account_details.get("Address"))
    city_state = _clean_text(account_details.get("CityState"))
    postal_code = _clean_text(account_details.get("PostalCode"))

    mailing_parts = [part for part in [address, city_state, postal_code] if part]

    return {
        "Account": int(account_details["AccountNumber"]),
        "accountId": int(account_details["AccountId"]),
        "taxAccountId": build_tax_account_id(account_details),
        "address": ", ".join(mailing_parts) if mailing_parts else None,
        "ownerName": _clean_text(account_details.get("OwnerName")),
        "propertyLocation": _clean_text(account_details.get("PropertyLocation")),
        "block": _clean_text(account_details.get("Block")),
        "lot": _clean_text(account_details.get("Lot")),
        "qualifier": _clean_text(account_details.get("Qualifier")),
        "bankName": _clean_text(account_details.get("BankName")),
        "principal": float(account_details.get("Principal") or 0.0),
        "interest": float(account_details.get("Interest") or 0.0),
        "totalDue": float(account_details.get("TotalDue") or 0.0),
        "updatedFromSource": datetime.utcnow().isoformat(timespec="seconds"),
    }


def _build_source_id(account_number, detail):
    source_key = {
        "Account": int(account_number),
        "TaxYear": int(detail.get("TaxYear") or 0),
        "Quarter": int(detail.get("Quarter") or 0),
        "TransactionDate": _clean_text(detail.get("TransactionDate")),
        "Description": _clean_text(detail.get("Description")),
        "Type": int(detail.get("Type") or 0),
        "TransactionId": int(detail.get("TransactionId") or 0),
        "TransCode": int(detail.get("TransCode") or 0),
        "BillSequence": int(detail.get("BillSequence") or 0),
        "SortCode": int(detail.get("SortCode") or 0),
        "Billed": float(detail.get("Billed") or 0.0),
        "Paid": float(detail.get("Paid") or 0.0),
        "Adjusted": float(detail.get("Adjusted") or 0.0),
        "Balance": float(detail.get("Balance") or 0.0),
        "DepositNumber": int(detail.get("DepositNumber") or 0),
        "PaymentSourceDescription": _clean_text(detail.get("PaymentSourceDescription")),
    }
    payload = json.dumps(source_key, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def normalize_billing_rows(account_details):
    account_number = int(account_details["AccountNumber"])
    account_id = int(account_details["AccountId"])
    rows = []

    for detail in account_details.get("Details", []):
        transaction_date = _parse_mmddyyyy(detail.get("TransactionDate"))
        description = _clean_text(detail.get("Description"))
        payment_source = _clean_text(detail.get("PaymentSourceDescription"))
        created_by = _clean_text(detail.get("CreatedBy"))
        check_number = _clean_text(detail.get("CheckNumber"))

        row = {
            "sourceId": _build_source_id(account_number, detail),
            "Account": account_number,
            "AccountId": account_id,
            "Year": str(detail.get("TaxYear")),
            "Qtr": str(detail.get("Quarter")),
            "DueDate": transaction_date,
            "TransactionDate": transaction_date,
            "Description": description,
            "Type": int(detail.get("Type") or 0),
            "Billed": float(detail.get("Billed") or 0.0),
            "Paid": float(detail.get("Paid") or 0.0),
            "Adjusted": float(detail.get("Adjusted") or 0.0),
            "OpenBalance": float(detail.get("Balance") or 0.0),
            "InterestDue": float(detail.get("Interest") or 0.0),
            "Days": int(detail.get("Days") or 0),
            "BillSequence": int(detail.get("BillSequence") or 0),
            "TransactionId": int(detail.get("TransactionId") or 0),
            "TransCode": int(detail.get("TransCode") or 0),
            "DepositNumber": int(detail.get("DepositNumber") or 0),
            "SortCode": int(detail.get("SortCode") or 0),
            "PaymentSourceDescription": payment_source,
            "CheckNumber": check_number,
            "CreatedBy": created_by,
        }

        if payment_source:
            row["PaidBy"] = payment_source

        rows.append(row)

    return rows


def classify_tax_rows(rows):
    billing_rows = []
    payment_rows = []

    for row in rows:
        description = (row.get("Description") or "").lower()
        is_billing = row.get("Billed", 0.0) != 0.0 or "bill" in description

        if is_billing:
            billing_rows.append(row)
        else:
            payment_rows.append(row)

    return billing_rows, payment_rows

"""
Manual bootstrap script to seed DynamoDB with representative CDSCO NSQ and spurious alert records (§5.3).
Run this script on Day 1 to seed the database with real demoable data.
Usage:
    python scripts/seed_nsq_data.py
"""
import sys
from pathlib import Path

# Add backend directory to sys.path so scripts can import src
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from src.tools.aws import get_dynamodb_resource, convert_floats_to_decimals
from src.pipelines.nsq_ingestion.parser import parse_table_rows
from src.config import settings
from src.utils.logger import logger

# Representative dataset based on real CDSCO NSQ and spurious alert publications
SAMPLE_CDSCO_TABLE = [
    # Header row
    ["S.No", "Name of Drug / Product Name", "Batch Number", "Date of Mfg", "Date of Expiry", "Name and Address of Manufacturer", "Result of Test / NSQ Reason", "Testing Laboratory"],
    # Rows
    ["1", "Paracetamol Tablets IP 500mg", "T-2401", "01/2024", "12/2026", "M/s Alpha Pharmaceuticals Pvt. Ltd., Solan (H.P.)", "Sample fails in Dissolution test", "CDL, Kolkata"],
    ["2", "Amoxicillin & Potassium Clavulanate Tablets", "AMX-8012", "03/2024", "02/2026", "Cipla Limited, Verna, Goa", "Fails in Assay of Clavulanic Acid (74.2%)", "RDTL, Chandigarh"],
    ["3", "Pantoprazole Gastro-Resistant Tablets IP", "PNT-991", "05/2024", "04/2026", "Sun Pharma Laboratories Ltd., Sikkim", "Fails in Uniformity of Weight and Dissolution", "CDL, Kolkata"],
    ["4", "Ciprofloxacin Hydrochloride Tablets IP 500mg", "CIP-405", "02/2024", "01/2026", "M/s Generic Cure Pharma, Roorkee", "Spurious: The firm at given address does not exist. Fictitious manufacturer.", "CDL, Kolkata"],
    ["5", "Azithromycin Tablets IP 500mg", "AZI-772", "06/2024", "05/2026", "Alkem Laboratories Ltd., Baddi", "Fails in Description & Related Substances", "RDTL, Guwahati"],
    ["6", "Cough Relief Syrup (Dextromethorphan)", "CR-104", "04/2024", "03/2026", "M/s Wellness Remedies Pvt Ltd, Haridwar", "Sample contains diethylene glycol contaminant above permissible limit", "RDTL, Chandigarh"],
    ["7", "Telmisartan Tablets IP 40mg", "TEL-301", "07/2024", "06/2026", "Dr. Reddy's Laboratories Co., Hyderabad", "Fails in Assay test (83.1%)", "CDL, Kolkata"],
    ["8", "Paracetamol & Diclofenac Sodium Tablets", "PD-602", "08/2024", "07/2026", "M/s Fake Formulation India", "Spurious: Counterfeit packaging, not manufactured by genuine brand owner.", "CDL, Kolkata"],
]


def seed_database():
    """Seeds DynamoDB Batches and Manufacturers tables with CDSCO alerts."""
    print("Starting CDSCO alert data ingestion bootstrap...")
    items, error = parse_table_rows(
        table_matrix=SAMPLE_CDSCO_TABLE,
        source_month="2026-08",
        source_document_s3_key="nsq-pdfs/2026-08/CDL_Alert_Aug2026.pdf",
    )

    if error:
        print(f"Failed to parse seed table: {error}")
        return

    print(f"Successfully parsed {len(items)} alert records.")
    dynamo = get_dynamodb_resource()
    batches_table = dynamo.Table(settings.DYNAMODB_BATCHES_TABLE)
    mfr_table = dynamo.Table(settings.DYNAMODB_MANUFACTURERS_TABLE)

    mfr_counts = {}

    for item in items:
        # Write to Batches
        batches_table.put_item(Item=convert_floats_to_decimals(item))
        print(f"Ingested Batch: {item['batch_no']} ({item['drug_name']}) -> {item['alert_status']}")

        # Track manufacturer counters
        mfr_id = item["manufacturer_id_normalized"]
        if mfr_id not in mfr_counts:
            mfr_counts[mfr_id] = {
                "name": item["manufacturer_name"],
                "nsq_count": 0,
                "spurious_count": 0,
            }
        if item["alert_status"] == "SPURIOUS":
            mfr_counts[mfr_id]["spurious_count"] += 1
        else:
            mfr_counts[mfr_id]["nsq_count"] += 1

    # Write aggregate manufacturer metrics
    for mfr_id, data in mfr_counts.items():
        mfr_item = {
            "PK": f"MFR#{mfr_id}",
            "canonical_name": data["name"],
            "total_nsq_batches": data["nsq_count"],
            "total_spurious_batches": data["spurious_count"],
            "total_community_flagged_batches": 0,
        }
        mfr_table.put_item(Item=convert_floats_to_decimals(mfr_item))
        print(f"Updated Manufacturer: {mfr_id} (NSQ: {data['nsq_count']}, Spurious: {data['spurious_count']})")

    print("\nData seeding completed successfully! The database is now ready for testing.")


if __name__ == "__main__":
    seed_database()

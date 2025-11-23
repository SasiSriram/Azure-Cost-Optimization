import os
import csv
from dotenv import load_dotenv

from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.storage.blob import BlobServiceClient
from azure.mgmt.costmanagement import CostManagementClient
from settings import AUTO_DELETE , PROTECTED_TAG , REPORT_FILE


print("\n===== Azure Cost Optimization Tool =====\n")

# LOAD AZZURE CRENDENTIALS

load_dotenv("cred.env")
subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")

if not subscription_id:
    raise ValueError(" Subscription ID missing in cred.env")

credential = DefaultAzureCredential()

# CREATE AZURE CLIENTS

compute_client = ComputeManagementClient(credential, subscription_id)
storage_client = StorageManagementClient(credential, subscription_id)
cost_client = CostManagementClient(credential)

results = []


# HELP FUNCTIONS

def is_protected(tags: dict) -> bool:
    """Skip deletion if resource is tagged safe=yes."""
    return tags and tags.get(PROTECTED_TAG, "").lower() == "yes"


def log(rg, name, rtype, status):
    results.append([rg, name, rtype, status])


# SCANNERS 

def check_vms():
    print(" Checking VM Power States...")

    for vm in compute_client.virtual_machines.list_all():
        rg = vm.id.split("/")[4]
        instance = compute_client.virtual_machines.instance_view(rg, vm.name)
        states = [s.code for s in instance.statuses]

        if "PowerState/stopped" in str(states):
            log(rg, vm.name, "VM", "Stopped — billing may apply")
        elif "PowerState/deallocated" in str(states):
            log(rg, vm.name, "VM", "Deallocated — No cost")
        else:
            log(rg, vm.name, "VM", "Running")


def check_disks():
    print(" Finding unused disks...")

    for disk in compute_client.disks.list():
        rg = disk.id.split("/")[4]

        if disk.managed_by is None:
            status = "Unattached — recommended for cleanup"

            if is_protected(disk.tags):
                status = "⚠ Protected (safe=yes) — skipped"

            log(rg, disk.name, "Disk", status)

            if AUTO_DELETE and not is_protected(disk.tags):
                print(f"🗑 Removing disk: {disk.name}")
                compute_client.disks.begin_delete(rg, disk.name)


def check_storage():
    print(" Checking blob storage for empty containers...")

    for account in storage_client.storage_accounts.list():
        rg = account.id.split("/")[4]
        blob_client = BlobServiceClient(
            f"https://{account.name}.blob.core.windows.net/",
            credential
        )

        for container in blob_client.list_containers():
            items = list(blob_client.get_container_client(container.name).list_blobs(limit=1))
            if not items:
                log(rg, container.name, "Blob Container", "Empty — cleanup recommended")


# COST ANALYSIS 
def cost_analysis():
    print(" Analyzing monthly cost by resource group...")

    scope = f"/subscriptions/{subscription_id}"

    params = {
        "type": "Usage",
        "timeframe": "MonthToDate",
        "dataset": {
            "granularity": "None",
            "aggregation": {
                "totalCost": {"name": "PreTaxCost", "function": "Sum"}
            },
            "grouping": [{"type": "Dimension", "name": "ResourceGroupName"}],
        },
    }

    try:
        result = cost_client.query.usage(scope, params)

        cost_rows = []
        for row in result.rows:
            rg, cost = row[0], row[1]
            cost_rows.append([rg, f"rs:{cost:.2f}"])

        return cost_rows

    except Exception as e:
        print(" Cost API unavailable for this subscription type.")
        print("   Skipping cost breakdown.\n")
        return [["Not Supported", "N/A"]]


# REPORTING

def write_report(cost_table):
    print("\n Writing CSV Report...")

    with open(REPORT_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Resource Group", "Name", "Type", "Status"])
        writer.writerows(results)

        writer.writerow([])
        writer.writerow(["====== Monthly Cost Summary ======"])
        writer.writerow(["Resource Group", "Estimated Cost"])
        writer.writerows(cost_table)

    print(f" Report saved as: {REPORT_FILE}")



def main():
    check_vms()
    check_disks()
    check_storage()

    cost_data = cost_analysis()
    write_report(cost_data)

    print("\n Mode:", "AUTO DELETE ENABLED" if AUTO_DELETE else "READ-ONLY")
    print(" Completed.\n")


if __name__ == "__main__":
    main()

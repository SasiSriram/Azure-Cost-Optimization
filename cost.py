import os
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.mgmt.costmanagement import CostManagementClient
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.storage.blob import BlobServiceClient

try:
  # Load Credentials 
  load_dotenv(dotenv_path="cred.env")
  subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
  credential = DefaultAzureCredential()


  # create clients
  compute_client = ComputeManagementClient(credential,subscription_id)
  cost_client = CostManagementClient(credential)
  storage_client = StorageManagementClient(credential, subscription_id)


  #open report file
  with open ("cost_report.txt", "w") as report:
    report.write("==== Cost Optimization Report ====\n")


    # Check for stopped or idle Vms
    report.write("\n Idle or Stopped Vms: \n")
    for vm in compute_client.virtual_machines.list_all():
       rg_name = vm.id.split("/")[4]
       instance_view = compute_client.virtual_machines.instance_view(rg_name,vm.name)
       statuses = [s.code for s in instance_view.statuses]
       if any ("PowerState/stopped" in s for s in statuses):
         report.write(f"{vm.name} in {rg_name} is stopped - may still cost money. \n")
       elif any ("PowerState/deallocated" in s for s in statuses):
         report.write(f"{vm.name} in {rg_name} is deallocated - not charged. \n")
       else: 
         report.write(f"{vm.name} in {rg_name} is running. \n")



    # check for unattached disks

    report.write("\n Unattached Disks: \n")
    for disk in compute_client.disks.list():
      if disk.managed_by is None:
        report.write(f"{disk.name} ({disk.disk_size_gb} GB) - disk is Unattached consider deleting. \n")
      else:
        report.write(f"{disk.name} ({disk.disk_size_gb} GB) - disk is attached. \n")
    


    #cost summary --> payAsYouGo subscription support Cost Management API

    report.write("\n Monthly Cost by Resource Group: \n")
    result = cost_client.query.usage(
      scope=f"/subscriptions/{subscription_id}",
      parameters = { 
        "type": "Usage",
        "timeframe": "MonthToDate",
        "dataset": {
          "granularity": "Daily",
          "aggregation": {"totalCost": {"name": "PreTaxCost", "function": "Sum"}},
          "grouping": [{"type": "Dimension", "name": "ResourceGroupName"}],
        },
      },
    )
    for row in result.rows:
        group_name, cost = row[0], row[1]
        report.write(f"{group_name:20} : ₹{cost:.2f}\n")



    # Right size suggestions

    report.write("\n Right Size Recommendation: \n")
    for vm in compute_client.virtual_machines.list_all():
      size = vm.hardware_profile.vm_size
      if "Standard_D" in size:
          report.write(f"{vm.name}: Consider resizing from {size} --> Standard_B2s. \n")
      elif "Standard_E" in size:
          report.write(f"{vm.name}: Could switch from {size} --> Standard_D2s_v3. \n")
      else:
         report.write(f"{vm.name}: Size {size} is Reasonable. \n")


    # --- Blob Storage Analysis ---
    report.write("\nUnused or Empty Blob Containers:\n")
    for account in storage_client.storage_accounts.list():
      rg_name = account.id.split("/")[4]
      account_name = account.name
      try:
       # Connect to the blob service
  
          blob_service_client = BlobServiceClient(f"https://{account_name}.blob.core.windows.net/",credential=credential)
          containers = blob_service_client.list_containers()
          empty_found = False
          for container in containers:
            container_client = blob_service_client.get_container_client(container.name)
            blobs = container_client.list_blobs(limit=1)  # check if container has at least one blob
            if not any(blobs):
              report.write(f"Empty container: {container.name} in account {account_name} ({rg_name})\n")
              empty_found = True
          if not empty_found:
            report.write(f"Storage account {account_name} ({rg_name}) has no empty containers.\n")
      except Exception as e:
        report.write(f"Could not access storage account {account_name}: {e}\n")

    print("All results saved in cost_report.txt")

except ValueError:
  print("Subscription ID not found !")

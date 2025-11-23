#  Azure Cost Optimization Automation Tool

A Python-based automation tool designed to analyze Azure resources and detect potential cost-saving opportunities.  
It identifies unused or idle resources and optionally performs safe cleanup — helping reduce unwanted cloud billing.

## Features

**VM State Scan** - Detects running, stopped, and deallocated VMs 

**Disk Cleanup Detection** - Identifies unattached managed disks 

**Storage Optimization** - Finds empty blob containers

**Cost Usage Reporting** - Fetches monthly cost per resource group (if subscription is Pay as you Go)

**Tag-Based Protection** - Resources tagged `safe=yes` are never deleted

**Auto-Cleanup** - Automatically deletes unused disks when enabled 

**Export to CSV Report** - Saves findings and cost summary

##  Prerequisites

- Python `3.9`
- Azure CLI installed (`az login` required unless using Service Principal)
- Contributor or Reader role depending on mode:
  `Analysis only - Reader`
  `Auto-delete enabled - Contributor`

## Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Create a `cred.env` file
3. Run the script: `python main.py`

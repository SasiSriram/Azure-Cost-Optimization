# Azure Cost Optimization

This project helps you **reduce costs in your Azure subscription** 
By stopping idle VMs, deleting unattached disks, and resizing VMs, **this tool can reduce your Azure costs by 10–30%**, depending on usage.
It generates a detailed report (`cost_report.txt`) with recommendations for cost optimization.

## Features

- List stopped, deallocated, or running VMs
- Detect unattached disks that can be deleted
- Suggest VM right-sizing to smaller or cheaper SKUs
- Identify empty blob containers in storage accounts
- Generates a **cost optimization report** for review

## Setup:
1. Install dependencies: `pip install -r requirements.txt`
2. Create a `cred.env` file
3. Run the script: `python main.py`

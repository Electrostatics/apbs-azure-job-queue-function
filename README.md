# apbs-azure-job-queue-function

This repository contains an Azure Function App that serves as a launcher for APBS (Adaptive Poisson-Boltzmann Solver) and PDB2PQR jobs. The function app processes user requests to run molecular electrostatics calculations in the cloud using Azure Container Apps.

## Overview

The system processes molecular structure files (PDB files) through either PDB2PQR (for structure preparation) or APBS (for electrostatics calculations) using a serverless architecture. The function app acts as a job orchestrator, while the actual computational work happens in container instances.

### Key Components

- **Azure Function App**: Processes incoming job requests, validates input files, and queues jobs for execution
- **Azure Blob Storage**: Stores input and output files
- **Azure Queue Storage**: Manages job execution queue
- **Azure Container Apps**: Executes the actual APBS/PDB2PQR calculations
- **Azure Event Grid**: The low-latency event trigger platform

## Workflow

1. User submits a job to the system with PDB files and parameters
2. The Function App's blob trigger activates when a job configuration JSON file is uploaded
3. The app validates input files and parameters
4. Job status is initialized and stored in blob storage
5. Job information is placed in a queue for processing
6. A Container App is started to process the queued job
7. Results are stored back in blob storage and status is updated

## Project Structure

- **/.github/workflows/**: CI/CD workflows for deployment to Azure
  - **dev_apbs-azure-job-queue-function(dev).yml**: Deployment workflow for dev branch
  - **main_apbs-azure-job-queue-function.yml**: Deployment workflow for main branch
- **/launcher/**: Core business logic modules
  - **apbs.py**: APBS job setup
  - **azure_storage_utils.py**: Azure Blob Storage utilities
  - **jobsetup.py**: Base job setup class
  - **pdb2pqr.py**: PDB2PQR job setup
  - **utils.py**: Utility functions and helper classes
  - **weboptions.py**: Web form options processing
- **function_app.py**: Main Azure Function App definition and triggers
- **host.json**: Function App configuration
- **requirements.txt**: Python dependencies

## Job Types

The system supports two primary job types:
- PDB2PQR: Prepares molecular structures for electrostatics calculations
- APBS: Calculates electrostatic properties of molecules using the Poisson-Boltzmann equation

## Configuration

### Environment Variables
**NOTE: Be VERY intentional in setting these up since if these aren't set the function will not deploy**

The function app requires these environment variables:

- `BlobStorageConnectionString`: Connection string for Azure Blob Storage.
    - To find this, go to Security + Networking > Access keys. Be careful, this string has lots of power.
- `CONTAINER_APP_CLIENT_ID`: Managed Identity client ID
    - This maps to a role created to interact with the creating a contrainer app job
    - This gets created by [apbs-deploy-azure](https://github.com/Electrostatics/apbs-deploy-azure) and is named `apbs-container-app-access`
- `SUBSCRIPTION_ID`: Azure subscription ID
- `RESOURCE_GROUP_NAME`: Resource group containing Container Apps
    - This gets created by [apbs-deploy-azure](https://github.com/Electrostatics/apbs-deploy-azure) and is named `apbs-backend`
- `JOB_NAME`: Container App Job name
    - This gets created by [apbs-deploy-azure](https://github.com/Electrostatics/apbs-deploy-azure) and is named `apbs-app`
- `OutputQueue__credential`: This should be set to `managedIdentity`
- `OutputQueue__clientId`: The client ID for the managed identity used to access the output queue
    - This gets created by [apbs-deploy-azure](https://github.com/Electrostatics/apbs-deploy-azure) and is named `apbs-backend-data-access`
    - Find this in Managed Identites > `apbs-backend-data-access` > Client ID
- `OutputQueue__serviceUri`: The URI of the queue
    - Find this in your storage account Data Storage > Queues > Url

### Setup a deployment environment
1) Create a function app.
2) Setup your deployment from this repo. We use a modified version in the GitHub Actions seen above because we found it works better than what is provided by Azure.
3) Setup your environment variables from above.
4) For the roles mentioned above, ensure they are added to the function app via the UI.

## Deployment

The repository includes GitHub Actions workflows for CI/CD:

- Push to `dev` branch deploys to the dev slot
- Push to `main` branch deploys to production

If you are setting this workflow up yourself, you will need to create two deployment slots and set the above environment variables in your slot also.
This ensures that your dev slot also has the correct access to the variables.

## Dependencies

Key dependencies include:
- Azure Functions Core
- Azure Blob Storage SDK
- Azure Identity
- Azure Container Apps Management SDK

## Development Setup

1. Clone the repository
2. Create Python virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Install Azure Functions Core Tools version 4
5. Set up local.settings.json with required environment variables
6. Run the function app locally:
   ```
   func start
   ```

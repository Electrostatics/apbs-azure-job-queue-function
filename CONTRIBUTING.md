# Contributing to apbs-azure-job-queue-function

This document outlines the process for contributing to `apbs-azure-job-queue-function`, which is the Azure Function responsible for job handling in the APBS system.

## Project Overview

`apbs-azure-job-queue-function` serves as the middleware between the frontend and the backend processing system. It handles job submissions, manages the processing queue, and facilitates result retrieval.

## Development Environment Setup

### Prerequisites

- Azure Functions Core Tools
- Azure CLI
- Git
- GitHub account
- Python

### Getting Started

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/your-username/apbs-azure-job-queue-function.git
   cd apbs-azure-job-queue-function
   ```
3. Install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
4. Set up local configuration:
   - Create a `local.settings.json` file with required settings for testing

## Branch Structure

- `main`: Production branch - deployed to the production slot
- `dev`: Development branch - deployed to the development slot
- Feature branches should be created from `dev`

## Making Changes

1. Create a feature branch from `dev`:
   ```bash
   git checkout dev
   git pull origin dev
   git checkout -b feature/your-feature-name
   ```

2. Make your changes

3. Commit your changes:
   ```bash
   git commit -m "Description of changes"
   ```

## Pull Request Process

1. Push your feature branch to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

2. Create a pull request to the `dev` branch of the main repository

3. Your PR should include:
   - A description of changes
   - Any relevant issue numbers
   - Updates to documentation if you changed functionality

4. Changes will go through code review by project maintainers

5. Infrastructure changes will be reviewed with extra scrutiny

## Deployment Process

- PRs merged to `dev` are automatically deployed to the development slot
- After testing in the development slot, changes are promoted to production by merging `dev` into `main` or by performing a slot swap in Azure

## Deployment Slots

The function app uses deployment slots to manage different environments:
- Production slot: Receives traffic from the production frontend
- Development slot: Receives traffic from the development frontend

Each slot has its own configuration settings that direct traffic to the appropriate backend services.

## Security Considerations

- Do not commit sensitive information (keys, tokens, etc.) to the repository
- Environment-specific configuration is handled through deployment slot settings
- Function app uses managed identities for accessing Azure resources where possible

## Questions and Support

If you have questions or need help, please open an issue in the repository or contact the project maintainers.


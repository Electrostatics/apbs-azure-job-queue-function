## Deployment
We are using a modified way of handling Azure Function deployments.
We ran into many issues that were reflected by the community around deploying Python-based functions.
This causes us to use Azure Function Tools for the main deployment engine in GitHub Actions.

### Triggers
As found in the README, we use Event Grid to handle low-latency blob triggers. We largely are using [this tutorial](https://learn.microsoft.com/en-us/azure/azure-functions/functions-event-grid-blob-trigger?pivots=programming-language-python) to deploy.


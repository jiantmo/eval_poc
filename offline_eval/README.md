# Offline Evaluation POC

This project implements a Proof of Concept for an AI evaluation system.
The evaluation is divided into two stages: **Offline** and **Online**.

## Offline Evaluation

The offline evaluation consists of three main components:

1.  **Test Dataset**: Contains the inputs, expected outputs, and metadata for evaluation.
2.  **AI Application Environment (Aurora Env)**: The configurable service endpoint hosting the Agent or AI feature to be tested.
3.  **Evaluation Service Module**: Integrates with Azure AI Foundry Evaluation SDK and custom evaluators to measure performance metrics.

### Test Dataset Structure

Records in the dataset are stored as JSON objects with the following fields:

*   `input`: Inputs used to recreate the example (e.g., a question).
*   `expected` (Optional): The expected output of the model (e.g., the answer).
*   `metadata` (Optional): Key-value pairs for filtering and grouping (e.g., source, category).

### AI Application Environment

The environment is treated as data configuration, allowing users to select:
*   **Aurora Environment**: The specific version/instance of the integrated test environment (FNO, Dataverse, etc.).
*   **Agent**: The specific AI feature or bot to test within that environment.

Configuration is stored as JSON (e.g., `sample_env_config.json`) and loaded by the `EvalRunner`.

### Evaluation Service Module

This module allows users to configure a suite of evaluators.
*   **Azure Built-in Evaluators**: Wraps Azure AI Foundry Evaluation SDK metrics (e.g., Groundedness, Relevance, Coherence).
*   **Custom Evaluators**: Supports calling external HTTP endpoints for custom logic.
*   **Pass Rates**: Users can define thresholds for each metric.

Configuration is stored as JSON (e.g., `sample_eval_config.json`).

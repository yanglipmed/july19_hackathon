# Hackathon Agent

A simple AI agent built with Google's Agent Development Kit (ADK) that integrates with a deployed Gemma model on Cloud Run. This agent is designed to help hackathon participants with various tasks.

## Features

The agent provides four main capabilities:

1. **Ask Gemma** - Ask questions and get answers from the deployed Gemma model
2. **Generate Code** - Generate code in various programming languages with explanations
3. **Brainstorm Ideas** - Get creative ideas for projects and topics
4. **Explain Concepts** - Get explanations of complex concepts at different difficulty levels

## Prerequisites

- Python 3.12 or higher
- `uv` package manager (will be installed automatically with Docker)
- A deployed Gemma model on Cloud Run (set via `GEMMA_URL` environment variable)

## Local Development

### Setup

1. Install dependencies:

```bash
uv sync
```

2. Set your environment variables:

```bash
export GEMMA_URL="https://your-gemma-service-url"
```

3. Run the server:

```bash
uv run python server.py
```

The agent will be available at:

- Web interface: `http://localhost:8080/adk`
- API documentation: `http://localhost:8080/docs`
- Health check: `http://localhost:8080/health`

## Cloud Run Deployment

### Quick Deploy

```bash
# Deploy the agent to Cloud Run
gcloud run deploy hackathon-agent \
    --source . \
    --region europe-west1 \
    --no-allow-unauthenticated \
    --set-env-vars GEMMA_URL=https://your-gemma-service-url

# Get the service URL
gcloud run services describe hackathon-agent --region=us-central1 --format='value(status.url)'
```

### Testing with Authentication

```bash
# Get an authentication token
TOKEN=$(gcloud auth print-identity-token)

# Test the agent
curl -H "Authorization: Bearer ${TOKEN}" \
  "https://your-hackathon-agent-url/adk"
```


## Architecture

The agent consists of:

1. **GemmaClient**: Handles authenticated communication with the deployed Gemma model
2. **Agent Tools**: Four main functions that use the Gemma client to provide services
3. **ADK Agent**: The main agent that orchestrates tool usage and provides the chat interface
4. **FastAPI Server**: Exposes the agent via REST API and web interface

## Security

- The agent automatically handles authentication when deployed on Cloud Run
- For local development, it gracefully falls back to unauthenticated requests
- All external requests to Gemma are properly authenticated using Google Cloud identity tokens

## Customization

You can easily extend the agent by:

1. Adding new tools to `hackathon_agent/agent.py`
2. Modifying the agent's instruction and behavior
3. Adding new API endpoints to `server.py`
4. Customizing the Gemma client for different models or configurations

## Troubleshooting

### Common Issues

1. **"GEMMA_URL environment variable is required"**: Set the `GEMMA_URL` environment variable to your deployed Gemma service URL
2. **Authentication errors**: Ensure your Cloud Run service has the necessary IAM permissions to call other services
3. **Timeout errors**: The Gemma client uses a 30-second timeout; you may need to adjust this for slower models

### Logs

Check the application logs:

```bash
gcloud run services logs tail hackathon-agent --region=us-central1
```

## License

This project is licensed under the Apache License, Version 2.0.

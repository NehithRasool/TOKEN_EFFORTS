# Gen AI Mortgage Loan Application — Render Deployment

This package deploys the FastAPI website from the supplied notebook. It includes the 11-agent loan workflow, PDF reporting, individual application workflow, and Manager Portfolio Excel dashboard.

## Render
1. Push this folder to a GitHub repository.
2. In Render, create a **Web Service** from the repository.
3. Runtime: Python.
4. Build command: `pip install -r requirements.txt`
5. Start command: `uvicorn app:loan_web_app --host 0.0.0.0 --port $PORT`
6. Add environment variable `OPENROUTER_API_KEY` with your OpenRouter key.

A `render.yaml` is included for Blueprint deployment.

## Local
Set `OPENROUTER_API_KEY`, then run:

`uvicorn app:loan_web_app --host 0.0.0.0 --port 10000`

## Notes
- Render provides the `PORT` environment variable; the app binds to `0.0.0.0`.
- Uploaded files/reports are stored under the app data directory and are ephemeral on typical Render web services. For durable production storage, use external object/database storage.
- The supplied notebook's backend logic is retained rather than rewritten.

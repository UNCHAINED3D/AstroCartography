"""
Dev launcher for the Astrocartography API.

Run from the backend/ directory:

    python run.py

The app is also runnable directly with uvicorn:

    uvicorn api.main:app --port 8000 --reload
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)

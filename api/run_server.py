"""
Run this file to start the GST Fraud Detection API server.
The API will be available at http://localhost:8000
Interactive docs at http://localhost:8000/docs
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host     = "0.0.0.0",
        port     = 8000,
        reload   = True,   # auto-restart when you edit code
        workers  = 1,
    )
"""
Run the prediction service.

Usage:
    python -m prediction_service
    python -m prediction_service --port 8001
"""
import uvicorn
import argparse


def main():
    parser = argparse.ArgumentParser(description="Run Prediction Tracker API")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    args = parser.parse_args()

    print(f"Starting Prediction Tracker API on {args.host}:{args.port}")
    print(f"Docs available at: http://{args.host}:{args.port}/docs")

    uvicorn.run(
        "prediction_service.api:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )


if __name__ == "__main__":
    main()

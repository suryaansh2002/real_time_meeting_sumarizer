import uvicorn

from app.app import create_app
from fastapi.middleware.cors import CORSMiddleware


def main():
    app = create_app()
    app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

    uvicorn.run(app, host="127.0.0.1", port=8080)


if __name__ == "__main__":
    main()

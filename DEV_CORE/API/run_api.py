from devcore_api import create_app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("run_api:app", host="127.0.0.1", port=20131, reload=False)

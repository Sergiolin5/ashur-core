from fastapi import FastAPI

app = FastAPI(title="Ashur Core")


@app.get("/vivo")
def vivo() -> dict[str, bool]:
    return {"vivo": True}

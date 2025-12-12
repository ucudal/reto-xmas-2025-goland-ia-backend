from fastapi import FastAPI
from sqlalchemy.exc import OperationalError

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/health")
def health_check():
   return {"message": "200 corriendo..."}



from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI

from app.api.routes.base import router as base_router


app = FastAPI()

app.include_router(base_router)




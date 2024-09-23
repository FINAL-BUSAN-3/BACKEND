# main.py
from fastapi import FastAPI
from fastapi.routing import APIRouter
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

router = APIRouter(prefix="/api")


@router.get("/hello-world")
async def root():
    return {"message": "Hello World"} # 🔴 set Debug Point


app = FastAPI()
app.include_router(router)


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)

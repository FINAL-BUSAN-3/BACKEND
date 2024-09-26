# main.py
from fastapi import FastAPI
from controllers import test_controller

app = FastAPI()

# 컨트롤러의 라우터를 애플리케이션에 포함
app.include_router(test_controller.router)
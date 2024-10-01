from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from controllers import test_controller  # 필요에 따라 적절한 컨트롤러 경로로 수정하세요.

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],  # Vue.js 앱의 주소
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 컨트롤러의 라우터를 애플리케이션에 포함
app.include_router(test_controller.router)

# 테스트 엔드포인트 예시
@app.get("/items/{item_id}")
async def read_item(item_id: int):
    return {"item_id": item_id, "name": f"Item {item_id}"}

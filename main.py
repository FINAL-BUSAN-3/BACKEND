# main.py
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}


### 수행방법 정리
# 1. 라이브러리 설치
# 1.1. 방법1
# 	파일 -> 설정 -> 프로젝트 : fatapi -> 파이썬 인터프리터 -> + 버튼 -> uviconr, fastapi 설치
# 1.2. 방법2
# 	alt + f12 ->
# 	pip install fastapi
#   	pip install uvicorn
# 2. main.py 파일 생성 후 코드 작성
# 3. _init_.py 파일 생성
# 4. FastAPI 서버 실행 (테스트)
# 터미널에 다음 입력 : uvicorn main:app
# 5. http://localhost:8000/ 접속
# 6. FastAPI - Swagger UI
# Swagger UI 라고 하는 이 화면은 FastAPI에서 각 API의 기능 테스트에 상당히 많이 쓰인다.
# hello world 의 우측을 클릭하여 펼친 후 Try it out > Execute 를 클릭하면 아래와 같은 화면을 확인 할 수 있다.


### 발생 오류 정리
# 1. ImportError: cannot import name 'FastAPI' from 'fastapi'
#   (C:\Users\KFQ\Desktop\git\BACKEND\fastapi\__init__.py)
# - 원인 : fastapi 폴더와 FastAPI 패키지가 동일한 이름을 사용하면서 충돌이 발생한 것입니다.
# - 해결 방법 : 파일 경로 수정
#     (C:\Users\KFQ\Desktop\git\BACKEND\__init__.py)
#     (C:\Users\KFQ\Desktop\git\BACKEND\main.py)
# 2. Error while finding module specification for 'main.py'
#   (ModuleNotFoundError: __path__ attribute not found on 'main'
#   while trying to find 'main.py'). Try using 'main' instead of 'main.py' as the module name.
# - 원인 : main.py 파일을 모듈로 찾으려 했지만 실패한 경우 발생합니다.
#   python -m 명령어를 사용할 때 .py 확장자를 포함하지 않아야 하기 때문에 발생하는 문제입니다.
# - 해결 : Uvicorn을 사용한 FastAPI 실행
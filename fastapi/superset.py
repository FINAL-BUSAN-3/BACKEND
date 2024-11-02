import httpx

async def get_superset_data():
    superset_url = "http://localhost:8088/api/v1/dashboard/"  # Superset API 엔드포인트

    async with httpx.AsyncClient() as client:
        response = await client.get(superset_url)  # 헤더에서 Authorization 제거
        response.raise_for_status()  # 오류 발생 시 예외 발생
        return response.json()  # JSON 데이터 반환


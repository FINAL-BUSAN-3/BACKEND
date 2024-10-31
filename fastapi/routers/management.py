from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from database import get_db_connection

router = APIRouter()

# ============================================
# 관리 기본 엔드포인트
# ============================================

@router.get("/")
async def management_home():
    return {"message": "Welcome to Management Home"}

@router.get("/stock")
async def management_stock():
    return {"message": "Stock management data"}

@router.get("/month-sales")
async def management_month_sales():
    return {"message": "Monthly sales data"}

@router.get("/press/{period}")
async def management_press(period: str):
    return {"message": f"Press data for {period}"}

@router.get("/welding/{period}")
async def management_welding(period: str):
    return {"message": f"Welding data for {period}"}

# ============================================
# 주가 데이터 관련 함수
# ============================================

stock_data_map = {
    "005380": [],  # 현대차 주가 데이터
    "000270": []   # 기아차 주가 데이터
}

def get_naver_stock_price(symbol: str):
    """네이버 금융에서 주가 데이터를 가져옵니다."""
    try:
        url = f"https://finance.naver.com/item/main.nhn?code={symbol}"
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        price_element = soup.select_one('.no_today .blind')
        if not price_element:
            raise ValueError("주가 정보를 찾을 수 없습니다.")
        return price_element.text
    except Exception as e:
        print(f"Error fetching stock price: {e}")
        return None

@router.get("/stock-history/{symbol}")
async def fetch_stock_history(symbol: str):
    """주가 히스토리를 반환합니다."""
    global stock_data_map
    price = get_naver_stock_price(symbol)
    if price:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        current_price = float(price.replace(",", ""))

        # 이전 데이터와 동일할 경우 추가하지 않음
        if stock_data_map[symbol] and stock_data_map[symbol][-1]["price"] == current_price:
            return stock_data_map[symbol][-10:]  # 마지막 10개 데이터만 반환

        stock_data_map[symbol].append({"time": timestamp, "price": current_price})

        if len(stock_data_map[symbol]) > 100:
            stock_data_map[symbol] = stock_data_map[symbol][-100:]

    return stock_data_map[symbol][-10:]

# ============================================
# HD_sales 및 KIA_sales 데이터 엔드포인트
# ============================================

class SalesData(BaseModel):
    year: str
    count: int

@router.get("/sales/hd", response_model=List[SalesData])
async def get_hd_sales():
    """HD_sales 데이터를 반환합니다."""
    try:
        conn = await get_db_connection()
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT year, count FROM HD_sales ORDER BY year ASC")
            result = await cursor.fetchall()
            hd_sales = [{"year": row[0], "count": row[1]} for row in result]
        conn.close()
        return hd_sales
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sales/kia", response_model=List[SalesData])
async def get_kia_sales():
    """KIA_sales 데이터를 반환합니다."""
    try:
        conn = await get_db_connection()
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT year, count FROM KIA_sales ORDER BY year ASC")
            result = await cursor.fetchall()
            kia_sales = [{"year": row[0], "count": row[1]} for row in result]
        conn.close()
        return kia_sales
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

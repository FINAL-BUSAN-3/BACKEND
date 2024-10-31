import aiomysql

async def get_db_connection():
    return await aiomysql.connect(
        host='opyter.iptime.org',
        user='bigdata_busan_3',
        password='busan12345678*',
        db='web',
        port=3306
    )

async def get_db_press_connection():
    return await aiomysql.connect(
        host='opyter.iptime.org',
        user='bigdata_busan_3',
        password='busan12345678*',
        db='press',
        port=3306
    )

async def get_db_welding_connection():
    return await aiomysql.connect(
        host='opyter.iptime.org',
        user='bigdata_busan_3',
        password='busan12345678*',
        db='welding',
        port=3306
    )

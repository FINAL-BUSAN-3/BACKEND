from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def management_home():
    return {"message": "Welcome to User Management Home"}

@router.get("/user-search")
async def user_search():
    return {"message": "User search"}

@router.get("/user-add")
async def user_add():
    return {"message": "User added"}

@router.get("/user")
async def user():
    return {"message": "User data"}

@router.get("/user-detail")
async def user_detail():
    return {"message": "User detail"}

@router.get("/user-save")
async def user_save():
    return {"message": "User saved"}

@router.get("/group-search")
async def group_search():
    return {"message": "Group search"}

@router.get("/group")
async def group():
    return {"message": "Group data"}

# @router.get("/group-list")
# async def group_list():
#     return {"message": "Group list"}

@router.get("/group-add")
async def group_add():
    return {"message": "Group added"}

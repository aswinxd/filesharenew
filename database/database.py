import pymongo, os
from config import DB_URI, DB_NAME
from pymongo.collection import Collection


dbclient = pymongo.MongoClient(DB_URI)
database = dbclient[DB_NAME]


user_data = database['users']
join_requests: Collection = database['join_request']


async def present_user(user_id : int):
    found = user_data.find_one({'_id': user_id})
    return bool(found)

async def add_user(user_id: int):
    user_data.insert_one({'_id': user_id})
    return

async def full_userbase():
    user_docs = user_data.find()
    user_ids = []
    for doc in user_docs:
        user_ids.append(doc['_id'])
        
    return user_ids

async def del_user(user_id: int):
    user_data.delete_one({'_id': user_id})
    return

async def add_join_request(group_id: int, user_id: int) -> None:
    join_requests.insert_one({
        'group_id': group_id,
        'user_id': user_id,
    })

async def check_join_request(group_id: int, user_id: int) -> bool:
    request = join_requests.find_one({
        'group_id': group_id,
        'user_id': user_id
    })
    return bool(request)
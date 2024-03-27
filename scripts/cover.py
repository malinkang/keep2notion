

import requests
from notion_helper import NotionHelper
import os
LOGIN_API = "https://api.gotokeep.com/v1.1/users/login"
RUN_DATA_API = "https://api.gotokeep.com/pd/v3/stats/detail?dateUnit=all&type=running&lastDate={last_date}"
RUN_LOG_API = "https://api.gotokeep.com/pd/v3/runninglog/{run_id}"
from dotenv import load_dotenv
import utils
load_dotenv()
keep_headers = {
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:78.0) Gecko/20100101 Firefox/78.0",
    "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
}
def login():
    mobile = os.getenv("KEEP_MOBILE")
    password = os.getenv("KEEP_PASSWORD")
    data = {"mobile": mobile, "password": password}
    r = requests.post(LOGIN_API, headers=keep_headers, data=data)
    if r.ok:
        print("登录成功")
        token = r.json()["data"]["token"]
        keep_headers["Authorization"] = f"Bearer {token}"
        return get_run_id()
    else:
        print(r.text)
        return None

def get_run_id():
    last_date = 0
    results = []
    while 1:
        r = requests.get(RUN_DATA_API.format(
            last_date=last_date), headers=keep_headers)
        if r.ok:
            last_date = r.json()["data"]["lastTimestamp"]
            records = r.json().get("data").get("records")
            logs = [item.get("stats") for sublist in records for item in sublist['logs']]
            for log in logs:
                    results.append(log)
        
        print(f"last date = {last_date}")
        if not last_date:
            break
    return results

def get_run_data(id,name,page_id):
    r = requests.get(RUN_LOG_API.format(run_id=id), headers=keep_headers)
    shareImg = r.json().get("data").get("shareImg")
    cover = utils.upload_cover(shareImg)
    notion_helper.client.pages.update(page_id=page_id,cover=utils.get_icon(cover))
if __name__ == "__main__":
    notion_helper=NotionHelper()
    workouts=notion_helper.query_all(database_id=notion_helper.workout_database_id)
    # #查找图片错误的
    workouts = [item for item in workouts if "https://images.unsplash.com" in item['cover'].get("external").get("url")]
    item_dict = {item.get("properties").get("Id").get("rich_text")[0].get("plain_text"): item for item in workouts}
    logs = login()
    if logs:
        
        #按照结束时间倒序排序
        logs = sorted(logs, key=lambda x: x['endTime'])
        for log in logs:

            id = log.get("id")
            name = log.get("name")
            if id not in item_dict:
                continue
            page_id = item_dict.get(id).get("id")
            get_run_data(id,name,page_id)



#!/usr/bin/python
# -*- coding: UTF-8 -*-
import argparse
import json
import os
from dotenv import load_dotenv
import pendulum
from notion_helper import NotionHelper
import requests
import utils
from config import workout_properties_type_dict

LOGIN_API = "https://api.gotokeep.com/v1.1/users/login"
DATA_API = "https://api.gotokeep.com/pd/v3/stats/detail?dateUnit=all&type=all&lastDate={last_date}"
LOG_API = "https://api.gotokeep.com/pd/v3/{type}log/{id}"
WEIGHT = "https://api.gotokeep.com/feynman/v3/data-center/sub/body-data/detail?indicatorType=WEIGHT&pageSize=10"

keep_headers = {
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:78.0) Gecko/20100101 Firefox/78.0",
    "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
}
load_dotenv()


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


def get_weight_data():
    results = []
    next_page_token = None
    while True:
        url = WEIGHT
        if next_page_token:
            url += f"&nextPageToken={next_page_token}"

        response = requests.get(url, headers=keep_headers)
        if response.ok:
            data = response.json().get("data", {})
            results.extend(data.get("list", []))
            if not data.get("hasNextPage"):
                break
            next_page_token = data.get("nextPageToken")
        else:
            print("获取数据失败:", response.text)
            break
    return results


def insert_weight_data_to_notion(weight_data):
    # 获取 Notion 数据库中的所有数据
    existing_ids = set()
    notion_weights = notion_helper.query_all(
        database_id=notion_helper.weight_database_id)
    for item in notion_weights:
        if item.get("properties").get("id"):
            existing_ids.add(item.get("properties").get(
                "id").get("rich_text")[0].get("plain_text"))

    # 遍历数据并插入到 Notion
    for entry in weight_data:
        entry_id = entry.get("id")
        if entry_id in existing_ids:
            continue  # 跳过已存在的数据
        # 准备 Notion 数据库属性
        properties = {
            "id": {"rich_text": [{"text": {"content": entry_id}}]},
            "时间": {"date": {"start": pendulum.from_timestamp(entry["time"]["sampleEndTime"] / 1000, tz='Asia/Shanghai').to_iso8601_string()}},
            "体重": {"number": entry["value"]},
            "来源": {"title": [{"text": {"content": entry["source"]["displayName"]}}]},
            "单位": {"rich_text": [{"text": {"content": entry["indicatorUnit"]}}]},
        }
        icon_url = entry["source"].get("iconUrl")
        if icon_url:
            icon = utils.get_icon(icon_url)
            # 插入数据到 Notion
            notion_helper.client.pages.create(
                parent={"database_id": notion_helper.weight_database_id},
                properties=properties,
                cover=icon, icon=icon
            )
        else:
            notion_helper.client.pages.create(
                parent={"database_id": notion_helper.weight_database_id},
                properties=properties
            )


def get_run_id():
    last_date = 0
    results = []
    while 1:
        r = requests.get(DATA_API.format(
            last_date=last_date), headers=keep_headers)
        if r.ok:
            last_date = r.json()["data"]["lastTimestamp"]
            records = r.json().get("data").get("records")
            for record in records:
                for log in record.get("logs"):
                    if log.get("type") == "stats":
                        results.append(log.get("stats"))
        print(f"last date = {last_date}")
        if not last_date:
            break
    return results


def get_lastest():
    s = set()
    notion_workouts = notion_helper.query_all(
        database_id=notion_helper.workout_database_id
    )
    for i in notion_workouts:
        if i.get("properties").get("Id"):
            rich_text = i.get("properties").get("Id").get("rich_text")
            if rich_text:
                s.add(rich_text[0].get("plain_text"))
    return s


def get_run_data(log):
    r = requests.get(
        LOG_API.format(type=log.get("type"), id=log.get("id")), headers=keep_headers
    )
    if r.ok:
        data = r.json().get("data")
        workout = {}
        end_time = pendulum.from_timestamp(
            data.get("endTime") / 1000, tz="Asia/Shanghai"
        )
        workout["标题"] = log.get("name")
        workout["Id"] = data.get("id")
        workout["开始时间"] = data.get("startTime") / 1000
        workout["结束时间"] = data.get("endTime") / 1000
        workout["距离"] = round(data.get("distance", 0))
        workout["运动时长"] = data.get("duration")
        workout["平均配速"] = data.get("averagePace")
        workout["消耗热量"] = data.get("calorie")
        workout["运动类型"] = [
            notion_helper.get_relation_id(
                log.get("name"), id=notion_helper.type_database_id, icon=log.get("icon"))
        ]
        heartRate = data.get("heartRate")
        if heartRate:
            workout["平均心率"] = heartRate.get("averageHeartRate")
            workout["最大心率"] = heartRate.get("maxHeartRate")
        end_time = pendulum.from_timestamp(
            data.get("endTime") / 1000, tz="Asia/Shanghai"
        )
        cover = data.get("shareImg")
        if cover is None:
            cover = log.get("trackWaterMark")
        add_to_notion(workout, end_time, log.get("icon"), cover)


def add_to_notion(workout, end_time, icon, cover):
    properties = utils.get_properties(workout, workout_properties_type_dict)
    notion_helper.get_date_relation(properties, end_time)
    parent = {
        "database_id": notion_helper.workout_database_id,
        "type": "database_id",
    }
    icon = utils.get_icon(icon)
    # 封面长图有限制
    if cover and len(cover) <= 2000:
        pass
    else:
        if cover:
            cover = utils.upload_cover(cover)
        else:
            cover = "https://images.unsplash.com/photo-1547483238-f400e65ccd56?q=80&w=2970&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D"
    notion_helper.create_page(
        parent=parent, properties=properties, cover=utils.get_icon(cover), icon=icon
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    notion_helper = NotionHelper()
    s = get_lastest()
    logs = login()
    # weight_data = get_weight_data()
    # insert_weight_data_to_notion(weight_data)
    if logs:
        # 按照结束时间倒序排序
        logs = sorted(logs, key=lambda x: x["endTime"])
        for log in logs:
            id = log.get("id")
            if id in s:
                continue
            # 去掉重复数据
            if log.get("isDoubtful"):
                continue
            get_run_data(log)

#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from datetime import datetime
import asyncio

import httpx
from openai import APIConnectionError, APIError, AuthenticationError, OpenAI

import json

from fastapi_poe.types import ProtocolMessage
from fastapi_poe.client import get_bot_response

async def get_chat_response(messages, key: str, bot_name):
    response_text = ""
    print("Messages:", messages)
    async for partial in get_bot_response(messages=messages, bot_name=bot_name, api_key=key): 
        # Extract text from the raw_response field
        raw_response = json.loads(partial.raw_response['text'])
        text = raw_response.get('text', '')
        # Add the text to the response_text
        response_text += text
    return response_text


class ChatGPT():
    def __init__(self, conf: dict) -> None:
        self.key = conf.get("key")
        api = conf.get("api")
        proxy = conf.get("proxy")
        prompt = conf.get("prompt")
        self.model = conf.get("model", "gpt-3.5-turbo")
        self.LOG = logging.getLogger("ChatGPT")
        self.conversation_list = {}
        self.system_content_msg = {"role": "system", "content": "你是一位微信群中的小助手，现在你要按照你渊博的知识，回答下面的问题，同时注意返回内容的格式，不要使用 markdown，换行使用 \\n换行，请以精炼的语言回答提出的问题"}

    def __repr__(self):
        return 'ChatGPT'

    @staticmethod
    def value_check(conf: dict) -> bool:
        if conf:
            if conf.get("key") and conf.get("api") and conf.get("prompt"):
                return True
        return False

    async def get_answer(self, question: str, wxid: str) -> str:
        # wxid或者roomid,个人时为微信id，群消息时为群id
        self.updateMessage(wxid, question, "user")
        rsp = ""
        try:
            rsp = await get_chat_response(self.conversation_list[wxid], self.key,"GPT-4")
            rsp = rsp.replace("\n\n", "\n")
            self.updateMessage(wxid, rsp, "bot")
        except Exception as e0:
            self.LOG.error(f"发生未知错误：{str(e0)}")
            try:
                rsp = await get_chat_response(self.conversation_list[wxid], self.key, "GPT-3.5-Turbo")
                rsp = rsp.replace("\n\n", "\n")
                self.updateMessage(wxid, rsp, "bot")
            except Exception as e0:
                self.LOG.error(f"发生未知错误 2：{str(e0)}")

        return rsp

    def updateMessage(self, wxid: str, question: str, role: str) -> None:
        now_time = str(datetime.now().strftime("%Y-%m-%d / %H:%M:%S"))

        time_mk = "当需要回答时间时请直接参考回复:"
        # 初始化聊天记录,组装系统信息
        if wxid not in self.conversation_list.keys():
            question_ = [
                self.system_content_msg,
                {"role": "system", "content": "" + time_mk + now_time}
            ]
            self.conversation_list[wxid] = question_

        # 当前问题
        content_question_ = {"role": role, "content": question}
        self.conversation_list[wxid].append(content_question_)

        for cont in self.conversation_list[wxid]:
            if cont["role"] != "system":
                continue
            if cont["content"].startswith(time_mk):
                cont["content"] = time_mk + now_time

        # 只存储10条记录，超过滚动清除
        i = len(self.conversation_list[wxid])
        if i > 10:
            print("滚动清除微信记录：" + wxid)
            # 删除多余的记录，倒着删，且跳过第一个的系统消息
            del self.conversation_list[wxid][1]


if __name__ == "__main__":
    from configuration import Config
    config = Config().CHATGPT
    if not config:
        exit(0)

    chat = ChatGPT(config)

    async def ask_question():
        while True:
            q = input(">>> ")
            try:
                time_start = datetime.now()
                # 这里我们使用 await 来调用异步函数
                answer = await chat.get_answer(q, "wxid")
                print(answer)
                time_end = datetime.now()

                print(f"{round((time_end - time_start).total_seconds(), 2)}s")
            except Exception as e:
                print(e)

    # 运行事件循环
    asyncio.run(ask_question())

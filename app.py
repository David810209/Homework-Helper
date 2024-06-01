# -*- coding: utf-8 -*-
#載入LineBot所需要的套件
from flask import Flask, request, abort
import os
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *
import json
import tempfile
from ai_process.openAI_utils import OpenAIHandler
from redis_get.redis_db import RedisHandler
from notion_process.NotionAPI import Notion_handler
from config import LINEBOT_API_KEY, LINEBOT_HANDLER, OPENAI_API_KEY, PINECONE_API_KEY, PINECONE_ENVIRONMENT, MODEL_NAME, REDIS_HOST, REDIS_PASSWORD, REDIS_PORT
#執行檔案
app = Flask(__name__)

#初始化handler

redis_handler = RedisHandler(host=REDIS_HOST,port = REDIS_PORT,password=REDIS_PASSWORD)

# 必須放上自己的Channel Access Token

line_bot_api = LineBotApi(LINEBOT_API_KEY)
# 必須放上自己的Channel Secret

handler = WebhookHandler(LINEBOT_HANDLER)

# 監聽所有來自 /callback 的 Post Request (固定)
@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


#訊息傳遞區塊
# 處理file message
@handler.add(MessageEvent, message=FileMessage)
def handle_message(event):
    # 取得使用者id
    user_id = event.source.user_id
    #把讀進來的檔案存成暫存檔
    file_message = event.message
    file_content = line_bot_api.get_message_content(file_message.id)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        for chunk in file_content.iter_content():
            temp_file.write(chunk)
        temp_file_path = temp_file.name
        
    try:
        #丟暫存檔的路徑給處理pdf的function 回傳openAI的回應
        pinecone_index_name = redis_handler.get_user_pinecone_index_name(user_id)
        openaiHandler = OpenAIHandler(PINECONE_API_KEY, PINECONE_ENVIRONMENT, pinecone_index_name,OPENAI_API_KEY,MODEL_NAME)
        openaiHandler.upload_pdf(temp_file_path)
        response = f"PDF file uploaded successfully:"
    except Exception as e:
        response = f"Failed to process the PDF file: {str(e)}"
    finally:
        os.remove(temp_file_path)  # 清掉暫存檔
    #傳結果訊息給使用者
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response))

# 處理text message
@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    # 取得使用者id
    user_id = event.source.user_id
    # 讀取使用者傳來的訊息
    input_text = event.message.text 
    response = ""
    match input_text:
        case "註冊":
            response = TemplateSendMessage(
                alt_text='註冊',
                template=ButtonsTemplate(
                    title='註冊notion',
                    text='可以儲存一些資料到db',
                    actions=[
                        PostbackAction(
                            label='我要註冊',
                            data='action=startchat',
                            input_option='openKeyboard',
                            fill_in_text='setDB:(替換成你的英文名字)'
                        )
                        
                    ]
                )
            )
        case _ if input_text.startswith("setDB:"):
            name = input_text[len("setDB:"):]
            pinecone_index_name = name +"db"
            redis_handler.set_db(user_id,name,pinecone_index_name)
            response = TextSendMessage(text=f"User {name} has been created")
        case "getName":
            response = TextSendMessage(text=redis_handler.get_user_name(user_id))
        case "上傳PDF":
            response = TextSendMessage(text="先將PDF檔上傳到line keep 再透過KEEP傳到聊天室")
        case "問問題":
            response = TextSendMessage(text="你有啥問題")
        case "更新日歷":
            response = TextSendMessage("選擇服務項目",
            quick_reply=QuickReply(items=[
                QuickReplyButton(action=MessageAction(label="日歷連結", text="日歷連結")),
                QuickReplyButton(action=MessageAction(label="新增日歷", text="新增日歷")),
                QuickReplyButton(action=MessageAction(label="刪除日歷", text="刪除日歷")),
                QuickReplyButton(action=MessageAction(label="查看日歷", text="查看日歷"))
            ]))
        case "更新notion":
            response = TemplateSendMessage(
                alt_text='選擇服務項目',
                template=ButtonsTemplate(
                    title='更新notion',
                    text='選擇服務項目',
                    actions=[
                        PostbackAction(
                            label='輸入Notion API key',
                            data='action=startchat',
                            input_option='openKeyboard',
                            fill_in_text='NotionAPI:'
                        ),
                        PostbackAction(
                            label='輸入database key',
                            data='action=startchat',
                            input_option='openKeyboard',
                            fill_in_text='db:'
                        ),
                        PostbackAction(
                            label='建立Notion',
                            data='action=startchat',
                            input_option='openKeyboard',
                            fill_in_text='建立Notion\ndate:\nyear:\nmonth:\nday:\nhour:\nminute:\nhw:\ntext:'
                        ),
                        PostbackAction(
                            label='更新Notion已存在頁面',
                            data='action=startchat',
                            input_option='openKeyboard',
                            fill_in_text='更新Notion已存在頁面\n是否保存原頁面text:\n要更改的頁面原本名稱:\n\ndate:\nyear:\nmonth:\nday:\nhour:\nminute:\nhw:\ntext:'
                        )
                    ]
                )
            )
            
        case _ if input_text.startswith("NotionAPI:"):
            redis_handler.rds.hset(f"user:{user_id}", "notion_api_key", input_text[len("NotionAPI:"):])
            
        case _ if input_text.startswith("db:"):
            redis_handler.rds.hset(f"user:{user_id}", "notion_db_id", input_text[len("db:"):])
            
        case _ if input_text.startswith("建立Notion"):
            notion_handler = Notion_handler(user_id)
            # notion_handler.notion_test()
            date = notion_handler.date_format(input_text[len("year:"):], input_text[len("month:"):], input_text[len("day:"):], input_text[len("hour:"):], input_text[len("minute:"):])
            response = TextSendMessage(text="date set")
            # data_format = notion_handler.data_format(input_text[len("hw:"):], date)
            # notion_handler.create_page(data_format, input_text[len("text:"):])
            # response = TextSendMessage(text="建立成功")
        case _ if input_text.startswith("更新Notion已存在頁面"):
            notion_handler = Notion_handler(user_id)
            date = notion_handler.date_format(input_text[len("year:"):], input_text[len("month:"):], input_text[len("day:"):], input_text[len("hour:"):], input_text[len("minute:"):])
            data_format = notion_handler.data_format(input_text[len("hw:"):], date)
            page_id = notion_handler.get_page_id_by_name(input_text[len("要更改的頁面原本名稱:"):])
            if input_text[len("是否保存原頁面text:"):] == "是":
                erase_origin = False
            else:
                erase_origin = True
            notion_handler.update_page(page_id=page_id, data=data_format, text=input_text[len("text:"):], erase_origin=erase_origin)
            response = TextSendMessage(text="更新完成")
        case "日歷連結" | "新增日歷" | "刪除日歷" | "查看日歷":
            response = TextSendMessage(text="尚未完成服務")
        case _:
            try:
                # 處理對話 回傳openAI的回應
                pinecone_index_name = redis_handler.get_user_pinecone_index_name(user_id)
                openaiHandler = OpenAIHandler(PINECONE_API_KEY, PINECONE_ENVIRONMENT, pinecone_index_name,OPENAI_API_KEY,MODEL_NAME)
                response = TextSendMessage(text=openaiHandler.handle_conversation(user_id,input_text))
            except Exception as e:
                response= TextSendMessage(text=f"Failed to text: {str(e)}")
                
    #傳結果訊息給使用者
    line_bot_api.reply_message(event.reply_token, response)

#主程式
import os
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
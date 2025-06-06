# lambda/index.py

import json
import os
import boto3
from botocore.exceptions import ClientError
import urllib.request

API_URL = "https://2d67-34-125-235-214.ngrok-free.app/generate"
N_TURNS = 5  # ユーザー+アシスタントを合わせたターン数（ここでは直近5ターン分を保持）

def lambda_handler(event, context):
    try:
        print("Received event:", json.dumps(event))

        # Cognitoで認証されたユーザー情報を取得
        user_info = None
        if 'requestContext' in event and 'authorizer' in event['requestContext']:
            user_info = event['requestContext']['authorizer']['claims']
            print(f"Authenticated user: {user_info.get('email') or user_info.get('cognito:username')}")

        # リクエストボディの解析
        body = json.loads(event['body'])
        message = body['message']
        conversation_history = body.get('conversationHistory', [])

        print("Processing message:", message)

        # 会話履歴を使う
        messages = conversation_history.copy()

        # 新しいユーザーメッセージを履歴に追加
        messages.append({
            "role": "user",
            "content": message
        })

        # プロンプト組み立て（チャット履歴をそのまま文字列化する）
        prompt_parts = []
        for msg in messages[-N_TURNS*2:]:  # user+assistantで1ターンなので2倍取る
            if msg['role'] == 'user':
                prompt_parts.append(f"ユーザー: {msg['content']}")
            elif msg['role'] == 'assistant':
                prompt_parts.append(f"アシスタント: {msg['content']}")

        prompt = "\n".join(prompt_parts)

        print("Prompt: ", prompt)

        # --- ここからAPIリクエストを作って飛ばす
        data = json.dumps({
            "prompt": prompt,
            "max_new_tokens": 512,
            "do_sample": True,
            "temperature": 0.7,
            "top_p": 0.9
        }).encode("utf-8")

        req = urllib.request.Request(
            url=API_URL,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req) as res:
            response_body = json.loads(res.read())

        assistant_response = response_body["generated_text"]

        # アシスタントの応答を会話履歴に追加
        messages.append({
            "role": "assistant",
            "content": assistant_response
        })

        # 成功レスポンスの返却
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": True,
                "response": assistant_response,
                "conversationHistory": messages
            })
        }

    except Exception as error:
        print("Error:", str(error))

        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": False,
                "error": str(error)
            })
        }

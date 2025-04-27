# lambda/index.py
import json
import os
import urllib.request
from urllib.error import HTTPError, URLError
import re

# --- ユーティリティ関数 ---

def extract_region_from_arn(arn: str) -> str:
    """Lambda ARNからリージョンを抽出"""
    match = re.search(r'arn:aws:lambda:([^:]+):', arn)
    return match.group(1) if match else "us-east-1"

def build_prompt(conversation_history: list, user_message: str) -> str:
    """会話履歴とユーザーの最新メッセージからプロンプトを組み立て"""
    prompt = ""
    for msg in conversation_history:
        role = msg.get("role")
        content = msg.get("content")
        if role == "user":
            prompt += f"ユーザー: {content}\n"
        elif role == "assistant":
            prompt += f"アシスタント: {content}\n"
    prompt += f"ユーザー: {user_message}\nアシスタント:"
    return prompt

def send_request_to_model_api(model_api_url: str, prompt: str) -> dict:
    """モデルAPIにリクエストを送り、レスポンスを返す"""
    payload = {
        "prompt": prompt,
        "max_new_tokens": 100,
        "do_sample": True,
        "temperature": 0.7,
        "top_p": 0.9
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(model_api_url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")

    with urllib.request.urlopen(req) as res:
        response_data = res.read()
        return json.loads(response_data.decode("utf-8"))

# --- メインハンドラ ---

MODEL_API_URL = os.environ.get("MODEL_API_URL", "https://xxxxx.ngrok-free.app/generate")

def lambda_handler(event, context):
    try:
        print("Received event:", json.dumps(event))

        user_info = None
        if 'requestContext' in event and 'authorizer' in event['requestContext']:
            user_info = event['requestContext']['authorizer']['claims']
            print(f"Authenticated user: {user_info.get('email') or user_info.get('cognito:username')}")

        body = json.loads(event['body'])
        message = body['message']
        conversation_history = body.get('conversationHistory', [])
        print("User message:", message)

        prompt = build_prompt(conversation_history, message)

        print("Sending request to custom model API")
        try:
            response_json = send_request_to_model_api(MODEL_API_URL, prompt)
        except HTTPError as e:
            raise Exception(f"Model API error: {e.code}, {e.read().decode('utf-8')}")
        except URLError as e:
            raise Exception(f"Failed to reach server: {e.reason}")

        assistant_response = response_json.get("generated_text", "")

        # 会話履歴を更新
        updated_conversation_history = conversation_history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": assistant_response}
        ]

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
                "conversationHistory": updated_conversation_history
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


# # lambda/index.py
# import json
# import os
# import boto3
# import re  # 正規表現モジュールをインポート
# from botocore.exceptions import ClientError


# # Lambda コンテキストからリージョンを抽出する関数
# def extract_region_from_arn(arn):
#     # ARN 形式: arn:aws:lambda:region:account-id:function:function-name
#     match = re.search('arn:aws:lambda:([^:]+):', arn)
#     if match:
#         return match.group(1)
#     return "us-east-1"  # デフォルト値

# # グローバル変数としてクライアントを初期化（初期値）
# bedrock_client = None

# # モデルID
# MODEL_ID = os.environ.get("MODEL_ID", "us.amazon.nova-lite-v1:0")

# def lambda_handler(event, context):
#     try:
#         # コンテキストから実行リージョンを取得し、クライアントを初期化
#         global bedrock_client
#         if bedrock_client is None:
#             region = extract_region_from_arn(context.invoked_function_arn)
#             bedrock_client = boto3.client('bedrock-runtime', region_name=region)
#             print(f"Initialized Bedrock client in region: {region}")
        
#         print("Received event:", json.dumps(event))
        
#         # Cognitoで認証されたユーザー情報を取得
#         user_info = None
#         if 'requestContext' in event and 'authorizer' in event['requestContext']:
#             user_info = event['requestContext']['authorizer']['claims']
#             print(f"Authenticated user: {user_info.get('email') or user_info.get('cognito:username')}")
        
#         # リクエストボディの解析
#         body = json.loads(event['body'])
#         message = body['message']
#         conversation_history = body.get('conversationHistory', [])
        
#         print("Processing message:", message)
#         print("Using model:", MODEL_ID)
        
#         # 会話履歴を使用
#         messages = conversation_history.copy()
        
#         # ユーザーメッセージを追加
#         messages.append({
#             "role": "user",
#             "content": message
#         })
        
#         # Nova Liteモデル用のリクエストペイロードを構築
#         # 会話履歴を含める
#         bedrock_messages = []
#         for msg in messages:
#             if msg["role"] == "user":
#                 bedrock_messages.append({
#                     "role": "user",
#                     "content": [{"text": msg["content"]}]
#                 })
#             elif msg["role"] == "assistant":
#                 bedrock_messages.append({
#                     "role": "assistant", 
#                     "content": [{"text": msg["content"]}]
#                 })
        
#         # invoke_model用のリクエストペイロード
#         request_payload = {
#             "messages": bedrock_messages,
#             "inferenceConfig": {
#                 "maxTokens": 512,
#                 "stopSequences": [],
#                 "temperature": 0.7,
#                 "topP": 0.9
#             }
#         }
        
#         print("Calling Bedrock invoke_model API with payload:", json.dumps(request_payload))
        
#         # invoke_model APIを呼び出し
#         response = bedrock_client.invoke_model(
#             modelId=MODEL_ID,
#             body=json.dumps(request_payload),
#             contentType="application/json"
#         )
        
#         # レスポンスを解析
#         response_body = json.loads(response['body'].read())
#         print("Bedrock response:", json.dumps(response_body, default=str))
        
#         # 応答の検証
#         if not response_body.get('output') or not response_body['output'].get('message') or not response_body['output']['message'].get('content'):
#             raise Exception("No response content from the model")
        
#         # アシスタントの応答を取得
#         assistant_response = response_body['output']['message']['content'][0]['text']
        
#         # アシスタントの応答を会話履歴に追加
#         messages.append({
#             "role": "assistant",
#             "content": assistant_response
#         })
        
#         # 成功レスポンスの返却
#         return {
#             "statusCode": 200,
#             "headers": {
#                 "Content-Type": "application/json",
#                 "Access-Control-Allow-Origin": "*",
#                 "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
#                 "Access-Control-Allow-Methods": "OPTIONS,POST"
#             },
#             "body": json.dumps({
#                 "success": True,
#                 "response": assistant_response,
#                 "conversationHistory": messages
#             })
#         }
        
#     except Exception as error:
#         print("Error:", str(error))
        
#         return {
#             "statusCode": 500,
#             "headers": {
#                 "Content-Type": "application/json",
#                 "Access-Control-Allow-Origin": "*",
#                 "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
#                 "Access-Control-Allow-Methods": "OPTIONS,POST"
#             },
#             "body": json.dumps({
#                 "success": False,
#                 "error": str(error)
#             })
#         }

# lambda/index.py
import json
import os
#import boto3
#import re  # 正規表現モジュールをインポート
#from botocore.exceptions import ClientError
import urllib.request
import urllib.error

COLAB_API_URL = os.environ.get("COLAB_API_URL", "https://2c24-34-169-203-111.ngrok-free.app")


def call_colab_api(prompt: str, history: list[str]) -> str:
    """Colab FastAPI /generate を呼び出して応答文字列を返す"""
    payload = {
        "prompt": prompt,
        "conversation_history": history,
    }
    req = urllib.request.Request(
        url=f"{COLAB_API_URL}/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body["generated_text"]
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Colab API HTTP {e.code}: {e.read().decode()}") from e
    except Exception as e:
        raise RuntimeError(f"Colab API call failed: {e}") from e


def lambda_handler(event, context):
    try:
        body = json.loads(event["body"])
        message = body["message"]
        conversation_history: list[dict] = body.get("conversationHistory", [])

        # ユーザー発言を履歴に追加
        conversation_history.append({"role": "user", "content": message})

        # --- Colab に問い合わせ ---
        assistant_response = call_colab_api(message, conversation_history)

        # アシスタント発言を履歴に追加
        conversation_history.append({"role": "assistant", "content": assistant_response})

        # 成功レスポンス
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST",
            },
            "body": json.dumps(
                {
                    "success": True,
                    "response": assistant_response,
                    "conversationHistory": conversation_history,
                }
            ),
        }

    except Exception as e:
        # 例外発生時はエラーを返却
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST",
            },
            "body": json.dumps({"success": False, "error": str(e)}),
        }

import os
from flask import Flask, request, jsonify
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
import yaml

app = Flask(__name__)

# 環境変数から設定を読み込む（ここは変更ありません）
CONFIG = {
    "developer_token": os.environ.get("GOOGLE_DEVELOPER_TOKEN"),
    "client_id": os.environ.get("GOOGLE_CLIENT_ID"),
    "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET"),
    "refresh_token": os.environ.get("GOOGLE_REFRESH_TOKEN"),
    "login_customer_id": os.environ.get("GOOGLE_LOGIN_CUSTOMER_ID"),
    "use_proto_plus": "True",
}

@app.route('/get-ad-texts', methods=['POST'])
def get_ad_texts():
    data = request.get_json()
    if not data or 'customerId' not in data:
        return jsonify({"error": "customerId is required"}), 400

    customer_id = data['customerId']
    login_customer_id = CONFIG["login_customer_id"].replace("-", "")

    try:
        googleads_client = GoogleAdsClient.load_from_dict(CONFIG)
        ga_service = googleads_client.get_service("GoogleAdsService")

        # --- ▼▼▼ ここが最重要ポイントです ▼▼▼ ---
        # 広告アセット(ASSET)からテキスト情報(HEADLINE, DESCRIPTION)のみを取得する、軽量で正確なクエリ。
        # これにより、画像や動画などの重いデータは一切取得しなくなります。
        query = """
            SELECT
                campaign.name,
                ad_group.name,
                asset.text_asset.text,
                ad_group_asset.field_type
            FROM ad_group_asset
            WHERE
                ad_group_asset.status = 'ENABLED'
                AND ad_group.status = 'ENABLED'
                AND campaign.status = 'ENABLED'
                AND ad_group_asset.field_type IN ('HEADLINE', 'DESCRIPTION')
            LIMIT 10000
        """
        # --- ▲▲▲ ここまでが新しいクエリです ▲▲▲ ---

        stream = ga_service.search_stream(customer_id=customer_id.replace("-", ""), query=query)

        # 取得したデータを広告グループごとに整理してまとめる処理
        ads_dict = {}
        for batch in stream:
            for row in batch.results:
                ad_group_name = row.ad_group.name
                campaign_name = row.campaign.name
                field_type = row.ad_group_asset.field_type.name
                text = row.asset.text_asset.text

                ad_key = (campaign_name, ad_group_name)

                if ad_key not in ads_dict:
                    ads_dict[ad_key] = {
                        "campaign_name": campaign_name,
                        "ad_group_name": ad_group_name,
                        "headlines": [],
                        "descriptions": []
                    }
                
                if field_type == 'HEADLINE':
                    ads_dict[ad_key]["headlines"].append(text)
                elif field_type == 'DESCRIPTION':
                    ads_dict[ad_key]["descriptions"].append(text)
        
        results = list(ads_dict.values())

        return jsonify(results)

    except GoogleAdsException as ex:
        # エラー処理（変更ありません）
        return jsonify({"error": "Google Ads API request failed", "details": str(ex)}), 500
    except Exception as e:
        return jsonify({"error": "An unexpected error occurred", "details": str(e)}), 500

if __name__ == "__main__":
    # 変更ありません
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
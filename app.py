import os
from flask import Flask, request, jsonify
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
import yaml

app = Flask(__name__)

# 環境変数から設定を読み込む
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
    # MCCアカウントIDのハイフンを削除
    login_customer_id = CONFIG["login_customer_id"].replace("-", "")

    try:
        googleads_client = GoogleAdsClient.load_from_dict(CONFIG)

        ga_service = googleads_client.get_service("GoogleAdsService")

        query = """
            SELECT
                campaign.name,
                ad_group.name,
                ad_group_ad.ad.responsive_search_ad.headlines,
                ad_group_ad.ad.responsive_search_ad.descriptions
            FROM ad_group_ad
            WHERE
                ad_group_ad.status = 'ENABLED'
                AND ad_group.status = 'ENABLED'
                AND campaign.status = 'ENABLED'
                AND ad_group_ad.ad.type = 'RESPONSIVE_SEARCH_AD'
            LIMIT 1000
        """

        stream = ga_service.search_stream(customer_id=customer_id.replace("-", ""), query=query)

        results = []
        for batch in stream:
            for row in batch.results:
                ad = row.ad_group_ad.ad
                headlines = [h.text for h in ad.responsive_search_ad.headlines]
                descriptions = [d.text for d in ad.responsive_search_ad.descriptions]

                results.append({
                    "campaign_name": row.campaign.name,
                    "ad_group_name": row.ad_group.name,
                    "headlines": headlines,
                    "descriptions": descriptions,
                })

        return jsonify(results)

    except GoogleAdsException as ex:
        # エラー詳細をロギング（Renderのログで確認できます）
        print(f"Request with ID '{ex.request_id}' failed with status "
              f"'{ex.error.code().name}' and includes the following errors:")
        for error in ex.failure.errors:
            print(f"\tError with message '{error.message}'.")
            if error.location:
                for field_path_element in error.location.field_path_elements:
                    print(f"\t\tOn field: {field_path_element.field_name}")
        return jsonify({"error": "Google Ads API request failed", "details": str(ex)}), 500
    except Exception as e:
        return jsonify({"error": "An unexpected error occurred", "details": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
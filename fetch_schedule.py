import requests
import json
from datetime import datetime

url = "https://tm.tapi.videoready.tv/portal-search/pub/api/v1/channels/schedule"

params = {
  'date': "18-04-2026",
  'languageFilters': "",
  'genreFilters': "",
  'limit': "0",
  'offset': "0"
}

headers = {
  'User-Agent': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
  'Accept-Encoding': "gzip, deflate, br, zstd",
  'sec-ch-ua-platform': "\"Linux\"",
  'sec-ch-ua': "\"Chromium\";v=\"146\", \"Not-A.Brand\";v=\"24\", \"Google Chrome\";v=\"146\"",
  'sec-ch-ua-mobile': "?0",
  'device_details': "{\"pl\":\"web\",\"os\":\"Linux\",\"lo\":\"en-us\",\"app\":\"1.63.1\",\"dn\":\"PC\",\"bv\":146,\"bn\":\"CHROME\",\"device_id\":\"a94f3a42d582ac3968ba5ffe2f836338\",\"device_type\":\"WEB\",\"device_platform\":\"PC\",\"device_category\":\"open\",\"manufacturer\":\"Linux_CHROME_146\",\"model\":\"PC\",\"sname\":\"\"}",
  'content-type': "application/json",
  'locale': "ENG",
  'platform': "web",
  'origin': "https://watch.tataplay.com",
  'sec-fetch-site': "cross-site",
  'sec-fetch-mode': "cors",
  'sec-fetch-dest': "empty",
  'referer': "https://watch.tataplay.com/",
  'accept-language': "en-US,en;q=0.9,hi;q=0.8",
  'priority': "u=1, i"
}

try:
    response = requests.get(url, params=params, headers=headers, timeout=30)

    if response.status_code == 200:
        data = response.json()  # Proper JSON parsing

        # Dynamic filename (optional)
        filename = f"schedule_{params['date']}.json"

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"[✓] Data saved successfully to {filename}")

    else:
        print(f"[ERROR] Status Code: {response.status_code}")
        print(response.text)

except requests.exceptions.RequestException as e:
    print("[REQUEST ERROR]", str(e))

except json.JSONDecodeError:
    print("[ERROR] Response is not valid JSON")
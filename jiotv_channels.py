import requests
import json

# ================= CONFIG =================
API_URL = "https://jiotvapi.cdn.jio.com/apis/v3.0/getMobileChannelList/get/?langId=6&devicetype=phone&os=android&usertype=JIO&version=343"

OUTPUT_FILE = "channels.json"


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36 Edg/147.0.0.0",
    "Accept": "application/json",
    "Accept-Encoding": "gzip",
    "Connection": "Keep-Alive",
    "Host": "jiotvapi.cdn.jio.com",
    "Origin": "https://www.jiotv.com",
    "Referer": "https://www.jiotv.com/",
}
# ================= FETCH =================
def fetch_channels():
    print("[+] Fetching JioTV channels...")

    try:
        res = requests.get(API_URL, headers=HEADERS, timeout=20)
        res.raise_for_status()
        data = res.json()

        channels = []

        for ch in data.get("result", []):
            try:
                cid = int(ch.get("channel_id"))
                name = ch.get("channel_name", "").strip()
                logo = ch.get("logoUrl", "")

                # Fix logo URL
                if logo and not logo.startswith("http"):
                    logo = f"https://jiotv.catchup.cdn.jio.com/dare_images/images/{logo}"

                channels.append({
                    "id": cid,
                    "name": name,
                    "logo": logo
                })

            except Exception as e:
                print(f"[-] Skipping channel: {e}")

        print(f"[✓] Total Channels: {len(channels)}")
        return channels

    except Exception as e:
        print(f"[ERROR] Fetch failed: {e}")
        return []


# ================= SAVE =================
def save_json(channels):
    print("[+] Saving channels.json...")

    final = {
        "total": len(channels),
        "channels": channels
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final, f, indent=2, ensure_ascii=False)

    print("[✓] Saved successfully!")


# ================= MAIN =================
if __name__ == "__main__":
    data = fetch_channels()
    save_json(data)

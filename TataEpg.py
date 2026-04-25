import requests
import gzip
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import xml.dom.minidom as md

# ================= CONFIG =================
API = "https://tm.tapi.videoready.tv/content-detail/pub/api/v1/channels/schedule"

HEADERS = {
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

# ================= DATES =================
def get_dates():
    today = datetime.now()
    return [
        (today - timedelta(days=1)).strftime("%d-%m-%Y"),  # yesterday
        today.strftime("%d-%m-%Y"),                        # today
        (today + timedelta(days=1)).strftime("%d-%m-%Y")   # tomorrow
    ]

# ================= TIME FORMAT =================
def format_time(ms):
    dt = datetime.utcfromtimestamp(ms / 1000)
    return dt.strftime("%Y%m%d%H%M%S +0000")

# ================= FETCH =================
def fetch_channels():
    print("[+] Fetching Yesterday + Today + Tomorrow EPG...\n")

    limit = 20
    max_retries = 5

    all_channels = {}

    session = requests.Session()

    for DATE in get_dates():
        print(f"[+] Date: {DATE}")

        offset = 0

        while True:
            params = {
                "date": DATE,
                "languageFilters": "",
                "genreFilters": "",
                "limit": limit,
                "offset": offset
            }

            success = False

            for attempt in range(max_retries):
                try:
                    res = session.get(API, params=params, headers=HEADERS, timeout=20)

                    if res.status_code != 200:
                        continue

                    data = res.json().get("data", {})
                    channels = data.get("channelList", [])

                    success = True
                    break

                except Exception as e:
                    print(f"[Retry {attempt+1}] {DATE} → {e}")

            if not success:
                print(f"[!] Skipping batch {DATE}")
                offset += limit
                continue

            if not channels:
                break

            for ch in channels:
                ch_id = str(ch.get("id"))

                if ch_id not in all_channels:
                    all_channels[ch_id] = {
                        "id": ch_id,
                        "name": ch.get("title", "Unknown"),
                        "logo": ch.get("image"),
                        "poster": ch.get("image"),
                        "genres": ch.get("genres", []),
                        "epg": [],
                        "_ids": set()  # for dedup
                    }

                for prog in ch.get("epg", []):
                    pid = prog.get("id")

                    if pid and pid not in all_channels[ch_id]["_ids"]:
                        all_channels[ch_id]["_ids"].add(pid)
                        all_channels[ch_id]["epg"].append(prog)

            offset += limit
            total = data.get("total", 0)

            if offset >= total:
                break

    # cleanup
    for ch in all_channels.values():
        del ch["_ids"]

    print(f"\n[✓] Final Channels: {len(all_channels)}\n")
    return list(all_channels.values())

# ================= BUILD XML =================
def build_xml(channels):
    print("[+] Building XMLTV...")

    tv = ET.Element("tv")

    for ch in channels:
        ch_id = ch["id"]
        ch_name = ch["name"]

        channel = ET.SubElement(tv, "channel", id=ch_id)
        ET.SubElement(channel, "display-name").text = ch_name

        if ch["logo"]:
            ET.SubElement(channel, "icon", src=ch["logo"])

        programmes = sorted(ch["epg"], key=lambda x: x.get("startTime", 0))

        for prog in programmes:
            if not prog.get("startTime") or not prog.get("endTime"):
                continue

            programme = ET.SubElement(tv, "programme", {
                "start": format_time(prog["startTime"]),
                "stop": format_time(prog["endTime"]),
                "channel": ch_id,
                "catchup-id": str(prog.get("id", ""))
            })

            ET.SubElement(programme, "title").text = prog.get("title", "No Title")
            ET.SubElement(programme, "desc").text = prog.get("desc", "")

            genres = ch.get("genres", [])
            category = genres[0] if genres else "Others"
            ET.SubElement(programme, "category").text = category

            icon_url = (
                prog.get("imageUrl")
                or ch.get("poster")
                or ch.get("logo")
            )

            if icon_url:
                ET.SubElement(programme, "icon", src=icon_url)

    return tv

# ================= SAVE =================
def save_files(tv):
    gz_file = "TataEpg.xml.gz"

    rough = ET.tostring(tv, encoding='utf-8')
    parsed = md.parseString(rough)
    pretty = parsed.toprettyxml(indent="  ")
    pretty = "\n".join([l for l in pretty.split("\n") if l.strip()])

    with gzip.open(gz_file, "wb") as f:
        f.write(pretty.encode("utf-8"))

    print(f"[+] Saved: {gz_file}")

# ================= MAIN =================
if __name__ == "__main__":
    channels = fetch_channels()
    tv = build_xml(channels)
    save_files(tv)

    print("\n[✓] Done: 3-Day EPG Ready\n")
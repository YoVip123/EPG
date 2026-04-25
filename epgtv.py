import requests
import gzip
import xml.etree.ElementTree as ET
from datetime import datetime
import xml.dom.minidom as md

# ================= CONFIG =================
#https://tm.tapi.videoready.tv/content-detail/pub/api/v1/channels/schedule?date=&languageFilters=&genreFilters=&limit=20&offset=0
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

DATE = datetime.now().strftime("%d-%m-%Y")

# ================= TIME FORMAT =================
def format_time(ms):
    dt = datetime.utcfromtimestamp(ms / 1000)
    return dt.strftime("%Y%m%d%H%M%S +0000")


# ================= FETCH CHANNELS + EPG =================
def fetch_channels():
    print("[+] Fetching channels with EPG...\n")

    offset = 0
    limit = 20
    max_retries = 5

    all_channels = []
    seen_ids = set()

    session = requests.Session()  # reuse connection (important)

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
                    print(f"[ERROR] Status: {res.status_code}")
                    continue

                data = res.json().get("data", {})
                channels = data.get("channelList", [])

                success = True
                break

            except Exception as e:
                print(f"[Retry {attempt+1}] Error: {e}")

        if not success:
            print("[!] Skipping this batch, continuing...")
            offset += limit
            continue

        if not channels:
            print("[!] No more data")
            break

        new_added = 0

        for ch in channels:
            ch_id = ch.get("id")

            if ch_id not in seen_ids:
                seen_ids.add(ch_id)

                all_channels.append({
                    "id": str(ch_id),
                    "name": ch.get("title", "Unknown"),
                    "logo": ch.get("boxCoverImage") or ch.get("transparentImageUrl"),
                    "poster": ch.get("posterImage"),
                    "genres": ch.get("genres", []),
                    "epg": ch.get("epg", [])
                })

                new_added += 1

        print(f"[+] Total: {len(all_channels)} (+{new_added})")

        offset += limit

        total = data.get("total", 0)
        if offset >= total:
            break

    print(f"\n[✓] Final Channels: {len(all_channels)}\n")
    return all_channels


# ================= BUILD XML =================
def build_xml(channels):
    print("[+] Building XMLTV (custom format)...")

    tv = ET.Element("tv")

    for ch in channels:
        ch_id = f"{ch['id']}"
        ch_name = ch["name"]

        # CHANNEL
        channel = ET.SubElement(tv, "channel", id=ch_id)
        ET.SubElement(channel, "display-name").text = ch_name

        if ch["logo"]:
            ET.SubElement(channel, "icon", src=ch["logo"])

        # PROGRAMMES
        for prog in ch["epg"]:
            if not prog.get("startTime") or not prog.get("endTime"):
                continue

            programme = ET.SubElement(tv, "programme", {
                "start": format_time(prog["startTime"]),
                "stop": format_time(prog["endTime"]),
                "channel": ch_id,
                "catchup-id": str(prog.get("id", ""))
            })

            ET.SubElement(programme, "title").text = prog.get("title", "No Title")

            # Category
            genres = ch.get("genres", [])
            category = genres[0] if genres else "Others"
            ET.SubElement(programme, "category").text = category

            # Icon
            icon_url = (
                ch.get("poster")
                or ch.get("logo")
            )

            if icon_url:
                ET.SubElement(programme, "icon", src=icon_url)

    return tv


# ================= SAVE FILES (PRETTY XML) =================
def save_files(tv):
    xml_file = "tataepg.xml"
    gz_file = "tataepg.xml.gz"

    # Convert to string
    rough_string = ET.tostring(tv, encoding='utf-8')

    # Pretty format
    parsed = md.parseString(rough_string)
    pretty_xml = parsed.toprettyxml(indent="  ")

    # Remove blank lines
    pretty_xml = "\n".join([line for line in pretty_xml.split("\n") if line.strip()])

    # Save XML
    with open(xml_file, "w", encoding="utf-8") as f:
        f.write(pretty_xml)

    print(f"[+] Saved (Pretty): {xml_file}")

    # Compress
    with open(xml_file, "rb") as f_in:
        with gzip.open(gz_file, "wb") as f_out:
            f_out.writelines(f_in)

    print(f"[+] Compressed: {gz_file}")


# ================= MAIN =================
if __name__ == "__main__":
    channels = fetch_channels()
    tv = build_xml(channels)
    save_files(tv)

    print("\n[✓] Done: Full TataPlay EPG Ready\n")
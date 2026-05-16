import requests
import gzip
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime

# ==========================================================
# CONFIG
# ==========================================================
ACCESS_TOKEN = "YOUR_TOKEN_HERE"

headers = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'origin': 'https://www.zee5.com',
    'referer': 'https://www.zee5.com/',
    'x-access-token': ACCESS_TOKEN
}

# ==========================================================
# IMAGE HELPERS
# ==========================================================
def get_channel_logo(channel):
    """
    Build working Zee5 channel logo URL
    """
    channel_id = channel.get("id")
    list_image = channel.get("list_image")

    if not channel_id or not list_image:
        return None

    return (
        "https://akamaividz2.zee5.com/"
        "image/upload/"
        "w_528,h_297,c_scale,"
        "f_webp,q_auto:eco/"
        f"resources/{channel_id}/"
        f"channel_list/{list_image}"
    )


def get_programme_image(programme):
    """
    Build working Zee5 programme image URL
    """

    programme_id = programme.get("id")

    if not programme_id:
        return None

    image = programme.get("image", {})
    image_name = image.get("list")

    if not image_name:
        return None

    return (
        "https://akamaividz2.zee5.com/"
        "image/upload/"
        "w_1101,h_620,c_scale,"
        "f_webp,q_auto:eco/"
        f"resources/{programme_id}/"
        f"list/{image_name}.jpg"
    )


# ==========================================================
# 1. FETCH GENRES
# ==========================================================
print("Fetching genres...")

genres_url = "https://catalogapi.zee5.com/v1/channel/genres"

genres_response = requests.get(
    genres_url,
    params={
        'translation': 'en',
        'country': 'IN'
    },
    headers=headers
)

genres_data = genres_response.json()

auto_genres = ",".join(
    g["value"]
    for g in genres_data.get("genres", [])
)

# ==========================================================
# 2. FETCH CHANNELS (AUTO)
# ==========================================================
print("Fetching auto channels...")

channel_url = "https://catalogapi.zee5.com/v1/channel"

auto_response = requests.get(
    channel_url,
    params={
        'page': '1',
        'page_size': '100',
        'genres': auto_genres,
        'country': 'IN',
        'translation': 'en',
        'languages':
            'en,hi,hr,or,gu,ta,'
            'kn,pa,ml,mr,bn,te'
    },
    headers=headers
)

auto_channels = auto_response.json().get(
    "items",
    []
)

# ==========================================================
# 3. FETCH CHANNELS (HARDCODED)
# ==========================================================
print("Fetching hardcoded channels...")

hardcoded_response = requests.get(
    channel_url,
    params={
        'sort_by_field': 'channel_number',
        'page': '1',
        'page_size': '100',
        'genres': (
            'News,Electro Dance Music,'
            'Movie,Entertainment,'
            'Lifestyle,Devotional,'
            'Comedy,Drama,Education,'
            'Mythology,Trap,Indie,'
            'Crime & Mystery,Fitness,'
            'Live Event,Musical,'
            'Spiritual,'
            'Devotion/Spiritual'
        ),
        'country': 'IN',
        'translation': 'en',
        'languages':
            'en,hi,hr,or,gu,ta,'
            'kn,pa,ml,mr,bn,te'
    },
    headers=headers
)

hardcoded_channels = hardcoded_response.json().get(
    "items",
    []
)

# ==========================================================
# 4. MERGE CHANNELS
# ==========================================================
print("Merging channels...")

channel_map = {}

for ch in auto_channels + hardcoded_channels:
    channel_map[ch["id"]] = ch

channel_items = list(channel_map.values())

channel_ids = [
    ch["id"]
    for ch in channel_items
]

print(
    f"Total channels found: "
    f"{len(channel_ids)}"
)

# ==========================================================
# 5. CREATE XMLTV ROOT
# ==========================================================
tv = ET.Element(
    "tv",
    attrib={
        "generator-info-name":
            "Zee5 EPG Generator"
    }
)

# ==========================================================
# 6. ADD CHANNELS
# ==========================================================
print("Adding channels...")

for channel in channel_items:

    channel_id = channel["id"]

    ch = ET.SubElement(
        tv,
        "channel",
        id=channel_id
    )

    # Channel Name
    ET.SubElement(
        ch,
        "display-name"
    ).text = channel.get(
        "title",
        channel_id
    )

    # Channel Logo (FIXED)
    logo = get_channel_logo(channel)

    if logo:
        ET.SubElement(
            ch,
            "icon",
            src=logo
        )

# ==========================================================
# 7. FETCH EPG (-7 TO TODAY)
# ==========================================================
print("Fetching EPG...")

epg_url = "https://gwapi.zee5.com/v1/epg"

seen = set()

for day in range(-7, 4):

    print(f"Day {day}")

    response = requests.get(
        epg_url,
        params={
            'channels':
                ",".join(channel_ids),
            'start': str(day),
            'end': str(day),
            'time_offset': '+05:30',
            'page_size': '100',
            'translation': 'en',
            'country': 'IN'
        },
        headers=headers
    )

    epg_data = response.json()

    for channel in epg_data.get(
        "items",
        []
    ):

        channel_id = channel["id"]

        for item in channel.get(
            "items",
            []
        ):

            start = item.get(
                "start_time"
            )

            stop = item.get(
                "end_time"
            )

            if not start or not stop:
                continue

            # Remove duplicates
            unique = (
                channel_id,
                start,
                stop,
                item.get("title")
            )

            if unique in seen:
                continue

            seen.add(unique)

            # Time formatting
            start_dt = datetime.fromisoformat(
                start.replace(
                    "Z",
                    "+00:00"
                )
            )

            stop_dt = datetime.fromisoformat(
                stop.replace(
                    "Z",
                    "+00:00"
                )
            )

            programme = ET.SubElement(
                tv,
                "programme",
                start=start_dt.strftime(
                    "%Y%m%d%H%M%S +0000"
                ),
                stop=stop_dt.strftime(
                    "%Y%m%d%H%M%S +0000"
                ),
                channel=channel_id
            )

            # Title
            ET.SubElement(
                programme,
                "title",
                lang="en"
            ).text = item.get(
                "title",
                "Unknown"
            )

            # Description
            desc = item.get(
                "description",
                ""
            )

            if desc:
                ET.SubElement(
                    programme,
                    "desc",
                    lang="en"
                ).text = desc

            # Category
            genres = item.get(
                "genres",
                []
            )

            if genres:
                ET.SubElement(
                    programme,
                    "category"
                ).text = genres[0].get(
                    "value",
                    ""
                )

            # Programme Image
            prog_image = get_programme_image(item)

            if prog_image:
                ET.SubElement(
                    programme,
                    "icon",
                    src=prog_image
                )

# ==========================================================
# 8. PRETTY XML
# ==========================================================
print("Formatting XML...")

raw_xml = ET.tostring(
    tv,
    encoding="utf-8"
)

pretty_xml = minidom.parseString(
    raw_xml
).toprettyxml(
    indent="  ",
    encoding="utf-8"
)

# Remove empty lines
pretty_xml = b"\n".join(
    line
    for line in pretty_xml.splitlines()
    if line.strip()
)

# ==========================================================
# 9. SAVE XML.GZ
# ==========================================================
output = "Zee5.xml.gz"

with gzip.open(
    output,
    "wb"
) as f:
    f.write(pretty_xml)

print(f"Saved: {output}")
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from geopy.geocoders import Nominatim
import piexif
from staticmap import StaticMap, CircleMarker
from datetime import datetime, timedelta, time
import tempfile
import zipfile
import os
import requests
from io import BytesIO

# ---------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------

st.set_page_config(
    page_title="GPS Map Camera PRO",
    layout="wide"
)

st.title("📍 GPS Map Camera – PRO Clone")

# ---------------------------------------------------
# FONT SYSTEM
# ---------------------------------------------------

def get_font(size=24, bold=False):

    possible_fonts = []

    if bold:
        possible_fonts = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"
        ]
    else:
        possible_fonts = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"
        ]

    for font_path in possible_fonts:
        if os.path.exists(font_path):
            return ImageFont.truetype(font_path, size)

    return ImageFont.load_default()

# ---------------------------------------------------
# SHADOW TEXT
# ---------------------------------------------------

def draw_shadow_text(draw,
                     position,
                     text,
                     font,
                     fill="white"):

    x, y = position

    shadow_offset = max(2, font.size // 18)

    # Shadow
    draw.text(
        (x + shadow_offset, y + shadow_offset),
        text,
        font=font,
        fill="black"
    )

    # Main text
    draw.text(
        (x, y),
        text,
        font=font,
        fill=fill
    )

# ---------------------------------------------------
# GPS UTILITIES
# ---------------------------------------------------

def dms_to_deg(dms):

    d, m, s = dms

    return (
        d[0] / d[1]
        + m[0] / m[1] / 60
        + s[0] / s[1] / 3600
    )

def extract_gps(image):

    try:

        exif_dict = piexif.load(image.info["exif"])
        gps = exif_dict["GPS"]

        lat = dms_to_deg(gps[2])

        if gps[1] == b'S':
            lat = -lat

        lon = dms_to_deg(gps[4])

        if gps[3] == b'W':
            lon = -lon

        return lat, lon

    except:
        return None, None

# ---------------------------------------------------
# OFFLINE MAP
# ---------------------------------------------------

def create_map(lat, lon):

    m = StaticMap(
        500,
        320,
        url_template=
        "https://a.tile.openstreetmap.org/{z}/{x}/{y}.png"
    )

    m.add_marker(
        CircleMarker((lon, lat), "red", 12)
    )

    return m.render().convert("RGB")

# ---------------------------------------------------
# GOOGLE SATELLITE MAP
# ---------------------------------------------------

def create_google_satellite_map(
    lat,
    lon,
    api_key,
    zoom=17,
    size="500x320"
):

    url = (
        "https://maps.googleapis.com/maps/api/staticmap"
        f"?center={lat},{lon}"
        f"&zoom={zoom}"
        f"&size={size}"
        "&maptype=satellite"
        f"&markers=color:red|{lat},{lon}"
        f"&key={api_key}"
    )

    response = requests.get(url)

    if response.status_code != 200:
        raise Exception("Google Maps API error")

    return Image.open(
        BytesIO(response.content)
    ).convert("RGB")

# ---------------------------------------------------
# FILE UPLOAD
# ---------------------------------------------------

files = st.file_uploader(
    "Upload Images",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True
)

# ---------------------------------------------------
# LOCATION SETTINGS
# ---------------------------------------------------

st.subheader("📍 Location Settings")

manual_lat = st.number_input(
    "Manual Latitude (fallback)",
    value=16.676566,
    format="%.6f"
)

manual_lon = st.number_input(
    "Manual Longitude (fallback)",
    value=74.255245,
    format="%.6f"
)

simulate_movement = st.checkbox(
    "Simulate Photographer Movement"
)

use_custom_location = st.checkbox(
    "Override Auto-Location Name"
)

custom_location_text = st.text_input(
    "Custom Location Text",
    "My Custom Site, Project ABC"
)

# ---------------------------------------------------
# DATE & TIME SETTINGS
# ---------------------------------------------------

st.subheader("🕒 Date & Time Settings")

use_custom_time = st.checkbox(
    "Use Custom Date & Time"
)

col1, col2 = st.columns(2)

with col1:

    custom_date = st.date_input(
        "Custom Date",
        "today"
    )

with col2:

    st.write("Custom Time")

    t1, t2, t3 = st.columns(3)

    with t1:
        hr = st.selectbox(
            "Hr",
            [f"{i:02d}" for i in range(1, 13)],
            index=11
        )

    with t2:
        mn = st.selectbox(
            "Min",
            [f"{i:02d}" for i in range(60)],
            index=0
        )

    with t3:
        ampm = st.selectbox(
            "AM/PM",
            ["AM", "PM"]
        )

    hr24 = int(hr) % 12

    if ampm == "PM":
        hr24 += 12

    custom_time = time(
        hr24,
        int(mn)
    )

# ---------------------------------------------------
# MAP SETTINGS
# ---------------------------------------------------

st.subheader("🗺 Map Settings")

map_mode = st.radio(
    "Map Style",
    [
        "Google Satellite (API Key)",
        "Offline / OpenStreetMap"
    ],
    index=1
)

google_api_key = st.text_input(
    "Google Maps API Key",
    type="password"
)

# ---------------------------------------------------
# PROCESS
# ---------------------------------------------------

process = st.button(
    "🚀 Process Images"
)

# ---------------------------------------------------
# MAIN PROCESSING
# ---------------------------------------------------

if files and process:

    geolocator = Nominatim(
        user_agent="gps_camera_pro"
    )

    zip_path = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".zip"
    ).name

    with zipfile.ZipFile(
        zip_path,
        "w"
    ) as zipf:

        progress = st.progress(0)

        for idx, file in enumerate(files):

            # ----------------------------------------
            # OPEN IMAGE
            # ----------------------------------------

            img = Image.open(file).convert("RGB")

            draw = ImageDraw.Draw(img)

            img_width = img.width
            img_height = img.height

            # ----------------------------------------
            # ADAPTIVE FONT SIZES
            # ----------------------------------------

            title_size = max(42, img_width // 28)
            info_size = max(30, img_width // 45)
            small_size = max(24, img_width // 55)

            title_font = get_font(
                title_size,
                bold=True
            )

            info_font = get_font(
                info_size
            )

            small_font = get_font(
                small_size
            )

            # ----------------------------------------
            # GPS EXTRACTION
            # ----------------------------------------

            lat, lon = extract_gps(img)

            if lat is None:
                lat, lon = manual_lat, manual_lon

            # ----------------------------------------
            # SIMULATED MOVEMENT
            # ----------------------------------------

            if simulate_movement:

                lat += idx * 0.00015
                lon += idx * 0.00015

            # ----------------------------------------
            # LOCATION NAME
            # ----------------------------------------

            if (
                use_custom_location
                and custom_location_text.strip()
            ):

                final_location_string = (
                    custom_location_text.strip()
                )

            else:

                try:

                    location = geolocator.reverse(
                        (lat, lon),
                        zoom=18
                    )

                    addr = location.raw.get(
                        "address",
                        {}
                    )

                    city = addr.get(
                        "city",
                        addr.get(
                            "town",
                            addr.get(
                                "village",
                                ""
                            )
                        )
                    )

                    state = addr.get(
                        "state",
                        ""
                    )

                    country = addr.get(
                        "country",
                        ""
                    )

                    parts = [
                        p for p in (
                            city,
                            state,
                            country
                        ) if p
                    ]

                    final_location_string = (
                        ", ".join(parts)
                    )

                except:

                    final_location_string = (
                        "Unknown Location"
                    )

            # ----------------------------------------
            # MAP GENERATION
            # ----------------------------------------

            if (
                map_mode
                == "Google Satellite (API Key)"
            ):

                if not google_api_key:

                    st.error(
                        "Google API key required"
                    )

                    st.stop()

                map_img = (
                    create_google_satellite_map(
                        lat,
                        lon,
                        google_api_key
                    )
                )

            else:

                map_img = create_map(
                    lat,
                    lon
                )

            # ----------------------------------------
            # ADAPTIVE PANEL
            # ----------------------------------------

            panel_height = int(
                img_height * 0.22
            )

            overlay = Image.new(
                "RGBA",
                (img_width, panel_height),
                (0, 0, 0, 190)
            )

            img.paste(
                overlay,
                (0, img_height - panel_height),
                overlay
            )

            # ----------------------------------------
            # MAP SIZE
            # ----------------------------------------

            map_w = int(img_width * 0.25)
            map_h = int(panel_height * 0.78)

            map_img = map_img.resize(
                (map_w, map_h)
            )

            map_x = int(img_width * 0.02)
            map_y = img_height - panel_height + int(panel_height * 0.08)

            img.paste(
                map_img,
                (map_x, map_y)
            )

            # ----------------------------------------
            # TEXT POSITION
            # ----------------------------------------

            text_x = map_x + map_w + int(img_width * 0.03)

            y0 = img_height - panel_height + int(panel_height * 0.10)

            # ----------------------------------------
            # LOCATION TEXT
            # ----------------------------------------

            draw_shadow_text(
                draw,
                (text_x, y0),
                final_location_string,
                title_font
            )

            # ----------------------------------------
            # COORDINATES
            # ----------------------------------------

            draw_shadow_text(
                draw,
                (
                    text_x,
                    y0 + int(info_size * 1.8)
                ),
                f"Lat {lat:.6f}°",
                info_font
            )

            draw_shadow_text(
                draw,
                (
                    text_x,
                    y0 + int(info_size * 3.0)
                ),
                f"Long {lon:.6f}°",
                info_font
            )

            # ----------------------------------------
            # DATETIME
            # ----------------------------------------

            if use_custom_time:

                dt = datetime.combine(
                    custom_date,
                    custom_time
                )

                if simulate_movement:

                    dt += timedelta(
                        minutes=idx * 2
                    )

            else:

                dt = datetime.now()

            draw_shadow_text(
                draw,
                (
                    text_x,
                    y0 + int(info_size * 4.5)
                ),
                dt.strftime(
                    "%A, %d/%m/%Y %I:%M %p GMT +05:30"
                ),
                small_font
            )

            # ----------------------------------------
            # SAVE OUTPUT
            # ----------------------------------------

            out = tempfile.NamedTemporaryFile(
                delete=False,
                suffix=".jpg"
            )

            img.save(
                out.name,
                quality=95
            )

            zipf.write(
                out.name,
                f"gps_{idx+1}.jpg"
            )

            # ----------------------------------------
            # PREVIEW
            # ----------------------------------------

            if idx == 0:

                st.subheader("🖼 Preview")

                st.image(
                    img,
                    use_container_width=True
                )

            progress.progress(
                (idx + 1) / len(files)
            )

    # ---------------------------------------------------
    # DOWNLOAD
    # ---------------------------------------------------

    st.success("✅ Processing Complete")

    with open(zip_path, "rb") as f:

        st.download_button(
            "⬇ Download ZIP",
            f,
            file_name=
            "gps_map_camera_outputs.zip"
        )

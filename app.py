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
# FONT SYSTEM (Single-file cloud compatible)
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

title_font = get_font(34, bold=True)
info_font = get_font(24)
small_font = get_font(20)

# ---------------------------------------------------
# TEXT SHADOW
# ---------------------------------------------------

def draw_shadow_text(draw,
                     position,
                     text,
                     font,
                     fill="white"):

    x, y = position

    # Shadow
    draw.text(
        (x + 2, y + 2),
        text,
        font=font,
        fill="black"
    )

    # Main Text
    draw.text(
        (x, y),
        text,
        font=font,
        fill=fill
    )

# ---------------------------------------------------
# UTILITIES
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
        320,
        220,
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
    size="320x220"
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
    16.676566,
    format="%.6f"
)

manual_lon = st.number_input(
    "Manual Longitude (fallback)",
    74.255245,
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

    t_col1, t_col2, t_col3 = st.columns([1, 1, 1])

    with t_col1:
        hr = st.selectbox(
            "Hr",
            [f"{i:02d}" for i in range(1, 13)],
            index=11
        )

    with t_col2:
        mn = st.selectbox(
            "Min",
            [f"{i:02d}" for i in range(60)],
            index=0
        )

    with t_col3:
        ampm = st.selectbox(
            "AM/PM",
            ["AM", "PM"],
            index=0
        )

    hr_24 = int(hr) % 12

    if ampm == "PM":
        hr_24 += 12

    custom_time = time(
        hr_24,
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
# PROCESS BUTTON
# ---------------------------------------------------

process = st.button(
    "🚀 Process Images"
)

# ---------------------------------------------------
# PROCESSING
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

            # ----------------------------------------
            # EXTRACT GPS
            # ----------------------------------------

            lat, lon = extract_gps(img)

            if lat is None:
                lat, lon = manual_lat, manual_lon

            # ----------------------------------------
            # SIMULATE MOVEMENT
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
            # MAP IMAGE
            # ----------------------------------------

            if (
                map_mode
                == "Google Satellite (API Key)"
            ):

                if google_api_key:

                    map_img = (
                        create_google_satellite_map(
                            lat,
                            lon,
                            google_api_key
                        )
                    )

                else:

                    st.error(
                        "Google API key required"
                    )

                    st.stop()

            else:

                map_img = create_map(
                    lat,
                    lon
                )

            # ----------------------------------------
            # OVERLAY PANEL
            # ----------------------------------------

            panel_height = 270

            overlay = Image.new(
                "RGBA",
                (img.width, panel_height),
                (0, 0, 0, 190)
            )

            img.paste(
                overlay,
                (0, img.height - panel_height),
                overlay
            )

            # ----------------------------------------
            # MAP POSITION
            # ----------------------------------------

            img.paste(
                map_img,
                (20, img.height - panel_height + 25)
            )

            # ----------------------------------------
            # TEXT POSITIONS
            # ----------------------------------------

            y0 = img.height - panel_height + 35

            # ----------------------------------------
            # LOCATION TEXT
            # ----------------------------------------

            draw_shadow_text(
                draw,
                (410, y0),
                final_location_string,
                title_font
            )

            # ----------------------------------------
            # COORDINATES
            # ----------------------------------------

            draw_shadow_text(
                draw,
                (410, y0 + 58),
                f"Lat {lat:.6f}°",
                info_font
            )

            draw_shadow_text(
                draw,
                (410, y0 + 92),
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
                (410, y0 + 132),
                dt.strftime(
                    "%A, %d/%m/%Y %I:%M %p GMT +05:30"
                ),
                small_font
            )

            # ----------------------------------------
            # SAVE IMAGE
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
                    caption="Preview of first image",
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

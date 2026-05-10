import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from geopy.geocoders import Nominatim
from datetime import datetime
from io import BytesIO
import piexif
import requests
import tempfile
import zipfile
import os

# ---------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------

st.set_page_config(
    page_title="GPS Map Camera",
    layout="wide"
)

st.title("📍 GPS Map Camera PRO")

# ---------------------------------------------------
# FONT LOADER
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

    for path in possible_fonts:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)

    return ImageFont.load_default()

title_font = get_font(34, bold=True)
info_font = get_font(24)
small_font = get_font(20)

# ---------------------------------------------------
# TEXT DRAWING
# ---------------------------------------------------

def draw_shadow_text(draw,
                     position,
                     text,
                     font,
                     fill="white"):

    x, y = position

    # shadow
    draw.text(
        (x+2, y+2),
        text,
        font=font,
        fill="black"
    )

    # main text
    draw.text(
        (x, y),
        text,
        font=font,
        fill=fill
    )

# ---------------------------------------------------
# EXIF GPS EXTRACTION
# ---------------------------------------------------

def dms_to_deg(dms):

    d = dms[0][0] / dms[0][1]
    m = dms[1][0] / dms[1][1]
    s = dms[2][0] / dms[2][1]

    return d + (m / 60) + (s / 3600)

def extract_gps(image):

    try:
        exif_data = piexif.load(image.info["exif"])

        gps = exif_data["GPS"]

        lat = dms_to_deg(gps[2])
        lon = dms_to_deg(gps[4])

        if gps[1] == b'S':
            lat = -lat

        if gps[3] == b'W':
            lon = -lon

        return lat, lon

    except:
        return None, None

# ---------------------------------------------------
# GOOGLE SATELLITE MAP
# ---------------------------------------------------

def create_google_map(lat,
                      lon,
                      api_key,
                      zoom=17,
                      size="400x250"):

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
        raise Exception("Google Maps API Error")

    return Image.open(BytesIO(response.content)).convert("RGB")

# ---------------------------------------------------
# SIDEBAR
# ---------------------------------------------------

st.sidebar.header("⚙ Settings")

google_api_key = st.sidebar.text_input(
    "Google Maps API Key",
    type="password"
)

manual_lat = st.sidebar.number_input(
    "Manual Latitude",
    value=16.676566,
    format="%.6f"
)

manual_lon = st.sidebar.number_input(
    "Manual Longitude",
    value=74.255245,
    format="%.6f"
)

zoom = st.sidebar.slider(
    "Map Zoom",
    10,
    22,
    17
)

# ---------------------------------------------------
# FILE UPLOAD
# ---------------------------------------------------

uploaded_files = st.file_uploader(
    "Upload Images",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True
)

# ---------------------------------------------------
# PROCESS BUTTON
# ---------------------------------------------------

if uploaded_files and st.button("🚀 Generate GPS Photos"):

    if not google_api_key:
        st.error("Please enter Google Maps API Key")
        st.stop()

    geolocator = Nominatim(
        user_agent="gps_map_camera"
    )

    zip_temp = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".zip"
    )

    with zipfile.ZipFile(zip_temp.name, "w") as zipf:

        progress = st.progress(0)

        for idx, uploaded_file in enumerate(uploaded_files):

            image = Image.open(uploaded_file).convert("RGB")

            draw = ImageDraw.Draw(image)

            # ----------------------------------------
            # GPS Extraction
            # ----------------------------------------

            lat, lon = extract_gps(image)

            if lat is None:
                lat = manual_lat
                lon = manual_lon

            # ----------------------------------------
            # Reverse Geocode
            # ----------------------------------------

            try:

                location = geolocator.reverse(
                    (lat, lon),
                    zoom=18
                )

                address = location.raw.get(
                    "address",
                    {}
                )

                city = address.get(
                    "city",
                    address.get(
                        "town",
                        address.get(
                            "village",
                            ""
                        )
                    )
                )

                state = address.get(
                    "state",
                    ""
                )

                country = address.get(
                    "country",
                    ""
                )

            except:

                city = "Unknown"
                state = ""
                country = ""

            # ----------------------------------------
            # MAP
            # ----------------------------------------

            map_img = create_google_map(
                lat,
                lon,
                google_api_key,
                zoom=zoom
            )

            # ----------------------------------------
            # OVERLAY PANEL
            # ----------------------------------------

            panel_height = 280

            overlay = Image.new(
                "RGBA",
                (image.width, panel_height),
                (0, 0, 0, 190)
            )

            image.paste(
                overlay,
                (0, image.height - panel_height),
                overlay
            )

            # ----------------------------------------
            # PASTE MAP
            # ----------------------------------------

            image.paste(
                map_img,
                (20, image.height - panel_height + 15)
            )

            # ----------------------------------------
            # TEXT
            # ----------------------------------------

            y0 = image.height - panel_height + 25

            timestamp = datetime.now().strftime(
                "%A, %d/%m/%Y %I:%M %p"
            )

            draw_shadow_text(
                draw,
                (450, y0),
                f"{city}, {state}, {country}",
                title_font
            )

            draw_shadow_text(
                draw,
                (450, y0 + 60),
                f"Lat {lat:.6f}°",
                info_font
            )

            draw_shadow_text(
                draw,
                (450, y0 + 95),
                f"Long {lon:.6f}°",
                info_font
            )

            draw_shadow_text(
                draw,
                (450, y0 + 135),
                timestamp,
                small_font
            )

            # ----------------------------------------
            # SAVE OUTPUT
            # ----------------------------------------

            out_temp = tempfile.NamedTemporaryFile(
                delete=False,
                suffix=".jpg"
            )

            image.save(
                out_temp.name,
                quality=95
            )

            zipf.write(
                out_temp.name,
                f"gps_photo_{idx+1}.jpg"
            )

            st.image(
                image,
                caption=f"Processed Image {idx+1}",
                use_container_width=True
            )

            progress.progress(
                (idx + 1) / len(uploaded_files)
            )

    # ---------------------------------------------------
    # DOWNLOAD
    # ---------------------------------------------------

    st.success("✅ Processing Complete")

    st.download_button(
        "⬇ Download ZIP",
        data=open(zip_temp.name, "rb"),
        file_name="gps_map_camera_outputs.zip",
        mime="application/zip"
    )

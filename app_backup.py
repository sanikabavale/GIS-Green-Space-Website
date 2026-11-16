
from __future__ import annotations

from pathlib import Path
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
import sqlite3
import hashlib
import secrets
import tempfile
import traceback

import streamlit as st
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import folium
from streamlit_folium  import st_folium
import json


# =========================================================
# APPLICATION CONFIGURATION
# =========================================================

ROOT = Path(__file__).resolve().parent
RUNTIME_DIR = ROOT / "runtime"
AUTH_DB = RUNTIME_DIR / "accounts.db"

RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

st.set_page_config(
    page_title="GIS Green Space Accessibility",
    page_icon="🌳",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =========================================================
# DATABASE AND AUTHENTICATION
# =========================================================

def get_connection():
    return sqlite3.connect(AUTH_DB)


def init_auth_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL
            )
        """)


def hash_password(password, salt):
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        200000
    ).hex()


def register_user(username, password):
    username = username.strip()

    if len(username) < 3:
        return False, "Username must contain at least 3 characters."

    if len(password) < 6:
        return False, "Password must contain at least 6 characters."

    salt = secrets.token_bytes(16)
    password_hash = hash_password(password, salt)

    try:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO users (username, password_hash, salt)
                VALUES (?, ?, ?)
                """,
                (username, password_hash, salt.hex())
            )

        return True, "Account created successfully."

    except sqlite3.IntegrityError:
        return False, "This username already exists."


def authenticate_user(username, password):
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, username, password_hash, salt
            FROM users
            WHERE username = ?
            """,
            (username.strip(),)
        ).fetchone()

    if not row:
        return None

    user_id, saved_username, saved_hash, saved_salt = row

    entered_hash = hash_password(
        password,
        bytes.fromhex(saved_salt)
    )

    if secrets.compare_digest(entered_hash, saved_hash):
        return {
            "id": user_id,
            "username": saved_username
        }

    return None


init_auth_db()


# =========================================================
# SESSION STATE
# =========================================================

DEFAULT_STATE = {
    "authenticated": False,
    "user": None,
    "boundary": None,
    "parks": None,
    "residential": None,
    "analysis": None,
    "source_names": {},
    "page": "Overview"
}

for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


# =========================================================
# GLOBAL THEME
# =========================================================

# =========================================================
# GLOBAL THEME - MINT & GREY
# =========================================================

st.markdown("""
<style>

.stApp,
[data-testid="stAppViewContainer"] {
    background-color: #EDF2F1 !important;
    color: #263D36 !important;
}

[data-testid="stHeader"] {
    background: rgba(237, 242, 241, 0.95) !important;
}

[data-testid="stSidebar"] {
    background-color: #DCE8E5 !important;
    border-right: 1px solid #B8CDC5;
}

[data-testid="stSidebar"] * {
    color: #263D36 !important;
}

h1, h2, h3, h4 {
    color: #315D53 !important;
    font-weight: 700 !important;
}

p, label, li, .stMarkdown, .stCaption {
    color: #344D44 !important;
}

[data-testid="stMetric"] {
    background: #FFFFFF !important;
    border: 1px solid #C5D8D0 !important;
    border-radius: 14px !important;
    padding: 18px !important;
}

[data-testid="stMetricLabel"] {
    color: #526C61 !important;
}

[data-testid="stMetricValue"] {
    color: #315D53 !important;
}

.stButton > button {
    background: #477B6A !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 9px !important;
    min-height: 43px !important;
    font-weight: 700 !important;
}

.stButton > button:hover {
    background: #315D53 !important;
    color: #FFFFFF !important;
    border: none !important;
}

.stTextInput input,
.stNumberInput input,
.stTextArea textarea {
    background: #FFFFFF !important;
    color: #263D36 !important;
    border: 1px solid #A9C3B8 !important;
    border-radius: 8px !important;
}

.stTextInput input::placeholder,
.stTextArea textarea::placeholder {
    color: #647C71 !important;
    opacity: 1 !important;
}

[data-testid="stFileUploader"] {
    background: #FFFFFF !important;
    border: 1px dashed #80A99C !important;
    border-radius: 12px !important;
    padding: 14px !important;
}

[data-testid="stFileUploader"] * {
    color: #344D44 !important;
}

[data-testid="stTabs"] button {
    color: #315D53 !important;
    font-weight: 600 !important;
}

[data-testid="stExpander"] {
    background: #FFFFFF !important;
    border: 1px solid #C5D8D0 !important;
    border-radius: 10px !important;
}

[data-testid="stAlert"] {
    color: #263D36 !important;
}

[data-testid="stDataFrame"],
[data-testid="stTable"] {
    background: #FFFFFF !important;
}

hr {
    border-color: #C5D8D0 !important;
}

.small-caption {
    color: #526C61 !important;
    font-size: 13px;
}

.login-heading {
    color: #315D53 !important;
    font-size: 34px;
    font-weight: 800;
}

.login-subtitle {
    color: #526C61 !important;
    font-size: 15px;
}

.login-panel {
    background: #FFFFFF;
    border: 1px solid #D0DFD9;
    border-radius: 18px;
    padding: 28px;
    box-shadow: 0 12px 35px rgba(39, 75, 61, 0.09);
}

.login-image {
    min-height: 590px;
    height: 100%;
    border-radius: 18px;
    background-image:
        linear-gradient(
            180deg,
            rgba(20, 50, 39, 0.08),
            rgba(20, 50, 39, 0.45)
        ),
        url("https://images.unsplash.com/photo-1511497584788-876760111969?w=1200");
    background-size: cover;
    background-position: center;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    padding: 35px;
    box-sizing: border-box;
}

.login-image h2 {
    color: #FFFFFF !important;
    font-size: 30px;
}

.login-image p {
    color: #FFFFFF !important;
    font-size: 15px;
}

div[data-testid="stRadio"] label {
    color: #315D53 !important;
}

@media (max-width: 768px) {
    .login-image {
        min-height: 250px;
    }

    .login-panel {
        padding: 18px;
    }
}
</style>
""", unsafe_allow_html=True)


# =========================================================
# LOGIN PAGE - ELEGANT SPLIT DESIGN 1A
# =========================================================

def show_login_page():

    st.markdown("<br>", unsafe_allow_html=True)

    left, right = st.columns(
        [1, 1.15],
        gap="large",
        vertical_alignment="center"
    )

    with left:

        st.markdown("""
            <h2 style="color:#315D53;">
                Welcome Back
            </h2>
            <p style="color:#526C61;">
                Sign in to continue to your GIS workspace.
            </p>
        """, unsafe_allow_html=True)

        login_tab, register_tab = st.tabs([
            "Sign In",
            "Create Account"
        ])

        with login_tab:

            username = st.text_input(
                "Username",
                key="login_username"
            )

            password = st.text_input(
                "Password",
                type="password",
                key="login_password"
            )

            if st.button(
                "Sign In",
                use_container_width=True,
                key="login_button"
            ):

                if not username.strip() or not password:
                    st.error(
                        "Please enter your username and password."
                    )

                else:

                    user = authenticate_user(
                        username,
                        password
                    )

                    if user:
                        st.session_state.authenticated = True
                        st.session_state.user = user

                        st.success("Login successful.")
                        st.rerun()

                    else:
                        st.error(
                            "Invalid username or password."
                        )

        with register_tab:

            st.markdown("### Create Your Account")

            new_username = st.text_input(
                "Choose Username",
                key="register_username"
            )

            new_password = st.text_input(
                "Choose Password",
                type="password",
                key="register_password"
            )

            confirm_password = st.text_input(
                "Confirm Password",
                type="password",
                key="confirm_password"
            )

            if st.button(
                "Create Account",
                use_container_width=True,
                key="register_button"
            ):

                if not new_username.strip() or not new_password or not confirm_password:
                    st.error("Please complete all fields.")

                elif new_password != confirm_password:
                    st.error("Passwords do not match.")

                else:

                    success, message = register_user(
                        new_username,
                        new_password
                    )

                    if success:
                        st.success(message)
                    else:
                        st.error(message)

        st.markdown("""
            <p style="
                text-align:center;
                color:#526C61;
                font-size:12px;
                padding-top:18px;
            ">
                GIS-Based Spatial Analysis of Public Green Spaces
            </p>
        """, unsafe_allow_html=True)

    with right:

        st.markdown(
            """
            <div style="
                min-height:570px;
                width:100%;
                border-radius:18px;
                background:
                    linear-gradient(
                        180deg,
                        rgba(8,35,24,0.05),
                        rgba(8,35,24,0.78)
                    ),
                    url('https://www.ramagroupindia.com/_next/image?q=75&url=https%3A%2F%2Fbackend.ramagroupindia.com%2Fuploads%2FAerial_view_of_Ravet_s_vibrant_cityscape_2_f26775e2cf.png&w=1080');
                background-size:cover;
                background-position:center;
                display:flex;
                flex-direction:column;
                justify-content:flex-end;
                padding:35px;
                box-sizing:border-box;
            ">
                <h2 style="color:white;font-size:34px;font-weight:800;">
                    GREEN PUNE
                </h2>
                <p style="color:white;font-size:16px;line-height:1.7;">
                    GIS-Based Spatial Analysis of Public Green Spaces
                    Across Pune and Pimpri-Chinchwad.
                    Explore urban parks and green space accessibility.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )



# =========================================================
# GEOSPATIAL HELPER FUNCTIONS
# =========================================================

def load_vector(uploaded_file):

    if uploaded_file is None:
        return None

    filename = uploaded_file.name
    suffix = Path(filename).suffix.lower()

    try:

        with tempfile.TemporaryDirectory() as temp_dir:

            temp_path = Path(temp_dir)

            if suffix == ".zip":

                with ZipFile(BytesIO(uploaded_file.getvalue())) as archive:

                    shapefiles = [
                        name for name in archive.namelist()
                        if name.lower().endswith(".shp")
                        and not Path(name).name.startswith("__")
                    ]

                    if not shapefiles:
                        raise ValueError(
                            "No shapefile (.shp) found in ZIP."
                        )

                    shp_name = shapefiles[0]
                    shp_folder = Path(shp_name).parent

                    for member in archive.namelist():

                        member_path = Path(member)

                        if member_path.parent != shp_folder:
                            continue

                        if member_path.name.startswith("__"):
                            continue

                        if member_path.suffix.lower() in [
                            ".shp", ".shx", ".dbf", ".prj",
                            ".cpg", ".qix", ".sbn", ".sbx"
                        ]:

                            target = temp_path / member_path.name

                            target.write_bytes(
                                archive.read(member)
                            )

                shp_path = temp_path / Path(shp_name).name

                gdf = gpd.read_file(shp_path)

            else:

                file_path = temp_path / Path(filename).name
                file_path.write_bytes(uploaded_file.getvalue())

                if suffix not in [
                    ".geojson", ".json", ".gpkg", ".kml", ".shp"
                ]:
                    raise ValueError(
                        "Unsupported file format. "
                        "Upload GeoJSON, JSON, GPKG, KML, SHP or ZIP."
                    )

                gdf = gpd.read_file(file_path)

            if gdf.empty:
                raise ValueError("The uploaded dataset is empty.")

            if gdf.geometry.isna().all():
                raise ValueError("No valid geometry found.")

            if gdf.crs is None:
                raise ValueError(
                    "CRS is missing. Please upload a dataset "
                    "with a defined coordinate reference system."
                )

            return gdf

    except Exception as exc:
        raise ValueError(f"Unable to read {filename}: {exc}") from exc


def clean_layer(gdf):

    if gdf is None:
        return None

    result = gdf.copy()

    result = result[
        result.geometry.notna()
        & ~result.geometry.is_empty
    ].copy()

    try:
        result.geometry = result.geometry.make_valid()
    except Exception:
        result.geometry = result.geometry.buffer(0)

    result = result[
        result.geometry.notna()
        & ~result.geometry.is_empty
    ].copy()

    return result.reset_index(drop=True)


def metric_crs_for(gdf):

    geographic = gdf.to_crs("EPSG:4326")

    center = geographic.geometry.union_all().centroid

    longitude = center.x
    latitude = center.y

    zone = int((longitude + 180) / 6) + 1

    if latitude >= 0:
        epsg = 32600 + zone
    else:
        epsg = 32700 + zone

    return f"EPSG:{epsg}"


def clip_layer(layer, boundary):

    if layer is None or boundary is None:
        return None

    if layer.empty or boundary.empty:
        return layer.iloc[0:0].copy()

    projected = layer.to_crs(boundary.crs)

    study_area = boundary.geometry.union_all()

    result = projected.copy()

    result.geometry = result.geometry.intersection(study_area)

    result = result[
        result.geometry.notna()
        & ~result.geometry.is_empty
    ].copy()

    return result.reset_index(drop=True)


def make_export_bundle(result):

    output = BytesIO()

    with tempfile.TemporaryDirectory() as temp_dir:

        gpkg_path = Path(temp_dir) / "GIS_Analysis.gpkg"

        layers = {
            "study_boundary": result["boundary"],
            "green_spaces": result["parks_clipped"],
            "park_buffer": result["buffer"],
            "residential_inside": result["inside"],
            "residential_outside": result["outside"]
        }

        for index, (layer_name, layer) in enumerate(layers.items()):

            if layer is None or layer.empty:
                continue

            layer.to_file(
                gpkg_path,
                layer=layer_name,
                driver="GPKG",
                engine="pyogrio",
                mode="w" if index == 0 else "a"
            )

        if gpkg_path.exists():
            with ZipFile(output, "w", ZIP_DEFLATED) as archive:
                archive.write(
                    gpkg_path,
                    arcname="GIS_Analysis.gpkg"
                )

    output.seek(0)
    return output


# =========================================================
# STATIC MAP RENDERING
# =========================================================


def render_static_map(
    boundary=None,
    parks=None,
    buffer=None,
    inside=None,
    outside=None
):

    candidates = [
        layer for layer in [
            boundary, parks, buffer, inside, outside
        ]
        if layer is not None and not layer.empty
    ]

    if not candidates:
        st.info("Upload spatial datasets to display the map.")
        return

    try:
        source = candidates[0]

        if source.crs is None:
            st.error("Map cannot be displayed because CRS is missing.")
            return

        # Convert all available layers to geographic coordinates
        map_layers = [
            (buffer, "Park Buffer", "#3296E8", 0.20),
            (outside, "Residential Outside", "#E58B53", 0.35),
            (inside, "Residential Inside", "#25B7A1", 0.40),
            (parks, "Green Spaces", "#18A66B", 0.65),
            (boundary, "Study Boundary", "#D5A84B", 0.02)
        ]

        valid_layers = []

        for layer, label, color, opacity in map_layers:
            if layer is not None and not layer.empty:
                if layer.crs is None:
                    st.warning(f"{label} layer has no CRS and was skipped.")
                    continue

                geo_layer = layer.to_crs("EPSG:4326")
                valid_layers.append(
                    (geo_layer, label, color, opacity)
                )

        if not valid_layers:
            st.warning("No valid GIS layers are available.")
            return

        # Calculate map center and bounds
        bounds = [
            layer.total_bounds
            for layer, _, _, _ in valid_layers
        ]

        min_x = min(b[0] for b in bounds)
        min_y = min(b[1] for b in bounds)
        max_x = max(b[2] for b in bounds)
        max_y = max(b[3] for b in bounds)

        center_lat = (min_y + max_y) / 2
        center_lon = (min_x + max_x) / 2

        # Create interactive Folium map
        gis_map = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=12,
            tiles="CartoDB positron",
            control_scale=True,
            scrollWheelZoom=True
        )

        # Add GIS layers
        for layer, label, color, opacity in valid_layers:

            folium.GeoJson(
                data=layer.to_json(),
                name=label,
                style_function=lambda feature, c=color, o=opacity: {
                    "color": c,
                    "weight": 2,
                    "fillColor": c,
                    "fillOpacity": o
                },
                tooltip=folium.GeoJsonTooltip(
                    fields=[],
                    labels=False,
                    sticky=True
                )
            ).add_to(gis_map)

        # Fit map to the available GIS data
        gis_map.fit_bounds([
            [min_y, min_x],
            [max_y, max_x]
        ])

        # Add layer controls
        folium.LayerControl(
            collapsed=False
        ).add_to(gis_map)

        # Render interactive map in Streamlit
        st_folium(
            gis_map,
            width=None,
            height=650,
            use_container_width=True,
            returned_objects=[]
        )

    except Exception as exc:
        st.error(f"Interactive map rendering failed: {exc}")



# =========================================================
# METRIC CARD
# =========================================================

def metric_card(label, value):

    st.metric(
        label=label,
        value=value
    )


# =========================================================
# MAIN APPLICATION
# =========================================================

def show_main_app():

    user = st.session_state.user

    # -----------------------------------------------------
    # SIDEBAR
    # -----------------------------------------------------

    with st.sidebar:

        st.markdown("""
        <div style="text-align:center;padding:15px 0;">
            <div style="font-size:38px;">🌳</div>
            <h2 style="font-size:20px;">
                GIS Green Space
            </h2>
            <p style="font-size:12px;color:#A9C5BA;">
                Spatial Accessibility Analysis
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        st.write(f"Welcome, **{user['username']}**")

        page = st.radio(
            "Navigation",
            [
                "Overview",
                "Data Manager",
                "Spatial Analysis",
                "Interactive Map",
                
            ],
            key="navigation"
        )

        st.divider()

        if st.button("Logout", use_container_width=True):

            for key in DEFAULT_STATE:
                if key in st.session_state:
                    st.session_state[key] = DEFAULT_STATE[key]

            st.rerun()

        st.caption("GIS Project | Pimpri-Chinchwad")

    # -----------------------------------------------------
    # OVERVIEW
    # -----------------------------------------------------

    if page == "Overview":

        st.title("GIS Green Space Accessibility")
        st.write(
            "Spatial analysis of public green spaces "
            "and residential accessibility in Pimpri-Chinchwad."
        )

        st.divider()

        boundary = st.session_state.boundary
        parks = st.session_state.parks
        residential = st.session_state.residential
        result = st.session_state.analysis

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            metric_card(
                "Study Boundary",
                "Loaded" if boundary is not None else "Not Loaded"
            )

        with col2:
            metric_card(
                "Green Spaces",
                len(parks) if parks is not None else 0
            )

        with col3:
            metric_card(
                "Residential Features",
                len(residential) if residential is not None else 0
            )

        with col4:
            metric_card(
                "Analysis Status",
                "Completed" if result else "Pending"
            )

        st.subheader("Study Area Map")

        render_static_map(
            boundary=boundary,
            parks=parks
        )

        st.subheader("Project Objectives")

        st.markdown("""
        - Identify public green spaces.
        - Analyse residential accessibility to green spaces.
        - Create buffer zones around parks.
        - Identify residential areas inside and outside buffer zones.
        - Calculate green-space area and accessibility coverage.
        """)

    # -----------------------------------------------------
    # DATA MANAGER
    # -----------------------------------------------------

    elif page == "Data Manager":

        st.title("Data Manager")

        st.write(
            "Upload spatial datasets for the study area."
        )

        st.info(
            "Supported formats: GeoJSON, JSON, GPKG, "
            "KML, SHP and ZIP Shapefile."
        )

        st.subheader("1. Study Boundary")

        boundary_file = st.file_uploader(
            "Upload Study Boundary",
            type=["geojson", "json", "gpkg", "kml", "zip", "shp"],
            key="boundary_upload"
        )

        if boundary_file is not None:

            if st.button("Load Study Boundary"):

                try:
                    gdf = clean_layer(load_vector(boundary_file))

                    st.session_state.boundary = gdf
                    st.session_state.analysis = None

                    st.session_state.source_names["boundary"] = (
                        boundary_file.name
                    )

                    st.success("Study boundary loaded successfully.")

                except Exception as exc:
                    st.error(str(exc))

        st.divider()

        st.subheader("2. Public Green Spaces")

        parks_file = st.file_uploader(
            "Upload Green Spaces",
            type=["geojson", "json", "gpkg", "kml", "zip", "shp"],
            key="parks_upload"
        )

        if parks_file is not None:

            if st.button("Load Green Spaces"):

                try:
                    gdf = clean_layer(load_vector(parks_file))

                    st.session_state.parks = gdf
                    st.session_state.analysis = None

                    st.session_state.source_names["parks"] = (
                        parks_file.name
                    )

                    st.success("Green spaces loaded successfully.")

                except Exception as exc:
                    st.error(str(exc))

        st.divider()

        st.subheader("3. Residential Areas")

        residential_file = st.file_uploader(
            "Upload Residential Dataset",
            type=["geojson", "json", "gpkg", "kml", "zip", "shp"],
            key="residential_upload"
        )

        if residential_file is not None:

            if st.button("Load Residential Data"):

                try:
                    gdf = clean_layer(load_vector(residential_file))

                    st.session_state.residential = gdf
                    st.session_state.analysis = None

                    st.session_state.source_names["residential"] = (
                        residential_file.name
                    )

                    st.success("Residential data loaded successfully.")

                except Exception as exc:
                    st.error(str(exc))

        st.divider()

       
        st.subheader("Loaded Dataset Information")

        for key, label in [
            ("boundary", "Study Boundary"),
            ("parks", "Green Spaces"),
            ("residential", "Residential Areas")
        ]:

            layer = st.session_state[key]

            if layer is not None:

                st.markdown(f"**{label}**")
                st.write(f"Features: {len(layer)}")
                st.write(f"CRS: {layer.crs}")

                with st.expander(f"View {label} attributes"):

                    display_df = pd.DataFrame(
                        layer.drop(columns="geometry").head(10)
                    )

                    st.markdown(
                        display_df.to_html(
                            index=False,
                            escape=True
                        ),
                        unsafe_allow_html=True
                    )


    # -----------------------------------------------------
    # SPATIAL ANALYSIS
    # -----------------------------------------------------

def render_static_map(
    boundary=None,
    parks=None,
    buffer=None,
    inside=None,
    outside=None
):
    try:
        import json
        from folium.plugins import Fullscreen

        # Prepare available GIS layers
        layer_config = [
            (buffer, "Park Buffer", "#3296E8", 0.20),
            (outside, "Residential Outside", "#E58B53", 0.35),
            (inside, "Residential Inside", "#25B7A1", 0.40),
            (parks, "Green Spaces", "#18A66B", 0.75),
            (boundary, "Study Boundary", "#D5A84B", 0.02)
        ]

        valid_layers = []

        for layer, name, color, opacity in layer_config:

            if layer is None or layer.empty:
                continue

            if layer.crs is None:
                st.warning(f"{name}: CRS is missing. Layer skipped.")
                continue

            geo_layer = layer.to_crs("EPSG:4326")
            geo_layer = geo_layer[
                geo_layer.geometry.notna()
                & ~geo_layer.geometry.is_empty
            ]

            if geo_layer.empty:
                continue

            # Export geometry only to avoid Timestamp serialization errors
            geojson_data = json.loads(
                geo_layer.geometry.to_json()
            )

            valid_layers.append({
                "name": name,
                "color": color,
                "opacity": opacity,
                "geojson": geojson_data,
                "bounds": geo_layer.total_bounds
            })

        if not valid_layers:
            st.info("No valid spatial data available. Upload GIS datasets first.")
            return

        # Calculate map center
        min_lon = min(item["bounds"][0] for item in valid_layers)
        min_lat = min(item["bounds"][1] for item in valid_layers)
        max_lon = max(item["bounds"][2] for item in valid_layers)
        max_lat = max(item["bounds"][3] for item in valid_layers)

        center_lat = (min_lat + max_lat) / 2
        center_lon = (min_lon + max_lon) / 2

        # Create interactive map
        gis_map = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=12,
            tiles="CartoDB positron",
            control_scale=True,
            scrollWheelZoom=True,
            dragging=True,
            zoom_control=True,
            prefer_canvas=True
        )

        # Add GIS layers
        for item in valid_layers:

            folium.GeoJson(
                data=item["geojson"],
                name=item["name"],
                style_function=lambda feature, c=item["color"], o=item["opacity"]: {
                    "color": c,
                    "weight": 2,
                    "fillColor": c,
                    "fillOpacity": o
                },
                highlight_function=lambda feature: {
                    "weight": 4,
                    "fillOpacity": 0.65
                }
            ).add_to(gis_map)

        # Fit map to GIS data
        gis_map.fit_bounds(
            [
                [min_lat, min_lon],
                [max_lat, max_lon]
            ],
            padding=(25, 25),
            max_zoom=15
        )

        # Add map controls
        folium.LayerControl(
            position="topright",
            collapsed=False
        ).add_to(gis_map)

        Fullscreen(
            position="topleft",
            title="Open Fullscreen",
            title_cancel="Exit Fullscreen"
        ).add_to(gis_map)

        # Display interactive map
        st_folium(
            gis_map,
            height=680,
            use_container_width=True,
            returned_objects=[]
        )

    except Exception as exc:
        st.error(f"Interactive GIS Map Error: {exc}")
 
    # -----------------------------------------------------
    # INTERACTIVE MAP PAGE
    # -----------------------------------------------------

    elif page == "Interactive Map":

        st.title("GIS Results Map")

        result = st.session_state.analysis

        if result is None:

            boundary = st.session_state.boundary
            parks = st.session_state.parks

            if boundary is not None or parks is not None:

                st.info("Showing uploaded GIS layers.")

                render_static_map(
                    boundary=boundary,
                    parks=parks
                )

            else:
                st.warning("Upload GIS datasets first.")

        else:

            render_static_map(
                boundary=result["boundary"],
                parks=result["parks_clipped"],
                buffer=result["buffer"],
                inside=result["inside"],
                outside=result["outside"]
            )

            st.caption(
                "Interactive GIS visualization of green spaces "
                "and residential accessibility."
            )
 
# =========================================================
# APPLICATION ENTRY POINT
# =========================================================

if not st.session_state.authenticated:
    show_login_page()
else:
    show_main_app()

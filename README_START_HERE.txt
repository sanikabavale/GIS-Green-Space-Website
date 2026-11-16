GREENSPACE GIS — PIMPRI-CHINCHWAD WEB APPLICATION
=================================================

WHAT THIS IS
A Streamlit web application for the GIS mini project:
“GIS-Based Spatial Analysis of Public Green Space Accessibility in Pimpri-Chinchwad, Maharashtra”.
It supports real vector data upload, CRS validation, geometry cleaning, clipping, dissolved proximity buffers, spatial selection, interactive mapping and downloadable analysis outputs.

IMPORTANT HONESTY / DATA NOTE
The ZIP intentionally contains no fabricated spatial dataset or claimed analysis results. You must upload real data before the analysis can run. A map preview without data is only a neutral location view, not an official municipal boundary. The app does not claim that a 500 m straight-line buffer equals walking accessibility.

RUN IN WINDOWS / VS CODE
1. Extract this ZIP to a short writable path, for example C:\GIS_Green_Space_Website.
2. Open that folder in VS Code (File > Open Folder).
3. Open Terminal > New Terminal (PowerShell).
4. Run these commands:

   py -m venv .venv
   .\.venv\Scripts\python.exe -m pip install --upgrade pip
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   .\.venv\Scripts\python.exe -m streamlit run app.py

5. Open http://localhost:8501 in your browser.

If Python launcher `py` is unavailable, use `python` instead. If PowerShell activation is blocked, the commands above do not require activation.

UPLOAD DATA
Open Data Manager and load:
- Study boundary: official PCMC / ward polygon (GeoJSON, GeoPackage, zipped Shapefile or KML).
- Green spaces: park / garden polygons (OSM or another documented source).
- Residential features: building footprints or residential-area polygons (recommended for inside/outside comparison).

A Shapefile must be uploaded as one ZIP containing .shp, .shx, .dbf and .prj. GeoPackage with multiple layers should be exported as a single-layer file before upload. If CRS is missing, enter the actual source CRS; do not guess it. The default EPSG:4326 is only correct for longitude/latitude coordinates.

WORKFLOW
1. Upload boundary, parks and (if available) residential features.
2. Open Spatial Analysis, choose buffer distance (default 500 m), and run.
3. Review measured area, feature counts and limitations.
4. Open Interactive Map and toggle layers.
5. Download the processed GeoPackage layers and summary ZIP / CSV.

GIS METHODS
- Geometry validation (make valid where supported)
- Reprojection to a locally estimated UTM CRS (metres)
- Clip parks and residential data to the study boundary
- Dissolved buffer around the clipped green-space polygons
- Spatial intersection selection for residential features inside / outside the buffer

ACADEMIC SUBMISSION
QGIS is mandatory in the assignment. This website is a companion analysis/visualization tool; also create and save a .qgz QGIS project, and use QGIS Print Layout to export at least two final maps. Include source URLs, retrieval date, CRS, licence/attribution, measured results and limitations in your report. OSM data attribution: © OpenStreetMap contributors, https://www.openstreetmap.org/copyright.

TROUBLESHOOTING
- Install dependencies with the commands above in a short folder path.
- If a package install fails, copy the complete terminal error; do not randomly downgrade packages.
- If layers do not overlap, verify their source CRS and geographic coverage.
- If Clip returns no features, verify the boundary and input layers really overlap.
- The app processes uploaded data in the current session; re-upload after restarting the app.

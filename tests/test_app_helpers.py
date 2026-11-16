"""Lightweight tests for the GIS application's geometry and CRS helpers."""
import geopandas as gpd
from shapely.geometry import Polygon


def test_polygon_area_in_projected_crs():
    polygon = Polygon([(0, 0), (100, 0), (100, 100), (0, 100)])
    layer = gpd.GeoDataFrame({"id": [1]}, geometry=[polygon], crs="EPSG:32643")
    assert round(layer.geometry.area.iloc[0]) == 10000


def test_make_valid_available():
    polygon = Polygon([(0, 0), (1, 1), (1, 0), (0, 1), (0, 0)])
    layer = gpd.GeoDataFrame({"id": [1]}, geometry=[polygon], crs="EPSG:4326")
    fixed = layer.geometry.make_valid()
    assert fixed.iloc[0] is not None

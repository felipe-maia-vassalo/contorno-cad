"""JPEGs reais, segmentação e calibração; sem substituir fotos por desenhos."""
from pathlib import Path

import numpy as np
import pytest

from contorno_cad.imaging import (contour_points, png_bytes, process_image,
                                   read_image, right_wall)
from contorno_cad.profiles import (calibration_scale, mm_to_pixels,
                                    pixels_to_mm, smooth_wall)
from contorno_cad.project import dumps, image_bytes, loads, new_project, set_image

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def test_real_jpeg_decodes_with_original_resolution():
    data = (EXAMPLES / "ponteira_referencia.jpeg").read_bytes()
    assert data[:2] == b"\xff\xd8"
    image = read_image(data)
    assert image.shape == (619, 936, 3) and image.dtype == np.uint8
    assert float(image.std()) > 40
    png = png_bytes(image)
    assert read_image(png).shape == image.shape


def test_real_dark_object_contour_and_parameter_changes():
    rgb = read_image((EXAMPLES / "ponteira_referencia.jpeg").read_bytes())
    settings = {"crop": [20, 25, 495, 600], "method": "Escuro", "threshold": 180,
                "close": 5, "min_area": 1000}
    processed = process_image(rgb, settings)
    assert len(processed["contours"]) == 1
    assert processed["mask"].shape == rgb.shape[:2]
    assert not np.array_equal(processed["overlay"], rgb)
    wall, frame = right_wall(processed["contours"][0])
    assert len(wall) == 12 and frame["height_px"] > 500
    assert len(contour_points(processed["contours"][0], 2.0)) >= 8
    altered = process_image(rgb, dict(settings, threshold=80))
    assert not np.array_equal(processed["mask"], altered["mask"])
    edges = process_image(rgb, dict(settings, method="Canny", low=40, high=120))
    assert np.count_nonzero(edges["mask"]) > 100


def test_real_white_object_color_background_and_invalid_crop():
    rgb = read_image((EXAMPLES / "ponteira_curva.jpeg").read_bytes())
    processed = process_image(rgb, {"crop": [170, 100, 1060, 1091],
                                  "method": "Fundo colorido", "saturation": 105,
                                  "close": 5, "min_area": 1000})
    assert rgb.shape == (1091, 1280, 3)
    assert len(processed["contours"]) >= 1
    assert len(right_wall(processed["contours"][0])[0]) == 12
    with pytest.raises(ValueError, match="Recorte"):
        process_image(rgb, {"crop": [50, 50, 20, 20]})
    with pytest.raises(ValueError, match="desconhecido"):
        process_image(rgb, {"method": "mágico"})


def test_explicit_calibration_coordinates_and_smoothing():
    scale = calibration_scale([[100, 10], [100, 510]], 45)
    assert scale == pytest.approx(.09)
    px = [{"x": 150, "y": 510}, {"x": 160, "y": 260}, {"x": 155, "y": 10}]
    mm = pixels_to_mm(px, scale, [100, 510])
    assert mm[0]["x"] == pytest.approx(4.5) and mm[-1]["y"] == 45
    restored = mm_to_pixels(mm, scale, [100, 510])
    for original, returned in zip(px, restored):
        assert original["x"] == pytest.approx(returned["x"])
        assert original["y"] == pytest.approx(returned["y"])
    smooth = smooth_wall(mm, 20)
    assert len(smooth) == 20 and all(p["kind"] == "spline" for p in smooth)
    assert smooth[0]["x"] == pytest.approx(mm[0]["x"])
    with pytest.raises(ValueError):
        calibration_scale([[0, 0], [0, 0]], 45)
    with pytest.raises(ValueError):
        calibration_scale([[0, 0], [100, 0]], -1)
    with pytest.raises(ValueError):
        pixels_to_mm(px, 0, [100, 510])


def test_curve_controls_and_tangents_survive_coordinate_roundtrip():
    points = [{"x": 150, "y": 200, "kind": "arc", "mid_x": 180, "mid_y": 150},
              {"x": 160, "y": 100, "kind": "spline", "tangent_start": [2, -3],
               "tangent_end": [0, -1]}]
    mm = pixels_to_mm(points, .1, [100, 300])
    assert mm[0]["mid_x"] == pytest.approx(8)
    assert mm[0]["mid_y"] == pytest.approx(15)
    assert mm[1]["tangent_start"] == pytest.approx([.2, .3])
    assert mm[1]["tangent_end"] == pytest.approx([0, .1])
    restored = mm_to_pixels(mm, .1, [100, 300])
    for initial, returned in zip(points, restored):
        for key, value in initial.items():
            if key == "kind":
                assert value == returned[key]
            else:
                assert value == pytest.approx(returned[key])


def test_project_roundtrip_preserves_real_photo_and_rejects_bad_data():
    project = new_project()
    data = (EXAMPLES / "ponteira_referencia.jpeg").read_bytes()
    set_image(project, data, "real.jpeg")
    project["profile"] = [{"x": 15.0, "y": 0.0}, {"x": 14.0, "y": 39.0}]
    restored = loads(dumps(project))
    assert image_bytes(restored) == data and restored == project
    with pytest.raises(ValueError, match="Versão"):
        loads(b'{"schema_version":99}')
    with pytest.raises(ValueError):
        read_image(b"not an image")

"""Geometria real: volumes, curvas, operações e recusas explícitas."""
import math

import pytest

from contorno_cad.cad import GeometryError, build_model, sample_profile, validate_solid


def cap_project():
    return {"mode": "cap", "profile": [{"x": 17, "y": 0}, {"x": 16, "y": 20},
                                          {"x": 15, "y": 40}],
            "params": {"shoulder_height": 40, "dome_rise": 5, "dome_shape": 1,
                       "inner_diameter": 22.22, "socket_depth": 30}}


def test_cap_uses_calibrated_wall_and_changes_real_geometry():
    project = cap_project()
    first = build_model(project)
    report = validate_solid(first)
    assert report["valid"] and report["solids"] == 1
    assert report["dimensions_mm"]["z"] == pytest.approx(45, abs=0.05)
    assert report["dimensions_mm"]["x"] == pytest.approx(34, abs=0.05)
    project["params"]["dome_rise"] = 8
    second = build_model(project)
    changed = validate_solid(second)
    assert changed["valid"]
    assert changed["dimensions_mm"]["z"] == pytest.approx(48, abs=0.05)
    assert changed["volume_mm3"] > report["volume_mm3"] + 100
    project["profile"][0]["x"] = 19
    wider = validate_solid(build_model(project))
    assert wider["dimensions_mm"]["x"] == pytest.approx(38, abs=0.05)


def test_cap_custom_spline_changes_volume():
    project = cap_project()
    before = validate_solid(build_model(project))["volume_mm3"]
    project["params"]["dome_controls"] = [{"r": 0.8, "h": 0.7}, {"r": 0.4, "h": 0.95}]
    after = validate_solid(build_model(project))
    assert after["valid"] and abs(after["volume_mm3"] - before) > 50


def test_cap_dimensions_are_independent_of_cached_tessellation():
    project = cap_project()
    project["params"]["dome_controls"] = [{"r": .9, "h": .3}, {"r": .75, "h": .55},
                                            {"r": .5, "h": .825}, {"r": .25, "h": .94}]
    model = build_model(project)
    before = validate_solid(model)["dimensions_mm"]
    model.val().tessellate(.05, .1)
    after = validate_solid(model)["dimensions_mm"]
    assert after == pytest.approx(before, abs=.001)
    assert after["z"] == pytest.approx(45, abs=.001)


@pytest.mark.parametrize("change", [{"inner_diameter": 40}, {"socket_depth": 46},
                                   {"dome_controls": [{"r": 0.2, "h": 0.8}, {"r": 0.4, "h": 0.7}]}])
def test_cap_rejects_breakthrough_and_bad_curves(change):
    project = cap_project()
    project["params"].update(change)
    with pytest.raises(GeometryError):
        build_model(project)


def test_extrusion_exact_volume_and_hole():
    project = {"mode": "extrusion", "profile": [{"x": 0, "y": 0}, {"x": 20, "y": 0},
                                                   {"x": 20, "y": 10}, {"x": 0, "y": 10}],
               "params": {"depth": 5}}
    before = validate_solid(build_model(project))
    assert before["valid"] and before["volume_mm3"] == pytest.approx(1000)
    project["operations"] = [{"type": "hole", "diameter": 4, "depth": 5, "x": 10, "y": 5}]
    after = validate_solid(build_model(project))
    assert after["volume_mm3"] == pytest.approx(1000 - math.pi * 2**2 * 5)


def test_revolution_cylinder_is_exact():
    project = {"mode": "revolution", "profile": [{"x": 5, "y": 0}, {"x": 5, "y": 10}]}
    report = validate_solid(build_model(project))
    assert report["valid"] and report["volume_mm3"] == pytest.approx(math.pi * 25 * 10)


def test_revolution_closes_one_axis_endpoint_and_preserves_annular_section():
    project = {"mode": "revolution", "profile": [{"x": 0, "y": 0},
               {"x": 5, "y": 0}, {"x": 5, "y": 10}]}
    assert validate_solid(build_model(project))["volume_mm3"] == pytest.approx(math.pi * 25 * 10)
    project["profile"] = [{"x": 3, "y": 0}, {"x": 5, "y": 0},
                          {"x": 5, "y": 10}, {"x": 3, "y": 10}]
    project["params"] = {"close_to_axis": False}
    assert validate_solid(build_model(project))["volume_mm3"] == pytest.approx(math.pi * 16 * 10)


def test_spline_and_arc_extrusions():
    for profile in ([{"x": 0, "y": 0}, {"x": 10, "y": 0},
                     {"x": 10, "y": 10, "kind": "arc", "mx": 15, "my": 5}, {"x": 0, "y": 10}],
                    [{"x": 0, "y": 0}, {"x": 10, "y": 0},
                     {"x": 12, "y": 5, "kind": "spline"},
                     {"x": 10, "y": 10, "kind": "spline"}, {"x": 0, "y": 10}]):
        assert validate_solid(build_model({"mode": "extrusion", "profile": profile,
                                           "params": {"depth": 4}}))["valid"]


def test_profile_preview_uses_true_arc_and_constrained_spline():
    arc = sample_profile([{"x": 10, "y": 0}, {"x": 10, "y": 10,
                          "kind": "arc", "mid_x": 15, "mid_y": 5}], 64)
    assert arc[0] == pytest.approx({"x": 10, "y": 0})
    assert arc[-1] == pytest.approx({"x": 10, "y": 10})
    assert max(p["x"] for p in arc) == pytest.approx(15, abs=.001)
    spline = sample_profile([{"x": 10, "y": 0}, {"x": 12, "y": 5, "kind": "spline",
                              "tangent_start": [0, 1]}, {"x": 10, "y": 10,
                              "kind": "spline", "tangent_end": [-1, 0]}], 128)
    assert spline[0] == pytest.approx({"x": 10, "y": 0})
    assert spline[-1] == pytest.approx({"x": 10, "y": 10})
    assert abs(spline[1]["x"] - 10) < abs(spline[1]["y"]) * .05
    assert abs(spline[-2]["y"] - 10) < abs(spline[-2]["x"] - 10) * .05


def test_assisted_cut_fillet_chamfer_and_scale():
    project = {"mode": "assisted", "primitives": [{"shape": "box", "width": 20,
                   "depth": 20, "height": 10}, {"shape": "cylinder", "radius": 3,
                   "height": 10, "operation": "cut"}]}
    before = validate_solid(build_model(project))
    assert before["volume_mm3"] == pytest.approx(4000 - math.pi * 9 * 10)
    project["operations"] = [{"type": "fillet", "selector": "vertical", "radius": 1},
                              {"type": "chamfer", "selector": "bottom", "distance": 0.2},
                              {"type": "scale", "factor": 2}]
    after = validate_solid(build_model(project))
    assert after["valid"] and after["dimensions_mm"]["z"] == pytest.approx(20)


def test_assisted_loft_is_real_solid():
    model = build_model({"mode": "assisted", "primitives": [{"shape": "loft", "sections": [
        {"z": 0, "radius": 10}, {"z": 12, "radius": 6}, {"z": 20, "radius": 8}]}]})
    assert validate_solid(model)["valid"]


def test_no_silent_ignored_operations_or_invalid_solids():
    project = cap_project()
    project["operations"] = [{"type": "unknown"}]
    with pytest.raises(GeometryError, match="não implementada"):
        build_model(project)
    project["operations"] = [{"type": "fillet", "radius": 1000}]
    with pytest.raises(GeometryError):
        build_model(project)
    with pytest.raises(GeometryError):
        build_model({"mode": "extrusion", "profile": [{"x": 0, "y": 0}, {"x": 1, "y": 1}],
                     "params": {"depth": 5}})

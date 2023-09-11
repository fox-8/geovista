"""Unit-tests for :meth:`geovista.geoplotter.GeoPlotter.add_base_layer`."""
from __future__ import annotations

import pytest

from geovista.geoplotter import OPACITY_BLACKLIST, GeoPlotter


def test_no_opacity_kwarg(mocker):
    """Test with no opacity render request."""
    plotter = GeoPlotter()
    spy = mocker.spy(plotter, "_warn_opacity")
    plotter.add_base_layer()
    assert spy.call_count == 0
    assert plotter._missing_opacity is False


@pytest.mark.parametrize("key", ["opacity", "nan_opacity"])
@pytest.mark.parametrize("value", [None, 0.5])
def test_gpu_opacity_available(mocker, key, value):
    """Test with a mock gpu supporting opacity."""
    renderer = mocker.sentinel.renderer
    version = mocker.sentinel.version
    minfo = mocker.MagicMock(renderer=renderer, version=version)
    _ = mocker.patch("pyvista.GPUInfo", return_value=minfo)
    plotter = GeoPlotter()
    spy = mocker.spy(plotter, "add_text")
    kwargs = {key: value}
    plotter.add_base_layer(**kwargs)
    assert spy.call_count == 0
    assert plotter._missing_opacity is False


@pytest.mark.parametrize("key", ["opacity"])
@pytest.mark.parametrize("value", [None, 0.5])
def test_gpu_opacity_unavailable(mocker, key, value):
    """Test with a mock gpu not supporting opacity."""
    renderer, version = OPACITY_BLACKLIST[0]
    minfo = mocker.MagicMock(renderer=renderer, version=version)
    _ = mocker.patch("pyvista.GPUInfo", return_value=minfo)
    plotter = GeoPlotter()
    spy = mocker.spy(plotter, "add_text")
    kwargs = {key: value}
    plotter.add_base_layer(**kwargs)
    if value is None:
        assert spy.call_count == 0
        assert plotter._missing_opacity is False
    else:
        assert spy.call_count == 1
        args = ("Requires GPU opacity support",)
        kwargs = {
            "position": "lower_right",
            "font_size": 7,
            "color": "red",
            "shadow": True,
        }
        spy.assert_called_once_with(*args, **kwargs)
        assert plotter._missing_opacity is True

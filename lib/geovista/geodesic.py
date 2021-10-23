from collections.abc import Iterable
from typing import List, Optional, Tuple

import numpy as np
from numpy.typing import ArrayLike
import pyproj
import pyvista as pv

from .common import to_xyz, wrap
from .log import get_logger

__all__ = ["bbox", "geodesic", "geodesic_by_idx"]

# Configure the logger.
logger = get_logger(__name__)

#: Geodesic ellipse for manifold creation. See :func:`pyproj.get_ellps_map`.
MANIFOLD_ELLIPSE: str = "WGS84"

#: Number of equally spaced geodesic points between/including endpoint/s.
MANIFOLD_NPTS: int = 64

#: The bounding-box geometry will contain ``MANIFOLD_C**2`` faces.
MANIFOLD_C: int = 128


def geodesic(
    start_lon: float,
    start_lat: float,
    end_lon: float,
    end_lat: float,
    npts: Optional[int] = MANIFOLD_NPTS,
    radians: Optional[bool] = False,
    include_start: Optional[bool] = False,
    include_end: Optional[bool] = False,
    geod: Optional[pyproj.Geod] = None,
) -> Tuple[Tuple[float], Tuple[float]]:
    """
    TBD

    Notes
    -----
    .. versionadded:: 0.1.0

    """
    if geod is None:
        geod = pyproj.Geod(ellps=MANIFOLD_ELLIPSE)

    initial_idx = 0 if include_start else 1
    terminus_idx = 0 if include_end else 1

    glonlats = geod.npts(
        start_lon,
        start_lat,
        end_lon,
        end_lat,
        npts,
        radians=radians,
        initial_idx=initial_idx,
        terminus_idx=terminus_idx,
    )
    glons, glats = zip(*glonlats)
    glons = tuple(wrap(glons))

    return glons, glats


def geodesic_by_idx(
    longitudes: ArrayLike,
    latitudes: ArrayLike,
    start_idx: int,
    end_idx: int,
    npts: Optional[int] = MANIFOLD_NPTS,
    radians: Optional[bool] = False,
    include_start: Optional[bool] = False,
    include_end: Optional[bool] = False,
    geod: Optional[pyproj.Geod] = None,
) -> Tuple[List[float], List[float]]:
    """
    TBD

    Notes
    -----
    .. versionadded:: 0.1.0

    """
    if geod is None:
        geod = pyproj.Geod(ellps=MANIFOLD_ELLIPSE)

    start_lonlat = longitudes[start_idx], latitudes[start_idx]
    end_lonlat = longitudes[end_idx], latitudes[end_idx]

    result = geodesic(
        *start_lonlat,
        *end_lonlat,
        npts=npts,
        radians=radians,
        include_start=include_start,
        include_end=include_end,
        geod=geod,
    )

    return result


def bbox(
    longitudes: ArrayLike,
    latitudes: ArrayLike,
    ellps: Optional[str] = MANIFOLD_ELLIPSE,
    radius: Optional[float] = 1.1,
    c: Optional[int] = MANIFOLD_C,
    triangulate: Optional[bool] = False,
) -> pv.PolyData:
    """
    TBD

    Notes
    -----
    .. versionadded:: 0.1.0

    """
    if not isinstance(longitudes, Iterable):
        longitudes = [longitudes]
    if not isinstance(latitudes, Iterable):
        latitudes = [latitudes]

    lons = np.asanyarray(longitudes)
    lats = np.asanyarray(latitudes)
    n_lons, n_lats = lons.size, lats.size

    if n_lons != n_lats:
        emsg = (
            f"Require the same number of longitudes ({n_lons}) and "
            f"latitudes ({n_lats})."
        )
        raise ValueError(emsg)

    if n_lons < 4:
        emsg = (
            "Require a bounded-box geometry containing at least 4 longitude/latitude "
            f"values to create the bounded-box manifold, only got {n_lons}."
        )
        raise ValueError(emsg)

    if n_lons > 5:
        emsg = (
            "Require a bounded-box geometry containing 4 (open) or 5 (closed) "
            "longitude/latitude values to create the bounded-box manifold, "
            f"got {n_lons}."
        )
        raise ValueError(emsg)

    # ensure the specified bbox geometry is open
    if np.isclose(lons[0], lons[-1]) and np.isclose(lats[0], lats[-1]):
        lons, lats = lons[-1], lats[-1]

    # initialise
    idx_map = np.empty((c + 1, c + 1), dtype=int)
    bbox_lons, bbox_lats = [], []
    bbox_count = 0
    geod = pyproj.Geod(ellps=ellps)
    npts = c - 1
    n_faces = c * c
    logger.debug(f"c: {c}")
    logger.debug(f"n_faces: {n_faces}")
    logger.debug(f"idx_map: {idx_map.shape}")

    # corner indices
    c1_idx, c2_idx, c3_idx, c4_idx = range(4)

    def bbox_extend(lons: List[float], lats: List[float]) -> int:
        assert len(lons) == len(lats)
        bbox_lons.extend(lons)
        bbox_lats.extend(lats)
        return bbox_count + len(lons)

    def bbox_update(idx1, idx2, row=None, column=None) -> int:
        assert row is not None or column is not None
        if row is None:
            row = slice(None)
        if column is None:
            column = slice(None)
        glons, glats = geodesic_by_idx(
            bbox_lons, bbox_lats, idx1, idx2, npts=npts, geod=geod
        )
        idx_map[row, column] = [idx1] + list(np.arange(npts) + bbox_count) + [idx2]
        return bbox_extend(glons, glats)

    # register bbox edge indices, and points
    bbox_count = bbox_extend(lons, lats)
    bbox_count = bbox_update(c1_idx, c2_idx, row=0)
    bbox_count = bbox_update(c4_idx, c3_idx, row=-1)
    bbox_count = bbox_update(c1_idx, c4_idx, column=0)
    bbox_count = bbox_update(c2_idx, c3_idx, column=-1)

    # register bbox inner indices and points
    for row_idx in range(1, c):
        row = idx_map[row_idx]
        bbox_count = bbox_update(row[0], row[-1], row=row_idx)

    # generate the faces indices
    N_faces = np.broadcast_to(np.array([4], dtype=np.int8), (n_faces, 1))
    faces_c1 = np.ravel(idx_map[:c, :c]).reshape(-1, 1)
    faces_c2 = np.ravel(idx_map[:c, 1:]).reshape(-1, 1)
    faces_c3 = np.ravel(idx_map[1:, 1:]).reshape(-1, 1)
    faces_c4 = np.ravel(idx_map[1:, :c]).reshape(-1, 1)
    faces = np.hstack([N_faces, faces_c1, faces_c2, faces_c3, faces_c4])

    # generate the mesh
    xyz = to_xyz(bbox_lons, bbox_lats, radius=radius)
    pdata = pv.PolyData(xyz, faces=faces, n_faces=n_faces)
    logger.debug(f"bbox: n_faces={pdata.n_faces}, n_points={pdata.n_points}")

    if triangulate:
        pdata = pdata.triangulate()
        logger.debug(f"bbox: n_faces={pdata.n_faces}, n_points={pdata.n_points} (tri)")

    return pdata
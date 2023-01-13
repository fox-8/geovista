#!/usr/bin/env python3
"""
This example demonstrates how to create a mesh from CF UGRID 1-D latitude and
longitude (degrees) unstructured cell points and connectivity. The resulting
mesh contains quad cells.

It uses an unstructured Met Office LFRic C48 cubed-sphere of surface altitude
data.

Note that, the data is located on the mesh nodes/points which results in mesh
interpolation across the cell faces. The point surface altitudes are used to
extrude the mesh to reveal the surface topography. Also, Natural Earth
coastlines are rendered.

"""

import geovista as gv
from geovista.pantry import lfric_orog
import geovista.theme  # noqa: F401


def main() -> None:
    # load the sample data
    sample = lfric_orog()

    # create the mesh from the sample data
    mesh = gv.Transform.from_unstructured(
        sample.lons,
        sample.lats,
        connectivity=sample.connectivity,
        data=sample.data,
        name=sample.name,
    )

    # warp the mesh nodes by the surface altitude
    mesh.compute_normals(cell_normals=False, point_normals=True, inplace=True)
    mesh.warp_by_scalar(scalars=sample.name, inplace=True, factor=2e-5)

    # plot the mesh
    plotter = gv.GeoPlotter()
    sargs = dict(title=f"{sample.name} / {sample.units}", shadow=True)
    plotter.add_mesh(mesh, show_edges=True, scalar_bar_args=sargs)
    plotter.add_axes()
    plotter.add_text(
        "LFRic C48 Unstructured Cube-Sphere",
        position="upper_left",
        font_size=10,
        shadow=True,
    )
    plotter.show()


if __name__ == "__main__":
    main()
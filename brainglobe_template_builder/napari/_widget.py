"""
This module is an example of a barebones QWidget plugin for napari

It implements the Widget specification.
see: https://napari.org/stable/plugins/guides.html?#widgets

Replace code below according to your needs.
"""
from typing import Literal, Union

import numpy as np
from magicgui import magic_factory
from napari.layers import Image, Labels, Points
from napari.types import LayerDataTuple
from napari_plugin_engine import napari_hook_implementation

from brainglobe_template_builder.utils import (
    align_vectors,
    extract_largest_object,
    fit_plane_to_points,
    get_midline_points,
    threshold_image,
)

# 9 colors taken from ColorBrewer2.org Set3 palette
POINTS_COLOR_CYCLE = [
    "#8dd3c7",
    "#ffffb3",
    "#bebada",
    "#fb8072",
    "#80b1d3",
    "#fdb462",
    "#b3de69",
    "#fccde5",
    "#d9d9d9",
]


@magic_factory(
    call_button="generate mask",
    gauss_sigma={"widget_type": "SpinBox", "max": 20, "min": 0},
    threshold_method={"choices": ["triangle", "otsu", "isodata"]},
    erosion_size={"widget_type": "SpinBox", "max": 20, "min": 0},
)
def mask_widget(
    image: Image,
    gauss_sigma: float = 3,
    threshold_method: Literal["triangle", "otsu", "isodata"] = "triangle",
    erosion_size: int = 5,
) -> Union[LayerDataTuple, None]:
    """Threshold image and create a mask for the largest object.

    The mask is generated by applying a Gaussian filter to the image,
    thresholding the smoothed image, keeping only the largest object, and
    eroding the resulting mask.

    Parameters
    ----------
    image : Image
        A napari image layer to threshold.
    gauss_sigma : float
        Standard deviation for Gaussian kernel (in pixels) to smooth image
        before thresholding. Set to 0 to skip smoothing.
    threshold_method : str
        Thresholding method to use. One of 'triangle', 'otsu', and 'isodata'
        (corresponding to methods from the skimage.filters module).
        Defaults to 'triangle'.
    erosion_size : int
        Size of the erosion footprint (in pixels) to apply to the mask.
        Set to 0 to skip erosion.

    Returns
    -------
    napari.types.LayerDataTuple
        A napari Labels layer containing the mask.
    """

    if image is not None:
        assert isinstance(image, Image), "image must be a napari Image layer"
    else:
        print("Please select an image layer")
        return None

    from skimage import filters, morphology

    # Apply gaussian filter to image
    if gauss_sigma > 0:
        data_smoothed = filters.gaussian(image.data, sigma=gauss_sigma)
    else:
        data_smoothed = image.data

    # Threshold the (smoothed) image
    binary = threshold_image(data_smoothed, method=threshold_method)

    # Keep only the largest object in the binary image
    mask = extract_largest_object(binary)

    # Erode the mask
    if erosion_size > 0:
        mask = morphology.binary_erosion(
            mask, footprint=np.ones((erosion_size,) * image.ndim)
        )

    # return the mask as a napari Labels layer
    return (mask, {"name": "mask", "opacity": 0.5}, "labels")


@magic_factory(
    call_button="Estimate midline points",
)
def points_widget(
    mask: Labels,
) -> LayerDataTuple:
    """Create a points layer with 9 midline points.

    Parameters
    ----------
    mask : Labels
        A napari labels layer to use as a reference for the points.

    Returns
    -------
    napari.types.LayerDataTuple
        A napari Points layer containing the estimated midline points.
    """

    # Estimate 9 midline points
    points = get_midline_points(mask.data)

    point_labels = np.arange(1, points.shape[0] + 1)

    point_attrs = {
        "properties": {"label": point_labels},
        "face_color": "label",
        "face_color_cycle": POINTS_COLOR_CYCLE,
        "symbol": "cross",
        "edge_width": 0,
        "opacity": 0.6,
        "size": 6,
        "ndim": mask.ndim,
        "name": "midline points",
    }

    # Make mask layer invisible
    mask.visible = False

    return (points, point_attrs, "points")


@magic_factory(
    call_button="Align midline",
    image={"label": "Image"},
    points={"label": "Midline points"},
)
def align_widget(image: Image, points: Points) -> LayerDataTuple:
    """Align image to midline points.

    Parameters
    ----------
    image : Image
        A napari image layer to align.
    points : Points
        A napari points layer containing the midline points.

    Returns
    -------
    napari.types.LayerDataTuple
        A napari Image layer containing the aligned image.
    """

    from scipy.ndimage import affine_transform

    points_data = points.data
    centroid = np.mean(points_data, axis=0)
    normal_vector = fit_plane_to_points(points_data)

    # 1. Translate so centroid is at origin
    translate_to_origin = np.eye(4)
    translate_to_origin[:3, 3] = -centroid

    # 2. Rotate so normal vector aligns with x-axis
    x_axis = np.array([0, 0, 1])
    rotation_matrix = align_vectors(normal_vector, x_axis)
    rotation = np.eye(4)
    rotation[:3, :3] = rotation_matrix

    # 3. Translate so plane is at middle slice along x-axis
    translate_to_mid_x = np.eye(4)
    mid_x = image.data.shape[2] // 2
    translate_to_mid_x[2, 3] = mid_x - centroid[2]

    # Combine transformations
    transform = (
        np.linalg.inv(translate_to_origin)
        @ rotation
        @ translate_to_origin
        @ translate_to_mid_x
    )
    affine_matrix, offset = transform[:3, :3], transform[:3, 3]

    # Apply the transformation to the image
    transformed_image = affine_transform(
        image.data, affine_matrix, offset=offset
    )

    return (transformed_image, {"name": "aligned image"}, "image")


@napari_hook_implementation
def napari_experimental_provide_dock_widget():
    return [mask_widget, points_widget]

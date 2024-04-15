from pathlib import Path

import numpy as np
import pandas as pd
from brainglobe_utils import image_io as imio


def get_unique_folder_in_dir(search_dir: Path, search_str: str) -> Path:
    """
    Find a folder in a directory that contains a unique string.

    Parameters
    ----------
    search_dir : Path
        Directory to search in
    search_str : str
        String to search for in folder names

    Returns
    -------
    folder : Path
        Path to the folder that contains the search string
    """
    all_folders = [x for x in search_dir.iterdir() if x.is_dir()]
    folders_with_str = [x for x in all_folders if search_str in x.name]
    if len(folders_with_str) == 0:
        raise ValueError(f"No folders with {search_str} found")
    if len(folders_with_str) > 1:
        raise ValueError(f"Multiple folders with {search_str} found")
    return folders_with_str[0]


def load_image_to_napari(tiff_path: Path):
    """
    Load an image to napari

    Parameters
    ----------
    tiff_path : pathlib.Path
        path to the tiff image

    Returns
    -------
    image : np.ndarray
    """
    valid_extensions = [".tif", ".tiff"]
    if tiff_path.suffix not in valid_extensions:
        raise ValueError(
            f"File extension {tiff_path.suffix} is not valid. "
            f"Expected one of {valid_extensions}"
        )
    image = imio.load_any(tiff_path.as_posix())
    return image


def save_3d_points_to_csv(points: np.ndarray, file_path: Path):
    """
    Save 3D points to a csv file
    """

    if points.shape[1] != 3:
        raise ValueError(
            f"Points must be of shape (n, 3). Got shape {points.shape}"
        )
    if file_path.suffix != ".csv":
        raise ValueError(
            f"File extension {file_path.suffix} is not valid. "
            f"Expected file path to end in .csv"
        )

    points_df = pd.DataFrame(points, columns=["z", "y", "x"])
    points_df.to_csv(file_path, index=False)


def save_nii(stack: np.ndarray, pix_sizes: list, dest_path: Path):
    """
    Save 3D image stack to dest_path as a nifti image.

    Parameters
    ----------
    stack : np.ndarray
        3D image stack
    pix_sizes : list
        list of pixel dimensions in mm. The order is 'x', 'y', 'z'
    dest_path : pathlib.Path
        path to save the nifti image
    """
    transformation_matrix = _get_transf_matrix_from_res(pix_sizes)
    imio.to_nii(
        stack,
        dest_path.as_posix(),
        scale=pix_sizes,
        affine_transform=transformation_matrix,
    )


def _get_transf_matrix_from_res(pix_sizes: list) -> np.ndarray:
    """Create transformation matrix from a dictionary of pixel dimensions.

    Parameters
    ----------
    pix_sizes : list
        list of pixel dimensions in mm. The order is 'x', 'y', 'z'

    Returns
    -------
    np.ndarray
        A (4, 4) transformation matrix with the pixel dimensions
        on the first 3 diagonal entries.
    """
    transformation_matrix = np.eye(4)
    for i in range(3):
        transformation_matrix[i, i] = pix_sizes[i]
    return transformation_matrix


def tiff_to_nifti(tiff_path: Path, nifti_path: Path, pix_sizes: list):
    """
    Convert a tiff image to a nifti image

    Parameters
    ----------
    tiff_path : pathlib.Path
        path to the tiff image
    nifti_path : pathlib.Path
        path to save the nifti image
    pix_sizes : list
        list of pixel dimensions in mm. The order is 'x', 'y', 'z'
    """
    stack = imio.load_any(tiff_path.as_posix())
    save_nii(stack, pix_sizes, nifti_path)


def nifti_to_tiff(nifti_path: Path, tiff_path: Path):
    """
    Convert a nifti image to a tiff image

    Parameters
    ----------
    nifti_path : pathlib.Path
        path to the nifti image
    tiff_path : pathlib.Path
        path to save the tiff image
    """
    stack = imio.load_any(nifti_path.as_posix())
    imio.to_tiff(stack, tiff_path.as_posix())

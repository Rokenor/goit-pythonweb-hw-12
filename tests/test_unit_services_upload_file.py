"""Модульні тести завантаження аватарів — Cloudinary мокається повністю."""

from unittest.mock import MagicMock, patch

from src.services.upload_file import UploadFileService


def test_service_configures_cloudinary():
    with patch("src.services.upload_file.cloudinary.config") as config:
        UploadFileService("cloud", "key", "secret")

    config.assert_called_once_with(
        cloud_name="cloud", api_key="key", api_secret="secret", secure=True
    )


def test_upload_file_returns_resized_url():
    file = MagicMock()

    with (
        patch("src.services.upload_file.cloudinary.uploader.upload") as upload,
        patch("src.services.upload_file.cloudinary.CloudinaryImage") as image,
    ):
        upload.return_value = {"version": 42}
        image.return_value.build_url.return_value = "https://cloudinary/avatar.jpg"

        url = UploadFileService.upload_file(file, "deadpool")

    assert url == "https://cloudinary/avatar.jpg"
    upload.assert_called_once_with(
        file.file, public_id="ContactsApp/deadpool", overwrite=True
    )
    image.assert_called_once_with("ContactsApp/deadpool")
    image.return_value.build_url.assert_called_once_with(
        width=250, height=250, crop="fill", version=42
    )

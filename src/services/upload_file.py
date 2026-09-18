"""Завантаження аватарів у Cloudinary."""

import cloudinary
import cloudinary.uploader


class UploadFileService:
    """Обгортка над Cloudinary для зберігання аватарів користувачів."""

    def __init__(self, cloud_name: str, api_key: str, api_secret: str):
        """Налаштовує клієнт Cloudinary.

        :param cloud_name: назва хмари Cloudinary.
        :type cloud_name: str
        :param api_key: ключ доступу.
        :type api_key: str
        :param api_secret: секрет доступу.
        :type api_secret: str
        """
        self.cloud_name = cloud_name
        self.api_key = api_key
        self.api_secret = api_secret
        cloudinary.config(
            cloud_name=self.cloud_name,
            api_key=self.api_key,
            api_secret=self.api_secret,
            secure=True,
        )

    @staticmethod
    def upload_file(file, username: str) -> str:
        """Завантажує файл і повертає URL обрізаного зображення 250x250.

        Файл зберігається під сталим ``public_id``, тож новий аватар
        замінює попередній.

        :param file: завантажений файл (``UploadFile`` або схожий об'єкт).
        :param username: ім'я користувача, що входить у ``public_id``.
        :type username: str
        :return: URL зображення в Cloudinary.
        :rtype: str
        """
        public_id = f"ContactsApp/{username}"
        r = cloudinary.uploader.upload(file.file, public_id=public_id, overwrite=True)
        return cloudinary.CloudinaryImage(public_id).build_url(
            width=250, height=250, crop="fill", version=r.get("version")
        )

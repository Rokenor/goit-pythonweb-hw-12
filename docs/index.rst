.. Contacts API documentation master file

Документація Contacts API
=========================

REST API для зберігання та управління контактами: реєстрація й
аутентифікація за парою JWT-токенів, кешування поточного користувача
в Redis, ролі ``user`` / ``admin``, скидання пароля електронною поштою
та повний CRUD над контактами.

.. toctree::
   :maxdepth: 2
   :caption: Зміст:

   api
   repository
   services
   database
   conf


Головний модуль
===============

.. automodule:: main
   :members:
   :undoc-members:
   :show-inheritance:


Схеми даних
===========

.. automodule:: src.schemas
   :members:
   :undoc-members:
   :show-inheritance:


Покажчики
=========

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

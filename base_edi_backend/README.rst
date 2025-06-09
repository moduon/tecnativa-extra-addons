.. image:: https://img.shields.io/badge/license-AGPL--3-blue.svg
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

================
Base EDI Backend
================

Este módulo permite configurar exportaciones periódicas de datos de Odoo de
modo completamente configurable y permitiendo exportar periódicamente por ftp o por
correo electrónico.

Modo de empleo
==============

#. Ir a *Ajustes > Técnico > Edi Backend Configuration* creamos una configuración
   con un modelo y aplicamos distintas líneas de configuración.
#. Ir a *Ajustes > Técnico > Edi Backend* cramos una exportación y seleccionamos la
   configuración ya creada.
#. Una vez creado podemos ir al cron enlazado y configurarlo para que se ejecute cuando
   deseemos. (Podemos ejecutarlo manualmente para ver funcionamiento)
#. Nos dirigimos a la ficha de la exportación y en el 'SmartButton' History podremos
   encontrar todas las exportaciones que se han realizado.

Por hacer
=========

- Romper dependencias de l10n_aeat y publicar en OCA
- Tests
- Incluir importación por ftp

Credits
=======

Contributors
------------

* `Tecnativa <https://www.tecnativa.com>`_:

  * Sergio Teruel
  * David Vidal
  * Carlos Roca

Maintainer
----------

.. image:: https://www.tecnativa.com/logo.png
   :alt: Tecnativa
   :target: https://www.tecnativa.com

This module is maintained by Tecnativa.

Tecnativa is an IT consulting company specialized in Odoo and provides Odoo
development, installation, maintenance and hosting services.

To contribute to this module, please visit https://github.com/Tecnativa or
contact us at info@tecnativa.com.

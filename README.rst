============================
 LITESOPH
============================
Engines Interfaced with LITESOPH
============================
`GPAW <https://wiki.fysik.dtu.dk/gpaw/index.html>`_    (version 22.1.0 and less than 23.7.0)
  `Installation Instruction <https://wiki.fysik.dtu.dk/gpaw/install.html>`_ 

`Octopus <https://octopus-code.org/wiki/Main_Page>`_   (version 11.4)
  `Installation Instruction <https://octopus-code.org/wiki/Manual:Installation>`_

`NWChem <https://nwchemgit.github.io/>`_   (version 7.0.0 or later)
  `Installation Instruction <https://nwchemgit.github.io/Download.html>`_

Requirements
============

  * Python 3.7.6 or later
  * Tkinter
  * click
  * Numpy
  * Matplotlib
  * Paramiko
  * scp
  * Rsync

Installation
=============================================================================================================

.. code-block:: console

  $ git clone -b main https://github.com/LITESOPH/litesoph.git
  $ pip install <path-to-litesoph>


Configuration
=============================================================================================================
To create lsconfig file:
  .. code-block:: console

    $ litesoph config -c
  
To edit lsconfig file:
  .. code-block:: console

    $ litesoph config -e

Example lsconfig file
=========

.. code-block:: console

  [path]
  lsproject = <litesoph project path>
  lsroot = <installation path of litesoph>

 

Usage
===========================================================================================================

To start gui application, run:

.. code-block:: console

  $ litesoph gui



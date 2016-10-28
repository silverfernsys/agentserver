.. image:: https://img.shields.io/pypi/v/agentserver.svg
    :target: https://pypi.python.org/pypi/agentserver
.. image:: https://img.shields.io/pypi/l/agentserver.svg
    :target: https://pypi.python.org/pypi/agentserver

agentserver
===========

A server that allows you to control and monitor `supervisoragent <https://github.com/silverfernsys/supervisoragent>`_ instances.

**Commands**

.. code:: python

  agentserver
  agentserveradmin
  agentserverecho

**Note**
This project is under heavy development. It currently requires `Druid <http://druid.io/>`_, `PlyQL <https://github.com/implydata/plyql>`_, and `Kafka <https://kafka.apache.org/>`_ to run.

**TODOs**

- Druid and Kafka as optional dependencies.
- Documentation.
- A lot of the code relies heavily on integration tests for the HTTP and websocket APIs. Add unit tests.
- Expand code coverage. 
- User friendly way to create and initialize databases from ``agentserveradmin``.

Deploy the GUI in web mode
==========================

The :ref:`launching` section showed how you can launch the GUI on a local workstation.

To recap, you can launch the GUI in web mode by running:

.. code-block:: bash

   sigui --mode=web /path/for/my/sorting_analyzer

which will start a server on your localhost:

.. code-block:: bash

    Launching server at http://localhost:43957


However, the GUI can also be deployed on a remote server, and accessed through a web 
browser or directly in the cloud, thanks to its web mode.

Deploying on a remote lab server
--------------------------------

If you want to deploy the GUI on a remote lab server, the GUI can be used by multiple users
with VPN access to the server.

To setup the web GUI on a remote server, follow these steps:

1. Choose a server machine in your lab network (e.g. "my-lab-server") that is accessible
   through VPN by all lab members.

2. Install spikeinterface-gui and its dependencies on the server machine.

3. Launch the GUI launcher on the server machine with the following command:

.. code-block:: bash

   sigui --mode=web --address=auto-ip

If all your analyzers will be in the same root folder (or in subfolders), you can also specify the ``--root-folder`` option:

.. code-block:: bash

   sigui --mode=web --address=auto-ip --root-folder=/path/to/my/analyzers

4. The server will start and display the IP address to access the GUI launcher, e.g.:

.. code-block:: bash

    Launching server at http://SERVER.IP.ADDRESS:43957/launcher

5. Share the displayed IP address with all lab members, so they can connect to the GUI launcher
   from their local machines.


Deploying on cloud platforms
----------------------------

The ``spikeinterface-gui`` web mode can also be deployed on cloud platforms such as AWS, GCP, or Azure.

This type of deployment is recommended if all your raw and sorted data are already stored
in the cloud.

You will need a simple wrapper python script that ``Panel`` can serve.

For example, create a file named ``si_launcher.py`` with the following content:

.. code-block:: python

    from spikeinterface_gui.launcher import Launcher

    launcher = Launcher(backend="panel")
    launcher.layout.servable()

Then, you need a ``Dockerfile`` which installs the GUI and serves the panel app as entry point.
Here is a minimal example of a ``Dockerfile``:

.. code-block:: docker

    FROM python:3.9-slim

    RUN pip install spikeinterface-gui[web]

    COPY si_launcher.py /si_launcher.py

    EXPOSE 8000

    ENTRYPOINT ["sh", "-c", "panel serve /si_launcher.py --address 0.0.0.0 --port 8000 --allow-websocket-origin ${ALLOW_WEBSOCKET_ORIGIN} --keep-alive 10000 --warm"]


You can then build and run the Docker image on your cloud platform of choice, making sure to set the
``ALLOW_WEBSOCKET_ORIGIN`` environment variable to the domain name or IP address of your server.

Note that you can also customize the launcher script to pre-load specific sorting analyzers or set a root folder.
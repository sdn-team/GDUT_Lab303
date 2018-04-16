Assuming that this directory is put in ~/ryu/ryu/app/
After downloading this directory, type following
in your command line:
$ cd ~/ryu
$ PYTHONPATH=. ./bin/ryu run --observe-links \
    ryu/app/gui_topology/gui_topology.py


In another terminal run mininet:
$ sudo python net1.1.py


Access http://127.0.0.1:8080 with your web browser.
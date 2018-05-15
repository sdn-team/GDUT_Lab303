Assuming that this directory is put in ~/ryu/ryu/app/
After downloading this directory, type following
in your command line:
$ cd ~/ryu
$ PYTHONPATH=. ./bin/ryu run --observe-links \
    ryu/app/gui_topology/gui_topology.py


In another terminal run mininet:
$ sudo python 4.py


To calculate the current path from h1 to h4, you may need to use this rest command:
$ curl -X POST -d '{"nw_src":"10.0.1.1","nw_dst":"10.0.1.4"}' \
    https://localhost:8080/routing/path

Access http://127.0.0.1:8080 with your web browser.
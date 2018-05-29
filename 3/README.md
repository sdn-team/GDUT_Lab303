#  多控制器控制网络

我们使用了两个虚拟机来对网络进行控制，每一个虚拟机中运行了一个Ryu控制器。
在这种情况下，每个Ryu控制器只能知道自己范围内的网络拓扑，如果想要多控制器互相交互来得到全局拓扑，可以使用Zookeeper来得到。

# 如何使用多控制器控制网络
在第一个虚拟机中，运行第一个控制器，监听端口为6661
```bash
$ cd ~/ryu
$ PYTHONPATH=. ./bin/ryu run \
    --observe-links ryu/app/sdn_com/1/gui_topology/gui_topology.py \
    --ofp-listen-port=6661 
```

在另外一个虚拟机中，配置IP地址（此时应保证与第一个虚拟机在同一个子网中），然后运行第二个控制器，监听端口为6662
```bash
$ ifconfig eth0 192.168.75.147 netmask 255.255.255.0
$ cd ~/ryu
$ PYTHONPATH=. ./bin/ryu run \
    --observe-links ryu/app/sdn_com/1/gui_topology/gui_topology.py \
    --ofp-listen-port=6662
```

在第一个虚拟机中，运行mininet脚本创建网络拓扑
```bash
$ cd ~/ryu/ryu/app/sdn_com/net
$ sudo python 3.py
```

分别在两个虚拟机中使用浏览器登录地址127.0.0.1:8080可以查看各自的网络拓扑

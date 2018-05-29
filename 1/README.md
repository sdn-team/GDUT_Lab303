# 搭建基础网络

本控制器用于对基本网络进行控制（避免环路广播风暴），并通过gui视图得到当前网络拓扑结构

# 如何使用本控制器
打开一个ubuntu终端，运行控制器
```bash
$ cd ~/ryu
$ PYTHONPATH=. ./bin/ryu run \
    --observe-links ryu/app/sdn_com/1/gui_topology/gui_topology.py
```

再打开另外一个终端，运行mininet脚本创建网络拓扑
```bash
$ cd ~/ryu/ryu/app/sdn_com/net
$ sudo python 1.py
```

在浏览器中登录127.0.0.1:8080，可查看当前网络拓扑

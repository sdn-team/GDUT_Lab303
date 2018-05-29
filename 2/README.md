# 网络基础控制功能

本控制器用于对基本网络进行控制（禁止某个流的转发），并通过gui视图得到当前网络拓扑结构

# 如何使用本控制器
打开一个ubuntu终端，运行控制器
```bash
$ cd ~/ryu
$ PYTHONPATH=. ./bin/ryu run \
    --observe-links ryu/app/sdn_com/2/gui_topology/gui_topology.py
```

再打开另外一个终端，运行mininet脚本创建网络拓扑
```bash
$ cd ~/ryu/ryu/app/sdn_com/net
$ sudo python 2.py
```

此时在mininet CLI中pingall，主机应两两ping通
```bash
# pingall
```

再打开一个终端，使用REST命令将源地址为10.0.1.3（h3的地址）的流全部丢弃
```bash
$ curl -X POST -d \
    '{"nw_src":"10.0.1.3","actions":"DENY", "priority":"100"}' \
    http://localhost:8080/firewall/rules/0000000000000003
```

此时在mininet CLI中再次pingall，可以看到与h3相关全部ping不通，而其余的都可以。

在浏览器中登录127.0.0.1:8080，可查看当前网络拓扑

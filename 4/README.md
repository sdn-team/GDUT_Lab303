# 动态改变转发规则

本控制器用于动态地改变转发路径

# 如何使用本控制器
打开一个ubuntu终端
```bash
$ cd ~/ryu
$ PYTHONPATH=. ./bin/ryu run --observe-links ryu/app/sdn_com/4/gui_topology/gui_topology.py
```

再打开另外一个终端
```bash
$ cd ~/ryu/ryu/app/sdn_com/net
$ sudo python 4.py
```

如果您想要修改控制器参数（如动态转发路径的间隔时间，路径个数等等），可以在setting.py中修改

在miniet CLI中令h1不停地ping h4,此时可以看到，每隔30s（在setting.py中设置HARD_TIMEOUT），
ping所需要的时间骤然增加，这是因为流表已过期，交换机必须重新packet in给控制器查询流表。
此时控制器收到packet in消息后，动态地将路径改变，并下发流表给对应的交换机。

# 验证程序验证转发路径

以下 REST 命令可以得到 10.0.1.1 到 10.0.1.4 的路径
```bash
$ curl -X POST -d '{"nw_src":"10.0.1.1","nw_dst":"10.0.1.4"}' \
    https://localhost:8080/routing/path
```

或者您也可以在您的浏览器中访问127.0.0.1:8080，并在浏览器的验证程序中输入对应的IP地址。
此时可以看到对应的转发路径已经变成红色。

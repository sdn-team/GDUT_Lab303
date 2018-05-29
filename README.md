# 第五届全国高校SDN大赛

本目录文件用于第五届全国高校SDN大赛，其中文件夹1，2，3，4分别对应题目1，2，3，4。
文件夹net中存放了所有题目的mininet脚本文件，脚本1.py,2.py...分别对应题目1，2...。

为了使用本文档，请您将此目录放置在~/ryu/app/目录下，并以sdn_com命名。

为了使用浏览器查看网络的拓扑结构视图，您需要对ryu/base/app_manager.py做如下修改：
```bash
diff --git a/ryu/base/app_manager.py b/ryu/base/app_manager.py
index f684259..84d37d2 100644
--- a/ryu/base/app_manager.py
+++ b/ryu/base/app_manager.py
@@ -505,8 +505,18 @@ class AppManager(object):
         return app
 
     def instantiate_apps(self, *args, **kwargs):
+        # HACK: Because gui_topology will register itself to interrupt all
+        # REST calls, instantiate it later.
+        gui_cls = 'gui_topology'
+        for applications_cls in self.applications_cls.keys():
+            if applications_cls.find('gui_topology') != -1:
+                gui_cls = applications_cls
+                break
+        gui_topology = self.applications_cls.pop(gui_cls, None)
         for app_name, cls in self.applications_cls.items():
             self._instantiate(app_name, cls, *args, **kwargs)
+        if gui_topology:
+            self._instantiate(gui_cls, gui_topology, *args, **kwargs)
 
         self._update_bricks()
         self.report_bricks()
```
这是因为gui_topology.py会影响其他的rest命令，所以应该最后才对它进行实例化。
var CONF = {
    image: {
        width: 50,
        height: 40
    },
    force: {
        width: 960,
        height: 600,
        dist: 200,
        charge: -600
    }
};

var ws = new WebSocket("ws://" + location.host + "/v1.0/topology/ws");
ws.onmessage = function(event) {
    var data = JSON.parse(event.data);
    var result = rpc[data.method](data.params);
    var ret = {"id": data.id, "jsonrpc": "2.0", "result": result};
    this.send(JSON.stringify(ret));
}

function trim_zero(obj) {
    return String(obj).replace(/^0+/, "");
}

function dpid_to_int(dpid) {
    return Number("0x" + dpid);
}
//d3 make data visible
var elem = {  //the {} is used for defining a object,generally concludes attr and var, and function
    force: d3.layout.force()
        .size([CONF.force.width, CONF.force.height])
        .charge(CONF.force.charge)
        .linkDistance(CONF.force.dist)
        .on("tick", _tick), //refresh one frame by one frame
    svg: d3.select("body").append("svg")
        .attr("id", "topology")
        .attr("width", CONF.force.width)
        .attr("height", CONF.force.height),
    console: d3.select("body").append("div")
        .attr("id", "console")
        .attr("width", CONF.force.width)
};
function _tick() {
    elem.link.attr("x1", function(d) { return d.source.x; })
        .attr("y1", function(d) { return d.source.y; })
        .attr("x2", function(d) { return d.target.x; })
        .attr("y2", function(d) { return d.target.y; });

    elem.relaxlink.attr("x1", function(d) { return d.source.x; })
        .attr("y1", function(d) { return d.source.y; })
        .attr("x2", function(d) { return d.target.x; })
        .attr("y2", function(d) { return d.target.y; });

    elem.busylink.attr("x1", function(d) { return d.source.x; })
        .attr("y1", function(d) { return d.source.y; })
        .attr("x2", function(d) { return d.target.x; })
        .attr("y2", function(d) { return d.target.y; });

    elem.node.attr("transform", function(d) { return "translate(" + d.x + "," + d.y + ")"; });

    elem.hostNode.attr("transform", function(d) { return "translate(" + d.x + "," + d.y + ")"; });

    elem.port.attr("transform", function(d) {
        var p = topo.get_port_point(d);
        return "translate(" + p.x + "," + p.y + ")";
    });
}


elem.drag = elem.force.drag().on("dragstart", _dragstart);
function _dragstart(d) {
    if(!d.isHost){
        var dpid = dpid_to_int(d.dpid)
        elem.console.selectAll("ul").remove();
        d3.json("/stats/flow/" + dpid, function(e, data) {
            flows = data[dpid];
//            console.log(flows);
            li = elem.console.append("ul")
                .selectAll("li");
            li.data(flows).enter().append("li")
                .text(function (d) { return "Flow Information :"+JSON.stringify(d, null, " "); });
        });
        var myConsole = document.getElementById("console");
        var ul = document.createElement("ul");
        var li = document.createElement("li");
        li.innerHTML = "Switch Information : "+JSON.stringify(d, null, " ");
        myConsole.appendChild(ul);
        ul.appendChild(li);
     }else{
            // show the host info
            elem.console.selectAll("ul").remove();
            var myConsole = document.getElementById("console");
            var ul = document.createElement("ul");
            var li = document.createElement("li");
            li.innerHTML = "Host Information :"+JSON.stringify(d, null, " ");
            myConsole.appendChild(ul);
            ul.appendChild(li);
     }
      d3.select(this).classed("fixed", d.fixed = true);
}
elem.node = elem.svg.selectAll(".node");
elem.link = elem.svg.selectAll(".link");
elem.busylink = elem.svg.selectAll(".busylink");
elem.relaxlink = elem.svg.selectAll(".relaxlink");
elem.port = elem.svg.selectAll(".port");
elem.hostNode = elem.svg.selectAll(".hostNode")
elem.update = function () {
    this.force
        .nodes(topo.nodes)
        .links(topo.links)
        .start();

    this.link = this.link.data(topo.links);
    this.link.exit().remove();
    this.link.enter().append("line")
        .attr("class", "link");

    this.busylink = this.busylink.data(topo.busyLinks);
    this.busylink.exit().remove();
    this.busylink.enter().append("line")
        .attr("class", "busylink");

//    this.relaxlink = this.relaxlink.data(topo.relaxLinks);
//    this.relaxlink.exit().remove();
//    this.relaxlink.enter().append("line")
//        .attr("class", "relaxlink");


    this.node = this.node.data(topo.switchNodes);
    this.node.exit().remove();
    var nodeEnter = this.node.enter().append("g")
        .attr("class", "node")
        .on("dblclick", function(d) { d3.select(this).classed("fixed", d.fixed = false); })
        .call(this.drag);
    nodeEnter.append("image")
        .attr("xlink:href", "./router.svg")
        .attr("x", -CONF.image.width/2)
        .attr("y", -CONF.image.height/2)
        .attr("width", CONF.image.width)
        .attr("height", CONF.image.height);
    nodeEnter.append("text")
        .attr("dx", -CONF.image.width/2)
        .attr("dy", CONF.image.height-10)
        .text(function(d) { return "dpid: " + trim_zero(d.dpid); });

    this.hostNode = this.hostNode.data(topo.hostNodes);
    this.hostNode.exit().remove();
    var hostNodeEnter = this.hostNode.enter().append("g")
        .attr("class", "hostnode")
        .on("dblclick", function(d) { d3.select(this).classed("fixed", d.fixed = false); })
        .call(this.drag);
    hostNodeEnter.append("image")
        .attr("xlink:href", "./host.svg")
        .attr("x", -CONF.image.width/2)
        .attr("y", -CONF.image.height/2)
        .attr("width", CONF.image.width+5)
        .attr("height", CONF.image.height+5);
    hostNodeEnter.append("text")
        .attr("dx", -CONF.image.width/2+12)
        .attr("dy", CONF.image.height-10+2)
        .text("host");

    var ports = topo.get_ports();
    this.port.remove();
    this.port = this.svg.selectAll(".port").data(ports);
    var portEnter = this.port.enter().append("g")
        .attr("class", "port");
    portEnter.append("circle")
        .attr("r", 8);
    portEnter.append("text")
        .attr("dx", -3)
        .attr("dy", 3)
        .text(function(d) { return trim_zero(d.port_no); });
};

function is_valid_link(link) {
    return (link.src.dpid < link.dst.dpid)
}
function dpid_patch(num){
    //  from single num to 16 bit num ,like 1 to 0000000000000001
    var data = num + "";
    var str_length = data.length;
    for (var i = 0 ; i< 16-str_length;i++){
        data = "0"+data;
    }
    return data
}
function sleep(numberMillis) {
    var now = new Date();
    var exitTime = now.getTime() + numberMillis;
    while (true) {
        now = new Date();
        if (now.getTime() > exitTime)
        return;
        }
}
var topo = {
    switchNodes : [],
    hostNodes : [],
    nodes: [],
    busyLinks: [],
    relaxLinks : [],
    links: [],
    node_index: {}, // dpid -> index of nodes array
    hostNode_index: {},
    initialize: function (data) {
        this.add_nodes(data.switches,data.hostss);
        this.add_links(data.links);
        this.add_hostLinks();


        document.getElementById("com_btn").onclick=function(){
            var src_ip1 = document.getElementById("src_ip1").value;
            var src_ip2 = document.getElementById("src_ip2").value;
            var src_ip3 = document.getElementById("src_ip3").value;
            var src_ip4 = document.getElementById("src_ip4").value;
            var dst_ip1 = document.getElementById("dst_ip1").value;
            var dst_ip2 = document.getElementById("dst_ip2").value;
            var dst_ip3 = document.getElementById("dst_ip3").value;
            var dst_ip4 = document.getElementById("dst_ip4").value;
            if((src_ip1<=255 && src_ip1>=0) && (src_ip2<=255 && src_ip2>=0) && (src_ip3<=255 && src_ip3>=0) && (src_ip4<=255 && src_ip4>=0)
             && (dst_ip1<=255 && dst_ip1>=0) && (dst_ip2<=255 && dst_ip2>=0) && (dst_ip3<=255 && dst_ip1>=0) && (dst_ip4<=255 && dst_ip4>=0)){
                    var src_ip = src_ip1 +"."+ src_ip2 +"."+ src_ip3 +"."+ src_ip4;
                    var dst_ip = dst_ip1 +"."+ dst_ip2 +"."+ dst_ip3 +"."+ dst_ip4;
                    var json_url = "/routing/path";
                    d3.json(json_url,function (error,data){
                            topo.add_busyLinks(data,src_ip,dst_ip);
                    }).header("Content-Type","application/json").send("POST", JSON.stringify({nw_src: src_ip, nw_dst: dst_ip}));
             }else{
                alert("the input address is invalid");
             }

        };
//    some testing commands
//        alert(data.switches);
//        alert(data.links);
//        alert(data.hosts);
    },
    add_nodes: function (nodes,hosts) {
        var node_id = 0;
        for (var i = 0; i < nodes.length; i++) {
            nodes[i].isHost=false;
            nodes[i].node_id = node_id;
            node_id++;
            this.nodes.push(nodes[i]);
            //console.log("add switch: " + JSON.stringify(nodes[i]));
        }
        for (var i = 0; i < hosts.length; i++) {
            hosts[i].isHost=true;
            hosts[i].node_id = node_id;
            node_id++;
            this.nodes.push(hosts[i]);
           // console.log("add host: " + JSON.stringify(hosts[i]));
        }
        this.refresh_node_index();
    },
    add_links: function (links) {
        for (var i = 0; i < links.length; i++) {
            if (!is_valid_link(links[i])) continue;
            //console.log("add link: " + JSON.stringify(links[i]));

            var src_dpid = links[i].src.dpid;
            var dst_dpid = links[i].dst.dpid;
            var src_index = this.node_index[src_dpid];
            var dst_index = this.node_index[dst_dpid];
            var link = {
                source: src_index,
                target: dst_index,
                port: {
                    src: links[i].src,
                    dst: links[i].dst
                }
            }
            this.links.push(link);
        }
    },
    add_busyLinks :function (data,src_ip ,dst_ip){
        var src_host_mac , dst_host_mac;
        for (var i = 1; i < this.hostNodes.length; i++ ){
            if (this.hostNodes[i].ipv4[0] == src_ip){
                src_host_mac = this.hostNodes[i].mac;
            }
            if (this.hostNodes[i].ipv4[0] == dst_ip){
                dst_host_mac = this.hostNodes[i].mac;
            }
        }
        // clear the isBusy flag
        for (var i =0; i < this.links.length; i++){
            this.links[i].isBusy = false;
        }
        this.busyLinks.splice(0,this.busyLinks.length);
        this.relaxLinks.splice(0,this.relaxLinks.length);

        // get the busy link between switches
        var busy_link_src, busy_link_dst;
        for(var i =1 ;i <data.length ;i++){
            busy_link_src = dpid_patch(data[i-1]);
            busy_link_dst = dpid_patch(data[i]);
            console.log(busy_link_src,busy_link_dst);
            for (var j =0; j < this.links.length; j++){
                if (this.links[j].target.isHost == false){
                    if(busy_link_src == this.links[j].source.dpid && busy_link_dst == this.links[j].target.dpid){
                                this.links[j].isBusy = true;
                    }
                }
            }
        }
        // get the buys link between host and switch
        for (var j =0; j < this.links.length; j++){
                if (this.links[j].target.isHost == true){
                    if(src_host_mac == this.links[j].target.mac || dst_host_mac == this.links[j].target.mac){
                            this.links[j].isBusy = true;
                    }else{
                            this.links[j].isBusy = false;
                    }
                }
        }
        for (var i = 0 ;i<this.links.length;i++){
            if (this.links[i].isBusy == true){
                this.busyLinks.push(this.links[i]);
            }
            else{
                this.relaxLinks.push(this.links[i]);
            }
        }
        elem.update();
//        console.log(this.links);
//        console.log(this.busyLinks,this.relaxLinks);
    },
    add_hostLinks : function (){
        for (var i = 0; i < this.nodes.length; i++){
            if (this.nodes[i].isHost) {
                this.hostNodes.push(this.nodes[i]);
            }else{
                this.switchNodes.push(this.nodes[i]);
            }
        }
        for (var i =0 ;i < this.hostNodes.length; i++){
            var src_index = this.hostNodes[i].node_id;
            var dst_index = 0;
            var switchFlag = 0;
            var portFlag = 0;
            for (switchFlag; switchFlag< this.switchNodes.length; switchFlag++){
                if(this.hostNodes[i].port.dpid == this.switchNodes[switchFlag].dpid){
                    dst_index = this.switchNodes[switchFlag].node_id;
                    for ( portFlag;portFlag< this.switchNodes[switchFlag].ports.length;portFlag++){
                        if(this.hostNodes[i].port.name == this.switchNodes[switchFlag].ports[portFlag].name )
                            break;
                    }
                    break;
                }
            }
            var link = {
                source : dst_index,
                target : src_index,
                port: {
                    src: this.switchNodes[switchFlag].ports[portFlag],
                    dst: this.hostNodes[i].port
                }
            }
            this.links.push(link);
        }
    },
    delete_nodes: function (nodes) {
        for (var i = 0; i < nodes.length; i++) {
            console.log("delete switch: " + JSON.stringify(nodes[i]));

            node_index = this.get_node_index(nodes[i]);
            this.nodes.splice(node_index, 1);
        }
        this.refresh_node_index();
    },
    delete_links: function (links) {
        for (var i = 0; i < links.length; i++) {
            if (!is_valid_link(links[i])) continue;
            console.log("delete link: " + JSON.stringify(links[i]));

            link_index = this.get_link_index(links[i]);
            this.links.splice(link_index, 1);
        }
    },
    get_node_index: function (node) {
        for (var i = 0; i < this.nodes.length; i++) {
            if (node.dpid == this.nodes[i].dpid) {
                return i;
            }
        }
        return null;
    },
    get_link_index: function (link) {
        for (var i = 0; i < this.links.length; i++) {
            if (link.src.dpid == this.links[i].port.src.dpid &&
                    link.src.port_no == this.links[i].port.src.port_no &&
                    link.dst.dpid == this.links[i].port.dst.dpid &&
                    link.dst.port_no == this.links[i].port.dst.port_no) {
                return i;
            }
        }
        return null;
    },
    get_ports: function () {
        var ports = [];
        var pushed = {};
        for (var i = 0; i < this.links.length; i++) {
            function _push(p, dir) {
                key = p.dpid + ":" + p.port_no;
                if (key in pushed) {
                    return 0;
                }

                pushed[key] = true;
                p.link_idx = i;
                p.link_dir = dir;
                return ports.push(p);
            }
            _push(this.links[i].port.src, "source");
            _push(this.links[i].port.dst, "target");
        }

        return ports;
    },
    get_port_point: function (d) {
        var weight = 0.88; //decide where the circle locates,such the middle if the weight is equal to 0.5

        var link = this.links[d.link_idx];

        var x1 = link.source.x;
        var y1 = link.source.y;
        var x2 = link.target.x;
        var y2 = link.target.y;
        if (d.link_dir == "target") weight = 1.0 - weight;  // if the port is the target port ,to draw the circle near the target port,the weight should be changed
        var x = x1 * weight + x2 * (1.0 - weight);
        var y = y1 * weight + y2 * (1.0 - weight);

        return {x: x, y: y};
    },
    refresh_node_index: function(){
        this.node_index = {};
        for (var i = 0; i < this.nodes.length; i++) {
            this.node_index[this.nodes[i].dpid] = i;
        }
    },
// some testing command
//        for (var i = 0; i < this.nodes.length; i++) {
//               console.log(i+" : "+this.node_index[i]);
//        }
//    },
}

var rpc = {
    event_switch_enter: function (params) {
        var switches = [];
        for(var i=0; i < params.length; i++){
            switches.push({"dpid":params[i].dpid,"ports":params[i].ports});
        }
        topo.add_nodes(switches);
        elem.update();
        return "";
    },
    event_switch_leave: function (params) {
        var switches = [];
        for(var i=0; i < params.length; i++){
            switches.push({"dpid":params[i].dpid,"ports":params[i].ports});
        }
        topo.delete_nodes(switches);
        elem.update();
        return "";
    },
    event_link_add: function (links) {
        topo.add_links(links);
        elem.update();
        return "";
    },
    event_link_delete: function (links) {
        topo.delete_links(links);
        elem.update();
        return "";
    },
}

function initialize_topology() {
    d3.json("/v1.0/topology/switches", function(error, switches) {
        d3.json("/v1.0/topology/links", function(error, links) {
            d3.json("v1.0/topology/hosts", function(error, hosts) {
                topo.initialize({switches: switches, links: links, hostss: hosts});  //self-added hosts:host   test-result:response normally
                elem.update();
            });
        });
    });

}

function main() {
    initialize_topology();
}

main();

  for i in $(seq 1 2);
        do
	let port=i+6660
        xterm -title "app$i" -hold -e ryu-manager ryu.app.simple_switch_13 --ofp-tcp-listen-port=$port &
        done

$fn=100;

in=25.4;
tube_d=33.5;

bottom_w=6*in;

// base height = 2 * 1/2 in acrylic sheet + fan (32mm tall) 

echo((7.5*in-in-32)/in);

fan_x=92;
fan_bolt_d=4.5;
fan_bolt_edge=2.5+fan_bolt_d/2;

bolt=1/4*in+.2;

module top_plate(){
    difference(){
        
        square(bottom_w+in/2,center=true);
        
        for(i=[0:1]){
            translate([(-1)^i*(bottom_w/2-in/2),0])
            circle(d=bolt);
        }
        for(i=[0:1]){
            translate([0,(-1)^i*(bottom_w/2-in/2)])
            circle(d=bolt);
        }
        
    }
}

top_plate();
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



module spacer(){
    difference(){
    square([fan_x*1.5,in],center=true);
    
    for(i=[0:1]){
            translate([(bottom_w/4-bottom_w/2*i),0])
            circle(d=bolt);
        }
    }
}

spacer();
$fn=100;

in=25.4;
tube_d=33.5;

bottom_w=135;
long=7*in;



// base height = 2 * 1/2 in acrylic sheet + fan (32mm tall) 

echo((7.5*in-in-32)/in);

fan_x=92;
fan_bolt_d=4.5;
fan_bolt_edge=2.5+fan_bolt_d/2;

bolt=1/4*in+.2;

for(i=[0:7])
    translate([i*10,0,0])
    difference(){
    square(8,center=true);
        circle(d=fan_bolt_d);
    }
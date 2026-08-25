$fn=100;

in=25.4;
tube_d=33.5;

bottom_w=6*in;
long=7*in;
mod=1.25*in+3;


// base height = 2 * 1/2 in acrylic sheet + fan (32mm tall) 
/*
tube is at 4 inch high

first box + spacer
1in out of acrylic + 32mm fan height


*/
shift_from_bot=4*in-1*in-32;
echo(shift_from_bot);
tube_ID=33.5;

fan_x=92;
fan_bolt_d=4.5;
fan_bolt_edge=2.5+fan_bolt_d/2;

bolt=1/4*in+.2;

module long_side_tube(){
    difference(){
    square([long,bottom_w],center=true);
        
            translate([0,(bottom_w/2+in/2-mod)])
            circle(d=bolt);
        
        for(i=[0:1]){
            translate([(bottom_w/4-bottom_w/2*i),-(bottom_w/2-mod)])
            circle(d=bolt);
        }
     translate([0,-bottom_w/2+shift_from_bot+tube_ID/2])
        circle(tube_ID);
    }
}

long_side_tube();
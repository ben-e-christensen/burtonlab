use <starch_box_bottom_plate.scad>
use <starch_box_top_plate.scad>
use <starch_box_side_plate.scad>
use <starch_box_long_side.scad>
use <starch_box_spacer.scad>
use <starch_box_side_plate_tube.scad>

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
all=false;
if(all){
bottom_plate();

for(i=[0:1]){
    translate([(bottom_w)*(i+1)+(i+1)*5+in/2*(i+1)+10*i,0])
    if(i==0) {
    long_side();
    } else {
        long_side_tube();
    }
}

translate([in/4,-bottom_w-in/4-5])
top_plate();

for(i=[0:1]){
    translate([(bottom_w)*(i+1)+(i+1)*5+in/4+5,-bottom_w-in/4-5])
    side_plate();
}

translate([bottom_w*3,0,0])
rotate([0,0,90])
spacer();
translate([bottom_w*3,-bottom_w-10,0])
rotate([0,0,90])
spacer();
translate([12*in-bottom_w/2,-bottom_w*2+55,0])
square([24*in-1,.1],center=true);
} 
// ELSE!!!!!!!!!!!!!!
else {
    bottom_plate(1.5);
    translate([(7*in + 5),0])
    
    long_side(1.5);
    
}
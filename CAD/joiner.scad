$fn=100;
in=25.4;
x=in;
y=4*in;
bolt=1/4*in+.4;

module join(){
difference() {
    square([x,y],center=true);
    for(i=[0:3]) {
        translate([0,y/2-in/2-in*i])
        circle(d=bolt);
    }
}}
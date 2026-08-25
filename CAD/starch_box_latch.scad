$fn=100;

in=25.4;
x=20;

z=3;
bolt=1/4*in+.2;

mod=1.25*in;

module latch(y=in){
    difference(){
        cube([x,y,z],center=true);
        
        translate([0,y/2-in/2,-z])
        cylinder(100,d=bolt);
    }
}

latch();

rotate([90,0,0])
translate([0,mod/2+z/2,in/2-z/2])
latch(mod);

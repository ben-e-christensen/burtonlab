$fn=100;

z=5;
in=25.4;
bolt=in/4+.4;
bnc_w=14.75;
bnc_h=15.75;
bnc_port=12;

module slat(){
    difference(){
        cube([in,in,z],center=true);
        translate([0,0,-z])
        cylinder(100,d=bolt);
    }
}



module bnc() {
    difference(){
    cube([bnc_w+z,in,bnc_h+z/2],center=true);
    translate([0,z,-z/4-.01]){
    cube([bnc_w,in,bnc_h],center=true);
        rotate([90,0,0])
    cylinder(100,d=bnc_port);
    }
        
    }
}
for(i=[0:1]){
translate([(-1)^i*((bnc_w+z)/2+in/2),0,-(bnc_h-z/2)/2])
slat();
}
bnc();
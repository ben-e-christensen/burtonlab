$fn=100;

in=25.4;
OD=6*in;

thickness=15;
h=3*in;
bracket_z=5;

block=in*3;
bolt=in/4+.2;

module ring() {
    difference(){
        union(){
            
            cylinder(h,d=OD+thickness);
            
        }
        translate([0,0,-h])
        cylinder(h*3,d=OD);
    }
}


module cantilever() {
    difference(){
    cylinder(10,d=OD+thickness);
    translate([0,0,-h])
     cylinder(h*3,d=OD);
        
        translate([0,-150,-1])
        cube([300,300,100]);
    }
    
    translate([-in/2,-OD/2-block/2,5]) {
    cube([in,block,10],center=true);
    translate([0,-1.5*in,in-2.5])
        difference() {
        cube([in,5,in*2+5],center=true);
            
            
            for(i=[0:1]){
            rotate([90,0,0])
            translate([0,(in*2+5)/2-in/2-i*in,-5])
            cylinder(100,d=bolt);
            }
        }
        }
     translate([-5,OD/2+(block/2)/3,5]) {
         difference(){
    cube([10,block/3,10],center=true);
             rotate([0,90,0])
             translate([0,4,-10])
             cylinder(100,d=bolt);
         }
     } 
}

cantilever();
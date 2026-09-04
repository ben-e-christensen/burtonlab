$fn=100;

h=25.5;
w=28.5;
m3=2.2;
z=6;

actual_h=32;

box_w=16;
wire_box_w=5;
circle_d=8;

circle_h=8.75;

in=25.4;
bolt=in/4+.4;


module plate() {
    difference(){
        cube([in*2,actual_h,z],center=true);
        for(i=[0:1]){
        translate([(-1)^i*(-box_w/2-circle_d/2+.75),(-1)^i*(h/2-circle_h/2),-z*2])
        cylinder(100,m3,m3);
    }
    
    for(i=[0:1]){
        translate([(-1)^i*(box_w/2+wire_box_w/2),0,-z/2])
        cube([wire_box_w,10,z*3],center=true);
        translate([-20*(-1)^i,0,0])
        cube([20,3,20],center=true);
    }
}

translate([0,actual_h/2+z/2,in])
difference(){
    cube([in*2,z,in*2+z],center=true);
    
    translate([0,-z,0])
    rotate([90,0,0])

    for(i=[0:1]){
        for(j=[0:1]){
            translate([(-1)^i*(in/2),((in*2+z)/2-in/2-(in*j)),-50])
            cylinder(50,d=bolt);
        }
    }
    
}

}

plate();
$fn=100;


IR=51.5/2;
OR=IR+6;
h=15;
x=8;
y=18;
in=25.4;
sq_x=100;
sq_y=OR*2+25;
sq_h=6;

bolt=in/4+.2;

module hole() {
    difference(){
        union(){
            cylinder(h,OR,OR);
            translate([0,0,-sq_h/2+.1])
            
            cube([sq_x,sq_y,sq_h],center=true);
            }
        translate([0,0,-h])
        cylinder(h*3,IR,IR);
        
            for(i=[0:1]){
                translate([sq_x/2 - 15, (-1)^i*(sq_y/2 - 15),-h])
                cylinder(100,d=bolt);
            }
    translate([-50,0,0])
    cube([sq_x,sq_y+2,100],center=true);
    }
    translate([x/2,OR+y/4,h/2])
    difference(){
    cube([x,y,h],center=true);
        
        rotate([0,90,0])
        translate([0,2,-h])
        cylinder(100,d=bolt);
    }
    
    translate([x/2,-OR-y/4,h/2])
    difference(){
    cube([x,y,h],center=true);
        
        rotate([0,90,0])
        translate([0,-2,-h])
        cylinder(100,d=bolt);
    }
    
    
}

hole();
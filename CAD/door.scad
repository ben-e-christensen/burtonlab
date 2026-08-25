$fn=100;

in=25.4;
x=9.5*in;
y=8*in;

bolt=in*1/4+.2;

hinge_x=26.5;
hinge_y=76.5;
hinge_d=7;
bolt_dist_x=4.3+bolt/2;
bolt_dist_y_top=7.2+bolt/2;
bolt_dist_y_bottom=6.6+bolt/2;

cutout=2.25*in+1;

offset=5;
offset_mid=-3;

module hinge_holes() {
    translate([0,hinge_y/2-bolt_dist_y_top])
    circle(d=bolt);
    translate([0,-hinge_y/2+bolt_dist_y_bottom])
    circle(d=bolt);
}

module plate(){
    difference(){
        square([x,y],center=true);
        translate([-x/2+hinge_x-bolt_dist_x,0])
        hinge_holes();
        translate([x/2-(x-y+1/4*in)/2+.1,y/2-cutout/2+.01])
        square([x-y+1/4*in,cutout],center=true);
        
        translate([0,-y/2+1/8*in-.01])
        square([x+1,1/4*in],center=true);
        
    }
}

plate();

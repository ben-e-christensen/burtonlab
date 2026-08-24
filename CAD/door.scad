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

cutout=2*in+1;

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
        translate([x/2-(x-y)/2+.1,y/2-cutout/2+.01])
        square([x-y,cutout],center=true);
        
    }
}



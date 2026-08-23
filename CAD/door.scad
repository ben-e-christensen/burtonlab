$fn=100;

in=25.4;
x=9*in;
y=8*in;

bolt=in*1/4;

hinge_x=30;
hinge_y=70;

offset=5;
offset_mid=-3;


module plate(){
    difference(){
        square([x,y],center=true);
    }
}

module hinge(just_bolts=false){
    if(just_bolts){
        for(i=[0:2]){
            if(i==1){
                translate([offset_mid,hinge_y/3-hinge_y/3*i])
                circle(d=bolt);
        } else {
            translate([0,hinge_y/3-hinge_y/3*i])
            circle(d=bolt);
        }
    }} else {
    difference(){
        square([hinge_x,hinge_y],center=true);
        translate([offset,0])
        for(i=[0:2]){
            if(i==1){
                translate([offset_mid,hinge_y/3-hinge_y/3*i])
                circle(d=bolt);
        } else {
            translate([0,hinge_y/3-hinge_y/3*i])
            circle(d=bolt);
        }
    }
    }
    }
}

plate();
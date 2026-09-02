$fn=100;

in=25.4;

cam_x=40;
cam_y=50;
bolt_shift1=20;
bolt_shift2=30;
bolt=in/4+.4;

l=2*in;
w=4*in;

// actual cam + lens = 137
echo(137+in/2);

module cam_bracket(){
    difference(){
        square([cam_x,cam_y],center=true);

        circle(d=bolt);
    }
}

module cam_slat(){
    difference(){
        square([w,l],center=true);
        circle(d=bolt);
        for(i=[0:1]){
            for(j=[0:1]){
            translate([(-1)^i*(w/2-in/2),(-1)^j*(l/2-in/2)])
                circle(d=bolt);
            }
        }
    }
}

cam_slat();
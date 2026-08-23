$fn=100;

in=25.4;

distance=4*in;
bolt=1/4*in;
depth=50;

// ????????????????????????????
bracket=in/2;

module plate(){
    difference(){
        square([distance,depth],center=true);
        
        
        for(i=[0:1]){
            translate([(-1)^i*(distance/2-bracket),depth/2-bracket])
            circle(d=bolt);
        }
        circle(d=bolt);
    }
}

plate();
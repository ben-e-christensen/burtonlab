$fn=100;

in=25.4;

distance=10*in;
bolt=1/4*in+.4;
// slot for webcam to slide through
slot_width=40;
slot_height=8;
depth=slot_width+in*3.5;

post_sq=in+1.5;


// ????????????????????????????
bracket=in/2;

module post() {
    square(post_sq,center=true);
    
    for(i=[0:4]){
        translate([0,in*2 - i*in])
        circle(d=bolt);
        
    }
}

module plate(){
    difference(){
        square([distance,depth],center=true);
        for(i=[0:1]){
            translate([(-1)^i*(distance/2-post_sq/2+.1),0])
            post();
        }
        
        square([slot_height,slot_width],center=true);
        
        
    }
}

module holes(){
    for(i=[0:1]){
            translate([(-1)^i*(distance/2-bracket),depth/2-bracket])
            circle(d=bolt);
        }
        circle(d=bolt);
    }

plate();
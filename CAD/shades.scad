$fn=100;

in=25.4;

l=9*in;
w=3*in;

bolt=in/4+.4;

slot=in/2;

module ceiling(left=true){
    difference(){
    square([l,w],center=true);
    
    for(i=[0:1]){
        translate([-l/2+in/2,(-1)^i*in])
        circle(d=bolt);
    }
    if(left){
    translate([-l/2+in,-w/2+in/8-.01])
    for(i=[0:7]){
        translate([slot*(i*2)+slot/2,0])
        square([slot,in/4],center=true);
    } }
    
    else {
      translate([-l/2+in,w/2-in/8+.01])
    for(i=[0:7]){
        translate([slot*(i*2)+slot/2,0])
        square([slot,in/4],center=true);
    }  
    }
    translate([l/2-in/8+.01,w/2+.01])
    for(i=[0:2]){
        translate([0,-(slot*(i*2)+slot/2)])
        square([in/4,slot],center=true);
    }

    
}
}



module wall(left=true){
       difference(){
    square([l-in,w],center=true);
    
    if(left){
    translate([-l/2+in,-w/2+in/8-.01])
    for(i=[0:7]){
        translate([slot*(i*2)+slot/2,0])
        square([slot,in/4],center=true);
    } }
    
    else {
      translate([-l/2+in,w/2-in/8+.01])
    for(i=[0:7]){
        translate([slot*(i*2)+slot/2,0])
        square([slot,in/4],center=true);
    }  
    }
    translate([4*in-in/8+.01,w/2+.01])
    for(i=[0:2]){
        translate([0,-(slot*(i*2)+slot/2)])
        square([in/4,slot],center=true);
    }
} 
}

module endcap(){
    difference(){
        square(w,center=true);
        translate([-(1.5*in-in/8+.01),w/2+.01-slot])
    for(i=[0:2]){
        translate([0,-(slot*(i*2)+slot/2)])
        square([in/4,slot],center=true);
    }
    translate([-l/2+in+slot,-w/2+in/8-.01])
    for(i=[0:7]){
        translate([slot*(i*2)+slot/2,0])
        square([slot,in/4],center=true);
    }
    
    
    }
}


visual=false;

if(visual){
 ceiling();
translate([in/2,-1.5*in+in/4,-1.5*in+in/4])
rotate([90,0,0])
wall(false);   
    
    translate([4.5*in-in/4+5,0,-1.5*in+in/4])
    rotate([0,90,0])
    endcap();
} else{

ceiling();
translate([in/2,-3*in,0])
wall(false);

translate([0,3.2*in,0]){
ceiling(false);
    
translate([in/2,3*in,0])
    //rotate([0,0,180])
wall();
    
    translate([6*in,0,0])
    for(i=[0:1]){
        translate([0,-i*3*in-i*5,0])
        endcap();
    }
}}



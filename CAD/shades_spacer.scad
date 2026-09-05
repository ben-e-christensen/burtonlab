$fn=100;

in=25.4;

l=9*in;
w=3*in;

bolt=in/4+.4;

slot=in/2;

module ceiling(left=true){
    difference(){
    square([in,w],center=true);
    
    for(i=[0:1]){
        translate([0,(-1)^i*in])
        circle(d=bolt);
    }


    
}
}
rotate([0,0,90]){
translate([0,w+5,0])
ceiling();
ceiling();}
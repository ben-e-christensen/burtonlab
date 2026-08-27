$fn=100;
in=25.4;
w=3*in;
bolt=in/4+.2;

module side(){
    difference(){
        square([w,in],center=true);
        for(i=[0:2]){
            translate([-in+in*i,0,0])
            circle(d=bolt);
        }
    }
}
rotate([0,0,90])
translate([-w/2+in/2,-w/2+in/2])
side();

side();
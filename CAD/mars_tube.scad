$fn=100;

in=25.4;
thickness=20;
OD=7.75*in;
OOD=OD+15;

to_bar=(4.5*in)-OD/2;
echo(to_bar);


h=17.5;


block=in*3;
bolt=in/4+.2;

module post_tie(){
        difference(){
    hull(){

        translate([-in,-OOD/2-to_bar/2+4,h/2])
            cube([in,to_bar+8,h],center=true);
        translate([-in*2,-OOD/2+12.5,h/2])
            cube([5,5,h],center=true);
        translate([-in,-OOD/2-to_bar/2+4,h/2])
            translate([in/2-5,-(to_bar+8+2*in)/2,0])
                cube([10,2*in,h],center=true);
    }
    
    // bolt holes
    for(i=[0:1]){
        translate([-in,-OOD/2-to_bar/2+4,h/2])
            translate([in/2-5,-(to_bar+8+2*in)/2,0])
                rotate([0,90,0]){
                    translate([0,in/2-i*in,-h])
                        cylinder(100,d=bolt);
                    translate([0,in/2-i*in,-27+5*i])
                    cylinder(15,d=bolt+5);
                }

                        
    }
}
}



module cantilever(extra=true) {
    
    
    difference(){
        
    cylinder(h,d=OD+thickness);

        cube([in,1000,h*3],center=true);
    translate([0,0,-h])
     cylinder(h*3,d=OD);
        
        translate([0,-150,-1])
        cube([300,300,100]);
    }
    for(i=[0:1]){
        rotate([180*i,0,0])
        translate([0,0,-h*2*i])

    for(j=[0:1]){
        if(extra) {
    translate([0,0,h*j])
            post_tie();
        }
        else {
            post_tie();
        }
        
            

}
}   
        

}

difference(){

    
cantilever(false);
    translate([0,OOD+OOD/2.5,0])
cube([OOD*2,OOD*2,OOD*2],center=true);
    
}


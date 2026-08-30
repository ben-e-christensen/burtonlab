$fn=100;
in=25.4;
w=3*in;
bolt=in/4+.2;
gap=5;                  // clearance between parts

module side(){
    difference(){
        square([w,in],center=true);
        for(i=[0:2])
            translate([-in+in*i,0,0])
            circle(d=bolt);
    }
}

module l(){
    rotate([0,0,90])
    translate([-w/2+in/2,-w/2+in/2])
    side();
    side();
}

// l() with its bounding box corner at the origin (box is w x w)
module lb(){ translate([w/2, w-in/2]) l(); }

// two nested L's -> w x (w+in+gap)
module pair(){
    translate([w,w]) rotate(180) lb();   // corner at bottom-left
    translate([0, in+gap]) lb();         // corner at top-right, bumped up for clearance
}

module nest(){
    pair();
    translate([w+gap,0]) pair();
}

nest();

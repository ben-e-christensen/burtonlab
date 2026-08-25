$fn=100;

in=8;
rad=1/8*in;

wire_s=in*3-rad;
wire_l=in*7;

module tube() {
    difference(){
        cylinder(6*in,in,in);
        translate([0,0,-3])
        cylinder(7*in,4/5*in,4/5*in);
    }
}

module just_ball(){
    translate([0,0,rad])
    sphere(rad);
}

module midway(){
    cylinder(wire_s,in/25,in/25);
    translate([0,0,wire_s+rad])
    sphere(rad);
}

module just_wire(){
    cylinder(wire_l,in/25,in/25);
    translate([0,0,wire_l+rad])
    sphere(rad);
}

tube();
just_wire();
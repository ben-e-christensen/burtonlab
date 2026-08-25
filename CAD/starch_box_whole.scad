$fn=100;

in=25.4;
tube_d=33.5;

bottom_w=6*in;

// base height = 2 * 1/2 in acrylic sheet + fan (32mm tall) 

echo((7.5*in-in-32)/in);

fan_x=92;
fan_bolt_d=4.5;
fan_bolt_edge=2.5+fan_bolt_d/2;

bolt=1/4*in+.2;

/*
    TO DO
    
    bottom spacers
    top plate
    side plates
    side plate with tube hole
*/

module bottom_plate(pock_r=1){
    difference(){
        
        square(bottom_w,center=true);
        
        for(i=[0:1]){
            for(j=[0:1]){
            translate([(-1)^i*(fan_x/2-fan_bolt_edge),(-1)^j*(fan_x/2-fan_bolt_edge)])
            circle(d=fan_bolt_edge);
            }}
            
        for(i=[0:1]){
            translate([(bottom_w/2-in/2),(bottom_w/4-bottom_w/2*i)])
            circle(d=bolt);
        }
        
        for(i=[0:1]){
            translate([-(bottom_w/2-in/2),(bottom_w/4-bottom_w/2*i)])
            circle(d=bolt);
        }
        
        for(i=[0:1]){
            translate([(bottom_w/4-bottom_w/2*i),(bottom_w/2-in/2)])
            circle(d=bolt);
        }
        
        for(i=[0:1]){
            translate([(bottom_w/4-bottom_w/2*i),-(bottom_w/2-in/2)])
            circle(d=bolt);
        }
        

pock_field = 90;   // field diameter
pock_pitch = 6;    // center-to-center spacing

R = pock_field/2 - pock_r;
row_h = pock_pitch * sin(60);

for (j = [-ceil(R/row_h) : ceil(R/row_h)]) {
    y = j * row_h;
    xoff = (j % 2 == 0) ? 0 : pock_pitch/2;
    for (i = [-ceil(R/pock_pitch) : ceil(R/pock_pitch)]) {
        x = i*pock_pitch + xoff;
        if (x*x + y*y <= R*R)
            translate([x,y]) circle(r=pock_r, $fn=16);
    }
}
    }
}
check=false;
if(check){
for(i=[0:1]){
    color("blue")
            translate([(bottom_w/4-bottom_w/2*i),-(bottom_w/2-in/2),5])
            square(in,center=true);
        }
        color("red")
        translate([0,0,10])
        square(92,center=true);
        
    }
bottom_plate();

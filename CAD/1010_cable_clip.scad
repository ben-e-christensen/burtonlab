$fn=100;

in=25.4;

w=0.256*in-.1;
d=0.323*in-.1-3;
w_plus=15-.1;
slot=6;

echo(d);

difference(){
    union(){
linear_extrude(height=10)
    polygon(points=[
        [-w_plus/2, 0],
        [w_plus/2, 0],
        [w/2, -d],
        [-w/2, -d],
    ]);
        translate([0,1.25,5])
        cube([slot,2.5,10],center=true);
        translate([0,w_plus/2+4,0])
        difference(){
            cylinder(10,d=w_plus+5);
            translate([0,0,-1])
            cylinder(15,d=w_plus+2);
        }
    }
    translate([0,2,1])
    cube([w/2,d*3,20],center=true);
    
}
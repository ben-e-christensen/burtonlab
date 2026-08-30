$fn=100;

in=25.4;
z=5;

diam=7.5*in;
echo(diam);

cylinder(5,d=diam);
difference(){
    cylinder(50,d=diam+in/4);
    cylinder(500,d=diam);
}

colors=["blue","gray","black","green"];

color("red")
translate([0,0,15])
cube([80,80,5],center=true);


for(i=[0:3]){
    color(colors[i])
    translate([0,0,20])
    rotate([30,0,i*90])
    translate([0,diam/2-30,0])
    cube([60,60,5],center=true);
}

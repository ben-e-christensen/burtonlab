$fn=100;

in=25.4;
side=8*in;

w=in*4;
h=in/2+.05;

space=29/2+9+in/2;

module cutout(sq=true){
    if(sq){
        difference(){
            square(side,center=true);
            translate([0,-space-h/2])
            square([w,h],center=true);
        }
    } else {
        square([w,h],center=true);
    }
}
visual=true;
if(visual){
    //camera
color("black")
translate([0,0,-3])
square([30,29],center=true);

//bottom bracket
color("blue")
translate([0,-29/2-4.5,-3])
square([30,9],center=true);

//1/2 inch acrylic spacer
color("purple")
translate([0,-29/2-9-in/4,-3])
square([30,in/2],center=true);
    
color("grey")
translate([-w/2+in/2,-space+h/2+in/4,-3])
square(in,center=true);
    
    color("grey")
translate([w/2-in/2,-space+h/2+in/4,-3])
square(in,center=true);
}

cutout();

//focal diam = 63.5
// cam height with spacer (from mid) = 29/2 + 9

echo(63.5/2-(29/2+9));
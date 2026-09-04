$fn=100;


IR=51.5/2;
OR=IR+6;
h=15;
x=8;
y=18;
in=25.4;
sq_x=100;
sq_y=OR*2+25;
sq_h=6;

bolt=in/4+.2;

side=in*3.25;

echo(sq_x/2-15);
echo(sq_y/2 - 15);

difference(){
    square(side,center=true);
    
    circle(d=in);
    
    for(i=[0:1]){
                translate([sq_x/2 - 15, (-1)^i*(sq_y/2 - 15)])
                circle(d=bolt);
            }
    for(i=[0:1]){
                translate([-sq_x/2 + 15, (-1)^i*(sq_y/2 - 15)])
                circle(d=bolt);
            }
}
use <camera_plate.scad>
use <door.scad>
use <joiner.scad>


in=25.4;
spacer=5;


plate();

translate([9.5*in+spacer,0,0])
plate();

translate([6.5,-6.5*in-spacer,0])
camera_plate();
translate([6.5+in*10+spacer,-6.5*in-spacer,0])
camera_plate();

translate([(15*in+2),-2*in-2,0])
join();
translate([(15*in+2),2*in,0])
join();

translate([(15*in+2+(in+5)),-2*in-2,0])
join();
translate([(15*in+2+(in+5)),2*in,0])
join();

translate([(15*in+2+(in+5)*2),-2*in-2,0])
join();
translate([(15*in+2+(in+5)*2),2*in,0])
join();

translate([(15*in+2+(in+5)*3),-2*in-2,0])
join();
translate([(15*in+2+(in+5)*3),2*in,0])
join();
$fn=100;

bolt=4.25;
from_edge=5+4.4/2;
edge=22.5;

module spacer(){
    difference(){
        polygon(points=[[0, 0], [edge, 0], [0, edge]]);
        
        translate([from_edge,from_edge])
        circle(d=bolt);
    }
}

module sq(){
    for(i=[0:1]){
        rotate([0,0,i*180])
        translate([-i*(edge+2),-i*(edge+2),0])
        
        spacer();
    }
}

module cut() {
    for(i=[0:8]){
        if(i>5){
        translate([(i-6)*(edge+4),2*(edge+4),0])
        sq();
        }else if(i>2){
        translate([(i-3)*(edge+4),(edge+4),0])
        sq();
        }
        else {
        translate([i*(edge+4),0,0])
        sq();
        }
}
}
cut();
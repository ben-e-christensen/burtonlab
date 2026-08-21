**Charge Readings - Kiethley**

Function generator was set to a square wave at 250mHz, 10Vpp, 50% duty cylce, with no offset. Due to the function generator expecting a 50 ohm impedance on the load, and what we were probing (the metal ball soldered to a copper wire) was an open circuit we actually saw a 20Vpp swing, i.e. going from +10V to -10V. This is evident from the transfer function of the circuit: 

$V_{load}=V_{source}\times\frac{R_L}{R_L+R_S}$

Normal impedance matching lines, i.e. $R_L$ and $R_S$ both equal 50, makes $V_{load}=\frac{1}{2}V_{source}$, which is what the function generator expects and so it actually pushes 20Vpp when it is set to 10Vpp. In our case $R_L=\inf$ so we see $V_{load}=V_{source}$, which is all perhaps a bit long winded way of saying this is why we see a 20V swing on the potential of the ball, even though the function generator is set to 10Vpp. 

Given that, the charge on the ball (ignoring that of the wire and the little clump of solder connecting the two) is: 

$Q=4\pi \epsilon _{0}rV$ 
The radius of the ball is 3.175*10e-3m. At 10V the ball has a Q of 3.53pC and at -10V will have -3.53pC. So when we see the pulse of the square wave happens, in either direction, we should expect to see $\Delta Q$ of ~7pC.
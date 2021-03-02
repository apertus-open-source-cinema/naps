
# Protocol
* 1 Clock lane (TODO: which lane?)
* 4 Data lanes (TODO: which lanes)
* 0x00 and 0xFF codes are disallowed
* in idle (when no data is to be sent) the transmitter transmits 0x00 and 0xFF alternating
* the 0x00 0xFF pattern is used for training (both bit alignment and word alignment)
* 12 consecutive bits are sent one one lane. the next 12 bits are on the next lane

```
       bit number
lvds0: 01 02 03 04 05 06 07 08 
lvds1: 09 10 11 12 13 14 15 16
lvds2: 17 28 19 20 21 22 23 24
lvds3: 25 26 27 28 29 30 31 32
lane5 is clock
```